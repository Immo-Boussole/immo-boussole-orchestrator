"""
Instance registry — YAML-backed persistence layer.

The registry file (instances.yaml) is read on every access and written
atomically so that external edits (e.g. hand-editing instances.yaml) are
always picked up without a server restart.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML as _YAML
from pydantic import BaseModel, field_validator

from app.config import get_settings

_yaml = _YAML()
_yaml.default_flow_style = False

# ── Thread-safety lock for file writes ───────────────────────────────────────
_lock = threading.Lock()


# ── Data model ───────────────────────────────────────────────────────────────

class InstanceConfig(BaseModel):
    """Represents one registered Immo-Boussole instance."""

    name: str
    """Unique identifier for this instance (used as key everywhere)."""

    host: str = "local"
    """Docker host connection string.

    Accepted values:
    - ``"local"``                           → default local Docker socket
    - ``"unix:///var/run/docker.sock"``     → explicit Unix socket
    - ``"npipe:////./pipe/docker_engine"``  → Windows named pipe
    - ``"ssh://user@hostname"``             → remote via SSH
    - ``"tcp://hostname:2376"``             → remote TCP (add tls_cert for TLS)
    """

    port: int = 8000
    """Host port exposed for the Immo-Boussole web UI."""

    image: str | None = "wikijm/immo-boussole:latest"
    """Docker image to pull. Set to ``None`` to build from *build_context*."""

    env_file: str | None = None
    """Path to a .env file injected into the container."""

    build_context: str | None = None
    """Directory containing a Dockerfile, used when *image* is ``None``."""

    tls_cert: str | None = None
    """Path to TLS client cert bundle for ``tcp://`` hosts."""

    description: str = ""
    """Human-readable description shown in the web UI."""

    @field_validator("name")
    @classmethod
    def name_must_be_slug(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "Instance name must only contain letters, digits, hyphens, and underscores."
            )
        return v.lower()


# ── Registry helpers ──────────────────────────────────────────────────────────

def _registry_path() -> Path:
    return get_settings().instances_path


def load_registry() -> list[InstanceConfig]:
    """Load and return all instances from the YAML registry file."""
    path = _registry_path()
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        data: dict[str, Any] = _yaml.load(fh) or {}
    raw_list: list[dict] = data.get("instances", []) or []
    return [InstanceConfig(**item) for item in raw_list]


def save_registry(instances: list[InstanceConfig]) -> None:
    """Persist the instance list to the YAML registry file (atomic write)."""
    path = _registry_path()
    payload = {
        "instances": [inst.model_dump(exclude_none=False) for inst in instances]
    }
    tmp = path.with_suffix(".yaml.tmp")
    with _lock:
        with tmp.open("w", encoding="utf-8") as fh:
            _yaml.dump(payload, fh)
        tmp.replace(path)


def get_instance(name: str) -> InstanceConfig:
    """Return an instance by name, raising ``KeyError`` if not found."""
    name = name.lower()
    for inst in load_registry():
        if inst.name == name:
            return inst
    raise KeyError(f"Instance '{name}' not found in registry.")


def add_instance(config: InstanceConfig) -> None:
    """Add a new instance to the registry.

    Raises:
        ValueError: If an instance with the same name already exists.
    """
    instances = load_registry()
    if any(i.name == config.name for i in instances):
        raise ValueError(f"Instance '{config.name}' already exists.")
    instances.append(config)
    save_registry(instances)


def remove_instance(name: str) -> None:
    """Remove an instance from the registry by name.

    Raises:
        KeyError: If the instance is not found.
    """
    name = name.lower()
    instances = load_registry()
    new_list = [i for i in instances if i.name != name]
    if len(new_list) == len(instances):
        raise KeyError(f"Instance '{name}' not found in registry.")
    save_registry(new_list)


def update_instance(name: str, updated: InstanceConfig) -> None:
    """Replace an existing instance config in the registry.

    Raises:
        KeyError: If the instance is not found.
    """
    name = name.lower()
    instances = load_registry()
    for i, inst in enumerate(instances):
        if inst.name == name:
            instances[i] = updated
            save_registry(instances)
            return
    raise KeyError(f"Instance '{name}' not found in registry.")
