# 🧠 Autonomous Agent Memory Protocol & Operational Directives

> **CRITICAL DIRECTIVES (MANDATORY FOR ALL ACTIONS & MEMORIES):**
> 1. **Conciseness**: All memory notes, summaries, cards, and responses must be **concise and straight to the point**. Include only high-signal, necessary facts, code patterns, and verified solutions. Eliminate conversational filler, redundant explanations, and unverified assumptions.
> 2. **Source of Truth**: The `memory-vault/` is the **authoritative single source of truth** for all project conventions, architecture invariants, environment quirks, and session trajectory. Always ground your decisions in the vault before taking action, and persist all verified solutions back to the vault. Never rely on unverified assumptions when vault memory exists.

---

## 🔄 The 3-Phase Autonomous Task Lifecycle

Every AI agent working in this repository MUST follow this 3-phase memory protocol autonomously for every user request:

```
[User Task]
    │
    ▼
Phase 1: Pre-Task Recall ──► (Glance at memory-vault/INDEX.md or run recall)
    │
    ▼
Phase 2: Task Execution  ──► (Adhere to learned rules, avoid past mistakes)
    │
    ▼
Phase 3: Post-Task Write ──► (Persist verified solutions, supersede outdated facts)
```

---

### Phase 1: Pre-Task Memory Recall (Before Taking Action)
Before generating code or executing complex plans, ground yourself in project memory:

1. **Instant Context Grounding (~120 tokens)**:
   ```bash
   python memory-vault/memory.py context
   ```
2. **Glance at Central Compass**:
   Read [INDEX.md](file:///c:/Users/USER/Downloads/AI-PersistentMemory-Vault/memory-vault/INDEX.md) to locate relevant categories and pointers (~150 tokens).
3. **Or Run Peek Recall for Specific Task Keywords**:
   ```bash
   python memory-vault/memory.py recall "<task keywords or problem description>"
   ```
4. **Deep Read (Only if needed)**:
   If a 1-line summary indicates critical past bugs or configuration, read that specific card:
   ```bash
   python memory-vault/memory.py get <CARD_ID>
   ```

---

### Phase 2: Execution with Anti-Pattern Checking
- **Treat the Vault as Source of Truth**: Base all architecture, tool choices, and code designs on verified vault records.
- **Guardrails**: Review [rules.md](file:///c:/Users/USER/Downloads/AI-PersistentMemory-Vault/memory-vault/rules.md) to avoid repeating known mistakes (e.g. Windows PowerShell escaping quirks).
- **Conventions**: Stay strictly aligned with preferences in [profile.md](file:///c:/Users/USER/Downloads/AI-PersistentMemory-Vault/memory-vault/profile.md).

---

### Phase 3: Post-Task Autonomous Record (After Every Completed Task)
Immediately upon successfully completing a non-trivial task or resolving a bug, record the finding before concluding your turn:

#### 1. Record an Episode (Task resolution, bug fix, trial-and-error outcome):
```bash
python memory-vault/memory.py record \
  --type episode \
  --title "Short Descriptive Title" \
  --summary "Concise 1-line summary of problem and solution" \
  --tags "keyword1,keyword2" \
  --content "Concise technical facts: what failed, exact fix, verified command." \
  --next "Next recommended step for session continuity"
```
*(Passing `--next` automatically updates `memory-vault/session.md` so future sessions immediately know where to resume).*

#### 2. Record New Architecture / Knowledge:
```bash
python memory-vault/memory.py record \
  --type knowledge \
  --title "Component Architecture" \
  --summary "Core purpose and interface" \
  --tags "arch,component" \
  --content "Key interfaces and invariants."
```

#### 3. Resolving Contradictions (Superseding Old Knowledge):
If a new solution or user choice contradicts an earlier memory card:
```bash
python memory-vault/memory.py record \
  --type episode \
  --title "Migrated from X to Y" \
  --summary "Replaced X with Y for better performance" \
  --tags "migration,tech" \
  --content "Reason for replacement and new configuration." \
  --supersedes <OLD_CARD_ID>
```
*The engine automatically flags `<OLD_CARD_ID>` as `status: superseded`, hiding it from future searches while preserving history.*

---

## 🛠️ CLI Quick Reference

| Command | Purpose |
| :--- | :--- |
| `python memory-vault/memory.py context` | Instant ~120 token grounding payload (profile, active rules, recent learnings) |
| `python memory-vault/memory.py session start` | Start a new session linked to previous session |
| `python memory-vault/memory.py session list` | View chronological linked session audit trail |
| `python memory-vault/memory.py recall "<query>"` | Token-lean peek search (returns 1-line summaries) |
| `python memory-vault/memory.py recall "<query>" --full` | Search and print full card bodies |
| `python memory-vault/memory.py get <id>` | Fetch exact full content of a card |
| `python memory-vault/memory.py record ...` | Create an atomic memory card and update index |
| `python memory-vault/memory.py supersede <old_id> <new_id>` | Manually link an old card as superseded |
| `python memory-vault/memory.py prune` | Archive episodes older than 60 days |
| `python memory-vault/memory.py status` | Show active/superseded counts and health |
| `python memory-vault/memory.py reindex` | Rebuild SQLite FTS5 database and INDEX.md |
