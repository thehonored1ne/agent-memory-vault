# 🚀 AI-PersistentMemory-Vault: Drop-In Agent Memory

A standalone, 100% local, zero-dependency persistent memory engine for AI coding agents.

> **CRITICAL RULE FOR ALL CONTENTS:**
> All contents must be concise and straight to the point. Include only high-signal, necessary information. No fluff, no filler.

---

## ⚡ How to Drop This Into Any New Project

### Step 1: Copy to Your New Repo
Copy the `memory-vault/` directory and `AGENTS.md` into your new project root:
```
my-new-project/
├── AGENTS.md
└── memory-vault/
```

### Step 2: Initialize
Run the zero-dependency initializer:
```bash
python memory-vault/memory.py init
```
This automatically bootstraps the directory structure and the local SQLite FTS5 index.

### Step 3: Done!
Any AI coding agent (Antigravity, Cursor, Windsurf, Claude Code, Copilot) reading `AGENTS.md` will autonomously:
1. **Recall** relevant memories before taking action.
2. **Adhere** to project anti-patterns in `rules.md`.
3. **Record** task solutions, learnings, and superseding updates upon completing tasks.

---

## 🔑 Core Capabilities

- **Token-Efficient Peek Mode**: `recall` returns 1-line summaries and pointers (~50-100 tokens), preventing context degradation and API cost spikes.
- **Central Compass (`INDEX.md`)**: A consolidated Map of Content where agents quickly glance to navigate directly to target knowledge.
- **Contradiction Resolution (`--supersedes`)**: When new facts emerge, old conflicting cards are marked `status: superseded` and hidden from active search.
- **Zero Dependencies**: Uses Python's built-in `sqlite3` with BM25 FTS5 search. No Docker, no pip installs, no cloud databases.
