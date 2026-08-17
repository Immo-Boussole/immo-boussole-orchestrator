# 🎛️ Immo-Boussole Orchestrator — Implementation Plan

## Context & Goal

**Immo-Boussole Orchestrator** is a standalone web + CLI application that manages multiple [Immo-Boussole](https://github.com/Immo-Boussole/immo-boussole) instances running on local or remote Docker hosts. It provides:

- A **FastAPI + Jinja2 web dashboard** with dark/light theme toggle and HTTP Basic auth
- A **Typer CLI** (`orchestrator`) for scripting and automation
- A **Docker control layer** via `python-on-whales`, supporting local socket, remote SSH, and remote TCP/TLS
- A **YAML-based registry** (`instances.yaml`) as the single source of truth
- A **notification system** (Webhook + SMTP email) for unexpected state changes
- An **MCP server** (port 9001) exposing orchestration tools to Claude Desktop
- A **GitHub Actions CI/CD pipeline** (pytest + Docker Hub publish)

---

## Architecture Overview

```
immo-boussole-orchestrator/
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Settings (pydantic-settings, .env)
│   ├── auth.py                  # HTTP Basic auth middleware
│   ├── registry.py              # YAML instances.yaml read/write
│   ├── docker_manager.py        # python-on-whales abstraction layer
│   ├── notifier.py              # Webhook + SMTP notifications
│   ├── scheduler.py             # APScheduler health-check poller
│   ├── mcp_server.py            # MCP server (SSE, port 9001)
│   ├── routers/
│   │   ├── instances.py         # REST API: CRUD + actions on instances
│   │   ├── logs.py              # SSE log streaming endpoint
│   │   └── health.py            # /health endpoint
│   └── models.py                # Pydantic models (Instance, Status, ...)
├── cli/
│   └── main.py                  # Typer CLI entry point
├── templates/
│   ├── base.html                # Base layout (nav, theme toggle, auth)
│   ├── index.html               # Dashboard — instance list + status cards
│   ├── instance_detail.html     # Instance detail: logs, actions, config
│   └── partials/                # HTMX / JS partials
├── static/
│   ├── css/
│   │   └── main.css             # Vanilla CSS — dark/light tokens, layout
│   └── js/
│       └── app.js               # Theme toggle, log streaming, UI logic
├── tests/
│   ├── test_registry.py
│   ├── test_docker_manager.py
│   ├── test_api.py
│   ├── test_notifier.py
│   └── run_tests.py
├── .github/
│   └── workflows/
│       ├── ci.yml               # Run pytest on push/PR
│       └── docker-publish.yml   # Build + push Docker Hub on tag
├── Dockerfile
├── docker-compose.yml           # Local dev (bind mounts)
├── docker-compose.hub.yml       # Production (Docker Hub image)
├── .env.example
├── instances.yaml.example
├── requirements.txt
├── AGENTS.md
└── README.md
```

---

## Phase 1 — Project Scaffolding & Configuration

### [NEW] `requirements.txt`
Core dependencies:
```
fastapi
uvicorn[standard]
jinja2
python-multipart
pydantic-settings
python-dotenv
python-on-whales
typer[all]
rich
httpx
aiosmtplib
apscheduler
mcp
pyyaml
passlib[bcrypt]
pytest
pytest-asyncio
httpx         # async test client
```

### [NEW] `.env.example`
All orchestrator environment variables documented with defaults.

### [NEW] `app/config.py`
`pydantic-settings` `Settings` class loading from `.env`:
- `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`
- `ORCHESTRATOR_PORT` (default `9000`)
- `INSTANCES_FILE` (default `instances.yaml`)
- `NOTIFICATION_WEBHOOK_URL`, SMTP settings
- `MCP_PORT` (default `9001`)

---

## Phase 2 — Instance Registry (YAML)

### [NEW] `instances.yaml.example`
Example registry file with two instances (dev/prod).

### [NEW] `app/registry.py`
- `InstanceConfig` Pydantic model: `name`, `host`, `port`, `image`, `env_file`, `tls_cert`, `build_context`
- `load_registry() → list[InstanceConfig]`
- `save_registry(instances: list[InstanceConfig]) → None`
- `get_instance(name) → InstanceConfig`
- `add_instance(config) → None` (raises if name conflict)
- `remove_instance(name) → None`
- `update_instance(name, config) → None`

File is loaded on startup and re-read on every write to allow external edits.

---

## Phase 3 — Docker Manager

### [NEW] `app/docker_manager.py`
Wraps `python-on-whales` to abstract connection types:

```python
def get_docker_client(host: str, tls_cert: str | None) -> DockerClient:
    """
    host: "local" | "unix:///..." | "npipe:///..." | "ssh://user@host" | "tcp://host:port"
    """
```

Key methods (all async-compatible via `asyncio.to_thread`):
- `get_status(instance) → InstanceStatus` — container state, health, uptime, image digest
- `start(instance)`, `stop(instance)`, `restart(instance)`
- `pull_image(instance, tag=None)` — pull from Docker Hub
- `build_image(instance)` — build from local Dockerfile
- `recreate(instance)` — pull/build + stop + rm + run (rolling update)
- `remove(instance, keep_volumes=True)`
- `clone(source, target_name, target_host)` — export volumes + recreate
- `stream_logs(instance) → AsyncGenerator[str]` — tail -f via SDK
- `backup(instance)` — call Immo-Boussole `/admin/backup` endpoint
- `restore(instance, archive_path)` — call Immo-Boussole `/admin/restore` endpoint

**Connection strategy:**
| `host` value | `python-on-whales` client arg |
|---|---|
| `local` | no `host` (uses default socket) |
| `unix://...` | `host="unix://..."` |
| `npipe://...` | `host="npipe://..."` (Windows) |
| `ssh://user@host` | `host="ssh://user@host"` |
| `tcp://host:port` | `host="tcp://..."` + optional TLS |

---

## Phase 4 — FastAPI Backend (REST API)

### [NEW] `app/main.py`
- Mounts routers: `/api/instances`, `/api/logs`, `/health`
- Mounts static files and Jinja2 templates
- Registers startup/shutdown lifecycle (scheduler, MCP)
- Applies HTTP Basic auth middleware

### [NEW] `app/auth.py`
`HTTPBasic` dependency. Reads credentials from `Settings`. Returns `401` with `WWW-Authenticate` header on failure.

### [NEW] `app/routers/instances.py`

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/instances` | List all instances + live status |
| `POST` | `/api/instances` | Register a new instance |
| `GET` | `/api/instances/{name}` | Get single instance detail |
| `PUT` | `/api/instances/{name}` | Update instance config |
| `DELETE` | `/api/instances/{name}` | Remove instance (+ optional volumes) |
| `POST` | `/api/instances/{name}/start` | Start |
| `POST` | `/api/instances/{name}/stop` | Stop |
| `POST` | `/api/instances/{name}/restart` | Restart |
| `POST` | `/api/instances/{name}/update` | Pull/build + recreate |
| `POST` | `/api/instances/{name}/clone` | Clone to new instance |
| `POST` | `/api/instances/{name}/backup` | Trigger backup |
| `POST` | `/api/instances/{name}/restore` | Trigger restore |

### [NEW] `app/routers/logs.py`
`GET /api/instances/{name}/logs/stream` — Server-Sent Events (SSE) streaming logs via `python-on-whales` log tail.

### [NEW] `app/routers/health.py`
`GET /health` — Returns `{"status": "ok"}`.

### [NEW] `app/models.py`
Pydantic models:
- `InstanceConfig` (registry shape)
- `InstanceStatus` (`state`, `health`, `uptime`, `image`, `digest`, `ports`)
- `InstanceSummary` = `InstanceConfig` + `InstanceStatus`
- `CreateInstanceRequest`, `UpdateInstanceRequest`, `CloneInstanceRequest`

---

## Phase 5 — Health Poller & Notifications

### [NEW] `app/scheduler.py`
APScheduler `AsyncIOScheduler` polling every 30s:
- Calls `docker_manager.get_status()` for each instance
- Detects state transitions (running → stopped, healthy → unhealthy)
- On unexpected change → calls `notifier.notify()`

### [NEW] `app/notifier.py`
- `notify_webhook(event: NotificationEvent)` — POST JSON to `NOTIFICATION_WEBHOOK_URL`
- `notify_email(event: NotificationEvent)` — Send email via `aiosmtplib` (SMTP/TLS)
- `notify(event)` — Calls all configured channels
- `NotificationEvent`: `instance_name`, `previous_state`, `new_state`, `timestamp`, `message`

---

## Phase 6 — Web UI

### Design Principles
- Consistent with Immo-Boussole's dark glassmorphism aesthetic
- Dark / Light mode toggle (CSS variables + `data-theme` attribute on `<html>`)
- Fully responsive (mobile, tablet, desktop)
- No framework — Vanilla CSS + minimal JS
- Real-time log streaming via SSE (`EventSource` API)

### [NEW] `static/css/main.css`
CSS variables for both themes:
```css
:root[data-theme="dark"] { --bg: #0f1117; --surface: rgba(255,255,255,.05); ... }
:root[data-theme="light"] { --bg: #f4f6f9; --surface: rgba(0,0,0,.04); ... }
```
Components: navbar, instance cards (status badge, action buttons), modal (create/clone), log terminal panel, notification toast.

### [NEW] `templates/base.html`
- `<html data-theme="dark">` default
- Navbar: logo + instance count badge + theme toggle button + auth user display
- Flash messages area
- `{% block content %}{% endblock %}`

### [NEW] `templates/index.html`
Dashboard — grid of **instance cards**:
- Instance name, host, port, image tag
- Status badge: 🟢 Running / 🔴 Stopped / 🟡 Unhealthy / ⚪ Unknown
- Uptime counter
- Quick action buttons: Start, Stop, Restart, Update, Logs, Delete
- "Add Instance" floating button → modal form

### [NEW] `templates/instance_detail.html`
- Full instance config display + inline edit
- Action bar (all operations)
- **Live log terminal** (SSE stream, monospace, auto-scroll)
- Backup / Restore section

### [NEW] `static/js/app.js`
- `ThemeManager`: toggle + localStorage persistence
- `LogStream`: `EventSource` connection, line rendering, auto-scroll, stop/start
- `InstanceActions`: fetch wrappers + toast notifications for API calls
- Status auto-refresh (polling `/api/instances` every 15s)

---

## Phase 7 — CLI (`orchestrator`)

### [NEW] `cli/main.py`
Typer app with Rich-powered output:

```
orchestrator list
orchestrator add [OPTIONS]
orchestrator start <name>
orchestrator stop <name>
orchestrator restart <name>
orchestrator update <name> [--tag TAG]
orchestrator logs <name> [--follow] [--tail N]
orchestrator clone <source> <target>
orchestrator remove <name> [--keep-volumes]
orchestrator backup <name>
orchestrator restore <name> --file FILE
orchestrator ui               # open web UI in browser
orchestrator status <name>    # single instance status
```

All commands call the local REST API (default `http://localhost:9000`) so CLI and UI stay in sync. API base URL configurable via `--api-url` global option or `ORCHESTRATOR_API_URL` env var.

---

## Phase 8 — MCP Server

### [NEW] `app/mcp_server.py`
SSE-based MCP server on port `9001` using the `mcp` library.

Exposed tools:

| Tool | Description |
|---|---|
| `list_instances` | Returns all instances and their current status |
| `get_instance_status` | Get status of a specific instance |
| `start_instance` | Start a stopped instance |
| `stop_instance` | Stop a running instance |
| `restart_instance` | Restart an instance |
| `update_instance` | Pull latest image and recreate |
| `create_instance` | Register and start a new instance |
| `delete_instance` | Remove an instance |
| `get_instance_logs` | Return last N lines of logs |
| `backup_instance` | Trigger a backup |

---

## Phase 9 — Docker & CI/CD

### [NEW] `Dockerfile`
- Multi-stage build: `python:3.12-slim`
- Installs dependencies, copies app
- Exposes ports `9000` (web) and `9001` (MCP)
- Mounts `/var/run/docker.sock` for local Docker access
- Entrypoint: `uvicorn app.main:app --host 0.0.0.0 --port 9000`

### [NEW] `docker-compose.yml` (local dev)
- Bind mounts: `./app`, `./templates`, `./static`
- Mounts Docker socket
- Hot-reload enabled (`--reload`)

### [NEW] `docker-compose.hub.yml` (production)
- Uses `wikijm/immo-boussole-orchestrator:latest` from Docker Hub
- Named volume for `instances.yaml` persistence
- Docker socket mount

### [NEW] `.github/workflows/ci.yml`
- Triggers on: push to `main`, pull requests
- Steps: checkout → Python 3.12 → `pip install` → `pytest --ci`

### [NEW] `.github/workflows/docker-publish.yml`
- Triggers on: push tags `v*`
- Steps: checkout → Docker Buildx → login Docker Hub → build + push `wikijm/immo-boussole-orchestrator:{tag}` + `latest`

---

## Phase 10 — Project Files & Docs

### [NEW] `AGENTS.md`
Same rules as Immo-Boussole: responsive design, commit conventions, Chrome DevTools QA.

### [NEW] `tests/run_tests.py`
Test runner (mirrors Immo-Boussole pattern), supporting `--ci` flag.

### [NEW] `tests/test_registry.py`
Unit tests: load/save/add/remove/update instances in the YAML registry.

### [NEW] `tests/test_docker_manager.py`
Unit tests: mock `python-on-whales` — verify client construction per host type.

### [NEW] `tests/test_api.py`
Integration tests: FastAPI `TestClient` — verify all REST endpoints, auth rejection.

### [NEW] `tests/test_notifier.py`
Unit tests: mock `httpx` and `aiosmtplib` — verify webhook payload and SMTP call.

---

## Implementation Order

```
Phase 1  →  Scaffolding & Config
Phase 2  →  Registry (YAML)
Phase 3  →  Docker Manager
Phase 4  →  FastAPI REST API
Phase 5  →  Health Poller & Notifier
Phase 6  →  Web UI (HTML/CSS/JS)
Phase 7  →  CLI (Typer)
Phase 8  →  MCP Server
Phase 9  →  Dockerfile & CI/CD
Phase 10 →  Tests & Documentation
```

---

## Verification Plan

### Automated Tests
```bash
python tests/run_tests.py --ci
```
- Registry CRUD round-trips
- Docker manager client construction (mocked)
- All REST endpoints (status codes, payloads, auth)
- Notifier webhook/email dispatch (mocked)

### Manual Verification (Chrome DevTools MCP)
- Screenshot at 375×667 (mobile), 768×1024 (tablet), 1280×800 (desktop)
- `list_console_messages` → 0 JS errors
- `list_network_requests` → 0 4xx/5xx errors
- `lighthouse_audit` on `/` and `/instances/{name}`

### Functional Verification
- Create a `dev` instance → verify container appears in `docker ps`
- Start / stop / restart → status badges update in real time
- Trigger update → new image pulled, container recreated
- Clone `dev` → `staging` instance appears with correct config
- MCP: query `list_instances` from Claude Desktop → correct response
- Notification: stop a container manually → webhook fires within 30s

---

> **Next step**: Approve this plan and run `/goal` to execute all phases autonomously.
