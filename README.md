# Agent Memory Vault (`agent-memory-vault`)

[![npm version](https://img.shields.io/npm/v/agent-memory-vault.svg)](https://www.npmjs.com/package/agent-memory-vault)
[![npm downloads](https://img.shields.io/npm/dm/agent-memory-vault.svg)](https://www.npmjs.com/package/agent-memory-vault)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A zero-dependency, local persistent memory architecture for AI coding agents. 

Designed to prevent context degradation, eliminate hallucinations, resolve contradictory instructions, and stop token waste across software projects.

---

## Overview

Modern AI coding agents (Antigravity, Cursor, Claude Code, Windsurf, Copilot) are bounded by finite context windows. Over long sessions or across multiple days:
- **Context Degradation**: Earlier decisions are forgotten, causing agents to repeat previously resolved bugs.
- **Token Inefficiency**: Ingesting entire chat transcripts or raw documentation burns tens of thousands of tokens per request.
- **Contradictory Knowledge**: When project dependencies or architectures change (e.g., migrating from `npm` to `pnpm`), traditional vector stores often retrieve conflicting versions of facts.
- **Lack of Session Continuity**: Fresh chat sessions start blind, unaware of where prior work ended.

**Agent Memory Vault** solves these challenges by providing an autonomous, 100% local cognitive memory layer that acts as the single source of truth for your codebase.

---

## Architecture & Core Mechanics

### 1. The Vault as the Source of Truth
All project invariants, tech stack specifications, environment quirks, and architectural rules are stored in human-readable Markdown files with YAML frontmatter. The agent is explicitly instructed to treat the vault as the authoritative record rather than guessing or relying on probabilistic assumptions.

### 2. Hierarchical, Token-Lean Retrieval
Instead of dumping full files into context, `memory.py recall` executes queries against a local SQLite FTS5 index in ~2ms on CPU and returns only card IDs, tags, and one-line summaries (~50–80 tokens total). Full file bodies are loaded only if strictly necessary.

### 3. Central Compass (`INDEX.md`)
The vault maintains an auto-generated Map of Content (`INDEX.md`). At the start of a task, agents glance at this directory (~120 tokens) to immediately locate and navigate to the relevant pointer, avoiding blind directory searches.

### 4. Scalable Linked-Chain Sessions (`sessions/`)
Rather than overwriting a single session file, each session is preserved as a timestamped card (`session_YYYYMMDD_HHMMSS.md`) that links to the previous session (`previous_session: SES-...`). This creates an immutable audit trail and ensures seamless handoffs across fresh chat windows.

### 5. Contradiction Resolution via Superseding
When requirements or tools change, older records are updated to `status: superseded` and linked to the replacement card. The retrieval engine excludes superseded cards from active search by default, preventing conflicting advice from reaching prompt context.

### 6. Auto-Enforced Conciseness Gatekeeper
Memory summaries are strictly validated and capped at 220 characters. Overly verbose summaries are automatically trimmed to preserve high-signal density and prevent token bloat.

### 7. Zero External Dependencies
Built entirely on the Python Standard Library (`sqlite3` with FTS5, `pathlib`, `json`, `argparse`). Requires no cloud databases, Docker containers, or `pip install` commands.

---

## Quickstart

### Option 1: Instant Setup via npx (Recommended)

Run directly in the root of any existing project:

```bash
npx agent-memory-vault init
```

Or install globally for use across all local repositories:

```bash
npm install -g agent-memory-vault
agent-memory-vault init
```

This single command automatically:
- Scaffolds `memory-vault/` and configures `AGENTS.md` without overwriting existing project rules.
- Analyzes project files to auto-detect your stack (Laravel, Next.js, Vite, Pest, Python, etc.) and writes them to `profile.md`.
- Builds the SQLite FTS5 index and initializes the central compass (`INDEX.md`).
- Creates the initial session handoff card.

### Option 2: Direct Setup (No Node.js Required)

If working in environments without Node.js or npm, copy `memory-vault/` and `AGENTS.md` into your project root and initialize directly with Python:

```bash
python memory-vault/memory.py init
```

### Verification

Check vault status and ensure the FTS5 index is active:

```bash
python memory-vault/memory.py status
```

Your AI assistant will now autonomously ground itself before taking action and record verified solutions upon completing tasks.

---

## Autonomous Agent Lifecycle

Every agent follows a three-phase operational cycle:

```
[Incoming User Task]
        │
        ▼
Phase 1: Pre-Task Recall ────► Run 'memory.py context' or inspect 'INDEX.md'
        │
        ▼
Phase 2: Task Execution  ────► Adhere to rules.md; treat vault as source of truth
        │
        ▼
Phase 3: Post-Task Write ────► Persist verified findings; update session handoff
```

---

## CLI Reference

### Grounding & Search
| Command | Purpose |
| :--- | :--- |
| `python memory-vault/memory.py context` | Outputs ~130 token grounding payload (profile, active rules, last session handoff) |
| `python memory-vault/memory.py recall "<query>"` | Token-lean peek search (returns 1-line summaries & pointers) |
| `python memory-vault/memory.py recall "<query>" --full` | Search and display full card contents |
| `python memory-vault/memory.py get <id>` | Fetch exact full content of a specific card |

### Record & Memory Management
| Command | Purpose |
| :--- | :--- |
| `python memory-vault/memory.py record ...` | Create an atomic memory card and update index (`--type`, `--title`, `--summary`, `--tags`, `--content`) |
| `python memory-vault/memory.py record ... --next "..."` | Create an episode card and automatically update active session handoff |
| `python memory-vault/memory.py record ... --supersedes <id>` | Create a card while flagging an older conflicting card as superseded |
| `python memory-vault/memory.py supersede <old> <new>` | Explicitly link an old card as superseded by a newer card |

### Session Chain Management
| Command | Purpose |
| :--- | :--- |
| `python memory-vault/memory.py session start [--goal "..."]` | Start a new session card linked to the previous session |
| `python memory-vault/memory.py session log --task "..." [--next "..."]` | Append completed task progress to active session handoff |
| `python memory-vault/memory.py session list` | Display the full chronological linked chain of sessions |
| `python memory-vault/memory.py session current` | View the complete active session card |

### Maintenance & Health
| Command | Purpose |
| :--- | :--- |
| `python memory-vault/memory.py status` | View active, superseded, and archived card counts and database status |
| `python memory-vault/memory.py reindex` | Rebuild SQLite FTS5 database and `INDEX.md` from markdown files |
| `python memory-vault/memory.py prune [--days 60]` | Archive episodes older than specified TTL to keep active index compact |

---

## Directory Layout

```
project-root/
├── AGENTS.md                  # Autonomous agent memory protocol (non-destructive)
└── memory-vault/
    ├── memory.py              # Single-file CLI engine (SQLite FTS5, indexing, lifecycle)
    ├── INDEX.md               # Central Map of Content (Library catalog / pointers)
    ├── profile.md             # Project & user profile (OS, stack, conventions)
    ├── rules.md               # Hard anti-patterns and guardrails ("don't do X")
    ├── sessions/              # Chronological linked session records (audit trail)
    ├── knowledge/             # Concise atomic architectural knowledge cards
    ├── episodes/              # Concise task resolutions, bug fixes, and outcomes
    ├── archive/               # Pruned historical records past TTL
    ├── .gitignore             # Ignores .system/ binary cache from git
    ├── .system/               # Local SQLite FTS5 index database (.index.db)
    └── README.md              # Vault-internal documentation
```

---

## License

MIT
