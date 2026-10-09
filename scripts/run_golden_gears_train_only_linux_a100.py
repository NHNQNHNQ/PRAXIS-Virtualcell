#!/usr/bin/env python3
"""Run the frozen Norman GEARS train-only candidate on one Linux A100."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import importlib.util
import json
import os
import platform
import re
import shutil
import site
import stat
import subprocess
import sys
import sysconfig
import threading
from importlib.metadata import version
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).parents[1]
_MANIFEST_PATH = _ROOT / "data/golden/norman_2019/gears_train_only_linux_a100_run.json"
_PROTOCOL_PATH = _ROOT / "data/golden/norman_2019/gears_train_only_protocol.json"
_BUILDER_PATH = _ROOT / "scripts/build_golden_gears_train_only_candidate.py"
_SMOKE_PATH = _ROOT / "scripts/train_golden_gears_train_only_candidate.py"
_FULL_PATH = _ROOT / "scripts/run_golden_gears_train_only_full.py"
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
_SHA256 = re.compile(r"[0-9a-f]{64}")


class LinuxA100RunError(ValueError):
    """Fail-closed Linux A100 execution error."""


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LinuxA100RunError(f"required source is unavailable: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _dependencies():
    builder = _load_module("golden_gears_linux_builder", _BUILDER_PATH)
    smoke = _load_module("golden_gears_linux_smoke", _SMOKE_PATH)
    full = _load_module("golden_gears_linux_full", _FULL_PATH)
    return builder, smoke, full


def _json(payload: bytes, builder) -> dict[str, Any]:
    try:
        value = json.loads(
            payload,
            object_pairs_hook=builder._reject_duplicate_keys,
            parse_constant=lambda _value: (_ for _ in ()).throw(LinuxA100RunError("non-finite JSON")),
        )
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise LinuxA100RunError("invalid JSON") from exc
    if not isinstance(value, dict):
        raise LinuxA100RunError("expected a JSON object")
    return value


def _load_manifest(builder, protocol: dict[str, Any]) -> tuple[dict[str, Any], str]:
    payload = builder._regular_bytes(
        _MANIFEST_PATH,
        size=_MANIFEST_PATH.stat().st_size,
        sha256=builder._sha256(_MANIFEST_PATH),
        label="Linux A100 run manifest",
    )
    manifest = _json(payload, builder)
    normalized = copy.deepcopy(manifest)
    try:
        payload_sha256 = normalized["identity"]["payload_sha256"]
        normalized["identity"]["payload_sha256"] = None
    except (KeyError, TypeError) as exc:
        raise LinuxA100RunError("Linux run manifest identity is invalid") from exc
    identity = manifest.get("identity", {})
    dependencies = identity.get("source_dependencies", {})
    expected_dependencies = {
        "scripts/build_golden_gears_train_only_candidate.py": builder._sha256(_BUILDER_PATH),
        "scripts/train_golden_gears_train_only_candidate.py": builder._sha256(_SMOKE_PATH),
        "scripts/run_golden_gears_train_only_full.py": builder._sha256(_FULL_PATH),
    }
    base = identity.get("base_protocol", {})
    claims = manifest.get("claim_ceiling", {})
    execution = manifest.get("execution", {})
    if not (
        manifest.get("schema_version") == "praxis.golden-gears-train-only-linux-a100-run.v1"
        and _SHA256.fullmatch(str(payload_sha256))
        and builder._fingerprint(normalized) == payload_sha256
        and identity.get("payload_hash_algorithm")
        == "sha256(canonical_json(manifest_with_identity.payload_sha256_set_to_null))"
        and identity.get("worker_path") == "scripts/run_golden_gears_train_only_linux_a100.py"
        and identity.get("worker_sha256") == builder._sha256(Path(__file__))
        and dependencies == expected_dependencies
        and base
        == {
            "path": "data/golden/norman_2019/gears_train_only_protocol.json",
            "size_bytes": _PROTOCOL_PATH.stat().st_size,
            "sha256": builder._sha256(_PROTOCOL_PATH),
            "payload_sha256": protocol["identity"]["payload_sha256"],
        }
        and execution.get("device") == "cuda:0"
        and execution.get("single_visible_gpu_required") is True
        and execution.get("torch_deterministic_algorithms") is True
        and execution.get("cudnn_deterministic") is True
        and execution.get("cudnn_benchmark") is False
        and execution.get("smoke") == {"seed": 11, "epochs": 1, "batch_size": 8, "output_record": "smoke-record.json"}
        and execution.get("full")
        == {
            "seeds": [11, 23, 37],
            "epochs_per_seed": 20,
            "batch_size": 32,
            "slurm_job_required": True,
            "output_record": "collection-record.json",
        }
        and execution.get("full_requires_verified_smoke_from_this_manifest") is True
        and claims
        == {
            "benchmark_status": "NOT_RUN",
            "benchmark_passed": None,
            "scientifically_validated": False,
            "promotion_eligible": False,
            "production_promoted": False,
            "registry_or_default_route_changed": False,
            "bitwise_equivalent_to_darwin_cpu_candidate": False,
        }
    ):
        raise LinuxA100RunError("Linux run manifest identity or contract changed")
    return manifest, hashlib.sha256(payload).hexdigest()


def _validate_parent_environment(manifest: dict[str, Any]) -> None:
    runtime = manifest["runtime"]
    for name, expected in runtime["required_environment"].items():
        if os.environ.get(name) != expected:
            raise LinuxA100RunError(f"required environment changed: {name}")
    if any(name in os.environ for name in runtime["forbidden_environment"]):
        raise LinuxA100RunError("forbidden parent environment is present")
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    if not visible or len([item for item in visible.split(",") if item]) != 1:
        raise LinuxA100RunError("exactly one Slurm-assigned GPU must be visible")
    if site.ENABLE_USER_SITE:
        raise LinuxA100RunError("user site-packages must be disabled")


def _gears_source_identity(builder) -> str:
    import gears

    root = Path(gears.__file__).parent
    records = []
    for path in sorted(root.glob("*.py")):
        payload = path.read_bytes()
        records.append(
            {
                "path": f"gears/{path.name}",
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    return builder._fingerprint(records)


def _module_origins(runtime: dict[str, Any]) -> None:
    prefix = Path(sys.prefix).resolve(strict=True)
    for distribution, module_name in {
        "anndata": "anndata",
        "h5py": "h5py",
        "numpy": "numpy",
        "pandas": "pandas",
        "PyYAML": "yaml",
        "torch": "torch",
        "torch-geometric": "torch_geometric",
        "cell-gears": "gears",
    }.items():
        module = importlib.import_module(module_name)
        origin = getattr(module, "__file__", None)
        if (
            version(distribution) != runtime["packages"][distribution]
            or not isinstance(origin, str)
            or not Path(origin).resolve(strict=True).is_relative_to(prefix)
        ):
            raise LinuxA100RunError(f"module origin is outside the frozen runtime: {module_name}")


def _driver_version() -> str:
    result = subprocess.run(
        ["/usr/bin/nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
        capture_output=True,
        check=False,
        text=True,
        env={"PATH": os.defpath, "LC_ALL": "C", "LANG": "C"},
    )
    values = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    if result.returncode or len(values) != 1:
        raise LinuxA100RunError("NVIDIA driver identity is unavailable")
    return values.pop()


def _runtime_identity(manifest: dict[str, Any], builder) -> dict[str, Any]:
    _validate_parent_environment(manifest)
    expected = manifest["runtime"]
    observed_packages = {name: version(name) for name in expected["packages"]}
    _module_origins(expected)
    import torch

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise LinuxA100RunError("exactly one CUDA device must be available")
    observed = {
        "python": platform.python_version(),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "sysconfig_platform": sysconfig.get_platform(),
        "packages": observed_packages,
        "gears_source_manifest_sha256": _gears_source_identity(builder),
        "torch_runtime_version": torch.__version__,
        "torch_cuda_version": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "nvidia_driver_version": _driver_version(),
        "logical_device": "cuda:0",
        "visible_device_count": torch.cuda.device_count(),
        "gpu_name": torch.cuda.get_device_name(0),
        "compute_capability": list(torch.cuda.get_device_capability(0)),
    }
    keys = set(observed)
    expected_identity = {key: expected[key] for key in keys}
    if observed != expected_identity:
        raise LinuxA100RunError("Linux A100 runtime identity changed")
    return observed


def _child_env(staging: Path | None, manifest: dict[str, Any]) -> dict[str, str]:
    environment = {
        "PATH": os.defpath,
        "LC_ALL": "C",
        "LANG": "C",
        "TZ": "UTC",
        "HOME": "/nonexistent",
        "CUDA_VISIBLE_DEVICES": os.environ["CUDA_VISIBLE_DEVICES"],
    }
    environment.update(manifest["runtime"]["required_environment"])
    if staging is not None:
        (staging / ".matplotlib").mkdir(mode=0o700, exist_ok=True)
        environment["MPLCONFIGDIR"] = str(staging / ".matplotlib")
    return environment


def _network_probe(manifest: dict[str, Any]) -> None:
    code = (
        "import socket\n"
        "try: socket.create_connection(('1.1.1.1',53),timeout=.2)\n"
        "except OSError: raise SystemExit(0)\n"
        "raise SystemExit(9)\n"
    )
    result = subprocess.run(
        [*manifest["runtime"]["network_isolation_argv"], sys.executable, "-c", code],
        env=_child_env(None, manifest),
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise LinuxA100RunError("rootless network isolation is unavailable")


_CUDA_CHILD = r"""
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
 random.seed(value); np.random.seed(value); torch.manual_seed(value); torch.cuda.manual_seed_all(value)
reset(seed); torch.use_deterministic_algorithms(True); torch.set_num_threads(1); torch.set_num_interop_threads(1)
torch.backends.cudnn.deterministic=True; torch.backends.cudnn.benchmark=False
if not torch.cuda.is_available() or torch.cuda.device_count()!=1: raise RuntimeError('single CUDA device absent')
if torch.cuda.get_device_name(0)!=job['gpu_name']: raise RuntimeError('GPU identity changed')
if list(torch.cuda.get_device_capability(0))!=job['compute_capability']: raise RuntimeError('GPU capability changed')
adata=anndata.read_h5ad(root/'input/native_train_only.h5ad')
pd_=PertData(str(root/'work'))
reset(0); pd_.new_data_process('norman_golden_train_only',adata=adata,skip_calc_de=False)
pd_.split='no_test'; pd_.seed=0; pd_.train_gene_set_size=None; pd_.subgroup=None
pd_.set2conditions=job['split']; pd_.get_dataloader(batch_size=job['batch_size'])
if set(pd_.dataloader)!={'train_loader','val_loader'}: raise RuntimeError('held-out loader present')
reset(seed); g=GEARS(pd_,device='cuda:0',weight_bias_track=False); reset(seed); m=job['model']
g.model_initialize(hidden_size=m['hidden_size'],num_go_gnn_layers=m['num_go_gnn_layers'],
 num_gene_gnn_layers=m['num_gene_gnn_layers'],decoder_hidden_size=m['decoder_hidden_size'],
 num_similar_genes_go_graph=m['num_similar_genes_go_graph'],
 num_similar_genes_co_express_graph=m['num_similar_genes_co_express_graph'],
 coexpress_threshold=m['coexpress_threshold'],uncertainty=m['uncertainty'],
 uncertainty_reg=m['uncertainty_reg'],direction_lambda=m['direction_lambda'],no_perturb=m['no_perturb'])
reset(seed); g.train(epochs=job['epochs'],lr=m['learning_rate'],weight_decay=m['weight_decay'])
torch.cuda.synchronize()
out=root/'model'; out.mkdir(); g.save_model(str(out))
state=torch.load(out/'model.pt',map_location='cpu',weights_only=True)
if not isinstance(state,dict) or not state: raise RuntimeError('empty or unsafe state dict')
records=[]
for key,tensor in sorted(state.items()):
 if not isinstance(key,str) or not isinstance(tensor,torch.Tensor): raise RuntimeError('non-tensor state')
 value=tensor.detach().cpu().contiguous()
 finite=not (value.is_floating_point() or value.is_complex()) or bool(torch.isfinite(value).all())
 if not finite: raise RuntimeError('non-finite tensor')
 records.append({'key':key,'shape':list(value.shape),'dtype':str(value.dtype),'numel':value.numel(),
  'sha256':hashlib.sha256(value.numpy().tobytes()).hexdigest(),'finite':True})
tensor_manifest={'schema_version':'praxis.torch-state-tensor-manifest.v1','weights_only':True,
 'tensor_count':len(records),'total_numel':sum(item['numel'] for item in records),
 'all_finite':True,'tensors':records}
(out/'tensor-manifest.json').write_text(json.dumps(tensor_manifest,sort_keys=True,separators=(',',':'))+'\n')
"""


def _run_child(argv: list[str], *, environment: dict[str, str]) -> tuple[int, bytes, bytes]:
    process = subprocess.Popen(
        argv,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []

    def drain(stream, chunks: list[bytes], descriptor: int) -> None:
        while chunk := stream.read(8192):
            chunks.append(chunk)
            os.write(descriptor, chunk)

    assert process.stdout is not None and process.stderr is not None
    threads = [
        threading.Thread(target=drain, args=(process.stdout, stdout_chunks, 1), daemon=True),
        threading.Thread(target=drain, args=(process.stderr, stderr_chunks, 2), daemon=True),
    ]
    for thread in threads:
        thread.start()
    returncode = process.wait()
    for thread in threads:
        thread.join()
    return returncode, b"".join(stdout_chunks), b"".join(stderr_chunks)


def _sanitized_log(stdout: bytes, stderr: bytes, staging_path: Path) -> bytes:
    try:
        text = (b"STDOUT\n" + stdout + b"\nSTDERR\n" + stderr).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise LinuxA100RunError("GEARS logs are not UTF-8") from exc
    text = text.replace(str(staging_path), "<STAGING>")
    text = re.sub(
        r"(?<![\w.])/(?:home|root|Users|Volumes|private|tmp|var)(?:/[^\s:]+)+",
        "<ABSOLUTE_PATH>",
        text,
    )
    if str(staging_path) in text or staging_path.name in text:
        raise LinuxA100RunError("training log path redaction failed")
    return text.encode("utf-8")


def _execution_claim(*, mode: str, seed: int, epochs: int, batch_size: int) -> dict[str, Any]:
    return {
        "mode": mode,
        "device": "cuda:0",
        "network_denied_by_rootless_namespace": True,
        "filesystem_read_isolation": False,
        "single_visible_gpu": True,
        "torch_deterministic_algorithms": True,
        "cudnn_deterministic": True,
        "cudnn_benchmark": False,
        "child_input_inventory_restricted_to_attested_prepare_artifacts": True,
        "seed": seed,
        "epochs": epochs,
        "batch_size": batch_size,
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
    mode: str,
    seed: int,
    epochs: int,
    batch_size: int,
    protocol: dict[str, Any],
    manifest: dict[str, Any],
    manifest_sha256: str,
    source_record: dict[str, Any],
    source_record_sha256: str,
    runtime: dict[str, Any],
    metrics: dict[str, Any],
    display_metrics: dict[str, Any],
    metrics_call_audit: dict[str, Any],
    log_record: dict[str, Any],
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    role = manifest["record_roles"]["smoke" if mode == "smoke" else "seed"]
    return {
        "schema_version": "praxis.golden-gears-train-only-linux-a100-seed.v1",
        "record_role": role,
        "candidate_name": protocol["candidate"]["name"],
        "mode": mode,
        "protocol_sha256": manifest["identity"]["base_protocol"]["payload_sha256"],
        "linux_run_manifest_payload_sha256": manifest["identity"]["payload_sha256"],
        "linux_run_manifest_sha256": manifest_sha256,
        "linux_worker_sha256": manifest["identity"]["worker_sha256"],
        "prepare_record_sha256": source_record_sha256,
        "prepare_input": source_record["derived_input_artifact"],
        "runtime": runtime,
        "execution": _execution_claim(
            mode=mode,
            seed=seed,
            epochs=epochs,
            batch_size=batch_size,
        ),
        "internal_validation": metrics,
        "internal_validation_log_display": display_metrics,
        "metrics_call_audit": metrics_call_audit,
        "training_log": log_record,
        "contamination_audit": source_record["contamination_audit"],
        "prospective_test_blinding": False,
        "artifacts": artifacts,
        **manifest["claim_ceiling"],
    }


def _inventory(root: Path) -> None:
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise LinuxA100RunError("seed output must be a private operator-owned directory")
    files: set[str] = set()
    directories: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        item = path.lstat()
        if stat.S_ISDIR(item.st_mode):
            directories.add(relative)
        elif stat.S_ISREG(item.st_mode) and item.st_nlink == 1:
            files.add(relative)
        else:
            raise LinuxA100RunError("seed output contains an unsafe entry")
    if files != _SEED_FILES or directories != _SEED_DIRECTORIES:
        raise LinuxA100RunError("seed output inventory changed")


def _verify_metrics(record: dict[str, Any], epochs: int, full) -> None:
    previous = full._EPOCHS
    try:
        full._EPOCHS = epochs
        full._verify_full_precision_metrics(record)
    except Exception as exc:
        raise LinuxA100RunError("full-precision validation receipt changed") from exc
    finally:
        full._EPOCHS = previous


def _verify_log(root: Path, record: dict[str, Any], smoke, epochs: int) -> None:
    payload, _info = smoke._read_regular(root / "training.log")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise LinuxA100RunError("published training log is not UTF-8") from exc
    log_record = record.get("training_log", {})
    if not (
        text.startswith("STDOUT\n\nSTDERR\n")
        and record.get("internal_validation_log_display") == smoke._parse_metrics(text, epochs)
        and set(log_record) == {"raw_stdout_sha256", "raw_stderr_sha256", "published_log_is_path_redacted"}
        and _SHA256.fullmatch(str(log_record.get("raw_stdout_sha256")))
        and _SHA256.fullmatch(str(log_record.get("raw_stderr_sha256")))
        and log_record.get("published_log_is_path_redacted") is True
        and not re.search(
            r"(?<![\w.])/(?:home|root|Users|Volumes|private|tmp|var)(?:/[^\s:]+)+",
            text,
        )
    ):
        raise LinuxA100RunError("published training log or receipt changed")


def _verify_seed(
    *,
    root: Path,
    mode: str,
    seed: int,
    epochs: int,
    batch_size: int,
    builder,
    smoke,
    full,
    protocol: dict[str, Any],
    manifest: dict[str, Any],
    manifest_sha256: str,
    source_record: dict[str, Any],
    source_record_sha256: str,
    runtime: dict[str, Any],
) -> dict[str, Any]:
    _inventory(root)
    payload, _info = smoke._read_regular(root / "candidate-record.json")
    record = _json(payload, builder)
    _verify_log(root, record, smoke, epochs)
    _verify_metrics(record, epochs, full)
    full._verify_safe_runtime_manifests(root, seed, protocol, smoke, builder)
    tensor_payload, _info = smoke._read_regular(root / "model/tensor-manifest.json")
    tensor_manifest = _json(tensor_payload, builder)
    smoke._validate_tensor_manifest(tensor_manifest)
    if tensor_manifest != full._recomputed_tensor_manifest(root / "model/model.pt"):
        raise LinuxA100RunError("checkpoint differs from its tensor manifest")
    artifacts = full._artifact_records(root, builder)
    expected = _seed_record(
        mode=mode,
        seed=seed,
        epochs=epochs,
        batch_size=batch_size,
        protocol=protocol,
        manifest=manifest,
        manifest_sha256=manifest_sha256,
        source_record=source_record,
        source_record_sha256=source_record_sha256,
        runtime=runtime,
        metrics=record.get("internal_validation"),
        display_metrics=record.get("internal_validation_log_display"),
        metrics_call_audit=record.get("metrics_call_audit"),
        log_record=record.get("training_log"),
        artifacts=artifacts,
    )
    if record != expected:
        raise LinuxA100RunError(f"completed seed {seed} record changed")
    for relative in _SEED_FILES:
        item, _info = smoke._read_regular(root / relative)
        if any(prefix in item for prefix in (b"/home/", b"/root/", b"/Users/", b"/Volumes/")):
            raise LinuxA100RunError("published seed contains an absolute local path")
    return record


def _train_seed(
    *,
    mode: str,
    seed: int,
    epochs: int,
    batch_size: int,
    parent: Path,
    parent_fd: int,
    prepare_root: Path,
    builder,
    smoke,
    full,
    protocol: dict[str, Any],
    manifest: dict[str, Any],
    manifest_sha256: str,
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
            raise LinuxA100RunError(f"seed {seed} output must be write-new")
        staging_name, staging_fd = builder._new_staging_directory(parent_fd, output_name)
        staging_path = parent / staging_name
        original_cwd_fd = smoke._bind_working_directory(staging_fd)
        staging = Path(".")
        full._snapshot_inputs(staging, prepare_root, source_record, protocol, builder)
        split = smoke._verify_h5ad(staging / "input/native_train_only.h5ad", protocol, builder)
        job = {
            "seed": seed,
            "epochs": epochs,
            "batch_size": batch_size,
            "split": split,
            "model": protocol["training"]["model"],
            "gpu_name": manifest["runtime"]["gpu_name"],
            "compute_capability": manifest["runtime"]["compute_capability"],
        }
        (staging / "job.json").write_bytes(builder._canonical_bytes(job))
        code = full._METRICS_CAPTURE_CHILD + _CUDA_CHILD + full._FULL_RECEIPTS_CHILD
        argv = [*manifest["runtime"]["network_isolation_argv"], sys.executable, "-c", code]
        returncode, stdout, stderr = _run_child(argv, environment=_child_env(staging, manifest))
        (staging / "training.log").write_bytes(_sanitized_log(stdout, stderr, staging_path))
        if returncode:
            raise LinuxA100RunError(f"GEARS Linux A100 seed {seed} child failed")
        display_metrics = smoke._parse_metrics(stderr.decode("utf-8", errors="strict"), epochs)
        receipt = _json((staging / smoke._RECEIPT).read_bytes(), builder)
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
            and receipt["epochs"] == epochs
            and receipt["test_loader_present"] is False
        ):
            raise LinuxA100RunError("GEARS child receipt changed")
        tensor_manifest = _json((staging / "model/tensor-manifest.json").read_bytes(), builder)
        smoke._validate_tensor_manifest(tensor_manifest)
        artifacts = full._artifact_records(staging, builder)
        record = _seed_record(
            mode=mode,
            seed=seed,
            epochs=epochs,
            batch_size=batch_size,
            protocol=protocol,
            manifest=manifest,
            manifest_sha256=manifest_sha256,
            source_record=source_record,
            source_record_sha256=source_record_sha256,
            runtime=runtime,
            metrics=receipt["internal_validation"],
            display_metrics=display_metrics,
            metrics_call_audit=receipt["metrics_call_audit"],
            log_record={
                "raw_stdout_sha256": hashlib.sha256(stdout).hexdigest(),
                "raw_stderr_sha256": hashlib.sha256(stderr).hexdigest(),
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
            mode=mode,
            seed=seed,
            epochs=epochs,
            batch_size=batch_size,
            builder=builder,
            smoke=smoke,
            full=full,
            protocol=protocol,
            manifest=manifest,
            manifest_sha256=manifest_sha256,
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


def _verify_named_seed(*, parent_fd: int, **context: Any) -> dict[str, Any]:
    seed = context["seed"]
    name = f"seed-{seed}"
    seed_fd = os.open(
        name,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=parent_fd,
    )
    smoke = context["smoke"]
    original_cwd_fd = smoke._bind_working_directory(seed_fd)
    try:
        context["builder"]._assert_named_directory_inode(parent_fd, name, seed_fd)
        context.pop("prepare_root", None)
        record = _verify_seed(root=Path("."), **context)
        context["builder"]._assert_named_directory_inode(parent_fd, name, seed_fd)
        return record
    finally:
        os.fchdir(original_cwd_fd)
        os.close(original_cwd_fd)
        os.close(seed_fd)


def _seed_identity(seed: int, record: dict[str, Any], parent: Path, builder) -> dict[str, Any]:
    root = parent / f"seed-{seed}"
    return {
        "seed": seed,
        "candidate_record": {
            "path": f"seed-{seed}/candidate-record.json",
            **builder._file_record(root / "candidate-record.json", single_link=True),
        },
        "model_pt": {"path": f"seed-{seed}/model/model.pt", **record["artifacts"]["model.pt"]},
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


def _smoke_record(
    record: dict[str, Any],
    parent: Path,
    builder,
    protocol: dict[str, Any],
    manifest: dict[str, Any],
    manifest_sha256: str,
    source_record_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "praxis.golden-gears-train-only-linux-a100-smoke.v1",
        "record_role": manifest["record_roles"]["smoke"],
        "status": "completed",
        "candidate_name": protocol["candidate"]["name"],
        "protocol_sha256": manifest["identity"]["base_protocol"]["payload_sha256"],
        "linux_run_manifest_payload_sha256": manifest["identity"]["payload_sha256"],
        "linux_run_manifest_sha256": manifest_sha256,
        "linux_worker_sha256": manifest["identity"]["worker_sha256"],
        "prepare_record_sha256": source_record_sha256,
        "execution": {
            "seed": 11,
            "epochs": 1,
            "batch_size": 8,
            "device": "cuda:0",
            "verified": True,
            "golden_validation_expression_or_outcomes_read": False,
            "golden_test_expression_or_outcomes_read": False,
        },
        "seed": _seed_identity(11, record, parent, builder),
        **manifest["claim_ceiling"],
    }


def _collection_record(
    records: list[dict[str, Any]],
    parent: Path,
    builder,
    protocol: dict[str, Any],
    manifest: dict[str, Any],
    manifest_sha256: str,
    source_record_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "praxis.golden-gears-train-only-linux-a100-collection.v1",
        "record_role": manifest["record_roles"]["collection"],
        "status": "completed",
        "candidate_name": protocol["candidate"]["name"],
        "protocol_sha256": manifest["identity"]["base_protocol"]["payload_sha256"],
        "linux_run_manifest_payload_sha256": manifest["identity"]["payload_sha256"],
        "linux_run_manifest_sha256": manifest_sha256,
        "linux_worker_sha256": manifest["identity"]["worker_sha256"],
        "prepare_record_sha256": source_record_sha256,
        "execution": {
            "seeds": [11, 23, 37],
            "epochs_per_seed": 20,
            "batch_size": 32,
            "device": "cuda:0",
            "scheduler": "slurm",
            "all_seed_candidates_verified": True,
            "golden_validation_expression_or_outcomes_read": False,
            "golden_test_expression_or_outcomes_read": False,
        },
        "seeds": [
            _seed_identity(seed, record, parent, builder) for seed, record in zip((11, 23, 37), records, strict=True)
        ],
        **manifest["claim_ceiling"],
    }


def _load_context(prepare_root: Path) -> dict[str, Any]:
    builder, smoke, full = _dependencies()
    try:
        protocol = builder._load_protocol(_PROTOCOL_PATH.absolute())
        smoke._verify_runner_identity(builder, protocol)
        manifest, manifest_sha256 = _load_manifest(builder, protocol)
        runtime = _runtime_identity(manifest, builder)
        _network_probe(manifest)
        prepare_root = prepare_root.absolute()
        source_record, source_record_sha256 = smoke._verify_prepare_root(prepare_root, builder, protocol)
        prepared = manifest["prepared_artifact"]
        if (
            builder._file_record(prepare_root / "candidate-record.json", single_link=True)
            != {
                "size_bytes": prepared["candidate_record"]["size_bytes"],
                "sha256": prepared["candidate_record"]["sha256"],
            }
            or builder._fingerprint({**source_record, "protocol_sha256": None})
            != prepared["candidate_record"]["normalized_sha256"]
            or any(
                builder._file_record(prepare_root / relative, single_link=True) != expected
                for relative, expected in prepared["files"].items()
            )
        ):
            raise LinuxA100RunError("prepared artifact differs from the Linux manifest")
    except Exception as exc:
        if isinstance(exc, LinuxA100RunError):
            raise
        raise LinuxA100RunError("Linux A100 inputs or runtime changed") from exc
    return {
        "builder": builder,
        "smoke": smoke,
        "full": full,
        "protocol": protocol,
        "manifest": manifest,
        "manifest_sha256": manifest_sha256,
        "source_record": source_record,
        "source_record_sha256": source_record_sha256,
        "runtime": runtime,
        "prepare_root": prepare_root,
    }


def _open_output(output_root: Path, builder) -> tuple[Path, int]:
    output_root = output_root.absolute()
    parent, parent_fd = builder._validated_output_parent(output_root / "seed-11")
    if parent != output_root or platform.system() != "Linux":
        os.close(parent_fd)
        raise LinuxA100RunError("output root must be an existing private Linux directory")
    return parent, parent_fd


def _read_or_train(
    *,
    mode: str,
    seed: int,
    epochs: int,
    batch_size: int,
    parent: Path,
    parent_fd: int,
    context: dict[str, Any],
) -> dict[str, Any]:
    name = f"seed-{seed}"
    seed_context = {
        **context,
        "mode": mode,
        "seed": seed,
        "epochs": epochs,
        "batch_size": batch_size,
    }
    try:
        info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return _train_seed(parent=parent, parent_fd=parent_fd, **seed_context)
    if not stat.S_ISDIR(info.st_mode):
        raise LinuxA100RunError(f"completed seed {seed} path is not a directory")
    return _verify_named_seed(parent_fd=parent_fd, **seed_context)


def run_smoke(*, prepare_root: Path, output_root: Path) -> dict[str, Any]:
    context = _load_context(prepare_root)
    parent, parent_fd = _open_output(output_root, context["builder"])
    try:
        record = _read_or_train(
            mode="smoke",
            seed=11,
            epochs=1,
            batch_size=8,
            parent=parent,
            parent_fd=parent_fd,
            context=context,
        )
        receipt = _smoke_record(
            record,
            parent,
            context["builder"],
            context["protocol"],
            context["manifest"],
            context["manifest_sha256"],
            context["source_record_sha256"],
        )
        payload = context["builder"]._canonical_bytes(receipt) + b"\n"
        try:
            observed = context["full"]._read_regular_at(parent_fd, "smoke-record.json")
        except FileNotFoundError:
            context["full"]._atomic_write_new(parent_fd, "smoke-record.json", payload, context["builder"])
        else:
            if observed != payload:
                raise LinuxA100RunError("existing smoke receipt changed")
        return receipt
    finally:
        os.close(parent_fd)


def _verify_smoke(smoke_root: Path, context: dict[str, Any]) -> None:
    smoke_root = smoke_root.absolute()
    parent, parent_fd = _open_output(smoke_root, context["builder"])
    try:
        record = _verify_named_seed(
            parent_fd=parent_fd,
            **context,
            mode="smoke",
            seed=11,
            epochs=1,
            batch_size=8,
        )
        expected = _smoke_record(
            record,
            parent,
            context["builder"],
            context["protocol"],
            context["manifest"],
            context["manifest_sha256"],
            context["source_record_sha256"],
        )
        observed = _json(context["full"]._read_regular_at(parent_fd, "smoke-record.json"), context["builder"])
        if observed != expected:
            raise LinuxA100RunError("verified smoke receipt changed")
    finally:
        os.close(parent_fd)


def run_full(*, prepare_root: Path, smoke_root: Path, output_root: Path) -> dict[str, Any]:
    if not os.environ.get("SLURM_JOB_ID"):
        raise LinuxA100RunError("full training must run inside Slurm")
    context = _load_context(prepare_root)
    _verify_smoke(smoke_root, context)
    parent, parent_fd = _open_output(output_root, context["builder"])
    try:
        records = [
            _read_or_train(
                mode="full",
                seed=seed,
                epochs=20,
                batch_size=32,
                parent=parent,
                parent_fd=parent_fd,
                context=context,
            )
            for seed in (11, 23, 37)
        ]
        collection = _collection_record(
            records,
            parent,
            context["builder"],
            context["protocol"],
            context["manifest"],
            context["manifest_sha256"],
            context["source_record_sha256"],
        )
        payload = context["builder"]._canonical_bytes(collection) + b"\n"
        try:
            observed = context["full"]._read_regular_at(parent_fd, "collection-record.json")
        except FileNotFoundError:
            context["full"]._atomic_write_new(parent_fd, "collection-record.json", payload, context["builder"])
        else:
            if observed != payload:
                raise LinuxA100RunError("existing collection receipt changed")
        return collection
    finally:
        os.close(parent_fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    smoke_parser = subparsers.add_parser("smoke")
    smoke_parser.add_argument("--prepare-root", type=Path, required=True)
    smoke_parser.add_argument("--output-root", type=Path, required=True)
    full_parser = subparsers.add_parser("full")
    full_parser.add_argument("--prepare-root", type=Path, required=True)
    full_parser.add_argument("--smoke-root", type=Path, required=True)
    full_parser.add_argument("--output-root", type=Path, required=True)
    arguments = parser.parse_args(argv)
    if arguments.command == "smoke":
        run_smoke(prepare_root=arguments.prepare_root, output_root=arguments.output_root)
    else:
        run_full(
            prepare_root=arguments.prepare_root,
            smoke_root=arguments.smoke_root,
            output_root=arguments.output_root,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
