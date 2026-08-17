"""
Integration tests for the FastAPI REST API.
Uses httpx.AsyncClient + ASGITransport (no real server needed).
"""
from __future__ import annotations

import base64
import pytest
import pytest_asyncio

from httpx import AsyncClient, ASGITransport

from app.main import create_app


VALID_AUTH = ("admin", "admin")
BAD_AUTH   = ("wrong", "creds")

def _auth_header(user: str, pwd: str) -> dict:
    token = base64.b64encode(f"{user}:{pwd}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    """Create app with a temp instances.yaml."""
    import os
    tmp = tmp_path_factory.mktemp("data")
    yaml_path = tmp / "instances.yaml"
    yaml_path.write_text("instances: []\n")
    os.environ["INSTANCES_FILE"] = str(yaml_path)
    os.environ["ADMIN_USERNAME"] = "admin"
    os.environ["ADMIN_PASSWORD"] = "admin"
    os.environ["SECRET_KEY"]     = "test-secret"
    # Clear cached settings
    from app.config import get_settings
    get_settings.cache_clear()
    return create_app()


@pytest_asyncio.fixture
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ── /health ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── Auth ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_instances_requires_auth(client):
    resp = await client.get("/api/instances")
    assert resp.status_code == 401
    assert "WWW-Authenticate" in resp.headers


@pytest.mark.asyncio
async def test_list_instances_wrong_credentials(client):
    resp = await client.get("/api/instances", headers=_auth_header(*BAD_AUTH))
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_instances_valid_auth(client):
    resp = await client.get("/api/instances", headers=_auth_header(*VALID_AUTH))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Instance CRUD ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_instance(client):
    payload = {
        "name": "testinst",
        "host": "local",
        "port": 8500,
        "image": "wikijm/immo-boussole:latest",
        "description": "Test instance",
        "start_after_create": False,
    }
    resp = await client.post(
        "/api/instances",
        json=payload,
        headers=_auth_header(*VALID_AUTH),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["config"]["name"] == "testinst"
    assert data["config"]["port"] == 8500


@pytest.mark.asyncio
async def test_create_duplicate_returns_409(client):
    payload = {"name": "testinst", "port": 8500, "start_after_create": False}
    resp = await client.post(
        "/api/instances",
        json=payload,
        headers=_auth_header(*VALID_AUTH),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_instance(client):
    resp = await client.get(
        "/api/instances/testinst",
        headers=_auth_header(*VALID_AUTH),
    )
    assert resp.status_code == 200
    assert resp.json()["config"]["name"] == "testinst"


@pytest.mark.asyncio
async def test_get_nonexistent_instance_404(client):
    resp = await client.get(
        "/api/instances/doesnotexist",
        headers=_auth_header(*VALID_AUTH),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_instance(client):
    payload = {"description": "Updated description", "port": 8501}
    resp = await client.put(
        "/api/instances/testinst",
        json=payload,
        headers=_auth_header(*VALID_AUTH),
    )
    assert resp.status_code == 200
    assert resp.json()["config"]["description"] == "Updated description"
    assert resp.json()["config"]["port"] == 8501


@pytest.mark.asyncio
async def test_list_includes_created_instance(client):
    resp = await client.get("/api/instances", headers=_auth_header(*VALID_AUTH))
    names = [i["config"]["name"] for i in resp.json()]
    assert "testinst" in names


@pytest.mark.asyncio
async def test_delete_instance(client):
    resp = await client.delete(
        "/api/instances/testinst?keep_volumes=true",
        headers=_auth_header(*VALID_AUTH),
    )
    assert resp.status_code == 200
    assert "removed" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_delete_nonexistent_returns_404(client):
    resp = await client.delete(
        "/api/instances/ghost",
        headers=_auth_header(*VALID_AUTH),
    )
    assert resp.status_code == 404
