"""
Server-Sent Events (SSE) log streaming router.

Endpoint: GET /api/instances/{name}/logs/stream
Streams live docker logs to the client as SSE events.

Endpoint: GET /api/instances/{name}/logs
Returns last N lines of logs as JSON.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app import docker_manager
from app.auth import require_auth
from app.registry import get_instance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/instances", tags=["logs"])


@router.get("/{name}/logs")
async def get_logs(
    name: str,
    tail: int = Query(100, ge=1, le=5000, description="Number of log lines to return"),
    _user: str = Depends(require_auth),
) -> dict:
    """Return the last *tail* lines of container logs as JSON."""
    try:
        inst = get_instance(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Instance '{name}' not found.")
    lines = await docker_manager.get_logs(inst, tail=tail)
    return {"instance": name, "lines": lines}


@router.get("/{name}/logs/stream")
async def stream_logs(
    name: str,
    _user: str = Depends(require_auth),
) -> StreamingResponse:
    """Stream live Docker logs as Server-Sent Events.

    The client connects via EventSource and receives log lines as ``data:`` events.
    """
    try:
        inst = get_instance(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Instance '{name}' not found.")

    async def _sse_generator():
        try:
            async for line in docker_manager.stream_logs(inst):
                # SSE format: "data: <line>\n\n"
                safe = line.replace("\n", " ")
                yield f"data: {safe}\n\n"
                await asyncio.sleep(0)  # yield control to event loop
        except asyncio.CancelledError:
            logger.debug("Log stream cancelled for instance %s", name)
        except Exception as exc:
            yield f"data: [stream error] {exc}\n\n"

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
