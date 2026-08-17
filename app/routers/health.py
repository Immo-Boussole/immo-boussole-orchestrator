"""Health check endpoint."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness probe — always returns 200 OK."""
    return {"status": "ok"}
