"""
HTTP Basic authentication dependency for FastAPI.

Usage in a route:
    @router.get("/protected")
    async def protected(user: str = Depends(require_auth)):
        ...
"""
from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import get_settings

security = HTTPBasic()


def require_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Validate HTTP Basic credentials against the configured admin account.

    Returns the authenticated username on success.
    Raises HTTP 401 on failure.
    """
    settings = get_settings()

    correct_username = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        settings.admin_username.encode("utf-8"),
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        settings.admin_password.encode("utf-8"),
    )

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
