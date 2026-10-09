"""One-command, held-out Golden Norman baseline prediction.

The caller supplies the already downloaded H5AD.  Network access, identifier
conversion, split generation, model discovery, and scientific promotion are
intentionally outside this runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from collections.abc import Sequence
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from praxis_virtualcell.benchmarks.golden_norman import (
    GoldenNormanError,
    _canonical_hash,
    _coerce_contract,
    _pack_condition_deltas,
    _stable_runtime_evidence,
    _write_json,
    build_baseline_assets,
    condition_macro_mse,
    derive_pack,
)
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.core.request_v2 import legacy_request_to_v2
from praxis_virtualcell.data_packs.registry import PackRegistry
from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.capability_registry import ExecutionPlan
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
from praxis_virtualcell.workflows.run_virtualcell_query import run_formal_query

_BASELINE = "additive_linear"
_MODEL_NAME = "norman_additive_linear"


def _request_id(condition_id: str, targets: Sequence[str]) -> str:
    payload = json.dumps(
        [condition_id, *targets],
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return f"golden-held-out-{hashlib.sha256(payload).hexdigest()[:16]}"


def _run_condition(
    pack_root: Path,
    model_cache_root: Path,
    registry_root: Path,
    output_path: Path,
    condition_id: str,
    contract: dict[str, Any],
) -> dict[str, Any]:
    manifest, truth, targets, partitions, feature_ids = _pack_condition_deltas(pack_root)
    if condition_id not in truth:
        raise GoldenNormanError(f"unknown non-control condition: {condition_id!r}")
    partition = partitions[condition_id]
    if partition != "test":
        raise GoldenNormanError(f"condition must be in the frozen test partition, got {partition!r}")
    target_ids = list(targets[condition_id])
    if not target_ids:
        raise GoldenNormanError("held-out condition has no canonical targets")

    packs = PackRegistry()
    packs.register(pack_root)
    zoo = ModelZooRegistry(registry_path=str(registry_root / f"{_BASELINE}.yaml"))
    if zoo.capability_names() != [_MODEL_NAME]:
        raise GoldenNormanError("runner requires the frozen additive one-card registry")
    cache = ModelCache(root=str(model_cache_root))
    request_id = _request_id(condition_id, target_ids)
    request_dict = {
        "request_id": request_id,
        "species": "human",
        "cell_type": "K562",
        # P8 v1 represents a combination as ordered gene targets.  This is
        # recorded below and must not be presented as strict P16R binding.
        "perturbation_type": "gene",
        "perturbation_targets": target_ids,
        "input_modality": "scRNA",
        "output_modality": "delta_expression",
        "task_type": "predict_delta_expression",
    }
    expected_request = VirtualCellRequest.from_dict(request_dict)
    expected_request_payload = asdict(expected_request)
    expected_request_fingerprint = _canonical_hash(legacy_request_to_v2(expected_request).to_dict())
    result = run_formal_query(
        request_dict,
        config=RuntimeConfig(mode=Mode.OFFLINE, llm_enabled=False),
        enable_llm_report=False,
        pack_id=manifest.pack_id,
        pack_version=manifest.pack_version,
        pack_registry=packs,
        model_registry=zoo,
        model_cache=cache,
    )
    report = result.get("structured_report")
    if not isinstance(report, dict):
        raise GoldenNormanError("formal runtime did not return a structured report")
    if report.get("abstain") is not False or report.get("models_used") != [_MODEL_NAME]:
        raise GoldenNormanError("formal runtime abstained or selected another model")
    if result.get("llm_used_for_prediction") is not False:
        raise GoldenNormanError("formal runtime must not use an LLM for prediction")
    trace = result.get("trace")
    if not isinstance(trace, list) or any(not isinstance(item, dict) for item in trace):
        raise GoldenNormanError("formal runtime trace is invalid")
    if any(
        "Mock" in str(item.get(role, "")) or "CaseRunner" in str(item.get(role, ""))
        for item in trace
        for role in ("sender", "receiver")
    ):
        raise GoldenNormanError("formal trace contains a legacy predictor")
    prediction = report.get("prediction")
    if not isinstance(prediction, dict):
        raise GoldenNormanError("formal runtime did not return a prediction")
    raw_delta = prediction.get("delta")
    if (
        not isinstance(raw_delta, list)
        or any(type(value) is not float for value in raw_delta)
        or any(not np.isfinite(value) for value in raw_delta)
    ):
        raise GoldenNormanError("formal runtime prediction must be finite float values")
    vector = np.asarray(raw_delta, dtype=np.float64)
    if vector.shape != (len(feature_ids),) or not np.isfinite(vector).all():
        raise GoldenNormanError("formal runtime prediction violates feature contract")
    if (
        prediction.get("baseline") != _BASELINE
        or prediction.get("n_features") != len(feature_ids)
        or prediction.get("feature_ids_sha256") != _canonical_hash(feature_ids)
        or prediction.get("value_type") != "delta_expression"
    ):
        raise GoldenNormanError("formal runtime prediction metadata changed")

    provenance = report.get("provenance")
    if not isinstance(provenance, dict):
        raise GoldenNormanError("formal runtime provenance is invalid")
    raw_reports = provenance.get("compatibility_reports")
    try:
        plan = ExecutionPlan.model_validate(provenance.get("execution_plan"))
    except Exception as exc:
        raise GoldenNormanError("formal execution plan is invalid") from exc
    if not isinstance(raw_reports, list) or len(raw_reports) != 1:
        raise GoldenNormanError("runner requires one compatibility report")
    if len(plan.steps) != 1 or len(plan.reports) != 1:
        raise GoldenNormanError("runner requires one report and one execution step")
    compatibility = plan.reports[0]
    step = plan.steps[0]
    expected_pack = manifest.fingerprint()
    expected_plan_payload = deepcopy(provenance["execution_plan"])
    expected_plan_payload["reports"] = [compatibility.to_dict()]
    expected_plan_payload["steps"] = [step.to_dict()]
    identity = {
        "request_id": plan.request_id,
        "request_fingerprint": plan.request_fingerprint,
        "pack_fingerprint": plan.pack_fingerprint,
        "environment_fingerprint": plan.environment_fingerprint,
        "reports": [compatibility.fingerprint()],
        "steps": [step.to_dict()],
    }
    expected_plan_id = f"plan_{_canonical_hash(identity)[:24]}"
    if not (
        plan.to_dict() == expected_plan_payload
        and plan.plan_id == expected_plan_id
        and report.get("request") == expected_request_payload
        and plan.request_fingerprint == expected_request_fingerprint
        and plan.request_id == report.get("request_id") == request_id
        and plan.pack_id == manifest.pack_id
        and plan.pack_version == manifest.pack_version
        and plan.pack_fingerprint == expected_pack
        and compatibility.to_dict() == raw_reports[0]
        and compatibility.request_id == plan.request_id
        and compatibility.request_fingerprint == plan.request_fingerprint
        and compatibility.pack_id == plan.pack_id
        and compatibility.pack_version == plan.pack_version
        and compatibility.pack_fingerprint == plan.pack_fingerprint
        and compatibility.environment_fingerprint == plan.environment_fingerprint
        and compatibility.model_name == step.model_name == _MODEL_NAME
        and compatibility.model_version == step.model_version
        and compatibility.model_fingerprint == step.model_fingerprint
        and compatibility.fingerprint() == step.compatibility_fingerprint
    ):
        raise GoldenNormanError("formal execution identities do not close")
    if plan.executable is not True or plan.legacy_adapter is not False:
        raise GoldenNormanError("runner requires a non-legacy executable plan")
    if (
        compatibility.pack_valid is not True
        or compatibility.model_compatible is not True
        or compatibility.scientifically_validated is not False
    ):
        raise GoldenNormanError("formal compatibility state changed")
    compatibility_hash, report_hash = _stable_runtime_evidence(
        report,
        compatibility.to_dict(),
        step.to_dict(),
    )
    score, losses = condition_macro_mse(
        {condition_id: truth[condition_id]},
        {condition_id: vector},
    )
    record = {
        "schema_version": "vc.golden-condition-run.v1",
        "record_role": "held_out_real_data_baseline_not_scientific_evidence",
        "benchmark_id": contract["benchmark_id"],
        "contract_sha256": _canonical_hash(contract),
        "condition": {
            "id": condition_id,
            "partition": partition,
            "evaluation_scope": ("single_gene" if len(target_ids) == 1 else "combination"),
            "targets": target_ids,
            "legacy_perturbation_encoding": ("gene_with_multiple_ordered_targets" if len(target_ids) > 1 else None),
        },
        "pack": {
            "id": manifest.pack_id,
            "version": manifest.pack_version,
            "fingerprint": manifest.fingerprint(),
        },
        "model": {
            "baseline": _BASELINE,
            "name": _MODEL_NAME,
            "fingerprint": compatibility.model_fingerprint,
            "scientifically_validated": False,
        },
        "prediction": {
            "delta": vector.tolist(),
            "sha256": _canonical_hash(vector.tolist()),
            "n_features": len(feature_ids),
            "feature_ids_sha256": _canonical_hash(feature_ids),
            "value_type": "delta_expression",
            "unseen_train_targets": prediction.get("unseen_train_targets", []),
        },
        "observation": {
            "truth_sha256": _canonical_hash(truth[condition_id].tolist()),
            "definition": contract["metric"]["truth"],
        },
        "metric": {
            **contract["metric"],
            "aggregation": "one_frozen_test_condition",
            "score": score,
            "condition_loss": losses[condition_id],
        },
        "runtime": {
            "request_id": report["request_id"],
            "request_fingerprint": plan.request_fingerprint,
            "plan_id": plan.plan_id,
            "environment_fingerprint": plan.environment_fingerprint,
            "plan_legacy_adapter": plan.legacy_adapter,
            "compatibility_contract_sha256": compatibility_hash,
            "report_contract_sha256": report_hash,
            "legacy_predictors_registered": False,
            "llm_used_for_prediction": False,
        },
        "states": {
            "real_data_used": True,
            "execution_performed": True,
            "pack_valid": True,
            "model_compatible": True,
            "scientifically_validated": False,
            "production_promoted": False,
            "p16r_run": False,
            "benchmark_evidence_created": False,
            "policy_changed": False,
        },
    }
    _write_json(output_path, record)
    return record


def run_golden_condition(
    source_h5ad: str | Path,
    output_dir: str | Path,
    *,
    condition_id: str = "AHR+KLF1",
) -> dict[str, Any]:
    """Derive, fit, formally predict, and score one held-out condition."""

    if not isinstance(condition_id, str) or not condition_id:
        raise GoldenNormanError("condition_id must be a non-empty string")
    source = Path(source_h5ad).resolve()
    raw_output = Path(output_dir)
    if not raw_output.is_absolute():
        raise GoldenNormanError("output_dir must be absolute")
    if raw_output.exists() or raw_output.is_symlink():
        raise GoldenNormanError(f"output directory already exists: {raw_output}")
    output = raw_output.resolve()
    if not output.parent.is_dir():
        raise GoldenNormanError("output parent must already exist")
    value = _coerce_contract(None)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=str(output.parent)))
    try:
        pack = derive_pack(source, temporary / "pack", contract=value)
        build_baseline_assets(
            pack,
            temporary / "model_cache",
            temporary / "registries",
            contract=value,
        )
        record = _run_condition(
            pack,
            temporary / "model_cache",
            temporary / "registries",
            temporary / "prediction.json",
            condition_id,
            value,
        )
        if output.exists() or output.is_symlink():
            raise GoldenNormanError(f"output directory appeared during run: {output}")
        temporary.replace(output)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return record


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen Golden Norman additive baseline on one held-out "
            "condition. The source H5AD must already be downloaded and verified."
        )
    )
    parser.add_argument("--source-h5ad", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--condition-id", default="AHR+KLF1")
    args = parser.parse_args(argv)
    record = run_golden_condition(
        args.source_h5ad,
        args.output_dir,
        condition_id=args.condition_id,
    )
    summary = {
        "output": str(args.output_dir.resolve() / "prediction.json"),
        "condition_id": record["condition"]["id"],
        "partition": record["condition"]["partition"],
        "mse": record["metric"]["score"],
        "scientifically_validated": False,
        "production_promoted": False,
    }
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
