"""P8 product closure: Pack surfaces, fail-closed execution, and job identity."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml

from praxis_virtualcell.io.job_store import JobStore
from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper
from praxis_virtualcell.pack_product import (
    PackIndex,
    builtin_pack_roots,
    compatibility_payload,
    inspect_pack,
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


def _write_model_stack(tmp_path: Path, *, empty: bool = False) -> tuple[Path, Path]:
    registry_path = tmp_path / ("empty-models.yaml" if empty else "models.yaml")
    models = {} if empty else {_MODEL_NAME: _model_card()}
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
    assert payload["execution_plan"]["executable"] is True
    assert payload["execution_plan"]["steps"][0]["model_name"] == _MODEL_NAME
    rendered = json.dumps(payload, sort_keys=True)
    assert str(tmp_path) not in rendered
    assert "asset_paths" not in rendered


def test_model_present_executes_and_job_identity_locks_fingerprints(tmp_path):
    result = _run(tmp_path)
    report = result["structured_report"]
    assert report["abstain"] is False
    assert report["prediction"] == {"delta": [0.5]}
    assert report["models_used"] == [_MODEL_NAME]

    store = JobStore(str(tmp_path / "runs"))
    store.save("locked-job", request=_legacy_request(), result=result)
    loaded = store.load("locked-job")
    identity = loaded["execution_identity"]
    assert identity["schema_version"] == "vc.job-execution-identity.v1"
    assert identity["pack"]["pack_id"] == _human_identity()[0]
    assert len(identity["pack"]["fingerprint"]) == 64
    assert identity["models"][0]["name"] == _MODEL_NAME
    assert len(identity["models"][0]["fingerprint"]) == 64
    assert len(identity["fingerprint"]) == 64

    with pytest.raises(FileExistsError, match="already exists"):
        store.save("locked-job", request={"changed": True}, result=result)
    assert store.load("locked-job")["execution_identity"] == identity


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
    assert payloads[4]["execution_plan"]["executable"] is True
    assert payloads[5]["reliability_decision"]["abstain"] is False
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
    assert compatibility.json()["execution_plan"]["executable"] is True
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
    assert provenance["execution_identity"]["pack"]["pack_id"] == pack_id
    assert provenance["execution_identity"]["models"][0]["name"] == _MODEL_NAME


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
