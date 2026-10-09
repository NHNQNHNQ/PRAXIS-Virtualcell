"""Tests for broker self trained."""
import hashlib

from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry


def _ask(name):
    return AgentMessage("q1", "Client", "ModelBrokerAgent", "model_request",
                        {"model_name": name}, "t1")


def _resolve_default(name, cache=None):
    bus = MessageBus()
    ModelBrokerAgent(cache=cache).handle(_ask(name), bus)
    return bus.latest("model_broker_result").payload


def test_yeast_deletion_fitness_planned_fail_closed():
    """Verify yeast deletion fitness planned fail closed."""
    p = _resolve_default("yeast_deletion_fitness")
    assert p["available"] is False
    assert p["status"] == "planned"
    assert "planned" in p["reason"] or "not available" in p["reason"]

    assert p["wrapper"].endswith("self_trained_wrapper.SelfTrainedWrapper")


def test_self_trained_source_requires_manual_fetch(tmp_path):
    """Verify self trained source requires manual fetch."""
    import praxis_virtualcell.agents.model_broker_agent as mba
    reg_yaml = tmp_path / "reg.yaml"
    reg_yaml.write_text(
        "models:\n"
        "  st:\n"
        "    name: st\n    type: self_trained\n    species: [human]\n"
        "    module: genetic_hub\n    task: predict_delta_expression\n"
        "    source: 'self_trained:st'\n"
        "    license: internal\n    status: available\n"
        "    wrapper: x.Y\n    version: v1\n    requires: []\n"
        "    reliability_policy: ml_disagreement\n"
        "    training_card:\n"
        "      training_data: donor norman\n      split: seed split\n"
        "      baseline: naive\n      metrics: {delta_pearson: 0.4615}\n"
        "      provenance: scored on .53\n",
        encoding="utf-8")
    bus = MessageBus()
    mba.ModelBrokerAgent(registry=ModelZooRegistry(registry_path=str(reg_yaml))).handle(_ask("st"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False
    assert "source" in p["reason"] or "manual" in p["reason"]


def test_self_trained_with_local_ckpt_and_sha_passes(tmp_path, monkeypatch):
    """Verify self trained with local ckpt and sha passes."""
    import praxis_virtualcell.agents.model_broker_agent as mba
    monkeypatch.setattr(mba, "_dep_available", lambda dep: True)

    payload = b"fake-mean-delta-tensor"
    sha = hashlib.sha256(payload).hexdigest()
    reg_yaml = tmp_path / "reg.yaml"
    reg_yaml.write_text(
        "models:\n"
        "  st:\n"
        "    name: st\n    type: self_trained\n    species: [human]\n"
        "    module: genetic_hub\n    task: predict_delta_expression\n"
        "    source: cobra_bundled_textbook\n"
        "    license: internal\n    status: available\n    wrapper: x.Y\n    version: v1\n"
        "    requires: []\n    reliability_policy: ml_disagreement\n"
        "    training_card:\n"
        "      training_data: donor norman\n      split: seed split\n"
        "      baseline: naive\n      metrics: {delta_pearson: 0.4615}\n"
        "      provenance: scored on .53\n"
        "    assets:\n"
        "      - filename: mean_delta.pt\n"
        f"        sha256: '{sha}'\n"
        "        source_note: local\n",
        encoding="utf-8")
    cache = ModelCache(root=str(tmp_path))
    ap = cache.asset_path("st", "mean_delta.pt")
    ap.parent.mkdir(parents=True, exist_ok=True)
    ap.write_bytes(payload)

    bus = MessageBus()
    mba.ModelBrokerAgent(registry=ModelZooRegistry(registry_path=str(reg_yaml)),
                         cache=cache).handle(_ask("st"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is True


def test_self_trained_sha_placeholder_fail_closed(tmp_path, monkeypatch):
    """Verify self trained sha placeholder fail closed."""
    import praxis_virtualcell.agents.model_broker_agent as mba
    monkeypatch.setattr(mba, "_dep_available", lambda dep: True)

    reg_yaml = tmp_path / "reg.yaml"
    reg_yaml.write_text(
        "models:\n"
        "  st:\n"
        "    name: st\n    type: self_trained\n    species: [human]\n"
        "    module: genetic_hub\n    task: predict_delta_expression\n"
        "    source: cobra_bundled_textbook\n    license: internal\n    status: available\n"
        "    wrapper: x.Y\n    version: v1\n    requires: []\n    reliability_policy: ml_disagreement\n"
        "    training_card:\n"
        "      training_data: donor norman\n      split: seed split\n"
        "      baseline: naive\n      metrics: {pearson: null, note: planned}\n"
        "      provenance: planned; no weights yet\n"
        "    assets:\n"
        "      - filename: mean_delta.pt\n"
        "        sha256: null\n"
        "        source_note: local\n",
        encoding="utf-8")
    cache = ModelCache(root=str(tmp_path))
    bus = MessageBus()
    mba.ModelBrokerAgent(registry=ModelZooRegistry(registry_path=str(reg_yaml)),
                         cache=cache).handle(_ask("st"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False
    assert "manual_fetch" in p["reason"] or "sha256" in p["reason"] or "asset" in p["reason"]
