from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

_ROOT = Path(__file__).parents[1]
_BUILDER_PATH = _ROOT / "scripts/build_golden_gears_train_only_candidate.py"
_PROTOCOL_PATH = _ROOT / "data/golden/norman_2019/gears_train_only_protocol.json"


def _builder():
    spec = importlib.util.spec_from_file_location("golden_gears_builder", _BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _unfrozen_protocol() -> dict:
    return json.loads(_PROTOCOL_PATH.read_text(encoding="utf-8"))


def test_protocol_identity_and_claim_ceiling_are_frozen() -> None:
    value = _unfrozen_protocol()
    module = _builder()
    assert value["identity"]["builder_sha256"] == module._sha256(_BUILDER_PATH)
    copy = json.loads(module._canonical_bytes(value))
    copy["identity"]["payload_sha256"] = None
    assert value["identity"]["payload_sha256"] == module._fingerprint(copy)
    assert value["claim_ceiling"] == {
        "output_schema_version": "praxis.golden-gears-train-only-candidate.v1",
        "output_record_role": "candidate_training_and_contamination_audit_not_scientific_evidence",
        "benchmark_status": "NOT_RUN",
        "benchmark_passed": None,
        "scientifically_validated": False,
        "promotion_eligible": False,
        "production_promoted": False,
    }
    assert value["validation_gate_before_descriptive_test"]["evaluator_status"] == ("NOT_IMPLEMENTED_NOT_EXECUTABLE")


def test_duplicate_protocol_keys_fail_closed(tmp_path: Path) -> None:
    module = _builder()
    path = tmp_path / "protocol.json"
    path.write_text('{"schema_version":"x","schema_version":"y"}', encoding="utf-8")
    with pytest.raises(module.CandidateBuildError, match="duplicate JSON keys"):
        module._load_protocol(path)


def test_graph_scope_audit_binds_native_and_fallback_sets() -> None:
    module = _builder()
    protocol = _unfrozen_protocol()
    rows: list[tuple[str, str, str]] = []
    for partition in ("train", "validation", "test"):
        control = protocol["pack"]["control_condition_ids"][partition]
        rows.append((f"{partition}-ctrl", partition, control))
    rows.extend(
        [
            ("train-a", "train", "A+ctrl"),
            ("train-missing", "train", "MISSING+ctrl"),
            ("validation-a", "validation", "B+ctrl"),
            ("test-a", "test", "A+B"),
            ("test-missing", "test", "A+MISSING2"),
        ]
    )
    obs = pd.DataFrame(
        {"split": [row[1] for row in rows], "condition_id": [row[2] for row in rows]},
        index=[row[0] for row in rows],
    )
    mapping = {
        value: module._canonical_targets(value)
        for value in obs["condition_id"]
        if not value.startswith("norman.control.")
    }
    eligible = {"A", "B"}
    fallback = protocol["candidate"]["fallback"]
    fallback["unsupported_train_targets"] = {
        "symbols": ["MISSING"],
        "count": 1,
        "sha256": module._fingerprint(["MISSING"]),
    }
    fallback["excluded_from_native_training"] = {
        "rows": 1,
        "conditions": {"MISSING+ctrl": 1},
        "condition_ids_sha256": module._fingerprint(["MISSING+ctrl"]),
    }
    fallback["unsupported_test_targets"] = {
        "symbols": ["MISSING2"],
        "count": 1,
        "sha256": module._fingerprint(["MISSING2"]),
    }
    fallback.update(
        {
            "expected_test_native_raw_conditions": 1,
            "expected_test_native_raw_condition_ids_sha256": module._fingerprint(["A+B"]),
            "expected_test_native_canonical_conditions": 1,
            "expected_test_native_canonical_conditions_sha256": module._fingerprint([["A", "B"]]),
            "expected_test_fallback_conditions": ["A+MISSING2"],
            "expected_test_fallback_rows": 1,
            "expected_test_fallback_condition_ids_sha256": module._fingerprint(["A+MISSING2"]),
            "expected_test_fallback_observation_ids_source_order_sha256": module._fingerprint(["test-missing"]),
            "expected_test_fallback_observation_ids_sorted_sha256": module._fingerprint(["test-missing"]),
        }
    )
    protocol["training"]["native_input"]["excluded_observation_ids"] = {
        "count": 1,
        "source_order_sha256": module._fingerprint(["train-missing"]),
        "sorted_sha256": module._fingerprint(["train-missing"]),
    }

    result = module._graph_scope_audit(obs, protocol, mapping, eligible)
    assert result["train"]["unsupported_conditions"] == ["MISSING+ctrl"]
    assert result["validation"]["unsupported_conditions"] == []
    assert result["test"]["unsupported_conditions"] == ["A+MISSING2"]

    obs.loc["validation-a", "condition_id"] = "B+MISSING"
    mapping["B+MISSING"] = ("B", "MISSING")
    with pytest.raises(module.CandidateBuildError, match="graph scope identity changed"):
        module._graph_scope_audit(obs, protocol, mapping, eligible)


def test_cli_has_no_interpreter_override() -> None:
    source = _BUILDER_PATH.read_text(encoding="utf-8")
    assert 'add_argument("--python"' not in source
    assert "python = Path(sys.executable)" in source
    assert "deny network*" in source
    assert "KMP_DUPLICATE_LIB_OK" not in source


def test_output_parent_rejects_intermediate_symlink(tmp_path: Path) -> None:
    module = _builder()
    outside = tmp_path / "outside"
    outside.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(outside, target_is_directory=True)
    with pytest.raises(module.CandidateBuildError, match="symlink or non-directory"):
        module._validated_output_parent(alias / "nested" / "candidate")
    assert not (outside / "nested").exists()


def test_parent_environment_is_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _builder()
    protocol = _unfrozen_protocol()
    required = protocol["runtime_environment"]["required_environment"]
    monkeypatch.setattr(module.site, "ENABLE_USER_SITE", False)
    for name, value in required.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("KMP_DUPLICATE_LIB_OK", raising=False)
    module._validate_parent_environment(protocol)
    monkeypatch.setenv("OMP_NUM_THREADS", "2")
    with pytest.raises(module.CandidateBuildError, match="OMP_NUM_THREADS"):
        module._validate_parent_environment(protocol)
    monkeypatch.setenv("OMP_NUM_THREADS", required["OMP_NUM_THREADS"])
    monkeypatch.setenv("KMP_DUPLICATE_LIB_OK", "TRUE")
    with pytest.raises(module.CandidateBuildError, match="forbidden parent"):
        module._validate_parent_environment(protocol)


def test_parent_module_outside_venv_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _builder()
    fake = tmp_path / "numpy.py"
    fake.write_text("# injected", encoding="utf-8")
    monkeypatch.setattr(module.importlib, "import_module", lambda _name: SimpleNamespace(__file__=str(fake)))
    import importlib.metadata

    monkeypatch.setattr(importlib.metadata, "version", lambda _name: "1")
    runtime = {"packages": {name: "1" for name in ("anndata", "h5py", "numpy", "pandas", "PyYAML")}}
    with pytest.raises(module.CandidateBuildError, match="outside the frozen runtime"):
        module._validate_parent_module_origins(runtime)


def test_snapshot_binds_the_open_source_bytes(tmp_path: Path) -> None:
    module = _builder()
    source = tmp_path / "source.bin"
    target = tmp_path / "snapshot.bin"
    source.write_bytes(b"verified bytes")
    expected = module._sha256(source)
    module._snapshot_regular_file(source, target, size=14, sha256=expected)
    assert target.read_bytes() == b"verified bytes"
    with pytest.raises(module.CandidateBuildError, match="differed while snapshotting"):
        module._snapshot_regular_file(source, tmp_path / "bad.bin", size=14, sha256="0" * 64)


def test_staging_is_created_relative_to_held_parent_fd(tmp_path: Path) -> None:
    module = _builder()
    trusted = tmp_path / "trusted"
    trusted.mkdir(mode=0o700)
    _parent, parent_fd = module._validated_output_parent(trusted / "candidate")
    try:
        name, staging_fd = module._new_staging_directory(parent_fd, "candidate")
        try:
            assert name.startswith(".candidate.")
            assert (os.fstat(staging_fd).st_dev, os.fstat(staging_fd).st_ino) == (
                (trusted / name).stat().st_dev,
                (trusted / name).stat().st_ino,
            )
        finally:
            os.close(staging_fd)
    finally:
        os.close(parent_fd)


def test_replaced_staging_name_is_rejected_before_publish(tmp_path: Path) -> None:
    module = _builder()
    trusted = tmp_path / "trusted"
    trusted.mkdir(mode=0o700)
    _parent, parent_fd = module._validated_output_parent(trusted / "candidate")
    name, staging_fd = module._new_staging_directory(parent_fd, "candidate")
    try:
        (trusted / name).rename(trusted / "displaced")
        (trusted / name).mkdir(mode=0o700)
        with pytest.raises(module.CandidateBuildError, match="identity changed"):
            module._assert_named_directory_inode(parent_fd, name, staging_fd)
    finally:
        os.close(staging_fd)
        os.close(parent_fd)
