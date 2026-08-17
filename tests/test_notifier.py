"""
Unit tests for the notifier module.
Mocks httpx and aiosmtplib to verify dispatch logic without real network calls.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.notifier import NotificationEvent, notify_webhook, notify_email, notify


SAMPLE_EVENT = NotificationEvent(
    instance_name="prod",
    previous_state="running",
    new_state="exited",
    message="Container exited unexpectedly",
    timestamp=datetime(2026, 8, 17, 12, 0, 0, tzinfo=timezone.utc),
)


# ── NotificationEvent ─────────────────────────────────────────────────────────

def test_notification_event_to_dict():
    d = SAMPLE_EVENT.to_dict()
    assert d["instance_name"] == "prod"
    assert d["previous_state"] == "running"
    assert d["new_state"] == "exited"
    assert "2026" in d["timestamp"]


# ── notify_webhook ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_not_called_when_disabled(monkeypatch):
    """If NOTIFICATION_WEBHOOK_URL is empty, no HTTP call should be made."""
    from app import notifier as notifier_module
    import app.notifier as nm
    with patch.object(nm, "get_settings") as mock_settings:
        mock_settings.return_value.webhook_enabled = False
        with patch("httpx.AsyncClient") as mock_client_cls:
            await notify_webhook(SAMPLE_EVENT)
            mock_client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_webhook_posts_json(monkeypatch):
    """When enabled, notify_webhook should POST JSON to the configured URL."""
    import app.notifier as nm
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch.object(nm, "get_settings") as mock_settings:
        mock_settings.return_value.webhook_enabled = True
        mock_settings.return_value.notification_webhook_url = "http://hooks.example.com/notify"
        with patch("httpx.AsyncClient", return_value=mock_client):
            await notify_webhook(SAMPLE_EVENT)

    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert call_kwargs[1]["json"]["instance_name"] == "prod"
    assert call_kwargs[1]["json"]["new_state"] == "exited"


# ── notify_email ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_email_not_called_when_disabled(monkeypatch):
    import app.notifier as nm
    with patch.object(nm, "get_settings") as mock_settings:
        mock_settings.return_value.smtp_enabled = False
        with patch("aiosmtplib.send") as mock_send:
            await notify_email(SAMPLE_EVENT)
            mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_email_sends_when_configured(monkeypatch):
    import app.notifier as nm
    with patch.object(nm, "get_settings") as mock_settings:
        settings = MagicMock()
        settings.smtp_enabled = True
        settings.smtp_host = "smtp.example.com"
        settings.smtp_port = 587
        settings.smtp_username = "user"
        settings.smtp_password = "pass"
        settings.smtp_from = "orch@example.com"
        settings.smtp_recipients = ["admin@example.com"]
        settings.smtp_use_tls = True
        mock_settings.return_value = settings

        with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            await notify_email(SAMPLE_EVENT)
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1]
            assert call_kwargs["hostname"] == "smtp.example.com"


# ── notify (dispatcher) ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notify_calls_both_channels():
    import app.notifier as nm
    with patch.object(nm, "notify_webhook", new_callable=AsyncMock) as mock_wh, \
         patch.object(nm, "notify_email",   new_callable=AsyncMock) as mock_em:
        await notify(SAMPLE_EVENT)
        mock_wh.assert_called_once_with(SAMPLE_EVENT)
        mock_em.assert_called_once_with(SAMPLE_EVENT)
