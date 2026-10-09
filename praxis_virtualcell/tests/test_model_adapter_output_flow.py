"""P13 strict adapter envelopes through wrapper, ensemble, and governance."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from praxis_virtualcell.agents.critic import CriticAgent
from praxis_virtualcell.agents.ensemble import EnsembleCoordinatorAgent, _flat_values
from praxis_virtualcell.agents.provenance_agent import ProvenanceAgent
from praxis_virtualcell.agents.reliability import ReliabilityAgent
from praxis_virtualcell.agents.report import ReportAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.core.request_v2 import legacy_request_to_v2
from praxis_virtualcell.governance.gate_util import apply_governance_gate
from praxis_virtualcell.model_zoo.adapter_sdk import (
    AdapterOutputContract,
    AdapterRegistry,
    DeltaExpressionReferenceAdapter,
)
from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper


def _request():
    return legacy_request_to_v2(
        VirtualCellRequest(
            request_id="p13-output-flow",
            species="human",
            perturbation_type="gene",
            perturbation_targets=["TP53"],
            input_modality="scRNA",
            output_modality="delta_expression",
            task_type="predict_delta_expression",
        )
    )


def _raw(values=(0.25, -0.5)):
    return {
        "prediction": {"delta": list(values)},
        "uncertainty": {
            "available": False,
            "method": "point_estimate",
            "calibrated": False,
            "reason": "no calibrated uncertainty",
        },
        "ood": {"detected": False, "dimensions": [], "reason": None},
    }


class _StrictWrapper(ModelWrapper):
    def declare_scope(self):
        return {}

    def run_prediction(self, model_input):
        self.seen_input = model_input
        return deepcopy(self.raw_output)


def _wrapper(raw=None, *, adapter=None, card=None):
    adapter = adapter or DeltaExpressionReferenceAdapter()
    prepared = adapter.prepare_input(_request())
    wrapper = _StrictWrapper.from_capability(
        card=card or SimpleNamespace(name="StrictWrapper", version="1.0.0"),
        compatibility_report=SimpleNamespace(executable=True),
        asset_paths={},
        runtime_adapter=adapter,
        prepared_input=prepared,
    )
    wrapper.raw_output = _raw() if raw is None else raw
    return wrapper, adapter, prepared


def _run_wrapper(wrapper):
    bus = MessageBus()
    bus.send(AgentMessage("brain", "SpeciesBrain", "x", "brain_retrieved", {}, "t"))
    wrapper.handle(
        AgentMessage(
            "predict",
            "test",
            wrapper.name,
            "predict",
            {"request": {"request_id": "p13-output-flow"}, "brain_context": {}},
            "t",
        ),
        bus,
    )
    return bus.latest("predictor_result").payload


def _strict_result(name, values):
    adapter = DeltaExpressionReferenceAdapter()
    envelope = adapter.adapt_output(adapter.prepare_input(_request()), _raw(values))
    return {
        "agent_name": name,
        "status": "success",
        "prediction": {"delta": list(values)},
        "uncertainty": _raw(values)["uncertainty"],
        "provenance": {"adapter_output": envelope.to_dict()},
    }


def _ensemble(results, *, adapter_registry=None):
    bus = MessageBus()
    EnsembleCoordinatorAgent(adapter_registry=adapter_registry).handle(
        AgentMessage(
            "m",
            "test",
            "EnsembleCoordinator",
            "ensemble",
            {"request": {}, "brain_context": {}, "results": results},
            "t",
        ),
        bus,
    )
    return bus.latest("ensemble_done").payload


def test_wrapper_uses_broker_prepared_input_and_emits_envelope_only_in_provenance():
    wrapper, adapter, prepared = _wrapper()
    assert wrapper.prepare_input(
        {"request_id": "p13-output-flow"}, {}
    ) == prepared.model_input
    with pytest.raises(ValueError, match="request_id"):
        wrapper.prepare_input({"request_id": "different"}, {})

    bus = MessageBus()
    bus.send(AgentMessage("brain", "SpeciesBrain", "x", "brain_retrieved", {}, "t"))
    wrapper.handle(
        AgentMessage(
            "predict",
            "test",
            wrapper.name,
            "predict",
            {"request": {"request_id": "p13-output-flow"}, "brain_context": {}},
            "t",
        ),
        bus,
    )
    result = bus.latest("predictor_result").payload
    assert result["status"] == "success"
    assert "adapter_output" not in result
    assert result["provenance"]["adapter_output"]["provenance"][
        "adapter_fingerprint"
    ] == adapter.fingerprint()


def test_wrapper_contract_failure_is_rejected_instead_of_failed():
    wrapper, _, _ = _wrapper(_raw((float("nan"),)))
    bus = MessageBus()
    bus.send(AgentMessage("brain", "SpeciesBrain", "x", "brain_retrieved", {}, "t"))
    wrapper.handle(
        AgentMessage(
            "predict",
            "test",
            wrapper.name,
            "predict",
            {"request": {"request_id": "p13-output-flow"}, "brain_context": {}},
            "t",
        ),
        bus,
    )
    result = bus.latest("predictor_result").payload
    assert result["status"] == "rejected"
    assert result["rejection_reason"] == "runtime_output_adapter_contract"


def test_strict_wrapper_preserves_adapter_abstention_provenance():
    raw = _raw()
    raw.update(
        prediction=None,
        abstain=True,
        abstain_reasons=["test-only abstention"],
    )
    wrapper, _, _ = _wrapper(raw)
    result = _run_wrapper(wrapper)
    assert result["status"] == "rejected"
    assert result["rejection_reason"] == "runtime_adapter_abstained"
    assert result["provenance"]["adapter_output"]["abstain"] is True


def test_strict_wrapper_delegates_omitted_prediction_to_adapter_abstention():
    raw = _raw()
    del raw["prediction"]
    raw.update(abstain=True, abstain_reasons=["test-only abstention"])
    wrapper, _, _ = _wrapper(raw)
    result = _run_wrapper(wrapper)
    assert result["status"] == "rejected"
    assert result["rejection_reason"] == "runtime_adapter_abstained"
    assert result["provenance"]["adapter_output"]["abstain"] is True


class _OptionalUncertaintyAdapter(DeltaExpressionReferenceAdapter):
    adapter_id = "test-only-optional-uncertainty"
    output_contract = AdapterOutputContract(
        schema_version="vc.adapter-output-contract.v1",
        task="predict_delta_expression",
        output="delta_expression",
        value_type="float",
        shape=(None,),
        unit=None,
        uncertainty_required=False,
        ood_required=True,
        abstain_allowed=True,
    )


@pytest.mark.parametrize(
    ("adapter", "raw", "uncertainty_contract", "reason"),
    [
        (
            _OptionalUncertaintyAdapter(),
            {key: value for key, value in _raw().items() if key != "uncertainty"},
            SimpleNamespace(
                required=True,
                methods=("approved_method",),
                calibrated=False,
            ),
            "uncertainty_contract_missing",
        ),
        (
            DeltaExpressionReferenceAdapter(),
            _raw(),
            SimpleNamespace(
                required=True,
                methods=("approved_method",),
                calibrated=False,
            ),
            "uncertainty_contract_method",
        ),
        (
            DeltaExpressionReferenceAdapter(),
            _raw(),
            SimpleNamespace(
                required=True,
                methods=("point_estimate",),
                calibrated=True,
            ),
            "uncertainty_contract_calibration",
        ),
    ],
)
def test_strict_wrapper_enforces_model_card_uncertainty(
    adapter,
    raw,
    uncertainty_contract,
    reason,
):
    card = SimpleNamespace(
        name="StrictWrapper",
        version="1.0.0",
        uncertainty=uncertainty_contract,
    )
    wrapper, _, _ = _wrapper(raw, adapter=adapter, card=card)
    result = _run_wrapper(wrapper)
    assert result["status"] == "rejected"
    assert result["rejection_reason"] == reason


class _StaleProvenanceAdapter(DeltaExpressionReferenceAdapter):
    adapter_id = "test-only-stale-provenance"

    def adapt_output(self, prepared, raw_output):
        envelope = super().adapt_output(prepared, raw_output)
        provenance = envelope.provenance.model_copy(
            update={"request_fingerprints": ("f" * 64,)}
        )
        return envelope.model_copy(update={"provenance": provenance})


def test_strict_wrapper_rejects_cross_request_adapter_provenance():
    wrapper, _, _ = _wrapper(_raw(), adapter=_StaleProvenanceAdapter())
    result = _run_wrapper(wrapper)
    assert result["status"] == "rejected"
    assert result["rejection_reason"] == "runtime_output_adapter_contract"


def test_strict_wrapper_rejects_unsafe_projection_metadata_before_public_report():
    wrapper, adapter, _ = _wrapper(_raw())
    original = adapter.adapt_output
    secret = "/private/test-pack-root/model.bin"

    def unsafe_output(prepared_input, raw_output):
        return original(prepared_input, raw_output).model_copy(
            update={"projection_metadata": {"local_path": secret}}
        )

    adapter.adapt_output = unsafe_output
    result = _run_wrapper(wrapper)

    assert result["status"] == "rejected"
    assert result["rejection_reason"] == "runtime_output_adapter_contract"
    assert secret not in str(result)


def test_legacy_ensemble_shape_and_fields_are_unchanged():
    result = {
        "agent_name": "legacy",
        "status": "success",
        "prediction": {"delta": [1.0, 3.0], "baseline": "x"},
        "uncertainty": {"sigma": 0.1},
        "provenance": {},
    }
    payload = _ensemble([result])
    assert payload["ensemble"] == {"delta": [1.0, 3.0], "baseline": "x"}
    assert payload["models_used"] == ["legacy"]
    assert "adapter_output" not in payload


def test_strict_single_and_two_model_outputs_use_registered_adapter_projection():
    one = _ensemble([_strict_result("one", (1.0, 3.0))])
    assert one["ensemble"] == {"delta": [1.0, 3.0]}
    assert one["adapter_output"]["values"] == [1.0, 3.0]

    two = _ensemble(
        [_strict_result("one", (1.0, 3.0)), _strict_result("two", (3.0, 5.0))]
    )
    assert two["models_used"] == ["one", "two"]
    assert two["ensemble"] == {"delta": [2.0, 4.0]}
    assert two["adapter_output"]["values"] == [2.0, 4.0]
    assert two["disagreement"]["n_models"] == 2


def test_mixed_or_fingerprint_mismatched_outputs_fail_closed():
    strict = _strict_result("strict", (1.0, 2.0))
    legacy = {
        "agent_name": "legacy",
        "status": "success",
        "prediction": {"delta": [1.0, 2.0]},
        "uncertainty": {"sigma": 0.1},
        "provenance": {},
    }
    mixed = _ensemble([strict, legacy])
    assert mixed["models_used"] == []
    assert mixed["models_rejected"] == ["strict", "legacy"]
    assert mixed["ensemble"] is None
    assert "adapter_output" not in mixed

    mismatched = deepcopy(_strict_result("other", (1.0, 2.0)))
    mismatched["provenance"]["adapter_output"]["provenance"][
        "adapter_fingerprint"
    ] = "f" * 64
    invalid = _ensemble([strict, mismatched])
    assert invalid["models_used"] == []
    assert invalid["ensemble"] is None

    unregistered = _ensemble([strict], adapter_registry=AdapterRegistry())
    assert unregistered["models_used"] == []
    assert unregistered["ensemble"] is None


@pytest.mark.parametrize(
    "malformation",
    ["unit", "shape", "values", "uncertainty", "ood"],
)
def test_ensemble_rejects_malformed_adapter_envelopes(malformation):
    strict = _strict_result("strict", (1.0, 2.0))
    envelope = strict["provenance"]["adapter_output"]
    if malformation == "unit":
        envelope["unit"] = "count"
    elif malformation == "shape":
        envelope["shape"] = [1]
    elif malformation == "values":
        envelope["values"] = [float("nan"), 2.0]
    else:
        envelope[malformation] = None
    payload = _ensemble([strict])
    assert payload["models_used"] == []
    assert payload["ensemble"] is None
    assert "adapter_output" not in payload


class _ExplodingAggregateAdapter(DeltaExpressionReferenceAdapter):
    adapter_id = "test-only-exploding-aggregate"

    def aggregate(self, envelopes):
        raise RuntimeError("test-only adapter failure")


def test_ensemble_fault_isolates_unexpected_adapter_aggregate_errors():
    adapter = _ExplodingAggregateAdapter()
    envelope = adapter.adapt_output(adapter.prepare_input(_request()), _raw())
    result = {
        "agent_name": "strict",
        "status": "success",
        "prediction": {"delta": [0.25, -0.5]},
        "uncertainty": _raw()["uncertainty"],
        "provenance": {"adapter_output": envelope.to_dict()},
    }
    payload = _ensemble([result], adapter_registry=AdapterRegistry([adapter]))
    assert payload["models_used"] == []
    assert payload["ensemble"] is None


class _ReservedProjectionAdapter(DeltaExpressionReferenceAdapter):
    adapter_id = "test-only-reserved-projection"

    def project_output(self, envelope):
        self.validate_envelope(envelope)
        return {"production_promoted": True}


def test_ensemble_rejects_adapter_issued_policy_projection():
    adapter = _ReservedProjectionAdapter()
    envelope = adapter.adapt_output(adapter.prepare_input(_request()), _raw())
    result = {
        "agent_name": "strict",
        "status": "success",
        "prediction": {"delta": [0.25, -0.5]},
        "uncertainty": _raw()["uncertainty"],
        "provenance": {"adapter_output": envelope.to_dict()},
    }
    payload = _ensemble([result], adapter_registry=AdapterRegistry([adapter]))
    assert payload["models_used"] == []
    assert payload["ensemble"] is None


def test_disagreement_flattening_accepts_json_nested_arrays():
    assert _flat_values([[1.0, 2.0], [3.0, 4.0]]) == [1.0, 2.0, 3.0, 4.0]


def test_strict_fields_are_conditional_and_critic_uses_envelope_uncertainty_contract():
    strict = _strict_result("strict", (1.0, 2.0))
    payload = {
        "request": {"species": "human"},
        "brain_context": {"rules_referenced": ["rule"]},
        "results": [strict],
        "models_used": ["strict"],
        "models_rejected": [],
        "models_failed": [],
        "ensemble": {"delta": [1.0, 2.0]},
        "adapter_output": strict["provenance"]["adapter_output"],
        "reliability_decision": {"abstain": False, "reliability": "medium", "reasons": []},
    }
    bus = MessageBus()
    CriticAgent().handle(
        AgentMessage("c", "Reliability", "Critic", "review", payload, "t"), bus
    )
    critic_payload = bus.latest("critic_done").payload
    assert not any(
        item.startswith("missing_uncertainty")
        for item in critic_payload["critic_violations"]
    )

    ProvenanceAgent().handle(
        AgentMessage("p", "Critic", "ProvenanceAgent", "assemble", critic_payload, "t"),
        bus,
    )
    provenance_payload = bus.latest("provenance_done").payload
    assert provenance_payload["provenance"]["adapter_outputs"]["strict"]
    ReportAgent().handle(
        AgentMessage("r", "ProvenanceAgent", "Report", "render", provenance_payload, "t"),
        bus,
    )
    assert bus.latest("report_done").payload["report"]["adapter_output"]

    legacy_payload = {**payload, "results": [], "adapter_output": None}
    ProvenanceAgent().handle(
        AgentMessage("l", "Critic", "ProvenanceAgent", "assemble", legacy_payload, "t"),
        bus,
    )
    assert "adapter_outputs" not in bus.latest("provenance_done").payload["provenance"]


def test_governance_override_clears_public_adapter_output_but_keeps_audit_copy():
    envelope = _strict_result("strict", (1.0, 2.0))["provenance"]["adapter_output"]
    report = {
        "abstain": False,
        "prediction": {"delta": [1.0, 2.0]},
        "adapter_output": envelope,
        "provenance": {"adapter_output": envelope},
    }
    assert apply_governance_gate(report, "gate", "test_gate", {}) is True
    assert report["prediction"] is None
    assert report["adapter_output"] is None
    assert report["provenance"]["adapter_output"] == envelope


def test_non_delta_adapter_output_never_uses_delta_trained_learned_reliability():
    bus = MessageBus()
    ReliabilityAgent(mode="learned").handle(
        AgentMessage(
            "growth",
            "EnsembleCoordinator",
            "Reliability",
            "assess",
            {
                "request": {"perturbation_targets": ["b0001"]},
                "brain_context": {"generic": {}},
                "results": [],
                "models_used": ["growth-model"],
                "ensemble": {"growth": [1.0]},
                "disagreement": {
                    "score": None,
                    "metric": "pairwise_cosine_distance",
                    "n_models": 1,
                },
                "adapter_output": {
                    "task": "predict_growth",
                    "output": "growth",
                },
            },
            "t",
        ),
        bus,
    )

    payload = bus.latest("reliability_decided").payload
    assert payload["learned_reliability"] == {
        "reliability_mode": "learned",
        "fallback": True,
        "reason": "unsupported_adapter_output",
    }
