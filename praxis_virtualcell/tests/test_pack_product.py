"""P8 product closure: Pack surfaces, fail-closed execution, and job identity."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml

from praxis_virtualcell.core.config import RuntimeConfig
from praxis_virtualcell.io.job_store import JobStore
from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper
from praxis_virtualcell.pack_product import (
    PackIndex,
    PackUnavailable,
    builtin_pack_roots,
    compatibility_payload,
    inspect_pack,
    pack_catalog_payload,
    run_pack_query,
    validate_pack_summary,
)

_MODEL_NAME = "p8_product_dummy"
_MODEL_BYTES = b"p8-product-dummy-model\n"
_MODEL_SHA = hashlib.sha256(_MODEL_BYTES).hexdigest()


class ProductDummyPredictor(ModelWrapper):
    """Test-only executable model for the public Pack surface."""

    name = "unbound_p8_product_dummy"

    def declare_scope(self) -> dict:
        return {
            "species": ["human"],
            "module": "genetic_hub",
            "task": ["predict_delta_expression"],
            "perturbation": ["gene"],
        }

    def run_prediction(self, model_input: dict) -> dict:
        assert self.capability_assets["model.bin"].endswith("model.bin")
        return {
            "prediction": {"delta": [0.5]},
            "uncertainty": {"method": "deterministic_fixture"},
            "evidence": ["p8_product_test_only"],
        }


def _legacy_request(**changes) -> dict:
    request = {
        "request_id": "p8-product-request",
        "species": "human",
        "cell_type": "K562",
        "perturbation_type": "gene",
        "perturbation_targets": ["AHR"],
        "input_modality": "scRNA",
        "output_modality": "delta_expression",
        "task_type": "predict_delta_expression",
    }
    request.update(changes)
    return request


def _model_card() -> dict:
    return {
        "schema_version": "vc.model-card.v1",
        "name": _MODEL_NAME,
        "type": "public_model",
        "species": ["human"],
        "taxon": ["NCBITaxon:9606"],
        "module": "genetic_hub",
        "modality": [{"name": "scRNA", "ontology_id": "EFO:0008913"}],
        "assay": ["EFO:0008913"],
        "cell_domain": {
            "cell_type_ids": [],
            "cell_type_names": ["K562"],
            "tissue_ids": [],
            "tissue_names": [],
            "allow_unspecified": False,
        },
        "perturbation": ["gene"],
        "task": "predict_delta_expression",
        "output": ["delta_expression"],
        "feature_namespace": [
            {
                "name": "EnsemblGene",
                "version": "GRCh38",
                "id_format": "ensembl_gene",
            }
        ],
        "representation": ["matrix:X"],
        "source": "cache:p8-product-test-only",
        "license": "CC0-1.0",
        "status": "available",
        "wrapper": (
            "praxis_virtualcell.tests.test_pack_product.ProductDummyPredictor"
        ),
        "version": "dummy-v1",
        "requires": [],
        "assets": [
            {
                "filename": "model.bin",
                "sha256": _MODEL_SHA,
                "media_type": "application/octet-stream",
                "source_note": "generated in pytest tmp_path",
            }
        ],
        "resources": {"python_dependencies": [], "required": ["cpu"]},
        "uncertainty": {
            "required": True,
            "methods": ["deterministic_fixture"],
            "calibrated": False,
        },
        "ood": {
            "action": "abstain",
            "dimensions": [
                "taxon",
                "modality",
                "assay",
                "cell_domain",
                "perturbation",
                "task",
                "output",
                "feature_namespace",
                "representation",
            ],
        },
        "reliability_policy": "p8_product_test_only",
        "provenance": {
            "training_data": "none; deterministic test fixture",
            "distributable": True,
        },
    }


def _write_model_stack(
    tmp_path: Path,
    *,
    empty: bool = False,
    model_version: str | None = None,
) -> tuple[Path, Path]:
    registry_path = tmp_path / ("empty-models.yaml" if empty else "models.yaml")
    card = _model_card()
    if model_version is not None:
        card["version"] = model_version
    models = {} if empty else {_MODEL_NAME: card}
    registry_path.write_text(
        yaml.safe_dump({"models": models}, sort_keys=False),
        encoding="utf-8",
    )
    cache_root = tmp_path / ("empty-cache" if empty else "model-cache")
    if not empty:
        asset = cache_root / _MODEL_NAME / "model.bin"
        asset.parent.mkdir(parents=True)
        asset.write_bytes(_MODEL_BYTES)
    return registry_path, cache_root


def _product_index(tmp_path: Path) -> PackIndex:
    return PackIndex(index_path=tmp_path / "pack-index.json")


def _human_identity() -> tuple[str, str]:
    return "p8-human-tiny", "1.0.0"


def _run(
    tmp_path: Path,
    request: dict | None = None,
    *,
    empty_models: bool = False,
) -> dict:
    registry_path, cache_root = _write_model_stack(
        tmp_path,
        empty=empty_models,
    )
    pack_id, pack_version = _human_identity()
    return run_pack_query(
        request or _legacy_request(),
        pack_id=pack_id,
        pack_version=pack_version,
        index=_product_index(tmp_path),
        model_registry_path=registry_path,
        model_cache_root=cache_root,
    )


def test_builtin_human_mouse_bacteria_packs_are_real_and_auditable(tmp_path):
    roots = builtin_pack_roots()
    assert set(roots) == {"human", "mouse", "bacteria"}
    assert all((root / "manifest.yaml").is_file() for root in roots.values())
    assert all((root / "tiny.h5ad").is_file() for root in roots.values())

    records = _product_index(tmp_path).list_records()
    assert [record["pack_id"] for record in records] == [
        "p8-bacteria-tiny",
        "p8-human-tiny",
        "p8-mouse-tiny",
    ]
    assert all(record["pack_valid"] is True for record in records)
    assert all(record["scientifically_validated"] is False for record in records)
    assert {record["manifest_schema_version"] for record in records} == {
        "vc.pack.v0.2"
    }
    assert {
        namespace["name"]
        for record in records
        for namespace in record["feature_namespaces"]
    } == {"EnsemblGene", "NCBIGene"}


def test_inspect_is_explicitly_unchecked_while_validate_reads_assets():
    root = builtin_pack_roots()["human"]
    inspected = inspect_pack(root)
    validated = validate_pack_summary(root)

    assert inspected["validation_status"] == "unchecked"
    assert inspected["pack_valid"] is None
    assert validated["validation_status"] == "valid"
    assert validated["pack_valid"] is True
    assert validated["pack_fingerprint"] == inspected["pack_fingerprint"]


def test_register_is_durable_idempotent_and_revalidates_assets(tmp_path):
    external = tmp_path / "external"
    shutil.copytree(builtin_pack_roots()["human"], external)
    manifest_path = external / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["pack_id"] = "p8-external-human"
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )
    index_path = tmp_path / "index" / "packs.json"

    first = PackIndex(index_path=index_path)
    registered = first.register(external)
    assert registered["pack_valid"] is True
    assert first.register(external) == registered

    second = PackIndex(index_path=index_path)
    assert second.get_record("p8-external-human", "1.0.0") == registered

    with (external / "tiny.h5ad").open("ab") as stream:
        stream.write(b"tampered")
    invalid = second.get_record("p8-external-human", "1.0.0")
    assert invalid["pack_valid"] is False
    assert invalid["validation_status"] == "invalid"
    assert any("size mismatch" in reason for reason in invalid["reasons"])


def test_invalid_registered_pack_record_redacts_server_root(tmp_path):
    external = tmp_path / "private-pack-root"
    shutil.copytree(builtin_pack_roots()["human"], external)
    manifest_path = external / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["pack_id"] = "p8-private-path-test"
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )
    index = PackIndex(index_path=tmp_path / "pack-index.json")
    index.register(external)
    manifest_path.unlink()

    record = index.get_record("p8-private-path-test", "1.0.0")
    assert record["pack_valid"] is False
    assert str(tmp_path) not in json.dumps(record)


def test_compatibility_payload_has_no_server_paths(tmp_path):
    registry_path, cache_root = _write_model_stack(tmp_path)
    pack_id, pack_version = _human_identity()
    payload = compatibility_payload(
        _legacy_request(),
        pack_id=pack_id,
        pack_version=pack_version,
        index=_product_index(tmp_path),
        model_registry_path=registry_path,
        model_cache_root=cache_root,
    )

    assert payload["schema_version"] == "vc.pack-compatibility-surface.v1"
    assert payload["pack"]["pack_valid"] is True
    assert payload["execution_plan"]["schema_version"] == "vc.execution-plan.v2"
    assert payload["execution_plan"]["executable"] is False
    assert payload["execution_plan"]["steps"] == []
    migrated = payload["execution_plan"]["reports"][0]
    assert migrated["model_name"] == _MODEL_NAME
    assert migrated["scientifically_validated"] is None
    assert migrated["policy_present"] is False
    assert migrated["production_promoted"] is False
    assert "registry.release_incomplete" in migrated["reasons"]
    assert "evidence.missing" in migrated["reasons"]
    assert "policy.missing" in migrated["reasons"]
    rendered = json.dumps(payload, sort_keys=True)
    assert str(tmp_path) not in rendered
    assert "asset_paths" not in rendered


def test_missing_model_registry_path_is_redacted_from_catalog_error():
    secret_path = "/Volumes/T7/PRIVATE-P12-REGISTRY-MISSING.yaml"

    with pytest.raises(ValueError, match="model_zoo registry is unavailable") as error:
        pack_catalog_payload(model_registry_path=secret_path)

    assert secret_path not in str(error.value)


def test_catalog_uses_one_model_registry_snapshot(tmp_path, monkeypatch):
    import praxis_virtualcell.pack_product as product

    original = product.ModelZooRegistry
    calls = 0

    def tracked_registry(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(product, "ModelZooRegistry", tracked_registry)
    payload = product.pack_catalog_payload(index=_product_index(tmp_path))

    assert calls == 1
    releases = payload["model_registry"]["releases"]
    assert payload["model_capabilities"][0]["registry_releases"] == [
        release
        for release in releases
        if release["model_name"] == payload["model_capabilities"][0]["name"]
    ]


def test_pack_query_rejects_llm_before_model_runtime(monkeypatch):
    def unexpected_runtime(*args, **kwargs):
        pytest.fail("Pack-aware LLM request reached model/runtime setup")

    monkeypatch.setattr(
        "praxis_virtualcell.pack_product._model_stack",
        unexpected_runtime,
    )
    monkeypatch.setattr(
        "praxis_virtualcell.pack_product.run_query",
        unexpected_runtime,
    )

    with pytest.raises(PackUnavailable, match="pack-aware LLM reporting is unavailable"):
        run_pack_query(
            _legacy_request(),
            pack_id="not-read",
            pack_version="not-read",
            config=RuntimeConfig(llm_enabled=True),
        )


def test_legacy_model_migration_abstains_and_job_identity_locks_fingerprints(tmp_path):
    result = _run(tmp_path)
    report = result["structured_report"]
    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["models_used"] == []
    assert report["provenance"]["execution_plan"]["schema_version"] == (
        "vc.execution-plan.v2"
    )

    store = JobStore(str(tmp_path / "runs"))
    store.save("locked-job", request=_legacy_request(), result=result)
    loaded = store.load("locked-job")
    identity = loaded["execution_identity"]
    assert identity["schema_version"] == "vc.job-execution-identity.v2"
    assert identity["pack"]["pack_id"] == _human_identity()[0]
    assert len(identity["pack"]["fingerprint"]) == 64
    assert identity["models"][0]["name"] == _MODEL_NAME
    assert len(identity["models"][0]["fingerprint"]) == 64
    assert len(identity["models"][0]["release_fingerprint"]) == 64
    assert identity["models"][0]["evidence_fingerprints"] == []
    assert identity["models"][0]["policy_fingerprint"] is None
    assert identity["models"][0]["scientifically_validated"] is None
    assert identity["models"][0]["policy_present"] is False
    assert identity["models"][0]["production_promoted"] is False
    assert identity["models"][0]["executable"] is False
    assert len(identity["fingerprint"]) == 64
    assert str(tmp_path) not in json.dumps(identity, sort_keys=True)

    with pytest.raises(FileExistsError, match="already exists"):
        store.save("locked-job", request={"changed": True}, result=result)
    assert store.load("locked-job")["execution_identity"] == identity

    mismatched = _legacy_request(request_id="different-request")
    with pytest.raises(ValueError, match="request does not match"):
        store.save("mismatched-job", request=mismatched, result=result)
    assert not (tmp_path / "runs" / "mismatched-job").exists()

    impossible_outcome = copy.deepcopy(result)
    impossible_outcome["structured_report"]["models_used"] = ["unplanned_model"]
    with pytest.raises(ValueError, match="outside the execution plan"):
        store.save(
            "impossible-outcome",
            request=_legacy_request(),
            result=impossible_outcome,
        )
    assert not (tmp_path / "runs" / "impossible-outcome").exists()


def test_unsafe_legacy_model_version_is_redacted_on_every_product_surface(tmp_path):
    secret_version = "/Volumes/T7/private/model-version"
    registry_path, cache_root = _write_model_stack(
        tmp_path,
        model_version=secret_version,
    )
    index = _product_index(tmp_path)
    pack_id, pack_version = _human_identity()

    catalog = pack_catalog_payload(index=index, model_registry_path=registry_path)
    compatibility = compatibility_payload(
        _legacy_request(),
        pack_id=pack_id,
        pack_version=pack_version,
        index=index,
        model_registry_path=registry_path,
        model_cache_root=cache_root,
    )
    result = run_pack_query(
        _legacy_request(),
        pack_id=pack_id,
        pack_version=pack_version,
        index=index,
        model_registry_path=registry_path,
        model_cache_root=cache_root,
    )
    store = JobStore(str(tmp_path / "runs"))
    store.save("redacted-version", request=_legacy_request(), result=result)
    loaded = store.load("redacted-version")

    assert catalog["model_capabilities"][0]["version"] is None
    assert catalog["model_registry"]["releases"][0]["model_version"] is None
    assert compatibility["execution_plan"]["reports"][0]["model_version"] is None
    assert loaded["execution_identity"]["models"][0]["version"] is None
    for public in (catalog, compatibility, result, loaded):
        assert secret_version not in json.dumps(public, sort_keys=True)


def test_runtime_request_binding_matches_gene_normalization(tmp_path):
    request = _legacy_request(perturbation_targets=[" ahr "])
    result = _run(tmp_path, request)
    store = JobStore(str(tmp_path / "runs"))

    store.save("normalized-gene", request=request, result=result)
    identity = store.load("normalized-gene")["execution_identity"]

    assert identity["schema_version"] == "vc.job-execution-identity.v2"
    assert len(identity["submitted_request_fingerprint"]) == 64
    assert len(identity["request_fingerprint"]) == 64
    assert identity["submitted_request_fingerprint"] != identity["request_fingerprint"]


def test_historical_job_load_projects_or_rejects_private_model_fields(tmp_path):
    secret = "/Volumes/T7/private/legacy-model.bin"
    job = tmp_path / "runs" / "legacy-job"
    job.mkdir(parents=True)
    (job / "status").write_text("done", encoding="utf-8")
    (job / "report.json").write_text(
        json.dumps(
            {
                "provenance": {
                    "execution_plan": {"asset_paths": {"model.bin": secret}}
                }
            }
        ),
        encoding="utf-8",
    )
    (job / "provenance.json").write_text(
        json.dumps(
            {"execution_plan": {"asset_paths": {"model.bin": secret}}}
        ),
        encoding="utf-8",
    )
    (job / "execution_identity.json").write_text(
        json.dumps({"models": [{"version": secret}]}),
        encoding="utf-8",
    )

    loaded = JobStore(str(tmp_path / "runs")).load("legacy-job")
    rendered = json.dumps(loaded, sort_keys=True)

    assert secret not in rendered
    assert "asset_paths" not in rendered
    assert loaded["provenance"]["execution_plan"]["available"] is False
    assert loaded["execution_identity"]["available"] is False


def test_historical_job_execution_identity_is_verified_before_projection(tmp_path):
    def signed(value: dict) -> dict:
        value = copy.deepcopy(value)
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        value["fingerprint"] = hashlib.sha256(encoded).hexdigest()
        return value

    def load(identity: dict, job_id: str) -> dict:
        job = tmp_path / "runs" / job_id
        job.mkdir(parents=True)
        (job / "status").write_text("done", encoding="utf-8")
        (job / "execution_identity.json").write_text(
            json.dumps(identity),
            encoding="utf-8",
        )
        return JobStore(str(tmp_path / "runs")).load(job_id)["execution_identity"]

    valid_v1 = signed(
        {
            "schema_version": "vc.job-execution-identity.v1",
            "legacy_adapter": False,
            "pack": {
                "pack_id": "historical-pack",
                "pack_version": "1.0.0",
                "fingerprint": "1" * 64,
            },
            "models": [
                {
                    "name": "historical_model",
                    "version": "1.0.0",
                    "fingerprint": "2" * 64,
                    "compatibility_fingerprint": "3" * 64,
                    "executable": False,
                }
            ],
        }
    )
    assert load(valid_v1, "valid-v1") == valid_v1

    valid_v2 = signed(
        {
            "schema_version": "vc.job-execution-identity.v2",
            "legacy_adapter": False,
            "plan_id": f"plan_{'4' * 24}",
            "submitted_request_fingerprint": "5" * 64,
            "request_fingerprint": "6" * 64,
            "pack": None,
            "environment_snapshot_fingerprint": "7" * 64,
            "execution_step_fingerprints": [],
            "structured_report_fingerprint": "8" * 64,
            "outcome": {
                "abstain": True,
                "models_used": [],
                "prediction_present": False,
            },
            "models": [],
        }
    )
    assert load(valid_v2, "valid-v2") == valid_v2

    tampered = copy.deepcopy(valid_v2)
    tampered["request_fingerprint"] = "9" * 64
    assert load(tampered, "tampered-signature")["available"] is False

    contradictory = copy.deepcopy(valid_v2)
    contradictory.pop("fingerprint")
    contradictory["outcome"] = {
        "abstain": False,
        "models_used": [],
        "prediction_present": True,
    }
    contradictory = signed(contradictory)
    assert load(contradictory, "contradictory-outcome")["available"] is False

    promoted_without_evidence = copy.deepcopy(valid_v2)
    promoted_without_evidence.pop("fingerprint")
    promoted_without_evidence["models"] = [
        {
            "name": "unvalidated_model",
            "version": "1.0.0",
            "fingerprint": "a" * 64,
            "release_fingerprint": "b" * 64,
            "capability_fingerprint": "c" * 64,
            "artifact_fingerprints": [],
            "environment_fingerprint": None,
            "adapter_fingerprints": [],
            "evidence_fingerprints": [],
            "policy_fingerprint": "d" * 64,
            "compatibility_fingerprint": "e" * 64,
            "cataloged": True,
            "artifact_ready": False,
            "revoked": False,
            "superseded_by": None,
            "benchmark_passed": None,
            "scientifically_validated": None,
            "promotion_eligible": None,
            "policy_present": True,
            "production_promoted": True,
            "executable": False,
        }
    ]
    promoted_without_evidence = signed(promoted_without_evidence)
    assert (
        load(promoted_without_evidence, "promoted-without-evidence")["available"]
        is False
    )


@pytest.mark.parametrize(
    ("query", "empty_models", "reason"),
    [
        (_legacy_request(), True, None),
        (_legacy_request(input_modality="protein"), False, "request.modality"),
        (_legacy_request(cell_type="HeLa"), False, "request.cell_domain"),
        (_legacy_request(species="mouse"), False, "request.taxon"),
    ],
)
def test_no_model_and_invalid_scope_honestly_abstain(
    tmp_path,
    query,
    empty_models,
    reason,
):
    result = _run(
        tmp_path,
        query,
        empty_models=empty_models,
    )
    report = result["structured_report"]
    plan = report["provenance"]["execution_plan"]

    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["models_used"] == []
    assert plan["steps"] == []
    if reason is None:
        assert plan["reports"] == []
    else:
        assert reason in plan["reports"][0]["reasons"]
    assert not any(name.startswith("Mock") for name in report["models_rejected"])


def test_pack_cli_exposes_all_six_commands(tmp_path, monkeypatch, capsys):
    from praxis_virtualcell import cli

    index_path = tmp_path / "pack-index.json"
    registry_path, cache_root = _write_model_stack(tmp_path)
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(_legacy_request()), encoding="utf-8")
    monkeypatch.setenv("PRAXIS_VC_PACK_INDEX", str(index_path))
    monkeypatch.setenv("PRAXIS_VC_MODEL_REGISTRY", str(registry_path))
    monkeypatch.setenv("PRAXIS_VC_MODEL_CACHE", str(cache_root))
    root = builtin_pack_roots()["human"]
    pack_id, pack_version = _human_identity()

    calls = [
        ["pack", "inspect", str(root)],
        ["pack", "validate", str(root)],
        ["pack", "register", str(root)],
        ["pack", "list"],
        [
            "pack",
            "compatibility",
            "--request",
            str(request_path),
            "--pack-id",
            pack_id,
            "--pack-version",
            pack_version,
        ],
        [
            "pack",
            "run",
            "--request",
            str(request_path),
            "--pack-id",
            pack_id,
            "--pack-version",
            pack_version,
            "--out",
            str(tmp_path / "runs" / "cli-job"),
        ],
    ]
    payloads = []
    for argv in calls:
        assert cli.main(argv) == 0
        payloads.append(json.loads(capsys.readouterr().out))

    assert payloads[0]["validation_status"] == "unchecked"
    assert payloads[1]["pack_valid"] is True
    assert payloads[2]["pack_id"] == pack_id
    assert len(payloads[3]["packs"]) == 3
    assert payloads[3]["model_registry"]["schema_version"] == (
        "vc.model-registry-catalog.v2"
    )
    assert payloads[3]["model_capabilities"][0]["registry_releases"]
    migrated = payloads[3]["model_registry"]["releases"][0]
    assert migrated["scientifically_validated"] is None
    assert migrated["production_promoted"] is False
    assert payloads[4]["execution_plan"]["executable"] is False
    assert payloads[5]["reliability_decision"]["abstain"] is True
    assert (
        tmp_path / "runs" / "cli-job" / "execution_identity.json"
    ).is_file()


@pytest.fixture()
def pack_api_client(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    registry_path, cache_root = _write_model_stack(tmp_path)
    monkeypatch.setenv("PRAXIS_VC_RUNS", str(tmp_path / "runs"))
    monkeypatch.setenv("PRAXIS_VC_PACK_INDEX", str(tmp_path / "pack-index.json"))
    monkeypatch.setenv("PRAXIS_VC_MODEL_REGISTRY", str(registry_path))
    monkeypatch.setenv("PRAXIS_VC_MODEL_CACHE", str(cache_root))
    monkeypatch.delenv("PRAXIS_VIRTUALCELL_MODE", raising=False)

    import importlib

    import praxis_vc_api.services.runtime_service as runtime_service

    importlib.reload(runtime_service)
    from praxis_vc_api.main import app

    return TestClient(app)


def test_pack_api_is_read_only_and_pack_jobs_preserve_identity(pack_api_client):
    client = pack_api_client
    pack_id, pack_version = _human_identity()

    listed = client.get("/api/packs")
    assert listed.status_code == 200
    assert listed.json()["schema_version"] == "vc.pack-catalog.v1"
    assert len(listed.json()["packs"]) == 3
    assert listed.json()["model_registry"]["schema_version"] == (
        "vc.model-registry-catalog.v2"
    )
    assert listed.json()["model_capabilities"][0]["registry_releases"]
    assert listed.json()["model_registry"]["releases"][0][
        "production_promoted"
    ] is False

    inspected = client.get(f"/api/packs/{pack_id}/{pack_version}")
    assert inspected.status_code == 200
    assert inspected.json()["pack_id"] == pack_id

    validated = client.get(f"/api/packs/{pack_id}/{pack_version}/validate")
    assert validated.status_code == 200
    assert validated.json()["pack_valid"] is True

    compatibility = client.post(
        "/api/packs/compatibility",
        json={
            "request": _legacy_request(),
            "pack_id": pack_id,
            "pack_version": pack_version,
        },
    )
    assert compatibility.status_code == 200
    assert compatibility.json()["execution_plan"]["executable"] is False
    assert "asset_paths" not in json.dumps(compatibility.json())

    assert client.post("/api/packs/register", json={}).status_code in {404, 405}

    job = client.post(
        "/api/jobs",
        json={
            "request": _legacy_request(),
            "mode": "offline",
            "pack_id": pack_id,
            "pack_version": pack_version,
        },
    )
    assert job.status_code == 200
    provenance = client.get(
        f"/api/reports/{job.json()['job_id']}/provenance"
    ).json()
    assert provenance["execution_identity"]["schema_version"] == (
        "vc.job-execution-identity.v2"
    )
    assert provenance["execution_identity"]["pack"]["pack_id"] == pack_id
    assert provenance["execution_identity"]["models"][0]["name"] == _MODEL_NAME
    assert provenance["execution_identity"]["models"][0][
        "production_promoted"
    ] is False


def test_pack_api_rejects_partial_pack_identity(pack_api_client):
    partial = pack_api_client.post(
        "/api/jobs",
        json={
            "request": _legacy_request(),
            "mode": "offline",
            "pack_id": _human_identity()[0],
        },
    )
    assert partial.status_code == 422

    misspelled = pack_api_client.post(
        "/api/jobs",
        json={
            "request": _legacy_request(),
            "mode": "offline",
            "packid": _human_identity()[0],
            "packversion": _human_identity()[1],
        },
    )
    assert misspelled.status_code == 422

    extra = pack_api_client.post(
        "/api/packs/compatibility",
        json={
            "request": _legacy_request(),
            "pack_id": _human_identity()[0],
            "pack_version": _human_identity()[1],
            "fallback": "legacy",
        },
    )
    assert extra.status_code == 422
