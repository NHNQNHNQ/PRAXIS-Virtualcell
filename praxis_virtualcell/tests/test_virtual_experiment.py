"""P17 deterministic Virtual Experiment contracts and fail-closed governance."""

from __future__ import annotations

import hashlib
import importlib
import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

import pytest

from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.core.exceptions import InputValidationError
from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2
from praxis_virtualcell.io.job_store import JobStore
from praxis_virtualcell.model_zoo.capability_registry import (
    CompatibilityReportV2,
    EnvironmentSnapshot,
    ExecutionPlanV2,
    ExecutionStepV2,
)
from praxis_virtualcell.model_zoo.registry_v2 import (
    AdapterIdentity,
    ArtifactIdentity,
    EnvironmentIdentity,
    ModelRegistryV2,
    ModelReleaseRecord,
    OperatorPolicyRecord,
    RegistryLifecycleEvent,
    ValidationEvidence,
)
from praxis_virtualcell.pack_product import (
    PackIndex,
    _public_provenance,
    run_pack_query,
    virtual_experiment_payload,
)
from praxis_virtualcell.tests.test_model_registry_v2 import (
    _complete_v2_report_payload,
    complete_registry_payload,
)
from praxis_virtualcell.tests.test_pack_product import (
    _write_legacy_pack_index,
    _write_model_stack,
)
from praxis_virtualcell.tests.test_pack_semantics import _fixture, _write_pack
from praxis_virtualcell.virtual_experiment import (
    VirtualCellBrainContextV1,
    VirtualExperimentCompilationV1,
    VirtualExperimentContractError,
    VirtualExperimentDAGV1,
    VirtualExperimentNodeV1,
    compile_virtual_experiment,
    execution_plan_fingerprint,
)

_PACK_FINGERPRINT = "2" * 64
_ENVIRONMENT_SNAPSHOT_FINGERPRINT = hashlib.sha256(b"environment-snapshot").hexdigest()


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _signed(value: dict) -> dict:
    value = deepcopy(value)
    value["fingerprint"] = _fingerprint(value)
    return value


def _request(
    *,
    request_id: str = "test-request",
    taxonomy_id: str = "NCBITaxon:9606",
    scientific_name: str = "Homo sapiens",
    cell_type_name: str = "K562",
    target: str = "ENSG00000106546",
) -> VirtualCellRequestV2:
    return VirtualCellRequestV2.from_dict(
        {
            "schema_version": "vc.request.v2",
            "request_id": request_id,
            "species": {
                "schema_version": "vc.species-ref.v1",
                "taxonomy_id": taxonomy_id,
                "scientific_name": scientific_name,
                "common_name": None,
            },
            "cell_context": {
                "schema_version": "vc.cell-context.v1",
                "cell_type_name": cell_type_name,
                "cell_type_id": None,
                "tissue_name": None,
                "tissue_id": None,
                "attributes": {},
            },
            "input_modality": {
                "schema_version": "vc.modality.v1",
                "name": "scRNA",
                "ontology_id": "EFO:0008913",
                "unit": None,
                "feature_namespace": "EnsemblGene",
            },
            "output_modality": {
                "schema_version": "vc.modality.v1",
                "name": "delta_expression",
                "ontology_id": None,
                "unit": None,
                "feature_namespace": "EnsemblGene",
            },
            "perturbation": {
                "schema_version": "vc.perturbation.v1",
                "kind": "gene",
                "targets": [target],
                "dose_value": None,
                "dose_unit": None,
                "timepoint": None,
            },
            "task": {
                "schema_version": "vc.task.v1",
                "task_type": "predict_delta_expression",
                "requested_outputs": ["delta_expression"],
            },
            "baseline_context": None,
            "metadata": {},
            "constraints": {},
        }
    )


def _report(
    request: VirtualCellRequestV2,
    model_name: str,
    *,
    state: str = "promoted",
) -> CompatibilityReportV2:
    payload = _complete_v2_report_payload()
    payload.update(
        {
            "request_id": request.request_id,
            "request_fingerprint": _fingerprint(request.to_dict()),
            "model_name": model_name,
            "model_version": "1.0.0",
            "model_fingerprint": _fingerprint(f"{model_name}:model"),
            "release_fingerprint": _fingerprint(f"{model_name}:release"),
            "capability_fingerprint": _fingerprint(f"{model_name}:capability"),
            "environment_fingerprint": _fingerprint(f"{model_name}:environment"),
            "pack_fingerprint": _PACK_FINGERPRINT,
            "environment_snapshot_fingerprint": _ENVIRONMENT_SNAPSHOT_FINGERPRINT,
            "artifact_fingerprints": [_fingerprint(f"{model_name}:artifact")],
            "adapter_fingerprints": [_fingerprint(f"{model_name}:adapter")],
            "evidence_fingerprints": [_fingerprint(f"{model_name}:evidence")],
            "policy_fingerprint": _fingerprint(f"{model_name}:policy"),
        }
    )
    _apply_report_state(payload, state)
    return CompatibilityReportV2.from_dict(payload)


def _apply_report_state(payload: dict, state: str) -> None:
    if state == "non_promoted":
        payload.update(production_promoted=False, executable=False)
    elif state == "missing_evidence":
        payload.update(
            evidence_fingerprints=[],
            benchmark_passed=None,
            scientifically_validated=None,
            promotion_eligible=None,
            production_promoted=False,
            executable=False,
        )
    elif state == "revoked":
        payload.update(revoked=True, executable=False)
    elif state == "missing_policy":
        payload.update(
            policy_fingerprint=None,
            policy_present=False,
            production_promoted=False,
            executable=False,
        )
    elif state == "missing_adapter":
        payload.update(
            adapter_fingerprints=[],
            adapter_compatible=False,
            executable=False,
        )
    elif state == "missing_environment":
        payload.update(
            environment_fingerprint=None,
            environment_compatible=False,
            executable=False,
        )
    elif state == "missing_pack":
        payload.update(
            pack_id=None,
            pack_version=None,
            pack_fingerprint=None,
            pack_valid=False,
            executable=False,
        )
    elif state != "promoted":
        raise ValueError(f"unknown report state: {state}")


def _registry(release_count: int) -> ModelRegistryV2:
    base = complete_registry_payload()
    artifacts = []
    environments = []
    adapters = []
    evidence_records = []
    policy_records = []
    releases = []
    for index in range(release_count):
        model_name = f"model_{chr(ord('a') + index)}"
        model_fingerprint = _fingerprint(f"{model_name}:model")

        artifact_value = deepcopy(base["artifacts"][0])
        artifact_value.update(
            artifact_id=f"{model_name}:model.bin",
            model_fingerprint=model_fingerprint,
            cache_key=f"{model_name}/model.bin",
            sha256=_fingerprint(f"{model_name}:asset-bytes"),
            source="test-only synthetic artifact",
        )
        artifact = ArtifactIdentity.from_dict(artifact_value)

        adapter_value = deepcopy(base["adapters"][0])
        adapter_value.update(
            adapter_id=f"{model_name}-adapter",
            implementation=f"tests.adapters.{model_name.title().replace('_', '')}Adapter",
            input_contract_fingerprint=_fingerprint(f"{model_name}:input-contract"),
            output_contract_fingerprint=_fingerprint(f"{model_name}:output-contract"),
        )
        adapter = AdapterIdentity.from_dict(adapter_value)

        environment_value = deepcopy(base["environments"][0])
        environment_value.update(
            environment_id=f"{model_name}-cpu-lock",
            lock_digest=_fingerprint(f"{model_name}:lock"),
            adapter_fingerprints=[adapter.fingerprint()],
        )
        environment = EnvironmentIdentity.from_dict(environment_value)

        evidence_value = deepcopy(base["evidence_records"][0])
        evidence_value.update(
            evidence_id=f"{model_name}-test-only-evidence",
            pack_fingerprint=_PACK_FINGERPRINT,
            model_fingerprint=model_fingerprint,
            environment_fingerprint=environment.fingerprint(),
            adapter_fingerprints=[adapter.fingerprint()],
            protocol_fingerprint=_fingerprint(f"{model_name}:protocol"),
            baseline_fingerprint=_fingerprint(f"{model_name}:baseline"),
            result_sha256=_fingerprint(f"{model_name}:result"),
        )
        evidence = ValidationEvidence.from_dict(evidence_value)

        release_value = deepcopy(base["releases"][0])
        release_value.update(
            release_id=f"{model_name}@1.0.0",
            model_name=model_name,
            model_version="1.0.0",
            model_fingerprint=model_fingerprint,
            pack_fingerprints=[_PACK_FINGERPRINT],
            artifact_fingerprints=[artifact.fingerprint()],
            environment_fingerprint=environment.fingerprint(),
            adapter_fingerprints=[adapter.fingerprint()],
            evidence_fingerprints=[evidence.fingerprint()],
            policy_fingerprint=None,
        )
        release_without_policy = ModelReleaseRecord.from_dict(release_value)

        policy_value = deepcopy(base["policy_records"][0])
        policy_value.update(
            policy_id=f"{model_name}-test-only-policy",
            capability_fingerprint=release_without_policy.capability_fingerprint(),
            evidence_fingerprints=[evidence.fingerprint()],
        )
        policy = OperatorPolicyRecord.from_dict(policy_value)
        release = ModelReleaseRecord.from_dict(
            {**release_without_policy.to_dict(), "policy_fingerprint": policy.fingerprint()}
        )
        artifacts.append(artifact)
        adapters.append(adapter)
        environments.append(environment)
        evidence_records.append(evidence)
        policy_records.append(policy)
        releases.append(release)

    events = []
    for release_index, release in enumerate(releases, start=1):
        for action in ("cataloged", "artifact_ready"):
            sequence = len(events) + 1
            event = RegistryLifecycleEvent.from_dict(
                {
                    "schema_version": "vc.model-registry-event.v1",
                    "event_id": f"event-{sequence}",
                    "sequence": sequence,
                    "previous_event_fingerprint": (events[-1].fingerprint() if events else None),
                    "release_fingerprint": release.fingerprint(),
                    "action": action,
                    "target_release_fingerprint": None,
                    "recorded_at": f"2026-08-0{release_index}T00:00:0{sequence}Z",
                    "operator_id": "test-only-operator",
                    "reason": "contract conformance fixture only",
                }
            )
            events.append(event)

    return ModelRegistryV2.from_dict(
        {
            "schema_version": "vc.model-registry.v2",
            "artifacts": [item.to_dict() for item in artifacts],
            "environments": [item.to_dict() for item in environments],
            "adapters": [item.to_dict() for item in adapters],
            "evidence_records": [item.to_dict() for item in evidence_records],
            "policy_records": [item.to_dict() for item in policy_records],
            "releases": [item.to_dict() for item in releases],
            "lifecycle_events": [item.to_dict() for item in events],
        }
    )


def _registry_report(
    request: VirtualCellRequestV2,
    registry: ModelRegistryV2,
    index: int,
    *,
    state: str = "promoted",
) -> CompatibilityReportV2:
    release = registry.releases[index]
    payload = _complete_v2_report_payload()
    payload.update(
        request_id=request.request_id,
        request_fingerprint=_fingerprint(request.to_dict()),
        model_name=release.model_name,
        model_version=release.model_version,
        model_fingerprint=release.model_fingerprint,
        release_fingerprint=release.fingerprint(),
        capability_fingerprint=release.capability_fingerprint(),
        pack_fingerprint=_PACK_FINGERPRINT,
        environment_fingerprint=release.environment_fingerprint,
        environment_snapshot_fingerprint=_ENVIRONMENT_SNAPSHOT_FINGERPRINT,
        artifact_fingerprints=list(release.artifact_fingerprints),
        adapter_fingerprints=list(release.adapter_fingerprints),
        evidence_fingerprints=list(release.evidence_fingerprints),
        policy_fingerprint=release.policy_fingerprint,
    )
    _apply_report_state(payload, state)
    return CompatibilityReportV2.from_dict(payload)


def _step(report: CompatibilityReportV2) -> ExecutionStepV2:
    assert report.model_version is not None
    assert report.release_fingerprint is not None
    assert report.capability_fingerprint is not None
    assert report.environment_fingerprint is not None
    assert report.policy_fingerprint is not None
    return ExecutionStepV2.from_dict(
        {
            "schema_version": "vc.execution-step.v2",
            "model_name": report.model_name,
            "model_version": report.model_version,
            "model_fingerprint": report.model_fingerprint,
            "release_fingerprint": report.release_fingerprint,
            "capability_fingerprint": report.capability_fingerprint,
            "artifact_fingerprints": list(report.artifact_fingerprints),
            "environment_fingerprint": report.environment_fingerprint,
            "adapter_fingerprints": list(report.adapter_fingerprints),
            "evidence_fingerprints": list(report.evidence_fingerprints),
            "policy_fingerprint": report.policy_fingerprint,
            "compatibility_fingerprint": report.fingerprint(),
            "wrapper": "praxis_virtualcell.tests.test_virtual_experiment.TestAdapter",
            "agent_name": report.model_name,
            "asset_paths": dict(report.asset_paths),
        }
    )


def _plan(
    request: VirtualCellRequestV2,
    reports: tuple[CompatibilityReportV2, ...] = (),
    *,
    with_pack: bool = True,
) -> ExecutionPlanV2:
    steps = tuple(_step(report) for report in reports if report.executable)
    return ExecutionPlanV2.build(
        request_id=request.request_id,
        request_fingerprint=_fingerprint(request.to_dict()),
        pack_id="test-pack" if with_pack else None,
        pack_version="1.0.0" if with_pack else None,
        pack_fingerprint=_PACK_FINGERPRINT if with_pack else None,
        environment_snapshot_fingerprint=_ENVIRONMENT_SNAPSHOT_FINGERPRINT,
        reports=reports,
        steps=steps,
    )


def _fifth_taxon_pack(tmp_path: Path) -> Path:
    source = deepcopy(_fixture("human"))
    source.update(
        pack_id="p17-zebrafish-tiny",
        pack_version="1.0.0",
        taxon={"ontology_id": "NCBITaxon:7955", "scientific_name": "Danio rerio"},
        assembly={"name": "GRCz11", "accession": "GCF_000002035.6"},
        provenance={
            "source": "synthetic P17 fifth-taxon fixture",
            "created_by": "PRAXIS-VirtualCell tests",
            "citation": "none",
        },
    )
    source["feature_namespace"]["version"] = "GRCz11"
    source["cell_semantics"]["local_terms"].append(
        {
            "id": "VCCELL:zebrafish-test",
            "role": "identity",
            "label": "synthetic zebrafish cell",
            "definition": "Test-only cell identity.",
        }
    )
    target_map: dict[str, str] = {}
    for feature in source["fixture_features"]:
        old = feature["id"]
        feature["id"] = old.replace("ENSG", "ENSDARG")
        target_map[old] = feature["id"]
    for perturbation in source["perturbations"]["values"]:
        perturbation["targets"] = [target_map.get(target, target) for target in perturbation["targets"]]
    for observation in source["fixture_observations"]:
        observation["cell_identity_id"] = "VCCELL:zebrafish-test"
    return _write_pack(tmp_path / "zebrafish-pack", source)


def _contract_result(
    request: VirtualCellRequestV2,
    *,
    candidate_dag: object = None,
    release_count: int = 0,
) -> dict:
    registry = _registry(release_count)
    reports = tuple(_registry_report(request, registry, index) for index in range(release_count))
    plan = _plan(request, reports)
    compilation = compile_virtual_experiment(
        request,
        plan,
        registry,
        candidate_dag=candidate_dag,
    )
    provenance = {
        "execution_contract": "vc.virtual-experiment-compilation.v1",
        "execution_plan": plan.to_dict(),
        "compatibility_reports": [report.to_dict() for report in reports],
        "virtual_experiment": compilation.to_dict(),
        "rejection_reasons": {},
        "rules_referenced": [],
        "rules_hit": [],
        "n_messages": 0,
    }
    return {
        "structured_report": {
            "request_id": request.request_id,
            "prediction": None,
            "models_used": [],
            "models_rejected": [],
            "models_failed": [],
            "abstain": True,
            "abstain_reasons": [compilation.decision.reason],
            "reliability": "low",
            "provenance": provenance,
        },
        "narrative": None,
        "trace": [],
        "provenance": provenance,
        "reliability_decision": {
            "abstain": True,
            "reliability": "low",
            "learned_reliability": None,
        },
        "llm_used_for_prediction": False,
        "mode": "offline",
        "llm_enabled": False,
    }


@pytest.mark.parametrize("report_count", [0, 1])
def test_broker_plan_only_never_instantiates_a_wrapper(report_count: int):
    request = _request()
    reports = (_report(request, "model_a"),) if report_count else ()
    plan = _plan(request, reports)
    capabilities = Mock()
    capabilities.plan.return_value = plan
    capabilities.instantiate.side_effect = AssertionError("wrapper instantiated")
    broker = object.__new__(ModelBrokerAgent)
    broker._capabilities = capabilities
    broker._environment = EnvironmentSnapshot(
        schema_version="vc.environment.v1",
        python_dependencies=[],
        resources=["cpu"],
    )

    assert broker.plan(request, None) is plan
    capabilities.plan.assert_called_once_with(request, None, broker._environment)
    capabilities.instantiate.assert_not_called()


def test_job_store_keeps_valid_v1_and_v2_identity_history(tmp_path: Path):
    identities = (
        _signed(
            {
                "schema_version": "vc.job-execution-identity.v1",
                "legacy_adapter": True,
                "pack": None,
                "models": [],
            }
        ),
        _signed(
            {
                "schema_version": "vc.job-execution-identity.v2",
                "legacy_adapter": False,
                "plan_id": f"plan_{'4' * 24}",
                "submitted_request_fingerprint": "5" * 64,
                "request_fingerprint": "6" * 64,
                "pack": None,
                "environment_snapshot_fingerprint": "7" * 64,
                "execution_step_fingerprints": [],
                "structured_report_fingerprint": "8" * 64,
                "outcome": {
                    "abstain": True,
                    "models_used": [],
                    "prediction_present": False,
                },
                "models": [],
            }
        ),
    )
    store = JobStore(str(tmp_path / "runs"))
    for index, identity in enumerate(identities, start=1):
        directory = tmp_path / "runs" / f"historical-{index}"
        directory.mkdir(parents=True)
        (directory / "status").write_text("done", encoding="utf-8")
        (directory / "execution_identity.json").write_text(
            json.dumps(identity),
            encoding="utf-8",
        )
        assert store.load(directory.name)["execution_identity"] == identity


@pytest.mark.parametrize("release_count", [0, 1])
def test_zero_or_one_capability_is_deterministic_empty_dag_abstain(
    release_count: int,
):
    request = _request()
    registry = _registry(release_count)
    reports = tuple(_registry_report(request, registry, index) for index in range(release_count))
    plan = _plan(request, reports)

    first = compile_virtual_experiment(request, plan, registry)
    second = compile_virtual_experiment(request, plan, registry)

    assert first.to_dict() == second.to_dict()
    assert first.authoritative_fingerprint() == second.authoritative_fingerprint()
    assert first.dag.nodes == first.dag.edges == ()
    assert first.dag.plan_fingerprint == execution_plan_fingerprint(plan)
    assert first.brain_context.dag_fingerprint == first.dag.fingerprint()
    assert first.decision.participating_capability_count == release_count
    assert len(first.decision.participating_capability_fingerprints) == release_count
    assert (
        first.brain_context.participating_capability_fingerprints
        == first.decision.participating_capability_fingerprints
    )
    assert first.decision.eligible_for_multi_model_execution is False
    assert first.decision.executable is False
    assert first.decision.execution_performed is False
    assert first.decision.abstain is True
    assert VirtualExperimentCompilationV1.from_dict(first.to_dict()) == first


def test_two_distinct_exact_capabilities_form_nodes_but_remain_contract_only():
    request = _request()
    registry = _registry(2)
    reports = tuple(_registry_report(request, registry, index) for index in range(2))
    plan = _plan(request, reports)

    compilation = compile_virtual_experiment(request, plan, registry)

    assert len(compilation.dag.nodes) == 2
    assert compilation.dag.edges == ()
    assert len({node.capability_fingerprint for node in compilation.dag.nodes}) == 2
    assert compilation.decision.participating_capability_count == 2
    assert (
        compilation.decision.participating_capability_fingerprints
        == compilation.dag.participating_capability_fingerprints
        == compilation.brain_context.participating_capability_fingerprints
    )
    assert compilation.decision.eligible_for_multi_model_execution is True
    assert compilation.decision.executable is False
    assert compilation.decision.execution_performed is False
    assert compilation.decision.abstain is True
    assert compilation.decision.final_verdict == "abstain"
    assert compilation.decision.reason == "contract_only_execution_not_authorized"


def test_compiler_revalidates_model_construct_and_rejects_subclass_inputs():
    request = _request()
    registry = _registry(0)
    plan = _plan(request)
    request_fields = dict(request.__dict__)
    request_fields["request_id"] = " invalid "
    constructed_request = VirtualCellRequestV2.model_construct(**request_fields)
    plan_fields = dict(plan.__dict__)
    plan_fields["plan_id"] = f"plan_{'f' * 24}"
    constructed_plan = ExecutionPlanV2.model_construct(**plan_fields)

    class RequestSubclass(VirtualCellRequestV2):
        pass

    subclassed_request = RequestSubclass.from_dict(request.to_dict())

    with pytest.raises(VirtualExperimentContractError):
        compile_virtual_experiment(constructed_request, plan, registry)
    with pytest.raises(VirtualExperimentContractError):
        compile_virtual_experiment(request, constructed_plan, registry)
    with pytest.raises(VirtualExperimentContractError, match="exact"):
        compile_virtual_experiment(subclassed_request, plan, registry)


def test_multi_adapter_node_keeps_aligned_contract_identities():
    request = _request()
    registry = _registry(2)
    plan = _plan(
        request,
        tuple(_registry_report(request, registry, index) for index in range(2)),
    )
    value = compile_virtual_experiment(request, plan, registry).dag.nodes[0].to_dict()
    second_adapter = _fingerprint("second-adapter")
    second_input = _fingerprint("second-input-contract")
    second_output = _fingerprint("second-output-contract")
    value["adapter_fingerprints"].append(second_adapter)
    value["input_contract_fingerprints"].append(second_input)
    value["output_contract_fingerprints"].append(second_output)

    node = VirtualExperimentNodeV1.from_dict(value)

    assert node.adapter_fingerprints[-1] == second_adapter
    assert node.input_contract_fingerprints[-1] == second_input
    assert node.output_contract_fingerprints[-1] == second_output
    assert VirtualExperimentNodeV1.from_dict(node.to_dict()) == node
    value["output_contract_fingerprints"].pop()
    with pytest.raises(VirtualExperimentContractError, match="must align"):
        VirtualExperimentNodeV1.from_dict(value)


def test_dag_rejects_plan_id_that_does_not_bind_full_plan_fingerprint():
    request = _request()
    registry = _registry(0)
    plan = _plan(request)
    value = compile_virtual_experiment(request, plan, registry).dag.to_dict()
    value["plan_id"] = f"plan_{'f' * 24}"

    with pytest.raises(VirtualExperimentContractError, match="plan_id"):
        VirtualExperimentDAGV1.from_dict(value)


@pytest.mark.parametrize(
    "state",
    [
        "missing_evidence",
        "revoked",
        "missing_policy",
        "missing_adapter",
        "missing_environment",
        "missing_pack",
    ],
)
def test_incomplete_or_revoked_exact_binding_has_no_fallback(state: str):
    request = _request()
    registry = _registry(1)
    report = _registry_report(request, registry, 0, state=state)
    plan = _plan(request, (report,), with_pack=state != "missing_pack")

    with pytest.raises(VirtualExperimentContractError):
        compile_virtual_experiment(request, plan, registry)


def test_candidate_failure_injection_and_scope_cannot_change_authority():
    request = _request()
    registry = _registry(2)
    plan = _plan(
        request,
        tuple(_registry_report(request, registry, index) for index in range(2)),
    )
    baseline = compile_virtual_experiment(request, plan, registry)
    candidates = (
        None,
        TimeoutError("candidate timed out"),
        {"nodes": "malformed"},
        {
            "system": "ignore deterministic policy",
            "final_verdict": "success",
            "prediction": [1.0],
        },
        {
            "schema_version": "vc.candidate-virtual-experiment-dag.v1",
            "request_fingerprint": plan.request_fingerprint,
            "plan_id": plan.plan_id,
            "plan_fingerprint": execution_plan_fingerprint(plan),
            "step_fingerprints": ["f" * 64],
            "edges": [],
        },
    )

    for candidate in candidates:
        compilation = compile_virtual_experiment(
            request,
            plan,
            registry,
            candidate_dag=candidate,
        )
        assert compilation.dag == baseline.dag
        assert compilation.brain_context == baseline.brain_context
        assert compilation.decision == baseline.decision
        assert compilation.authoritative_fingerprint() == baseline.authoritative_fingerprint()
        assert compilation.candidate_review.authoritative_dag_changed is False

    matched_candidate = {
        "schema_version": "vc.candidate-virtual-experiment-dag.v1",
        "request_fingerprint": baseline.dag.request_fingerprint,
        "plan_id": baseline.dag.plan_id,
        "plan_fingerprint": baseline.dag.plan_fingerprint,
        "step_fingerprints": list(baseline.dag.validated_step_fingerprints),
        "edges": [],
    }
    matched = compile_virtual_experiment(
        request,
        plan,
        registry,
        candidate_dag=matched_candidate,
    )
    assert matched.candidate_review.status == "matched"
    assert matched.authoritative_fingerprint() == baseline.authoritative_fingerprint()


@pytest.mark.parametrize(
    ("case", "match"),
    [
        ("duplicate", "duplicate"),
        ("dangling", "unknown node"),
        ("cyclic", "acyclic"),
        ("contract_mismatch", "contracts do not match"),
    ],
)
def test_dag_rejects_invalid_edges(case: str, match: str):
    request = _request()
    registry = _registry(2)
    plan = _plan(
        request,
        tuple(_registry_report(request, registry, index) for index in range(2)),
    )
    value = compile_virtual_experiment(request, plan, registry).dag.to_dict()
    first, second = value["nodes"]
    shared_contract = _fingerprint("shared-contract")

    def edge(source: str, target: str, output: str, input_: str) -> dict:
        return {
            "schema_version": "vc.virtual-experiment-edge.v1",
            "source_step_fingerprint": source,
            "target_step_fingerprint": target,
            "output_contract_fingerprint": output,
            "input_contract_fingerprint": input_,
        }

    if case in {"duplicate", "cyclic"}:
        for node in value["nodes"]:
            node["input_contract_fingerprints"] = [shared_contract]
            node["output_contract_fingerprints"] = [shared_contract]
    if case == "duplicate":
        item = edge(
            first["execution_step_fingerprint"],
            second["execution_step_fingerprint"],
            shared_contract,
            shared_contract,
        )
        value["edges"] = [item, deepcopy(item)]
    elif case == "dangling":
        value["edges"] = [
            edge(
                "f" * 64,
                first["execution_step_fingerprint"],
                first["input_contract_fingerprints"][0],
                first["input_contract_fingerprints"][0],
            )
        ]
    elif case == "cyclic":
        value["edges"] = sorted(
            [
                edge(
                    first["execution_step_fingerprint"],
                    second["execution_step_fingerprint"],
                    shared_contract,
                    shared_contract,
                ),
                edge(
                    second["execution_step_fingerprint"],
                    first["execution_step_fingerprint"],
                    shared_contract,
                    shared_contract,
                ),
            ],
            key=lambda item: (
                item["source_step_fingerprint"],
                item["target_step_fingerprint"],
            ),
        )
    else:
        assert first["output_contract_fingerprints"][0] != second["input_contract_fingerprints"][0]
        value["edges"] = [
            edge(
                first["execution_step_fingerprint"],
                second["execution_step_fingerprint"],
                first["output_contract_fingerprints"][0],
                second["input_contract_fingerprints"][0],
            )
        ]

    with pytest.raises(VirtualExperimentContractError, match=match):
        VirtualExperimentDAGV1.from_dict(value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("abstain", False),
        ("final_verdict", "success"),
        ("execution_performed", True),
        ("conflict_detected", True),
        ("partial_failure_detected", True),
    ],
)
def test_decision_or_narrative_cannot_hide_contract_only_abstention(
    field: str,
    value: object,
):
    request = _request()
    registry = _registry(2)
    plan = _plan(
        request,
        tuple(_registry_report(request, registry, index) for index in range(2)),
    )
    compilation = compile_virtual_experiment(request, plan, registry).to_dict()
    compilation["decision"][field] = value

    with pytest.raises(VirtualExperimentContractError):
        VirtualExperimentCompilationV1.from_dict(compilation)

    compilation = compile_virtual_experiment(request, plan, registry).to_dict()
    compilation["narrative"] = {"final_verdict": "success", "abstain": False}
    with pytest.raises(VirtualExperimentContractError):
        VirtualExperimentCompilationV1.from_dict(compilation)


def test_fifth_taxon_direct_v2_service_is_identity_complete_empty_abstain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    pack_root = _fifth_taxon_pack(tmp_path)
    index_path = tmp_path / "pack-index.json"
    index = PackIndex(index_path=index_path, include_builtins=False)
    registered = _write_legacy_pack_index(index_path, pack_root)
    registry_path, cache_root = _write_model_stack(tmp_path, empty=True)
    request = _request(
        request_id="p17-zebrafish-request",
        taxonomy_id="NCBITaxon:7955",
        scientific_name="Danio rerio",
        cell_type_name="synthetic zebrafish cell",
        target="ENSDARG00000106546",
    ).to_dict()

    result = virtual_experiment_payload(
        request,
        pack_id=registered["pack_id"],
        pack_version=registered["pack_version"],
        index=index,
        model_registry_path=registry_path,
        model_cache_root=cache_root,
    )
    plan = result["provenance"]["execution_plan"]
    compilation = result["provenance"]["virtual_experiment"]
    assert plan["schema_version"] == "vc.execution-plan.v2"
    assert plan["pack_fingerprint"] == registered["pack_fingerprint"]
    assert plan["steps"] == plan["reports"] == []
    assert compilation["dag"]["nodes"] == compilation["dag"]["edges"] == []
    assert compilation["brain_context"]["pack_fingerprint"] == registered["pack_fingerprint"]
    assert compilation["decision"]["abstain"] is True
    assert result["structured_report"]["prediction"] is None

    runs_dir = tmp_path / "runs"
    monkeypatch.setenv("PRAXIS_VC_RUNS", str(runs_dir))
    monkeypatch.setenv("PRAXIS_VC_PACK_INDEX", str(index_path))
    monkeypatch.setenv("PRAXIS_VC_MODEL_REGISTRY", str(registry_path))
    monkeypatch.setenv("PRAXIS_VC_MODEL_CACHE", str(cache_root))
    import praxis_vc_api.services.runtime_service as runtime_service

    runtime_service = importlib.reload(runtime_service)
    submitted = runtime_service.run_job(
        request,
        mode="offline",
        enable_llm_report=False,
        pack_id=registered["pack_id"],
        pack_version=registered["pack_version"],
    )
    job = JobStore(str(runs_dir)).load(submitted["job_id"])
    identity = job["execution_identity"]
    assert identity["schema_version"] == "vc.job-execution-identity.v3"
    assert identity["pack"]["fingerprint"] == registered["pack_fingerprint"]
    assert identity["brain_fingerprint"] == compilation["decision"]["brain_fingerprint"]
    assert identity["dag_fingerprint"] == compilation["decision"]["dag_fingerprint"]
    assert identity["outcome"] == {
        "abstain": True,
        "models_used": [],
        "prediction_present": False,
    }


def test_virtual_experiment_surface_rejects_legacy_without_resolution_fallback():
    with pytest.raises(InputValidationError, match="exact vc.request.v2"):
        virtual_experiment_payload(
            {
                "request_id": "legacy-request",
                "species": "human",
                "cell_type": "K562",
                "perturbation_type": "gene",
                "perturbation_targets": ["AHR"],
                "input_modality": "scRNA",
                "output_modality": "delta_expression",
                "task_type": "predict_delta_expression",
            },
            pack_id="not-resolved",
            pack_version="1.0.0",
        )


def test_v2_marker_cannot_enter_legacy_pack_runner():
    hybrid = _request().to_dict()
    hybrid.update(
        {
            "species": "human",
            "cell_type": "K562",
            "perturbation_type": "gene",
            "perturbation_targets": ["AHR"],
            "task_type": "predict_delta_expression",
        }
    )
    with pytest.raises(InputValidationError, match="direct virtual experiment"):
        run_pack_query(
            hybrid,
            pack_id="must-not-resolve",
            pack_version="1.0.0",
        )


def test_candidate_audit_status_has_separate_non_authoritative_checksum():
    request = _request()
    compilation = compile_virtual_experiment(
        request,
        _plan(request),
        _registry(0),
    )
    tampered = compilation.to_dict()
    tampered["candidate_review"].update(
        status="matched",
        reason="candidate_matched_authoritative_dag",
    )

    with pytest.raises(VirtualExperimentContractError, match="candidate review"):
        VirtualExperimentCompilationV1.from_dict(tampered)
    assert compilation.authoritative_fingerprint() == compilation.fingerprint()


def test_brain_cannot_drop_participant_adapter_contract_identities():
    result = _contract_result(_request(), release_count=2)
    raw_compilation = deepcopy(result["provenance"]["virtual_experiment"])
    raw_compilation["brain_context"]["adapter_input_contract_fingerprints"] = []
    raw_compilation["brain_context"]["adapter_output_contract_fingerprints"] = []
    changed_brain = VirtualCellBrainContextV1.from_dict(raw_compilation["brain_context"])
    raw_compilation["decision"]["brain_fingerprint"] = changed_brain.fingerprint()

    with pytest.raises(VirtualExperimentContractError, match="participants"):
        VirtualExperimentCompilationV1.from_dict(raw_compilation)


def test_asset_paths_do_not_enter_virtual_experiment_or_public_provenance():
    request = _request()
    registry = _registry(2)
    reports = tuple(_registry_report(request, registry, index) for index in range(2))
    clean_plan = _plan(request, reports)
    secret = "/private/model-cache/secret-model.bin"
    path_reports = tuple(
        CompatibilityReportV2.from_dict({**report.to_dict(), "asset_paths": {"model.bin": secret}})
        for report in reports
    )
    path_plan = _plan(request, path_reports)

    clean = compile_virtual_experiment(request, clean_plan, registry)
    with_paths = compile_virtual_experiment(request, path_plan, registry)
    public = _public_provenance(
        {
            "execution_plan": path_plan.to_dict(),
            "virtual_experiment": with_paths.to_dict(),
        }
    )

    assert path_plan.plan_id == clean_plan.plan_id
    assert with_paths.authoritative_fingerprint() == clean.authoritative_fingerprint()
    assert secret not in json.dumps(with_paths.to_dict())
    assert secret not in json.dumps(public)
    assert all("asset_paths" not in item for item in public["execution_plan"]["steps"])
    assert all("asset_paths" not in item for item in public["execution_plan"]["reports"])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("request_id", "different-request"),
        ("models_rejected", ["invented-model"]),
        ("models_failed", ["invented-model"]),
        ("abstain_reasons", ["success"]),
        ("reliability", "high"),
        ("invented_verdict", "success"),
    ],
)
def test_job_store_v3_binds_contract_only_report_semantics(
    field: str,
    value: object,
):
    request = _request()
    result = _contract_result(request)
    result["structured_report"][field] = value

    with pytest.raises(ValueError, match="structured report is inconsistent"):
        JobStore._execution_identity(result, request=request.to_dict())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("trace", [{"event": "model_executed"}]),
        ("narrative", "Prediction succeeded."),
    ],
)
def test_job_store_v3_rejects_execution_trace_or_narrative(
    field: str,
    value: object,
):
    request = _request()
    result = _contract_result(request)
    result[field] = value

    with pytest.raises(ValueError, match="trace and narrative must be empty"):
        JobStore._execution_identity(result, request=request.to_dict())


def test_job_store_v3_rejects_split_virtual_experiment_provenance():
    request = _request()
    result = _contract_result(request)
    report_provenance = deepcopy(result["structured_report"]["provenance"])
    report_provenance.pop("execution_contract")
    result["structured_report"]["provenance"] = report_provenance

    with pytest.raises(ValueError, match="provenances differ"):
        JobStore._execution_identity(result, request=request.to_dict())


def test_job_store_v3_rejects_resigned_tamper_and_cross_binding(tmp_path: Path):
    store = JobStore(str(tmp_path / "runs"))
    request_a = _request(request_id="job-a")
    result_a = _contract_result(request_a)
    first = store._execution_identity(result_a, request=request_a.to_dict())
    second = store._execution_identity(result_a, request=request_a.to_dict())
    assert first == second
    assert first["schema_version"] == "vc.job-execution-identity.v3"
    candidate_result = _contract_result(
        request_a,
        candidate_dag={"malicious": "candidate-only metadata"},
    )
    assert store._execution_identity(candidate_result, request=request_a.to_dict()) == first

    mismatched_result = deepcopy(result_a)
    raw_compilation = deepcopy(mismatched_result["provenance"]["virtual_experiment"])
    original_plan_fingerprint = raw_compilation["dag"]["plan_fingerprint"]
    suffix = "0" * 40
    if original_plan_fingerprint.endswith(suffix):
        suffix = "1" * 40
    changed_plan_fingerprint = original_plan_fingerprint[:24] + suffix
    raw_compilation["dag"]["plan_fingerprint"] = changed_plan_fingerprint
    changed_dag = VirtualExperimentDAGV1.from_dict(raw_compilation["dag"])
    raw_compilation["brain_context"]["plan_fingerprint"] = changed_plan_fingerprint
    raw_compilation["brain_context"]["dag_fingerprint"] = changed_dag.fingerprint()
    changed_brain = VirtualCellBrainContextV1.from_dict(raw_compilation["brain_context"])
    raw_compilation["decision"]["dag_fingerprint"] = changed_dag.fingerprint()
    raw_compilation["decision"]["brain_fingerprint"] = changed_brain.fingerprint()
    mismatched_compilation = VirtualExperimentCompilationV1.from_dict(raw_compilation).to_dict()
    mismatched_result["provenance"]["virtual_experiment"] = mismatched_compilation
    mismatched_result["structured_report"]["provenance"]["virtual_experiment"] = mismatched_compilation
    with pytest.raises(ValueError, match="does not match execution plan"):
        store._execution_identity(
            mismatched_result,
            request=request_a.to_dict(),
        )

    mismatched_steps_result = deepcopy(result_a)
    raw_compilation = deepcopy(mismatched_steps_result["provenance"]["virtual_experiment"])
    raw_compilation["dag"]["validated_step_fingerprints"] = ["f" * 64]
    changed_dag = VirtualExperimentDAGV1.from_dict(raw_compilation["dag"])
    raw_compilation["brain_context"]["execution_step_fingerprints"] = ["f" * 64]
    raw_compilation["brain_context"]["dag_fingerprint"] = changed_dag.fingerprint()
    changed_brain = VirtualCellBrainContextV1.from_dict(raw_compilation["brain_context"])
    raw_compilation["decision"]["dag_fingerprint"] = changed_dag.fingerprint()
    raw_compilation["decision"]["brain_fingerprint"] = changed_brain.fingerprint()
    mismatched_compilation = VirtualExperimentCompilationV1.from_dict(raw_compilation).to_dict()
    mismatched_steps_result["provenance"]["virtual_experiment"] = mismatched_compilation
    mismatched_steps_result["structured_report"]["provenance"]["virtual_experiment"] = mismatched_compilation
    with pytest.raises(ValueError, match="does not match execution plan"):
        store._execution_identity(
            mismatched_steps_result,
            request=request_a.to_dict(),
        )

    store.save("job-a", request=request_a.to_dict(), result=result_a)
    assert store.load("job-a")["execution_identity"] == first

    identity_path = tmp_path / "runs" / "job-a" / "execution_identity.json"
    v1_downgrade = _signed(
        {
            "schema_version": "vc.job-execution-identity.v1",
            "legacy_adapter": True,
            "pack": None,
            "models": [],
        }
    )
    identity_path.write_text(json.dumps(v1_downgrade), encoding="utf-8")
    assert store.load("job-a")["execution_identity"]["available"] is False

    downgraded = deepcopy(first)
    downgraded["schema_version"] = "vc.job-execution-identity.v2"
    downgraded.pop("brain_fingerprint")
    downgraded.pop("dag_fingerprint")
    downgraded.pop("fingerprint")
    identity_path.write_text(json.dumps(_signed(downgraded)), encoding="utf-8")
    assert store.load("job-a")["execution_identity"]["available"] is False

    report_path = tmp_path / "runs" / "job-a" / "report.json"
    provenance_path = tmp_path / "runs" / "job-a" / "provenance.json"
    original_report = report_path.read_text(encoding="utf-8")
    original_provenance = provenance_path.read_text(encoding="utf-8")
    report = json.loads(original_report)
    provenance = json.loads(original_provenance)
    report["provenance"].pop("virtual_experiment")
    report["provenance"].pop("execution_contract")
    provenance.pop("virtual_experiment")
    provenance.pop("execution_contract")
    report_path.write_text(json.dumps(report), encoding="utf-8")
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    assert store.load("job-a")["execution_identity"]["available"] is False
    report_path.write_text(original_report, encoding="utf-8")
    provenance_path.write_text(original_provenance, encoding="utf-8")
    identity_path.write_text(json.dumps(first), encoding="utf-8")

    trace_path = tmp_path / "runs" / "job-a" / "trace.json"
    trace_path.write_text(json.dumps([{"event": "model_executed"}]), encoding="utf-8")
    assert store.load("job-a")["execution_identity"]["available"] is False
    trace_path.write_text("[]", encoding="utf-8")

    narrative_path = tmp_path / "runs" / "job-a" / "narrative_report.md"
    narrative_path.write_text("Prediction succeeded.", encoding="utf-8")
    assert store.load("job-a")["execution_identity"]["available"] is False
    narrative_path.unlink()

    tampered = deepcopy(first)
    tampered["brain_fingerprint"] = "f" * 64
    tampered.pop("fingerprint")
    identity_path.write_text(json.dumps(_signed(tampered)), encoding="utf-8")
    assert store.load("job-a")["execution_identity"]["available"] is False

    request_b = _request(request_id="job-b")
    result_b = _contract_result(request_b)
    store.save("job-b", request=request_b.to_dict(), result=result_b)
    identity_b = json.loads((tmp_path / "runs" / "job-b" / "execution_identity.json").read_text(encoding="utf-8"))
    identity_path.write_text(json.dumps(identity_b), encoding="utf-8")
    assert store.load("job-a")["execution_identity"]["available"] is False
