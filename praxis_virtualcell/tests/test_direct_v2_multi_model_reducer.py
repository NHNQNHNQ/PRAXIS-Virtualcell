"""Generic U2 conformance: a reducer must be explicit, bound, and auditable."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest

from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Clock, IdGen, RuntimeConfig
from praxis_virtualcell.core.runtime import AgentRuntime, _aggregate_execution_scope
from praxis_virtualcell.model_zoo.adapter_sdk import (
    AdapterContractError,
    AdapterExecutionProvenance,
    AdapterOutputEnvelope,
    AdapterRegistry,
)
from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.capability_registry import ExecutionPlanV3
from praxis_virtualcell.model_zoo.post_result_policy import (
    OutputReducerBindingV1,
    OutputReducerModelAdapterBindingV1,
    OutputReducerPolicyNotFoundError,
    OutputReducerPolicyRegistry,
    OutputReducerPolicySpecV1,
    OutputReducerReceiptV1,
    OutputReducerStepReceiptV1,
    reducer_implementation_fingerprint,
)
from praxis_virtualcell.model_zoo.wrapper_registry import WrapperRegistry
from praxis_virtualcell.tests.test_capability_runtime import (
    _MODEL_BYTES,
    _TEST_ARTIFACT_SNAPSHOT_BUDGET,
    _card,
    _pack_registry,
    _v2_registry_and_environment,
    _write_registry,
)
from praxis_virtualcell.tests.test_direct_v2_single_model import (
    _pack_bound_request,
    _PathlessPackAdapter,
    _ScalarAdapter,
    _ScalarWrapper,
)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _mean_two_scalar_envelopes(
    outputs: tuple[AdapterOutputEnvelope, ...],
) -> AdapterOutputEnvelope:
    """A module-level, generic reducer used only by U2 conformance fixtures."""

    first, second = outputs
    value = (float(first.values[0]) + float(second.values[0])) / 2.0
    return AdapterOutputEnvelope(
        schema_version="vc.adapter-output-envelope.v1",
        task=first.task,
        output=first.output,
        shape=first.shape,
        unit=first.unit,
        values=(value,),
        uncertainty=None,
        ood=None,
        abstain=False,
        abstain_reasons=(),
        projection_metadata={"fixture": "test-only-reducer"},
        provenance=AdapterExecutionProvenance(
            schema_version="vc.adapter-execution-provenance.v1",
            adapter_fingerprint=first.provenance.adapter_fingerprint,
            input_fingerprints=(
                first.provenance.input_fingerprints[0],
                second.provenance.input_fingerprints[0],
            ),
            input_contract_fingerprint=first.provenance.input_contract_fingerprint,
            output_contract_fingerprint=first.provenance.output_contract_fingerprint,
            request_fingerprints=tuple(
                dict.fromkeys(
                    (
                        first.provenance.request_fingerprints[0],
                        second.provenance.request_fingerprints[0],
                    )
                )
            ),
            pack_fingerprints=tuple(
                dict.fromkeys((*first.provenance.pack_fingerprints, *second.provenance.pack_fingerprints))
            ),
            compatibility_fingerprints=(
                first.provenance.compatibility_fingerprints[0],
                second.provenance.compatibility_fingerprints[0],
            ),
        ),
    )


def _same_mean_with_different_source(
    outputs: tuple[AdapterOutputEnvelope, ...],
) -> AdapterOutputEnvelope:
    """Semantically similar fixture with a deliberately different source hash."""

    return _mean_two_scalar_envelopes(outputs)


def _wrong_unit_two_scalar_envelopes(
    outputs: tuple[AdapterOutputEnvelope, ...],
) -> AdapterOutputEnvelope:
    value = _mean_two_scalar_envelopes(outputs)
    return value.model_copy(update={"unit": "wrong-unit"})


def _abstaining_two_scalar_envelopes(
    outputs: tuple[AdapterOutputEnvelope, ...],
) -> AdapterOutputEnvelope:
    value = _mean_two_scalar_envelopes(outputs)
    return value.model_copy(
        update={
            "values": None,
            "shape": None,
            "abstain": True,
            "abstain_reasons": ("test-only-reducer-abstention",),
        }
    )


class _SecondScalarWrapper(_ScalarWrapper):
    def run_prediction(self, model_input: dict) -> dict:
        self.calls += 1
        assert model_input["request_id"] == "direct-v2-public-contract"
        return {"value": 0.75}


class _TwoValueScalarAdapter(_PathlessPackAdapter):
    def adapt_output(self, prepared, raw_output):
        if set(raw_output) != {"value"} or raw_output["value"] not in {0.25, 0.75}:
            raise AssertionError("the synthetic wrappers returned unexpected output")
        output = super().adapt_output(prepared, {"value": 0.25})
        return output.model_copy(update={"values": (float(raw_output["value"]),)})


def _two_model_runtime(
    tmp_path,
    *,
    reducer_registry: OutputReducerPolicyRegistry | None,
    domain_extensions=(),
    snapshot_budget: dict | None = None,
):
    """Build a real generic Broker chain with two exact synthetic models."""

    tmp_path.mkdir(parents=True, exist_ok=True)
    request = _pack_bound_request()
    first_card = _card()
    first_card.update(
        {
            "name": "test_only_direct_v2_scalar_one",
            "wrapper": f"{_ScalarWrapper.__module__}.{_ScalarWrapper.__qualname__}",
            "task": "test_scalar_task",
            "output": ["test_output"],
        }
    )
    second_card = deepcopy(first_card)
    second_card.update(
        {
            "name": "test_only_direct_v2_scalar_two",
            "wrapper": f"{_SecondScalarWrapper.__module__}.{_SecondScalarWrapper.__qualname__}",
        }
    )
    packs = _pack_registry()
    pack = packs.record("tiny-human-scrna", "0.1.0")
    adapter = _TwoValueScalarAdapter()
    first_registry, environment = _v2_registry_and_environment(
        first_card,
        pack.fingerprint,
        promoted=False,
        runtime_adapter=adapter,
        research_execution_authorized=True,
        runtime_tasks=("test_scalar_task",),
        runtime_outputs=("test_output",),
        identity_suffix="one",
        snapshot_budget=_TEST_ARTIFACT_SNAPSHOT_BUDGET if snapshot_budget is None else snapshot_budget,
    )
    second_registry, _ = _v2_registry_and_environment(
        second_card,
        pack.fingerprint,
        promoted=False,
        runtime_adapter=adapter,
        research_execution_authorized=True,
        runtime_tasks=("test_scalar_task",),
        runtime_outputs=("test_output",),
        identity_suffix="two",
        snapshot_budget=_TEST_ARTIFACT_SNAPSHOT_BUDGET if snapshot_budget is None else snapshot_budget,
    )
    first_root = tmp_path / "one"
    second_root = tmp_path / "two"
    first_root.mkdir()
    second_root.mkdir()
    first_zoo = _write_registry(first_root, first_card, registry_v2=first_registry)
    second_zoo = _write_registry(second_root, second_card, registry_v2=second_registry)
    from praxis_virtualcell.model_zoo.registry import ModelZooRegistry

    zoo = ModelZooRegistry.from_components(first_zoo, second_zoo)
    cache = ModelCache(root=str(tmp_path / "cache"))
    for name in zoo.capability_names():
        asset_path = cache.asset_path(name, "model.bin")
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        asset_path.write_bytes(_MODEL_BYTES)
    wrappers = WrapperRegistry()
    wrappers.register(first_card["wrapper"], _ScalarWrapper)
    wrappers.register(second_card["wrapper"], _SecondScalarWrapper)
    broker = ModelBrokerAgent(
        registry=zoo,
        cache=cache,
        pack_registry=packs,
        environment=environment,
        adapter_registry=AdapterRegistry([adapter]),
        wrapper_registry=wrappers,
        output_reducer_registry=reducer_registry,
    )
    runtime = AgentRuntime(
        RuntimeConfig(),
        bus=MessageBus(),
        clock=Clock(),
        idgen=IdGen(),
        domain_extensions=domain_extensions,
    )
    runtime.register_agent(broker)
    return request, runtime, adapter, zoo


def _reducer_policy(
    zoo,
    adapter: _TwoValueScalarAdapter,
    reducer,
    *,
    policy_id: str,
) -> OutputReducerPolicySpecV1:
    bindings = tuple(
        OutputReducerModelAdapterBindingV1(
            schema_version="vc.output-reducer-model-adapter-binding.v1",
            model_name=name,
            model_fingerprint=zoo.card(name).fingerprint(),
            release_fingerprint=next(
                release.fingerprint() for release in zoo.registry_v2.releases if release.model_name == name
            ),
            adapter_fingerprint=adapter.fingerprint(),
        )
        for name in zoo.capability_names()
    )
    return OutputReducerPolicySpecV1(
        schema_version="vc.output-reducer-policy.v1",
        policy_id=policy_id,
        policy_version="1.0.0",
        entrypoint=f"{reducer.__module__}.{reducer.__qualname__}",
        implementation_fingerprint=reducer_implementation_fingerprint(reducer),
        task="test_scalar_task",
        output_contract_fingerprint=adapter.output_contract.fingerprint(),
        model_adapter_bindings=bindings,
        model_count=2,
    )


def _runtime_with_mean_policy(tmp_path, *, domain_extensions=(), snapshot_budget: dict | None = None):
    request, runtime, adapter, zoo = _two_model_runtime(
        tmp_path,
        reducer_registry=None,
        domain_extensions=domain_extensions,
        snapshot_budget=snapshot_budget,
    )
    policy = _reducer_policy(
        zoo,
        adapter,
        _mean_two_scalar_envelopes,
        policy_id="test-only-mean-two-scalars",
    )
    reducers = OutputReducerPolicyRegistry()
    reducers.register(policy, _mean_two_scalar_envelopes)
    # Rebuild the same generic dependencies with the explicit policy registry;
    # no runtime discovers a reducer from the request.
    request, runtime, adapter, zoo = _two_model_runtime(
        tmp_path / "bound",
        reducer_registry=reducers,
        domain_extensions=domain_extensions,
        snapshot_budget=snapshot_budget,
    )
    return (
        request,
        runtime,
        adapter,
        zoo,
        _reducer_policy(
            zoo,
            adapter,
            _mean_two_scalar_envelopes,
            policy_id="test-only-mean-two-scalars",
        ),
    )


def _mean_not_executed(_outputs):
    raise AssertionError("this test only validates reducer policy identity")


def _binding(
    name: str,
    model: str,
    release: str,
    adapter: str,
) -> OutputReducerModelAdapterBindingV1:
    return OutputReducerModelAdapterBindingV1(
        schema_version="vc.output-reducer-model-adapter-binding.v1",
        model_name=name,
        model_fingerprint=model,
        release_fingerprint=release,
        adapter_fingerprint=adapter,
    )


def _policy(bindings: tuple[OutputReducerModelAdapterBindingV1, ...]) -> OutputReducerPolicySpecV1:
    return OutputReducerPolicySpecV1(
        schema_version="vc.output-reducer-policy.v1",
        policy_id="test-only-mean",
        policy_version="1.0.0",
        entrypoint=f"{__name__}._mean_not_executed",
        implementation_fingerprint=reducer_implementation_fingerprint(_mean_not_executed),
        task="test_scalar_task",
        output_contract_fingerprint="a" * 64,
        model_adapter_bindings=bindings,
        model_count=2,
    )


def test_u2_requires_an_explicit_ordered_generic_reducer_policy() -> None:
    first = _binding("test_scalar_one", "1" * 64, "3" * 64, "a" * 64)
    second = _binding("test_scalar_two", "2" * 64, "4" * 64, "a" * 64)
    registry = OutputReducerPolicyRegistry()

    with pytest.raises(OutputReducerPolicyNotFoundError):
        registry.resolve(
            task="test_scalar_task",
            output_contract_fingerprint="a" * 64,
            model_adapter_bindings=(first, second),
        )

    policy = _policy((first, second))
    registry.register(policy, _mean_not_executed)
    resolved = registry.resolve(
        task="test_scalar_task",
        output_contract_fingerprint="a" * 64,
        model_adapter_bindings=(first, second),
    )

    assert resolved.binding() == OutputReducerBindingV1(
        schema_version="vc.output-reducer-binding.v1",
        policy_id="test-only-mean",
        policy_version="1.0.0",
        policy_fingerprint=policy.fingerprint(),
    )
    with pytest.raises(OutputReducerPolicyNotFoundError):
        registry.resolve(
            task="test_scalar_task",
            output_contract_fingerprint="a" * 64,
            model_adapter_bindings=(second, first),
        )


def test_output_reducer_public_contracts_reject_rooted_path_identifiers() -> None:
    """Reducer identity and receipt fields must be safe to return publicly."""

    first = _binding("test_scalar_one", "1" * 64, "3" * 64, "a" * 64)
    second = _binding("test_scalar_two", "2" * 64, "4" * 64, "a" * 64)
    binding = _policy((first, second)).binding()

    raw_binding = binding.to_dict()
    raw_binding["policy_version"] = "/private/reducer-version"
    with pytest.raises(ValueError, match="path-safe"):
        OutputReducerBindingV1.from_dict(raw_binding)

    raw_model_binding = first.to_dict()
    raw_model_binding["model_name"] = "/private/reducer-source.py"
    with pytest.raises(ValueError, match="path-safe"):
        OutputReducerModelAdapterBindingV1.from_dict(raw_model_binding)

    raw_receipt = OutputReducerReceiptV1(
        schema_version="vc.output-reducer-receipt.v1",
        output_reducer=binding,
        step_receipts=(
            OutputReducerStepReceiptV1(
                schema_version="vc.output-reducer-step-receipt.v1",
                model_name="test_scalar_one",
                execution_step_fingerprint="1" * 64,
                input_hash="2" * 64,
                output_hash="3" * 64,
            ),
            OutputReducerStepReceiptV1(
                schema_version="vc.output-reducer-step-receipt.v1",
                model_name="test_scalar_two",
                execution_step_fingerprint="4" * 64,
                input_hash="5" * 64,
                output_hash="6" * 64,
            ),
        ),
        reduced_output_hash="7" * 64,
    ).to_dict()
    raw_receipt["step_receipts"][0]["model_name"] = "/private/reducer-source.py"
    with pytest.raises(ValueError, match="path-safe"):
        OutputReducerReceiptV1.from_dict(raw_receipt)


def test_execution_plan_v3_is_a_write_new_reducer_bound_contract() -> None:
    assert "vc.execution-plan.v3" in str(ExecutionPlanV3.model_fields["schema_version"].annotation)


def test_any_research_model_keeps_a_reduced_output_research_only() -> None:
    class Report:
        def __init__(self, research: bool) -> None:
            self.research_execution_authorized = research

    assert _aggregate_execution_scope([Report(False), Report(True)]) == "research_only"
    assert _aggregate_execution_scope([Report(False), Report(False)]) == "production"


def test_reducer_output_must_pass_the_registered_adapter_contract() -> None:
    """Red evidence: generic reducer output cannot bypass adapter validation."""

    request = _pack_bound_request()
    adapter = _ScalarAdapter()
    prepared_one = adapter.prepare_input(
        request,
        pack=type("Pack", (), {"fingerprint": "1" * 64})(),
        compatibility_report=type("Report", (), {"fingerprint": lambda self: "2" * 64})(),
    )
    prepared_two = prepared_one.model_copy(update={"compatibility_fingerprint": "3" * 64})
    first = adapter.adapt_output(prepared_one, {"value": 0.25})
    second = adapter.adapt_output(prepared_two, {"value": 0.25}).model_copy(update={"values": (0.75,)})
    candidate = _wrong_unit_two_scalar_envelopes((first, second))

    with pytest.raises(AdapterContractError):
        adapter.validate_envelope(candidate)


def test_direct_v2_two_generic_models_require_an_exact_reducer_before_preparation(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, runtime, _adapter, _zoo = _two_model_runtime(
        tmp_path,
        reducer_registry=None,
    )
    broker = runtime._agents["ModelBrokerAgent"]
    calls: list[object] = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("a missing reducer must stop before wrapper preparation")

    monkeypatch.setattr(broker._capabilities, "instantiate", forbidden)

    report = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert calls == []
    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["provenance"]["execution_plan"]["schema_version"] == "vc.execution-plan.v2"
    assert report["provenance"]["execution_plan"]["steps"] == []
    assert "output_reducer_required" in report["abstain_reasons"]


@pytest.mark.parametrize(
    "budget",
    (
        {
            "schema_version": "vc.artifact-snapshot-budget-policy.v1",
            "max_live_snapshot_payload_bytes": len(_MODEL_BYTES) * 2 - 1,
            "max_snapshot_entries_per_execution": 2,
            "retention_scope": "execution_only",
        },
        {
            "schema_version": "vc.artifact-snapshot-budget-policy.v1",
            "max_live_snapshot_payload_bytes": len(_MODEL_BYTES) * 2,
            "max_snapshot_entries_per_execution": 1,
            "retention_scope": "execution_only",
        },
    ),
)
def test_direct_v2_reducer_budget_rejects_whole_plan_before_any_snapshot_or_wrapper(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    budget: dict,
) -> None:
    """Aggregate V3 budget is enforced before either model can prepare."""

    request, runtime, _adapter, _zoo, _policy = _runtime_with_mean_policy(
        tmp_path,
        snapshot_budget=budget,
    )
    broker = runtime._agents["ModelBrokerAgent"]

    def forbidden(*_args, **_kwargs):
        raise AssertionError("budget-exceeded plan must stop before wrapper preparation")

    monkeypatch.setattr(broker._capabilities, "instantiate", forbidden)
    report = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["provenance"]["execution_plan"]["steps"] == []
    assert "artifact.snapshot_budget_exceeded" in report["abstain_reasons"]


def test_direct_v2_two_generic_models_execute_only_through_bound_mean_reducer(
    tmp_path,
) -> None:
    request, runtime, _adapter, zoo, policy = _runtime_with_mean_policy(tmp_path)

    report = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    plan = report["provenance"]["execution_plan"]
    receipt = report["provenance"]["output_reducer_receipt"]
    expected_names = zoo.capability_names()
    assert report["abstain"] is False
    assert report["prediction"]["values"] == [0.5]
    assert report["models_used"] == expected_names
    assert report["execution_scope"] == "research_only"
    assert report["scientifically_validated"] is False
    assert plan["schema_version"] == "vc.execution-plan.v3"
    assert plan["output_reducer"] == policy.binding().to_dict()
    assert list(report["provenance"]["per_call_hashes"]) == expected_names
    assert receipt["output_reducer"] == policy.binding().to_dict()
    assert [item["model_name"] for item in receipt["step_receipts"]] == expected_names
    assert receipt["reduced_output_hash"] == _fingerprint(report["prediction"])
    public = json.dumps(report["provenance"], sort_keys=True)
    assert "entrypoint" not in public
    assert "_mean_two_scalar_envelopes" not in public


def test_direct_v2_reducer_order_drift_hard_abstains_before_wrapper_execution(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, runtime, adapter, zoo = _two_model_runtime(tmp_path, reducer_registry=None)
    correct = _reducer_policy(
        zoo,
        adapter,
        _mean_two_scalar_envelopes,
        policy_id="test-only-mean-two-scalars",
    )
    reversed_policy = correct.model_copy(
        update={"model_adapter_bindings": tuple(reversed(correct.model_adapter_bindings))}
    )
    reducers = OutputReducerPolicyRegistry()
    reducers.register(reversed_policy, _mean_two_scalar_envelopes)
    runtime._agents["ModelBrokerAgent"]._output_reducers = reducers
    broker = runtime._agents["ModelBrokerAgent"]
    calls: list[object] = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("an ordered reducer mismatch must stop before preparation")

    monkeypatch.setattr(broker._capabilities, "instantiate", forbidden)

    report = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert calls == []
    assert report["abstain"] is True
    assert report["prediction"] is None
    assert "output_reducer_required" in report["abstain_reasons"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("task", "wrong_task"),
        ("output_contract_fingerprint", "0" * 64),
    ],
)
def test_direct_v3_private_reducer_spec_drift_stops_before_wrapper_execution(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    request, runtime, _adapter, _zoo, _policy = _runtime_with_mean_policy(tmp_path)
    broker = runtime._agents["ModelBrokerAgent"]
    original_take = broker.take_prepared_v2
    calls: list[str] = []

    def tampered_take(plan_id: str):
        handoff = original_take(plan_id)
        object.__setattr__(handoff["output_reducer"].spec, field, value)
        for name, execution in handoff["executions"].items():
            execution["wrapper"].run_prediction = lambda _input, *, _name=name: calls.append(_name)
        return handoff

    monkeypatch.setattr(broker, "take_prepared_v2", tampered_take)
    report = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert calls == []
    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["models_used"] == []
    assert report["abstain_reasons"] == ["prepared_execution_invalid"]


def test_direct_v3_private_reducer_source_drift_stops_before_wrapper_execution(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, runtime, _adapter, _zoo, _policy = _runtime_with_mean_policy(tmp_path)
    broker = runtime._agents["ModelBrokerAgent"]
    original_take = broker.take_prepared_v2
    calls: list[str] = []

    def tampered_take(plan_id: str):
        handoff = original_take(plan_id)
        object.__setattr__(
            handoff["output_reducer"],
            "reducer",
            _same_mean_with_different_source,
        )
        for name, execution in handoff["executions"].items():
            execution["wrapper"].run_prediction = lambda _input, *, _name=name: calls.append(_name)
        return handoff

    monkeypatch.setattr(broker, "take_prepared_v2", tampered_take)
    report = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert calls == []
    assert report["abstain_reasons"] == ["prepared_execution_invalid"]


def test_direct_v3_revoked_reducer_policy_stops_before_wrapper_execution(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A prepared callable cannot outlive revocation from the explicit registry."""

    request, runtime, _adapter, _zoo, _policy = _runtime_with_mean_policy(tmp_path)
    broker = runtime._agents["ModelBrokerAgent"]
    original_take = broker.take_prepared_v2
    calls: list[str] = []

    def revoked_take(plan_id: str):
        handoff = original_take(plan_id)
        broker._output_reducers = OutputReducerPolicyRegistry()
        for name, execution in handoff["executions"].items():
            execution["wrapper"].run_prediction = lambda _input, *, _name=name: calls.append(_name)
        return handoff

    monkeypatch.setattr(broker, "take_prepared_v2", revoked_take)
    report = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert calls == []
    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["abstain_reasons"] == ["prepared_execution_invalid"]


@pytest.mark.parametrize(
    ("attribute", "value"),
    [
        ("name", "forged-model"),
        ("model_version", "999.0.0"),
        ("_capability_assets", {"model.bin": "/tmp/forged-model.bin"}),
    ],
)
def test_direct_v3_private_wrapper_identity_drift_stops_before_wrapper_execution(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    attribute: str,
    value: object,
) -> None:
    request, runtime, _adapter, _zoo, _policy = _runtime_with_mean_policy(tmp_path)
    broker = runtime._agents["ModelBrokerAgent"]
    original_take = broker.take_prepared_v2
    calls: list[str] = []

    def tampered_take(plan_id: str):
        handoff = original_take(plan_id)
        first = handoff["executions"]["test_only_direct_v2_scalar_one"]["wrapper"]
        setattr(first, attribute, value)
        for name, execution in handoff["executions"].items():
            execution["wrapper"].run_prediction = lambda _input, *, _name=name: calls.append(_name)
        return handoff

    monkeypatch.setattr(broker, "take_prepared_v2", tampered_take)
    report = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert calls == []
    assert report["abstain_reasons"] == ["prepared_execution_invalid"]


def test_direct_v2_second_model_preparation_failure_returns_v3_empty_plan(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, runtime, _adapter, _zoo, _policy = _runtime_with_mean_policy(tmp_path)
    broker = runtime._agents["ModelBrokerAgent"]
    original = broker._capabilities.instantiate
    calls: list[str] = []

    def fail_second(step, *args, **kwargs):
        calls.append(step.model_name)
        if step.model_name.endswith("_two"):
            raise RuntimeError("synthetic second wrapper failure")
        return original(step, *args, **kwargs)

    monkeypatch.setattr(broker._capabilities, "instantiate", fail_second)

    report = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    plan = report["provenance"]["execution_plan"]
    assert calls == ["test_only_direct_v2_scalar_one", "test_only_direct_v2_scalar_two"]
    assert report["abstain"] is True
    assert report["prediction"] is None
    assert plan["schema_version"] == "vc.execution-plan.v3"
    assert plan["steps"] == []
    assert all("runtime.preparation_failed" in item["reasons"] for item in plan["reports"])
    assert all("output_reducer_required" not in item["reasons"] for item in plan["reports"])
    assert "runtime.preparation_failed" in report["abstain_reasons"]
    assert "model.wrapper_initialization" in report["abstain_reasons"]


@pytest.mark.parametrize(
    ("reducer", "reason"),
    [
        (_wrong_unit_two_scalar_envelopes, "output_reducer_failed"),
        (_abstaining_two_scalar_envelopes, "output_reducer_abstained"),
    ],
)
def test_direct_v2_reducer_invalid_or_abstaining_output_hard_abstains(
    tmp_path,
    reducer,
    reason,
) -> None:
    request, runtime, adapter, zoo = _two_model_runtime(tmp_path, reducer_registry=None)
    policy = _reducer_policy(
        zoo,
        adapter,
        reducer,
        policy_id=f"test-only-{reducer.__name__}",
    )
    reducers = OutputReducerPolicyRegistry()
    reducers.register(policy, reducer)
    runtime._agents["ModelBrokerAgent"]._output_reducers = reducers

    report = runtime.run_workflow_v2(
        request,
        pack_id="tiny-human-scrna",
        pack_version="0.1.0",
    )

    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["models_used"] == []
    assert report["abstain_reasons"] == [reason]
    assert "output_reducer_receipt" not in report["provenance"]
