"""
FastAPI application entry point.

Mounts:
- REST API routers (/api/instances, /api/instances/{name}/logs, /health)
- Static files (/static)
- Jinja2 HTML templates (/ and /instances/{name})
- HTTP Basic auth on all routes
- Lifecycle events: start/stop scheduler
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import docker_manager
from app.auth import require_auth
from app.config import get_settings
from app.registry import get_instance, load_registry
from app.routers import health, instances, logs
from app.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup → run scheduler. Shutdown → stop scheduler."""
    logger.info("Starting Immo-Boussole Orchestrator…")
    start_scheduler()
    yield
    logger.info("Shutting down Immo-Boussole Orchestrator…")
    stop_scheduler()


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Immo-Boussole Orchestrator",
        description=(
            "CLI & web orchestrator to deploy, manage, monitor, "
            "and update multiple Immo-Boussole instances."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── Static files ──────────────────────────────────────────────────────────
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # ── API Routers ───────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(instances.router)
    app.include_router(logs.router)

    # ── Jinja2 templates ──────────────────────────────────────────────────────
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    # ── UI Routes ─────────────────────────────────────────────────────────────

    @app.get("/", response_class=HTMLResponse)
    async def index(
        request: Request,
        user: str = Depends(require_auth),
    ):
        """Dashboard — instance overview."""
        registry = load_registry()
        import asyncio
        statuses = await asyncio.gather(
            *[docker_manager.get_status(i) for i in registry],
            return_exceptions=True,
        )
        instances_data = []
        for inst, status in zip(registry, statuses):
            if isinstance(status, Exception):
                from app.docker_manager import InstanceStatus
                status = InstanceStatus(state="error", health="none", error=str(status))
            instances_data.append({"config": inst, "status": status})

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "instances": instances_data,
                "user": user,
                "settings": settings,
            },
        )

    @app.get("/instances/{name}", response_class=HTMLResponse)
    async def instance_detail(
        name: str,
        request: Request,
        user: str = Depends(require_auth),
    ):
        """Instance detail page with live logs and action bar."""
        try:
            inst = get_instance(name)
        except KeyError:
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/")
        status = await docker_manager.get_status(inst)
        return templates.TemplateResponse(
            "instance_detail.html",
            {
                "request": request,
                "instance": inst,
                "status": status,
                "user": user,
            },
        )

    return app


app = create_app()
