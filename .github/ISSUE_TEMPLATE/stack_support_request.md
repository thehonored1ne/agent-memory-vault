---
name: Tech Stack / Framework Request
about: Request automatic stack detection for a new language, framework, or test runner
title: '[STACK] Support '
labels: 'enhancement, stack-detection'
assignees: ''
---

**Requested Stack / Tool**
- Framework / Tool Name: [e.g. Django, SvelteKit, Rust Cargo, Go, FastAPI]
- Category: [e.g. Backend, Frontend, Testing, Package Manager]

**Identifying Files**
What files in a project indicate this stack is being used?
- [e.g. `Cargo.toml`, `go.mod`, `manage.py`, `svelte.config.js`]

**Recommended Invariants & Rules**
What defaults or conventions should the memory vault detect and place into `profile.md` or `rules.md` for AI agents working in this stack?
- [e.g. Prefer `cargo test`, avoid editing `target/` directory, use `poetry run`]
