"""P1 运行时模型权威清单：路由必须只使用 ready 工件。"""
import copy
import json
import os
from dataclasses import replace
from pathlib import Path
from shutil import copyfile

import pytest
import yaml

import praxis_virtualcell.model_zoo.runtime_manifest as runtime_manifest_module
from praxis_virtualcell.mdr_gnb.coordinator.mdr_router import route_mdr
from praxis_virtualcell.mdr_gnb.predictors.default_registry import build_default_registry
from praxis_virtualcell.mdr_gnb.predictors.registry import PredictorRegistry, PredictorSpec
from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
from praxis_virtualcell.model_zoo.runtime_manifest import (
    RuntimeModelManifest,
    capture_runtime_model_execution_context,
    get_runtime_manifest,
    sha256_file,
)
from praxis_virtualcell.model_zoo.tools.build_mdr_gnb_catalog import (
    build_catalog,
    evidence_record_sha256,
)


# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts


def _sir_request(drug: str = "meropenem") -> dict:
    return {
        "species": "escherichia_coli",
        "drug": drug,
        "drug_class": "carbapenems",
        "requested_outputs": ["SIR"],
    }


def _temporary_ready_sir_catalog(tmp_path: Path) -> tuple[Path, Path]:
    """Copy one real ready artifact into an isolated catalog for drift tests."""
    source = RuntimeModelManifest()
    model_id = "sir/escherichia_coli/meropenem"
    model = copy.deepcopy(source.models[model_id])
    source_artifact = source._repo_path(str(model["asset"]["path"]))
    artifact = tmp_path / "model.joblib"
    copyfile(source_artifact, artifact)
    model["asset"] = {
        "path": artifact.name,
        "sha256": sha256_file(artifact),
    }
    generated_from = {}
    copied_sources = {
        "sir_batch_manifest": "batch.yaml",
        "evidence_tiers": "evidence_tiers.yaml",
        "amrfinder_sir_rules": "amrfinder_sir_rules.yaml",
    }
    for source_name, filename in copied_sources.items():
        source_path = source._repo_path(
            str(source.doc["generated_from"][source_name]["path"])
        )
        destination = tmp_path / filename
        copyfile(source_path, destination)
        generated_from[source_name] = {
            "path": destination.name,
            "sha256": sha256_file(destination),
        }
    evidence_tiers = tmp_path / copied_sources["evidence_tiers"]
    validation = model["validation"]
    validation["evidence_source_path"] = evidence_tiers.name
    validation["evidence_source_sha256"] = sha256_file(evidence_tiers)
    catalog = tmp_path / "runtime.yaml"
    catalog.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "catalog_version": "test-request-context",
                "generated_from": generated_from,
                "models": {model_id: model},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return catalog, artifact


def test_sir_contract_is_sha_locked_and_load_probed():
    readiness = RuntimeModelManifest().inspect_sir(
        "escherichia_coli", "meropenem", probe=True
    )

    assert readiness.declared is True
    assert readiness.ready is True
    assert readiness.validated is False  # 当前没有闭合的 CC/E5 科学验证，不可借 readiness 升级
    assert readiness.reason_code == "ready"
    assert readiness.expected_sha256
    assert readiness.artifact_path.endswith("genotype_to_sir__meropenem.joblib")


def test_get_runtime_manifest_reloads_when_catalog_bytes_change(tmp_path, monkeypatch):
    """A long-lived worker must not pin a catalog merely by its pathname."""
    catalog = tmp_path / "catalog.yaml"
    catalog.write_bytes(runtime_manifest_module.DEFAULT_CATALOG.read_bytes())
    monkeypatch.setattr(runtime_manifest_module, "DEFAULT_CATALOG", catalog)
    get_runtime_manifest.cache_clear()
    try:
        first = get_runtime_manifest()
        catalog.write_bytes(catalog.read_bytes() + b"\n# request-context-rotation\n")
        second = get_runtime_manifest()
    finally:
        get_runtime_manifest.cache_clear()

    assert first is not second
    assert first.catalog_digest != second.catalog_digest


def test_request_context_detects_artifact_drift_and_rechecks_before_load(tmp_path):
    """Preflight receipts change on byte drift and block an in-flight stale load."""
    catalog, artifact = _temporary_ready_sir_catalog(tmp_path)
    context = capture_runtime_model_execution_context(
        species="escherichia_coli",
        drug="meropenem",
        output_kinds=["sir_class"],
        catalog_path=catalog,
        repo_root=tmp_path,
    )
    status = context.requested_capabilities[0]
    assert status.ready is True
    before_identity = dict(context.public_identity)
    before_stat = artifact.stat()

    # Preserve the old size/mtime explicitly.  ctime must still change, so the
    # strong file-identity cache cannot reuse the digest for the old bytes.
    artifact.write_bytes(b"x" * before_stat.st_size)
    os.utime(artifact, ns=(before_stat.st_atime_ns, before_stat.st_mtime_ns))
    after_stat = artifact.stat()
    assert after_stat.st_dev == before_stat.st_dev
    assert after_stat.st_ino == before_stat.st_ino
    assert after_stat.st_size == before_stat.st_size
    assert after_stat.st_mtime_ns == before_stat.st_mtime_ns
    assert after_stat.st_ctime_ns != before_stat.st_ctime_ns
    assert runtime_manifest_module._sha256_with_stat(
        str(artifact),
        after_stat.st_dev,
        after_stat.st_ino,
        after_stat.st_size,
        after_stat.st_mtime_ns,
        after_stat.st_ctime_ns,
    ) == sha256_file(artifact)

    changed = capture_runtime_model_execution_context(
        species="escherichia_coli",
        drug="meropenem",
        output_kinds=["sir_class"],
        catalog_path=catalog,
        repo_root=tmp_path,
    )
    assert changed.public_identity["requested_readiness_digest"] != (
        before_identity["requested_readiness_digest"]
    )
    assert changed.requested_capabilities[0].reason_code == "artifact_sha256_mismatch"
    with pytest.raises(ValueError, match="request_artifact_integrity_drift"):
        context.assert_current()
    with pytest.raises(ValueError, match="request_artifact_integrity_drift"):
        context.load_ready_model("sir/escherichia_coli/meropenem")

    public_identity = json.dumps(before_identity, sort_keys=True)
    for secret_or_raw_field in ("amr_profile", "blaKPC", "smiles", "sequence"):
        assert secret_or_raw_field not in public_identity


def test_request_context_assert_current_rejects_catalog_byte_rotation(tmp_path):
    """A cache hit may not outlive the exact catalog bytes it was keyed under."""
    catalog, _artifact = _temporary_ready_sir_catalog(tmp_path)
    context = capture_runtime_model_execution_context(
        species="escherichia_coli",
        drug="meropenem",
        output_kinds=["sir_class"],
        catalog_path=catalog,
        repo_root=tmp_path,
    )

    catalog.write_bytes(catalog.read_bytes() + b"\n# rotated-after-preflight\n")

    with pytest.raises(ValueError, match="request_artifact_integrity_drift"):
        context.assert_current()


def test_activity_request_context_binds_sidecar_receipt_to_cache_and_drift_guard(monkeypatch):
    """An eligible experimental sidecar is part of request/cache integrity too.

    The iML1515 sidecar is not routeable, so it does not belong in the normal
    readiness list.  It can nevertheless execute from an ``sm_activity`` request;
    its catalog-bound contract must therefore change the preflight receipt and be
    rechecked before a cache hit is replayed.
    """
    context = capture_runtime_model_execution_context(
        species="escherichia_coli",
        drug="trimethoprim",
        output_kinds=["sm_activity"],
    )
    assert [contract.model_id for contract in context.experimental_sidecars] == [
        "mechanism/escherichia_coli/iml1515"
    ]
    before_identity = dict(context.public_identity)
    original = RuntimeModelManifest.inspect_experimental_sidecar

    def _rotated_sidecar_receipt(self, model_id, *, loader_path=None):
        contract = original(self, model_id, loader_path=loader_path)
        return replace(contract, reason_code=f"{contract.reason_code}:rotated")

    monkeypatch.setattr(
        RuntimeModelManifest,
        "inspect_experimental_sidecar",
        _rotated_sidecar_receipt,
    )
    changed = capture_runtime_model_execution_context(
        species="escherichia_coli",
        drug="trimethoprim",
        output_kinds=["sm_activity"],
    )

    assert changed.public_identity["requested_readiness_digest"] != (
        before_identity["requested_readiness_digest"]
    )
    with pytest.raises(ValueError, match="request_artifact_integrity_drift"):
        context.assert_current()


def test_all_catalog_prediction_artifacts_are_ready_under_the_project_runtime():
    """T2 production-path probe: every locally executable catalog entry passes."""
    manifest = RuntimeModelManifest()
    checked = [
        manifest.inspect(model_id, probe=True)
        for model_id, model in manifest.models.items()
        if model.get("execution") == "predict"
    ]

    assert len(checked) == 129  # 127 SIR + small-molecule + peptide
    assert all(status.declared and status.ready for status in checked)
    assert not any(status.validated for status in checked)


def test_tracked_runtime_catalog_is_reproducible_from_its_sources(tmp_path):
    generated = tmp_path / "registry_mdr_gnb.yaml"
    build_catalog(output=generated)
    tracked = Path(__file__).resolve().parents[3] / "praxis_virtualcell" / "model_zoo" / "registry_mdr_gnb.yaml"
    assert generated.read_bytes() == tracked.read_bytes()


def test_catalog_pins_amrfinder_rules_source():
    manifest = RuntimeModelManifest()
    rules = (
        Path(__file__).resolve().parents[3]
        / "praxis_virtualcell" / "mdr_gnb" / "predictors"
        / "rules"
        / "amrfinder_sir_rules.yaml"
    )

    assert manifest.doc["generated_from"]["amrfinder_sir_rules"] == {
        "path": "praxis_virtualcell/mdr_gnb/predictors/rules/amrfinder_sir_rules.yaml",
        "sha256": sha256_file(rules),
    }


def test_sir_catalog_binds_each_model_to_an_exact_evidence_record():
    manifest = RuntimeModelManifest()
    model_id = "sir/escherichia_coli/meropenem"
    model = manifest.models[model_id]
    validation = model["validation"]
    evidence = manifest.sir_evidence_record(model_id)
    source = manifest.doc["generated_from"]["evidence_tiers"]

    assert validation["evidence_key"] == "escherichia_coli:meropenem"
    assert validation["evidence_source_path"] == source["path"]
    assert validation["evidence_source_sha256"] == source["sha256"]
    assert validation["evidence_record_sha256"] == evidence_record_sha256(evidence)
    assert validation["evidence_tier"] == evidence["tier"]
    assert validation["evidence_level"] == evidence["evidence_level"]
    assert validation["artifact_sha256"] == model["asset"]["sha256"]


@pytest.mark.parametrize(
    ("field", "value", "reason_code"),
    [
        ("evidence_key", "escherichia_coli:not_a_real_drug", "sir_evidence_key_mismatch"),
        ("evidence_source_path", "wrong_evidence_tiers.yaml", "sir_evidence_source_path_mismatch"),
        ("evidence_source_sha256", "0" * 64, "sir_evidence_source_sha256_mismatch"),
        ("evidence_tier", "E5", "sir_evidence_tier_mismatch"),
        ("evidence_level", "E5", "sir_evidence_level_mismatch"),
        ("evidence_record_sha256", "0" * 64, "sir_evidence_record_sha256_mismatch"),
        ("artifact_sha256", "0" * 64, "sir_evidence_artifact_sha256_mismatch"),
    ],
)
def test_sir_evidence_metadata_drift_is_never_routeable(
    tmp_path: Path,
    field: str,
    value: str,
    reason_code: str,
):
    catalog, _artifact = _temporary_ready_sir_catalog(tmp_path)
    document = yaml.safe_load(catalog.read_text(encoding="utf-8"))
    model_id = "sir/escherichia_coli/meropenem"
    document["models"][model_id]["validation"][field] = value
    catalog.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    manifest = RuntimeModelManifest(catalog, repo_root=tmp_path)
    readiness = manifest.inspect_sir("escherichia_coli", "meropenem", probe=False)

    assert readiness.declared is True
    assert readiness.ready is False
    assert readiness.reason_code == reason_code
    assert manifest.inspect(model_id, probe=False).reason_code == reason_code
    with pytest.raises(ValueError, match=reason_code):
        manifest.load_ready_model(model_id)


@pytest.mark.parametrize(
    ("source_name", "reason_code"),
    [
        ("sir_batch_manifest", "sir_source_manifest_sha256_mismatch"),
        ("evidence_tiers", "sir_evidence_tiers_sha256_mismatch"),
        ("amrfinder_sir_rules", "sir_amrfinder_rules_sha256_mismatch"),
    ],
)
def test_missing_required_sir_source_contract_is_never_routeable(
    tmp_path: Path,
    source_name: str,
    reason_code: str,
):
    catalog, _artifact = _temporary_ready_sir_catalog(tmp_path)
    document = yaml.safe_load(catalog.read_text(encoding="utf-8"))
    del document["generated_from"][source_name]
    catalog.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    readiness = RuntimeModelManifest(catalog, repo_root=tmp_path).inspect_sir(
        "escherichia_coli",
        "meropenem",
        probe=False,
    )

    assert readiness.ready is False
    assert readiness.reason_code == reason_code


@pytest.mark.parametrize(
    ("source_name", "reason_code"),
    [
        ("sir_batch_manifest", "sir_source_manifest_sha256_mismatch"),
        ("evidence_tiers", "sir_evidence_tiers_sha256_mismatch"),
        ("amrfinder_sir_rules", "sir_amrfinder_rules_sha256_mismatch"),
    ],
)
def test_physically_missing_required_sir_source_is_never_routeable(
    tmp_path: Path,
    source_name: str,
    reason_code: str,
):
    catalog, _artifact = _temporary_ready_sir_catalog(tmp_path)
    document = yaml.safe_load(catalog.read_text(encoding="utf-8"))
    source_path = tmp_path / document["generated_from"][source_name]["path"]
    source_path.unlink()

    readiness = RuntimeModelManifest(catalog, repo_root=tmp_path).inspect_sir(
        "escherichia_coli",
        "meropenem",
        probe=False,
    )

    assert readiness.ready is False
    assert readiness.reason_code == reason_code


@pytest.mark.parametrize(
    ("source_name", "reason_code"),
    [
        ("sir_batch_manifest", "sir_source_manifest_sha256_mismatch"),
        ("evidence_tiers", "sir_evidence_tiers_sha256_mismatch"),
        ("amrfinder_sir_rules", "sir_amrfinder_rules_sha256_mismatch"),
    ],
)
def test_sir_source_path_escape_is_a_machine_readable_denial(
    tmp_path: Path,
    source_name: str,
    reason_code: str,
):
    catalog, _artifact = _temporary_ready_sir_catalog(tmp_path)
    document = yaml.safe_load(catalog.read_text(encoding="utf-8"))
    document["generated_from"][source_name]["path"] = "../../outside.yaml"
    catalog.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    readiness = RuntimeModelManifest(catalog, repo_root=tmp_path).inspect_sir(
        "escherichia_coli",
        "meropenem",
        probe=False,
    )

    assert readiness.ready is False
    assert readiness.reason_code == reason_code


def test_dependency_version_mismatch_is_never_routeable(monkeypatch):
    manifest = RuntimeModelManifest()
    original_version = runtime_manifest_module.importlib.metadata.version

    def _wrong_sklearn_version(distribution: str) -> str:
        if distribution == "scikit-learn":
            return "1.8.0"
        return original_version(distribution)

    monkeypatch.setattr(
        runtime_manifest_module.importlib.metadata,
        "version",
        _wrong_sklearn_version,
    )
    readiness = manifest.inspect_sir("escherichia_coli", "meropenem", probe=True)
    assert readiness.ready is False
    assert readiness.reason_code == "dependency_version_mismatch:scikit-learn"


def test_numpy_major_three_is_rejected_before_artifact_deserialization(monkeypatch):
    """Unsupported NumPy majors must not attempt to unpickle model artifacts."""
    manifest = RuntimeModelManifest()
    original_version = runtime_manifest_module.importlib.metadata.version

    def _numpy_three(distribution: str) -> str:
        if distribution == "numpy":
            return "3.0.0"
        return original_version(distribution)

    def _adapter_must_not_load(*_args, **_kwargs):
        raise AssertionError("NumPy 3 must be rejected before adapter deserialization")

    monkeypatch.setattr(
        runtime_manifest_module.importlib.metadata,
        "version",
        _numpy_three,
    )
    monkeypatch.setattr(runtime_manifest_module, "_load_adapter", _adapter_must_not_load)

    readiness = manifest.inspect_sir("escherichia_coli", "meropenem", probe=True)

    assert readiness.ready is False
    assert readiness.reason_code == "dependency_version_mismatch:numpy"


def test_numpy_major_two_remains_eligible_for_the_existing_artifact_probe(monkeypatch):
    """The guard is a major-version fence, not an unreviewed exact NumPy pin."""
    manifest = RuntimeModelManifest()
    original_version = runtime_manifest_module.importlib.metadata.version

    def _numpy_two(distribution: str) -> str:
        if distribution == "numpy":
            return "2.99.0"
        return original_version(distribution)

    monkeypatch.setattr(
        runtime_manifest_module.importlib.metadata,
        "version",
        _numpy_two,
    )
    readiness = manifest.inspect_sir("escherichia_coli", "meropenem", probe=True)

    assert readiness.ready is True
    assert readiness.reason_code == "ready"


def test_unknown_sir_contract_is_not_declared_and_fails_closed():
    readiness = RuntimeModelManifest().inspect_sir(
        "escherichia_coli", "totally_fake_drug_zzz", probe=True
    )

    assert readiness.declared is False
    assert readiness.ready is False
    assert readiness.reason_code == "sir_model_not_declared"


def test_pinned_source_manifest_digest_is_enforced(tmp_path):
    batch = tmp_path / "batch.yaml"
    batch.write_text("models: {}\n", encoding="utf-8")
    runtime = tmp_path / "runtime.yaml"
    runtime.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "generated_from": {
                    "sir_batch_manifest": {
                        "path": "batch.yaml",
                        "sha256": "0" * 64,
                    }
                },
                "models": {
                    "sir/escherichia_coli/meropenem": {
                        "id": "sir/escherichia_coli/meropenem",
                        "execution": "predict",
                        "capability": {"output_kind": "sir_class"},
                        "runtime": {
                            "adapter": "genotype_to_sir",
                            "dependency_versions": {"scikit-learn": "1.9.0"},
                        },
                        "asset": {"path": "missing.joblib", "sha256": "1" * 64},
                        "validation": {"status": "limited"},
                        "lifecycle": {"declared": True},
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    manifest = RuntimeModelManifest(runtime, repo_root=tmp_path)
    readiness = manifest.inspect_sir(
        "escherichia_coli", "meropenem"
    )
    assert readiness.declared is True
    assert readiness.ready is False
    assert readiness.reason_code == "sir_source_manifest_sha256_mismatch"
    with pytest.raises(ValueError, match="sir_source_manifest_sha256_mismatch"):
        manifest.load_ready_model("sir/escherichia_coli/meropenem")


def test_pinned_evidence_tier_digest_is_enforced(monkeypatch):
    manifest = RuntimeModelManifest()
    original = manifest._source_is_current

    def _stale_evidence_only(source_name: str) -> bool:
        return source_name != "evidence_tiers" and original(source_name)

    monkeypatch.setattr(manifest, "_source_is_current", _stale_evidence_only)
    readiness = manifest.inspect_sir("escherichia_coli", "meropenem", probe=True)

    assert readiness.declared is True
    assert readiness.ready is False
    assert readiness.reason_code == "sir_evidence_tiers_sha256_mismatch"


def test_pinned_amrfinder_rule_digest_is_enforced(monkeypatch):
    manifest = RuntimeModelManifest()
    original = manifest._source_is_current

    def _stale_rules_only(source_name: str) -> bool:
        return source_name != "amrfinder_sir_rules" and original(source_name)

    monkeypatch.setattr(manifest, "_source_is_current", _stale_rules_only)
    readiness = manifest.inspect_sir("escherichia_coli", "meropenem", probe=True)

    assert readiness.declared is True
    assert readiness.ready is False
    assert readiness.reason_code == "sir_amrfinder_rules_sha256_mismatch"
    with pytest.raises(ValueError, match="sir_amrfinder_rules_sha256_mismatch"):
        manifest.load_ready_model("sir/escherichia_coli/meropenem")


def test_router_filters_a_declared_but_unready_spec():
    registry = PredictorRegistry()
    registry.register(
        PredictorSpec(
            name="declared_but_unready",
            version="test",
            species=["escherichia_coli"],
            drug_class=["carbapenems"],
            output_kind="sir_class",
            artifact_path="test://missing.joblib",
            readiness=lambda _ctx: (False, "artifact_missing"),
        )
    )

    route = route_mdr(_sir_request(), registry)
    assert route.disposition == "abstain"
    assert route.reason == "no_ready_capability"
    assert route.candidates == []
    assert route.unready_candidates == [
        {"name": "declared_but_unready", "reason_code": "artifact_missing"}
    ]


def test_default_router_uses_exact_ready_sir_contract_not_wildcard_declaration():
    registry = build_default_registry()

    ready = route_mdr(_sir_request(), registry)
    assert ready.disposition == "accept"
    assert any(spec.name == "genotype_to_sir" for spec in ready.candidates)

    unavailable = route_mdr(_sir_request("totally_fake_drug_zzz"), registry)
    assert unavailable.disposition == "abstain"
    assert unavailable.reason == "no_ready_capability"
    assert any(item["reason_code"] == "sir_model_not_declared"
               for item in unavailable.unready_candidates)


def test_default_router_fails_closed_on_stale_amrfinder_rules(monkeypatch):
    manifest = get_runtime_manifest()
    original = manifest._source_is_current

    def _stale_rules_only(source_name: str) -> bool:
        return source_name != "amrfinder_sir_rules" and original(source_name)

    monkeypatch.setattr(manifest, "_source_is_current", _stale_rules_only)
    route = route_mdr(_sir_request(), build_default_registry())

    assert route.disposition == "abstain"
    assert route.reason == "no_ready_capability"
    assert {
        "name": "genotype_to_sir",
        "reason_code": "sir_amrfinder_rules_sha256_mismatch",
    } in route.unready_candidates


def test_report_exposes_exact_catalog_state_when_no_declared_sir_exists():
    result = run_mdr_query(
        {
            "species": "escherichia_coli",
            "drug_panel": [{"drug": "totally_fake_drug_zzz", "drug_class": "carbapenems"}],
            "requested_outputs": ["SIR"],
            "amr_profile": {"blaKPC-2": True},
        },
        seed_task_id="catalog-fake-sir",
    )

    report = result["report"]
    capability = report["provenance"]["capability"]
    assert result["route"]["reason"] == "no_ready_capability"
    assert report["abstained"] is True
    assert {"no_ready_capability", "sir_model_not_declared"} <= set(
        report["abstain_reasons"]
    )
    assert capability["catalog_digest"]
    assert capability["catalog_reason_code"] == "catalog_loaded"
    assert capability["requested"] == [
        {
            "model_id": "sir/escherichia_coli/totally_fake_drug_zzz",
            "declared": False,
            "ready": False,
            "validated": False,
            "validation_status": "unverified",
            "reason_code": "sir_model_not_declared",
            "execution": None,
            "artifact_path": None,
            "expected_sha256": None,
            "catalog_digest": capability["catalog_digest"],
        }
    ]
