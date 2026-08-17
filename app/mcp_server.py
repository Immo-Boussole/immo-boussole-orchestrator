"""
MCP Server — exposes orchestration tools to Claude Desktop and other LLM tools.

Uses FastMCP (the same library as immo-boussole).
Start independently: python -m app.mcp_server
Or served alongside the FastAPI app on MCP_PORT (default 9001).

Tools exposed:
  list_instances        – All registered instances + live status
  get_instance_status   – Status of a single instance
  start_instance        – Start a stopped container
  stop_instance         – Stop a running container
  restart_instance      – Restart a container
  update_instance       – Pull latest image and recreate
  create_instance       – Register and start a new instance
  delete_instance       – Remove an instance
  get_instance_logs     – Last N lines of logs
  backup_instance       – Trigger Immo-Boussole backup
"""
from __future__ import annotations

import json
import logging

from fastmcp import FastMCP

from app import docker_manager
from app.config import get_settings
from app.registry import (
    InstanceConfig,
    add_instance,
    get_instance,
    load_registry,
    remove_instance,
)

logger = logging.getLogger(__name__)

# ── FastMCP server instance ───────────────────────────────────────────────────
mcp = FastMCP("immo-boussole-orchestrator")


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_instances() -> str:
    """List all registered Immo-Boussole instances with their live Docker status."""
    instances = load_registry()
    result = []
    for inst in instances:
        status = await docker_manager.get_status(inst)
        result.append({**inst.model_dump(), "status": status.to_dict()})
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_instance_status(name: str) -> str:
    """Get the live Docker status of a specific Immo-Boussole instance.

    Args:
        name: Instance name
    """
    try:
        inst = get_instance(name)
    except KeyError:
        return json.dumps({"error": f"Instance '{name}' not found."})
    status = await docker_manager.get_status(inst)
    return json.dumps({"instance": inst.name, "status": status.to_dict()}, indent=2)


@mcp.tool()
async def start_instance(name: str) -> str:
    """Start a stopped Immo-Boussole instance container.

    Args:
        name: Instance name
    """
    try:
        inst = get_instance(name)
        await docker_manager.start(inst)
        return f"Instance '{name}' started successfully."
    except KeyError:
        return f"Error: Instance '{name}' not found."
    except Exception as exc:
        return f"Error starting '{name}': {exc}"


@mcp.tool()
async def stop_instance(name: str) -> str:
    """Stop a running Immo-Boussole instance container.

    Args:
        name: Instance name
    """
    try:
        inst = get_instance(name)
        await docker_manager.stop(inst)
        return f"Instance '{name}' stopped successfully."
    except KeyError:
        return f"Error: Instance '{name}' not found."
    except Exception as exc:
        return f"Error stopping '{name}': {exc}"


@mcp.tool()
async def restart_instance(name: str) -> str:
    """Restart an Immo-Boussole instance container.

    Args:
        name: Instance name
    """
    try:
        inst = get_instance(name)
        await docker_manager.restart(inst)
        return f"Instance '{name}' restarted successfully."
    except KeyError:
        return f"Error: Instance '{name}' not found."
    except Exception as exc:
        return f"Error restarting '{name}': {exc}"


@mcp.tool()
async def update_instance(name: str, tag: str = "") -> str:
    """Pull the latest image (or a specific tag) and recreate the container.

    Args:
        name: Instance name
        tag: Optional image tag (e.g. '1.2.3'). Leave empty for 'latest'.
    """
    try:
        inst = get_instance(name)
        await docker_manager.update(inst, tag=tag or None)
        return f"Instance '{name}' updated (tag={tag or 'latest'})."
    except KeyError:
        return f"Error: Instance '{name}' not found."
    except Exception as exc:
        return f"Error updating '{name}': {exc}"


@mcp.tool()
async def create_instance(
    name: str,
    host: str = "local",
    port: int = 8000,
    image: str = "wikijm/immo-boussole:latest",
    description: str = "",
) -> str:
    """Register a new Immo-Boussole instance in the orchestrator.

    Args:
        name: Unique instance name (letters, digits, hyphens, underscores)
        host: Docker host connection string (e.g. 'local', 'ssh://user@host')
        port: Host port for the Immo-Boussole web UI
        image: Docker image reference
        description: Human-readable description
    """
    try:
        cfg = InstanceConfig(
            name=name, host=host, port=port,
            image=image, description=description,
        )
        add_instance(cfg)
        return f"Instance '{cfg.name}' registered successfully."
    except Exception as exc:
        return f"Error creating instance: {exc}"


@mcp.tool()
async def delete_instance(name: str, keep_volumes: bool = True) -> str:
    """Remove an Immo-Boussole instance (keeps volumes by default).

    Args:
        name: Instance name
        keep_volumes: If False, also delete Docker volumes (destructive!)
    """
    try:
        inst = get_instance(name)
        await docker_manager.remove(inst, keep_volumes=keep_volumes)
        remove_instance(inst.name)
        return f"Instance '{name}' deleted (keep_volumes={keep_volumes})."
    except KeyError:
        return f"Error: Instance '{name}' not found."
    except Exception as exc:
        return f"Error deleting '{name}': {exc}"


@mcp.tool()
async def get_instance_logs(name: str, tail: int = 50) -> str:
    """Return the last N lines of container logs for an instance.

    Args:
        name: Instance name
        tail: Number of log lines to return (default: 50)
    """
    try:
        inst = get_instance(name)
        lines = await docker_manager.get_logs(inst, tail=tail)
        return "\n".join(lines)
    except KeyError:
        return f"Error: Instance '{name}' not found."
    except Exception as exc:
        return f"Error fetching logs for '{name}': {exc}"


@mcp.tool()
async def backup_instance(name: str) -> str:
    """Trigger an Immo-Boussole backup via its REST API.

    Args:
        name: Instance name
    """
    try:
        inst = get_instance(name)
        result = await docker_manager.backup(inst)
        return json.dumps(result, indent=2)
    except KeyError:
        return f"Error: Instance '{name}' not found."
    except Exception as exc:
        return f"Error backing up '{name}': {exc}"


# ── Entry point (standalone SSE server) ───────────────────────────────────────

if __name__ == "__main__":
    settings = get_settings()
    mcp.run(transport="sse", host="0.0.0.0", port=settings.mcp_port)
