"""
Application configuration via pydantic-settings.
Loaded from environment variables / .env file.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All orchestrator configuration, loaded from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Security ──────────────────────────────────────────────────────────────
    secret_key: str = "change-me"

    # ── Web UI Auth (HTTP Basic) ───────────────────────────────────────────────
    admin_username: str = "admin"
    admin_password: str = "admin"

    # ── Server ────────────────────────────────────────────────────────────────
    orchestrator_host: str = "0.0.0.0"
    orchestrator_port: int = 9000

    # ── MCP Server ────────────────────────────────────────────────────────────
    mcp_port: int = 9001

    # ── Instance Registry ─────────────────────────────────────────────────────
    instances_file: str = "instances.yaml"

    @property
    def instances_path(self) -> Path:
        return Path(self.instances_file)

    # ── Notifications — Webhook ───────────────────────────────────────────────
    notification_webhook_url: str | None = None

    # ── Notifications — SMTP ──────────────────────────────────────────────────
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "orchestrator@example.com"
    smtp_to: str = ""          # Comma-separated list
    smtp_use_tls: bool = True

    @property
    def smtp_recipients(self) -> list[str]:
        """Return the list of SMTP recipient addresses."""
        return [addr.strip() for addr in self.smtp_to.split(",") if addr.strip()]

    # ── Health Poller ─────────────────────────────────────────────────────────
    health_poll_interval: int = 30   # seconds

    # ── Debug ─────────────────────────────────────────────────────────────────
    debug: bool = False

    # ── Derived helpers ───────────────────────────────────────────────────────
    @property
    def smtp_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_recipients)

    @property
    def webhook_enabled(self) -> bool:
        return bool(self.notification_webhook_url)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton Settings instance."""
    return Settings()
