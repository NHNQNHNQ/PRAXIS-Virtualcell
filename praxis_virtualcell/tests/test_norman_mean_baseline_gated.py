"""Tests for norman mean baseline gated."""
import importlib.util

import pytest

from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry

_HAS_TORCH = importlib.util.find_spec("torch") is not None


def _ask(name):
    return AgentMessage("q1", "Client", "ModelBrokerAgent", "model_request", {"model_name": name}, "t1")




def test_registry_has_norman_mean_baseline_self_trained():
    reg = ModelZooRegistry()
    e = reg.get("norman_mean_baseline")
    assert e["type"] == "self_trained"
    assert e["species"] == ["human"]
    assert e["module"] == "genetic_hub"
    assert e["task"] == "predict_delta_expression"
    assert e["wrapper"].endswith("self_trained_wrapper.SelfTrainedWrapper")


def test_registry_training_card_has_real_anchor():
    """Verify registry training card has real anchor."""
    card = ModelZooRegistry().get("norman_mean_baseline")["training_card"]
    assert card["metrics"]["delta_pearson"] == pytest.approx(0.4615, abs=1e-4)
    assert card["metrics"]["n"] == 18874
    assert "norman" in card["training_data"].lower()


def test_broker_norman_mean_baseline_fail_closed():
    """Verify broker norman mean baseline fail closed."""
    bus = MessageBus()
    ModelBrokerAgent().handle(_ask("norman_mean_baseline"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False
    assert p["wrapper"].endswith("self_trained_wrapper.SelfTrainedWrapper")


def test_yeast_deletion_fitness_still_planned_no_data():
    """Verify yeast deletion fitness still planned no data."""
    e = ModelZooRegistry().get("yeast_deletion_fitness")
    assert e["status"] == "planned"
    prov = str(e["training_card"]["provenance"]).lower()
    assert "planned" in prov or "no weights" in prov


def test_norman_mean_baseline_source_self_trained_fail_closed():
    """Verify norman mean baseline source self trained fail closed."""
    bus = MessageBus()
    ModelBrokerAgent().handle(_ask("norman_mean_baseline"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False
    assert p["reason"]




pytestmark_remote = pytest.mark.remote


@pytest.mark.remote
def test_real_train_mean_delta_and_score():
    """Verify real train mean delta and score."""
    import torch  # noqa: F401 - Require the external inference dependency.

    from praxis_virtualcell.benchmarks.mean_baseline import score_mean_baseline

    res = score_mean_baseline(test_seed=1, train_seed=0)

    assert res["delta_pearson"] == pytest.approx(0.4615, abs=5e-3)
    assert res["n"] > 10000


@pytest.mark.remote
def test_real_selftrained_wrapper_run_prediction():
    """Verify real selftrained wrapper run prediction."""
    import torch  # noqa: F401 - Require the external inference dependency.

    from praxis_virtualcell.model_zoo.wrappers.self_trained_wrapper import SelfTrainedWrapper


    ckpt = __import__("os").environ.get("P7_MEAN_DELTA_CKPT")
    if not ckpt:
        pytest.skip("P7_MEAN_DELTA_CKPT must point to an available mean_delta checkpoint")
    w = SelfTrainedWrapper(ckpt_stem=ckpt)
    ctx = torch.zeros(2000)
    out = w.run_prediction({"targets": ["AHR"], "_context": ctx})
    assert out["prediction"]["n_genes"] == 2000
    assert out["prediction"]["is_naive_lower_bound_baseline"] is True
    assert out["uncertainty"]["available"] is False
