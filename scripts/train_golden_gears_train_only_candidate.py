#!/usr/bin/env python3
"""Train the frozen Norman GEARS candidate from a verified prepare artifact."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).parents[1]
_BUILDER_PATH = _ROOT / "scripts/build_golden_gears_train_only_candidate.py"
_PROTOCOL_PATH = _ROOT / "data/golden/norman_2019/gears_train_only_protocol.json"
_RECEIPT = "child-receipt.json"
_MODEL_FILES = ("config.pkl", "model.pt", "tensor-manifest.json")
_METRIC = re.compile(r"Validation Top 20 DE MSE:\s*([^\s.]+(?:\.[^\s.]*)?)\.")
_EPOCH = re.compile(r"Epoch\s+(\d+):\s+Train Overall MSE:")


class CandidateTrainError(ValueError):
    """Fail-closed train-only candidate error."""


def _builder():
    spec = importlib.util.spec_from_file_location("golden_gears_builder", _BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise CandidateTrainError("candidate builder is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_regular(path: Path) -> tuple[bytes, os.stat_result]:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise CandidateTrainError("expected a regular file")
        chunks = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise CandidateTrainError("file changed while reading")
        return b"".join(chunks), after
    finally:
        os.close(descriptor)


def _json(payload: bytes, builder) -> dict[str, Any]:
    try:
        value = json.loads(
            payload,
            object_pairs_hook=builder._reject_duplicate_keys,
            parse_constant=lambda _value: (_ for _ in ()).throw(CandidateTrainError("non-finite JSON")),
        )
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CandidateTrainError("invalid JSON") from exc
    if not isinstance(value, dict):
        raise CandidateTrainError("expected a JSON object")
    return value


def _is_apfs(path: Path) -> bool:
    if sys.platform != "darwin":
        return False
    result = subprocess.run(["/bin/df", "-P", str(path)], capture_output=True, text=True, check=False)
    lines = result.stdout.splitlines()
    if result.returncode or len(lines) < 2:
        return False
    device = lines[-1].split()[0]
    info = subprocess.run(["/usr/sbin/diskutil", "info", device], capture_output=True, text=True, check=False)
    return info.returncode == 0 and re.search(r"File System Personality:\s+APFS\b", info.stdout) is not None


def _bind_working_directory(directory_fd: int) -> int:
    original = os.open(".", os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    os.fchdir(directory_fd)
    return original


def _is_venv_invocation(executable: Path, prefix: Path, base_prefix: Path) -> bool:
    if prefix.resolve() == base_prefix.resolve():
        return False
    # A stdlib venv normally symlinks bin/python to the base interpreter; bind its
    # invocation path here and bind imported modules to sys.prefix below.
    return executable.absolute().is_relative_to(prefix.resolve())


def _verify_runtime(builder, protocol: dict[str, Any]) -> dict[str, Any]:
    if not _is_venv_invocation(Path(sys.executable), Path(sys.prefix), Path(sys.base_prefix)):
        raise CandidateTrainError("interpreter is outside the virtual environment")
    try:
        builder._validate_parent_environment(protocol)
        runtime = builder._runtime_probe(Path(sys.executable), protocol)
        builder._validate_parent_module_origins(runtime)
    except Exception as exc:
        raise CandidateTrainError("runtime identity changed") from exc
    return runtime


def _verify_runner_identity(builder, protocol: dict[str, Any]) -> str:
    identity = protocol.get("identity", {})
    boundary = protocol.get("execution_boundary", {})
    expected_path = "scripts/train_golden_gears_train_only_candidate.py"
    observed = builder._sha256(Path(__file__))
    if not (
        identity.get("train_runner_path") == expected_path
        and identity.get("train_runner_sha256") == observed
        and boundary.get("train_runner_modes") == ["smoke"]
        and boundary.get("smoke_status") == "IMPLEMENTED_TECHNICAL_ONLY"
        and boundary.get("train_status") == "NOT_IMPLEMENTED_NOT_EXECUTABLE"
    ):
        raise CandidateTrainError("train runner differs from the frozen protocol")
    return observed


def _verify_prepare_record(record: dict[str, Any], protocol: dict[str, Any]) -> None:
    expected_runtime = protocol["runtime_environment"]
    expected_wheels = protocol["wheelhouse"]
    expected_native = protocol["training"]["native_input"]
    expected_pack = protocol["pack"]
    audit = record.get("contamination_audit", {})
    pairwise = audit.get("pairwise", {})
    if not (
        record.get("schema_version") == protocol["claim_ceiling"]["output_schema_version"]
        and record.get("record_role") == protocol["claim_ceiling"]["output_record_role"]
        and record.get("mode") == "prepare"
        and record.get("candidate_name") == protocol["candidate"]["name"]
        and record.get("protocol_sha256") == protocol["identity"]["payload_sha256"]
        and record.get("builder_sha256") == protocol["identity"]["builder_sha256"]
        and record.get("training_receipts") == []
        and record.get("benchmark_status") == "NOT_RUN"
        and record.get("benchmark_passed") is None
        and record.get("scientifically_validated") is False
        and record.get("promotion_eligible") is False
        and record.get("production_promoted") is False
        and record.get("registry_or_default_route_changed") is False
        and record.get("pack", {}).get("pack_fingerprint") == expected_pack["pack_fingerprint"]
        and record.get("pack", {}).get("expression_sha256") == expected_pack["expression_sha256"]
        and record.get("derived_input", {}).get("native_rows") == expected_native["rows"]
        and record.get("derived_input", {}).get("feature_count") == expected_pack["shape"][1]
        and record.get("derived_input", {}).get("native_observation_ids_sha256")
        == expected_native["observation_ids_source_order_sha256"]
        and record.get("runtime", {}).get("packages") == expected_runtime["packages"]
        and record.get("runtime", {}).get("gears_source_manifest_sha256")
        == protocol["candidate"]["implementation"]["installed_source_manifest_sha256"]
        and record.get("wheelhouse", {}).get("manifest_sha256") == expected_wheels["manifest_sha256"]
        and audit.get("status") == "passed"
        and audit.get("rows") == protocol["contamination_contract"]["expected"]["rows"]
        and all(
            value.get("condition_ids") == [] and value.get("canonical_target_tuples") == []
            for value in pairwise.values()
        )
        and len(pairwise) == 3
    ):
        raise CandidateTrainError("prepare candidate record identity changed")


def _verify_prepare_root(root: Path, builder, protocol: dict[str, Any]) -> tuple[dict[str, Any], str]:
    if root.is_symlink():
        raise CandidateTrainError("prepare root must not be a symlink")
    root = root.resolve(strict=True)
    info = root.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise CandidateTrainError("prepare root must be private and operator-owned")
    expected_files = {
        "candidate-record.json",
        "input/native_train_only.h5ad",
        "gears-data/gene2go_all.pkl",
        "gears-data/essential_all_data_pert_genes.pkl",
        "gears-data/go_essential_all/go_essential_all.csv",
    }
    observed_files: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        item = path.lstat()
        if stat.S_ISLNK(item.st_mode) or not (stat.S_ISREG(item.st_mode) or stat.S_ISDIR(item.st_mode)):
            raise CandidateTrainError("prepare inventory contains an unsafe entry")
        if stat.S_ISREG(item.st_mode):
            observed_files.add(relative)
    if observed_files != expected_files:
        raise CandidateTrainError("prepare inventory changed")
    attestation = protocol.get("execution_boundary", {}).get("prepared_artifact_attestation", {})
    record_attestation = attestation.get("candidate_record_normalized")
    h5ad_attestation = attestation.get("native_train_only_h5ad")
    if not isinstance(record_attestation, dict) or not isinstance(h5ad_attestation, dict):
        raise CandidateTrainError("prepared artifact attestation is absent from the frozen protocol")
    record_bytes, _ = _read_regular(root / "candidate-record.json")
    record = _json(record_bytes, builder)
    normalized_record = dict(record)
    normalized_record["protocol_sha256"] = None
    if not (
        record_attestation.get("algorithm")
        == "sha256(canonical_json(candidate_record_with_protocol_sha256_set_to_null))"
        and record_attestation.get("sha256") == builder._fingerprint(normalized_record)
    ):
        raise CandidateTrainError("prepare candidate record differs from its independent attestation")
    _verify_prepare_record(record, protocol)
    artifact = record["derived_input_artifact"]
    if (
        artifact.get("path") != "input/native_train_only.h5ad"
        or {"size_bytes": artifact.get("size_bytes"), "sha256": artifact.get("sha256")} != h5ad_attestation
    ):
        raise CandidateTrainError("derived input path changed")
    checks = {
        "input/native_train_only.h5ad": h5ad_attestation,
        "gears-data/gene2go_all.pkl": protocol["downloads"]["gene2go"],
        "gears-data/essential_all_data_pert_genes.pkl": protocol["downloads"]["essential_genes"],
        "gears-data/go_essential_all/go_essential_all.csv": protocol["downloads"]["go_graph"]["csv"],
    }
    for relative, expected in checks.items():
        path = root / relative
        actual = builder._file_record(path, single_link=True)
        if actual != {"size_bytes": expected["size_bytes"], "sha256": expected["sha256"]}:
            raise CandidateTrainError(f"prepared asset identity changed: {relative}")
    return record, builder._sha256(root / "candidate-record.json")


def _split_from_labels(
    observation_ids: list[str], labels: list[str], protocol: dict[str, Any], builder
) -> dict[str, list[str]]:
    if len(observation_ids) != len(labels):
        raise CandidateTrainError("derived input columns have different lengths")
    expected = protocol["training"]["native_input"]
    if (
        len(labels) != expected["rows"]
        or builder._fingerprint(observation_ids) != expected["observation_ids_source_order_sha256"]
    ):
        raise CandidateTrainError("derived observation identity changed")
    conditions = sorted(set(labels))
    if builder._fingerprint(conditions) != expected["canonical_child_labels_including_control_sha256"]:
        raise CandidateTrainError("derived condition identity changed")
    noncontrol = [value for value in conditions if value != "ctrl"]
    ranked = sorted(
        (builder._canonical_targets(value) for value in noncontrol),
        key=lambda item: (builder._rank(item, protocol["training"]["preprocessing_seed"]), item),
    )
    count = math.ceil(len(ranked) * 0.1)
    validation_targets, train_targets = ranked[:count], ranked[count:]
    split = {
        "train": sorted(["ctrl", *(builder._child_label(item) for item in train_targets)]),
        "val": sorted(builder._child_label(item) for item in validation_targets),
    }
    internal = protocol["training"]["internal_validation"]
    train_ids = [item for item, label in zip(observation_ids, labels, strict=True) if label in split["train"]]
    val_ids = [item for item, label in zip(observation_ids, labels, strict=True) if label in split["val"]]
    if not (
        builder._fingerprint([list(item) for item in train_targets]) == internal["train_rank_order_target_lists_sha256"]
        and builder._fingerprint([list(item) for item in validation_targets])
        == internal["validation_rank_order_target_lists_sha256"]
        and builder._fingerprint(split["train"]) == internal["train_canonical_labels_with_control_sha256"]
        and builder._fingerprint(split["val"]) == internal["validation_canonical_labels_sha256"]
        and len(train_ids) == internal["train_rows"]
        and builder._fingerprint(train_ids) == internal["train_observation_ids_source_order_sha256"]
        and len(val_ids) == internal["validation_rows"]
        and builder._fingerprint(val_ids) == internal["validation_observation_ids_source_order_sha256"]
        and not set(split["train"]).intersection(split["val"])
    ):
        raise CandidateTrainError("internal train/validation split identity changed")
    return split


def _verify_h5ad(path: Path, protocol: dict[str, Any], builder) -> dict[str, list[str]]:
    import anndata

    source = anndata.read_h5ad(path, backed="r")
    try:
        if (
            list(source.shape) != [protocol["training"]["native_input"]["rows"], protocol["pack"]["shape"][1]]
            or list(source.obs.columns) != ["condition", "cell_type"]
            or list(source.var.columns) != ["gene_name"]
            or source.uns
            or source.obsm
            or source.varm
            or source.layers
            or source.raw is not None
            or set(map(str, source.obs["cell_type"])) != {"K562"}
        ):
            raise CandidateTrainError("derived H5AD schema changed")
        ids = list(map(str, source.obs_names))
        labels = list(map(str, source.obs["condition"]))
        return _split_from_labels(ids, labels, protocol, builder)
    finally:
        source.file.close()


def _parse_metrics(stdout: str, epochs: int) -> dict[str, Any]:
    epoch_values = [int(value) for value in _EPOCH.findall(stdout)]
    raw_values = _METRIC.findall(stdout)
    try:
        values = [float(value) for value in raw_values]
    except ValueError as exc:
        raise CandidateTrainError("validation metric is not numeric") from exc
    if epoch_values != list(range(1, epochs + 1)) or len(values) != epochs or not all(map(math.isfinite, values)):
        raise CandidateTrainError(
            "finite validation Top20 DE MSE was not reported once per epoch "
            f"(epochs={epoch_values!r}, values={raw_values!r})"
        )
    best = min(range(epochs), key=values.__getitem__)
    return {
        "metric": "internal_validation_top20_de_mse",
        "per_epoch": [{"epoch": index + 1, "value": value} for index, value in enumerate(values)],
        "best_epoch": best + 1,
        "best_value": values[best],
        "printed_precision": 4,
    }


def _sanitized_log(stdout: bytes, stderr: bytes, staging_path: Path) -> bytes:
    try:
        text = (b"STDOUT\n" + stdout + b"\nSTDERR\n" + stderr).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CandidateTrainError("GEARS logs are not UTF-8") from exc
    text = text.replace(str(staging_path), "<STAGING>")
    text = re.sub(r"(?<![\w.])/(?:Users|Volumes|private|tmp|var)(?:/[^\s:]+)+", "<ABSOLUTE_PATH>", text)
    if str(staging_path) in text or staging_path.name in text:
        raise CandidateTrainError("training log path redaction failed")
    return text.encode("utf-8")


_CHILD = r"""
import hashlib,json,os,random
from pathlib import Path
root=Path.cwd(); job=json.loads((root/'job.json').read_text())
import dcor
import numpy as np,pandas as pd,torch
pd.Series.nonzero=lambda self:self.to_numpy().nonzero()
from gears import GEARS,PertData
import anndata
seed=job['seed']
def reset(value):
 random.seed(value); np.random.seed(value); torch.manual_seed(value)
reset(seed); torch.use_deterministic_algorithms(True); torch.set_num_threads(1); torch.set_num_interop_threads(1)
adata=anndata.read_h5ad(root/'input/native_train_only.h5ad')
pd_=PertData(str(root/'work'))
reset(0); pd_.new_data_process('norman_golden_train_only',adata=adata,skip_calc_de=False)
pd_.split='no_test'; pd_.seed=0; pd_.train_gene_set_size=None; pd_.subgroup=None
pd_.set2conditions=job['split']; pd_.get_dataloader(batch_size=job['batch_size'])
if set(pd_.dataloader) != {'train_loader','val_loader'}: raise RuntimeError('held-out loader present')
reset(seed); g=GEARS(pd_,device='cpu',weight_bias_track=False); reset(seed); m=job['model']
g.model_initialize(hidden_size=m['hidden_size'],num_go_gnn_layers=m['num_go_gnn_layers'],
 num_gene_gnn_layers=m['num_gene_gnn_layers'],decoder_hidden_size=m['decoder_hidden_size'],
 num_similar_genes_go_graph=m['num_similar_genes_go_graph'],
 num_similar_genes_co_express_graph=m['num_similar_genes_co_express_graph'],
 coexpress_threshold=m['coexpress_threshold'],uncertainty=m['uncertainty'],
 uncertainty_reg=m['uncertainty_reg'],direction_lambda=m['direction_lambda'],no_perturb=m['no_perturb'])
reset(seed); g.train(epochs=job['epochs'],lr=m['learning_rate'],weight_decay=m['weight_decay'])
out=root/'model'; out.mkdir(); g.save_model(str(out))
state=torch.load(out/'model.pt',map_location='cpu',weights_only=True)
if not isinstance(state,dict) or not state: raise RuntimeError('empty or unsafe state dict')
records=[]
for key,tensor in sorted(state.items()):
 if not isinstance(key,str) or not isinstance(tensor,torch.Tensor): raise RuntimeError('non-tensor state')
 value=tensor.detach().cpu().contiguous()
 finite=not (value.is_floating_point() or value.is_complex()) or bool(torch.isfinite(value).all())
 if not finite: raise RuntimeError('non-finite tensor')
 payload=value.numpy().tobytes()
 records.append({'key':key,'shape':list(value.shape),'dtype':str(value.dtype),'numel':value.numel(),
  'sha256':hashlib.sha256(payload).hexdigest(),'finite':True})
manifest={'schema_version':'praxis.torch-state-tensor-manifest.v1','weights_only':True,
 'tensor_count':len(records),'total_numel':sum(item['numel'] for item in records),'all_finite':True,'tensors':records}
(out/'tensor-manifest.json').write_text(json.dumps(manifest,sort_keys=True,separators=(',',':'))+'\n')
(root/'child-receipt.json').write_text(json.dumps({'status':'completed','seed':seed,'epochs':job['epochs'],
 'test_loader_present':False},sort_keys=True,separators=(',',':'))+'\n')
"""


def _validate_tensor_manifest(value: dict[str, Any]) -> None:
    tensors = value.get("tensors")
    if not (
        value.get("schema_version") == "praxis.torch-state-tensor-manifest.v1"
        and value.get("weights_only") is True
        and value.get("all_finite") is True
        and isinstance(tensors, list)
        and tensors
        and value.get("tensor_count") == len(tensors)
        and value.get("total_numel") == sum(item.get("numel", -1) for item in tensors)
        and all(
            isinstance(item.get("key"), str)
            and isinstance(item.get("shape"), list)
            and isinstance(item.get("dtype"), str)
            and isinstance(item.get("numel"), int)
            and item["numel"] >= 0
            and re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", ""))
            and item.get("finite") is True
            for item in tensors
        )
    ):
        raise CandidateTrainError("tensor manifest is invalid")


def train(*, prepare_root: Path, output: Path, protocol_path: Path = _PROTOCOL_PATH) -> dict[str, Any]:
    builder = _builder()
    try:
        protocol = builder._load_protocol(protocol_path.absolute())
    except Exception as exc:
        raise CandidateTrainError("frozen protocol identity changed") from exc
    runner_sha256 = _verify_runner_identity(builder, protocol)
    smoke = protocol["training"]["smoke"]
    if smoke != {"seed": 11, "epochs": 1, "batch_size": 8, "technical_only": True}:
        raise CandidateTrainError("smoke contract changed")
    runtime = _verify_runtime(builder, protocol)
    prepare_root = prepare_root.absolute()
    source_record, source_record_sha256 = _verify_prepare_root(prepare_root, builder, protocol)

    output = output.absolute()
    parent, parent_fd = builder._validated_output_parent(output)
    staging_name = ""
    staging_fd = -1
    original_cwd_fd = -1
    try:
        if not _is_apfs(parent):
            raise CandidateTrainError("output parent must be on APFS")
        try:
            os.stat(output.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise CandidateTrainError("output must be write-new")
        staging_name, staging_fd = builder._new_staging_directory(parent_fd, output.name)
        staging_path = parent / staging_name
        original_cwd_fd = _bind_working_directory(staging_fd)
        staging = Path(".")
        (staging / "input").mkdir(mode=0o700)
        (staging / "work/go_essential_all").mkdir(parents=True, mode=0o700)
        copies = {
            "input/native_train_only.h5ad": source_record["derived_input_artifact"],
            "work/gene2go_all.pkl": protocol["downloads"]["gene2go"],
            "work/essential_all_data_pert_genes.pkl": protocol["downloads"]["essential_genes"],
            "work/go_essential_all/go_essential_all.csv": protocol["downloads"]["go_graph"]["csv"],
        }
        source_names = {
            "work/gene2go_all.pkl": "gears-data/gene2go_all.pkl",
            "work/essential_all_data_pert_genes.pkl": "gears-data/essential_all_data_pert_genes.pkl",
            "work/go_essential_all/go_essential_all.csv": "gears-data/go_essential_all/go_essential_all.csv",
        }
        for target, expected in copies.items():
            source = prepare_root / source_names.get(target, target)
            builder._snapshot_regular_file(
                source, staging / target, size=expected["size_bytes"], sha256=expected["sha256"]
            )
        split = _verify_h5ad(staging / "input/native_train_only.h5ad", protocol, builder)
        job = {
            "seed": smoke["seed"],
            "epochs": smoke["epochs"],
            "batch_size": smoke["batch_size"],
            "split": split,
            "model": protocol["training"]["model"],
        }
        (staging / "job.json").write_bytes(builder._canonical_bytes(job))
        if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").is_file():
            raise CandidateTrainError("network-denying sandbox is unavailable")
        result = subprocess.run(
            [
                "/usr/bin/sandbox-exec",
                "-p",
                "(version 1)(allow default)(deny network*)",
                sys.executable,
                "-c",
                _CHILD,
            ],
            cwd=staging,
            env=builder._child_env(staging=staging),
            capture_output=True,
            check=False,
        )
        log = _sanitized_log(result.stdout, result.stderr, staging_path)
        (staging / "training.log").write_bytes(log)
        if result.returncode:
            raise CandidateTrainError("GEARS smoke child failed")
        # GEARS routes all progress and epoch metrics through print_sys(), which
        # writes to stderr. Stdout is intentionally not treated as a metric source.
        metrics = _parse_metrics(result.stderr.decode("utf-8", errors="strict"), smoke["epochs"])
        receipt = _json((staging / _RECEIPT).read_bytes(), builder)
        if receipt != {"status": "completed", "seed": 11, "epochs": 1, "test_loader_present": False}:
            raise CandidateTrainError("GEARS child receipt changed")
        manifest = _json((staging / "model/tensor-manifest.json").read_bytes(), builder)
        _validate_tensor_manifest(manifest)
        artifacts = {
            "config.pkl": {
                **builder._file_record(staging / "model/config.pkl", single_link=True),
                "unsafe_pickle": True,
            },
            "model.pt": {
                **builder._file_record(staging / "model/model.pt", single_link=True),
                "weights_only_verified": True,
            },
            "tensor-manifest.json": builder._file_record(staging / "model/tensor-manifest.json", single_link=True),
            "training.log": builder._file_record(staging / "training.log", single_link=True),
        }
        record = {
            "schema_version": "praxis.golden-gears-train-only-trained-candidate.v1",
            "record_role": "technical_smoke_research_candidate_not_scientific_evidence",
            "candidate_name": protocol["candidate"]["name"],
            "mode": "smoke",
            "protocol_sha256": protocol["identity"]["payload_sha256"],
            "runner_sha256": runner_sha256,
            "prepare_record_sha256": source_record_sha256,
            "prepare_input": source_record["derived_input_artifact"],
            "runtime": runtime,
            "execution": {
                "device": "cpu",
                "network_denied_by_sandbox": True,
                "filesystem_read_isolation": False,
                "seed": 11,
                "epochs": 1,
                "batch_size": 8,
                "internal_validation_de_dropout_preprocessing_independent": False,
                "internal_validation_coexpression_graph_independent": True,
                "internal_validation_gradient_fit_excludes_validation": True,
                "internal_validation_checkpoint_selection_uses_validation": True,
                "internal_validation_role": "technical_checkpoint_selection_only",
                "preprocessing_scope": "all_45450_native_supported_outer_train_rows_before_internal_split",
                "golden_validation_expression_used": False,
                "golden_test_expression_used": False,
                "golden_validation_test_metadata_audit_consumed": True,
                "prospective_test_blinding": False,
                "test_loader_present": False,
            },
            "internal_validation": metrics,
            "training_log": {
                "raw_stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                "raw_stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
                "published_log_is_path_redacted": True,
            },
            "contamination_audit": source_record["contamination_audit"],
            "prospective_test_blinding": False,
            "artifacts": artifacts,
            "benchmark_status": "NOT_RUN",
            "benchmark_passed": None,
            "scientifically_validated": False,
            "promotion_eligible": False,
            "production_promoted": False,
            "registry_or_default_route_changed": False,
        }
        (staging / "candidate-record.json").write_bytes(builder._canonical_bytes(record) + b"\n")
        (staging / _RECEIPT).unlink()
        (staging / "job.json").unlink()
        shutil.rmtree(staging / "input")
        shutil.rmtree(staging / "work")
        shutil.rmtree(staging / ".matplotlib", ignore_errors=True)
        allowed = {"candidate-record.json", "training.log", *[f"model/{name}" for name in _MODEL_FILES]}
        observed = {path.relative_to(staging).as_posix() for path in staging.rglob("*") if path.is_file()}
        if observed != allowed or any(path.is_symlink() for path in staging.rglob("*")):
            raise CandidateTrainError("trained output inventory changed")
        builder._assert_named_directory_inode(parent_fd, staging_name, staging_fd)
        builder._publish(Path(staging_name), Path(output.name), parent_fd=parent_fd)
        builder._assert_named_directory_inode(parent_fd, output.name, staging_fd)
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
        os.close(parent_fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=_PROTOCOL_PATH)
    parser.add_argument("--mode", choices=("smoke",), required=True)
    arguments = parser.parse_args(argv)
    train(prepare_root=arguments.prepare_root, output=arguments.output, protocol_path=arguments.protocol)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
