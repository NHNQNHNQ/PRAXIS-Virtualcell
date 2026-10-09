"""Tests for provenance gate."""
import importlib

import pytest

from praxis_virtualcell.model_zoo.registry import ModelZooRegistry


def _wrapper_instance(class_path: str):
    mod, cls = class_path.rsplit(".", 1)
    return getattr(importlib.import_module(mod), cls)()


@pytest.fixture(scope="module")
def reg():
    return ModelZooRegistry()


@pytest.mark.parametrize("name", ["gears", "scgpt"])
def test_registry_module_matches_wrapper_scope(reg, name):
    """Verify registry module matches wrapper scope."""
    e = reg.get(name)
    w = _wrapper_instance(e["wrapper"])
    assert w.declare_scope()["module"] == e["module"]
    assert set(e["species"]) <= set(w.declare_scope()["species"]) or \
           set(w.declare_scope()["species"]) <= set(e["species"])


@pytest.mark.parametrize("name", ["gears", "scgpt"])
def test_registry_anchor_matches_wrapper_provenance(reg, name):
    """Verify registry anchor matches wrapper provenance."""
    e = reg.get(name)
    w = _wrapper_instance(e["wrapper"])
    wp = w.declare_provenance()
    if name == "gears":
        assert wp["metrics"]["pearson_de"] == pytest.approx(
            e["provenance"]["metrics"]["pearson_de"], abs=1e-4)
        assert wp["not_comparable_to_donor_base"] is True
    else:
        assert wp["metrics"]["delta_pearson"] == pytest.approx(
            e["provenance"]["metrics"]["delta_pearson"], abs=1e-4)
        assert wp["not_comparable_to_donor_base"] is False


@pytest.mark.parametrize("name", ["gears", "scgpt"])
def test_distributability_declared(reg, name):
    """Verify distributability declared."""
    e = reg.get(name)
    assert e["assets"] and all("source_note" in a for a in e["assets"])
    assert e["provenance"]["distributable"] is False


def test_public_models_wrapper_importable(reg):
    """Verify public models wrapper importable."""
    for name in ("gears", "scgpt"):
        w = _wrapper_instance(reg.get(name)["wrapper"])
        assert w.declare_scope()["module"] == "genetic_hub"


def test_broker_fail_closed_depth_for_public_models():
    """Verify broker fail closed depth for public models."""
    from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
    from praxis_virtualcell.core.bus import MessageBus
    from praxis_virtualcell.core.message import AgentMessage

    for name in ("gears", "scgpt"):
        bus = MessageBus()
        ModelBrokerAgent().handle(AgentMessage(
            "q", "C", "ModelBrokerAgent", "model_request", {"model_name": name}, "t"), bus)
        p = bus.latest("model_broker_result").payload
        assert p["available"] is False and p["reason"]
        assert p["wrapper"]
