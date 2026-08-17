from __future__ import annotations

import ast
import errno
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).parents[2] / "scripts/freeze_k562_crispra_blinded_intake.py"


def _module():
    spec = importlib.util.spec_from_file_location("freeze_k562_crispra_blinded_intake", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(module, path: Path, value: dict) -> bytes:
    payload = module._canonical_bytes(value) + b"\n"
    path.write_bytes(payload)
    return payload


def _install_controlled_no_replace(module, monkeypatch) -> None:
    def controlled_no_replace(parent_fd: int, source_name: str, destination_name: str) -> None:
        try:
            os.stat(destination_name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise module.BlindedIntakeError("output must be write-new")
        os.rename(
            source_name,
            destination_name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )

    monkeypatch.setattr(module, "_rename_no_replace", controlled_no_replace)


def _fixture(module, tmp_path: Path) -> tuple[Path, Path, dict[str, bytes]]:
    private_root = tmp_path / "private-custodian-root"
    private_root.mkdir(mode=0o700)
    private_root.chmod(0o700)
    contract = module._strict_json(module._CONTRACT.read_bytes(), "contract")
    asset_contract = contract["input_contract"]["asset_contract"]
    opaque_payloads = {}
    assets = []
    for role in asset_contract["required_roles"]:
        if role == "outcome_delta":
            payload = b'{"outcome":NaN,"duplicate":1,"duplicate":2}\n\x00private:' + os.fsencode(private_root)
        else:
            payload = f"opaque:{role}".encode()
        opaque_payloads[role] = payload
        filename = f"sealed-{role}.bin"
        (private_root / filename).write_bytes(payload)
        assets.append(
            {
                "asset_id": f"{role}-primary",
                "role": role,
                "filename": filename,
                "source_locator": f"custodian:synthetic-{role}",
                "license": "CC0-1.0",
                "media_type": "application/octet-stream",
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    assets.sort(key=lambda item: item["asset_id"])
    assets_by_role = {item["role"]: item for item in assets}
    closure = {field: assets_by_role[role]["sha256"] for role, field in asset_contract["role_sha256_fields"].items()}
    closure["license_sha256"] = hashlib.sha256(b"CC0-1.0").hexdigest()
    scope = {
        "schema_version": contract["input_contract"]["scope_manifest_schema_version"],
        "record_role": "outcome_opaque_custodian_scope_declaration",
        "bundle_role": contract["input_contract"]["allowed_bundle_roles"][0],
        "source_id": "custodian:synthetic",
        "laboratory_id": "laboratory:fixture",
        "dataset_fingerprint": "1" * 64,
        "platform_fingerprint": "2" * 64,
        "source": "custodian:synthetic-dataset",
        "license": "CC0-1.0",
        "outcome_values_in_manifest": False,
        "condition_set_sha256": "3" * 64,
        "group_set_sha256": "4" * 64,
        "condition_counts": {
            "gene_combination": 2,
            "matched_non_targeting_control": 3,
            "single_gene": 5,
        },
        "asset_identity_closure": closure,
        "scope": contract["input_contract"]["required_scope"],
        "opaque_assets": assets,
    }
    scope_payload = _write_json(module, private_root / module._SCOPE_NAME, scope)
    event_types = contract["input_contract"]["custody_event_order"]
    events = [
        {
            "sequence": sequence,
            "event_id": f"event:{sequence}",
            "event_type": event_type,
            "recorded_at": f"2026-08-17T00:00:0{sequence}Z",
            "operator_id": "custodian:fixture",
            "outcome_decoded": False,
            "candidate_team_received_asset_bytes": False,
            "candidate_outputs_used_for_condition_selection": False,
        }
        for sequence, event_type in enumerate(event_types, start=1)
    ]
    custody = {
        "schema_version": contract["input_contract"]["custody_record_schema_version"],
        "record_role": "private_value_free_custody_record_not_scientific_evidence",
        "custody_id": "custody:synthetic",
        "custodian_id": "custodian:fixture",
        "authorization_record_sha256": "5" * 64,
        "scope_manifest_sha256": hashlib.sha256(scope_payload).hexdigest(),
        "events": events,
    }
    _write_json(module, private_root / module._CUSTODY_NAME, custody)
    for sidecar in private_root.glob("._*"):
        sidecar.unlink()
    return private_root, tmp_path / "consumer-manifest.json", opaque_payloads


def test_freeze_is_value_free_path_free_self_hashed_and_write_new(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    _install_controlled_no_replace(module, monkeypatch)
    private_root, output, opaque_payloads = _fixture(module, tmp_path)

    manifest = module.freeze(private_root=private_root, output=output)

    payload = output.read_bytes()
    assert payload == module._canonical_bytes(manifest) + b"\n"
    unhashed = json.loads(module._canonical_bytes(manifest))
    unhashed["identity"]["payload_sha256"] = None
    assert manifest["identity"]["payload_sha256"] == module._fingerprint(unhashed)
    assert manifest["identity"]["verifier_sha256"] == hashlib.sha256(_SCRIPT.read_bytes()).hexdigest()
    assert manifest["scope"] == {
        "adaptation": {"consumer": "evaluation-client", "steps": 0},
        "cell_identity": {"cellosaurus_id": "CVCL_0004", "name": "K562"},
        "feature_axis": {
            "count": 5045,
            "namespace": "EnsemblGene",
            "ordered_ids_sha256": "ecca6c636629e35ae5f5a0ec6fe84c1a7983e1adb263fbbcaea70a0c5495b2b7",
            "version": "Ensembl 84",
        },
        "intervention": {
            "control": "matched non-targeting control",
            "mode": "gene-targeted CRISPRa",
            "scopes": ["single-gene", "gene-combination"],
            "timepoint_hours": 120,
        },
        "measurement": {"assay_scope": "whole-transcriptome", "modality": "scRNA"},
        "organism": {"scientific_name": "Homo sapiens", "taxonomy_id": "NCBITaxon:9606"},
        "target_axis": {
            "count": 68,
            "namespace": "EnsemblGene",
            "ordered_ids_sha256": "2bc167c08c3b7a822ddfa626af55e515078a29ba13463607d70419692f777e57",
            "version": "Ensembl 84",
        },
    }
    assert manifest["status"] == {
        "intake_status": "READY_FOR_ESCROW",
        "trusted_pin_required": True,
        "trusted_pin_present": False,
        "evaluation_lock_required": True,
        "evaluation_lock_present": False,
        "evaluation_authorized": False,
        "pair_closure_required": True,
        "pair_closure_present": False,
        "pair_closure_status": "PENDING_SECOND_INDEPENDENT_RECEIPT",
    }
    assert manifest["states"] == {
        "benchmark_status": "NOT_RUN",
        "benchmark_passed": None,
        "scientifically_validated": False,
        "promotion_eligible": False,
        "production_promoted": False,
        "registry_or_default_route_changed": False,
    }
    assert manifest["blind_boundary"] == {
        "outcome_values_in_scope_manifest": False,
        "opaque_asset_bytes_embedded": False,
        "opaque_asset_paths_embedded": False,
        "outcome_decoded": False,
        "candidate_team_received_asset_bytes": False,
        "candidate_outputs_used_for_condition_selection": False,
    }
    assert {item["role"] for item in manifest["opaque_asset_identities"]} == {
        "raw_counts",
        "cell_metadata",
        "feature_metadata",
        "condition_metadata",
        "preprocessing_code",
        "preprocessing_environment",
        "outcome_delta",
    }
    outcome_identity = next(item for item in manifest["opaque_asset_identities"] if item["role"] == "outcome_delta")
    assert outcome_identity == {
        "asset_id": "outcome_delta-primary",
        "role": "outcome_delta",
        "source_locator": "custodian:synthetic-outcome_delta",
        "license": "CC0-1.0",
        "media_type": "application/octet-stream",
        "size_bytes": len(opaque_payloads["outcome_delta"]),
        "sha256": hashlib.sha256(opaque_payloads["outcome_delta"]).hexdigest(),
    }
    assert manifest["pair_requirement"] == {
        "all_independence_fields_must_differ": True,
        "independence_fields": ["custodian_id", "dataset_fingerprint", "laboratory_id", "platform_fingerprint"],
        "required_receipt_count": 2,
        "required_roles": ["independent_external_dataset_and_platform", "replacement_primary_holdout"],
        "single_receipt_status": "PENDING_SECOND_INDEPENDENT_RECEIPT",
    }
    serialized = payload.decode("utf-8")
    assert str(private_root) not in serialized
    assert all(f"sealed-{role}.bin" not in serialized for role in opaque_payloads)
    assert 'outcome"' not in serialized
    assert list(inspect.signature(module.freeze).parameters) == ["private_root", "output"]
    with pytest.raises(module.BlindedIntakeError, match="write-new"):
        module.freeze(private_root=private_root, output=output)
    assert output.read_bytes() == payload
    assert not list(tmp_path.glob(".praxis-k562-intake-*.tmp"))


def test_contract_raw_and_logical_identities_are_both_pinned(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    raw = module._CONTRACT.read_bytes()
    assert len(raw) == module._CONTRACT_SIZE_BYTES
    assert hashlib.sha256(raw).hexdigest() == module._CONTRACT_SHA256
    changed = module._strict_json(raw, "contract")
    changed["input_contract"]["required_scope"]["intervention"]["timepoint_hours"] = 121
    changed["identity"]["payload_sha256"] = None
    changed["identity"]["payload_sha256"] = module._fingerprint(changed)
    changed_path = tmp_path / "changed-contract.json"
    _write_json(module, changed_path, changed)
    monkeypatch.setattr(module, "_CONTRACT", changed_path)

    with pytest.raises(module.BlindedIntakeError, match="raw identity changed"):
        module._load_contract()


@pytest.mark.parametrize("mutation", ["duplicate_role", "zero_count", "closure"])
def test_freeze_rejects_incomplete_asset_or_condition_closure(tmp_path: Path, mutation: str) -> None:
    module = _module()
    private_root, output, _ = _fixture(module, tmp_path)
    scope_path = private_root / module._SCOPE_NAME
    scope = module._strict_json(scope_path.read_bytes(), "scope")
    if mutation == "duplicate_role":
        scope["opaque_assets"][0]["role"] = scope["opaque_assets"][1]["role"]
    elif mutation == "zero_count":
        scope["condition_counts"]["single_gene"] = 0
    else:
        scope["asset_identity_closure"]["raw_counts_sha256"] = "0" * 64
    _write_json(module, scope_path, scope)

    with pytest.raises(module.BlindedIntakeError):
        module.freeze(private_root=private_root, output=output)
    assert not output.exists()


@pytest.mark.parametrize(
    "local_locator",
    [
        "/private/outcome",
        "../outcome",
        "file:///private/outcome",
        r"C:\outcome",
        "custodian:/private/outcome",
        "custodian:C:/outcome",
        "custodian:Users/alice/private/outcome",
    ],
)
def test_freeze_rejects_local_source_paths(tmp_path: Path, local_locator: str) -> None:
    module = _module()
    private_root, output, _ = _fixture(module, tmp_path)
    scope_path = private_root / module._SCOPE_NAME
    scope = module._strict_json(scope_path.read_bytes(), "scope")
    scope["opaque_assets"][0]["source_locator"] = local_locator
    _write_json(module, scope_path, scope)

    with pytest.raises(module.BlindedIntakeError, match="source_locator"):
        module.freeze(private_root=private_root, output=output)
    assert not output.exists()


def test_atomic_publication_fsync_failure_keeps_complete_final_without_temp(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    _install_controlled_no_replace(module, monkeypatch)
    private_root, output, _ = _fixture(module, tmp_path)
    real_fsync = module.os.fsync
    calls = 0

    def fail_directory_fsync(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError(errno.EIO, "synthetic directory fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(module.os, "fsync", fail_directory_fsync)
    with pytest.raises(module.BlindedIntakeError, match="cannot persist"):
        module.freeze(private_root=private_root, output=output)
    assert calls == 2
    payload = output.read_bytes()
    manifest = module._strict_json(payload, "retained failed-publication manifest")
    unhashed = json.loads(module._canonical_bytes(manifest))
    unhashed["identity"]["payload_sha256"] = None
    assert manifest["identity"]["payload_sha256"] == module._fingerprint(unhashed)
    assert str(private_root) not in payload.decode("utf-8")
    assert not list(tmp_path.glob(".praxis-k562-intake-*.tmp"))


def test_atomic_publication_rechecks_inode_without_deleting_replacement(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    private_root, output, _ = _fixture(module, tmp_path)
    _install_controlled_no_replace(module, monkeypatch)
    real_rename = module._rename_no_replace

    def replace_after_publish(parent_fd: int, source_name: str, destination_name: str) -> None:
        real_rename(parent_fd, source_name, destination_name)
        os.unlink(destination_name, dir_fd=parent_fd)
        descriptor = os.open(
            destination_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
            dir_fd=parent_fd,
        )
        try:
            os.write(descriptor, b"replacement")
        finally:
            os.close(descriptor)

    monkeypatch.setattr(module, "_rename_no_replace", replace_after_publish)
    with pytest.raises(module.BlindedIntakeError, match="identity or bytes changed"):
        module.freeze(private_root=private_root, output=output)
    assert output.read_bytes() == b"replacement"
    assert not list(tmp_path.glob(".praxis-k562-intake-*.tmp"))


def test_atomic_publication_rechecks_parent_binding_before_return(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    private_root, _, _ = _fixture(module, tmp_path)
    publication_parent = tmp_path / "publication"
    publication_parent.mkdir(mode=0o700)
    publication_parent.chmod(0o700)
    output = publication_parent / "consumer-manifest.json"
    moved_parent = tmp_path / "publication-moved"
    _install_controlled_no_replace(module, monkeypatch)
    real_verify = module._verify_published

    def swap_parent_after_verify(*args, **kwargs) -> None:
        real_verify(*args, **kwargs)
        publication_parent.rename(moved_parent)
        publication_parent.mkdir()

    monkeypatch.setattr(module, "_verify_published", swap_parent_after_verify)
    with pytest.raises(module.BlindedIntakeError, match="parent binding changed"):
        module.freeze(private_root=private_root, output=output)
    assert not output.exists()
    retained = moved_parent / output.name
    module._strict_json(retained.read_bytes(), "retained moved-parent manifest")
    assert not list(moved_parent.glob(".praxis-k562-intake-*.tmp"))


def test_atomic_publication_requires_owner_mode_0700_parent(tmp_path: Path) -> None:
    module = _module()
    private_root = tmp_path / "private"
    private_root.mkdir(mode=0o700)
    private_root.chmod(0o700)
    public_parent = tmp_path / "public-parent"
    public_parent.mkdir(mode=0o755)
    public_parent.chmod(0o755)
    if public_parent.stat().st_mode & 0o777 != 0o755:
        pytest.skip("filesystem cannot represent a non-0700 output parent")
    output = public_parent / "consumer-manifest.json"

    with pytest.raises(module.BlindedIntakeError, match="parent binding changed"):
        module._write_new(output, b'{"path_free":true}\n', private_root)
    assert not output.exists()


def test_real_filesystem_atomic_publication_succeeds_or_fails_closed(tmp_path: Path) -> None:
    module = _module()
    private_root = tmp_path / "private"
    private_root.mkdir(mode=0o700)
    private_root.chmod(0o700)
    output = tmp_path / "real-publication.json"
    payload = b'{"path_free":true}\n'

    try:
        module._write_new(output, payload, private_root)
    except module.BlindedIntakeError as exc:
        assert "cannot provide atomic no-replace publication" in str(exc)
        assert not output.exists()
    else:
        assert output.read_bytes() == payload
        with pytest.raises(module.BlindedIntakeError, match="write-new"):
            module._write_new(output, payload, private_root)
        assert output.read_bytes() == payload
    assert not list(tmp_path.glob(".praxis-k562-intake-*.tmp"))


@pytest.mark.parametrize("mutation", ["tamper", "extra", "duplicate", "nonfinite", "event_order"])
def test_freeze_rejects_changed_or_invalid_intake(tmp_path: Path, mutation: str) -> None:
    module = _module()
    private_root, output, _ = _fixture(module, tmp_path)
    if mutation == "tamper":
        with (private_root / "sealed-outcome_delta.bin").open("ab") as stream:
            stream.write(b"tampered")
    elif mutation == "extra":
        (private_root / "unexpected.bin").write_bytes(b"extra")
    elif mutation == "duplicate":
        (private_root / module._SCOPE_NAME).write_bytes(b'{"schema_version":1,"schema_version":2}\n')
    elif mutation == "nonfinite":
        (private_root / module._SCOPE_NAME).write_bytes(b'{"bad":NaN}\n')
    else:
        custody_path = private_root / module._CUSTODY_NAME
        custody = module._strict_json(custody_path.read_bytes(), "custody")
        custody["events"].reverse()
        _write_json(module, custody_path, custody)

    expected_error = {
        "duplicate": "duplicate JSON key",
        "nonfinite": "non-finite JSON number",
    }.get(mutation)
    if expected_error is None:
        with pytest.raises(module.BlindedIntakeError):
            module.freeze(private_root=private_root, output=output)
    else:
        with pytest.raises(module.BlindedIntakeError, match=expected_error):
            module.freeze(private_root=private_root, output=output)
    assert not output.exists()


def test_freeze_rejects_symlinked_opaque_asset(tmp_path: Path) -> None:
    module = _module()
    private_root, output, opaque_payloads = _fixture(module, tmp_path)
    asset = private_root / "sealed-outcome_delta.bin"
    outside = tmp_path / "outside.bin"
    outside.write_bytes(opaque_payloads["outcome_delta"])
    asset.unlink()
    try:
        asset.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(module.BlindedIntakeError):
        module.freeze(private_root=private_root, output=output)
    assert not output.exists()


@pytest.mark.parametrize("replacement", ["hardlink", "fifo"])
def test_freeze_rejects_non_single_link_or_special_asset(tmp_path: Path, replacement: str) -> None:
    module = _module()
    private_root, output, opaque_payloads = _fixture(module, tmp_path)
    asset = private_root / "sealed-outcome_delta.bin"
    asset.unlink()
    try:
        if replacement == "hardlink":
            outside = tmp_path / "outside.bin"
            outside.write_bytes(opaque_payloads["outcome_delta"])
            os.link(outside, asset)
        else:
            os.mkfifo(asset)
    except OSError as exc:
        pytest.skip(f"{replacement} unavailable: {exc}")

    with pytest.raises(module.BlindedIntakeError, match="regular and single-link"):
        module.freeze(private_root=private_root, output=output)
    assert not output.exists()


def test_verifier_imports_only_stdlib_and_exposes_no_asset_argument() -> None:
    tree = ast.parse(_SCRIPT.read_text(encoding="utf-8"))
    imports = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    imports.update(
        alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
    )
    assert imports <= {
        "__future__",
        "argparse",
        "ctypes",
        "datetime",
        "errno",
        "hashlib",
        "json",
        "os",
        "pathlib",
        "re",
        "secrets",
        "stat",
        "sys",
        "typing",
        "urllib",
    }
    assert imports.isdisjoint({"anndata", "numpy"})
    module = _module()
    assert list(inspect.signature(module.freeze).parameters) == ["private_root", "output"]
