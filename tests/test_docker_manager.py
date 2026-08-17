"""
Unit tests for docker_manager — mocked python-on-whales.
Verifies client construction per host type without a real Docker daemon.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.docker_manager import _make_client, _container_name, InstanceStatus
from app.registry import InstanceConfig


# ── _make_client ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_docker_client():
    """Patch DockerClient so no real Docker connection is made."""
    with patch("app.docker_manager.DockerClient") as mock_cls:
        mock_cls.return_value = MagicMock()
        yield mock_cls


def test_local_host_no_args(mock_docker_client):
    inst = InstanceConfig(name="local-test", host="local")
    _make_client(inst)
    mock_docker_client.assert_called_once_with()


def test_unix_socket_host(mock_docker_client):
    inst = InstanceConfig(name="unix-test", host="unix:///var/run/docker.sock")
    _make_client(inst)
    mock_docker_client.assert_called_once_with(host="unix:///var/run/docker.sock")


def test_ssh_host(mock_docker_client):
    inst = InstanceConfig(name="ssh-test", host="ssh://deploy@server.example.com")
    _make_client(inst)
    mock_docker_client.assert_called_once_with(host="ssh://deploy@server.example.com")


def test_tcp_host_no_tls(mock_docker_client):
    inst = InstanceConfig(name="tcp-test", host="tcp://192.168.1.10:2376")
    _make_client(inst)
    mock_docker_client.assert_called_once_with(host="tcp://192.168.1.10:2376")


def test_npipe_host(mock_docker_client):
    inst = InstanceConfig(name="win-test", host="npipe:////./pipe/docker_engine")
    _make_client(inst)
    mock_docker_client.assert_called_once_with(host="npipe:////./pipe/docker_engine")


def test_empty_host_treated_as_local(mock_docker_client):
    inst = InstanceConfig(name="empty-test", host="")
    _make_client(inst)
    mock_docker_client.assert_called_once_with()


# ── _container_name ───────────────────────────────────────────────────────────

def test_container_name_format():
    inst = InstanceConfig(name="prod")
    assert _container_name(inst) == "immo-boussole-prod-app"


def test_container_name_dev():
    inst = InstanceConfig(name="dev")
    assert _container_name(inst) == "immo-boussole-dev-app"


# ── InstanceStatus ────────────────────────────────────────────────────────────

def test_instance_status_defaults():
    st = InstanceStatus()
    assert st.state == "unknown"
    assert st.health == "unknown"
    assert st.uptime_seconds is None
    assert st.ports == []
    assert st.error is None


def test_instance_status_to_dict():
    st = InstanceStatus(state="running", health="healthy", uptime_seconds=3600)
    d = st.to_dict()
    assert d["state"] == "running"
    assert d["health"] == "healthy"
    assert d["uptime_seconds"] == 3600
