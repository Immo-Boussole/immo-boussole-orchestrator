---
description: Project rule to always provide a short English commit message after code changes
---

# Commit Message Guideline

For every code change in this project:
- Always provide a concise and descriptive Git commit message in **English** at the end of each response / task walkthrough, adhering to the **Conventional Commits** standard.
- Use the following prefixes as appropriate:
  - `feat(...)` — new feature or capability
  - `fix(...)` — bug fix
  - `refactor(...)` — code restructuring without behavior change
  - `test(...)` — adding or updating tests
  - `docs(...)` — documentation only
  - `chore(...)` — tooling, CI, dependencies
  - `style(...)` — CSS/UI changes with no logic change
  - `perf(...)` — performance improvements

**Scope examples**: `(registry)`, `(docker)`, `(ui)`, `(cli)`, `(mcp)`, `(notifier)`, `(auth)`, `(ci)`.

Example: `feat(docker): add SSH tunnel support for remote Docker hosts`
