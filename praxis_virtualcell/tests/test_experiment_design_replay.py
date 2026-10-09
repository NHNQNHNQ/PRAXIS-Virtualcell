from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from praxis_virtualcell.core.request_v2 import CellContext, VirtualCellRequestV2
from praxis_virtualcell.experiment_design import (
    ExperimentActionV1,
    ExperimentDesignContractError,
    ReplayOutcomeLedgerV1,
    ReplayProtocolV1,
    ReplayResultV1,
    ReplaySelectionReceiptV1,
    ReplaySelectionRowV1,
    ReplaySelectionViewV1,
    compile_contract_only_experiment,
    evaluate_replay,
    freeze_replay_protocol,
    select_replay_actions,
)
from praxis_virtualcell.model_zoo.adapter_sdk import _fingerprint


def _fp(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _request() -> VirtualCellRequestV2:
    return VirtualCellRequestV2.from_dict(
        {
            "schema_version": "vc.request.v2",
            "request_id": "p27ae-synthetic-request",
            "species": {
                "schema_version": "vc.species-ref.v1",
                "taxonomy_id": "NCBITaxon:9606",
                "scientific_name": "Homo sapiens",
                "common_name": "human",
            },
            "cell_context": {
                "schema_version": "vc.cell-context.v1",
                "cell_type_name": "K562",
                "cell_type_id": None,
                "tissue_name": None,
                "tissue_id": None,
                "attributes": {"fixture": "synthetic_conformance_only"},
            },
            "input_modality": {
                "schema_version": "vc.modality.v1",
                "name": "scRNA",
                "ontology_id": "EFO:0008913",
                "unit": "count",
                "feature_namespace": "EnsemblGene",
            },
            "output_modality": {
                "schema_version": "vc.modality.v1",
                "name": "delta_expression",
                "ontology_id": None,
                "unit": "log2_fold_change",
                "feature_namespace": "EnsemblGene",
            },
            "perturbation": {
                "schema_version": "vc.perturbation.v1",
                "kind": "gene",
                "targets": ["TP53"],
                "dose_value": None,
                "dose_unit": None,
                "timepoint": None,
            },
            "task": {
                "schema_version": "vc.task.v1",
                "task_type": "synthetic_perturbation_delta_prediction",
                "requested_outputs": ["delta_expression"],
            },
            "baseline_context": None,
            "metadata": {},
            "constraints": {"fixture_only": True},
        }
    )


def _action(index: int) -> ExperimentActionV1:
    return ExperimentActionV1.from_dict(
        {
            "schema_version": "vc.experiment-action.v1",
            "action_id": f"synthetic-action-{index}",
            "request_fingerprint": _fp(f"request-{index}"),
            "cell_scope_fingerprint": _fp("cell-scope"),
            "model_scope_fingerprint": _fp("model-scope"),
            "pack_fingerprint": _fp("pack"),
            "compatibility_fingerprint": _fp(f"compatibility-{index}"),
            "execution_step_fingerprint": _fp(f"step-{index}"),
            "evidence_fingerprint": _fp("evidence"),
            "calibration_fingerprint": _fp("calibration"),
            "ood_fingerprint": _fp("ood"),
            "perturbation_id": f"synthetic-gene-{index}",
            "control_id": "synthetic-vehicle-control",
            "replicate_count": 2,
            "batch_ids": [f"batch-{index}-a", f"batch-{index}-b"],
            "endpoint": "synthetic_delta_expression",
            "endpoint_unit": "log2_fold_change",
            "planned_cost": "1",
            "cost_unit": "synthetic_cost_unit",
            "constraints": ["synthetic_fixture_only"],
            "feasibility_status": "synthetic_conformance_only",
            "feasibility_reasons": [
                "synthetic_fixture_not_real_model_domain",
                "external_execution_not_authorized",
            ],
            "synthetic_catalog_eligible": True,
            "real_model_domain_verified": False,
            "scientifically_validated": False,
            "production_promoted": False,
            "external_execution_allowed": False,
            "record_role": "synthetic_conformance_action",
        }
    )


def _view() -> ReplaySelectionViewV1:
    heuristic = ("0.9", "0.8", "0.7", "0.6", "0.5", "0.4")
    uncertainty = ("0.1", "0.95", "0.4", "0.8", "0.3", "0.6")
    diversity = ("group-a", "group-a", "group-b", "group-b", "group-c", "group-c")
    rows: list[dict[str, object]] = []
    for index in range(6):
        action = _action(index)
        rows.append(
            {
                "schema_version": "vc.replay-selection-row.v1",
                "action": action.to_dict(),
                "group_id": f"heldout-group-{index}",
                "heuristic_score": heuristic[index],
                "uncertainty_score": uncertainty[index],
                "diversity_group": diversity[index],
                "expert_priority": 6 - index,
            }
        )
    parsed_rows = [ReplaySelectionRowV1.from_dict(row) for row in rows]
    return ReplaySelectionViewV1.from_dict(
        {
            "schema_version": "vc.replay-selection-view.v1",
            "pool_id": "synthetic-replay-pool",
            "manifest_fingerprint": _fp("synthetic-manifest"),
            "group_split_fingerprint": _fp("synthetic-group-split"),
            "action_catalog_fingerprint": _fingerprint([row.action.fingerprint() for row in parsed_rows]),
            "rows": [row.to_dict() for row in parsed_rows],
            "split_method": "synthetic_group_partition_conformance",
            "selection_partition": "synthetic_candidate_pool",
            "outcome_partition": "synthetic_hidden_outcome_fixture",
            "leakage_audit_status": "unavailable_synthetic_conformance",
            "outcome_fields_available": False,
            "historical_asset_used": False,
            "record_role": "synthetic_conformance_selection_view",
        }
    )


def _protocol(view: ReplaySelectionViewV1 | None = None) -> ReplayProtocolV1:
    selected_view = view or _view()
    return freeze_replay_protocol(
        selected_view,
        budget_count=2,
        random_seed=17,
    )


def _ledger(
    view: ReplaySelectionViewV1,
    *,
    first_utility: str = "0.8",
) -> ReplayOutcomeLedgerV1:
    rows: list[dict[str, object]] = []
    for index, selection_row in enumerate(view.rows):
        if index == 1:
            status = "failed"
            utility = None
            cost = "1"
        elif index == 2:
            status = "unavailable"
            utility = None
            cost = None
        else:
            status = "observed"
            utility = first_utility if index == 0 else "0.2"
            cost = "1"
        rows.append(
            {
                "schema_version": "vc.replay-outcome-row.v1",
                "action_id": selection_row.action.action_id,
                "group_id": selection_row.group_id,
                "status": status,
                "realized_utility": utility,
                "realized_cost": cost,
            }
        )
    return ReplayOutcomeLedgerV1.from_dict(
        {
            "schema_version": "vc.replay-outcome-ledger.v1",
            "pool_id": view.pool_id,
            "manifest_fingerprint": view.manifest_fingerprint,
            "group_split_fingerprint": view.group_split_fingerprint,
            "action_catalog_fingerprint": view.action_catalog_fingerprint,
            "selection_view_fingerprint": view.fingerprint(),
            "outcome_contract_fingerprint": _protocol(view).outcome_contract_fingerprint,
            "rows": rows,
            "historical_asset_used": False,
            "record_role": "synthetic_conformance_outcome_ledger",
        }
    )


def _resign(raw: dict[str, object], id_field: str, prefix: str) -> None:
    raw[id_field] = f"{prefix}{_fingerprint({k: v for k, v in raw.items() if k != id_field})[:24]}"


def test_authoritative_design_is_empty_value_free_and_human_gated() -> None:
    design = compile_contract_only_experiment(
        request=_request(),
        question="Which synthetic perturbation should be considered?",
        hypothesis="No action is executable without an exact promoted domain.",
    )

    assert design.schema_version == "vc.virtual-experiment.v1"
    assert design.selected_action_ids == ()
    assert design.model_scope_fingerprint is None
    assert design.pack_fingerprint is None
    assert design.evidence_fingerprint is None
    assert design.policy_fingerprint is None
    assert design.request_fingerprint == _fingerprint(_request().to_dict())
    assert design.perturbation_ids == ("TP53",)
    assert design.control_id is None
    assert design.replicate_count is None
    assert design.batch_ids == ()
    assert design.endpoint == "delta_expression"
    assert design.endpoint_unit == "log2_fold_change"
    assert design.cost_limit is None
    assert design.cost_unit is None
    assert design.feasibility_status == "unavailable_no_validated_action_space"
    assert design.human_approval_required is True
    assert design.human_approval_status == "required_not_granted"
    assert design.abstain is True
    assert design.executable is False
    assert design.execution_performed is False
    assert design.scientifically_validated is False
    assert design.production_promoted is False
    assert (
        design.fingerprint()
        == compile_contract_only_experiment(
            request=_request(),
            question="Which synthetic perturbation should be considered?",
            hypothesis="No action is executable without an exact promoted domain.",
        ).fingerprint()
    )

    class Bomb:
        def __iter__(self):
            raise AssertionError("candidate must not be inspected")

        __len__ = __iter__
        __getitem__ = __iter__
        __repr__ = __iter__

    with pytest.raises(TypeError, match="candidate"):
        compile_contract_only_experiment(
            request=_request(),
            question="q",
            hypothesis="h",
            candidate=Bomb(),  # type: ignore[call-arg]
        )


def test_public_design_binds_request_without_echoing_secrets_or_rejecting_core_units() -> None:
    raw = _request().to_dict()
    raw["output_modality"]["unit"] = "CPM"
    raw["metadata"] = {
        "api_key": "sk-p27-secret",
        "asset_path": "/private/p27/asset.bin",
    }
    raw["constraints"] = {"private_note": "do-not-echo"}
    request = VirtualCellRequestV2.from_dict(raw)

    design = compile_contract_only_experiment(
        request=request,
        question="Can the exact request be designed?",
        hypothesis="The model domain is unavailable.",
    )
    serialized = design.to_dict()
    rendered = str(serialized)

    assert design.request_id == request.request_id
    assert design.request_fingerprint == _fingerprint(request.to_dict())
    assert design.endpoint_unit == "CPM"
    assert "request" not in serialized
    assert "sk-p27-secret" not in rendered
    assert "/private/p27/asset.bin" not in rendered
    assert "do-not-echo" not in rendered


def test_selection_view_structurally_excludes_outcomes_and_selection_is_deterministic() -> None:
    view = _view()
    protocol = _protocol(view)
    receipts = select_replay_actions(protocol, view)

    assert tuple(receipt.strategy for receipt in receipts) == (
        "active_heuristic",
        "random",
        "uncertainty_only",
        "diversity",
        "expert_rule",
    )
    assert all(len(receipt.selected_action_ids) == 2 for receipt in receipts)
    assert all(receipt.outcome_accessed is False for receipt in receipts)
    assert tuple(receipt.to_dict() for receipt in receipts) == tuple(
        receipt.to_dict() for receipt in select_replay_actions(protocol, view)
    )
    assert receipts[0].selected_action_ids == ("synthetic-action-0", "synthetic-action-1")
    assert receipts[2].selected_action_ids == ("synthetic-action-1", "synthetic-action-3")
    assert receipts[3].selected_action_ids == ("synthetic-action-0", "synthetic-action-2")
    assert receipts[4].selected_action_ids == ("synthetic-action-5", "synthetic-action-4")

    raw_row = view.rows[0].to_dict()
    raw_row["realized_utility"] = "1"
    with pytest.raises(ExperimentDesignContractError, match="extra"):
        ReplaySelectionRowV1.from_dict(raw_row)


def test_receipts_are_frozen_before_reveal_and_do_not_depend_on_outcome_values() -> None:
    view = _view()
    protocol = _protocol(view)
    before = tuple(receipt.to_dict() for receipt in select_replay_actions(protocol, view))
    first = evaluate_replay(protocol, view, select_replay_actions(protocol, view), _ledger(view))
    second = evaluate_replay(
        protocol,
        view,
        select_replay_actions(protocol, view),
        _ledger(view, first_utility="-0.4"),
    )

    assert before == tuple(receipt.to_dict() for receipt in select_replay_actions(protocol, view))
    assert first.receipt_fingerprints == second.receipt_fingerprints
    assert first.outcome_ledger_fingerprint != second.outcome_ledger_fingerprint
    assert first.fingerprint() != second.fingerprint()


def test_failed_and_unavailable_outcomes_are_preserved_without_zero_fill() -> None:
    view = _view()
    protocol = _protocol(view)
    result = evaluate_replay(protocol, view, select_replay_actions(protocol, view), _ledger(view))

    active = result.summaries[0]
    assert active.selected_action_ids == ("synthetic-action-0", "synthetic-action-1")
    assert active.observed_count == 1
    assert active.failed_count == 1
    assert active.unavailable_count == 0
    assert active.failed_action_ids == ("synthetic-action-1",)
    assert active.mean_realized_utility == "0.8"
    assert active.total_realized_cost == "2"
    assert active.missing_values_imputed is False
    uncertainty = result.summaries[2]
    assert uncertainty.failed_count == 1
    assert uncertainty.unavailable_count == 0
    diversity = result.summaries[3]
    assert diversity.unavailable_action_ids == ("synthetic-action-2",)
    assert result.replay_maturity == "synthetic_conformance_only"
    assert result.historical_replay_status == "replay_not_run_asset_pending"
    assert result.primary_passed is None
    assert result.scientifically_validated is False
    assert result.promotion_eligible is False
    assert result.production_promoted is False
    assert result.execution_performed is False
    assert result.external_action_performed is False


def test_wrong_identity_missing_outcome_and_partial_receipts_fail_closed() -> None:
    view = _view()
    protocol = _protocol(view)
    receipts = select_replay_actions(protocol, view)
    ledger = _ledger(view)

    wrong_ledger = ledger.to_dict()
    wrong_ledger["pool_id"] = "wrong-pool"
    with pytest.raises(ExperimentDesignContractError, match="does not match"):
        evaluate_replay(protocol, view, receipts, ReplayOutcomeLedgerV1.from_dict(wrong_ledger))

    omitted = ledger.to_dict()
    omitted["rows"] = omitted["rows"][1:]  # type: ignore[index]
    with pytest.raises(ExperimentDesignContractError, match="explicit unavailable"):
        evaluate_replay(protocol, view, receipts, ReplayOutcomeLedgerV1.from_dict(omitted))

    with pytest.raises(ExperimentDesignContractError, match="all five"):
        evaluate_replay(protocol, view, receipts[:-1], ledger)

    stale = receipts[0].to_dict()
    stale["selected_action_ids"] = ["synthetic-action-5", "synthetic-action-1"]
    with pytest.raises(ExperimentDesignContractError, match="stale"):
        ReplaySelectionReceiptV1.from_dict(stale)

    forged_raw = receipts[0].to_dict()
    forged_raw["selected_action_ids"] = ["synthetic-action-4", "synthetic-action-5"]
    forged_raw["selected_action_fingerprints"] = [
        view.rows[4].action.fingerprint(),
        view.rows[5].action.fingerprint(),
    ]
    forged_raw["selected_uncertainty_scores"] = [
        view.rows[4].uncertainty_score,
        view.rows[5].uncertainty_score,
    ]
    _resign(forged_raw, "receipt_id", "replay_receipt_")
    forged_receipts = (ReplaySelectionReceiptV1.from_dict(forged_raw), *receipts[1:])
    with pytest.raises(ExperimentDesignContractError, match="frozen selector"):
        evaluate_replay(protocol, view, forged_receipts, ledger)

    wrong_group = ledger.to_dict()
    wrong_group["rows"][0]["group_id"] = "wrong-heldout-group"  # type: ignore[index]
    with pytest.raises(ExperimentDesignContractError, match="group binding"):
        evaluate_replay(
            protocol,
            view,
            receipts,
            ReplayOutcomeLedgerV1.from_dict(wrong_group),
        )


def test_recomputed_hashes_cannot_raise_synthetic_status_or_add_authority() -> None:
    view = _view()
    protocol = _protocol(view)
    receipts = select_replay_actions(protocol, view)
    result = evaluate_replay(protocol, view, receipts, _ledger(view))

    protocol_raw = protocol.to_dict()
    protocol_raw["historical_replay_status"] = "complete"
    _resign(protocol_raw, "protocol_id", "replay_protocol_")
    with pytest.raises(ExperimentDesignContractError):
        ReplayProtocolV1.from_dict(protocol_raw)

    receipt_raw = receipts[0].to_dict()
    receipt_raw["outcome_accessed"] = True
    _resign(receipt_raw, "receipt_id", "replay_receipt_")
    with pytest.raises(ExperimentDesignContractError):
        ReplaySelectionReceiptV1.from_dict(receipt_raw)

    result_raw = result.to_dict()
    for field in (
        "scientifically_validated",
        "promotion_eligible",
        "production_promoted",
        "execution_performed",
        "external_action_performed",
        "shadow_reviewed",
        "prospective_pilot",
        "autonomous_experiment",
    ):
        forged = dict(result_raw)
        forged[field] = True
        _resign(forged, "result_id", "replay_result_")
        with pytest.raises(ExperimentDesignContractError):
            ReplayResultV1.from_dict(forged)

    design = compile_contract_only_experiment(request=_request(), question="q", hypothesis="h")
    for field, value in (
        ("control_id", "llm-control"),
        ("replicate_count", 3),
        ("batch_ids", ["llm-batch"]),
        ("cost_limit", "10"),
        ("action_catalog_fingerprint", _fp("invented-action-space")),
        ("selected_action_ids", ["invented-action"]),
        ("executable", True),
    ):
        forged = design.to_dict()
        forged[field] = value
        _resign(forged, "experiment_id", "experiment_")
        with pytest.raises(ExperimentDesignContractError):
            type(design).from_dict(forged)


def test_nested_model_copy_and_lying_subclasses_are_rejected() -> None:
    view = _view()
    row_raw = view.rows[0].to_dict()
    action = view.rows[0].action.model_copy(update={"production_promoted": True})
    row_raw["action"] = action
    with pytest.raises((ExperimentDesignContractError, ValidationError)):
        ReplaySelectionRowV1.model_validate(row_raw)

    class LyingAction(ExperimentActionV1):
        hidden_prediction: tuple[float, ...] = (1.0,)

        def to_dict(self):
            return view.rows[0].action.to_dict()

    lying = LyingAction.model_validate({**view.rows[0].action.to_dict(), "hidden_prediction": (1.0,)})
    row_raw["action"] = lying
    with pytest.raises((ExperimentDesignContractError, ValidationError)):
        ReplaySelectionRowV1.model_validate(row_raw)

    protocol = _protocol(view)
    result = evaluate_replay(protocol, view, select_replay_actions(protocol, view), _ledger(view))
    summary_raw = result.summaries[0].to_dict()
    summary_raw["comparison_verdict"] = "scientific_pass"
    forged_summary = result.summaries[0].model_copy(update={"comparison_verdict": "scientific_pass"})
    result_raw = result.to_dict()
    result_raw["summaries"][0] = forged_summary  # type: ignore[index]
    _resign(result_raw, "result_id", "replay_result_")
    with pytest.raises((ExperimentDesignContractError, ValidationError)):
        ReplayResultV1.model_validate(result_raw)

    class EvilCellContext(CellContext):
        production_promoted: bool = True
        prediction: tuple[float, ...] = (1.0,)

    request = _request()
    evil_context = EvilCellContext.model_validate(
        {
            **request.cell_context.to_dict(),
            "production_promoted": True,
            "prediction": (1.0,),
        }
    )
    forged_request = request.model_copy(update={"cell_context": evil_context})
    with pytest.raises(ExperimentDesignContractError):
        compile_contract_only_experiment(
            request=forged_request,
            question="q",
            hypothesis="h",
        )


@pytest.mark.parametrize(
    "field",
    (
        "cell_scope_fingerprint",
        "model_scope_fingerprint",
        "pack_fingerprint",
        "evidence_fingerprint",
        "calibration_fingerprint",
        "ood_fingerprint",
        "endpoint",
    ),
)
def test_selection_view_rejects_mixed_comparator_domains(field: str) -> None:
    raw = _view().to_dict()
    action = raw["rows"][1]["action"]  # type: ignore[index]
    action[field] = "different_endpoint" if field == "endpoint" else _fp(f"different-{field}")
    parsed_actions = [
        ExperimentActionV1.from_dict(row["action"])  # type: ignore[index]
        for row in raw["rows"]  # type: ignore[union-attr]
    ]
    raw["action_catalog_fingerprint"] = _fingerprint([action.fingerprint() for action in parsed_actions])
    with pytest.raises(ExperimentDesignContractError, match="mix comparator domain"):
        ReplaySelectionViewV1.from_dict(raw)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("control_id", "synthetic-gene-0"),
        ("replicate_count", 0),
        ("batch_ids", ["duplicate", "duplicate"]),
        ("planned_cost", "NaN"),
        ("planned_cost", "01"),
        ("planned_cost", "-1"),
        ("endpoint_unit", "bananas"),
        ("cost_unit", "USD"),
        ("feasibility_status", "feasible"),
        ("external_execution_allowed", True),
        ("scientifically_validated", True),
        ("production_promoted", True),
    ),
)
def test_invalid_action_design_and_status_are_rejected(field: str, value: object) -> None:
    raw = _action(0).to_dict()
    raw[field] = value
    with pytest.raises((ExperimentDesignContractError, ValidationError)):
        ExperimentActionV1.from_dict(raw)


def test_protocol_rejects_identity_or_outcome_access_drift_even_when_resigned() -> None:
    protocol = _protocol()
    for field, value in (
        ("strategies", ["active_heuristic", "random"]),
        ("tie_breaker", "random"),
        ("outcome_access_policy", "selector_may_read_outcomes"),
        ("selector_outcome_access_allowed", True),
        ("group_split_fingerprint", "0" * 64),
    ):
        raw = protocol.to_dict()
        raw[field] = value
        _resign(raw, "protocol_id", "replay_protocol_")
        if field == "group_split_fingerprint":
            forged = ReplayProtocolV1.from_dict(raw)
            with pytest.raises(ExperimentDesignContractError, match="does not match"):
                select_replay_actions(forged, _view())
        else:
            with pytest.raises(ExperimentDesignContractError):
                ReplayProtocolV1.from_dict(raw)

    random_split = _view().to_dict()
    random_split["split_method"] = "random"
    with pytest.raises(ExperimentDesignContractError):
        ReplaySelectionViewV1.from_dict(random_split)
