---
id: RUL-001
type: rule
title: System Rules & Anti-Patterns
summary: Windows path escaping, zero-dependency preference, concise outputs, pre-task recall requirement.
status: active
updated_at: 2026-09-22
tags: [rules, anti-patterns, windows, execution]
---

> **CRITICAL RULE FOR ALL NOTES & CARDS:**
> All contents must be concise and straight to the point. Include only high-signal, necessary information. No fluff, no filler.

# System Rules & Anti-Patterns

## Hard Guardrails
- **Windows Path Handling**: Always use forward slashes (`/`) or escaped backslashes in script paths and command strings.
- **Dependency Minimalization**: Do not introduce heavy dependencies when standard library or native tools suffice.
- **Memory Recency**: Check `INDEX.md` or run `memory.py recall` before executing any multi-step task.
- **Concise Outputs**: Do not repeat explanations; keep answers, logs, and memory entries atomic and focused.
