# 🎛️ Immo-Boussole Orchestrator

> **CLI & web orchestrator** to deploy, manage, monitor, and update multiple [Immo-Boussole](https://github.com/Immo-Boussole/immo-boussole) instances on local or remote Docker hosts — from any OS (Windows, Linux, macOS).

---

## ✨ Overview

**Immo-Boussole Orchestrator** is the control plane for your Immo-Boussole fleet. Whether you run a development instance on your laptop, a staging environment on a remote server, or multiple production deployments, this tool gives you a single pane of glass to manage them all.

It communicates directly with Docker daemons — locally via Unix/TCP socket, or remotely via SSH tunnel or TLS — and is itself fully containerizable.

---

## 🚀 Key Features

- **Multi-instance management** — Create, start, stop, restart, update, and delete Immo-Boussole instances
- **Multi-host support** — Connect to local Docker daemons or remote hosts (SSH, TCP/TLS)
- **Real-time monitoring** — Live health status, uptime, and log streaming per instance
- **Backup & Restore** — Trigger backups and restores via the Immo-Boussole API
- **Instance cloning** — Duplicate a full instance (config + data) in one command
- **Image flexibility** — Use Docker Hub official images or build from local sources, per instance
- **Web UI** — Browser-based dashboard with dark/light theme toggle
- **CLI** — Full-featured command-line interface (`orchestrator` command)
- **Notifications** — Webhook (generic POST JSON) and Email (SMTP) alerts on instance state changes
- **MCP Server** — Model Context Protocol server to manage instances via Claude Desktop or any LLM tool
- **Auth** — HTTP Basic authentication for the web interface
- **CI/CD** — GitHub Actions pipeline: tests + Docker Hub image publication

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **CLI** | Typer |
| **Docker Control** | `python-on-whales` (Docker SDK) |
| **Config Storage** | YAML (`instances.yaml`) |
| **Frontend** | HTML5, Vanilla CSS, Jinja2 templates |
| **Notifications** | HTTPX (webhook), `aiosmtplib` (SMTP) |
| **MCP** | `mcp` library (Model Context Protocol) |
| **Containerization** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions |

---

## ⚡ Quick Start

### 1. Using Docker (Recommended)

```bash
# Pull and run the orchestrator
docker compose -f docker-compose.hub.yml up -d
```

The web UI is accessible at **[http://localhost:9000](http://localhost:9000)**.

### 2. Local Python Development

```bash
# 1. Clone the repository
git clone https://github.com/Immo-Boussole/immo-boussole-orchestrator.git
cd immo-boussole-orchestrator

# 2. Setup virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env with your settings

# 5. Run the web server
python -m uvicorn app.main:app --reload --port 9000

# Or use the CLI
python -m orchestrator --help
```

---

## 🖥️ CLI Usage

```bash
# List all registered instances
orchestrator list

# Add a new instance
orchestrator add --name prod --host ssh://user@myserver --port 8000 --image wikijm/immo-boussole:latest

# Start / stop / restart
orchestrator start prod
orchestrator stop prod
orchestrator restart prod

# Update to a new image version
orchestrator update prod --tag 1.2.3

# View live logs
orchestrator logs prod --follow

# Clone an instance
orchestrator clone prod staging

# Remove an instance (keep volumes)
orchestrator remove prod --keep-volumes

# Trigger a backup
orchestrator backup prod

# Open the web UI in the browser
orchestrator ui
```

---

## ⚙️ Configuration

### `.env` — Orchestrator settings

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | *(required)* | Session signing key |
| `ADMIN_USERNAME` | `admin` | Web UI username |
| `ADMIN_PASSWORD` | *(required)* | Web UI password |
| `ORCHESTRATOR_PORT` | `9000` | Web UI listening port |
| `INSTANCES_FILE` | `instances.yaml` | Path to instances registry |
| `NOTIFICATION_WEBHOOK_URL` | *(optional)* | Webhook URL for alerts |
| `SMTP_HOST` | *(optional)* | SMTP server for email notifications |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USERNAME` | *(optional)* | SMTP credentials |
| `SMTP_PASSWORD` | *(optional)* | SMTP credentials |
| `SMTP_FROM` | *(optional)* | Sender email address |
| `SMTP_TO` | *(optional)* | Recipient email address(es) |

### `instances.yaml` — Instances registry

```yaml
instances:
  - name: dev
    host: local          # or ssh://user@host, tcp://host:2376
    port: 8000
    image: wikijm/immo-boussole:latest
    env_file: ./envs/dev.env
    tls_cert: null       # path to TLS cert for TCP hosts

  - name: prod
    host: ssh://deploy@myserver.com
    port: 8100
    image: wikijm/immo-boussole:1.2.3
    env_file: ./envs/prod.env
```

---

## 🔌 MCP Server

The orchestrator exposes an MCP server on port `9001` for integration with Claude Desktop and other LLM tools:

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "immo-boussole-orchestrator": {
      "url": "http://localhost:9001/sse"
    }
  }
}
```

Available MCP tools: `list_instances`, `start_instance`, `stop_instance`, `restart_instance`, `get_instance_status`, `get_instance_logs`, `update_instance`, `create_instance`, `delete_instance`, `backup_instance`.

---

## 🧪 Testing

```bash
# Run all tests
python tests/run_tests.py

# CI mode
python tests/run_tests.py --ci
```

---

## 🐳 Docker Hosts — Connectivity

| Target | Connection string | Notes |
|---|---|---|
| Local (Linux/macOS) | `local` or `unix:///var/run/docker.sock` | Default |
| Local (Windows) | `npipe:////./pipe/docker_engine` | Docker Desktop |
| Remote SSH | `ssh://user@hostname` | Key-based auth recommended |
| Remote TCP/TLS | `tcp://hostname:2376` | Requires TLS certs |

---

## 📄 License

This project is open-source. See [LICENSE](LICENSE) for details.

---

*Part of the [Immo-Boussole](https://github.com/Immo-Boussole) organization.*
