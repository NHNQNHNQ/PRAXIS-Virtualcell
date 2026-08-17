from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "data/golden/norman_2019/k562_crispra_acquisition_plan.json"
SCRIPT = ROOT / "scripts/verify_k562_crispra_acquisition_plan.py"


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_k562_crispra_acquisition_plan", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def _mutated_plan(tmp_path: Path, value: dict[str, object]) -> Path:
    path = (tmp_path / "changed-plan.json").resolve()
    path.write_bytes(_canonical(value) + b"\n")
    return path


def _accept_mutated_raw(module: ModuleType, monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    raw = path.read_bytes()
    monkeypatch.setattr(module, "_PLAN_SIZE", len(raw))
    monkeypatch.setattr(module, "_PLAN_SHA256", hashlib.sha256(raw).hexdigest())


def _rehash(value: dict[str, object]) -> str:
    identity = value["identity"]
    assert isinstance(identity, dict)
    identity["payload_sha256"] = None
    digest = hashlib.sha256(_canonical(value)).hexdigest()
    identity["payload_sha256"] = digest
    return digest


def test_exact_plan_verifies_and_keeps_claim_ceiling() -> None:
    module = _module()
    result = module.verify_plan(PLAN.resolve())

    assert result == {
        "schema_version": "praxis.k562-crispra-acquisition-plan-verification.v1",
        "status": "VERIFIED_READY_FOR_QUOTE_NOT_WET_LAB_EXECUTION",
        "plan_sha256": "07cc18bb20ad5e27c8795ff74b6024ae16c4e0b4b12c31e2761dbf3bc7ce98ee",
        "plan_payload_sha256": "b6ad8d74a5ae8e9f928f8356e9f3f6a43c323eff7b31159d4ef70b10aead4643",
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


def test_exact_axes_and_value_free_external_pairs_recompute() -> None:
    module = _module()
    plan = json.loads(PLAN.read_text())
    target_ids, symbols, index = module._verify_axes(plan)
    design = plan["condition_design"]
    _, primary_pairs = module._condition_payload(design["replacement_primary_holdout"], target_ids, symbols, index)
    _, external_pairs = module._condition_payload(
        design["independent_external_dataset_and_platform"], target_ids, symbols, index
    )
    reproduced, round_index = module._external_pairs(target_ids, set(primary_pairs), index)

    assert round_index == 0
    assert external_pairs == reproduced
    assert not set(primary_pairs) & set(external_pairs)
    degrees = {target_id: sum(target_id in pair for pair in external_pairs) for target_id in target_ids}
    assert sorted(degrees.values()) == [1] * 64 + [2] * 4


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda value: value["plan_status"].__setitem__("wet_lab_execution_authorized", True),
            "quote-only claim ceiling",
        ),
        (
            lambda value: value["axes"]["feature_axis"]["records"][0].__setitem__("ensembl_gene_id", "ENSG00000000000"),
            "feature axis identity drifted",
        ),
        (
            lambda value: value["condition_design"]["independent_external_dataset_and_platform"]["gene_combination"][
                0
            ].__setitem__("target_a_id", "ENSG00000000000"),
            "combination target order",
        ),
        (
            lambda value: value["wet_lab_contract"]["replication_and_qc"].__setitem__(
                "minimum_qc_singlets_per_condition_per_replicate", 99
            ),
            "wet-lab scope",
        ),
    ],
)
def test_semantic_drift_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutate,
    message: str,
) -> None:
    module = _module()
    value = json.loads(PLAN.read_text())
    mutate(value)
    payload_sha256 = _rehash(value)
    path = _mutated_plan(tmp_path, value)
    _accept_mutated_raw(module, monkeypatch, path)
    monkeypatch.setattr(module, "_PLAN_PAYLOAD_SHA256", payload_sha256)

    with pytest.raises(module.AcquisitionPlanError, match=message):
        module.verify_plan(path)


def test_raw_or_logical_identity_drift_fails_before_semantics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    value = json.loads(PLAN.read_text())
    value["identity"]["payload_sha256"] = "0" * 64
    path = _mutated_plan(tmp_path, value)
    _accept_mutated_raw(module, monkeypatch, path)

    with pytest.raises(module.AcquisitionPlanError, match="logical self-hash"):
        module.verify_plan(path)


def test_duplicate_json_key_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    path = (tmp_path / "duplicate.json").resolve()
    path.write_bytes(b'{"a":1,"a":2}\n')
    _accept_mutated_raw(module, monkeypatch, path)

    with pytest.raises(module.AcquisitionPlanError, match="duplicate JSON key"):
        module.verify_plan(path)


def test_symlink_and_hardlink_are_rejected(tmp_path: Path) -> None:
    module = _module()
    symlink = tmp_path / "plan-link.json"
    try:
        symlink.symlink_to(PLAN)
    except OSError:
        pytest.skip("filesystem cannot represent symlinks")
    with pytest.raises(module.AcquisitionPlanError, match="absolute and non-symlink"):
        module.verify_plan(symlink.absolute())

    copy = tmp_path / "plan-copy.json"
    linked = tmp_path / "plan-hardlink.json"
    copy.write_bytes(PLAN.read_bytes())
    try:
        os.link(copy, linked)
    except OSError:
        pytest.skip("filesystem cannot represent hardlinks")
    with pytest.raises(module.AcquisitionPlanError, match="single-link regular file"):
        module.verify_plan(copy.resolve())


def test_verifier_has_no_scientific_runtime_dependency() -> None:
    source = SCRIPT.read_text()
    assert "import anndata" not in source
    assert "import numpy" not in source
    assert "import pandas" not in source
    assert "import torch" not in source
    assert "golden" not in source.lower()
