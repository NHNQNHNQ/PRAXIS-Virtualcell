"""Runtime resolver for the versioned MDR-GNB model catalog.

The catalog records declarations and scientific validation boundaries.  Readiness is
derived at runtime from the exact artifact, digest, dependencies, deserialization and
adapter schema probe; it is never copied from a registry ``status`` or evidence tier.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = Path(__file__).with_name("registry_mdr_gnb.yaml")
EXPERIMENTAL_SIDECAR_CONTRACT_VERSION = "mdr-gem-sidecar-v1"


def canonical_drug_id(value: str) -> str:
    return value.strip().lower().replace("/", "_").replace(" ", "_")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=512)
def _sha256_with_stat(
    path_string: str,
    device: int,
    inode: int,
    size: int,
    mtime_ns: int,
    ctime_ns: int,
) -> str:
    """Return a digest cached only while a strong local file identity is unchanged.

    ``device``, ``inode``, ``size``, ``mtime_ns`` and ``ctime_ns`` form a local
    filesystem cache key, not a substitute for a content-addressed release.  The
    key catches ordinary in-place writes and atomic replacements while avoiding a
    full re-hash of the same large artifact for every readiness probe.  An
    attacker (or filesystem) able to preserve all of those fields can still fool
    this cache, and the stat/hash/load sequence remains subject to TOCTOU; model
    deployment therefore still needs immutable versioned artifact paths.

    Adapter deserialization is separately cached by the verified SHA-256.
    """
    del device, inode, size, mtime_ns, ctime_ns
    return sha256_file(Path(path_string))


@lru_cache(maxsize=256)
def _load_adapter(path_string: str, adapter: str, artifact_sha256: str) -> Any:
    """Load only after the caller verified bytes; cache by the verified SHA-256.

    This is intentionally not keyed by a logical model name or by filesystem
    timestamps.  A catalog/artifact rotation at the same path therefore cannot
    reuse an adapter object loaded for earlier bytes.
    """
    del artifact_sha256
    path = Path(path_string)
    if adapter == "genotype_to_sir":
        from praxis_virtualcell.mdr_gnb.predictors.genotype_to_sir import GenotypeToSIR

        return GenotypeToSIR.load(path)
    if adapter == "small_molecule":
        from praxis_virtualcell.mdr_gnb.predictors.small_molecule_model import (
            SmallMoleculeModel,
        )

        return SmallMoleculeModel.load(path)
    if adapter == "peptide":
        from praxis_virtualcell.mdr_gnb.predictors.peptide_activity_model import (
            PeptideActivityModel,
        )

        return PeptideActivityModel.load(path)
    raise ValueError(f"unsupported runtime adapter: {adapter}")


@dataclass(frozen=True)
class ModelReadiness:
    model_id: str | None
    declared: bool
    ready: bool
    validated: bool
    validation_status: str
    reason_code: str
    execution: str | None
    artifact_path: str | None
    expected_sha256: str | None
    catalog_digest: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "declared": self.declared,
            "ready": self.ready,
            "validated": self.validated,
            "validation_status": self.validation_status,
            "reason_code": self.reason_code,
            "execution": self.execution,
            "artifact_path": self.artifact_path,
            "expected_sha256": self.expected_sha256,
            "catalog_digest": self.catalog_digest,
        }


@dataclass(frozen=True)
class ExperimentalSidecarContract:
    """Integrity result for a direct experimental sidecar invocation.

    ``operational`` deliberately does *not* mean runtime-ready, routeable, validated,
    or scientifically accepted.  It says only that one experimental process has the
    exact catalog-bound artifact and dependency profile needed to execute locally.
    """

    model_id: str | None
    declared: bool
    operational: bool
    reason_code: str
    execution: str | None
    artifact_path: str | None
    expected_sha256: str | None
    dependency_versions: dict[str, str]
    catalog_digest: str
    contract_version: str = EXPERIMENTAL_SIDECAR_CONTRACT_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "model_id": self.model_id,
            "declared": self.declared,
            "operational": self.operational,
            "reason_code": self.reason_code,
            "execution": self.execution,
            "artifact_path": self.artifact_path,
            "expected_sha256": self.expected_sha256,
            "dependency_versions": dict(self.dependency_versions),
            "catalog_digest": self.catalog_digest,
        }


class RuntimeModelManifest:
    """Read the self-contained runtime catalog and derive request-safe readiness."""

    def __init__(
        self,
        catalog_path: Path | str | None = None,
        *,
        repo_root: Path | str | None = None,
        catalog_bytes: bytes | None = None,
    ) -> None:
        self.path = Path(catalog_path or DEFAULT_CATALOG).resolve()
        self.repo_root = Path(repo_root or REPO_ROOT).resolve()
        # A request-scoped execution context may have captured the YAML bytes
        # immediately before its cache lookup.  Parse precisely those bytes so
        # catalog digest, manifest document and later provenance are one fact.
        self._catalog_bytes = catalog_bytes if catalog_bytes is not None else self.path.read_bytes()
        self.catalog_digest = hashlib.sha256(self._catalog_bytes).hexdigest()
        self.doc = yaml.safe_load(self._catalog_bytes.decode("utf-8")) or {}
        self._validate_catalog()
        self.models: dict[str, dict[str, Any]] = self.doc["models"]
        self._sir_evidence_cache: (
            tuple[dict[str, dict[str, Any]] | None, str | None] | None
        ) = None

    def _validate_catalog(self) -> None:
        if self.doc.get("schema_version") != "1.0":
            raise ValueError("unsupported MDR-GNB catalog schema_version")
        models = self.doc.get("models")
        if not isinstance(models, dict) or not models:
            raise ValueError("MDR-GNB catalog requires non-empty models")
        for model_id, model in models.items():
            if not isinstance(model, dict) or model.get("id") != model_id:
                raise ValueError(f"invalid catalog model id: {model_id}")
            capability = model.get("capability")
            lifecycle = model.get("lifecycle")
            validation = model.get("validation")
            if not isinstance(capability, dict) or not isinstance(lifecycle, dict):
                raise ValueError(f"catalog model {model_id} lacks capability/lifecycle")
            if not isinstance(validation, dict) or not validation.get("status"):
                raise ValueError(f"catalog model {model_id} lacks validation status")
            if model.get("execution") == "predict":
                asset = model.get("asset")
                runtime = model.get("runtime")
                if not isinstance(asset, dict) or not asset.get("path") or not asset.get("sha256"):
                    raise ValueError(f"predict model {model_id} lacks SHA-locked asset")
                if not isinstance(runtime, dict) or not runtime.get("adapter"):
                    raise ValueError(f"predict model {model_id} lacks runtime adapter")
                versions = runtime.get("dependency_versions")
                if not isinstance(versions, dict) or not all(
                    isinstance(name, str) and isinstance(version, str)
                    for name, version in versions.items()
                ):
                    raise ValueError(
                        f"predict model {model_id} lacks dependency version contract"
                    )

    def _source_is_current(self, source_name: str) -> bool:
        source = (self.doc.get("generated_from") or {}).get(source_name)
        if not isinstance(source, dict):
            return False
        path_value = source.get("path")
        expected = source.get("sha256")
        if not isinstance(path_value, str) or not isinstance(expected, str):
            return False
        try:
            raw_path = Path(path_value)
            path = raw_path.resolve() if raw_path.is_absolute() else self._repo_path(path_value)
        except (OSError, ValueError):
            return False
        if path != self.repo_root and self.repo_root not in path.parents:
            return False
        try:
            return path.is_file() and sha256_file(path) == expected
        except OSError:
            return False

    def _sir_source_failure_reason(self) -> str | None:
        """Return the first stale catalog source that can affect SIR semantics."""
        if not self._source_is_current("sir_batch_manifest"):
            return "sir_source_manifest_sha256_mismatch"
        if not self._source_is_current("evidence_tiers"):
            return "sir_evidence_tiers_sha256_mismatch"
        if not self._source_is_current("amrfinder_sir_rules"):
            return "sir_amrfinder_rules_sha256_mismatch"
        return None

    def _evidence_tiers_source(self) -> tuple[dict[str, Any], Path] | None:
        """Return the catalog-bound evidence source only when its path is safe."""
        source = (self.doc.get("generated_from") or {}).get("evidence_tiers")
        if not isinstance(source, dict):
            return None
        path_value = source.get("path")
        expected_sha256 = source.get("sha256")
        if not isinstance(path_value, str) or not isinstance(expected_sha256, str):
            return None
        try:
            raw_path = Path(path_value)
            path = raw_path.resolve() if raw_path.is_absolute() else self._repo_path(path_value)
        except (OSError, ValueError):
            return None
        if path != self.repo_root and self.repo_root not in path.parents:
            return None
        return source, path

    @staticmethod
    def _evidence_record_sha256(record: dict[str, Any]) -> str:
        """Match the deterministic record digest emitted by the catalog builder."""
        serialized = json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _load_sir_evidence_records(
        self,
    ) -> tuple[dict[str, dict[str, Any]] | None, str | None]:
        """Load one SHA-bound evidence source into canonical species:drug records."""
        if self._sir_evidence_cache is not None:
            return self._sir_evidence_cache

        source_and_path = self._evidence_tiers_source()
        if source_and_path is None:
            self._sir_evidence_cache = (None, "sir_evidence_source_contract_missing")
            return self._sir_evidence_cache

        source, path = source_and_path
        try:
            source_bytes = path.read_bytes()
            if hashlib.sha256(source_bytes).hexdigest() != source["sha256"]:
                self._sir_evidence_cache = (None, "sir_evidence_tiers_sha256_mismatch")
                return self._sir_evidence_cache
            document = yaml.safe_load(source_bytes.decode("utf-8")) or {}
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            self._sir_evidence_cache = (None, "sir_evidence_source_unreadable")
            return self._sir_evidence_cache
        rows = document.get("evidence_tiers")
        if not isinstance(rows, list):
            self._sir_evidence_cache = (None, "sir_evidence_source_invalid")
            return self._sir_evidence_cache

        records: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                self._sir_evidence_cache = (None, "sir_evidence_source_invalid")
                return self._sir_evidence_cache
            species = row.get("species")
            drug = row.get("drug")
            if not isinstance(species, str) or not species or not isinstance(drug, str) or not drug:
                self._sir_evidence_cache = (None, "sir_evidence_source_invalid")
                return self._sir_evidence_cache
            key = f"{species}:{canonical_drug_id(drug)}"
            if key in records:
                self._sir_evidence_cache = (None, "sir_evidence_record_duplicate")
                return self._sir_evidence_cache
            records[key] = dict(row)

        self._sir_evidence_cache = (records, None)
        return self._sir_evidence_cache

    def _sir_evidence_contract_failure_reason(
        self,
        model_id: str,
        model: dict[str, Any],
    ) -> str | None:
        """Verify one SIR entry is bound to its exact evidence-tier record.

        Catalog-level source hashing catches source-file drift.  This additional
        contract catches catalog-only drift: a wrong key, tier, level, record
        digest, source identity, or artifact binding must not remain routeable.
        """
        try:
            _prefix, species, drug_id = model_id.split("/", maxsplit=2)
        except ValueError:
            return "sir_evidence_model_id_invalid"
        capability = model.get("capability") or {}
        if (
            capability.get("species") != species
            or canonical_drug_id(str(capability.get("drug_id") or "")) != drug_id
        ):
            return "sir_evidence_capability_mismatch"

        validation = model.get("validation")
        if not isinstance(validation, dict):
            return "sir_evidence_contract_missing"
        evidence_key = validation.get("evidence_key")
        if not isinstance(evidence_key, str) or not evidence_key:
            return "sir_evidence_key_missing"
        expected_key = f"{species}:{drug_id}"
        if evidence_key != expected_key:
            return "sir_evidence_key_mismatch"

        source_and_path = self._evidence_tiers_source()
        if source_and_path is None:
            return "sir_evidence_source_contract_missing"
        source, _path = source_and_path
        source_path = source.get("path")
        source_sha256 = source.get("sha256")
        if validation.get("evidence_source_path") is None:
            return "sir_evidence_source_path_missing"
        if validation.get("evidence_source_path") != source_path:
            return "sir_evidence_source_path_mismatch"
        if validation.get("evidence_source_sha256") is None:
            return "sir_evidence_source_sha256_missing"
        if validation.get("evidence_source_sha256") != source_sha256:
            return "sir_evidence_source_sha256_mismatch"

        records, source_failure = self._load_sir_evidence_records()
        if source_failure is not None:
            return source_failure
        assert records is not None
        record = records.get(expected_key)
        if record is None:
            return "sir_evidence_record_missing"
        if (
            record.get("species") != species
            or canonical_drug_id(str(record.get("drug") or "")) != drug_id
        ):
            return "sir_evidence_record_identity_mismatch"

        actual_tier = record.get("tier")
        actual_level = record.get("evidence_level")
        if not isinstance(actual_tier, str) or not actual_tier:
            return "sir_evidence_record_invalid"
        if not isinstance(actual_level, str) or not actual_level:
            return "sir_evidence_record_invalid"
        if validation.get("evidence_tier") is None:
            return "sir_evidence_tier_missing"
        if validation.get("evidence_tier") != actual_tier:
            return "sir_evidence_tier_mismatch"
        if validation.get("evidence_level") is None:
            return "sir_evidence_level_missing"
        if validation.get("evidence_level") != actual_level:
            return "sir_evidence_level_mismatch"

        expected_record_sha256 = validation.get("evidence_record_sha256")
        if not isinstance(expected_record_sha256, str) or not expected_record_sha256:
            return "sir_evidence_record_sha256_missing"
        if expected_record_sha256 != self._evidence_record_sha256(record):
            return "sir_evidence_record_sha256_mismatch"

        asset = model.get("asset") or {}
        artifact_sha256 = asset.get("sha256")
        if not isinstance(artifact_sha256, str) or not artifact_sha256:
            return "sir_evidence_artifact_sha256_missing"
        if validation.get("artifact_sha256") != artifact_sha256:
            return "sir_evidence_artifact_sha256_mismatch"
        return None

    def sir_evidence_record(self, model_id: str) -> dict[str, Any]:
        """Return a verified SIR evidence record or raise its fail-closed reason."""
        model = self.models.get(model_id)
        if model is None or not model_id.startswith("sir/"):
            raise ValueError("sir_model_not_declared")
        source_failure = self._sir_source_failure_reason()
        if source_failure is not None:
            raise ValueError(source_failure)
        contract_failure = self._sir_evidence_contract_failure_reason(model_id, model)
        if contract_failure is not None:
            raise ValueError(contract_failure)
        records, source_failure = self._load_sir_evidence_records()
        if source_failure is not None or records is None:
            raise ValueError(source_failure or "sir_evidence_source_invalid")
        evidence_key = str((model.get("validation") or {}).get("evidence_key"))
        return dict(records[evidence_key])

    def _repo_path(self, relative_path: str) -> Path:
        path = (self.repo_root / relative_path).resolve()
        if self.repo_root != path and self.repo_root not in path.parents:
            raise ValueError(f"catalog path escapes repository: {relative_path}")
        return path

    @staticmethod
    def _validation(model: dict[str, Any]) -> tuple[bool, str]:
        status = str((model.get("validation") or {}).get("status") or "unverified")
        return status == "validated", status

    @staticmethod
    def _numpy_major_compatibility_failure(dependencies: list[str]) -> str | None:
        """Return the fail-closed reason for an unsupported NumPy major.

        Current serialized production artifacts are only observed under NumPy 2.x.
        Their catalog contracts intentionally avoid pretending that every 2.x minor
        is byte-for-byte equivalent, but NumPy 3 must be rejected before joblib
        deserialization until a named compatibility profile validates it.
        """
        if "numpy" not in {dependency.lower() for dependency in dependencies}:
            return None
        try:
            actual_version = importlib.metadata.version("numpy")
            major = int(actual_version.split(".", 1)[0])
        except (importlib.metadata.PackageNotFoundError, TypeError, ValueError):
            return "dependency_version_mismatch:numpy"
        return "dependency_version_mismatch:numpy" if major >= 3 else None

    def _not_declared(
        self,
        reason_code: str,
        *,
        requested_model_id: str | None = None,
    ) -> ModelReadiness:
        return ModelReadiness(
            model_id=requested_model_id,
            declared=False,
            ready=False,
            validated=False,
            validation_status="unverified",
            reason_code=reason_code,
            execution=None,
            artifact_path=None,
            expected_sha256=None,
            catalog_digest=self.catalog_digest,
        )

    def _experimental_sidecar_contract(
        self,
        *,
        model_id: str | None,
        declared: bool,
        operational: bool,
        reason_code: str,
        execution: str | None,
        artifact_path: Path | None = None,
        expected_sha256: str | None = None,
        dependency_versions: dict[str, str] | None = None,
    ) -> ExperimentalSidecarContract:
        relative_path = None
        if artifact_path is not None:
            try:
                relative_path = str(artifact_path.relative_to(self.repo_root))
            except ValueError:
                relative_path = str(artifact_path)
        return ExperimentalSidecarContract(
            model_id=model_id,
            declared=declared,
            operational=operational,
            reason_code=reason_code,
            execution=execution,
            artifact_path=relative_path,
            expected_sha256=expected_sha256,
            dependency_versions=dict(dependency_versions or {}),
            catalog_digest=self.catalog_digest,
        )

    def inspect_experimental_sidecar(
        self,
        model_id: str,
        *,
        loader_path: Path | str | None = None,
    ) -> ExperimentalSidecarContract:
        """Verify one direct experimental sidecar without changing routing semantics.

        ``inspect`` intentionally reports every ``execution: experimental`` record as
        non-ready.  Direct calls such as the bounded iML1515 FBA simulation still need
        a separate fail-closed integrity gate: catalog identity, loader path, SHA-256,
        module availability, and every exact dependency version are checked here.
        A successful result never promotes the model to a routeable runtime predictor.
        """
        try:
            return self._inspect_experimental_sidecar(model_id, loader_path=loader_path)
        except Exception:  # noqa: BLE001 - direct sidecars must return a stable denial code
            return self._experimental_sidecar_contract(
                model_id=model_id,
                declared=False,
                operational=False,
                reason_code="sidecar_contract_exception",
                execution=None,
            )

    def _inspect_experimental_sidecar(
        self,
        model_id: str,
        *,
        loader_path: Path | str | None,
    ) -> ExperimentalSidecarContract:
        model = self.models.get(model_id)
        if model is None:
            return self._experimental_sidecar_contract(
                model_id=model_id,
                declared=False,
                operational=False,
                reason_code="model_not_declared",
                execution=None,
            )

        lifecycle = model.get("lifecycle") or {}
        runtime = model.get("runtime") or {}
        execution = str(model.get("execution") or "")
        declared = bool(lifecycle.get("declared"))
        dependency_versions = runtime.get("dependency_versions") or {}
        if not isinstance(dependency_versions, dict):
            dependency_versions = {}
        dependency_versions = {
            str(distribution): str(version)
            for distribution, version in dependency_versions.items()
            if isinstance(distribution, str) and isinstance(version, str)
        }

        if execution != "experimental":
            return self._experimental_sidecar_contract(
                model_id=model_id,
                declared=declared,
                operational=False,
                reason_code="execution_not_experimental",
                execution=execution,
                dependency_versions=dependency_versions,
            )
        if not declared:
            return self._experimental_sidecar_contract(
                model_id=model_id,
                declared=False,
                operational=False,
                reason_code="sidecar_not_declared",
                execution=execution,
                dependency_versions=dependency_versions,
            )
        if bool(lifecycle.get("routeable_when_ready")):
            return self._experimental_sidecar_contract(
                model_id=model_id,
                declared=True,
                operational=False,
                reason_code="experimental_sidecar_must_not_be_routeable",
                execution=execution,
                dependency_versions=dependency_versions,
            )

        asset = model.get("asset") or {}
        asset_path_value = asset.get("path")
        expected_sha256 = asset.get("sha256")
        if not isinstance(asset_path_value, str) or not isinstance(expected_sha256, str):
            return self._experimental_sidecar_contract(
                model_id=model_id,
                declared=True,
                operational=False,
                reason_code="artifact_contract_invalid",
                execution=execution,
                dependency_versions=dependency_versions,
            )
        try:
            artifact_path = self._repo_path(asset_path_value)
        except (OSError, ValueError):
            return self._experimental_sidecar_contract(
                model_id=model_id,
                declared=True,
                operational=False,
                reason_code="artifact_path_invalid",
                execution=execution,
                expected_sha256=expected_sha256,
                dependency_versions=dependency_versions,
            )
        if loader_path is not None:
            try:
                observed_loader_path = Path(loader_path).resolve()
            except OSError:
                return self._experimental_sidecar_contract(
                    model_id=model_id,
                    declared=True,
                    operational=False,
                    reason_code="loader_path_invalid",
                    execution=execution,
                    artifact_path=artifact_path,
                    expected_sha256=expected_sha256,
                    dependency_versions=dependency_versions,
                )
            if observed_loader_path != artifact_path:
                return self._experimental_sidecar_contract(
                    model_id=model_id,
                    declared=True,
                    operational=False,
                    reason_code="artifact_path_mismatch",
                    execution=execution,
                    artifact_path=artifact_path,
                    expected_sha256=expected_sha256,
                    dependency_versions=dependency_versions,
                )
        if not artifact_path.is_file():
            return self._experimental_sidecar_contract(
                model_id=model_id,
                declared=True,
                operational=False,
                reason_code="artifact_missing",
                execution=execution,
                artifact_path=artifact_path,
                expected_sha256=expected_sha256,
                dependency_versions=dependency_versions,
            )
        if len(expected_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in expected_sha256
        ):
            return self._experimental_sidecar_contract(
                model_id=model_id,
                declared=True,
                operational=False,
                reason_code="artifact_sha256_contract_invalid",
                execution=execution,
                artifact_path=artifact_path,
                expected_sha256=expected_sha256,
                dependency_versions=dependency_versions,
            )
        try:
            actual_sha256 = sha256_file(artifact_path)
        except OSError:
            return self._experimental_sidecar_contract(
                model_id=model_id,
                declared=True,
                operational=False,
                reason_code="artifact_read_failed",
                execution=execution,
                artifact_path=artifact_path,
                expected_sha256=expected_sha256,
                dependency_versions=dependency_versions,
            )
        if actual_sha256 != expected_sha256:
            return self._experimental_sidecar_contract(
                model_id=model_id,
                declared=True,
                operational=False,
                reason_code="artifact_sha256_mismatch",
                execution=execution,
                artifact_path=artifact_path,
                expected_sha256=expected_sha256,
                dependency_versions=dependency_versions,
            )

        dependencies = runtime.get("dependencies") or []
        if not isinstance(dependencies, list) or not all(
            isinstance(module_name, str) and module_name for module_name in dependencies
        ):
            return self._experimental_sidecar_contract(
                model_id=model_id,
                declared=True,
                operational=False,
                reason_code="dependency_contract_invalid",
                execution=execution,
                artifact_path=artifact_path,
                expected_sha256=expected_sha256,
                dependency_versions=dependency_versions,
            )
        missing_version_contract = sorted(set(dependencies) - set(dependency_versions))
        if missing_version_contract:
            return self._experimental_sidecar_contract(
                model_id=model_id,
                declared=True,
                operational=False,
                reason_code=(
                    "dependency_version_contract_incomplete:"
                    + ",".join(missing_version_contract)
                ),
                execution=execution,
                artifact_path=artifact_path,
                expected_sha256=expected_sha256,
                dependency_versions=dependency_versions,
            )
        missing_modules = []
        for module_name in dependencies:
            try:
                installed = importlib.util.find_spec(module_name) is not None
            except (ImportError, AttributeError, ValueError):
                installed = False
            if not installed:
                missing_modules.append(module_name)
        if missing_modules:
            return self._experimental_sidecar_contract(
                model_id=model_id,
                declared=True,
                operational=False,
                reason_code=f"dependency_missing:{','.join(sorted(missing_modules))}",
                execution=execution,
                artifact_path=artifact_path,
                expected_sha256=expected_sha256,
                dependency_versions=dependency_versions,
            )
        mismatched_versions = []
        for distribution, expected_version in sorted(dependency_versions.items()):
            try:
                actual_version = importlib.metadata.version(distribution)
            except importlib.metadata.PackageNotFoundError:
                actual_version = None
            except Exception:  # noqa: BLE001 - a bad metadata provider must fail closed
                actual_version = None
            if actual_version != expected_version:
                mismatched_versions.append(distribution)
        if mismatched_versions:
            return self._experimental_sidecar_contract(
                model_id=model_id,
                declared=True,
                operational=False,
                reason_code=(
                    "dependency_version_mismatch:" + ",".join(sorted(mismatched_versions))
                ),
                execution=execution,
                artifact_path=artifact_path,
                expected_sha256=expected_sha256,
                dependency_versions=dependency_versions,
            )
        return self._experimental_sidecar_contract(
            model_id=model_id,
            declared=True,
            operational=True,
            reason_code="sidecar_contract_verified",
            execution=execution,
            artifact_path=artifact_path,
            expected_sha256=expected_sha256,
            dependency_versions=dependency_versions,
        )

    def inspect_sir(self, species: str, drug: str, *, probe: bool = False) -> ModelReadiness:
        source_failure = self._sir_source_failure_reason()
        if source_failure is not None:
            return ModelReadiness(
                model_id=f"sir/{species}/{canonical_drug_id(drug)}",
                # The catalog still declares the unit; the old source input has changed
                # underneath it, so it is deliberately no longer safe to execute.
                declared=f"sir/{species}/{canonical_drug_id(drug)}" in self.models,
                ready=False,
                validated=False,
                validation_status="unverified",
                reason_code=source_failure,
                execution="predict",
                artifact_path=None,
                expected_sha256=None,
                catalog_digest=self.catalog_digest,
            )
        model_id = f"sir/{species}/{canonical_drug_id(drug)}"
        if model_id not in self.models:
            return self._not_declared("sir_model_not_declared", requested_model_id=model_id)
        model = self.models[model_id]
        evidence_failure = self._sir_evidence_contract_failure_reason(model_id, model)
        if evidence_failure is not None:
            return ModelReadiness(
                model_id=model_id,
                declared=bool((model.get("lifecycle") or {}).get("declared")),
                ready=False,
                validated=False,
                validation_status=str(
                    (model.get("validation") or {}).get("status") or "unverified"
                ),
                reason_code=evidence_failure,
                execution=str(model.get("execution") or "predict"),
                artifact_path=None,
                expected_sha256=None,
                catalog_digest=self.catalog_digest,
            )
        return self.inspect(model_id, probe=probe)

    def inspect(self, model_id: str, *, probe: bool = False) -> ModelReadiness:
        # ``load_ready_model`` uses this generic entry point.  Keep the generated
        # catalog and its SIR source manifest coupled here too, rather than allowing
        # that loader path to bypass the exact-source integrity check.
        source_failure = self._sir_source_failure_reason() if model_id.startswith("sir/") else None
        if source_failure is not None:
            model = self.models.get(model_id)
            return ModelReadiness(
                model_id=model_id,
                declared=bool((model or {}).get("lifecycle", {}).get("declared")),
                ready=False,
                validated=False,
                validation_status=str(
                    (model or {}).get("validation", {}).get("status") or "unverified"
                ),
                reason_code=source_failure,
                execution=str((model or {}).get("execution") or "predict"),
                artifact_path=None,
                expected_sha256=None,
                catalog_digest=self.catalog_digest,
            )
        model = self.models.get(model_id)
        if model is None:
            return self._not_declared("model_not_declared", requested_model_id=model_id)
        if model_id.startswith("sir/"):
            evidence_failure = self._sir_evidence_contract_failure_reason(model_id, model)
            if evidence_failure is not None:
                return ModelReadiness(
                    model_id=model_id,
                    declared=bool((model.get("lifecycle") or {}).get("declared")),
                    ready=False,
                    validated=False,
                    validation_status=str(
                        (model.get("validation") or {}).get("status") or "unverified"
                    ),
                    reason_code=evidence_failure,
                    execution=str(model.get("execution") or "predict"),
                    artifact_path=None,
                    expected_sha256=None,
                    catalog_digest=self.catalog_digest,
                )
        validated, validation_status = self._validation(model)
        execution = str(model.get("execution") or "")
        lifecycle = model["lifecycle"]
        if execution != "predict":
            return ModelReadiness(
                model_id=model_id,
                declared=bool(lifecycle.get("declared")),
                ready=False,
                validated=False,
                validation_status=validation_status,
                reason_code=str(lifecycle.get("reason_code") or f"{execution}_not_routeable"),
                execution=execution,
                artifact_path=None,
                expected_sha256=None,
                catalog_digest=self.catalog_digest,
            )

        asset = model["asset"]
        artifact_path = self._repo_path(str(asset["path"]))
        expected_sha = str(asset["sha256"])
        if not artifact_path.is_file():
            return self._readiness(
                model_id,
                False,
                validated,
                validation_status,
                "artifact_missing",
                model,
                artifact_path,
                expected_sha,
            )
        stat = artifact_path.stat()
        actual_sha = _sha256_with_stat(
            str(artifact_path),
            stat.st_dev,
            stat.st_ino,
            stat.st_size,
            stat.st_mtime_ns,
            stat.st_ctime_ns,
        )
        if actual_sha != expected_sha:
            return self._readiness(
                model_id,
                False,
                validated,
                validation_status,
                "artifact_sha256_mismatch",
                model,
                artifact_path,
                expected_sha,
            )
        dependencies = list((model.get("runtime") or {}).get("dependencies") or [])
        missing = [name for name in dependencies if importlib.util.find_spec(name) is None]
        if missing:
            return self._readiness(
                model_id,
                False,
                validated,
                validation_status,
                f"dependency_missing:{','.join(sorted(missing))}",
                model,
                artifact_path,
                expected_sha,
            )
        numpy_failure = self._numpy_major_compatibility_failure(dependencies)
        if numpy_failure is not None:
            return self._readiness(
                model_id,
                False,
                validated,
                validation_status,
                numpy_failure,
                model,
                artifact_path,
                expected_sha,
            )
        version_contract = dict((model.get("runtime") or {}).get("dependency_versions") or {})
        mismatched = []
        for distribution, expected_version in sorted(version_contract.items()):
            try:
                actual_version = importlib.metadata.version(distribution)
            except importlib.metadata.PackageNotFoundError:
                actual_version = None
            if actual_version != expected_version:
                mismatched.append(distribution)
        if mismatched:
            return self._readiness(
                model_id,
                False,
                validated,
                validation_status,
                f"dependency_version_mismatch:{','.join(mismatched)}",
                model,
                artifact_path,
                expected_sha,
            )
        if probe:
            try:
                self._probe_model(model, artifact_path, actual_sha)
            except Exception:  # pragma: no cover - intentionally hide adapter details from API
                return self._readiness(
                    model_id,
                    False,
                    validated,
                    validation_status,
                    "artifact_probe_failed",
                    model,
                    artifact_path,
                    expected_sha,
                )
        return self._readiness(
            model_id,
            True,
            validated,
            validation_status,
            "ready",
            model,
            artifact_path,
            expected_sha,
        )

    def load_ready_model(self, model_id: str) -> Any:
        """Return a verified, cached adapter object or raise a machine-readable ValueError."""
        readiness = self.inspect(model_id, probe=True)
        if not readiness.ready:
            raise ValueError(readiness.reason_code)
        model = self.models[model_id]
        path = self._repo_path(str(model["asset"]["path"]))
        return _load_adapter(
            str(path),
            str(model["runtime"]["adapter"]),
            str(readiness.expected_sha256),
        )

    def inspect_request_capabilities(
        self,
        *,
        species: str,
        drug: str,
        output_kinds: list[str],
        probe: bool = False,
    ) -> list[ModelReadiness]:
        """Return exact model/stub states for the caller's requested outputs.

        This is deliberately a presentation/provenance helper, not a second router:
        callers must still use readiness-aware registry routing.  The map keeps report
        and API lifecycle states rooted in this catalog rather than evidence tiers or
        broad species-level registry declarations.
        """
        statuses: list[ModelReadiness] = []
        for output_kind in sorted(set(output_kinds)):
            if output_kind == "sir_class":
                status = self.inspect_sir(species, drug, probe=probe)
            elif output_kind == "sm_activity":
                status = self.inspect(f"activity/{species}/small_molecule", probe=probe)
            elif output_kind == "peptide_activity":
                status = self.inspect(f"activity/{species}/peptide", probe=probe)
            elif output_kind == "mic_scalar":
                status = self.inspect("stub/mic_regressor", probe=False)
            elif output_kind == "mechanism_state":
                experimental_id = f"mechanism/{species}/iml1515"
                status = (
                    self.inspect(experimental_id, probe=False)
                    if experimental_id in self.models
                    else self.inspect("stub/mechanism_state", probe=False)
                )
            else:
                status = self._not_declared(
                    "output_kind_not_declared",
                    requested_model_id=f"unknown/{species}/{output_kind}",
                )
            statuses.append(status)
        return statuses

    @staticmethod
    def _probe_model(model: dict[str, Any], path: Path, artifact_sha256: str) -> None:
        adapter = str(model["runtime"]["adapter"])
        artifact = _load_adapter(str(path), adapter, artifact_sha256)
        if adapter == "genotype_to_sir":
            feature_names = list(getattr(artifact, "feature_names", None) or [])
            if not feature_names or len(feature_names) != len(set(feature_names)):
                raise ValueError("sir_artifact_feature_schema_invalid")
            probability = float(artifact.predict_proba_r(np.zeros((1, len(feature_names))))[0])
            if not 0.0 <= probability <= 1.0:
                raise ValueError("sir_artifact_probability_invalid")
        elif adapter == "small_molecule":
            if getattr(artifact, "_rf", None) is None or not getattr(artifact, "train_size", 0):
                raise ValueError("sm_activity_artifact_schema_invalid")
        elif adapter == "peptide":
            if getattr(artifact, "_rf", None) is None or not getattr(artifact, "train_size", 0):
                raise ValueError("peptide_activity_artifact_schema_invalid")

    def _readiness(
        self,
        model_id: str,
        ready: bool,
        validated: bool,
        validation_status: str,
        reason_code: str,
        model: dict[str, Any],
        artifact_path: Path,
        expected_sha: str,
    ) -> ModelReadiness:
        return ModelReadiness(
            model_id=model_id,
            declared=bool(model["lifecycle"].get("declared")),
            ready=ready,
            validated=validated and ready,
            validation_status=validation_status,
            reason_code=reason_code,
            execution=str(model.get("execution") or ""),
            artifact_path=str(artifact_path.relative_to(self.repo_root)),
            expected_sha256=expected_sha,
            catalog_digest=self.catalog_digest,
        )

    def lifecycle_summary(self) -> dict[str, Any]:
        """Static catalog truth; expensive file probes remain request-scoped and explicit."""
        models = list(self.models.values())
        return {
            "catalog_digest": self.catalog_digest,
            "declared": len(models),
            "routeable_when_ready": sum(
                bool((model.get("lifecycle") or {}).get("routeable_when_ready")) for model in models
            ),
            "validation_status": {
                status: sum(
                    (model.get("validation") or {}).get("status") == status
                    for model in models
                )
                for status in ("validated", "limited", "unverified")
            },
            "on_demand_readiness": True,
            "orphaned_evidence": list(self.doc.get("orphaned_evidence") or []),
        }


RUNTIME_MODEL_EXECUTION_CONTEXT_SCHEMA = "mdr-runtime-model-context-v2"


def _readiness_receipt(status: ModelReadiness) -> dict[str, Any]:
    """Stable, non-biological facts used to bind a request to model readiness."""
    return {
        "model_id": status.model_id,
        "declared": status.declared,
        "ready": status.ready,
        "reason_code": status.reason_code,
        "execution": status.execution,
        "artifact_path": status.artifact_path,
        "expected_sha256": status.expected_sha256,
        "catalog_digest": status.catalog_digest,
    }


@dataclass(frozen=True)
class RuntimeModelExecutionContext:
    """One request's catalog/readiness observation.

    This is intentionally opaque runtime state rather than a replacement for the
    public model lifecycle API.  It captures only the model units requested by a
    caller, then lets route, provenance and adapter loading share the same
    manifest.  ``load_ready_model`` rechecks its selected receipt immediately
    before use, so a drift after cache-key capture fails closed instead of mixing
    the cache namespace from one artifact state with an adapter from another.
    Eligible direct experimental sidecars are captured separately because they
    are intentionally not routeable ``ModelReadiness`` entries but can still
    contribute a bounded mechanism result to an ``sm_activity`` request.
    """

    manifest: RuntimeModelManifest
    species: str
    drug: str
    output_kinds: tuple[str, ...]
    requested_capabilities: tuple[ModelReadiness, ...]
    experimental_sidecars: tuple[ExperimentalSidecarContract, ...]
    public_identity: dict[str, Any]

    @property
    def catalog_digest(self) -> str:
        return self.manifest.catalog_digest

    @property
    def doc(self) -> dict[str, Any]:
        return self.manifest.doc

    @property
    def lifecycle_identity(self) -> dict[str, Any]:
        return {
            "catalog_version": self.manifest.doc.get("catalog_version"),
            "catalog_digest": self.manifest.catalog_digest,
        }

    def _selected_status(self, model_id: str) -> ModelReadiness | None:
        for status in self.requested_capabilities:
            if status.model_id == model_id:
                return status
        return None

    def inspect_sir(self, species: str, drug: str, *, probe: bool = False) -> ModelReadiness:
        del probe
        model_id = f"sir/{species}/{canonical_drug_id(drug)}"
        return self._selected_status(model_id) or self.manifest.inspect_sir(
            species, drug, probe=True
        )

    def inspect(self, model_id: str, *, probe: bool = False) -> ModelReadiness:
        del probe
        return self._selected_status(model_id) or self.manifest.inspect(model_id, probe=True)

    def inspect_request_capabilities(
        self,
        *,
        species: str,
        drug: str,
        output_kinds: list[str],
        probe: bool = False,
    ) -> list[ModelReadiness]:
        del probe
        # The core calls this with the same normalized request used at capture.
        # For another capability query, fall back to a live manifest inspection
        # rather than accidentally presenting this request's receipts as another.
        if (
            species == self.species
            and drug == self.drug
            and tuple(sorted(set(output_kinds))) == self.output_kinds
        ):
            return list(self.requested_capabilities)
        return self.manifest.inspect_request_capabilities(
            species=species,
            drug=drug,
            output_kinds=output_kinds,
            probe=True,
        )

    def assert_current(self) -> None:
        """Fail closed if the captured catalog or selected readiness receipts drift.

        This is intentionally a cheap cache-return guard: it re-reads the catalog
        bytes and performs ``probe=False`` readiness checks, which still verify
        source/artifact/dependency facts without deserializing every selected
        adapter again.  It is not an immutable release or an atomic filesystem
        snapshot; ``load_ready_model`` retains its probe-time recheck immediately
        before adapter reuse/load.
        """
        try:
            catalog_bytes = self.manifest.path.read_bytes()
        except OSError as exc:
            raise ValueError("request_artifact_integrity_drift") from exc
        if catalog_bytes != self.manifest._catalog_bytes:
            raise ValueError("request_artifact_integrity_drift")
        current = self.manifest.inspect_request_capabilities(
            species=self.species,
            drug=self.drug,
            output_kinds=list(self.output_kinds),
            probe=False,
        )
        captured_receipts = tuple(
            _readiness_receipt(status) for status in self.requested_capabilities
        )
        current_receipts = tuple(_readiness_receipt(status) for status in current)
        if current_receipts != captured_receipts:
            raise ValueError("request_artifact_integrity_drift")
        captured_sidecars = tuple(contract.as_dict() for contract in self.experimental_sidecars)
        current_sidecars = []
        for contract in self.experimental_sidecars:
            if not contract.model_id:
                raise ValueError("request_artifact_integrity_drift")
            current_sidecars.append(
                self.manifest.inspect_experimental_sidecar(contract.model_id).as_dict()
            )
        if tuple(current_sidecars) != captured_sidecars:
            raise ValueError("request_artifact_integrity_drift")

    def load_ready_model(self, model_id: str) -> Any:
        """Recheck the captured selected unit just before adapter reuse/load."""
        self.assert_current()
        selected = self._selected_status(model_id)
        if selected is not None:
            current = self.manifest.inspect(model_id, probe=True)
            if _readiness_receipt(current) != _readiness_receipt(selected):
                raise ValueError("request_artifact_integrity_drift")
        return self.manifest.load_ready_model(model_id)


def capture_runtime_model_execution_context(
    *,
    species: str,
    drug: str,
    output_kinds: list[str],
    catalog_path: Path | str | None = None,
    repo_root: Path | str | None = None,
) -> RuntimeModelExecutionContext:
    """Capture model catalog bytes and selected readiness before a cache lookup.

    ``probe=True`` verifies the selected adapter/schema but may reuse the
    SHA-keyed adapter cache; this function does not claim a fresh joblib
    deserialization on every request.  Its identity intentionally excludes raw
    biological request inputs such as AMR profile, SMILES and sequence.
    """
    path = Path(catalog_path or DEFAULT_CATALOG).resolve()
    catalog_bytes = path.read_bytes()
    manifest = RuntimeModelManifest(
        path,
        repo_root=repo_root,
        catalog_bytes=catalog_bytes,
    )
    normalized_kinds = tuple(sorted(set(output_kinds)))
    statuses = tuple(
        manifest.inspect_request_capabilities(
            species=species,
            drug=drug,
            output_kinds=list(normalized_kinds),
            probe=True,
        )
    )
    # iML1515 is intentionally experimental/non-routeable, so it must not be
    # represented as a ready normal predictor.  It can still run as the bounded
    # mechanism sidecar of an EC small-molecule request.  Bind its contract before
    # a cache lookup so artifact/dependency drift cannot replay an earlier FBA
    # result under a route-only receipt.
    experimental_sidecars: tuple[ExperimentalSidecarContract, ...] = ()
    if "sm_activity" in normalized_kinds and drug:
        sidecar_model_id = f"mechanism/{species}/iml1515"
        if sidecar_model_id in manifest.models:
            experimental_sidecars = (
                manifest.inspect_experimental_sidecar(sidecar_model_id),
            )
    sidecar_receipts = [contract.as_dict() for contract in experimental_sidecars]
    receipt_payload = {
        "schema_version": RUNTIME_MODEL_EXECUTION_CONTEXT_SCHEMA,
        "catalog_version": manifest.doc.get("catalog_version"),
        "catalog_digest": manifest.catalog_digest,
        "requested": [_readiness_receipt(status) for status in statuses],
        "experimental_sidecars": sidecar_receipts,
    }
    canonical = json.dumps(
        receipt_payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    public_identity = {
        "schema_version": RUNTIME_MODEL_EXECUTION_CONTEXT_SCHEMA,
        "catalog_version": manifest.doc.get("catalog_version"),
        "catalog_digest": manifest.catalog_digest,
        "requested_readiness_digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "requested_capability_count": len(statuses),
        "experimental_sidecar_count": len(experimental_sidecars),
        "experimental_sidecars": sidecar_receipts,
    }
    return RuntimeModelExecutionContext(
        manifest=manifest,
        species=species,
        drug=drug,
        output_kinds=normalized_kinds,
        requested_capabilities=statuses,
        experimental_sidecars=experimental_sidecars,
        public_identity=public_identity,
    )


@lru_cache(maxsize=8)
def _get_runtime_manifest_for_bytes(
    catalog_path: str,
    catalog_bytes: bytes,
) -> RuntimeModelManifest:
    """Reuse only an unchanged catalog document, never a path-only singleton."""
    return RuntimeModelManifest(Path(catalog_path), catalog_bytes=catalog_bytes)


def get_runtime_manifest() -> RuntimeModelManifest:
    """Return the manifest for the catalog bytes observed by this caller.

    Reading the catalog digest on every call is intentionally cheap relative to
    prediction and prevents a long-lived ASGI worker from pinning a catalog solely
    because its pathname has not changed.  The helper may reuse an object only
    when its exact YAML bytes are identical.
    """
    path = Path(DEFAULT_CATALOG).resolve()
    return _get_runtime_manifest_for_bytes(str(path), path.read_bytes())


# Retain the standard cache-control affordance used by existing test fixtures,
# while making the public resolver content-sensitive rather than a permanent
# path-only singleton.
get_runtime_manifest.cache_clear = _get_runtime_manifest_for_bytes.cache_clear  # type: ignore[attr-defined]
