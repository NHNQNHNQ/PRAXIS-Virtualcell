"""Path-free P12 identity for the exact train-only additive Candidate-2."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

from praxis_virtualcell.model_zoo.adapter_sdk import DeltaExpressionReferenceAdapter
from praxis_virtualcell.model_zoo.capability_registry import ModelCard
from praxis_virtualcell.model_zoo.registry_v2 import (
    ArtifactIdentity,
    EnvironmentIdentityV2,
    ModelRegistryV2,
    ModelReleaseRecord,
    RegistryLifecycleEvent,
)
from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper

MODEL_NAME = "norman_additive_ridge_train_only_alpha_0_1"
MODEL_VERSION = "1.0.0-candidate.2"
PACK_FINGERPRINT = "42165e430bab3474cdc9e607770ff5e204608c4243f84e492c08e2c6442c55ee"

_ARTIFACT_SPECS = {
    "baseline.json": (
        95109,
        "70ce31dbdca35d0e9f530679b61163cf8dd6abd585fdb1b4af245a50d9c54150",
        "application/json",
    ),
    "candidate-record.json": (
        6165,
        "743bc29d2659de8eb8ee51511937f8e4f4532d02fe89bc3a82ce4cae087e1518",
        "application/json",
    ),
    "linear_coefficients.npy": (
        2744608,
        "b11e6555fb3cdcf626d74a6fc5ece181c6d0c7f92c45e2bd737689773c5fd426",
        "application/x-npy",
    ),
    "linear_intercept.npy": (
        40488,
        "6a68609d883ce01a764567a7eae8dd64e645d2b3cbdcab5db50d5c106a0e1cae",
        "application/x-npy",
    ),
}

_RUNTIME_PACKAGES = (
    ("anndata", "0.12.11"),
    ("cell-gears", "0.1.2"),
    ("dcor", "0.6"),
    ("h5py", "3.16.0"),
    ("networkx", "3.6.1"),
    ("numpy", "2.4.4"),
    ("pandas", "2.3.3"),
    ("pyyaml", "6.0.3"),
    ("scanpy", "1.12.1"),
    ("scikit-learn", "1.8.0"),
    ("scipy", "1.17.1"),
    ("torch", "2.11.0"),
    ("torch-geometric", "2.7.0"),
    ("tqdm", "4.67.3"),
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _verified_inventory(root: str | Path) -> dict[str, dict[str, Any]]:
    raw_root = Path(root)
    if raw_root.is_symlink():
        raise ValueError("Candidate-2 artifact root must not be a symlink")
    try:
        resolved = raw_root.resolve(strict=True)
        root_fd = os.open(resolved, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError as exc:
        raise ValueError("Candidate-2 artifact root is unavailable") from exc
    try:
        if set(os.listdir(root_fd)) != set(_ARTIFACT_SPECS):
            raise ValueError("Candidate-2 artifact inventory must contain exactly four files")
        records: dict[str, dict[str, Any]] = {}
        inodes: dict[str, tuple[int, int]] = {}
        for name, (expected_size, expected_sha256, media_type) in _ARTIFACT_SPECS.items():
            flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
            try:
                file_fd = os.open(name, flags, dir_fd=root_fd)
            except OSError as exc:
                raise ValueError(f"Candidate-2 artifact is unavailable: {name}") from exc
            try:
                before = os.fstat(file_fd)
                if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size != expected_size:
                    raise ValueError(f"Candidate-2 artifact metadata changed: {name}")
                digest = hashlib.sha256()
                while chunk := os.read(file_fd, 1024 * 1024):
                    digest.update(chunk)
                after = os.fstat(file_fd)
            finally:
                os.close(file_fd)
            identity_fields = (
                "st_dev",
                "st_ino",
                "st_mode",
                "st_nlink",
                "st_size",
                "st_mtime_ns",
                "st_ctime_ns",
            )
            if any(getattr(before, field) != getattr(after, field) for field in identity_fields):
                raise ValueError(f"Candidate-2 artifact changed while hashing: {name}")
            linked = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            if any(getattr(after, field) != getattr(linked, field) for field in identity_fields):
                raise ValueError(f"Candidate-2 artifact changed after hashing: {name}")
            actual_sha256 = digest.hexdigest()
            if actual_sha256 != expected_sha256:
                raise ValueError(f"Candidate-2 artifact SHA-256 changed: {name}")
            inodes[name] = (after.st_dev, after.st_ino)
            records[name] = {
                "sha256": actual_sha256,
                "size_bytes": after.st_size,
                "media_type": media_type,
            }
        if set(os.listdir(root_fd)) != set(_ARTIFACT_SPECS):
            raise ValueError("Candidate-2 artifact inventory changed while hashing")
        for name, inode in inodes.items():
            current = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            if (current.st_dev, current.st_ino) != inode:
                raise ValueError(f"Candidate-2 artifact changed after inventory: {name}")
        return records
    finally:
        os.close(root_fd)


class Candidate2IdentityOnlyWrapper(ModelWrapper):
    """Fail closed until a separate evidence-bound execution policy exists."""

    name = MODEL_NAME

    def declare_scope(self) -> dict:
        return {
            "species": ["human"],
            "cell_identity": "CVCL_0004",
            "module": "genetic_hub",
            "task": ["predict_delta_expression"],
            "perturbation": ["gene", "gene_combination"],
        }

    def run_prediction(self, model_input: dict) -> dict:
        raise RuntimeError("Candidate-2 release is identity-only and has no execution authorization")


def _model_card(records: dict[str, dict[str, Any]]) -> ModelCard:
    return ModelCard.from_dict(
        {
            "schema_version": "vc.model-card.v1",
            "name": MODEL_NAME,
            "type": "self_trained",
            "species": ["human"],
            "taxon": ["NCBITaxon:9606"],
            "module": "genetic_hub",
            "modality": [{"name": "scRNA", "ontology_id": "EFO:0008913"}],
            "assay": ["EFO:0008913"],
            "cell_domain": {
                "cell_type_ids": ["CVCL_0004"],
                "cell_type_names": ["K562"],
                "tissue_ids": [],
                "tissue_names": [],
                "allow_unspecified": False,
            },
            "perturbation": ["gene", "gene_combination"],
            "task": "predict_delta_expression",
            "output": ["delta_expression"],
            "feature_namespace": [{"name": "EnsemblGene", "version": "Ensembl 84", "id_format": "ensembl_gene"}],
            "representation": ["matrix:X"],
            "source": "local:golden-norman-train-only-candidate-2",
            "license": "CC0-1.0",
            "status": "available",
            "wrapper": "scripts.candidate2_release_identity.Candidate2IdentityOnlyWrapper",
            "version": MODEL_VERSION,
            "requires": ["numpy"],
            "assets": [
                {
                    "filename": name,
                    "sha256": record["sha256"],
                    "media_type": record["media_type"],
                    "source_note": "Exact deterministic outer-train-only Candidate-2 artifact.",
                }
                for name, record in records.items()
            ],
            "resources": {"python_dependencies": ["numpy"], "required": ["cpu"]},
            "uncertainty": {"required": True, "methods": ["point_estimate"], "calibrated": False},
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
            "reliability_policy": "identity_only_no_execution_without_evidence_and_policy",
            "training_card": {
                "training_data": "norman-2019-k562-golden@1.0.0 train",
                "split": "outer-train-only with deterministic inner condition split",
                "baseline": "condition-level additive ridge",
                "metrics": {},
                "provenance": "Exact candidate record and four artifact hashes",
                "algorithm": "condition-level additive ridge alpha=0.1",
                "candidate_record_sha256": records["candidate-record.json"]["sha256"],
                "evidence_status": "not_run",
            },
            "provenance": {
                "pack_fingerprint": PACK_FINGERPRINT,
                "candidate_role": "train_only_candidate_2_not_scientific_evidence",
                "default_route_changed": False,
            },
        }
    )


def _environment(adapter_fingerprint: str, records: dict[str, dict[str, Any]]) -> EnvironmentIdentityV2:
    packages = [{"name": name, "version": version} for name, version in _RUNTIME_PACKAGES]
    lock = {
        "schema_version": "praxis.additive-train-only-candidate2-environment-lock.v1",
        "python_version": "3.13.12",
        "platform_system": "Darwin",
        "cpu_architecture": "arm64",
        "packages": packages,
        "gears_source_manifest_sha256": ("031e22721292234cae68b841ea65b3d247896f53f585e45baef6222a7b11253a"),
        "candidate_record_sha256": records["candidate-record.json"]["sha256"],
        "adapter_fingerprint": adapter_fingerprint,
    }
    return EnvironmentIdentityV2.from_dict(
        {
            "schema_version": "vc.model-environment.v2",
            "environment_id": "candidate2-build-darwin-arm64",
            "python_version": lock["python_version"],
            "cpu_architecture": lock["cpu_architecture"],
            "packages": packages,
            "lock_digest": _fingerprint(lock),
            "image_digest": None,
            "resources": ["cpu"],
            "accelerators": [],
            "adapter_fingerprints": [adapter_fingerprint],
            "legacy_incomplete": False,
            "artifact_snapshot_budget_policy": {
                "schema_version": "vc.artifact-snapshot-budget-policy.v1",
                "max_live_snapshot_payload_bytes": sum(record["size_bytes"] for record in records.values()),
                "max_snapshot_entries_per_execution": len(records),
                "retention_scope": "execution_only",
            },
        }
    )


def build_candidate2_release_identity(artifact_root: str | Path) -> dict[str, Any]:
    """Reverify exact bytes and return one canonical, path-free identity closure."""

    records = _verified_inventory(artifact_root)
    card = _model_card(records)
    adapter = DeltaExpressionReferenceAdapter().identity()
    environment = _environment(adapter.fingerprint(), records)
    artifacts = tuple(
        ArtifactIdentity.from_dict(
            {
                "schema_version": "vc.model-artifact.v1",
                "artifact_id": f"{MODEL_NAME}:{name}",
                "model_fingerprint": card.fingerprint(),
                "uri": None,
                "cache_key": f"{MODEL_NAME}/{name}",
                "size_bytes": record["size_bytes"],
                "sha256": record["sha256"],
                "media_type": record["media_type"],
                "license": "CC0-1.0",
                "source": "Exact deterministic outer-train-only Candidate-2 artifact",
                "safe_load_policy": "data_only",
                "legacy_incomplete": False,
            }
        )
        for name, record in records.items()
    )
    release = ModelReleaseRecord.from_dict(
        {
            "schema_version": "vc.model-release.v1",
            "release_id": f"{MODEL_NAME}@{MODEL_VERSION}",
            "model_name": card.name,
            "model_version": card.version,
            "model_fingerprint": card.fingerprint(),
            "pack_fingerprints": [PACK_FINGERPRINT],
            "artifact_fingerprints": [artifact.fingerprint() for artifact in artifacts],
            "environment_fingerprint": environment.fingerprint(),
            "adapter_fingerprints": [adapter.fingerprint()],
            "evidence_fingerprints": [],
            "policy_fingerprint": None,
            "migration_status": "native",
            "legacy_status": None,
            "incomplete_reasons": [],
        }
    )
    cataloged = RegistryLifecycleEvent.from_dict(
        {
            "schema_version": "vc.model-registry-event.v1",
            "event_id": "candidate2-additive-cataloged",
            "sequence": 1,
            "previous_event_fingerprint": None,
            "release_fingerprint": release.fingerprint(),
            "action": "cataloged",
            "target_release_fingerprint": None,
            "recorded_at": "2026-08-17T00:00:00Z",
            "operator_id": "local-artifact-custodian",
            "reason": "Catalog exact Candidate-2 identity without execution or science authorization",
        }
    )
    ready = RegistryLifecycleEvent.from_dict(
        {
            "schema_version": "vc.model-registry-event.v1",
            "event_id": "candidate2-additive-artifact-ready",
            "sequence": 2,
            "previous_event_fingerprint": cataloged.fingerprint(),
            "release_fingerprint": release.fingerprint(),
            "action": "artifact_ready",
            "target_release_fingerprint": None,
            "recorded_at": "2026-08-17T00:00:01Z",
            "operator_id": "local-artifact-custodian",
            "reason": "All four local data-only artifacts passed inventory, size, link, and SHA-256 checks",
        }
    )
    registry = ModelRegistryV2.from_dict(
        {
            "schema_version": "vc.model-registry.v2",
            "artifacts": [artifact.to_dict() for artifact in artifacts],
            "environments": [environment.to_dict()],
            "adapters": [adapter.to_dict()],
            "evidence_records": [],
            "policy_records": [],
            "releases": [release.to_dict()],
            "lifecycle_events": [cataloged.to_dict(), ready.to_dict()],
        }
    )
    state = registry.state(release.fingerprint())
    receipt = {
        "schema_version": "praxis.additive-train-only-candidate2-release-receipt.v1",
        "record_role": "p12_multi_artifact_identity_only_not_scientific_evidence",
        "model_name": card.name,
        "model_version": card.version,
        "model_fingerprint": card.fingerprint(),
        "pack_fingerprint": PACK_FINGERPRINT,
        "release_fingerprint": release.fingerprint(),
        "capability_fingerprint": release.capability_fingerprint(),
        "registry_fingerprint": registry.fingerprint(),
        "environment_fingerprint": environment.fingerprint(),
        "adapter_fingerprint": adapter.fingerprint(),
        "artifacts": [
            {
                "filename": name,
                "artifact_fingerprint": artifact.fingerprint(),
                "sha256": record["sha256"],
                "size_bytes": record["size_bytes"],
                "safe_load_policy": artifact.safe_load_policy,
            }
            for (name, record), artifact in zip(records.items(), artifacts, strict=True)
        ],
        "evidence_fingerprints": [],
        "policy_fingerprint": None,
        "cataloged": state.cataloged,
        "artifact_ready": state.artifact_ready,
        "revoked": state.revoked,
        "superseded_by": state.superseded_by,
        "research_execution_authorized": False,
        "benchmark_passed": None,
        "scientifically_validated": None,
        "promotion_eligible": None,
        "production_promoted": False,
        "default_route_changed": False,
    }
    return {
        "schema_version": "praxis.additive-train-only-candidate2-release-identity.v1",
        "model_card": card.to_dict(),
        "registry": registry.to_dict(),
        "receipt": receipt,
    }


def candidate2_release_identity_bytes(artifact_root: str | Path) -> bytes:
    """Return canonical JSON plus one trailing newline for durable storage."""

    return _canonical_bytes(build_candidate2_release_identity(artifact_root)) + b"\n"
