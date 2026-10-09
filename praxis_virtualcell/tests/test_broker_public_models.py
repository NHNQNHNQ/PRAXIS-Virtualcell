"""Tests for broker public models."""
import hashlib
import importlib.util

from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.model_zoo.cache import ModelCache

_HAS_TORCH = importlib.util.find_spec("torch") is not None


def _ask(name):
    return AgentMessage("q1", "Client", "ModelBrokerAgent", "model_request",
                        {"model_name": name}, "t1")


def _resolve(name, cache=None):
    bus = MessageBus()
    ModelBrokerAgent(cache=cache).handle(_ask(name), bus)
    return bus.latest("model_broker_result").payload


def test_gears_fail_closed_missing_torch_locally():
    """Verify gears fail closed missing torch locally."""
    if _HAS_TORCH:
        import pytest
        pytest.skip("This assertion requires torch to be unavailable")
    p = _resolve("gears")
    assert p["available"] is False
    assert p["status"] == "planned"
    assert "torch" in p["reason"] or "gpu" in p["reason"] or "planned" in p["reason"]


def test_scgpt_fail_closed_locally():
    p = _resolve("scgpt")
    assert p["available"] is False
    assert p["reason"]


def test_wrapper_class_path_still_visible_when_unavailable():
    """Verify wrapper class path still visible when unavailable."""
    p = _resolve("scgpt")
    assert p["wrapper"].endswith("scgpt_wrapper.ScgptWrapper")
    assert p["available"] is False


def test_assets_sha_placeholder_gates_requires_manual_fetch(tmp_path):
    """Verify assets sha placeholder gates requires manual fetch."""
    import praxis_virtualcell.agents.model_broker_agent as mba
    from praxis_virtualcell.model_zoo.registry import ModelZooRegistry

    reg_yaml = tmp_path / "reg.yaml"
    reg_yaml.write_text(
        "models:\n"
        "  tm:\n"
        "    name: tm\n"
        "    type: public_model\n"
        "    species: [human]\n"
        "    module: genetic_hub\n"
        "    task: t\n"
        "    source: cobra_bundled_textbook\n"
        "    license: MIT\n"
        "    status: available\n"
        "    wrapper: x.Y\n"
        "    version: v1\n"
        "    requires: []\n"
        "    reliability_policy: p\n"
        "    assets:\n"
        "      - filename: w.pt\n"
        "        sha256: null\n"
        "        source_note: local\n",
        encoding="utf-8")
    cache = ModelCache(root=str(tmp_path))
    ap = cache.asset_path("tm", "w.pt")
    ap.parent.mkdir(parents=True, exist_ok=True)
    ap.write_bytes(b"weights-present-but-sha-unregistered")

    bus = MessageBus()
    mba.ModelBrokerAgent(registry=ModelZooRegistry(registry_path=str(reg_yaml)),
                         cache=cache).handle(_ask("tm"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False
    assert "asset" in p["reason"] or "manual_fetch" in p["reason"] or "sha256" in p["reason"]


def test_assets_present_and_sha_match_passes_asset_gate(tmp_path, monkeypatch):
    """Verify assets present and sha match passes asset gate."""
    import praxis_virtualcell.agents.model_broker_agent as mba
    from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
    monkeypatch.setattr(mba, "_dep_available", lambda dep: True)

    payload = b"fake-weights"
    sha = hashlib.sha256(payload).hexdigest()
    reg_yaml = tmp_path / "reg.yaml"
    reg_yaml.write_text(
        "models:\n"
        "  tm:\n"
        "    name: tm\n"
        "    type: public_model\n"
        "    species: [human]\n"
        "    module: genetic_hub\n"
        "    task: t\n"
        "    source: cobra_bundled_textbook\n"
        "    license: MIT\n"
        "    status: available\n"
        "    wrapper: x.Y\n"
        "    version: v1\n"
        "    requires: []\n"
        "    reliability_policy: p\n"
        "    assets:\n"
        "      - filename: w.pt\n"
        f"        sha256: '{sha}'\n"
        "        source_note: local\n",
        encoding="utf-8")
    cache = ModelCache(root=str(tmp_path))
    ap = cache.asset_path("tm", "w.pt")
    ap.parent.mkdir(parents=True, exist_ok=True)
    ap.write_bytes(payload)

    bus = MessageBus()
    mba.ModelBrokerAgent(registry=ModelZooRegistry(registry_path=str(reg_yaml)),
                         cache=cache).handle(_ask("tm"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is True


def test_assets_sha_mismatch_fail_closed(tmp_path, monkeypatch):
    """Verify assets sha mismatch fail closed."""
    import praxis_virtualcell.agents.model_broker_agent as mba
    from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
    monkeypatch.setattr(mba, "_dep_available", lambda dep: True)

    wrong_sha = hashlib.sha256(b"expected").hexdigest()
    reg_yaml = tmp_path / "reg.yaml"
    reg_yaml.write_text(
        "models:\n"
        "  tm:\n"
        "    name: tm\n    type: public_model\n    species: [human]\n"
        "    module: genetic_hub\n    task: t\n    source: cobra_bundled_textbook\n"
        "    license: MIT\n    status: available\n    wrapper: x.Y\n    version: v1\n"
        "    requires: []\n    reliability_policy: p\n"
        "    assets:\n"
        "      - filename: w.pt\n"
        f"        sha256: '{wrong_sha}'\n"
        "        source_note: local\n",
        encoding="utf-8")
    cache = ModelCache(root=str(tmp_path))
    ap = cache.asset_path("tm", "w.pt")
    ap.parent.mkdir(parents=True, exist_ok=True)
    ap.write_bytes(b"actual-different-bytes")

    bus = MessageBus()
    mba.ModelBrokerAgent(registry=ModelZooRegistry(registry_path=str(reg_yaml)),
                         cache=cache).handle(_ask("tm"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False
    assert "sha256" in p["reason"] or "asset" in p["reason"]
