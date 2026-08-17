"""
Docker Manager — abstraction layer over python-on-whales.

All blocking docker SDK calls are wrapped in ``asyncio.to_thread()`` so they
can be safely awaited from FastAPI async route handlers without blocking the
event loop.

Connection strategy
───────────────────
host value                      python-on-whales client
──────────────────────────────  ──────────────────────────────────────────────
"local"                         DockerClient()              (default socket)
"unix:///var/run/docker.sock"   DockerClient(host=...)      (explicit socket)
"npipe:////./pipe/docker_engine" DockerClient(host=...)     (Windows)
"ssh://user@hostname"           DockerClient(host=...)      (SSH tunnel)
"tcp://hostname:2376"           DockerClient(host=..., tls=TLSConfig(...))
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

from python_on_whales import DockerClient, DockerException
from python_on_whales.components.container.cli_wrapper import Container

from app.registry import InstanceConfig

logger = logging.getLogger(__name__)


# ── Client factory ────────────────────────────────────────────────────────────

def _make_client(instance: InstanceConfig) -> DockerClient:
    """Build a ``DockerClient`` for the given instance's Docker host."""
    host = instance.host.strip()

    if host in ("local", ""):
        return DockerClient()

    if host.startswith("tcp://") and instance.tls_cert:
        from python_on_whales.utils import DockerException  # noqa: F811
        # TLSConfig path: tls_cert should point to a directory containing
        # ca.pem, cert.pem, key.pem (Docker convention).
        from python_on_whales import DockerClient as DC
        return DC(host=host, tls=True)

    # unix://, npipe://, ssh://, tcp:// (no TLS)
    return DockerClient(host=host)


# ── Container name convention ─────────────────────────────────────────────────

def _container_name(instance: InstanceConfig) -> str:
    """Return the expected container name for an Immo-Boussole instance."""
    return f"immo-boussole-{instance.name}-app"


def _browserless_name(instance: InstanceConfig) -> str:
    return f"browserless-{instance.name}"


# ── Status dataclass ──────────────────────────────────────────────────────────

class InstanceStatus:
    """Live status snapshot for one Immo-Boussole instance."""

    __slots__ = (
        "state", "health", "uptime_seconds", "image", "image_digest",
        "ports", "error",
    )

    def __init__(
        self,
        state: str = "unknown",
        health: str = "unknown",
        uptime_seconds: int | None = None,
        image: str = "",
        image_digest: str = "",
        ports: list[str] | None = None,
        error: str | None = None,
    ) -> None:
        self.state = state
        self.health = health
        self.uptime_seconds = uptime_seconds
        self.image = image
        self.image_digest = image_digest
        self.ports = ports or []
        self.error = error

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "health": self.health,
            "uptime_seconds": self.uptime_seconds,
            "image": self.image,
            "image_digest": self.image_digest,
            "ports": self.ports,
            "error": self.error,
        }


# ── Core operations (sync, called via asyncio.to_thread) ─────────────────────

def _get_status_sync(instance: InstanceConfig) -> InstanceStatus:
    """Synchronous status fetch (run in thread pool)."""
    try:
        client = _make_client(instance)
        name = _container_name(instance)
        containers = client.container.list(all=True, filters={"name": name})
        if not containers:
            return InstanceStatus(state="absent", health="none")

        c: Container = containers[0]
        state = c.state.status or "unknown"
        health = "none"
        if c.state.health:
            health = c.state.health.status or "none"

        uptime: int | None = None
        if c.state.started_at:
            try:
                started = c.state.started_at
                if isinstance(started, str):
                    # python-on-whales may return a string on some versions
                    from dateutil import parser as dp
                    started = dp.parse(started)
                now = datetime.now(timezone.utc)
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                uptime = int((now - started).total_seconds())
            except Exception:
                uptime = None

        image_name = ""
        image_digest = ""
        try:
            image_name = c.image or ""
            if hasattr(c, "image_id"):
                image_digest = c.image_id or ""
        except Exception:
            pass

        ports: list[str] = []
        try:
            if c.network_settings and c.network_settings.ports:
                for container_port, host_bindings in c.network_settings.ports.items():
                    if host_bindings:
                        for binding in host_bindings:
                            ports.append(f"{binding['HostPort']}→{container_port}")
        except Exception:
            pass

        return InstanceStatus(
            state=state,
            health=health,
            uptime_seconds=uptime,
            image=image_name,
            image_digest=image_digest,
            ports=ports,
        )
    except DockerException as exc:
        logger.warning("Docker error fetching status for %s: %s", instance.name, exc)
        return InstanceStatus(state="error", health="none", error=str(exc))
    except Exception as exc:
        logger.warning("Unexpected error fetching status for %s: %s", instance.name, exc)
        return InstanceStatus(state="error", health="none", error=str(exc))


def _start_sync(instance: InstanceConfig) -> None:
    client = _make_client(instance)
    client.container.start(_container_name(instance))


def _stop_sync(instance: InstanceConfig) -> None:
    client = _make_client(instance)
    client.container.stop(_container_name(instance))


def _restart_sync(instance: InstanceConfig) -> None:
    client = _make_client(instance)
    client.container.restart(_container_name(instance))


def _pull_image_sync(instance: InstanceConfig, tag: str | None = None) -> None:
    """Pull (or re-pull) the Docker image for this instance."""
    client = _make_client(instance)
    image_ref = instance.image or "wikijm/immo-boussole:latest"
    if tag:
        # Replace tag portion
        base = image_ref.rsplit(":", 1)[0]
        image_ref = f"{base}:{tag}"
    client.image.pull(image_ref)
    logger.info("Pulled image %s for instance %s", image_ref, instance.name)


def _build_image_sync(instance: InstanceConfig) -> None:
    """Build Docker image from local build_context."""
    if not instance.build_context:
        raise ValueError(f"Instance '{instance.name}' has no build_context configured.")
    client = _make_client(instance)
    tag = f"immo-boussole-{instance.name}:local"
    client.buildx.build(
        context_path=instance.build_context,
        tags=[tag],
        load=True,
    )
    logger.info("Built image %s for instance %s", tag, instance.name)


def _remove_container_sync(
    instance: InstanceConfig, keep_volumes: bool = True
) -> None:
    """Remove the container (optionally keep volumes)."""
    client = _make_client(instance)
    name = _container_name(instance)
    try:
        client.container.remove(name, force=True, volumes=not keep_volumes)
        logger.info(
            "Removed container %s (keep_volumes=%s)", name, keep_volumes
        )
    except DockerException as exc:
        if "No such container" in str(exc):
            logger.debug("Container %s already absent, nothing to remove.", name)
        else:
            raise


def _recreate_sync(instance: InstanceConfig, tag: str | None = None) -> None:
    """Pull/build image, stop and remove old container, run new one."""
    client = _make_client(instance)

    # Determine image reference
    if instance.image:
        image_ref = instance.image
        if tag:
            base = image_ref.rsplit(":", 1)[0]
            image_ref = f"{base}:{tag}"
        client.image.pull(image_ref)
    elif instance.build_context:
        _build_image_sync(instance)
        image_ref = f"immo-boussole-{instance.name}:local"
    else:
        raise ValueError(
            f"Instance '{instance.name}' has neither image nor build_context."
        )

    # Stop & remove old container
    _remove_container_sync(instance, keep_volumes=True)

    # Resolve env file
    env_file_arg = instance.env_file if instance.env_file else None

    # Run new container
    container_name = _container_name(instance)
    run_kwargs: dict = dict(
        image=image_ref,
        name=container_name,
        detach=True,
        restart="always",
        publish=[(instance.port, 8000)],
    )
    if env_file_arg:
        run_kwargs["env_file"] = [env_file_arg]

    client.container.run(**run_kwargs)
    logger.info("Recreated container %s with image %s", container_name, image_ref)


def _get_logs_sync(instance: InstanceConfig, tail: int = 100) -> list[str]:
    """Return last *tail* log lines as a list of strings."""
    client = _make_client(instance)
    name = _container_name(instance)
    try:
        logs = client.container.logs(name, tail=tail)
        if isinstance(logs, bytes):
            return logs.decode(errors="replace").splitlines()
        if isinstance(logs, str):
            return logs.splitlines()
        return list(logs)
    except DockerException as exc:
        return [f"[error] {exc}"]


# ── Public async API ──────────────────────────────────────────────────────────

async def get_status(instance: InstanceConfig) -> InstanceStatus:
    """Async wrapper: fetch live status from Docker."""
    return await asyncio.to_thread(_get_status_sync, instance)


async def start(instance: InstanceConfig) -> None:
    """Start the instance's container."""
    await asyncio.to_thread(_start_sync, instance)


async def stop(instance: InstanceConfig) -> None:
    """Stop the instance's container."""
    await asyncio.to_thread(_stop_sync, instance)


async def restart(instance: InstanceConfig) -> None:
    """Restart the instance's container."""
    await asyncio.to_thread(_restart_sync, instance)


async def pull_image(instance: InstanceConfig, tag: str | None = None) -> None:
    """Pull (or re-pull) the Docker image."""
    await asyncio.to_thread(_pull_image_sync, instance, tag)


async def build_image(instance: InstanceConfig) -> None:
    """Build Docker image from local build_context."""
    await asyncio.to_thread(_build_image_sync, instance)


async def update(instance: InstanceConfig, tag: str | None = None) -> None:
    """Pull/build and recreate the container (rolling update)."""
    await asyncio.to_thread(_recreate_sync, instance, tag)


async def remove(instance: InstanceConfig, keep_volumes: bool = True) -> None:
    """Remove the instance's container."""
    await asyncio.to_thread(_remove_container_sync, instance, keep_volumes)


async def get_logs(instance: InstanceConfig, tail: int = 100) -> list[str]:
    """Return last *tail* log lines."""
    return await asyncio.to_thread(_get_logs_sync, instance, tail)


async def stream_logs(instance: InstanceConfig) -> AsyncGenerator[str, None]:
    """Async generator that yields log lines in real time via docker follow."""
    client = _make_client(instance)
    name = _container_name(instance)

    def _iter_logs():
        return client.container.logs(name, follow=True, stream=True)

    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    def _reader():
        try:
            for stream_type, line in _iter_logs():  # type: ignore[misc]
                if isinstance(line, bytes):
                    line = line.decode(errors="replace")
                loop.call_soon_threadsafe(queue.put_nowait, line.rstrip("\n"))
        except Exception as exc:
            loop.call_soon_threadsafe(queue.put_nowait, f"[stream error] {exc}")
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    thread = asyncio.to_thread(_reader)
    asyncio.ensure_future(thread)

    while True:
        item = await queue.get()
        if item is None:
            break
        yield item


async def clone(
    source: InstanceConfig,
    target_name: str,
    target_port: int,
    target_host: str = "local",
) -> InstanceConfig:
    """Clone source instance config to a new instance (config only, no data copy)."""
    from app.registry import InstanceConfig as IC, add_instance

    new_inst = IC(
        name=target_name,
        host=target_host,
        port=target_port,
        image=source.image,
        env_file=source.env_file,
        build_context=source.build_context,
        tls_cert=source.tls_cert,
        description=f"Clone of '{source.name}'",
    )
    add_instance(new_inst)
    return new_inst


async def backup(instance: InstanceConfig) -> dict:
    """Trigger an Immo-Boussole backup via its REST API."""
    import httpx
    url = f"http://localhost:{instance.port}/admin/backup"
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url)
        resp.raise_for_status()
        return resp.json()


async def restore(instance: InstanceConfig, archive_path: str) -> dict:
    """Trigger an Immo-Boussole restore via its REST API."""
    import httpx
    url = f"http://localhost:{instance.port}/admin/restore"
    with open(archive_path, "rb") as fh:
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(url, files={"file": fh})
            resp.raise_for_status()
            return resp.json()
