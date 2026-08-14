from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).parents[1]
_WORKER = _ROOT / "scripts/run_golden_gears_train_only_linux_a100.py"
_MANIFEST = _ROOT / "data/golden/norman_2019/gears_train_only_linux_a100_run.json"
_PROTOCOL = _ROOT / "data/golden/norman_2019/gears_train_only_protocol.json"


def _worker():
    spec = importlib.util.spec_from_file_location("golden_gears_linux_a100", _WORKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_manifest_binds_worker_dependencies_protocol_and_payload() -> None:
    module = _worker()
    builder, _smoke, _full = module._dependencies()
    protocol = builder._load_protocol(_PROTOCOL.resolve())
    manifest, raw_sha256 = module._load_manifest(builder, protocol)
    assert manifest["identity"]["worker_sha256"] == builder._sha256(_WORKER)
    assert manifest["identity"]["base_protocol"] == {
        "path": "data/golden/norman_2019/gears_train_only_protocol.json",
        "size_bytes": 22605,
        "sha256": "30d2bf08edd1fb41232699fe3588a09bfa18ecd2cf5881ed1eb5c5134a4e9bc3",
        "payload_sha256": "58285f730f46dc7fe7f5aad752a80cb8d22184171ff9186fd93e4040280388ef",
    }
    assert raw_sha256 == hashlib.sha256(_MANIFEST.read_bytes()).hexdigest()
    for relative, expected in manifest["identity"]["source_dependencies"].items():
        assert builder._sha256(_ROOT / relative) == expected


def test_contract_is_linux_a100_train_only_and_never_accepts_heldout_paths() -> None:
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    source = _WORKER.read_text(encoding="utf-8")
    assert manifest["runtime"]["platform_system"] == "Linux"
    assert manifest["runtime"]["logical_device"] == "cuda:0"
    assert manifest["runtime"]["visible_device_count"] == 1
    assert manifest["execution"]["smoke"] == {
        "seed": 11,
        "epochs": 1,
        "batch_size": 8,
        "output_record": "smoke-record.json",
    }
    assert manifest["execution"]["full"]["seeds"] == [11, 23, 37]
    assert manifest["execution"]["full"]["epochs_per_seed"] == 20
    assert manifest["execution"]["full"]["batch_size"] == 32
    assert manifest["data_boundary"]["golden_validation_expression_or_outcomes_read"] is False
    assert manifest["data_boundary"]["golden_test_expression_or_outcomes_read"] is False
    assert "norman_k562_golden.h5ad" not in source
    assert "validation-truth" not in source
    assert "test_loader" in source


def test_cuda_child_is_deterministic_single_gpu_and_has_no_test_loader() -> None:
    module = _worker()
    child = module._CUDA_CHILD
    assert "device='cuda:0'" in child
    assert "torch.cuda.device_count()!=1" in child
    assert "torch.use_deterministic_algorithms(True)" in child
    assert "torch.backends.cudnn.deterministic=True" in child
    assert "torch.backends.cudnn.benchmark=False" in child
    assert "set(pd_.dataloader)!={'train_loader','val_loader'}" in child
    assert "test_loader" not in child


def test_child_environment_preserves_only_one_visible_gpu(monkeypatch, tmp_path: Path) -> None:
    module = _worker()
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "GPU-fixture")
    environment = module._child_env(tmp_path, manifest)
    assert environment["CUDA_VISIBLE_DEVICES"] == "GPU-fixture"
    assert environment["CUBLAS_WORKSPACE_CONFIG"] == ":4096:8"
    assert environment["MPLCONFIGDIR"] == str(tmp_path / ".matplotlib")
    assert not set(manifest["runtime"]["forbidden_environment"]).intersection(environment)
    assert set(environment) == {
        "PATH",
        "LC_ALL",
        "LANG",
        "TZ",
        "HOME",
        "MPLCONFIGDIR",
        "CUDA_VISIBLE_DEVICES",
        *manifest["runtime"]["required_environment"],
    }


def test_full_requires_slurm_before_loading_any_candidate(monkeypatch, tmp_path: Path) -> None:
    module = _worker()
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    monkeypatch.setattr(
        module,
        "_load_context",
        lambda _path: (_ for _ in ()).throw(AssertionError("must not load inputs")),
    )
    with pytest.raises(module.LinuxA100RunError, match="inside Slurm"):
        module.run_full(
            prepare_root=tmp_path / "prepare",
            smoke_root=tmp_path / "smoke",
            output_root=tmp_path / "full",
        )


def test_full_smoke_gate_only_verifies_and_never_trains(monkeypatch, tmp_path: Path) -> None:
    module = _worker()
    root = tmp_path / "smoke"
    root.mkdir(mode=0o700)
    parent_fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    record = {"fixture": True}
    context = {
        "builder": SimpleNamespace(),
        "smoke": SimpleNamespace(),
        "full": SimpleNamespace(_read_regular_at=lambda *_args: b"{}"),
        "protocol": {},
        "manifest": {},
        "manifest_sha256": "manifest",
        "source_record": {},
        "source_record_sha256": "prepare",
        "runtime": {},
        "prepare_root": tmp_path / "prepare",
    }
    monkeypatch.setattr(module, "_open_output", lambda *_args: (root, parent_fd))
    monkeypatch.setattr(module, "_verify_named_seed", lambda **_kwargs: record)
    monkeypatch.setattr(module, "_smoke_record", lambda *_args: {"verified": True})
    monkeypatch.setattr(
        module,
        "_read_or_train",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("must not train")),
    )
    monkeypatch.setattr(
        module,
        "_json",
        lambda *_args: {"verified": True},
    )
    module._verify_smoke(root, context)


def test_network_namespace_contract_is_exact() -> None:
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["runtime"]["network_isolation_argv"] == [
        "/usr/bin/unshare",
        "--user",
        "--map-root-user",
        "--net",
        "--",
    ]
    assert manifest["runtime"]["filesystem_read_isolation"] is False


def test_claim_ceiling_never_promotes_science_or_benchmark() -> None:
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["claim_ceiling"] == {
        "benchmark_status": "NOT_RUN",
        "benchmark_passed": None,
        "scientifically_validated": False,
        "promotion_eligible": False,
        "production_promoted": False,
        "registry_or_default_route_changed": False,
        "bitwise_equivalent_to_darwin_cpu_candidate": False,
    }
