from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).parents[1]
_RUNNER = _ROOT / "scripts/train_golden_gears_train_only_candidate.py"
_PROTOCOL = _ROOT / "data/golden/norman_2019/gears_train_only_protocol.json"


def _runner():
    spec = importlib.util.spec_from_file_location("golden_gears_train_runner", _RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_metric_parser_requires_one_finite_top20_value_per_epoch() -> None:
    module = _runner()
    stdout = """Epoch 1: Train Overall MSE: 0.1 Validation Overall MSE: 0.2.
Train Top 20 DE MSE: 0.3 Validation Top 20 DE MSE: 0.0200.
Epoch 2: Train Overall MSE: 0.1 Validation Overall MSE: 0.2.
Train Top 20 DE MSE: 0.3 Validation Top 20 DE MSE: 0.0100.
"""
    assert module._parse_metrics(stdout, 2)["best_epoch"] == 2
    with pytest.raises(module.CandidateTrainError, match="finite validation"):
        module._parse_metrics(stdout.replace("0.0100", "nan"), 2)
    with pytest.raises(module.CandidateTrainError, match="finite validation"):
        module._parse_metrics(stdout.split("Epoch 2")[0], 2)


def test_internal_split_is_recomputed_and_bound_to_protocol() -> None:
    module = _runner()
    builder = module._builder()
    protocol = json.loads(_PROTOCOL.read_text(encoding="utf-8"))
    labels = ["ctrl", "A+ctrl", "B+ctrl", "A+B"]
    ids = [f"cell-{index}" for index in range(len(labels))]
    native = protocol["training"]["native_input"]
    native["rows"] = len(labels)
    native["observation_ids_source_order_sha256"] = builder._fingerprint(ids)
    native["canonical_child_labels_including_control_sha256"] = builder._fingerprint(sorted(labels))
    ranked = sorted(
        (builder._canonical_targets(value) for value in labels if value != "ctrl"),
        key=lambda item: (builder._rank(item, 0), item),
    )
    val_targets, train_targets = ranked[:1], ranked[1:]
    train_labels = sorted(["ctrl", *(builder._child_label(item) for item in train_targets)])
    val_labels = sorted(builder._child_label(item) for item in val_targets)
    train_ids = [item for item, label in zip(ids, labels, strict=True) if label in train_labels]
    val_ids = [item for item, label in zip(ids, labels, strict=True) if label in val_labels]
    internal = protocol["training"]["internal_validation"]
    internal.update(
        {
            "train_rank_order_target_lists_sha256": builder._fingerprint([list(item) for item in train_targets]),
            "validation_rank_order_target_lists_sha256": builder._fingerprint([list(item) for item in val_targets]),
            "train_canonical_labels_with_control_sha256": builder._fingerprint(train_labels),
            "validation_canonical_labels_sha256": builder._fingerprint(val_labels),
            "train_rows": len(train_ids),
            "train_observation_ids_source_order_sha256": builder._fingerprint(train_ids),
            "validation_rows": len(val_ids),
            "validation_observation_ids_source_order_sha256": builder._fingerprint(val_ids),
        }
    )
    assert module._split_from_labels(ids, labels, protocol, builder) == {
        "train": train_labels,
        "val": val_labels,
    }
    labels[-1] = "A+C"
    with pytest.raises(module.CandidateTrainError):
        module._split_from_labels(ids, labels, protocol, builder)


def test_tensor_manifest_must_be_weights_only_and_finite() -> None:
    module = _runner()
    value = {
        "schema_version": "praxis.torch-state-tensor-manifest.v1",
        "weights_only": True,
        "tensor_count": 1,
        "total_numel": 2,
        "all_finite": True,
        "tensors": [
            {
                "key": "weight",
                "shape": [2],
                "dtype": "torch.float32",
                "numel": 2,
                "sha256": "a" * 64,
                "finite": True,
            }
        ],
    }
    module._validate_tensor_manifest(value)
    value["tensors"][0]["finite"] = False
    with pytest.raises(module.CandidateTrainError, match="tensor manifest"):
        module._validate_tensor_manifest(value)


def test_venv_symlink_invocation_is_bound_lexically(tmp_path: Path) -> None:
    module = _runner()
    base = tmp_path / "base"
    prefix = tmp_path / "venv"
    (base / "bin").mkdir(parents=True)
    (prefix / "bin").mkdir(parents=True)
    target = base / "bin/python"
    target.write_bytes(b"")
    executable = prefix / "bin/python"
    executable.symlink_to(target)
    assert executable.resolve() == target
    assert module._is_venv_invocation(executable, prefix, base)


def test_published_log_redacts_staging_and_local_absolute_paths(tmp_path: Path) -> None:
    module = _runner()
    staging = tmp_path / ".candidate.secret"
    payload = module._sanitized_log(
        f"saved {staging}/model/model.pt\n".encode(),
        b"cache /Users/person/private/cache\n",
        staging,
    )
    assert str(staging).encode() not in payload
    assert staging.name.encode() not in payload
    assert b"/Users/" not in payload
    assert b"<STAGING>" in payload


def test_writes_remain_bound_to_open_staging_inode_after_name_replacement(tmp_path: Path) -> None:
    module = _runner()
    builder = module._builder()
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    _trusted, parent_fd = builder._validated_output_parent(parent / "candidate")
    name, staging_fd = builder._new_staging_directory(parent_fd, "candidate")
    original_fd = module._bind_working_directory(staging_fd)
    try:
        (parent / name).rename(parent / "displaced")
        (parent / name).mkdir(mode=0o700)
        Path("bound.txt").write_bytes(b"bound to descriptor")
        assert (parent / "displaced/bound.txt").read_bytes() == b"bound to descriptor"
        assert not (parent / name / "bound.txt").exists()
    finally:
        os.fchdir(original_fd)
        os.close(original_fd)
        os.close(staging_fd)
        os.close(parent_fd)


def test_runner_is_smoke_only_and_never_names_heldout_expression() -> None:
    source = _RUNNER.read_text(encoding="utf-8")
    assert 'choices=("smoke",)' in source
    assert "deny network*" in source
    assert "weights_only=True" in source
    assert "KMP_DUPLICATE_LIB_OK" not in source
    assert '"internal_validation_de_dropout_preprocessing_independent": False' in source
    assert '"internal_validation_coexpression_graph_independent": True' in source
    assert '"internal_validation_gradient_fit_excludes_validation": True' in source
    assert '"filesystem_read_isolation": False' in source
    assert 'golden_validation_expression_used": False' in source
    assert 'golden_test_expression_used": False' in source
    assert "_parse_metrics(result.stderr.decode" in source


def test_prepare_record_attestation_breaks_the_protocol_hash_cycle() -> None:
    source = _RUNNER.read_text(encoding="utf-8")
    assert 'normalized_record["protocol_sha256"] = None' in source
    assert "candidate_record_normalized" in source
    assert "builder._fingerprint(normalized_record)" in source


def test_frozen_protocol_binds_this_runner_and_prepared_input() -> None:
    module = _runner()
    builder = module._builder()
    protocol = builder._load_protocol(_PROTOCOL.resolve())
    assert module._verify_runner_identity(builder, protocol) == builder._sha256(_RUNNER)
    attestation = protocol["execution_boundary"]["prepared_artifact_attestation"]
    assert attestation["native_train_only_h5ad"] == {
        "size_bytes": 153256772,
        "sha256": "8c14761e0cc760386ef6564e542d80865caefc1bc0152b11f765218e49f95cf0",
    }
    assert attestation["candidate_record_normalized"]["algorithm"] == (
        "sha256(canonical_json(candidate_record_with_protocol_sha256_set_to_null))"
    )
