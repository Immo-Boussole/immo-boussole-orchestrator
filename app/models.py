"""
Pydantic models for the Orchestrator REST API.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ── Instance registry shape ───────────────────────────────────────────────────

class InstanceConfigSchema(BaseModel):
    """Mirrors registry.InstanceConfig — used in API request/response bodies."""

    name: str
    host: str = "local"
    port: int = 8000
    image: str | None = "wikijm/immo-boussole:latest"
    env_file: str | None = None
    build_context: str | None = None
    tls_cert: str | None = None
    description: str = ""


# ── Status ────────────────────────────────────────────────────────────────────

class InstanceStatusSchema(BaseModel):
    state: str
    health: str
    uptime_seconds: int | None = None
    image: str = ""
    image_digest: str = ""
    ports: list[str] = Field(default_factory=list)
    error: str | None = None


class InstanceSummary(BaseModel):
    """Combined config + live status — used in list and detail endpoints."""

    config: InstanceConfigSchema
    status: InstanceStatusSchema


# ── Request bodies ────────────────────────────────────────────────────────────

class CreateInstanceRequest(BaseModel):
    name: str
    host: str = "local"
    port: int = 8000
    image: str | None = "wikijm/immo-boussole:latest"
    env_file: str | None = None
    build_context: str | None = None
    tls_cert: str | None = None
    description: str = ""
    start_after_create: bool = False
    """If True, immediately recreate (run) the container after registration."""


class UpdateInstanceRequest(BaseModel):
    host: str | None = None
    port: int | None = None
    image: str | None = None
    env_file: str | None = None
    build_context: str | None = None
    tls_cert: str | None = None
    description: str | None = None


class CloneInstanceRequest(BaseModel):
    target_name: str
    target_port: int
    target_host: str = "local"


class UpdateTagRequest(BaseModel):
    tag: str | None = None
    """Optional new image tag. If None, re-pulls the current tag."""


class RestoreRequest(BaseModel):
    archive_path: str


# ── Generic response ──────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    detail: Any | None = None
