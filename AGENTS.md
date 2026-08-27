# General Guidelines for AI Agents (Immo-Boussole Orchestrator)

This document centralizes all mandatory rules and best practices for any AI agent working on this repository.

---

## 1. Responsive Design & Multi-Device Compatibility

For every code or user interface (UI/UX) modification:

- **Mandatory Multi-Device Support**: Always ensure interfaces render and function optimally across:
  - **PC / Desktop** (standard and widescreen displays)
  - **Tablets** (portrait and landscape orientations)
  - **Smartphones / Mobile Devices** (narrow vertical viewports, touch targets $\ge 44\text{px}$, no undesirable horizontal overflow)
- **CSS & Layout Checks**:
  - Use fluid flexbox/grid layouts and appropriate media queries.
  - Maintain component legibility, accessibility, and responsiveness (modals, banners, forms, instance cards, log terminal).
- **Orchestrator-Specific**: Instance card grids must collapse to single-column on mobile; log terminal panels must scroll horizontally without breaking layout; action buttons must wrap or collapse on narrow viewports.
- **Detailed Reference**: See [.agents/rules/responsive_design.md](file:///c:/tools/GitHub/Immo-Boussole/immo-boussole-orchestrator/.agents/rules/responsive_design.md).

---

## 2. Git Commit Message Format

For every code change:

- Always provide a concise, clear Git commit message in **English** at the end of the response / task summary, adhering to the **Conventional Commits** standard (e.g. `feat(docker)`, `fix(registry)`, `refactor(ui)`, `test(api)`, `docs(...)`).
- **Detailed Reference**: See [.agents/rules/commit_message_guideline.md](file:///c:/tools/GitHub/Immo-Boussole/immo-boussole-orchestrator/.agents/rules/commit_message_guideline.md).

---

## 3. Code Quality, Performance & Testing

- **Unit and Integration Tests**: Run and validate tests (`pytest`) to prevent regressions before marking any task complete.
- **Python 3.12+**: Prefer idiomatic, type-annotated Python. Use `async`/`await` for all I/O-bound operations (Docker SDK calls, SMTP, webhook HTTP requests).
- **Docker SDK**: Always use `python-on-whales` via `asyncio.to_thread()` for blocking calls — never call synchronous Docker SDK methods directly from async FastAPI route handlers.
- **Documentation Integrity**: Preserve docstrings, comments, and the `IMPLEMENTATION_PLAN.md` architecture. Update `IMPLEMENTATION_PLAN.md` if the architecture evolves.
- **Security**: Never log, expose in the API response, or render in the UI any sensitive data: SSH keys, Docker TLS certificates, SMTP passwords, webhook URLs, or the `ADMIN_PASSWORD`.

---

## 4. Frontend QA, Security & Responsive Validation via Chrome DevTools MCP

For any change affecting the UI, CSS, JavaScript, templates, or frontend routes:

- **Responsive Multi-Viewport Verification**: Test and capture screenshots across Mobile (e.g. $375\times 667$ px), Tablet (e.g. $768\times 1024$ px), and Desktop (e.g. $1280\times 800$ px) viewports using `resize_page` / `emulate` / `take_screenshot`. Ensure touch targets $\ge 44\text{px}$ and no horizontal overflow.
- **Regression Detection (Zero Error Policy)**: Verify with `list_console_messages` that there are 0 unhandled JS errors, and with `list_network_requests` that there are no unexpected HTTP $4\text{xx}/5\text{xx}$ errors.
- **Dark/Light Theme**: Always test UI changes in **both themes** (dark and light). Check contrast ratios for both.
- **Auth**: Verify the HTTP Basic auth challenge (401 + `WWW-Authenticate` header) fires on unauthenticated requests. Ensure credentials are never exposed in the DOM.
- **Security & Integrity**: Inspect console and DOM for CSP violations, security warnings, and sensitive data leakage. Ensure proper XSS sanitization via Jinja2 autoescaping.
- **Quality & Accessibility Audits**: Run `lighthouse_audit` on modified pages (`/` dashboard, `/instances/{name}` detail) to check accessibility, performance, and best practices.
- **Detailed Reference**: See [.agents/rules/chrome_devtools_qa.md](file:///c:/tools/GitHub/Immo-Boussole/immo-boussole-orchestrator/.agents/rules/chrome_devtools_qa.md).

---

## 5. Docker & Multi-Host Safety

- **Never assume local Docker**: Always resolve the Docker connection string from the instance config (`local`, `ssh://...`, `tcp://...`) — never hardcode the socket path.
- **Destructive operations** (remove instance, delete volumes): Always require explicit confirmation in the UI (confirm dialog) and explicit `--yes` flag in the CLI. Never auto-confirm.
- **Volume safety**: Default behavior for `remove` must be `--keep-volumes`. Deleting volumes must require a separate, explicit flag (`--delete-volumes`).
- **SSH keys**: SSH private keys used for remote Docker connections must never be stored in `instances.yaml` — reference key file paths only.

---

## 6. Documentation, Internationalization (i18n) & Cross-Repository Parity

- **English First & French Parity**: Write user-facing documentation in English first (`README.md`), and maintain exact parity in French (`README.fr.md`) in the same task/commit.
- **Cross-Repo Ecosystem**: Keep references, navigation banners, and GitHub links aligned across all repositories (`immo-boussole`, `immo-boussole-extension`, `immo-boussole-orchestrator`, `immo-boussole.wiki`).
- **Organization Namespace**: Always use `https://github.com/Immo-Boussole/<repo>`.
- **Text & Structure**: Focus on text, tables, and diagrams; do not spend time generating new screenshots unless requested.
- **Detailed Reference**: See [.agents/rules/documentation_and_i18n.md](file:///c:/tools/GitHub/Immo-Boussole/immo-boussole-orchestrator/.agents/rules/documentation_and_i18n.md).

---

## 7. GitHub Workflow Verification on Pushes & Pull Requests

- **Mandatory Workflow Monitoring**: After pushing code or creating/updating pull requests, always check the status of all triggered GitHub Actions workflows using `gh run list` / `gh run view` / `gh pr checks`.
- **Zero Failure Tolerance**: Never mark a task complete if any workflow job fails (CI, Docker build, lint, quality checks, test suite, security scans).
- **Immediate Failure Resolution**: Inspect failure logs (`gh run view <run-id> --log-failed`), diagnose the root cause, apply fixes, commit and push, and monitor until all workflows are 100% green.
- **Detailed Reference**: See [.agents/rules/github_workflow_verification.md](file:///c:/tools/GitHub/Immo-Boussole/immo-boussole-orchestrator/.agents/rules/github_workflow_verification.md).

---

## 8. Response Formatting & Step Progress Tracking

- **Standardized Step Headers**: Every multi-step response or status update must begin with a Level 3 heading adhering to `### [[current_step]/[total_steps]] [EMOJI] [Descriptive Step Title]`.
- **Technology & Action Emojis**: Always prefix step titles with the corresponding Unicode emoji (e.g. 🐍 Python, 🧪 Tests, 🐳 Docker, 🐙 GitHub, ⚙️ CI/CD, 🧩 WebExtension, 🌐 Frontend/Web, 🔍 Research, 📝 Docs/i18n, 🚀 Deploy/Release, 🛡️ Security, 🧭 Immo-Boussole Domain).
- **Detailed Reference**: See [.agents/rules/step_progress_and_formatting.md](file:///c:/tools/GitHub/Immo-Boussole/immo-boussole-orchestrator/.agents/rules/step_progress_and_formatting.md).

