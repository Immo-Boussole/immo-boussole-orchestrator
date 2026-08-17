"""
Unit tests for the YAML instance registry.
"""
from __future__ import annotations

import pytest
from pathlib import Path

from app.registry import (
    InstanceConfig,
    add_instance,
    get_instance,
    load_registry,
    remove_instance,
    save_registry,
    update_instance,
)


@pytest.fixture(autouse=True)
def tmp_registry(tmp_path, monkeypatch):
    """Redirect the registry to a temp file for each test."""
    registry_file = tmp_path / "instances.yaml"
    registry_file.write_text("instances: []\n")

    # Patch get_settings to return a settings object pointing to tmp file
    import app.registry as reg_module
    original_path = reg_module._registry_path

    def _patched_path():
        return registry_file

    monkeypatch.setattr(reg_module, "_registry_path", _patched_path)
    yield registry_file


# ── InstanceConfig validation ─────────────────────────────────────────────────

def test_instance_config_name_lowercase():
    inst = InstanceConfig(name="MyDev")
    assert inst.name == "mydev"


def test_instance_config_invalid_name():
    with pytest.raises(Exception):
        InstanceConfig(name="my dev!")  # spaces and ! not allowed


def test_instance_config_defaults():
    inst = InstanceConfig(name="test")
    assert inst.host == "local"
    assert inst.port == 8000
    assert inst.image == "wikijm/immo-boussole:latest"


# ── load_registry ─────────────────────────────────────────────────────────────

def test_load_empty_registry():
    result = load_registry()
    assert result == []


def test_load_registry_after_save():
    inst = InstanceConfig(name="dev", host="local", port=8000)
    save_registry([inst])
    loaded = load_registry()
    assert len(loaded) == 1
    assert loaded[0].name == "dev"


# ── add_instance ──────────────────────────────────────────────────────────────

def test_add_instance():
    inst = InstanceConfig(name="prod", port=8100)
    add_instance(inst)
    result = load_registry()
    assert any(i.name == "prod" for i in result)


def test_add_duplicate_raises():
    inst = InstanceConfig(name="dup")
    add_instance(inst)
    with pytest.raises(ValueError, match="already exists"):
        add_instance(inst)


# ── get_instance ──────────────────────────────────────────────────────────────

def test_get_instance_found():
    add_instance(InstanceConfig(name="findme", port=9999))
    result = get_instance("findme")
    assert result.port == 9999


def test_get_instance_not_found():
    with pytest.raises(KeyError):
        get_instance("nonexistent")


def test_get_instance_case_insensitive():
    add_instance(InstanceConfig(name="alpha"))
    result = get_instance("ALPHA")
    assert result.name == "alpha"


# ── remove_instance ───────────────────────────────────────────────────────────

def test_remove_instance():
    add_instance(InstanceConfig(name="todelete"))
    remove_instance("todelete")
    with pytest.raises(KeyError):
        get_instance("todelete")


def test_remove_nonexistent_raises():
    with pytest.raises(KeyError):
        remove_instance("ghost")


# ── update_instance ───────────────────────────────────────────────────────────

def test_update_instance():
    add_instance(InstanceConfig(name="updateme", port=8000))
    updated = InstanceConfig(name="updateme", port=9999, description="updated!")
    update_instance("updateme", updated)
    result = get_instance("updateme")
    assert result.port == 9999
    assert result.description == "updated!"


def test_update_nonexistent_raises():
    with pytest.raises(KeyError):
        update_instance("nope", InstanceConfig(name="nope"))


# ── save_registry (round-trip) ────────────────────────────────────────────────

def test_save_and_reload_multiple():
    instances = [
        InstanceConfig(name="dev",  port=8000, host="local"),
        InstanceConfig(name="prod", port=8100, host="ssh://deploy@server"),
    ]
    save_registry(instances)
    loaded = load_registry()
    assert len(loaded) == 2
    assert loaded[1].host == "ssh://deploy@server"
