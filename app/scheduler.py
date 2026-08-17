"""
Background health poller — APScheduler AsyncIOScheduler.

Polls every instance every HEALTH_POLL_INTERVAL seconds.
On state transitions (running→stopped, healthy→unhealthy, etc.) fires a
NotificationEvent through the notifier.
"""
from __future__ import annotations

import logging
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app import docker_manager
from app.config import get_settings
from app.notifier import NotificationEvent, notify
from app.registry import load_registry

logger = logging.getLogger(__name__)

# In-memory cache: instance_name → last known state string
_state_cache: dict[str, str] = {}

scheduler = AsyncIOScheduler()


async def _poll_instances() -> None:
    """Poll all registered instances and emit notifications on state changes."""
    instances = load_registry()
    for inst in instances:
        try:
            status = await docker_manager.get_status(inst)
            current_state = status.state
            previous_state = _state_cache.get(inst.name)

            if previous_state is None:
                # First poll — just record state, no notification
                _state_cache[inst.name] = current_state
                continue

            if current_state != previous_state:
                logger.info(
                    "Instance %s state change: %s → %s",
                    inst.name,
                    previous_state,
                    current_state,
                )
                _state_cache[inst.name] = current_state

                # Notify on unexpected/negative transitions
                unexpected = current_state in (
                    "exited", "dead", "paused", "absent", "error"
                )
                if unexpected:
                    event = NotificationEvent(
                        instance_name=inst.name,
                        previous_state=previous_state,
                        new_state=current_state,
                        message=status.error or "",
                    )
                    await notify(event)
        except Exception as exc:
            logger.warning(
                "Health poll failed for instance %s: %s", inst.name, exc
            )


def start_scheduler() -> None:
    """Register the poll job and start the scheduler."""
    settings = get_settings()
    scheduler.add_job(
        _poll_instances,
        trigger="interval",
        seconds=settings.health_poll_interval,
        id="health_poll",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info(
        "Health poller started (interval=%ds)", settings.health_poll_interval
    )


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Health poller stopped.")


def get_last_known_state(instance_name: str) -> str | None:
    """Return the last polled state for an instance (or None if never polled)."""
    return _state_cache.get(instance_name)
