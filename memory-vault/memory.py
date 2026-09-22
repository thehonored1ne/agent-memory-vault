#!/usr/bin/env python3
"""
Autonomous Persistent Memory Vault Engine
Zero-dependency, 100% local memory system for AI agents.
Features:
- FTS5 Full-text search with token-efficient summary peeks
- Central Map of Content (INDEX.md) auto-generation
- Contradiction resolution & card superseding
- Autonomous lifecycle & pruning
- Auto-detection of project stacks (Laravel, Next.js, Python, etc.)
- Strict conciseness gatekeeper
- One-shot context generator (memory.py context)
"""

import argparse
import datetime
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
from typing import Dict, List, Optional, Tuple
import uuid

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

VAULT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = VAULT_DIR.parent
SYSTEM_DIR = VAULT_DIR / ".system"
DB_PATH = SYSTEM_DIR / "index.db"
KNOWLEDGE_DIR = VAULT_DIR / "knowledge"
EPISODES_DIR = VAULT_DIR / "episodes"
ARCHIVE_DIR = VAULT_DIR / "archive"
INDEX_FILE = VAULT_DIR / "INDEX.md"
PROFILE_FILE = VAULT_DIR / "profile.md"
RULES_FILE = VAULT_DIR / "rules.md"
SESSIONS_DIR = VAULT_DIR / "sessions"
GITIGNORE_FILE = VAULT_DIR / ".gitignore"

CONCISENESS_NOTICE = (
    "> **CRITICAL RULE FOR ALL NOTES & CARDS:**\n"
    "> All contents must be concise and straight to the point. "
    "Include only high-signal, necessary information. No fluff, no filler.\n"
)
MAX_SUMMARY_LENGTH = 220

# ----------------------------------------------------------------------
# Frontmatter Parser & Formatter (Zero-dependency YAML subset)
# ----------------------------------------------------------------------
def parse_frontmatter(content: str) -> Tuple[Dict[str, any], str]:
    """Extracts YAML frontmatter and body from markdown text."""
    data = {}
    body = content
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", content, re.DOTALL)
    if match:
        raw_yaml, body = match.groups()
        for line in raw_yaml.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip()
                if val.startswith("[") and val.endswith("]"):
                    items = [x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip()]
                    data[key] = items
                elif (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    data[key] = val[1:-1]
                else:
                    data[key] = val
    return data, body.strip()

def format_frontmatter(metadata: Dict[str, any], body: str) -> str:
    """Formats metadata and body into standard markdown with YAML frontmatter."""
    lines = ["---"]
    for k, v in metadata.items():
        if isinstance(v, list):
            items_str = ", ".join(f'"{x}"' if " " in x else x for x in v)
            lines.append(f"{k}: [{items_str}]")
        elif isinstance(v, str) and (":" in v or "\n" in v or '"' in v):
            escaped = v.replace('"', '\\"')
            lines.append(f'{k}: "{escaped}"')
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + body.strip() + "\n"

# ----------------------------------------------------------------------
# SQLite Storage & FTS5 Indexing
# ----------------------------------------------------------------------
def get_db_connection() -> sqlite3.Connection:
    SYSTEM_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            type TEXT,
            title TEXT,
            summary TEXT,
            tags TEXT,
            path TEXT,
            status TEXT DEFAULT 'active',
            superseded_by TEXT DEFAULT '',
            created_at TEXT,
            updated_at TEXT,
            body TEXT
        )
    """)
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            id,
            title,
            summary,
            tags,
            body,
            content='memories',
            content_rowid='rowid'
        )
    """)
    cursor.executescript("""
        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
            INSERT INTO memories_fts(rowid, id, title, summary, tags, body)
            VALUES (new.rowid, new.id, new.title, new.summary, new.tags, new.body);
        END;
        CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, id, title, summary, tags, body)
            VALUES('delete', old.rowid, old.id, old.title, old.summary, old.tags, old.body);
        END;
        CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, id, title, summary, tags, body)
            VALUES('delete', old.rowid, old.id, old.title, old.summary, old.tags, old.body);
            INSERT INTO memories_fts(rowid, id, title, summary, tags, body)
            VALUES (new.rowid, new.id, new.title, new.summary, new.tags, new.body);
        END;
    """)
    conn.commit()

# ----------------------------------------------------------------------
# Project Stack Auto-Detection (Laravel, Node, Python, etc.)
# ----------------------------------------------------------------------
def detect_project_stack() -> Dict[str, any]:
    """Inspects project root to auto-detect framework, language, and tooling."""
    detected = {
        "frameworks": [],
        "languages": [],
        "tools": [],
        "notes": []
    }
    
    # 1. Check PHP / Laravel (composer.json)
    composer_file = PROJECT_ROOT / "composer.json"
    if composer_file.exists():
        detected["languages"].append("PHP")
        try:
            cdata = json.loads(composer_file.read_text(encoding="utf-8"))
            req = cdata.get("require", {})
            dev_req = cdata.get("require-dev", {})
            all_pkgs = {**req, **dev_req}

            if "laravel/framework" in req:
                detected["frameworks"].append(f"Laravel ({req['laravel/framework']})")
            if (PROJECT_ROOT / "artisan").exists():
                detected["tools"].append("Artisan CLI")
            if "pestphp/pest" in all_pkgs:
                detected["tools"].append("Pest (Test Runner)")
            elif "phpunit/phpunit" in all_pkgs:
                detected["tools"].append("PHPUnit (Test Runner)")
            if "livewire/livewire" in all_pkgs:
                detected["frameworks"].append("Livewire")
            if "inertiajs/inertia-laravel" in all_pkgs:
                detected["frameworks"].append("Inertia.js")
            if "filament/filament" in all_pkgs:
                detected["frameworks"].append("Filament Admin")
        except Exception:
            pass

    # 2. Check JavaScript / TypeScript (package.json)
    pkg_file = PROJECT_ROOT / "package.json"
    if pkg_file.exists():
        detected["languages"].append("JavaScript/TypeScript")
        try:
            pdata = json.loads(pkg_file.read_text(encoding="utf-8"))
            deps = {**pdata.get("dependencies", {}), **pdata.get("devDependencies", {})}
            if "next" in deps:
                detected["frameworks"].append("Next.js")
            if "vite" in deps:
                detected["frameworks"].append("Vite")
            if "vue" in deps:
                detected["frameworks"].append("Vue")
            if "react" in deps:
                detected["frameworks"].append("React")
            if "tailwindcss" in deps:
                detected["tools"].append("Tailwind CSS")
        except Exception:
            pass

        # Package manager lockfile
        if (PROJECT_ROOT / "pnpm-lock.yaml").exists():
            detected["tools"].append("pnpm")
        elif (PROJECT_ROOT / "yarn.lock").exists():
            detected["tools"].append("yarn")
        elif (PROJECT_ROOT / "bun.lockb").exists():
            detected["tools"].append("bun")
        elif (PROJECT_ROOT / "package-lock.json").exists():
            detected["tools"].append("npm")

    # 3. Check Python
    if any((PROJECT_ROOT / f).exists() for f in ["pyproject.toml", "requirements.txt", "Pipfile"]):
        detected["languages"].append("Python")

    # 4. Check Rust / Go
    if (PROJECT_ROOT / "Cargo.toml").exists():
        detected["languages"].append("Rust")
    if (PROJECT_ROOT / "go.mod").exists():
        detected["languages"].append("Go")

    return detected

def apply_auto_detection():
    """Updates profile.md and rules.md based on detected stack."""
    stack = detect_project_stack()
    if not (stack["frameworks"] or stack["languages"]):
        return

    # Update profile.md
    if PROFILE_FILE.exists():
        content = PROFILE_FILE.read_text(encoding="utf-8")
        if "## Auto-Detected Project Stack" not in content:
            section = ["\n## Auto-Detected Project Stack"]
            if stack["languages"]:
                section.append(f"- **Languages**: {', '.join(set(stack['languages']))}")
            if stack["frameworks"]:
                section.append(f"- **Frameworks**: {', '.join(set(stack['frameworks']))}")
            if stack["tools"]:
                section.append(f"- **Tooling**: {', '.join(set(stack['tools']))}")
            section_str = "\n".join(section) + "\n"
            PROFILE_FILE.write_text(content.strip() + section_str, encoding="utf-8")
            print("Updated profile.md with auto-detected project stack.")

    # If Laravel detected, add Laravel-specific rules if missing
    if any("Laravel" in f for f in stack["frameworks"]) and RULES_FILE.exists():
        rcontent = RULES_FILE.read_text(encoding="utf-8")
        if "Laravel Rules" not in rcontent:
            laravel_rules = (
                "\n## Laravel Rules\n"
                "- **Cache Clearing**: Run `php artisan optimize:clear` after editing `.env` or configuration.\n"
                "- **Validation**: Prefer FormRequest classes over inline controller validation.\n"
            )
            if any("Pest" in t for t in stack["tools"]):
                laravel_rules += "- **Testing**: Use Pest syntax (`test('...', function () { ... })`), avoid PHPUnit class tests.\n"
            RULES_FILE.write_text(rcontent.strip() + laravel_rules + "\n", encoding="utf-8")
            print("Added Laravel-specific guardrails to rules.md.")

# ----------------------------------------------------------------------
# Vault Management & Indexing
# ----------------------------------------------------------------------
def ensure_vault_gitignore():
    """Ensures .system/ is ignored while notes stay committed in git."""
    if not GITIGNORE_FILE.exists():
        GITIGNORE_FILE.write_text(".system/\n*.pyc\n__pycache__/\n", encoding="utf-8")

def ensure_agents_md():
    """Safely ensures AGENTS.md has the memory protocol without overwriting existing content."""
    agents_file = PROJECT_ROOT / "AGENTS.md"
    protocol_marker = "Autonomous Agent Memory Protocol"
    
    protocol_snippet = (
        "\n\n---\n"
        "# 🧠 Autonomous Agent Memory Protocol & Operational Directives\n\n"
        "> **CRITICAL DIRECTIVE (MANDATORY FOR ALL ACTIONS & MEMORIES):**\n"
        "> All memory notes, summaries, cards, and responses must be **concise and straight to the point**.\n"
        "> Include only high-signal, necessary facts, code patterns, and verified solutions.\n"
        "> Eliminate conversational filler, redundant explanations, and unverified assumptions.\n\n"
        "### 🔄 The 3-Phase Autonomous Task Lifecycle\n"
        "1. **Phase 1: Pre-Task Recall**: Run `python memory-vault/memory.py context` or glance at `memory-vault/INDEX.md`.\n"
        "2. **Phase 2: Task Execution**: Adhere to learned rules in `memory-vault/rules.md`.\n"
        "3. **Phase 3: Post-Task Write**: Run `python memory-vault/memory.py record --type episode ...` after completing tasks.\n\n"
        "See `memory-vault/INDEX.md` and `memory-vault/README.md` for full instructions.\n"
    )

    if not agents_file.exists():
        agents_file.write_text(protocol_snippet.strip() + "\n", encoding="utf-8")
        print("Created AGENTS.md with Autonomous Memory Protocol.")
    else:
        existing_content = agents_file.read_text(encoding="utf-8")
        if protocol_marker not in existing_content:
            agents_file.write_text(existing_content.rstrip() + protocol_snippet, encoding="utf-8")
            print("Appended Autonomous Memory Protocol to existing AGENTS.md without overwriting.")

def collect_all_markdown_files() -> List[Path]:
    files = []
    seen = set()
    if PROFILE_FILE.exists():
        files.append(PROFILE_FILE)
        seen.add(PROFILE_FILE.resolve())
    if RULES_FILE.exists():
        files.append(RULES_FILE)
        seen.add(RULES_FILE.resolve())
    for folder in [KNOWLEDGE_DIR, EPISODES_DIR, SESSIONS_DIR, ARCHIVE_DIR]:
        if folder.exists():
            for f in sorted(folder.glob("*.md")):
                if f.resolve() not in seen:
                    files.append(f)
                    seen.add(f.resolve())
    return files

def reindex_vault() -> int:
    """Scans all vault markdown files, rebuilds SQLite FTS index and INDEX.md."""
    conn = get_db_connection()
    init_db(conn)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM memories")
    cursor.execute("DELETE FROM memories_fts")

    files = collect_all_markdown_files()
    count = 0
    records = []
    seen_ids = set()

    for file_path in files:
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue
        meta, body = parse_frontmatter(content)
        if not meta or "id" not in meta:
            continue

        mem_id = meta.get("id", file_path.stem)
        if mem_id in seen_ids:
            continue
        seen_ids.add(mem_id)

        mem_type = meta.get("type", "knowledge")
        title = meta.get("title", file_path.stem)
        summary = meta.get("summary", "")
        tags = ", ".join(meta.get("tags", [])) if isinstance(meta.get("tags"), list) else str(meta.get("tags", ""))
        status = meta.get("status", "active")
        superseded_by = meta.get("superseded_by", "")
        created_at = meta.get("created_at", datetime.date.today().isoformat())
        updated_at = meta.get("updated_at", created_at)
        rel_path = file_path.relative_to(VAULT_DIR).as_posix()

        cursor.execute("""
            INSERT OR REPLACE INTO memories (id, type, title, summary, tags, path, status, superseded_by, created_at, updated_at, body)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (mem_id, mem_type, title, summary, tags, rel_path, status, superseded_by, created_at, updated_at, body))
        count += 1
        records.append({
            "id": mem_id,
            "type": mem_type,
            "title": title,
            "summary": summary,
            "tags": tags,
            "path": rel_path,
            "status": status,
            "superseded_by": superseded_by
        })

    conn.commit()
    conn.close()
    generate_index_file(records)
    return count

def generate_index_file(records: List[Dict[str, any]]):
    """Generates the central Map of Content (INDEX.md)."""
    now = datetime.date.today().isoformat()
    lines = [
        "# 🧭 Memory Vault Index (Map of Content)",
        f"*Last auto-indexed: {now} | Total Active Cards: {len([r for r in records if r['status'] == 'active'])}*",
        "",
        CONCISENESS_NOTICE.strip(),
        "",
        "---",
        "",
        "## 📁 1. System Rules & Profile"
    ]

    # Check latest session in sessions/
    latest_session = get_latest_session()
    if latest_session:
        l_path, l_meta, _ = latest_session
        s_id = l_meta.get("id", l_path.stem)
        rel_path = l_path.relative_to(VAULT_DIR).as_posix()
        total_sessions = len(get_all_sessions())
        lines.append(f"- **[{s_id}]** [{rel_path}]({rel_path}) — Active Session Handoff (Chain: {total_sessions} sessions) `[session, active]`")

    rules_and_profile = [r for r in records if r["type"] in ("profile", "rule") and r["status"] == "active"]
    if rules_and_profile:
        for r in rules_and_profile:
            tag_str = f" `[{r['tags']}]`" if r['tags'] else ""
            summary_str = f" — {r['summary']}" if r['summary'] else ""
            lines.append(f"- **[{r['id']}]** [{r['path']}]({r['path']}){summary_str}{tag_str}")
    elif not latest_session:
        lines.append("*(No active rules or profile)*")

    lines.append("")
    lines.append("## 📁 2. Architecture & Knowledge (`knowledge/`)")
    knowledge_records = [r for r in records if r["type"] == "knowledge" and r["status"] == "active"]
    if knowledge_records:
        for r in knowledge_records:
            tag_str = f" `[{r['tags']}]`" if r['tags'] else ""
            summary_str = f" — {r['summary']}" if r['summary'] else ""
            lines.append(f"- **[{r['id']}]** [{r['path']}]({r['path']}){summary_str}{tag_str}")
    else:
        lines.append("*(No active knowledge cards yet)*")

    lines.append("")
    lines.append("## 📁 3. Past Troubles & Episodes (`episodes/`)")
    episode_records = [r for r in records if r["type"] == "episode" and r["status"] == "active"]
    if episode_records:
        for r in episode_records:
            tag_str = f" `[{r['tags']}]`" if r['tags'] else ""
            summary_str = f" — {r['summary']}" if r['summary'] else ""
            lines.append(f"- **[{r['id']}]** [{r['path']}]({r['path']}){summary_str}{tag_str}")
    else:
        lines.append("*(No active episodes yet)*")

    superseded_records = [r for r in records if r["status"] in ("superseded", "archived")]
    if superseded_records:
        lines.append("")
        lines.append("## 📁 4. Archive & Superseded Records")
        for r in superseded_records:
            sup_str = f" (Superseded by {r['superseded_by']})" if r['superseded_by'] else " (Archived)"
            lines.append(f"- *[{r['id']}]* {r['title']}{sup_str}")

    lines.append("")
    INDEX_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

# ----------------------------------------------------------------------
# Recall / Search Pipeline (Hierarchical & Token-Lean)
# ----------------------------------------------------------------------
def recall_memories(query: str, full: bool = False, include_all: bool = False, limit: int = 5):
    """Searches memories with token-efficient peek mode by default."""
    if not DB_PATH.exists():
        reindex_vault()

    conn = get_db_connection()
    cursor = conn.cursor()

    sanitized_query = re.sub(r"[^\w\s]", " ", query).strip()
    words = [w for w in sanitized_query.split() if len(w) > 1]
    
    status_filter = "" if include_all else "AND status = 'active'"
    results = []

    if words:
        fts_expr = " OR ".join(f'"{w}"*' for w in words)
        try:
            sql = f"""
                SELECT m.id, m.type, m.title, m.summary, m.tags, m.path, m.status, m.updated_at, m.body,
                       bm25(memories_fts) as rank
                FROM memories_fts f
                JOIN memories m ON m.rowid = f.rowid
                WHERE memories_fts MATCH ? {status_filter}
                ORDER BY rank
                LIMIT ?
            """
            cursor.execute(sql, (fts_expr, limit))
            results = cursor.fetchall()
        except Exception:
            results = []

    if not results and words:
        like_clauses = " OR ".join(["title LIKE ? OR summary LIKE ? OR tags LIKE ? OR body LIKE ?"] * len(words))
        params = []
        for w in words:
            p = f"%{w}%"
            params.extend([p, p, p, p])
        sql = f"""
            SELECT id, type, title, summary, tags, path, status, updated_at, body, 1.0 as rank
            FROM memories
            WHERE ({like_clauses}) {status_filter}
            LIMIT ?
        """
        params.append(limit)
        cursor.execute(sql, params)
        results = cursor.fetchall()

    conn.close()

    if not results:
        print(f"No active memories found for query: '{query}'")
        return

    total_chars = sum(len(r['summary'] or '') + len(r['title'] or '') + len(r['tags'] or '') for r in results)
    approx_tokens = (total_chars // 4) + (len(results) * 20)

    print(f"=== Memory Recall: {len(results)} matches (~{approx_tokens} tokens) ===")
    for idx, r in enumerate(results, 1):
        tags_disp = f"[{r['tags']}]" if r['tags'] else "[]"
        print(f"\n[{idx}] [{r['id']}] {r['title']} ({r['type'].upper()})")
        print(f"    Path: memory-vault/{r['path']}")
        print(f"    Tags: {tags_disp}")
        print(f"    Summary: {r['summary'] or '(No summary)'}")
        if full:
            print(f"    --- Content ---")
            for line in (r['body'] or "").splitlines()[:20]:
                print(f"    {line}")
            if len((r['body'] or "").splitlines()) > 20:
                print("    ... [Content truncated, run 'memory.py get <id>' for full]")

# ----------------------------------------------------------------------
# Scalable Linked-Chain Session Management (sessions/)
# ----------------------------------------------------------------------
def get_all_sessions() -> List[Path]:
    """Returns all session files sorted chronologically."""
    if not SESSIONS_DIR.exists():
        return []
    return sorted(list(SESSIONS_DIR.glob("session_*.md")), key=lambda p: p.stem)

def get_latest_session() -> Optional[Tuple[Path, Dict[str, any], str]]:
    """Returns the most recent session file, metadata, and body."""
    sessions = get_all_sessions()
    if not sessions:
        return None
    latest_path = sessions[-1]
    try:
        content = latest_path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(content)
        return latest_path, meta, body
    except Exception:
        return None

def start_new_session(goal: str = "") -> Path:
    """Starts a new timestamped session card linked to the previous session."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now()
    rand_suffix = uuid.uuid4().hex[:4]
    timestamp_id = f"{now.strftime('%Y%m%d_%H%M%S')}_{rand_suffix}"
    display_time = now.strftime("%Y-%m-%d %H:%M")
    session_id = f"SES-{timestamp_id}"
    filename = f"session_{timestamp_id}.md"
    file_path = SESSIONS_DIR / filename

    latest = get_latest_session()
    prev_id = "none"
    prev_next_step = "Initialize project and review rules"
    prev_link = "None (Genesis Session)"

    if latest:
        prev_path, prev_meta, prev_body = latest
        prev_id = prev_meta.get("id", prev_path.stem)
        prev_next_step = prev_meta.get("next_step", "Continue active tasks")
        prev_link = f"[[sessions/{prev_path.name}]]"
        if prev_meta.get("status") == "active":
            prev_meta["status"] = "completed"
            prev_meta["updated_at"] = now.date().isoformat()
            prev_path.write_text(format_frontmatter(prev_meta, prev_body), encoding="utf-8")

    clean_goal = goal.strip() if goal else prev_next_step
    if len(clean_goal) > MAX_SUMMARY_LENGTH:
        clean_goal = clean_goal[:MAX_SUMMARY_LENGTH - 3].rstrip() + "..."

    metadata = {
        "id": session_id,
        "type": "session",
        "title": f"Session {display_time}",
        "date": now.isoformat(timespec="seconds"),
        "previous_session": prev_id,
        "status": "active",
        "summary": clean_goal,
        "next_step": clean_goal,
        "tags": ["session", "active"]
    }

    body = (
        f"\n{CONCISENESS_NOTICE}\n"
        f"# Session: {display_time}\n\n"
        f"## Context Handoff\n"
        f"- **Previous Session**: {prev_link}\n"
        f"- **Picked Up From**: {prev_next_step}\n\n"
        f"## Accomplished This Session\n"
        f"- *Session initiated with goal: {clean_goal}*\n\n"
        f"## Next Recommended Step\n"
        f"- {clean_goal}\n\n"
        f"## Active Blockers / WIP\n"
        f"- None.\n"
    )

    file_path.write_text(format_frontmatter(metadata, body), encoding="utf-8")
    print(f"Started new session card: [{session_id}] sessions/{filename}")
    if prev_id != "none":
        print(f"Linked to previous session: [{prev_id}]")
    reindex_vault()
    return file_path

def update_current_session(completed: str, next_step: str, blockers: str = "None"):
    """Appends task progress and updates handoff in the active session card."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    latest = get_latest_session()
    
    if not latest:
        start_new_session(goal=completed)
        latest = get_latest_session()

    file_path, meta, body = latest
    
    if meta.get("status") == "completed":
        start_new_session(goal=completed)
        latest = get_latest_session()
        file_path, meta, body = latest

    meta["updated_at"] = datetime.date.today().isoformat()
    clean_next = next_step[:MAX_SUMMARY_LENGTH].strip() if next_step else "Continue active project tasks"
    meta["next_step"] = clean_next
    meta["summary"] = f"Last completed: {completed[:100].strip()}"

    accomplished_bullet = f"- {completed.strip()}"
    if "## Accomplished This Session" in body:
        parts = body.split("## Accomplished This Session", 1)
        header = parts[0] + "## Accomplished This Session\n"
        rest = parts[1]
        if "## Next Recommended Step" in rest:
            acc_part, _ = rest.split("## Next Recommended Step", 1)
            clean_acc = acc_part.replace("- *Session initiated with goal:", "- Initial goal:").strip()
            new_body = (
                f"{header}{clean_acc}\n{accomplished_bullet}\n\n"
                f"## Next Recommended Step\n- {clean_next}\n\n"
                f"## Active Blockers / WIP\n- {blockers.strip()}\n"
            )
        else:
            new_body = f"{header}{accomplished_bullet}\n\n## Next Recommended Step\n- {clean_next}\n"
    else:
        new_body = body + f"\n\n## Accomplished This Session\n{accomplished_bullet}\n\n## Next Recommended Step\n- {clean_next}\n"

    file_path.write_text(format_frontmatter(meta, new_body), encoding="utf-8")
    print(f"Logged progress to session [{meta.get('id', file_path.stem)}].")
    reindex_vault()

def list_sessions():
    """Displays the chronological linked chain of all sessions."""
    sessions = get_all_sessions()
    if not sessions:
        print("No sessions recorded yet. Run 'memory.py session start' to begin.")
        return

    print(f"=== Session History Chain ({len(sessions)} sessions) ===")
    for idx, p in enumerate(sessions, 1):
        try:
            meta, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
            s_id = meta.get("id", p.stem)
            prev = meta.get("previous_session", "none")
            status = meta.get("status", "completed").upper()
            summary = meta.get("summary", "(No summary)")
            next_s = meta.get("next_step", "")
            arrow = "-> " if idx > 1 else "   "
            print(f"{arrow}[{idx}] [{s_id}] ({status})")
            print(f"       Summary:   {summary}")
            if next_s:
                print(f"       Next Step: {next_s}")
            print(f"       Prev Link: {prev}")
        except Exception:
            continue

def output_context():
    """Generates a compact, ~120-140 token grounding payload for active tasks."""
    conn = get_db_connection()
    init_db(conn)
    cursor = conn.cursor()

    # Get profile summary
    cursor.execute("SELECT summary FROM memories WHERE type = 'profile' AND status = 'active' LIMIT 1")
    p_row = cursor.fetchone()
    profile_summary = p_row['summary'] if p_row else "Standard development environment"

    # Get latest session handoff
    session_handoff = None
    latest_session = get_latest_session()
    if latest_session:
        l_path, l_meta, _ = latest_session
        s_id = l_meta.get("id", l_path.stem)
        l_summary = l_meta.get("summary", "")
        l_next = l_meta.get("next_step", "Continue active project tasks")
        l_prev = l_meta.get("previous_session", "none")
        session_handoff = (
            f"- Active Session: [{s_id}] (Previous: {l_prev})\n"
            f"- Last Progress:  {l_summary}\n"
            f"- Next Step:      {l_next}"
        )

    # Get top active rules
    cursor.execute("SELECT summary, body FROM memories WHERE type = 'rule' AND status = 'active' LIMIT 1")
    r_row = cursor.fetchone()
    rules_text = []
    if r_row and r_row['body']:
        for line in r_row['body'].splitlines():
            line = line.strip()
            if line.startswith("- **") or line.startswith("- "):
                rules_text.append(line)
    rules_block = "\n".join(rules_text[:5]) if rules_text else "- Keep all actions concise and verified."

    # Get last 2 active episodes
    cursor.execute("""
        SELECT id, title, summary FROM memories 
        WHERE type = 'episode' AND status = 'active' 
        ORDER BY created_at DESC, id DESC LIMIT 2
    """)
    recent_episodes = cursor.fetchall()
    conn.close()

    print("=== Agent Grounding Context (~130 tokens) ===")
    print(f"Profile: {profile_summary}")
    if session_handoff:
        print(f"\nWhere We Left Off:\n{session_handoff}")
    print(f"\nActive Rules:\n{rules_block}")
    if recent_episodes:
        print("\nRecent Verified Learnings:")
        for ep in recent_episodes:
            print(f"- [{ep['id']}] {ep['title']}: {ep['summary']}")
    print("=============================================")

# ----------------------------------------------------------------------
# Card Lookup & Recording
# ----------------------------------------------------------------------
def get_card(card_id: str):
    """Outputs the complete content of a specific card."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, path, status, superseded_by, body FROM memories WHERE id = ?", (card_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        print(f"Card '{card_id}' not found.")
        return

    full_path = VAULT_DIR / row['path']
    if full_path.exists():
        print(full_path.read_text(encoding="utf-8"))
    else:
        print(f"# {row['title']} [{row['id']}]\n\n{row['body']}")

def record_memory(
    card_type: str,
    title: str,
    summary: str,
    tags: List[str],
    content: str,
    supersedes: Optional[str] = None,
    next_step: Optional[str] = None
):
    """Records a new atomic memory card with strict conciseness enforcement and rolling session update."""
    clean_summary = summary.strip()
    
    # Strict Conciseness Gatekeeper
    if len(clean_summary) > MAX_SUMMARY_LENGTH:
        print(f"[!] Conciseness Notice: Summary exceeded {MAX_SUMMARY_LENGTH} characters.")
        clean_summary = clean_summary[:MAX_SUMMARY_LENGTH - 3].rstrip() + "..."
        print(f"    Auto-trimmed to: '{clean_summary}'")

    today = datetime.date.today().isoformat()
    now_clean = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"

    prefix = {"episode": "EP", "knowledge": "KN", "rule": "RUL"}.get(card_type, "MEM")
    card_id = f"{prefix}-{now_clean}"

    target_dir = EPISODES_DIR if card_type == "episode" else KNOWLEDGE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^\w\-]", "_", title.lower()).strip("_")[:40]
    filename = f"{card_id.lower()}_{slug}.md"
    file_path = target_dir / filename

    metadata = {
        "id": card_id,
        "type": card_type,
        "title": title.strip(),
        "summary": clean_summary,
        "status": "active",
        "tags": [t.strip() for t in tags if t.strip()],
        "created_at": today,
        "updated_at": today
    }
    if supersedes:
        metadata["supersedes"] = supersedes

    body_content = f"\n{CONCISENESS_NOTICE}\n# {title.strip()}\n\n{content.strip()}\n"
    full_text = format_frontmatter(metadata, body_content)
    file_path.write_text(full_text, encoding="utf-8")
    print(f"Saved memory card: [{card_id}] {file_path.relative_to(VAULT_DIR)}")

    # Rolling Checkpoint: Auto-update session handoff on completed episode
    if card_type == "episode":
        step_desc = next_step.strip() if next_step else "Continue active project tasks"
        update_current_session(completed=f"[{card_id}] {title.strip()}: {clean_summary}", next_step=step_desc)

    if supersedes:
        supersede_card(supersedes, card_id)

    reindex_vault()

def supersede_card(old_id: str, new_id: str):
    """Marks an older card as superseded by a newer card."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT path FROM memories WHERE id = ?", (old_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        print(f"Warning: Older card '{old_id}' to supersede was not found.")
        return

    old_path = VAULT_DIR / row['path']
    if not old_path.exists():
        return

    content = old_path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(content)
    meta["status"] = "superseded"
    meta["superseded_by"] = new_id
    meta["updated_at"] = datetime.date.today().isoformat()
    warning_banner = f"> [!WARNING]\n> **SUPERSEDED BY [{new_id}] on {meta['updated_at']}**\n> Do not use this card for active context.\n\n"
    new_full_text = format_frontmatter(meta, warning_banner + body)
    old_path.write_text(new_full_text, encoding="utf-8")
    print(f"Marked [{old_id}] as superseded by [{new_id}].")

def prune_vault(days: int = 60):
    """Archives episodes older than `days` days."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.date.today() - datetime.timedelta(days=days)
    archived_count = 0

    for file_path in EPISODES_DIR.glob("*.md"):
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue
        meta, body = parse_frontmatter(content)
        created_str = meta.get("created_at")
        if created_str:
            try:
                card_date = datetime.date.fromisoformat(created_str)
                if card_date < cutoff:
                    meta["status"] = "archived"
                    meta["archived_at"] = datetime.date.today().isoformat()
                    dest = ARCHIVE_DIR / file_path.name
                    dest.write_text(format_frontmatter(meta, body), encoding="utf-8")
                    file_path.unlink()
                    archived_count += 1
                    print(f"Archived stale episode: {file_path.name}")
            except Exception:
                continue

    reindex_vault()
    print(f"Prune complete. {archived_count} stale cards moved to archive.")

def vault_status():
    """Prints current status and health of the vault."""
    conn = get_db_connection()
    init_db(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) as count FROM memories GROUP BY status")
    counts = {r['status']: r['count'] for r in cursor.fetchall()}
    cursor.execute("SELECT type, COUNT(*) as count FROM memories WHERE status = 'active' GROUP BY type")
    type_counts = {r['type']: r['count'] for r in cursor.fetchall()}
    conn.close()

    print("=== Memory Vault Status ===")
    print(f"Location: {VAULT_DIR}")
    print(f"Active Cards:     {counts.get('active', 0)}")
    print(f"Superseded Cards: {counts.get('superseded', 0)}")
    print(f"Archived Cards:   {counts.get('archived', 0)}")
    print("Active by Type:")
    for t, c in type_counts.items():
        print(f"  - {t}: {c}")
    print(f"Index File: {INDEX_FILE} (Exists: {INDEX_FILE.exists()})")
    print(f"SQLite DB:  {DB_PATH} (Exists: {DB_PATH.exists()})")
    print(f".gitignore: {GITIGNORE_FILE} (Exists: {GITIGNORE_FILE.exists()})")

# ----------------------------------------------------------------------
# CLI Interface
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Autonomous Persistent Memory Vault Engine")
    subparsers = parser.add_subparsers(dest="command")

    # init
    subparsers.add_parser("init", help="Initialize or repair vault directory and SQLite FTS5 index")

    # context
    subparsers.add_parser("context", help="Output compact ~120 token grounding context for active task")

    # reindex
    subparsers.add_parser("reindex", help="Rebuild SQLite FTS5 index and INDEX.md from files")

    # recall
    recall_p = subparsers.add_parser("recall", help="Search memory with token-efficient peek mode")
    recall_p.add_argument("query", type=str, help="Search query or task summary")
    recall_p.add_argument("--full", action="store_true", help="Display full card content")
    recall_p.add_argument("--all", action="store_true", help="Include superseded and archived cards")
    recall_p.add_argument("--limit", type=int, default=5, help="Max results (default: 5)")

    # get
    get_p = subparsers.add_parser("get", help="Get full content of a specific card by ID")
    get_p.add_argument("id", type=str, help="Card ID (e.g. PRF-001, EP-20260922...)")

    # record
    rec_p = subparsers.add_parser("record", help="Record a new atomic memory card")
    rec_p.add_argument("--type", choices=["episode", "knowledge", "rule"], default="episode")
    rec_p.add_argument("--title", required=True, help="Short, clear card title")
    rec_p.add_argument("--summary", required=True, help="Concise 1-line summary (max 220 chars)")
    rec_p.add_argument("--tags", required=True, help="Comma-separated tags (e.g. 'auth,jwt,node')")
    rec_p.add_argument("--content", required=True, help="Concise body content")
    rec_p.add_argument("--supersedes", type=str, default=None, help="ID of an older card being superseded")
    rec_p.add_argument("--next", type=str, default=None, help="Recommended next step for rolling session handoff")

    # checkpoint (convenience alias for session log)
    chk_p = subparsers.add_parser("checkpoint", help="Update rolling session handoff checkpoint")
    chk_p.add_argument("--completed", required=True, help="Summary of task just completed")
    chk_p.add_argument("--next", default="Continue active project tasks", help="Next recommended step")
    chk_p.add_argument("--blockers", default="None", help="Active blockers or WIP notes")

    # session command suite
    sess_p = subparsers.add_parser("session", help="Manage linked session audit chain")
    sess_sub = sess_p.add_subparsers(dest="session_action")

    # session start
    s_start = sess_sub.add_parser("start", help="Start a new session linked to previous")
    s_start.add_argument("--goal", type=str, default="", help="Goal for this new session")

    # session log
    s_log = sess_sub.add_parser("log", help="Log task progress to the active session")
    s_log.add_argument("--task", required=True, help="Task completed")
    s_log.add_argument("--next", default="Continue active project tasks", help="Next recommended step")
    s_log.add_argument("--blockers", default="None", help="Active blockers or WIP notes")

    # session list
    sess_sub.add_parser("list", help="List all sessions in chronological chain")

    # session current
    sess_sub.add_parser("current", help="Display full content of active session")

    # supersede
    sup_p = subparsers.add_parser("supersede", help="Explicitly mark an old card superseded by a new one")
    sup_p.add_argument("old_id", type=str)
    sup_p.add_argument("new_id", type=str)

    # prune
    prune_p = subparsers.add_parser("prune", help="Archive episodes older than N days")
    prune_p.add_argument("--days", type=int, default=60)

    # status
    subparsers.add_parser("status", help="Show vault statistics and health")

    args = parser.parse_args()

    if args.command == "init":
        KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
        EPISODES_DIR.mkdir(parents=True, exist_ok=True)
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        ensure_vault_gitignore()
        ensure_agents_md()
        apply_auto_detection()
        count = reindex_vault()
        print(f"Vault initialized successfully with {count} indexed cards.")
    elif args.command == "context":
        output_context()
    elif args.command == "checkpoint":
        update_current_session(args.completed, args.next, args.blockers)
    elif args.command == "session":
        if args.session_action == "start":
            start_new_session(args.goal)
        elif args.session_action == "log":
            update_current_session(args.task, args.next, args.blockers)
        elif args.session_action == "list":
            list_sessions()
        elif args.session_action == "current":
            latest = get_latest_session()
            if latest:
                print(latest[0].read_text(encoding="utf-8"))
            else:
                print("No active session found. Run 'memory.py session start'.")
        else:
            sess_p.print_help()
    elif args.command == "reindex":
        count = reindex_vault()
        print(f"Re-indexing complete. {count} cards indexed.")
    elif args.command == "recall":
        recall_memories(args.query, full=args.full, include_all=args.all, limit=args.limit)
    elif args.command == "get":
        get_card(args.id)
    elif args.command == "record":
        tags_list = [t.strip() for t in args.tags.split(",") if t.strip()]
        record_memory(args.type, args.title, args.summary, tags_list, args.content, args.supersedes, args.next)
    elif args.command == "supersede":
        supersede_card(args.old_id, args.new_id)
        reindex_vault()
    elif args.command == "prune":
        prune_vault(args.days)
    elif args.command == "status":
        vault_status()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
