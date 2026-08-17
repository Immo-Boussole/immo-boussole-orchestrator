"""
REST API router for instance CRUD and lifecycle operations.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app import docker_manager
from app.auth import require_auth
from app.models import (
    CloneInstanceRequest,
    CreateInstanceRequest,
    InstanceConfigSchema,
    InstanceStatusSchema,
    InstanceSummary,
    MessageResponse,
    RestoreRequest,
    UpdateInstanceRequest,
    UpdateTagRequest,
)
from app.registry import (
    InstanceConfig,
    add_instance,
    get_instance,
    load_registry,
    remove_instance,
    update_instance,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/instances", tags=["instances"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _build_summary(inst: InstanceConfig) -> InstanceSummary:
    status_obj = await docker_manager.get_status(inst)
    return InstanceSummary(
        config=InstanceConfigSchema(**inst.model_dump()),
        status=InstanceStatusSchema(**status_obj.to_dict()),
    )


def _get_or_404(name: str) -> InstanceConfig:
    try:
        return get_instance(name)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{name}' not found.",
        )


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[InstanceSummary])
async def list_instances(
    _user: str = Depends(require_auth),
) -> list[InstanceSummary]:
    """List all registered instances with their live Docker status."""
    instances = load_registry()
    import asyncio
    summaries = await asyncio.gather(*[_build_summary(i) for i in instances])
    return list(summaries)


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("", response_model=InstanceSummary, status_code=status.HTTP_201_CREATED)
async def create_instance(
    body: CreateInstanceRequest,
    _user: str = Depends(require_auth),
) -> InstanceSummary:
    """Register a new instance and optionally start it."""
    cfg = InstanceConfig(
        name=body.name,
        host=body.host,
        port=body.port,
        image=body.image,
        env_file=body.env_file,
        build_context=body.build_context,
        tls_cert=body.tls_cert,
        description=body.description,
    )
    try:
        add_instance(cfg)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    if body.start_after_create:
        try:
            await docker_manager.update(cfg)
        except Exception as exc:
            logger.warning("Could not auto-start instance %s: %s", cfg.name, exc)

    return await _build_summary(cfg)


# ── Read ──────────────────────────────────────────────────────────────────────

@router.get("/{name}", response_model=InstanceSummary)
async def get_instance_detail(
    name: str,
    _user: str = Depends(require_auth),
) -> InstanceSummary:
    """Get config and live status for a single instance."""
    inst = _get_or_404(name)
    return await _build_summary(inst)


# ── Update config ─────────────────────────────────────────────────────────────

@router.put("/{name}", response_model=InstanceSummary)
async def update_instance_config(
    name: str,
    body: UpdateInstanceRequest,
    _user: str = Depends(require_auth),
) -> InstanceSummary:
    """Update an instance's configuration (does not restart the container)."""
    inst = _get_or_404(name)
    updated_data = inst.model_dump()
    for field, value in body.model_dump(exclude_none=True).items():
        updated_data[field] = value
    updated = InstanceConfig(**updated_data)
    update_instance(name, updated)
    return await _build_summary(updated)


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{name}", response_model=MessageResponse)
async def delete_instance(
    name: str,
    keep_volumes: bool = Query(True, description="Keep Docker volumes after removal"),
    _user: str = Depends(require_auth),
) -> MessageResponse:
    """Remove an instance's container and unregister it from the registry."""
    inst = _get_or_404(name)
    try:
        await docker_manager.remove(inst, keep_volumes=keep_volumes)
    except Exception as exc:
        logger.warning("Error removing container for %s: %s", name, exc)
    remove_instance(name)
    return MessageResponse(
        message=f"Instance '{name}' removed.",
        detail={"keep_volumes": keep_volumes},
    )


# ── Lifecycle actions ─────────────────────────────────────────────────────────

@router.post("/{name}/start", response_model=MessageResponse)
async def start_instance(
    name: str,
    _user: str = Depends(require_auth),
) -> MessageResponse:
    inst = _get_or_404(name)
    try:
        await docker_manager.start(inst)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return MessageResponse(message=f"Instance '{name}' started.")


@router.post("/{name}/stop", response_model=MessageResponse)
async def stop_instance(
    name: str,
    _user: str = Depends(require_auth),
) -> MessageResponse:
    inst = _get_or_404(name)
    try:
        await docker_manager.stop(inst)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return MessageResponse(message=f"Instance '{name}' stopped.")


@router.post("/{name}/restart", response_model=MessageResponse)
async def restart_instance(
    name: str,
    _user: str = Depends(require_auth),
) -> MessageResponse:
    inst = _get_or_404(name)
    try:
        await docker_manager.restart(inst)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return MessageResponse(message=f"Instance '{name}' restarted.")


@router.post("/{name}/update", response_model=MessageResponse)
async def update_instance_image(
    name: str,
    body: UpdateTagRequest | None = None,
    _user: str = Depends(require_auth),
) -> MessageResponse:
    """Pull latest image (or specified tag) and recreate the container."""
    inst = _get_or_404(name)
    tag = body.tag if body else None
    try:
        await docker_manager.update(inst, tag=tag)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return MessageResponse(
        message=f"Instance '{name}' updated.",
        detail={"tag": tag},
    )


@router.post("/{name}/clone", response_model=InstanceSummary)
async def clone_instance(
    name: str,
    body: CloneInstanceRequest,
    _user: str = Depends(require_auth),
) -> InstanceSummary:
    """Clone this instance's config to a new instance."""
    inst = _get_or_404(name)
    try:
        new_inst = await docker_manager.clone(
            source=inst,
            target_name=body.target_name,
            target_port=body.target_port,
            target_host=body.target_host,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return await _build_summary(new_inst)


@router.post("/{name}/backup", response_model=MessageResponse)
async def backup_instance(
    name: str,
    _user: str = Depends(require_auth),
) -> MessageResponse:
    """Trigger a backup via the Immo-Boussole API."""
    inst = _get_or_404(name)
    try:
        result = await docker_manager.backup(inst)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return MessageResponse(message=f"Backup triggered for '{name}'.", detail=result)


@router.post("/{name}/restore", response_model=MessageResponse)
async def restore_instance(
    name: str,
    body: RestoreRequest,
    _user: str = Depends(require_auth),
) -> MessageResponse:
    """Trigger a restore via the Immo-Boussole API."""
    inst = _get_or_404(name)
    try:
        result = await docker_manager.restore(inst, body.archive_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return MessageResponse(message=f"Restore triggered for '{name}'.", detail=result)
