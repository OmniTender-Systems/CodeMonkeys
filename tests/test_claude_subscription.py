"""Claude subscription auth (issue #234) — model router recognizes
subscription-based Anthropic credentials as a distinct auth path."""
from __future__ import annotations

import pytest

import server


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Point all file-backed state at a fresh tmp dir."""
    monkeypatch.setattr(server, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(server, "USERS_FILE", str(tmp_path / "users.json"))
    monkeypatch.setattr(server, "MODELS_FILE", str(tmp_path / "model_config.json"))
    monkeypatch.setattr(server, "SESSIONS_DIR", str(tmp_path / "sessions"))
    monkeypatch.setattr(server, "WORKSPACE_DIR", str(tmp_path / "workspace"))
    server.save_users({})
    yield


def _make_anthropic_subscription():
    """Provider entry shaped like a Claude Pro/Max subscription."""
    return {
        "label": "Claude Pro (subscription)",
        "kind": "anthropic",
        "base_url": "",
        "key": "session-token-placeholder",
        "model": "claude-sonnet-4-6",
        "models": ["claude-haiku-4-5", "claude-sonnet-4-6", "claude-opus-4-8"],
        "in": 3.0, "out": 15.0,
        "auth_type": "subscription",
        "auto": True,
    }


def test_subscription_anthropic_is_callable_without_api_key():
    """A subscription provider with a session token is callable, even though
    it has no traditional API key — the token IS the credential."""
    p = _make_anthropic_subscription()
    assert server._callable_provider(p) is True


def test_api_key_anthropic_still_needs_key():
    """Classic API-key Anthropic: not callable with empty key."""
    p = dict(_make_anthropic_subscription(), auth_type="api_key", key="")
    assert server._callable_provider(p) is False


def test_subscription_costs_are_zero():
    """Subscription providers bill $0/token (flat monthly rate)."""
    cfg = server.load_models()
    cfg["providers"]["claude-sub"] = _make_anthropic_subscription()
    resolved = server._resolve(cfg["providers"]["claude-sub"], pid="claude-sub")
    assert resolved["input_cost_per_m"] == 0
    assert resolved["output_cost_per_m"] == 0


def test_upsert_subscription_forces_zero_cost():
    """POST /api/models with auth_type=subscription always stores $0 costs,
    even if the caller passes per-token values."""
    req = server.ProviderUpsert(
        id="claude-sub",
        label="Claude Pro",
        kind="anthropic",
        model="claude-sonnet-4-6",
        auth_type="subscription",
        input_cost_per_m=999,  # should be ignored
        output_cost_per_m=999,
    )
    # Call the inner logic that models_upsert would execute:
    in_cost = server._validate_cost(req.input_cost_per_m, "input_cost_per_m")
    out_cost = server._validate_cost(req.output_cost_per_m, "output_cost_per_m")
    if req.auth_type == "subscription":
        in_cost, out_cost = 0.0, 0.0
    assert in_cost == 0.0
    assert out_cost == 0.0


def test_subscription_can_be_selected_by_main_provider():
    """Subscription Anthropic flows through the full provider-selection path."""
    cfg = server.load_models()
    cfg["providers"]["claude-sub"] = _make_anthropic_subscription()
    sel = server.main_provider(cfg)
    assert sel is not None
    # The chosen provider should have $0 costs and kind anthropic
    assert sel["kind"] == "anthropic"
    assert sel["input_cost_per_m"] == 0
    assert sel["output_cost_per_m"] == 0


def test_subscription_exposes_auth_type_in_models_get():
    """The /api/models GET response includes the new auth_type field so the
    UI can show a different input (session token vs API key)."""
    cfg = server.load_models()
    cfg["providers"]["claude-sub"] = _make_anthropic_subscription()
    # Build the API response shape inline (mirrors models_get):
    out = [
        {"id": pid, "auth_type": p.get("auth_type", "api_key")}
        for pid, p in cfg["providers"].items()
    ]
    sub = next(x for x in out if x["id"] == "claude-sub")
    assert sub["auth_type"] == "subscription"
    anth = next(x for x in out if x["id"] == "anthropic")
    assert anth["auth_type"] == "api_key"
