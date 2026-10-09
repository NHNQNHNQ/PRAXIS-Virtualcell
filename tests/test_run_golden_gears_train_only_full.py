from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).parents[1]
_WORKER = _ROOT / "scripts/run_golden_gears_train_only_full.py"
_SMOKE_RUNNER = _ROOT / "scripts/train_golden_gears_train_only_candidate.py"
_PROTOCOL = _ROOT / "data/golden/norman_2019/gears_train_only_protocol.json"


def _worker():
    spec = importlib.util.spec_from_file_location("golden_gears_full_worker", _WORKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_full_run_manifest_binds_worker_protocol_and_prepare_attestations() -> None:
    module = _worker()
    smoke = module._smoke_runner()
    builder = smoke._builder()
    protocol = builder._load_protocol(_PROTOCOL.resolve())
    manifest, raw_sha256 = module._load_and_verify_manifest(smoke, builder, protocol)
    assert manifest["identity"] == {
        "payload_sha256": manifest["identity"]["payload_sha256"],
        "payload_hash_algorithm": "sha256(canonical_json(manifest_with_identity.payload_sha256_set_to_null))",
        "base_protocol_path": "data/golden/norman_2019/gears_train_only_protocol.json",
        "base_protocol_payload_sha256": "58285f730f46dc7fe7f5aad752a80cb8d22184171ff9186fd93e4040280388ef",
        "worker_path": "scripts/run_golden_gears_train_only_full.py",
        "worker_sha256": builder._sha256(_WORKER),
        "smoke_helper_path": "scripts/train_golden_gears_train_only_candidate.py",
        "smoke_helper_sha256": "635db2e12fcfaa1668414c8bc812e6a015ac95aea39640def3884b2e28ff6582",
    }
    assert raw_sha256 == hashlib.sha256(module._RUN_MANIFEST_PATH.read_bytes()).hexdigest()
    assert manifest["prepared_artifact_attestation"] == {
        **protocol["execution_boundary"]["prepared_artifact_attestation"],
        "gears_assets": manifest["prepared_artifact_attestation"]["gears_assets"],
    }
    assert builder._sha256(_SMOKE_RUNNER) == manifest["identity"]["smoke_helper_sha256"]


def test_contract_is_fixed_and_child_never_receives_heldout_paths() -> None:
    module = _worker()
    source = _WORKER.read_text(encoding="utf-8")
    manifest = json.loads(module._RUN_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["execution"]["seeds"] == [11, 23, 37]
    assert manifest["execution"]["epochs_per_seed"] == 20
    assert manifest["execution"]["batch_size"] == 32
    assert manifest["execution"]["device"] == "cpu"
    assert manifest["execution"]["expected_compute_metrics_calls_per_seed"] == 40
    assert manifest["execution"]["child_inputs"] == [
        "input/native_train_only.h5ad",
        "work/gene2go_all.pkl",
        "work/essential_all_data_pert_genes.pkl",
        "work/go_essential_all/go_essential_all.csv",
        "job.json",
    ]
    assert "norman_k562_golden.h5ad" not in source
    assert "pack_root" not in source
    assert "deny network*" in source
    assert "captured_compute_metrics" in source
    assert "full_float_from_gears_compute_metrics" in source
    assert '"filesystem_read_isolation": False' in source


def test_checkpoint_selection_uses_full_precision_not_rounded_log_value() -> None:
    module = _worker()
    values = [0.100049 - index / 1_000_000 for index in range(20)]
    best = min(range(20), key=values.__getitem__)
    metric_set = {"mse": 0.1, "mse_de": 0.2, "pearson": 0.3, "pearson_de": 0.4}
    audit = [
        {
            "epoch": index + 1,
            "train": dict(metric_set),
            "validation": {**metric_set, "mse_de": value},
        }
        for index, value in enumerate(values)
    ]
    record = {
        "internal_validation": {
            "metric": "internal_validation_mse_de",
            "precision": "full_float_from_gears_compute_metrics",
            "per_epoch": [{"epoch": index + 1, "value": value} for index, value in enumerate(values)],
            "best_epoch": best + 1,
            "best_value": values[best],
        },
        "internal_validation_log_display": {
            "per_epoch": [{"epoch": index + 1, "value": float(f"{value:.4f}")} for index, value in enumerate(values)]
        },
        "metrics_call_audit": {
            "call_order": "train_then_validation_each_epoch",
            "expected_calls": 40,
            "observed_calls": 40,
            "per_epoch": audit,
        },
    }
    module._verify_full_precision_metrics(record)
    record["internal_validation"]["best_epoch"] = 1
    with pytest.raises(module.FullTrainError, match="checkpoint selection"):
        module._verify_full_precision_metrics(record)


def test_seed_inventory_rejects_extra_directory_and_special_entry(
    tmp_path: Path,
) -> None:
    module = _worker()
    root = tmp_path / "seed-11"
    (root / "model").mkdir(parents=True, mode=0o700)
    root.chmod(0o700)
    for relative in module._SEED_FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
    module._inventory(root)
    (root / "extra").mkdir()
    with pytest.raises(module.FullTrainError, match="inventory"):
        module._inventory(root)
    (root / "extra").rmdir()
    os.mkfifo(root / "special")
    with pytest.raises(module.FullTrainError, match="special"):
        module._inventory(root)


def test_safe_config_and_runtime_graph_manifest_are_strict(tmp_path: Path) -> None:
    module = _worker()
    smoke = module._smoke_runner()
    builder = smoke._builder()
    protocol = json.loads(_PROTOCOL.read_text(encoding="utf-8"))
    model = tmp_path / "model"
    model.mkdir()
    safe = {
        "schema_version": "praxis.golden-gears-safe-config.v1",
        "model": protocol["training"]["model"],
    }
    tensor = {
        "shape": [2, 3],
        "dtype": "torch.int64",
        "numel": 6,
        "sha256": "a" * 64,
        "finite": True,
    }
    weight = {
        "shape": [3],
        "dtype": "torch.float32",
        "numel": 3,
        "sha256": "b" * 64,
        "finite": True,
    }
    graph = {
        "schema_version": "praxis.gears-runtime-graph-manifest.v1",
        "seed": 11,
        "vocabularies": {
            "gene": {"count": 5045, "canonical_json_sha256": "c" * 64},
            "perturbation": {"count": 68, "canonical_json_sha256": "d" * 64},
        },
        "graphs": {
            "G_go": {
                "node_vocabulary": "perturbation",
                "edge_index": tensor,
                "edge_weight": weight,
            },
            "G_coexpress": {
                "node_vocabulary": "gene",
                "edge_index": tensor,
                "edge_weight": weight,
            },
        },
    }
    (model / "safe-config.json").write_bytes(builder._canonical_bytes(safe) + b"\n")
    (model / "runtime-graph-manifest.json").write_bytes(builder._canonical_bytes(graph) + b"\n")
    module._verify_safe_runtime_manifests(tmp_path, 11, protocol, smoke, builder)
    graph["seed"] = 23
    (model / "runtime-graph-manifest.json").write_bytes(builder._canonical_bytes(graph) + b"\n")
    with pytest.raises(module.FullTrainError, match="graph manifest"):
        module._verify_safe_runtime_manifests(tmp_path, 11, protocol, smoke, builder)


def test_atomic_collection_publication_never_replaces(tmp_path: Path) -> None:
    module = _worker()
    builder = module._smoke_runner()._builder()
    parent_fd = os.open(tmp_path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        module._atomic_write_new(parent_fd, "collection-record.json", b"first\n", builder)
        with pytest.raises(Exception, match="write-new"):
            module._atomic_write_new(parent_fd, "collection-record.json", b"second\n", builder)
        assert (tmp_path / "collection-record.json").read_bytes() == b"first\n"
    finally:
        os.close(parent_fd)


def test_resume_verifies_completed_seed_and_trains_only_missing_seeds(monkeypatch, tmp_path: Path) -> None:
    module = _worker()
    output = tmp_path / "output"
    output.mkdir(mode=0o700)
    (output / "seed-11").mkdir(mode=0o700)
    protocol = {"candidate": {"name": "fixture"}}

    class Builder:
        def _load_protocol(self, _path):
            return protocol

        def _validated_output_parent(self, _path):
            return output, os.open(output, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))

        def _canonical_bytes(self, value):
            return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

    builder = Builder()
    smoke = SimpleNamespace(
        _builder=lambda: builder,
        _verify_runner_identity=lambda *_args: None,
        _verify_runtime=lambda *_args: {},
        _verify_prepare_root=lambda *_args: ({}, "prepare-sha"),
        _is_apfs=lambda _path: True,
    )
    manifest = {
        "identity": {
            "base_protocol_payload_sha256": "protocol",
            "payload_sha256": "manifest",
            "worker_sha256": "worker",
        },
        "claim_ceiling": {},
    }
    calls: list[tuple[str, int]] = []
    monkeypatch.setattr(module, "_smoke_runner", lambda: smoke)
    monkeypatch.setattr(module, "_load_and_verify_manifest", lambda *_args: (manifest, "manifest-raw"))
    monkeypatch.setattr(
        module,
        "_verify_named_seed",
        lambda *, seed, **_kwargs: calls.append(("verify", seed)) or {"seed": seed},
    )
    monkeypatch.setattr(
        module,
        "_train_seed",
        lambda *, seed, **_kwargs: calls.append(("train", seed)) or {"seed": seed},
    )
    monkeypatch.setattr(module, "_collection_record", lambda **_kwargs: {"status": "completed"})
    monkeypatch.setattr(module, "_atomic_write_new", lambda *_args, **_kwargs: None)
    module.run_full(prepare_root=tmp_path / "prepare", output_root=output)
    assert calls == [("verify", 11), ("train", 23), ("train", 37)]
