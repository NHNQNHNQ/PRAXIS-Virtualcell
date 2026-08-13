#!/usr/bin/env python3
"""Run the frozen three-seed Norman GEARS full-training execution manifest."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import math
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).parents[1]
_SMOKE_RUNNER_PATH = _ROOT / "scripts/train_golden_gears_train_only_candidate.py"
_PROTOCOL_PATH = _ROOT / "data/golden/norman_2019/gears_train_only_protocol.json"
_RUN_MANIFEST_PATH = _ROOT / "data/golden/norman_2019/gears_train_only_full_run.json"
_SEEDS = (11, 23, 37)
_EPOCHS = 20
_BATCH_SIZE = 32
_SEED_FILES = {
    "candidate-record.json",
    "training.log",
    "model/config.pkl",
    "model/model.pt",
    "model/runtime-graph-manifest.json",
    "model/safe-config.json",
    "model/tensor-manifest.json",
}
_SEED_DIRECTORIES = {"model"}
_RAW_SHA256 = re.compile(r"[0-9a-f]{64}")


class FullTrainError(ValueError):
    """Fail-closed full-training worker error."""


def _smoke_runner():
    spec = importlib.util.spec_from_file_location("golden_gears_smoke_runner", _SMOKE_RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise FullTrainError("frozen smoke helper is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _manifest_expected(protocol: dict[str, Any], worker_sha256: str) -> dict[str, Any]:
    attestation = protocol["execution_boundary"]["prepared_artifact_attestation"]
    return {
        "schema_version": "praxis.golden-gears-train-only-full-run-manifest.v1",
        "identity": {
            "payload_sha256": None,
            "payload_hash_algorithm": "sha256(canonical_json(manifest_with_identity.payload_sha256_set_to_null))",
            "base_protocol_path": "data/golden/norman_2019/gears_train_only_protocol.json",
            "base_protocol_payload_sha256": protocol["identity"]["payload_sha256"],
            "worker_path": "scripts/run_golden_gears_train_only_full.py",
            "worker_sha256": worker_sha256,
            "smoke_helper_path": "scripts/train_golden_gears_train_only_candidate.py",
            "smoke_helper_sha256": protocol["identity"]["train_runner_sha256"],
        },
        "prepared_artifact_attestation": {
            "candidate_record_normalized": attestation["candidate_record_normalized"],
            "native_train_only_h5ad": attestation["native_train_only_h5ad"],
            "gears_assets": {
                "gears-data/gene2go_all.pkl": {
                    "size_bytes": protocol["downloads"]["gene2go"]["size_bytes"],
                    "sha256": protocol["downloads"]["gene2go"]["sha256"],
                },
                "gears-data/essential_all_data_pert_genes.pkl": {
                    "size_bytes": protocol["downloads"]["essential_genes"]["size_bytes"],
                    "sha256": protocol["downloads"]["essential_genes"]["sha256"],
                },
                "gears-data/go_essential_all/go_essential_all.csv": {
                    "size_bytes": protocol["downloads"]["go_graph"]["csv"]["size_bytes"],
                    "sha256": protocol["downloads"]["go_graph"]["csv"]["sha256"],
                },
            },
        },
        "execution": {
            "authorization_scope": "this_full_run_manifest_only",
            "base_protocol_train_status": "NOT_IMPLEMENTED_NOT_EXECUTABLE",
            "seeds": list(_SEEDS),
            "epochs_per_seed": _EPOCHS,
            "batch_size": _BATCH_SIZE,
            "device": "cpu",
            "checkpoint_selection_metric": "internal_validation_mse_de",
            "checkpoint_selection_precision": "full_float_from_gears_compute_metrics",
            "expected_compute_metrics_calls_per_seed": _EPOCHS * 2,
            "sequential_seed_order": True,
            "resume_policy": "strictly_verify_and_skip_completed_seed_write_new_missing_seed",
            "per_seed_publication": "atomic_no_replace_directory",
            "collection_publication": "atomic_no_replace_file_after_all_seeds_verify",
            "child_inputs": [
                "input/native_train_only.h5ad",
                "work/gene2go_all.pkl",
                "work/essential_all_data_pert_genes.pkl",
                "work/go_essential_all/go_essential_all.csv",
                "job.json",
            ],
            "output_layout": {
                "seed_directories": ["seed-11", "seed-23", "seed-37"],
                "per_seed_files": sorted(_SEED_FILES),
                "collection_record": "collection-record.json",
            },
            "runtime_graph_manifest": {
                "vocabulary_hash_algorithm": "sha256(canonical_json(ordered_string_list))",
                "tensor_content_hash_algorithm": "sha256(contiguous_cpu_numpy_tobytes)",
                "reconstruction_requirement": (
                    "evaluator_rebuilds_from_attested_prepare_artifacts_and_compares_exact_manifest"
                ),
            },
        },
        "data_boundary": {
            "golden_validation_expression_or_outcomes_read": False,
            "golden_test_expression_or_outcomes_read": False,
            "golden_validation_or_test_paths_provided_to_child": False,
            "golden_validation_test_metadata_audit_consumed": True,
            "internal_validation_source": "native_supported_golden_train_partition_only",
            "internal_validation_de_dropout_preprocessing_independent": False,
            "internal_validation_coexpression_graph_independent": True,
            "internal_validation_gradient_fit_excludes_validation": True,
            "internal_validation_checkpoint_selection_uses_validation": True,
            "filesystem_read_isolation": False,
            "network_denied_by_sandbox": True,
        },
        "record_roles": {
            "seed": "manifest_bound_full_training_candidate_not_scientific_evidence",
            "collection": "manifest_bound_full_training_collection_not_scientific_evidence",
        },
        "claim_ceiling": {
            "benchmark_status": "NOT_RUN",
            "benchmark_passed": None,
            "scientifically_validated": False,
            "promotion_eligible": False,
            "production_promoted": False,
            "registry_or_default_route_changed": False,
        },
    }


def _load_and_verify_manifest(smoke, builder, protocol: dict[str, Any]) -> tuple[dict[str, Any], str]:
    payload, _info = smoke._read_regular(_RUN_MANIFEST_PATH)
    manifest = smoke._json(payload, builder)
    worker_sha256 = builder._sha256(Path(__file__))
    normalized = copy.deepcopy(manifest)
    try:
        observed_payload_sha256 = normalized["identity"]["payload_sha256"]
        normalized["identity"]["payload_sha256"] = None
    except (KeyError, TypeError) as exc:
        raise FullTrainError("full-run manifest identity is invalid") from exc
    expected = _manifest_expected(protocol, worker_sha256)
    expected["identity"]["payload_sha256"] = observed_payload_sha256
    if not (
        manifest == expected
        and _RAW_SHA256.fullmatch(str(observed_payload_sha256))
        and builder._fingerprint(normalized) == observed_payload_sha256
        and protocol["execution_boundary"]["train_status"] == "NOT_IMPLEMENTED_NOT_EXECUTABLE"
        and protocol["training"]["training_seeds"] == list(_SEEDS)
        and protocol["training"]["model"]["max_epochs"] == _EPOCHS
        and protocol["training"]["model"]["batch_size"] == _BATCH_SIZE
    ):
        raise FullTrainError("full-run manifest identity or contract changed")
    return manifest, hashlib.sha256(payload).hexdigest()


def _execution_claim(seed: int) -> dict[str, Any]:
    return {
        "device": "cpu",
        "network_denied_by_sandbox": True,
        "filesystem_read_isolation": False,
        "child_input_inventory_restricted_to_attested_prepare_artifacts": True,
        "seed": seed,
        "epochs": _EPOCHS,
        "batch_size": _BATCH_SIZE,
        "internal_validation_de_dropout_preprocessing_independent": False,
        "internal_validation_coexpression_graph_independent": True,
        "internal_validation_gradient_fit_excludes_validation": True,
        "internal_validation_checkpoint_selection_uses_validation": True,
        "internal_validation_role": "technical_checkpoint_selection_only",
        "preprocessing_scope": "all_45450_native_supported_outer_train_rows_before_internal_split",
        "golden_validation_expression_or_outcomes_read": False,
        "golden_test_expression_or_outcomes_read": False,
        "golden_validation_or_test_paths_provided_to_child": False,
        "golden_validation_test_metadata_audit_consumed": True,
        "prospective_test_blinding": False,
        "test_loader_present": False,
    }


def _seed_record(
    *,
    seed: int,
    protocol: dict[str, Any],
    run_manifest: dict[str, Any],
    run_manifest_sha256: str,
    source_record: dict[str, Any],
    source_record_sha256: str,
    runtime: dict[str, Any],
    metrics: dict[str, Any],
    display_metrics: dict[str, Any],
    metrics_call_audit: dict[str, Any],
    log_record: dict[str, Any],
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    identity = run_manifest["identity"]
    return {
        "schema_version": "praxis.golden-gears-train-only-full-seed-candidate.v1",
        "record_role": run_manifest["record_roles"]["seed"],
        "candidate_name": protocol["candidate"]["name"],
        "mode": "full_train",
        "protocol_sha256": identity["base_protocol_payload_sha256"],
        "full_run_manifest_payload_sha256": identity["payload_sha256"],
        "full_run_manifest_sha256": run_manifest_sha256,
        "full_worker_sha256": identity["worker_sha256"],
        "smoke_helper_sha256": identity["smoke_helper_sha256"],
        "prepare_record_sha256": source_record_sha256,
        "prepare_input": source_record["derived_input_artifact"],
        "runtime": runtime,
        "execution": _execution_claim(seed),
        "internal_validation": metrics,
        "internal_validation_log_display": display_metrics,
        "metrics_call_audit": metrics_call_audit,
        "training_log": log_record,
        "contamination_audit": source_record["contamination_audit"],
        "prospective_test_blinding": False,
        "artifacts": artifacts,
        **run_manifest["claim_ceiling"],
    }


def _inventory(root: Path) -> None:
    root_info = root.lstat()
    if (
        not stat.S_ISDIR(root_info.st_mode)
        or root_info.st_uid != os.getuid()
        or stat.S_IMODE(root_info.st_mode) & 0o077
    ):
        raise FullTrainError("seed output must be a private operator-owned directory")
    files: set[str] = set()
    directories: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            directories.add(relative)
        elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
            files.add(relative)
        else:
            raise FullTrainError("seed output contains a symlink, linked file, or special entry")
    if files != _SEED_FILES or directories != _SEED_DIRECTORIES:
        raise FullTrainError("seed output inventory changed")


def _artifact_records(root: Path, builder) -> dict[str, Any]:
    return {
        "config.pkl": {
            **builder._file_record(root / "model/config.pkl", single_link=True),
            "unsafe_pickle": True,
        },
        "model.pt": {
            **builder._file_record(root / "model/model.pt", single_link=True),
            "weights_only_verified": True,
        },
        "tensor-manifest.json": builder._file_record(root / "model/tensor-manifest.json", single_link=True),
        "safe-config.json": builder._file_record(root / "model/safe-config.json", single_link=True),
        "runtime-graph-manifest.json": builder._file_record(
            root / "model/runtime-graph-manifest.json", single_link=True
        ),
        "training.log": builder._file_record(root / "training.log", single_link=True),
    }


def _recomputed_tensor_manifest(model_path: Path) -> dict[str, Any]:
    import torch

    state = torch.load(model_path, map_location="cpu", weights_only=True)
    if not isinstance(state, dict) or not state:
        raise FullTrainError("model checkpoint is empty or not a state dictionary")
    tensors = []
    for key, tensor in sorted(state.items()):
        if not isinstance(key, str) or not isinstance(tensor, torch.Tensor):
            raise FullTrainError("model checkpoint contains a non-tensor state")
        value = tensor.detach().cpu().contiguous()
        finite = not (value.is_floating_point() or value.is_complex()) or bool(torch.isfinite(value).all())
        if not finite:
            raise FullTrainError("model checkpoint contains a non-finite tensor")
        tensors.append(
            {
                "key": key,
                "shape": list(value.shape),
                "dtype": str(value.dtype),
                "numel": value.numel(),
                "sha256": hashlib.sha256(value.numpy().tobytes()).hexdigest(),
                "finite": True,
            }
        )
    return {
        "schema_version": "praxis.torch-state-tensor-manifest.v1",
        "weights_only": True,
        "tensor_count": len(tensors),
        "total_numel": sum(item["numel"] for item in tensors),
        "all_finite": True,
        "tensors": tensors,
    }


def _verify_log(root: Path, record: dict[str, Any], smoke) -> None:
    payload, _info = smoke._read_regular(root / "training.log")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise FullTrainError("published training log is not UTF-8") from exc
    if (
        not text.startswith("STDOUT\n\nSTDERR\n")
        or re.search(r"(?<![\w.])/(?:Users|Volumes|private|tmp|var)(?:/[^\s:]+)+", text)
        or record.get("internal_validation_log_display") != smoke._parse_metrics(text, _EPOCHS)
    ):
        raise FullTrainError("published training log or metrics changed")
    log_record = record.get("training_log", {})
    if log_record != {
        "raw_stdout_sha256": hashlib.sha256(b"").hexdigest(),
        "raw_stderr_sha256": log_record.get("raw_stderr_sha256"),
        "published_log_is_path_redacted": True,
    } or not _RAW_SHA256.fullmatch(str(log_record.get("raw_stderr_sha256"))):
        raise FullTrainError("training log receipt changed")


def _verify_full_precision_metrics(record: dict[str, Any]) -> None:
    internal = record.get("internal_validation")
    audit = record.get("metrics_call_audit")
    if not isinstance(internal, dict) or set(internal) != {
        "metric",
        "precision",
        "per_epoch",
        "best_epoch",
        "best_value",
    }:
        raise FullTrainError("full-precision internal validation receipt changed")
    per_epoch = internal["per_epoch"]
    if not (
        internal["metric"] == "internal_validation_mse_de"
        and internal["precision"] == "full_float_from_gears_compute_metrics"
        and isinstance(per_epoch, list)
        and [item.get("epoch") for item in per_epoch] == list(range(1, _EPOCHS + 1))
        and all(isinstance(item.get("value"), float) and math.isfinite(item["value"]) for item in per_epoch)
    ):
        raise FullTrainError("full-precision internal validation receipt changed")
    values = [item["value"] for item in per_epoch]
    best = min(range(_EPOCHS), key=values.__getitem__)
    if internal["best_epoch"] != best + 1 or internal["best_value"] != values[best]:
        raise FullTrainError("full-precision checkpoint selection changed")
    if not isinstance(audit, dict) or set(audit) != {
        "call_order",
        "expected_calls",
        "observed_calls",
        "per_epoch",
    }:
        raise FullTrainError("GEARS metrics call audit changed")
    audit_epochs = audit["per_epoch"]
    metric_keys = {"mse", "mse_de", "pearson", "pearson_de"}
    if not (
        audit["call_order"] == "train_then_validation_each_epoch"
        and audit["expected_calls"] == _EPOCHS * 2
        and audit["observed_calls"] == _EPOCHS * 2
        and isinstance(audit_epochs, list)
        and [item.get("epoch") for item in audit_epochs] == list(range(1, _EPOCHS + 1))
    ):
        raise FullTrainError("GEARS metrics call audit changed")
    for index, item in enumerate(audit_epochs):
        if set(item) != {"epoch", "train", "validation"}:
            raise FullTrainError("GEARS metrics call audit changed")
        for metrics in (item["train"], item["validation"]):
            if not (
                isinstance(metrics, dict)
                and set(metrics) == metric_keys
                and all(isinstance(value, float) and math.isfinite(value) for value in metrics.values())
            ):
                raise FullTrainError("GEARS metrics call audit changed")
        if item["validation"]["mse_de"] != values[index]:
            raise FullTrainError("checkpoint selection differs from captured validation metrics")
    display = record.get("internal_validation_log_display", {}).get("per_epoch")
    if not isinstance(display, list) or [item.get("value") for item in display] != [
        float(f"{value:.4f}") for value in values
    ]:
        raise FullTrainError("rounded log metrics differ from full-precision metrics")


def _verify_safe_runtime_manifests(root: Path, seed: int, protocol: dict[str, Any], smoke, builder) -> None:
    safe_payload, _info = smoke._read_regular(root / "model/safe-config.json")
    safe_config = smoke._json(safe_payload, builder)
    if safe_config != {
        "schema_version": "praxis.golden-gears-safe-config.v1",
        "model": protocol["training"]["model"],
    }:
        raise FullTrainError("safe model configuration changed")
    graph_payload, _info = smoke._read_regular(root / "model/runtime-graph-manifest.json")
    graph_manifest = smoke._json(graph_payload, builder)
    if not (
        set(graph_manifest) == {"schema_version", "seed", "vocabularies", "graphs"}
        and graph_manifest.get("schema_version") == "praxis.gears-runtime-graph-manifest.v1"
        and graph_manifest.get("seed") == seed
    ):
        raise FullTrainError("runtime graph manifest changed")
    vocabularies = graph_manifest.get("vocabularies")
    graphs = graph_manifest.get("graphs")
    if not isinstance(vocabularies, dict) or set(vocabularies) != {
        "gene",
        "perturbation",
    }:
        raise FullTrainError("runtime graph vocabulary manifest changed")
    if not isinstance(graphs, dict) or set(graphs) != {"G_go", "G_coexpress"}:
        raise FullTrainError("runtime graph manifest changed")
    for vocabulary in vocabularies.values():
        if not (
            isinstance(vocabulary, dict)
            and set(vocabulary) == {"count", "canonical_json_sha256"}
            and isinstance(vocabulary.get("count"), int)
            and vocabulary["count"] > 0
            and _RAW_SHA256.fullmatch(str(vocabulary.get("canonical_json_sha256")))
        ):
            raise FullTrainError("runtime graph vocabulary identity changed")
    for name, vocabulary_name in (("G_go", "perturbation"), ("G_coexpress", "gene")):
        graph = graphs[name]
        if not isinstance(graph, dict) or set(graph) != {
            "node_vocabulary",
            "edge_index",
            "edge_weight",
        }:
            raise FullTrainError("runtime graph tensor identity changed")
        if graph["node_vocabulary"] != vocabulary_name:
            raise FullTrainError("runtime graph vocabulary binding changed")
        edge_index, edge_weight = graph["edge_index"], graph["edge_weight"]
        for tensor in (edge_index, edge_weight):
            if not (
                isinstance(tensor, dict)
                and set(tensor) == {"shape", "dtype", "numel", "sha256", "finite"}
                and isinstance(tensor.get("shape"), list)
                and isinstance(tensor.get("dtype"), str)
                and isinstance(tensor.get("numel"), int)
                and tensor["numel"] > 0
                and _RAW_SHA256.fullmatch(str(tensor.get("sha256")))
                and tensor.get("finite") is True
            ):
                raise FullTrainError("runtime graph tensor identity changed")
        if not (
            len(edge_index["shape"]) == 2
            and edge_index["shape"][0] == 2
            and edge_index["numel"] == math.prod(edge_index["shape"])
            and len(edge_weight["shape"]) == 1
            and edge_weight["shape"][0] == edge_index["shape"][1]
            and edge_weight["numel"] == math.prod(edge_weight["shape"])
        ):
            raise FullTrainError("runtime graph tensor shapes changed")


def _verify_seed(
    *,
    root: Path,
    seed: int,
    smoke,
    builder,
    protocol: dict[str, Any],
    run_manifest: dict[str, Any],
    run_manifest_sha256: str,
    source_record: dict[str, Any],
    source_record_sha256: str,
    runtime: dict[str, Any],
) -> dict[str, Any]:
    _inventory(root)
    record_payload, _info = smoke._read_regular(root / "candidate-record.json")
    record = smoke._json(record_payload, builder)
    _verify_log(root, record, smoke)
    _verify_full_precision_metrics(record)
    _verify_safe_runtime_manifests(root, seed, protocol, smoke, builder)
    manifest_payload, _info = smoke._read_regular(root / "model/tensor-manifest.json")
    tensor_manifest = smoke._json(manifest_payload, builder)
    smoke._validate_tensor_manifest(tensor_manifest)
    if tensor_manifest != _recomputed_tensor_manifest(root / "model/model.pt"):
        raise FullTrainError("model checkpoint differs from its tensor manifest")
    artifacts = _artifact_records(root, builder)
    expected = _seed_record(
        seed=seed,
        protocol=protocol,
        run_manifest=run_manifest,
        run_manifest_sha256=run_manifest_sha256,
        source_record=source_record,
        source_record_sha256=source_record_sha256,
        runtime=runtime,
        metrics=record["internal_validation"],
        display_metrics=record["internal_validation_log_display"],
        metrics_call_audit=record["metrics_call_audit"],
        log_record=record["training_log"],
        artifacts=artifacts,
    )
    if record != expected:
        raise FullTrainError(f"completed seed {seed} record changed")
    for relative in _SEED_FILES:
        payload, _info = smoke._read_regular(root / relative)
        if any(value in payload for value in (b"/Users/", b"/Volumes/", b"/private/", b"/tmp/")):
            raise FullTrainError("published seed output contains an absolute local path")
    return record


def _snapshot_inputs(staging: Path, prepare_root: Path, source_record: dict[str, Any], protocol, builder) -> None:
    (staging / "input").mkdir(mode=0o700)
    (staging / "work/go_essential_all").mkdir(parents=True, mode=0o700)
    copies = {
        "input/native_train_only.h5ad": (
            "input/native_train_only.h5ad",
            source_record["derived_input_artifact"],
        ),
        "work/gene2go_all.pkl": (
            "gears-data/gene2go_all.pkl",
            protocol["downloads"]["gene2go"],
        ),
        "work/essential_all_data_pert_genes.pkl": (
            "gears-data/essential_all_data_pert_genes.pkl",
            protocol["downloads"]["essential_genes"],
        ),
        "work/go_essential_all/go_essential_all.csv": (
            "gears-data/go_essential_all/go_essential_all.csv",
            protocol["downloads"]["go_graph"]["csv"],
        ),
    }
    for target, (source, expected) in copies.items():
        builder._snapshot_regular_file(
            prepare_root / source,
            staging / target,
            size=expected["size_bytes"],
            sha256=expected["sha256"],
        )


_METRICS_CAPTURE_CHILD = r"""
import math
import gears.gears as gears_module
full_metric_records=[]
original_compute_metrics=gears_module.compute_metrics
def captured_compute_metrics(results):
 output=original_compute_metrics(results)
 metrics={str(key):float(value) for key,value in output[0].items()}
 if set(metrics) != {'mse','mse_de','pearson','pearson_de'} or not all(map(math.isfinite,metrics.values())):
  raise RuntimeError('non-finite or unexpected GEARS metrics')
 full_metric_records.append(metrics)
 return output
gears_module.compute_metrics=captured_compute_metrics
"""


_FULL_RECEIPTS_CHILD = r"""
def canonical(value):
 return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def tensor_record(tensor):
 value=tensor.detach().cpu().contiguous()
 finite=not (value.is_floating_point() or value.is_complex()) or bool(torch.isfinite(value).all())
 if not finite: raise RuntimeError('non-finite runtime graph tensor')
 return {'shape':list(value.shape),'dtype':str(value.dtype),'numel':value.numel(),
  'sha256':hashlib.sha256(value.numpy().tobytes()).hexdigest(),'finite':True}
genes=list(map(str,g.gene_list)); perts=list(map(str,g.pert_list))
safe={'schema_version':'praxis.golden-gears-safe-config.v1','model':job['model']}
graphs={'schema_version':'praxis.gears-runtime-graph-manifest.v1','seed':seed,
 'vocabularies':{
  'gene':{'count':len(genes),'canonical_json_sha256':hashlib.sha256(canonical(genes)).hexdigest()},
  'perturbation':{'count':len(perts),'canonical_json_sha256':hashlib.sha256(canonical(perts)).hexdigest()}},
 'graphs':{
  'G_go':{'node_vocabulary':'perturbation','edge_index':tensor_record(g.config['G_go']),
          'edge_weight':tensor_record(g.config['G_go_weight'])},
  'G_coexpress':{'node_vocabulary':'gene','edge_index':tensor_record(g.config['G_coexpress']),
                 'edge_weight':tensor_record(g.config['G_coexpress_weight'])}}}
(out/'safe-config.json').write_bytes(canonical(safe)+b'\n')
(out/'runtime-graph-manifest.json').write_bytes(canonical(graphs)+b'\n')
expected_calls=job['epochs']*2
if len(full_metric_records) != expected_calls: raise RuntimeError('unexpected GEARS metrics call count')
audit=[]
for index in range(job['epochs']):
 audit.append({'epoch':index+1,'train':full_metric_records[index*2],
               'validation':full_metric_records[index*2+1]})
values=[item['validation']['mse_de'] for item in audit]
best=min(range(job['epochs']),key=values.__getitem__)
full_validation={'metric':'internal_validation_mse_de','precision':'full_float_from_gears_compute_metrics',
 'per_epoch':[{'epoch':index+1,'value':value} for index,value in enumerate(values)],
 'best_epoch':best+1,'best_value':values[best]}
receipt={'status':'completed','seed':seed,'epochs':job['epochs'],'test_loader_present':False,
 'internal_validation':full_validation,
 'metrics_call_audit':{'call_order':'train_then_validation_each_epoch','expected_calls':expected_calls,
  'observed_calls':len(full_metric_records),'per_epoch':audit}}
(root/'child-receipt.json').write_bytes(canonical(receipt)+b'\n')
"""


def _train_seed(
    *,
    seed: int,
    parent: Path,
    parent_fd: int,
    prepare_root: Path,
    smoke,
    builder,
    protocol: dict[str, Any],
    run_manifest: dict[str, Any],
    run_manifest_sha256: str,
    source_record: dict[str, Any],
    source_record_sha256: str,
    runtime: dict[str, Any],
) -> dict[str, Any]:
    output_name = f"seed-{seed}"
    staging_name = ""
    staging_fd = -1
    original_cwd_fd = -1
    try:
        try:
            os.stat(output_name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise FullTrainError(f"seed {seed} output must be write-new")
        staging_name, staging_fd = builder._new_staging_directory(parent_fd, output_name)
        staging_path = parent / staging_name
        original_cwd_fd = smoke._bind_working_directory(staging_fd)
        staging = Path(".")
        _snapshot_inputs(staging, prepare_root, source_record, protocol, builder)
        split = smoke._verify_h5ad(staging / "input/native_train_only.h5ad", protocol, builder)
        job = {
            "seed": seed,
            "epochs": _EPOCHS,
            "batch_size": _BATCH_SIZE,
            "split": split,
            "model": protocol["training"]["model"],
        }
        (staging / "job.json").write_bytes(builder._canonical_bytes(job))
        if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").is_file():
            raise FullTrainError("network-denying sandbox is unavailable")
        result = subprocess.run(
            [
                "/usr/bin/sandbox-exec",
                "-p",
                "(version 1)(allow default)(deny network*)",
                sys.executable,
                "-c",
                _METRICS_CAPTURE_CHILD + smoke._CHILD + _FULL_RECEIPTS_CHILD,
            ],
            cwd=staging,
            env=builder._child_env(staging=staging),
            capture_output=True,
            check=False,
        )
        (staging / "training.log").write_bytes(smoke._sanitized_log(result.stdout, result.stderr, staging_path))
        if result.returncode:
            raise FullTrainError(f"GEARS full-training seed {seed} child failed")
        display_metrics = smoke._parse_metrics(result.stderr.decode("utf-8", errors="strict"), _EPOCHS)
        receipt = smoke._json((staging / smoke._RECEIPT).read_bytes(), builder)
        if not (
            set(receipt)
            == {
                "status",
                "seed",
                "epochs",
                "test_loader_present",
                "internal_validation",
                "metrics_call_audit",
            }
            and receipt["status"] == "completed"
            and receipt["seed"] == seed
            and receipt["epochs"] == _EPOCHS
            and receipt["test_loader_present"] is False
        ):
            raise FullTrainError(f"GEARS full-training seed {seed} child receipt changed")
        tensor_manifest = smoke._json((staging / "model/tensor-manifest.json").read_bytes(), builder)
        smoke._validate_tensor_manifest(tensor_manifest)
        artifacts = _artifact_records(staging, builder)
        record = _seed_record(
            seed=seed,
            protocol=protocol,
            run_manifest=run_manifest,
            run_manifest_sha256=run_manifest_sha256,
            source_record=source_record,
            source_record_sha256=source_record_sha256,
            runtime=runtime,
            metrics=receipt["internal_validation"],
            display_metrics=display_metrics,
            metrics_call_audit=receipt["metrics_call_audit"],
            log_record={
                "raw_stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                "raw_stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
                "published_log_is_path_redacted": True,
            },
            artifacts=artifacts,
        )
        (staging / "candidate-record.json").write_bytes(builder._canonical_bytes(record) + b"\n")
        (staging / smoke._RECEIPT).unlink()
        (staging / "job.json").unlink()
        shutil.rmtree(staging / "input")
        shutil.rmtree(staging / "work")
        shutil.rmtree(staging / ".matplotlib", ignore_errors=True)
        record = _verify_seed(
            root=staging,
            seed=seed,
            smoke=smoke,
            builder=builder,
            protocol=protocol,
            run_manifest=run_manifest,
            run_manifest_sha256=run_manifest_sha256,
            source_record=source_record,
            source_record_sha256=source_record_sha256,
            runtime=runtime,
        )
        builder._assert_named_directory_inode(parent_fd, staging_name, staging_fd)
        builder._publish(Path(staging_name), Path(output_name), parent_fd=parent_fd)
        builder._assert_named_directory_inode(parent_fd, output_name, staging_fd)
        return record
    except BaseException:
        if staging_name and staging_fd >= 0:
            try:
                builder._assert_named_directory_inode(parent_fd, staging_name, staging_fd)
            except Exception:
                pass
            else:
                shutil.rmtree(parent / staging_name, ignore_errors=True)
        raise
    finally:
        if original_cwd_fd >= 0:
            os.fchdir(original_cwd_fd)
            os.close(original_cwd_fd)
        if staging_fd >= 0:
            os.close(staging_fd)


def _verify_named_seed(
    *,
    seed: int,
    parent_fd: int,
    smoke,
    builder,
    **context: Any,
) -> dict[str, Any]:
    name = f"seed-{seed}"
    seed_fd = os.open(
        name,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=parent_fd,
    )
    original_cwd_fd = smoke._bind_working_directory(seed_fd)
    try:
        builder._assert_named_directory_inode(parent_fd, name, seed_fd)
        record = _verify_seed(root=Path("."), seed=seed, smoke=smoke, builder=builder, **context)
        builder._assert_named_directory_inode(parent_fd, name, seed_fd)
        return record
    finally:
        os.fchdir(original_cwd_fd)
        os.close(original_cwd_fd)
        os.close(seed_fd)


def _collection_record(
    *,
    records: list[dict[str, Any]],
    parent: Path,
    builder,
    protocol: dict[str, Any],
    run_manifest: dict[str, Any],
    run_manifest_sha256: str,
    source_record_sha256: str,
) -> dict[str, Any]:
    seeds = []
    for seed, record in zip(_SEEDS, records, strict=True):
        seed_root = parent / f"seed-{seed}"
        seeds.append(
            {
                "seed": seed,
                "candidate_record": {
                    "path": f"seed-{seed}/candidate-record.json",
                    **builder._file_record(seed_root / "candidate-record.json", single_link=True),
                },
                "model_pt": {
                    "path": f"seed-{seed}/model/model.pt",
                    **record["artifacts"]["model.pt"],
                },
                "tensor_manifest": {
                    "path": f"seed-{seed}/model/tensor-manifest.json",
                    **record["artifacts"]["tensor-manifest.json"],
                },
                "safe_config": {
                    "path": f"seed-{seed}/model/safe-config.json",
                    **record["artifacts"]["safe-config.json"],
                },
                "runtime_graph_manifest": {
                    "path": f"seed-{seed}/model/runtime-graph-manifest.json",
                    **record["artifacts"]["runtime-graph-manifest.json"],
                },
                "internal_validation": record["internal_validation"],
            }
        )
    identity = run_manifest["identity"]
    return {
        "schema_version": "praxis.golden-gears-train-only-full-collection.v1",
        "record_role": run_manifest["record_roles"]["collection"],
        "status": "completed",
        "candidate_name": protocol["candidate"]["name"],
        "protocol_sha256": identity["base_protocol_payload_sha256"],
        "full_run_manifest_payload_sha256": identity["payload_sha256"],
        "full_run_manifest_sha256": run_manifest_sha256,
        "full_worker_sha256": identity["worker_sha256"],
        "prepare_record_sha256": source_record_sha256,
        "execution": {
            "seeds": list(_SEEDS),
            "epochs_per_seed": _EPOCHS,
            "batch_size": _BATCH_SIZE,
            "device": "cpu",
            "all_seed_candidates_verified": True,
            "golden_validation_expression_or_outcomes_read": False,
            "golden_test_expression_or_outcomes_read": False,
        },
        "seeds": seeds,
        **run_manifest["claim_ceiling"],
    }


def _read_regular_at(parent_fd: int, name: str) -> bytes:
    descriptor = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise FullTrainError("expected a single-link regular file")
        chunks = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise FullTrainError("file changed while reading")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _atomic_write_new(parent_fd: int, name: str, payload: bytes, builder) -> None:
    temporary = f".{name}.{secrets.token_hex(8)}"
    descriptor = -1
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=parent_fd,
        )
        with os.fdopen(descriptor, "wb", closefd=False) as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        expected = os.fstat(descriptor)
        observed = os.stat(temporary, dir_fd=parent_fd, follow_symlinks=False)
        if (observed.st_dev, observed.st_ino) != (expected.st_dev, expected.st_ino):
            raise FullTrainError("collection staging file identity changed")
        builder._publish(Path(temporary), Path(name), parent_fd=parent_fd)
        observed = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (observed.st_dev, observed.st_ino) != (expected.st_dev, expected.st_ino):
            raise FullTrainError("published collection file identity changed")
    except BaseException:
        try:
            os.unlink(temporary, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        raise
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def run_full(*, prepare_root: Path, output_root: Path) -> dict[str, Any]:
    smoke = _smoke_runner()
    builder = smoke._builder()
    try:
        protocol = builder._load_protocol(_PROTOCOL_PATH.absolute())
        smoke._verify_runner_identity(builder, protocol)
        run_manifest, run_manifest_sha256 = _load_and_verify_manifest(smoke, builder, protocol)
        runtime = smoke._verify_runtime(builder, protocol)
        prepare_root = prepare_root.absolute()
        source_record, source_record_sha256 = smoke._verify_prepare_root(prepare_root, builder, protocol)
    except Exception as exc:
        if isinstance(exc, FullTrainError):
            raise
        raise FullTrainError("full-training inputs or runtime changed") from exc

    output_root = output_root.absolute()
    parent, parent_fd = builder._validated_output_parent(output_root / "seed-11")
    context = {
        "protocol": protocol,
        "run_manifest": run_manifest,
        "run_manifest_sha256": run_manifest_sha256,
        "source_record": source_record,
        "source_record_sha256": source_record_sha256,
        "runtime": runtime,
    }
    try:
        if parent != output_root or not smoke._is_apfs(parent):
            raise FullTrainError("output root must be an existing private APFS directory")
        records = []
        for seed in _SEEDS:
            name = f"seed-{seed}"
            try:
                info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                record = _train_seed(
                    seed=seed,
                    parent=parent,
                    parent_fd=parent_fd,
                    prepare_root=prepare_root,
                    smoke=smoke,
                    builder=builder,
                    **context,
                )
            else:
                if not stat.S_ISDIR(info.st_mode):
                    raise FullTrainError(f"completed seed {seed} path is not a directory")
                record = _verify_named_seed(
                    seed=seed,
                    parent_fd=parent_fd,
                    smoke=smoke,
                    builder=builder,
                    **context,
                )
            records.append(record)

        collection = _collection_record(
            records=records,
            parent=parent,
            builder=builder,
            protocol=protocol,
            run_manifest=run_manifest,
            run_manifest_sha256=run_manifest_sha256,
            source_record_sha256=source_record_sha256,
        )
        payload = builder._canonical_bytes(collection) + b"\n"
        try:
            existing = _read_regular_at(parent_fd, "collection-record.json")
        except FileNotFoundError:
            _atomic_write_new(parent_fd, "collection-record.json", payload, builder)
        else:
            if existing != payload:
                raise FullTrainError("existing collection record changed")
        return collection
    finally:
        os.close(parent_fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    arguments = parser.parse_args(argv)
    run_full(prepare_root=arguments.prepare_root, output_root=arguments.output_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
