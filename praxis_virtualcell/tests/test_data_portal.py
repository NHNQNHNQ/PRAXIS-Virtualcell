"""P7 data portal: strict catalog, allowlisted downloads, quarantined uploads."""

from __future__ import annotations

import hashlib
import json

import pytest
import yaml

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from praxis_vc_api.main import app

_TOKEN = "p7-test-upload-token-is-at-least-32-bytes"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _catalog(file_bytes: bytes = b"a,b\n1,2\n") -> dict:
    return {
        "schema_version": "vc.data-catalog.v1",
        "datasets": [
            {
                "id": "tiny-human",
                "version": "1",
                "title": "Tiny human fixture",
                "species": {
                    "runtime_id": "human",
                    "taxon_id": "NCBITaxon:9606",
                    "scientific_name": "Homo sapiens",
                },
                "modality": "scRNA",
                "value_semantics": "raw_counts",
                "observations": 1,
                "features": 1,
                "source": {
                    "landing_page": "https://example.test/tiny-human",
                    "citation": "P7 test fixture",
                },
                "terms": {
                    "id": "CC0-1.0",
                    "name": "CC0 1.0 Universal",
                    "url": "https://creativecommons.org/publicdomain/zero/1.0/",
                },
                "usage_status": "download_only",
                "scientifically_validated": False,
                "files": [
                    {
                        "id": "counts",
                        "filename": "counts.csv",
                        "path": "human/tiny-human/counts.csv",
                        "media_type": "text/csv",
                        "size_bytes": len(file_bytes),
                        "sha256": _sha256(file_bytes),
                        "source_url": "https://example.test/tiny-human/counts.csv",
                    }
                ],
            },
            {
                "id": "tiny-mouse",
                "version": "1",
                "title": "Tiny mouse fixture",
                "species": {
                    "runtime_id": "mouse",
                    "taxon_id": "NCBITaxon:10090",
                    "scientific_name": "Mus musculus",
                },
                "modality": "scRNA",
                "value_semantics": "raw_counts",
                "observations": 2,
                "features": 1,
                "source": {
                    "landing_page": "https://example.test/tiny-mouse",
                    "citation": "P7 test fixture",
                },
                "terms": {
                    "id": "CC0-1.0",
                    "name": "CC0 1.0 Universal",
                    "url": "https://creativecommons.org/publicdomain/zero/1.0/",
                },
                "usage_status": "download_only",
                "scientifically_validated": False,
                "files": [
                    {
                        "id": "counts",
                        "filename": "mouse.csv",
                        "path": "mouse/tiny-mouse/mouse.csv",
                        "media_type": "text/csv",
                        "size_bytes": 5,
                        "sha256": _sha256(b"mouse"),
                        "source_url": "https://example.test/tiny-mouse/mouse.csv",
                    }
                ],
            },
        ],
    }


@pytest.fixture()
def portal(tmp_path, monkeypatch):
    root = tmp_path / "data-root"
    public = root / "public"
    human = public / "human" / "tiny-human"
    human.mkdir(parents=True)
    file_bytes = b"a,b\n1,2\n"
    (human / "counts.csv").write_bytes(file_bytes)
    catalog_path = tmp_path / "catalog.yaml"
    catalog_path.write_text(
        yaml.safe_dump(_catalog(file_bytes), sort_keys=False),
        encoding="utf-8",
    )
    monkeypatch.setenv("PRAXIS_VC_DATA_ROOT", str(root))
    monkeypatch.setenv("PRAXIS_VC_DATA_CATALOG", str(catalog_path))
    monkeypatch.setenv("PRAXIS_VC_UPLOAD_TOKEN", _TOKEN)
    monkeypatch.setenv("PRAXIS_VC_UPLOAD_MAX_BYTES", "16")
    monkeypatch.setenv("PRAXIS_VC_UPLOAD_TOTAL_BYTES", "24")
    return TestClient(app), root, catalog_path


def _upload(
    client: TestClient,
    content: bytes,
    *,
    filename: str = "cells.h5ad",
    species: str = "human",
    token: str = _TOKEN,
):
    return client.post(
        "/api/data-uploads",
        data={"species": species},
        files={"file": (filename, content, "application/octet-stream")},
        headers={"Authorization": f"Bearer {token}"},
    )


def test_catalog_lists_exact_species_and_hides_server_paths(portal):
    client, root, _catalog_path = portal

    response = client.get("/api/data-catalog")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "vc.data-catalog.v1"
    assert payload["species"] == [
        {
            "id": "human",
            "taxon_id": "NCBITaxon:9606",
            "scientific_name": "Homo sapiens",
        },
        {
            "id": "mouse",
            "taxon_id": "NCBITaxon:10090",
            "scientific_name": "Mus musculus",
        },
    ]
    assert [dataset["id"] for dataset in payload["datasets"]] == [
        "tiny-human",
        "tiny-mouse",
    ]
    assert payload["datasets"][0]["files"][0]["available"] is True
    assert payload["datasets"][1]["files"][0]["available"] is False
    assert payload["datasets"][0]["usage_status"] == "download_only"
    assert payload["datasets"][0]["scientifically_validated"] is False
    assert payload["upload"] == {
        "enabled": True,
        "quarantine_only": True,
        "max_file_bytes": 16,
        "total_quota_bytes": 24,
        "accepted_extensions": [
            ".csv",
            ".csv.gz",
            ".h5ad",
            ".h5mu",
            ".mtx",
            ".mtx.gz",
            ".tar.gz",
            ".tsv",
            ".tsv.gz",
            ".zip",
        ],
    }
    encoded = json.dumps(payload)
    assert str(root) not in encoded
    assert _TOKEN not in encoded
    assert "path" not in payload["datasets"][0]["files"][0]


def test_catalog_species_filter_is_exact_and_does_not_fallback(portal):
    client, _root, _catalog_path = portal

    response = client.get("/api/data-catalog", params={"species": "mouse"})
    bad = client.get("/api/data-catalog", params={"species": "Human"})

    assert response.status_code == 200
    assert [dataset["id"] for dataset in response.json()["datasets"]] == [
        "tiny-mouse"
    ]
    assert bad.status_code == 400
    assert bad.json()["detail"] == "unsupported_species"


def test_catalog_config_rejects_duplicate_ids_and_unsafe_paths(portal):
    client, _root, catalog_path = portal
    document = _catalog()
    document["datasets"][1]["id"] = "tiny-human"
    document["datasets"][0]["files"][0]["path"] = "../escape.csv"
    catalog_path.write_text(
        yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )

    response = client.get("/api/data-catalog")

    assert response.status_code == 503
    assert response.json()["detail"] == "data_catalog_invalid"
    assert "escape" not in response.text


def test_download_serves_only_allowlisted_hash_verified_file(portal):
    client, _root, _catalog_path = portal

    response = client.get("/api/data-catalog/tiny-human/files/counts/download")
    partial = client.get(
        "/api/data-catalog/tiny-human/files/counts/download",
        headers={"Range": "bytes=0-2"},
    )

    assert response.status_code == 200
    assert response.content == b"a,b\n1,2\n"
    assert response.headers["content-disposition"] == (
        'attachment; filename="counts.csv"'
    )
    assert response.headers["accept-ranges"] == "bytes"
    assert partial.status_code == 206
    assert partial.content == b"a,b"


def test_download_fails_closed_on_missing_tampered_and_unknown_files(portal):
    client, root, _catalog_path = portal
    target = root / "public" / "human" / "tiny-human" / "counts.csv"
    target.write_bytes(b"tampered")

    tampered = client.get(
        "/api/data-catalog/tiny-human/files/counts/download"
    )
    missing = client.get(
        "/api/data-catalog/tiny-mouse/files/counts/download"
    )
    unknown = client.get(
        "/api/data-catalog/tiny-human/files/unknown/download"
    )
    traversal = client.get(
        "/api/data-catalog/..%2Ftiny-human/files/counts/download"
    )

    assert tampered.status_code == 409
    assert tampered.json()["detail"] == "dataset_integrity_failed"
    assert missing.status_code == 404
    assert missing.json()["detail"] == "dataset_file_unavailable"
    assert unknown.status_code == 404
    assert unknown.json()["detail"] == "dataset_file_not_found"
    assert traversal.status_code in {404, 400}


def test_download_rejects_symlink_escaping_public_root(portal, tmp_path):
    client, root, _catalog_path = portal
    target = root / "public" / "human" / "tiny-human" / "counts.csv"
    target.unlink()
    outside = tmp_path / "outside.csv"
    outside.write_bytes(b"a,b\n1,2\n")
    target.symlink_to(outside)

    response = client.get(
        "/api/data-catalog/tiny-human/files/counts/download"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "dataset_integrity_failed"


def test_download_fails_closed_when_hash_cannot_be_read(portal, monkeypatch):
    _client, _root, _catalog_path = portal
    from praxis_vc_api.services import data_portal_service

    def unreadable(_path):
        raise OSError("simulated read failure")

    monkeypatch.setattr(data_portal_service, "_hash_file", unreadable)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/api/data-catalog/tiny-human/files/counts/download"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "dataset_integrity_failed"


def test_upload_requires_configured_bearer_before_writing_body(portal, monkeypatch):
    client, root, _catalog_path = portal

    wrong = _upload(client, b"content", token="wrong-token")
    monkeypatch.delenv("PRAXIS_VC_UPLOAD_TOKEN")
    disabled = _upload(client, b"content")

    assert wrong.status_code == 401
    assert wrong.json()["detail"] == "upload_unauthorized"
    assert disabled.status_code == 503
    assert disabled.json()["detail"] == "uploads_disabled"
    assert not (root / "uploads").exists()


def test_upload_rejects_declared_oversize_before_multipart_parsing(portal):
    client, root, _catalog_path = portal

    response = client.post(
        "/api/data-uploads",
        data={"species": "human"},
        files={"file": ("cells.h5ad", b"x", "application/octet-stream")},
        headers={
            "Authorization": f"Bearer {_TOKEN}",
            "Content-Length": str(1024 * 1024 + 17),
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "upload_too_large"
    assert not (root / "uploads").exists()


def test_upload_limits_chunked_body_before_multipart_spooling(portal):
    client, root, _catalog_path = portal
    boundary = "p7-boundary"
    prefix = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="species"\r\n\r\n'
        "human\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="cells.h5ad"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    suffix = f"\r\n--{boundary}--\r\n".encode()

    response = client.post(
        "/api/data-uploads",
        content=iter((prefix, b"x" * 1_049_000, suffix)),
        headers={
            "Authorization": f"Bearer {_TOKEN}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Transfer-Encoding": "chunked",
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "upload_too_large"
    assert not (root / "uploads").exists()


def test_upload_rejects_symlinked_storage_without_writing_outside(
    portal, tmp_path
):
    client, root, _catalog_path = portal
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "uploads").symlink_to(outside, target_is_directory=True)

    response = _upload(client, b"exact-content")

    assert response.status_code == 503
    assert response.json()["detail"] == "uploads_disabled"
    assert not any(outside.iterdir())


def test_upload_stores_exact_bytes_and_receipt_in_quarantine(portal):
    client, root, _catalog_path = portal

    response = _upload(client, b"exact-content")

    assert response.status_code == 201
    payload = response.json()
    assert payload["schema_version"] == "vc.upload-receipt.v1"
    assert payload["status"] == "quarantined"
    assert payload["species"] == "human"
    assert payload["filename"] == "cells.h5ad"
    assert payload["size_bytes"] == 13
    assert payload["sha256"] == _sha256(b"exact-content")
    upload_dir = root / "uploads" / "quarantine" / payload["upload_id"]
    assert (upload_dir / "payload").read_bytes() == b"exact-content"
    receipt = json.loads((upload_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt == payload
    assert _TOKEN not in json.dumps(receipt)


def test_upload_does_not_silently_dedupe_identical_files(portal):
    client, root, _catalog_path = portal

    first = _upload(client, b"same").json()
    second = _upload(client, b"same").json()

    assert first["upload_id"] != second["upload_id"]
    assert first["sha256"] == second["sha256"]
    assert len(list((root / "uploads" / "quarantine").iterdir())) == 2


@pytest.mark.parametrize(
    ("filename", "species", "content", "status", "detail"),
    [
        ("../cells.h5ad", "human", b"x", 400, "unsafe_upload_filename"),
        ("cells.exe", "human", b"x", 400, "unsupported_upload_type"),
        ("cells.h5ad", "Human", b"x", 400, "unsupported_species"),
        ("cells.h5ad", "human", b"", 400, "empty_upload"),
        ("cells.h5ad", "human", b"x" * 17, 413, "upload_too_large"),
    ],
)
def test_upload_rejects_unsafe_type_species_empty_and_oversize(
    portal, filename, species, content, status, detail
):
    client, root, _catalog_path = portal

    response = _upload(
        client,
        content,
        filename=filename,
        species=species,
    )

    assert response.status_code == status
    assert response.json()["detail"] == detail
    quarantine = root / "uploads" / "quarantine"
    assert not quarantine.exists() or not any(quarantine.iterdir())


def test_upload_total_quota_is_enforced_without_partial_receipt(portal):
    client, root, _catalog_path = portal
    assert _upload(client, b"a" * 13).status_code == 201

    response = _upload(client, b"b" * 13)

    assert response.status_code == 413
    assert response.json()["detail"] == "upload_quota_exceeded"
    quarantine = root / "uploads" / "quarantine"
    assert len(list(quarantine.iterdir())) == 1
    assert not list(quarantine.rglob("*.part"))


def test_bundled_catalog_freezes_four_runtime_species_and_source_hashes(
    monkeypatch,
):
    monkeypatch.delenv("PRAXIS_VC_DATA_CATALOG", raising=False)
    from praxis_vc_api.services.data_portal_service import load_catalog

    catalog = load_catalog()
    datasets = catalog.datasets

    assert [dataset.species.runtime_id for dataset in datasets] == [
        "human",
        "mouse",
        "yeast",
        "bacteria",
    ]
    assert sum(
        file.size_bytes
        for dataset in datasets
        for file in dataset.files
    ) == 27_823_623
    assert {
        file.sha256
        for dataset in datasets
        for file in dataset.files
    } == {
        "9beae9e7852b2514b4449ecdc5d5a762445289dcfbe5ddb70a44866380b673ce",
        "483f7bae81020de70928f6eec71a373b47454e4fb6c39d54900232d98719dec3",
        "f7c16697210358abf14d18ee25edd66ff9e0ab39b9e977fc001d90ac28a7b00a",
        "2d64664d20c027bb5659d4caeed76f3470254aeb5ab84c78a775efba0c90a61c",
        "4d8e8e4bee7cf08dea4247f319403c1399af6c9e4069f40f65f54911b748a688",
    }
