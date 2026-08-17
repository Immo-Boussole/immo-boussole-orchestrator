"""
Notification system — Webhook (generic POST JSON) and SMTP email.

Usage:
    from app.notifier import NotificationEvent, notify
    await notify(NotificationEvent(instance_name="prod", ...))
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


# ── Event data ────────────────────────────────────────────────────────────────

@dataclass
class NotificationEvent:
    instance_name: str
    previous_state: str
    new_state: str
    message: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "instance_name": self.instance_name,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


# ── Webhook ───────────────────────────────────────────────────────────────────

async def notify_webhook(event: NotificationEvent) -> None:
    """POST event JSON to the configured webhook URL."""
    settings = get_settings()
    if not settings.webhook_enabled:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                settings.notification_webhook_url,  # type: ignore[arg-type]
                json=event.to_dict(),
            )
            resp.raise_for_status()
        logger.info(
            "Webhook notification sent for instance %s (%s → %s)",
            event.instance_name,
            event.previous_state,
            event.new_state,
        )
    except Exception as exc:
        logger.error("Webhook notification failed: %s", exc)


# ── SMTP email ────────────────────────────────────────────────────────────────

async def notify_email(event: NotificationEvent) -> None:
    """Send an alert email via SMTP."""
    settings = get_settings()
    if not settings.smtp_enabled:
        return
    try:
        import aiosmtplib
        from email.mime.text import MIMEText

        subject = (
            f"[Orchestrator] Instance '{event.instance_name}' "
            f"changed: {event.previous_state} → {event.new_state}"
        )
        body_lines = [
            f"Instance : {event.instance_name}",
            f"Previous state : {event.previous_state}",
            f"New state      : {event.new_state}",
            f"Timestamp      : {event.timestamp.isoformat()}",
        ]
        if event.message:
            body_lines.append(f"Details        : {event.message}")
        body = "\n".join(body_lines)

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = ", ".join(settings.smtp_recipients)

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            use_tls=settings.smtp_use_tls,
        )
        logger.info(
            "Email notification sent for instance %s → %s",
            event.instance_name,
            settings.smtp_recipients,
        )
    except Exception as exc:
        logger.error("Email notification failed: %s", exc)


# ── Dispatcher ────────────────────────────────────────────────────────────────

async def notify(event: NotificationEvent) -> None:
    """Dispatch a notification event to all configured channels."""
    import asyncio
    await asyncio.gather(
        notify_webhook(event),
        notify_email(event),
        return_exceptions=True,
    )
