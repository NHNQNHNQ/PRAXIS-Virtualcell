#!/usr/bin/env python3
"""Verify the exact outcome-blind K562 CRISPRa acquisition plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any


class AcquisitionPlanError(RuntimeError):
    """The acquisition plan is not the frozen value-free plan."""


_PLAN_SIZE = 388249
_PLAN_SHA256 = "07cc18bb20ad5e27c8795ff74b6024ae16c4e0b4b12c31e2761dbf3bc7ce98ee"
_PLAN_PAYLOAD_SHA256 = "b6ad8d74a5ae8e9f928f8356e9f3f6a43c323eff7b31159d4ef70b10aead4643"
_FEATURE_IDS_SHA256 = "ecca6c636629e35ae5f5a0ec6fe84c1a7983e1adb263fbbcaea70a0c5495b2b7"
_FEATURE_SYMBOLS_SHA256 = "76ed3a702c1cb54b4c957facdbf9ceb565cdacac1de5dbbd93dd62acd37c013b"
_TARGET_IDS_SHA256 = "2bc167c08c3b7a822ddfa626af55e515078a29ba13463607d70419692f777e57"
_TARGET_SYMBOLS_SHA256 = "0b386c66f34557efa721dc4857903a1789b483a7c305bda3dc08da8d7ab4831b"
_TARGET_MAPPING_SHA256 = "feed4e4e33bad71b498c95345e396dfce1fdadccac0768448c5df7c8e8e8fb37"
_PRIMARY_CONDITION_SET_SHA256 = "30f015924978feefd1eb29bb9e1a47a10f632d74c6bd6fe68f63c39a9b8383ea"
_EXTERNAL_CONDITION_SET_SHA256 = "29c16fbeda05db178fd6d01908d2f1ec01cac6b0e017ad1796f4f4e297716210"
_EXTERNAL_PAIR_PAYLOAD_SHA256 = "d069f6674236a9a7806fb253000b2ff2a9d40f4d878cc81b47e36e684bd995da"
_ENSEMBL = re.compile(r"ENSG[0-9]{11}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fingerprint(value: object) -> str:
    return _sha256(_canonical_bytes(value))


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise AcquisitionPlanError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise AcquisitionPlanError(f"non-finite JSON number: {value}")


def _load_plan(path: Path) -> dict[str, Any]:
    if not path.is_absolute() or path.is_symlink():
        raise AcquisitionPlanError("plan path must be absolute and non-symlink")
    resolved = path.resolve(strict=True)
    if resolved != path:
        raise AcquisitionPlanError("plan path must be canonical")
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise AcquisitionPlanError("platform lacks O_NOFOLLOW")
    try:
        descriptor = os.open(path, os.O_RDONLY | nofollow)
    except OSError as exc:
        raise AcquisitionPlanError("plan cannot be opened safely") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise AcquisitionPlanError("plan must be a single-link regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (before.st_dev, before.st_ino, before.st_size) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
    ):
        raise AcquisitionPlanError("plan changed while it was read")
    raw = b"".join(chunks)
    if len(raw) != _PLAN_SIZE or _sha256(raw) != _PLAN_SHA256:
        raise AcquisitionPlanError("plan raw identity is not frozen")
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise AcquisitionPlanError("plan is not strict JSON") from exc
    if type(value) is not dict or raw != _canonical_bytes(value) + b"\n":
        raise AcquisitionPlanError("plan must be canonical JSON plus one newline")
    return value


def _hash(value: object, field: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise AcquisitionPlanError(f"{field} must be a lowercase SHA-256")
    return value


def _verify_identity(plan: dict[str, Any]) -> None:
    identity = plan.get("identity")
    if type(identity) is not dict or set(identity) != {
        "payload_hash_algorithm",
        "payload_sha256",
    }:
        raise AcquisitionPlanError("plan identity is malformed")
    if identity["payload_hash_algorithm"] != ("sha256(canonical_json(plan_with_identity.payload_sha256_set_to_null))"):
        raise AcquisitionPlanError("plan payload hash algorithm drifted")
    expected = _hash(identity["payload_sha256"], "identity.payload_sha256")
    probe = json.loads(json.dumps(plan, allow_nan=False))
    probe["identity"]["payload_sha256"] = None
    if expected != _PLAN_PAYLOAD_SHA256 or _fingerprint(probe) != expected:
        raise AcquisitionPlanError("plan logical self-hash is invalid")


def _verify_claim_ceiling(plan: dict[str, Any]) -> None:
    if not (
        plan.get("schema_version") == "praxis.k562-crispra-acquisition-plan.v1"
        and plan.get("record_role") == "outcome_blind_prospective_acquisition_plan_not_scientific_evidence"
        and plan.get("plan_status")
        == {
            "status": "READY_FOR_QUOTE_NOT_WET_LAB_EXECUTION",
            "wet_lab_execution_authorized": False,
            "guide_map_frozen": False,
            "construct_sequence_identity_frozen": False,
            "provider_and_custodian_selected": False,
            "outcome_values_accessed": False,
            "benchmark_status": "NOT_RUN",
            "benchmark_passed": None,
            "scientifically_validated": False,
            "promotion_eligible": False,
            "production_promoted": False,
            "registry_or_default_route_changed": False,
        }
    ):
        raise AcquisitionPlanError("plan status exceeds the quote-only claim ceiling")
    provenance = plan.get("source_provenance")
    if type(provenance) is not dict or not (
        provenance.get("condition_selection_used_expression_or_outcomes") is False
        and provenance.get("train_only_h5ad", {}).get("expression_matrix_read") is False
        and provenance.get("train_only_h5ad", {}).get("validation_or_test_partition_read") is False
    ):
        raise AcquisitionPlanError("plan does not preserve the outcome-blind source boundary")


def _verify_axes(plan: dict[str, Any]) -> tuple[list[str], dict[str, str], dict[str, int]]:
    axes = plan.get("axes")
    if type(axes) is not dict:
        raise AcquisitionPlanError("axes are missing")
    feature_axis = axes.get("feature_axis")
    target_axis = axes.get("target_axis")
    if type(feature_axis) is not dict or type(target_axis) is not dict:
        raise AcquisitionPlanError("feature or target axis is missing")

    feature_records = feature_axis.get("records")
    if type(feature_records) is not list or len(feature_records) != 5045:
        raise AcquisitionPlanError("feature axis must contain exactly 5,045 records")
    feature_ids: list[str] = []
    feature_symbols: list[str] = []
    for index, record in enumerate(feature_records):
        if type(record) is not dict or set(record) != {"index", "ensembl_gene_id", "symbol"}:
            raise AcquisitionPlanError("feature record is malformed")
        gene_id = record["ensembl_gene_id"]
        symbol = record["symbol"]
        if (
            record["index"] != index
            or type(gene_id) is not str
            or _ENSEMBL.fullmatch(gene_id) is None
            or type(symbol) is not str
            or not symbol
            or symbol.strip() != symbol
        ):
            raise AcquisitionPlanError("feature record identity is invalid")
        feature_ids.append(gene_id)
        feature_symbols.append(symbol)
    if len(set(feature_ids)) != 5045:
        raise AcquisitionPlanError("feature IDs must be unique")
    if not (
        feature_axis.get("count") == 5045
        and feature_axis.get("namespace") == "EnsemblGene"
        and feature_axis.get("version") == "Ensembl 84"
        and feature_axis.get("ordered_ids_sha256") == _FEATURE_IDS_SHA256
        and feature_axis.get("ordered_symbols_sha256") == _FEATURE_SYMBOLS_SHA256
        and _fingerprint(feature_ids) == _FEATURE_IDS_SHA256
        and _fingerprint(feature_symbols) == _FEATURE_SYMBOLS_SHA256
    ):
        raise AcquisitionPlanError("feature axis identity drifted")

    target_records = target_axis.get("records")
    if type(target_records) is not list or len(target_records) != 68:
        raise AcquisitionPlanError("target axis must contain exactly 68 records")
    target_ids: list[str] = []
    target_symbols: list[str] = []
    for index, record in enumerate(target_records):
        if type(record) is not dict or set(record) != {"index", "ensembl_gene_id", "symbol"}:
            raise AcquisitionPlanError("target record is malformed")
        target_id = record["ensembl_gene_id"]
        target_symbol = record["symbol"]
        if (
            record["index"] != index
            or type(target_id) is not str
            or _ENSEMBL.fullmatch(target_id) is None
            or type(target_symbol) is not str
            or not target_symbol
        ):
            raise AcquisitionPlanError("target record identity is invalid")
        target_ids.append(target_id)
        target_symbols.append(target_symbol)
    mapping = [
        {"target_id": target_id, "symbol": symbol} for target_id, symbol in zip(target_ids, target_symbols, strict=True)
    ]
    feature_by_id = dict(zip(feature_ids, feature_symbols, strict=True))
    if not (
        target_ids == sorted(target_ids)
        and len(set(target_ids)) == 68
        and len(set(target_symbols)) == 68
        and all(
            feature_by_id.get(target_id) == symbol for target_id, symbol in zip(target_ids, target_symbols, strict=True)
        )
        and target_axis.get("count") == 68
        and target_axis.get("namespace") == "EnsemblGene"
        and target_axis.get("version") == "Ensembl 84"
        and target_axis.get("ordered_ids_sha256") == _TARGET_IDS_SHA256
        and target_axis.get("ordered_symbols_sha256") == _TARGET_SYMBOLS_SHA256
        and target_axis.get("ordered_id_symbol_pairs_sha256") == _TARGET_MAPPING_SHA256
        and _fingerprint(target_ids) == _TARGET_IDS_SHA256
        and _fingerprint(target_symbols) == _TARGET_SYMBOLS_SHA256
        and _fingerprint(mapping) == _TARGET_MAPPING_SHA256
    ):
        raise AcquisitionPlanError("target axis identity drifted")
    return (
        target_ids,
        dict(zip(target_ids, target_symbols, strict=True)),
        {target_id: index for index, target_id in enumerate(target_ids)},
    )


def _condition_payload(
    value: dict[str, Any],
    target_ids: list[str],
    symbols: dict[str, str],
    index: dict[str, int],
) -> tuple[dict[str, Any], list[tuple[str, str]]]:
    singles = value.get("single_gene")
    combinations = value.get("gene_combination")
    control = value.get("matched_non_targeting_control")
    if type(singles) is not list or type(combinations) is not list or type(control) is not dict:
        raise AcquisitionPlanError("condition set is malformed")
    expected_singles = [
        {
            "condition_label": f"{symbols[target_id]}+ctrl",
            "target_id": target_id,
            "target_symbol": symbols[target_id],
        }
        for target_id in target_ids
    ]
    if singles != expected_singles or control != {"condition_label": "ctrl", "required": True}:
        raise AcquisitionPlanError("single or control condition identity drifted")
    pairs: list[tuple[str, str]] = []
    expected_combinations: list[dict[str, str]] = []
    for item in combinations:
        if type(item) is not dict or set(item) != {
            "condition_label",
            "target_a_id",
            "target_a_symbol",
            "target_b_id",
            "target_b_symbol",
        }:
            raise AcquisitionPlanError("combination condition is malformed")
        a = item["target_a_id"]
        b = item["target_b_id"]
        if a not in index or b not in index or index[a] >= index[b]:
            raise AcquisitionPlanError("combination target order is not canonical")
        expected = {
            "condition_label": f"{symbols[a]}+{symbols[b]}",
            "target_a_id": a,
            "target_a_symbol": symbols[a],
            "target_b_id": b,
            "target_b_symbol": symbols[b],
        }
        if item != expected:
            raise AcquisitionPlanError("combination condition label or mapping drifted")
        pairs.append((a, b))
        expected_combinations.append(expected)
    if (
        len(pairs) != 36
        or len(set(pairs)) != 36
        or pairs != sorted(pairs, key=lambda pair: (index[pair[0]], index[pair[1]]))
    ):
        raise AcquisitionPlanError("combination conditions must be 36 unique canonical pairs")
    payload = {
        "single_gene": expected_singles,
        "gene_combination": expected_combinations,
        "matched_non_targeting_control": control,
    }
    if not (
        value.get("single_gene_count") == 68
        and value.get("gene_combination_count") == 36
        and value.get("condition_group_count_including_control") == 105
        and value.get("condition_set_payload_sha256") == _fingerprint(payload)
    ):
        raise AcquisitionPlanError("condition set counts or fingerprint drifted")
    return payload, pairs


def _external_pairs(
    target_ids: list[str],
    train_pairs: set[tuple[str, str]],
    index: dict[str, int],
) -> tuple[list[tuple[str, str]], int]:
    prefix = b"praxis.k562-crispra.external-pair-order.v1\0"
    ordered = sorted(
        target_ids,
        key=lambda target_id: (
            hashlib.sha256(prefix + target_id.encode("utf-8")).digest(),
            target_id,
        ),
    )
    tail = ordered[1:]
    selected: list[tuple[str, str]] | None = None
    selected_round: int | None = None
    for round_index in range(67):
        values = [ordered[0], *tail[round_index:], *tail[:round_index]]
        pairs = [tuple(sorted((values[k], values[67 - k]), key=index.__getitem__)) for k in range(34)]
        if not set(pairs).intersection(train_pairs):
            selected = pairs
            selected_round = round_index
            break
    if selected is None or selected_round is None:
        raise AcquisitionPlanError("external matching cannot be reproduced")
    selected_set = set(selected)
    extra_prefix = b"praxis.k562-crispra.external-pair-extra.v1\0"
    allowed = [
        (a, b)
        for position, a in enumerate(target_ids)
        for b in target_ids[position + 1 :]
        if (a, b) not in train_pairs and (a, b) not in selected_set
    ]
    allowed.sort(
        key=lambda pair: (
            hashlib.sha256(extra_prefix + pair[0].encode("utf-8") + b"\0" + pair[1].encode("utf-8")).digest(),
            pair,
        )
    )
    first = allowed[0]
    second = next(pair for pair in allowed[1:] if not set(pair).intersection(first))
    final = sorted([*selected, first, second], key=lambda pair: (index[pair[0]], index[pair[1]]))
    return final, selected_round


def _verify_conditions(
    plan: dict[str, Any], target_ids: list[str], symbols: dict[str, str], index: dict[str, int]
) -> None:
    design = plan.get("condition_design")
    if type(design) is not dict:
        raise AcquisitionPlanError("condition design is missing")
    primary_value = design.get("replacement_primary_holdout")
    external_value = design.get("independent_external_dataset_and_platform")
    selection = design.get("external_pair_selection")
    if type(primary_value) is not dict or type(external_value) is not dict or type(selection) is not dict:
        raise AcquisitionPlanError("condition design roles are malformed")
    primary_payload, primary_pairs = _condition_payload(primary_value, target_ids, symbols, index)
    external_payload, external_pairs = _condition_payload(external_value, target_ids, symbols, index)
    reproduced, selected_round = _external_pairs(target_ids, set(primary_pairs), index)
    degrees = {target_id: sum(target_id in pair for pair in reproduced) for target_id in target_ids}
    pair_payload = [{"target_a_id": a, "target_b_id": b} for a, b in reproduced]
    if not (
        _fingerprint(primary_payload) == _PRIMARY_CONDITION_SET_SHA256
        and _fingerprint(external_payload) == _EXTERNAL_CONDITION_SET_SHA256
        and external_pairs == reproduced
        and not set(primary_pairs).intersection(external_pairs)
        and selection.get("selected_zero_train_overlap_round") == selected_round == 0
        and selection.get("training_pair_overlap_count") == 0
        and selection.get("covered_target_count") == 68
        and selection.get("minimum_target_degree") == min(degrees.values()) == 1
        and selection.get("maximum_target_degree") == max(degrees.values()) == 2
        and selection.get("degree_one_target_count") == sum(value == 1 for value in degrees.values()) == 64
        and selection.get("degree_two_target_count") == sum(value == 2 for value in degrees.values()) == 4
        and selection.get("pair_payload_sha256") == _fingerprint(pair_payload) == _EXTERNAL_PAIR_PAYLOAD_SHA256
        and selection.get("expression_or_outcome_used") is False
    ):
        raise AcquisitionPlanError("outcome-free external pair selection drifted")


def _verify_wet_lab_and_custody(plan: dict[str, Any]) -> None:
    wet = plan.get("wet_lab_contract")
    custody = plan.get("custody_and_delivery_contract")
    change = plan.get("change_control")
    if type(wet) is not dict or type(custody) is not dict or type(change) is not dict:
        raise AcquisitionPlanError("wet-lab, custody, or change-control contract is missing")
    scope = wet.get("shared_scope", {})
    timing = scope.get("timepoint", {}) if type(scope) is dict else {}
    replication = wet.get("replication_and_qc", {})
    platforms = wet.get("role_specific_platforms", {})
    if not (
        scope.get("cellosaurus_id") == "CVCL_0004"
        and scope.get("reference_depositor_identity") == "ATCC CCL-243"
        and scope.get("crispra_system") == "dCas9-SunTag/scFv-VP64"
        and scope.get("crispra_substitutions_allowed") is False
        and scope.get("exact_guide_sequences_and_construct_bytes_must_be_frozen_before_execution") is True
        and scope.get("whole_transcriptome_required") is True
        and scope.get("direct_guide_capture_required") is True
        and timing
        == {
            "t0": "completion_of_library_transduction_and_washout",
            "guide_positive_selection_hours_after_t0": 72,
            "harvest_hours_after_t0": 120,
            "maximum_absolute_harvest_deviation_minutes": 15,
            "actual_timestamps_required": True,
        }
        and replication.get("biological_replicate_count_per_role") == 3
        and replication.get("minimum_qc_singlets_per_condition_per_replicate") == 100
        and replication.get("minimum_qc_matched_non_targeting_control_cells_per_replicate") == 1000
        and replication.get("quote_target_capture_multiplier_over_acceptance_floor") == 2.0
        and replication.get("formal_statistical_unit") == "biological_condition"
        and replication.get("cells_are_independent_statistical_units") is False
        and replication.get("qc_floor_change_after_data_generation_allowed") is False
        and replication.get("failed_floor_requires_write_new_rerun") is True
        and platforms.get("replacement_primary_holdout", {}).get("required_platform_family")
        == "10x_Chromium_whole_transcriptome_plus_CRISPR_Guide_Capture"
        and platforms.get("independent_external_dataset_and_platform", {}).get("required_platform_family")
        == "Parse_Evercode_WT_plus_CRISPR_Detect"
        and platforms.get("independent_external_dataset_and_platform", {}).get("non_10x_platform_required") is True
    ):
        raise AcquisitionPlanError("wet-lab scope, timing, platform, replicate, or QC gate drifted")
    if not (
        custody.get("independent_custodian_required") is True
        and custody.get("candidate_team_receives_outcome_bytes_before_evaluation_lock") is False
        and custody.get("evaluation_client_projection_reorder_fill_or_imputation_allowed") is False
        and custody.get("consumer_adaptation_steps") == 0
        and custody.get("provider_lab_platform_dataset_and_custodian_identities_must_differ_between_roles") is True
        and change.get("outcome_based_provider_condition_guide_qc_or_rerun_selection_allowed") is False
    ):
        raise AcquisitionPlanError("custody or outcome-blind change control drifted")


def verify_plan(path: Path) -> dict[str, Any]:
    plan = _load_plan(path)
    _verify_identity(plan)
    _verify_claim_ceiling(plan)
    target_ids, symbols, index = _verify_axes(plan)
    _verify_conditions(plan, target_ids, symbols, index)
    _verify_wet_lab_and_custody(plan)
    return {
        "schema_version": "praxis.k562-crispra-acquisition-plan-verification.v1",
        "status": "VERIFIED_READY_FOR_QUOTE_NOT_WET_LAB_EXECUTION",
        "plan_sha256": _PLAN_SHA256,
        "plan_payload_sha256": _PLAN_PAYLOAD_SHA256,
        "feature_count": 5045,
        "target_count": 68,
        "primary_single_count": 68,
        "primary_combination_count": 36,
        "external_single_count": 68,
        "external_unseen_combination_count": 36,
        "outcome_values_accessed": False,
        "benchmark_status": "NOT_RUN",
        "benchmark_passed": None,
        "scientifically_validated": False,
        "wet_lab_execution_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify_plan(args.plan)
    except (AcquisitionPlanError, OSError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "schema_version": "praxis.k562-crispra-acquisition-plan-verification.v1",
                    "status": "FAILED",
                    "error": str(exc),
                    "benchmark_status": "NOT_RUN",
                    "benchmark_passed": None,
                    "scientifically_validated": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
