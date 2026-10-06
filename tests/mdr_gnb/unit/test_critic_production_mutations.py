"""T4 critic guards must fire from the MDR production entry point.

These are mutation/counterexample tests, not direct ``check_invariants`` unit
tests: each deliberately corrupts one adjacent production-stage contract and
then asserts that the final report records the matching critic violation.
"""
from __future__ import annotations

import importlib

from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.mdr_gnb.abstain import AbstainDecision
from praxis_virtualcell.mdr_gnb.ensembler import EnsembleResult
from praxis_virtualcell.mdr_gnb.predictors.registry import (
    PredictorRegistry,
    PredictorSpec,
)

import pytest

# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts

workflow = importlib.import_module(
    "praxis_virtualcell.mdr_gnb.workflows.run_mdr_query"
)


def _sir_raw(*, amr_profile: dict | None = None) -> dict:
    return {
        "species": "escherichia_coli",
        "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenems"}],
        "requested_outputs": ["SIR"],
        "amr_profile": {"blaKPC-2": True} if amr_profile is None else amr_profile,
    }


def _registry_with_prediction(
    *,
    output_kind: str = "sir_class",
    prediction: dict | None = None,
) -> PredictorRegistry:
    registry = PredictorRegistry()
    if prediction is None:
        prediction = {
            "abstained": False,
            "output_kind": "sir_class",
            "sir": "S",
            "sir_prob": {"S": 0.9, "I": 0.0, "R": 0.1},
        }

    registry.register(
        PredictorSpec(
            name="production_mutation_predictor",
            version="test",
            species=["escherichia_coli"],
            drug_class=["*"],
            output_kind=output_kind,
            artifact_path="test://production-mutation",
            predict=lambda _ctx: dict(prediction),
        )
    )
    return registry


def _run_sir(registry: PredictorRegistry, *, seed: str, amr_profile: dict | None = None):
    return workflow.run_mdr_query(
        _sir_raw(amr_profile=amr_profile),
        seed_task_id=seed,
        registry=registry,
    )


def test_production_guard_detects_predict_before_retrieve(monkeypatch):
    """A corrupted trace ordering must not make retrieve-before-predict invisible."""

    class ReorderedTraceBus(workflow.MessageBus):
        def record_trace(self, message):
            super().record_trace(message)
            if message.message_type == "predictor_result":
                for index, prior in enumerate(self._trace):
                    if prior.message_type == "brain_retrieved":
                        self._trace.append(self._trace.pop(index))
                        break

    monkeypatch.setattr(workflow, "MessageBus", ReorderedTraceBus)
    out = _run_sir(_registry_with_prediction(), seed="guard-retrieve")

    assert "predict_before_retrieve" in out["report"]["critic_violations"]


def test_production_guard_detects_prediction_without_predictor(monkeypatch):
    """An aggregator regression with an output but no contributing model is caught."""

    def _corrupt_aggregate(_results):
        return EnsembleResult(
            output_kind="sir_class",
            ensemble={"sir": "S", "sir_prob": {"S": 0.9, "I": 0.0, "R": 0.1}},
            disagreement={"score": 0.0, "n_models": 0},
            models_used=[],
        )

    monkeypatch.setattr(workflow, "aggregate", _corrupt_aggregate)
    out = _run_sir(_registry_with_prediction(), seed="guard-no-model")

    assert "prediction_without_predictor" in out["report"]["critic_violations"]


def test_production_guard_detects_abstain_with_prediction(monkeypatch):
    """An abstain decision may not retain an upstream ensemble silently."""

    monkeypatch.setattr(
        workflow,
        "evaluate_abstain",
        lambda _ctx: AbstainDecision(True, ["forced_mutation_abstain"]),
    )
    out = _run_sir(_registry_with_prediction(), seed="guard-abstain")

    assert out["report"]["abstained"] is True
    assert "abstain_inconsistent_with_prediction" in out["report"]["critic_violations"]


def test_production_guard_detects_breakpoint_version_mismatch(monkeypatch):
    """A species-brain breakpoint regression is audited after the normal route."""

    class OldBreakpointAgent:
        name = "OldBreakpointAgent"

        def __init__(self, *, clock, idgen, **_kwargs):
            self.clock = clock
            self.idgen = idgen

        def handle(self, message, bus):
            bus.send(
                AgentMessage(
                    self.idgen.next(),
                    self.name,
                    "PredictorHub",
                    "brain_retrieved",
                    {
                        "request": message.payload["request"],
                        "brain_context": {
                            "species": "escherichia_coli",
                            "rules_referenced": ["test://brain-rules"],
                            "species_specific_breakpoints": {
                                "meropenem": {"source": "EUCAST v13.0"}
                            },
                        },
                    },
                    self.clock.now(),
                    parent_message_id=message.message_id,
                )
            )

    monkeypatch.setitem(workflow._AGENTS, "escherichia_coli", OldBreakpointAgent)
    out = _run_sir(_registry_with_prediction(), seed="guard-breakpoint")

    assert "breakpoint_version_mismatch" in out["report"]["critic_violations"]


def test_production_guard_detects_genotype_conclusion_contradiction(monkeypatch):
    """Rule-first fusion remains the actual conclusion inspected by the critic."""
    from praxis_virtualcell.mdr_gnb.coordinator import fusion

    def _force_resistant(result, **_kwargs):
        return {
            **result,
            "sir": "R",
            "fusion": {"method": "forced_mutation", "rule_pred": "R"},
        }

    monkeypatch.setattr(fusion, "fuse_sir", _force_resistant)
    out = _run_sir(
        _registry_with_prediction(),
        seed="guard-genotype",
        amr_profile={},
    )

    assert "genotype_conclusion_contradiction" in out["report"]["critic_violations"]


def test_production_guard_detects_missing_required_provenance(monkeypatch):
    """A catalog/provenance read failure cannot be masked by an arbitrary dict."""
    runtime_manifest = importlib.import_module(
        "praxis_virtualcell.model_zoo.runtime_manifest"
    )

    def _catalog_unavailable():
        raise RuntimeError("forced catalog unavailability")

    monkeypatch.setattr(runtime_manifest, "get_runtime_manifest", _catalog_unavailable)
    out = _run_sir(_registry_with_prediction(), seed="guard-provenance")

    assert "missing_provenance" in out["report"]["critic_violations"]


def test_production_guard_detects_mechanism_claim_without_g3():
    """A mechanism sidecar may not make an unqualified G3 claim."""
    registry = _registry_with_prediction(
        output_kind="sm_activity",
        prediction={
            "abstained": False,
            "output_kind": "sm_activity",
            "log10_mic": 0.3,
            "mic_ug_ml": 2.0,
            "max_tanimoto": 0.8,
            "is_ood": False,
        },
    )
    raw = {
        "species": "escherichia_coli",
        "drug_panel": [{"drug": "trimethoprim", "drug_class": "antimetabolites"}],
        "requested_outputs": ["activity"],
        "amr_profile": {"folA": True},
    }

    out = workflow.run_mdr_query(
        raw,
        seed_task_id="guard-mechanism",
        registry=registry,
        fuse_mech=lambda _species, _drug: {
            "available": True,
            "g3_gate": {"status": "not_evaluated", "claim_allowed": False},
            "mechanism_claim": "forced unsupported mechanism claim",
        },
    )

    assert "mechanism_claim_without_g3" in out["report"]["critic_violations"]
