"""Subagent cap: failed spawns must not consume slots (Claude Code discovered bug)."""
from __future__ import annotations

import pytest

import server


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(server, "USERS_FILE", str(tmp_path / "users.json"))
    monkeypatch.setattr(server, "MODELS_FILE", str(tmp_path / "model_config.json"))
    monkeypatch.setattr(server, "SESSIONS_DIR", str(tmp_path / "sessions"))
    monkeypatch.setattr(server, "WORKSPACE_DIR", str(tmp_path / "workspace"))
    server.save_users({})
    yield


def _make_session(username="test_user"):
    """Minimal session dict matching what agent_loop expects."""
    return {
        "username": username,
        "sid": "test-session",
        "agents_spawned": 0,
        "stop_flag": __import__("threading").Event(),
        "mode": "execute",
        "events": [],
    }


def test_unknown_agent_name_does_not_consume_cap():
    """Spawning an agent that doesn't exist should not count against the cap."""
    session = _make_session()
    result = server.run_subagent(session, "nonexistent_agent", "do something")
    assert "ERROR" in result
    assert session["agents_spawned"] == 0


def test_no_model_provider_does_not_consume_cap():
    """Spawning when no provider is configured should not burn a slot."""
    session = _make_session()
    # Use a real agent name from CORPS — but no provider configured
    agent_name = next(iter(server.CORPS), None)
    if agent_name is None:
        pytest.skip("No agents defined in CORPS")
    result = server.run_subagent(session, agent_name, "test task")
    # Either the cap is reached (if MAX_SUBAGENTS is 0) or no provider error
    assert "ERROR" in result
    assert session["agents_spawned"] == 0


def test_cap_already_max_blocks_immediately():
    """When cap is already reached, no increment happens."""
    session = _make_session()
    session["agents_spawned"] = server.MAX_SUBAGENTS
    result = server.run_subagent(session, "some_agent", "task")
    assert "cap" in result.lower() or "ERROR" in result
    assert session["agents_spawned"] == server.MAX_SUBAGENTS
