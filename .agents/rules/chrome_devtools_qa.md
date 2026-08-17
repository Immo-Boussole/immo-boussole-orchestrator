---
description: Project rule to enforce automated QA, regression checks, security audits, and responsive validation using Chrome DevTools MCP
---

# Chrome DevTools MCP Quality Assurance, Security & Responsive Testing

This rule defines the mandatory validation protocol using the Chrome DevTools MCP for any modification to the user interface (UI), templates, CSS styles, JavaScript files, or frontend routes of **Immo-Boussole Orchestrator**.

---

## 1. Triggers and Prerequisites

- **Triggers**: Any modification impacting visual rendering, frontend interactivity, accessibility, or client-side security.
- **Local Server**:
  - Check that the local development server is running (default: `http://localhost:9000`).
  - If the server is not running, start it in the background:
    ```bash
    python -m uvicorn app.main:app --reload --port 9000
    ```
    Use `run_command` with `IsDaemon: true`.

---

## 2. Multi-Device Validation Protocol (Responsive Design)

In compliance with [responsive_design.md](file:///c:/tools/GitHub/Immo-Boussole/immo-boussole-orchestrator/.agents/rules/responsive_design.md):

1. **Test across a minimum of 3 viewports** using `resize_page` or `emulate`:
   - **Mobile**: $375 \times 667$ px or $390 \times 844$ px (verify hamburger / drawer menus, no horizontal overflow, touch targets $\ge 44$ px).
   - **Tablet**: $768 \times 1024$ px (verify grid/flexbox layouts and portrait/landscape adaptation).
   - **Desktop**: $1280 \times 800$ px and/or $1920 \times 1080$ px (verify wide layouts and legibility).
2. **Visual Screenshots**:
   - Use `take_screenshot` across critical views to validate visual rendering:
     - Dashboard (instance list)
     - Instance detail page (logs terminal, action bar)
     - Add/Edit instance modal

---

## 3. Regression Detection (Zero Error Policy)

1. **JavaScript Console**:
   - Call `list_console_messages` after navigating and interacting with modified components.
   - **Requirement**: Zero unhandled JavaScript errors (`console.error`, uncaught exceptions).
2. **Network & API Requests**:
   - Call `list_network_requests`.
   - **Requirement**: Zero unexpected HTTP error codes ($4\text{xx} / 5\text{xx}$), no missing static assets (CSS, JS, fonts).
   - Pay particular attention to SSE log-streaming endpoints (`/api/instances/{name}/logs/stream`).

---

## 4. Security & Integrity Checks

1. **Auth & Credentials**:
   - Verify the HTTP Basic auth challenge fires correctly on unauthenticated requests (401 + `WWW-Authenticate` header).
   - Ensure no credentials are leaked in the console, DOM attributes, or JavaScript source.
2. **Console Security & Headers**:
   - Verify the absence of security warnings and Content Security Policy (CSP) violations.
3. **Data & Secret Leaks**:
   - Ensure no sensitive information (Docker socket paths, SSH keys, SMTP passwords, webhook URLs) is exposed in the rendered DOM or client-side JS.
4. **XSS & Injection Prevention**:
   - Verify that instance names, log output, and environment values displayed in the UI are consistently sanitized and escaped (Jinja2 autoescaping must be active).

---

## 5. Quality & Accessibility Audits (Lighthouse)

- Run `lighthouse_audit` on major modified pages:
  - `/` (dashboard)
  - `/instances/{name}` (instance detail)
- Verify Accessibility indicators (color contrast for both dark and light themes, `aria` tags, semantic HTML) and Best Practices.

---

## 6. Dark / Light Theme Validation

- After any CSS or theme-related change, test **both themes** by toggling `data-theme` on `<html>`:
  - Verify color contrast ratios meet WCAG AA in both modes.
  - Take screenshots in both modes at desktop and mobile viewports.

---

## 7. Corrective Actions & Reporting

- **Strict Blocking on Anomalies**: Any detected issue (console error, responsive glitch, network failure, auth bypass, or security risk) must be resolved immediately before completing the task.
- **Test Summary**: Summarize all verification steps and findings in the walkthrough or final task response.
