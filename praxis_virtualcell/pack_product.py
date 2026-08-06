"""Product-facing VirtualCellPack inspection, indexing, and execution helpers."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.core.config import RuntimeConfig
from praxis_virtualcell.core.exceptions import InputValidationError
from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.core.request_v2 import (
    VirtualCellRequestV2,
    legacy_request_to_v2,
)
from praxis_virtualcell.data_packs.errors import (
    PackRegistryError,
    VirtualCellPackError,
)
from praxis_virtualcell.data_packs.manifest import PackManifest, load_manifest
from praxis_virtualcell.data_packs.registry import PackRegistry
from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.capability_registry import (
    CapabilityRegistry,
    EnvironmentSnapshot,
    ExecutionPlanV2,
)
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
from praxis_virtualcell.model_zoo.registry_v2 import public_model_version
from praxis_virtualcell.virtual_experiment import (
    VirtualExperimentContractError,
    compile_virtual_experiment,
)
from praxis_virtualcell.workflows.run_virtualcell_query import (
    run_query,
    validate_candidate,
)

_INDEX_SCHEMA_V1 = "vc.pack-index.v1"
_INDEX_SCHEMA = "vc.pack-index.v2"
_INDEX_ENTRY_KEYS_V1 = {
    "pack_id",
    "pack_version",
    "pack_fingerprint",
    "root",
}
_INDEX_ENTRY_KEYS = {
    *_INDEX_ENTRY_KEYS_V1,
    "factory_registration_fingerprint",
    "factory_store_root",
}


class PackProductError(ValueError):
    """Base error for product Pack surfaces."""


class PackNotFound(PackProductError):
    pass


class PackUnavailable(PackProductError):
    pass


class PackIndexError(PackProductError):
    pass


def builtin_pack_roots() -> dict[str, Path]:
    root = Path(__file__).resolve().parent / "example_packs"
    return {
        species: root / species
        for species in ("human", "mouse", "bacteria")
    }


def _modalities(manifest: PackManifest) -> list[dict[str, str]]:
    if manifest.multiomics is not None:
        return [
            {
                "name": item.modality.name,
                "ontology_id": item.modality.ontology_id,
            }
            for item in manifest.multiomics.modalities
        ]
    assert manifest.modality is not None
    return [
        {
            "name": manifest.modality.name,
            "ontology_id": manifest.modality.ontology_id,
        }
    ]


def _feature_namespaces(manifest: PackManifest) -> list[dict[str, str]]:
    if manifest.multiomics is not None:
        return [
            {
                "name": item.feature_namespace.name,
                "version": item.feature_namespace.version,
                "id_format": item.feature_semantics.id_format,
            }
            for item in manifest.multiomics.modalities
        ]
    assert manifest.feature_namespace is not None
    id_format = (
        manifest.feature_semantics.id_format
        if manifest.feature_semantics is not None
        else {
            "EnsemblGene": "ensembl_gene",
            "NCBIGene": "ncbi_gene_curie",
            "UniProtKB": "uniprot_protein",
        }.get(manifest.feature_namespace.name, "unspecified")
    )
    return [
        {
            "name": manifest.feature_namespace.name,
            "version": manifest.feature_namespace.version,
            "id_format": id_format,
        }
    ]


def _summary(
    manifest: PackManifest,
    *,
    source: str,
    validation_status: str,
    pack_valid: bool | None,
    reasons: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "vc.pack-record.v1",
        "pack_id": manifest.pack_id,
        "pack_version": manifest.pack_version,
        "pack_fingerprint": manifest.fingerprint(),
        "manifest_schema_version": manifest.schema_version,
        "taxon": {
            "ontology_id": manifest.taxon.ontology_id,
            "scientific_name": manifest.taxon.scientific_name,
        },
        "assembly": {
            "name": manifest.assembly.name,
            "accession": manifest.assembly.accession,
        },
        "modalities": _modalities(manifest),
        "feature_namespaces": _feature_namespaces(manifest),
        "asset_count": len(manifest.assets),
        "source": source,
        "validation_status": validation_status,
        "pack_valid": pack_valid,
        "model_compatible": None,
        "scientifically_validated": False,
        "reasons": list(reasons or []),
    }


def _redacted_reason(exc: Exception, root: Path) -> str:
    return str(exc).replace(str(root), "<pack-root>")


def inspect_pack(pack_root: str | Path) -> dict[str, Any]:
    root = Path(pack_root).resolve()
    manifest = load_manifest(root / "manifest.yaml")
    return _summary(
        manifest,
        source="path",
        validation_status="unchecked",
        pack_valid=None,
    )


def validate_pack_summary(
    pack_root: str | Path,
    *,
    source: str = "path",
) -> dict[str, Any]:
    root = Path(pack_root).resolve()
    manifest = load_manifest(root / "manifest.yaml")
    try:
        validated = PackRegistry().register(root)
    except VirtualCellPackError as exc:
        return _summary(
            manifest,
            source=source,
            validation_status="invalid",
            pack_valid=False,
            reasons=[_redacted_reason(exc, root)],
        )
    return _summary(
        validated,
        source=source,
        validation_status="valid",
        pack_valid=True,
    )


def _reject_duplicate_json(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise PackIndexError(f"duplicate Pack index key: {key}")
        value[key] = item
    return value


def _valid_index_entry(value: Any, *, schema_version: str) -> dict[str, str | None]:
    expected_fields = (
        _INDEX_ENTRY_KEYS_V1
        if schema_version == _INDEX_SCHEMA_V1
        else _INDEX_ENTRY_KEYS
    )
    if not isinstance(value, dict) or set(value) != expected_fields:
        raise PackIndexError("Pack index entry has invalid fields")
    entry: dict[str, str | None] = {}
    for field in _INDEX_ENTRY_KEYS_V1:
        item = value[field]
        if not isinstance(item, str) or not item or item.strip() != item:
            raise PackIndexError(f"Pack index {field} must be a non-empty string")
        entry[field] = item
    registration_fingerprint = value.get("factory_registration_fingerprint")
    if registration_fingerprint is not None and (
        not isinstance(registration_fingerprint, str)
        or len(registration_fingerprint) != 64
        or any(char not in "0123456789abcdef" for char in registration_fingerprint)
    ):
        raise PackIndexError(
            "Pack index factory registration fingerprint must be lowercase SHA-256 or null"
        )
    entry["factory_registration_fingerprint"] = registration_fingerprint
    factory_store_root = value.get("factory_store_root")
    if (registration_fingerprint is None) != (factory_store_root is None):
        raise PackIndexError(
            "Pack index factory registration and store identities must be present together"
        )
    if factory_store_root is not None:
        if not isinstance(factory_store_root, str) or not factory_store_root:
            raise PackIndexError("Pack index factory store root must be a non-empty string")
        store_root = Path(factory_store_root)
        if not store_root.is_absolute() or str(store_root.resolve()) != factory_store_root:
            raise PackIndexError("Pack index factory store root must be canonical and absolute")
    entry["factory_store_root"] = factory_store_root
    if len(entry["pack_fingerprint"]) != 64 or any(
        char not in "0123456789abcdef"
        for char in entry["pack_fingerprint"]
    ):
        raise PackIndexError("Pack index fingerprint must be lowercase SHA-256")
    root = Path(entry["root"])
    if not root.is_absolute() or str(root.resolve()) != entry["root"]:
        raise PackIndexError("Pack index root must be a canonical absolute path")
    return entry


class PackIndex:
    """Durable local path index; every read revalidates Pack bytes."""

    def __init__(
        self,
        index_path: str | Path | None = None,
        *,
        include_builtins: bool = True,
    ) -> None:
        configured = index_path or os.environ.get("PRAXIS_VC_PACK_INDEX")
        self.explicit_index_path = index_path is not None
        self.path = Path(
            configured
            or Path.home()
            / ".local"
            / "share"
            / "praxis-virtualcell"
            / "pack-index.json"
        ).expanduser()
        self.include_builtins = include_builtins

    def _read(self) -> list[dict[str, str | None]]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(
                self.path.read_text(encoding="utf-8"),
                object_pairs_hook=_reject_duplicate_json,
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise PackIndexError(f"cannot read Pack index: {exc}") from exc
        if (
            not isinstance(raw, dict)
            or set(raw) != {"schema_version", "packs"}
            or raw["schema_version"] not in {_INDEX_SCHEMA_V1, _INDEX_SCHEMA}
            or not isinstance(raw["packs"], list)
        ):
            raise PackIndexError("invalid Pack index contract")
        entries = [
            _valid_index_entry(item, schema_version=raw["schema_version"])
            for item in raw["packs"]
        ]
        keys = [(item["pack_id"], item["pack_version"]) for item in entries]
        roots = [item["root"] for item in entries]
        if len(set(keys)) != len(keys) or len(set(roots)) != len(roots):
            raise PackIndexError("Pack index contains duplicate identity or root")
        return entries

    def _write(self, entries: list[dict[str, str | None]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {
                "schema_version": _INDEX_SCHEMA,
                "packs": sorted(
                    entries,
                    key=lambda item: (
                        item["pack_id"],
                        item["pack_version"],
                    ),
                ),
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n"
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=self.path.parent,
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        finally:
            try:
                Path(temporary).unlink()
            except FileNotFoundError:
                pass

    def _roots(self) -> list[tuple[str, Path, dict[str, str | None] | None]]:
        roots: list[tuple[str, Path, dict[str, str | None] | None]] = []
        if self.include_builtins:
            roots.extend(
                ("builtin", root, None)
                for root in builtin_pack_roots().values()
            )
        roots.extend(
            ("registered", Path(entry["root"]), entry)
            for entry in self._read()
        )
        return roots

    @staticmethod
    def _record(
        source: str,
        root: Path,
        expected: dict[str, str | None] | None,
    ) -> dict[str, Any]:
        try:
            record = validate_pack_summary(root, source=source)
        except (OSError, VirtualCellPackError) as exc:
            if expected is None:
                raise PackIndexError(f"cannot inspect built-in Pack {root}: {exc}") from exc
            return {
                "schema_version": "vc.pack-record.v1",
                "pack_id": expected["pack_id"],
                "pack_version": expected["pack_version"],
                "pack_fingerprint": expected["pack_fingerprint"],
                "manifest_schema_version": None,
                "taxon": None,
                "assembly": None,
                "modalities": [],
                "feature_namespaces": [],
                "asset_count": None,
                "source": source,
                "validation_status": "invalid",
                "pack_valid": False,
                "model_compatible": None,
                "scientifically_validated": False,
                "reasons": [_redacted_reason(exc, root)],
            }
        if expected is not None:
            mismatches = [
                field
                for field in (
                    "pack_id",
                    "pack_version",
                    "pack_fingerprint",
                )
                if record[field] != expected[field]
            ]
            if mismatches:
                record["validation_status"] = "invalid"
                record["pack_valid"] = False
                record["reasons"].append(
                    f"registered Pack identity changed: {mismatches}"
                )
            registration_fingerprint = expected[
                "factory_registration_fingerprint"
            ]
            if registration_fingerprint is not None:
                try:
                    from praxis_virtualcell.pack_factory import (
                        PackFactoryStore,
                    )

                    store_root = expected["factory_store_root"]
                    assert isinstance(store_root, str)
                    store = PackFactoryStore.open(Path(store_root))
                    registration = store.verify_registration(
                        registration_fingerprint
                    )
                    if (
                        registration.pack_id != expected["pack_id"]
                        or registration.pack_version != expected["pack_version"]
                        or registration.pack_fingerprint
                        != expected["pack_fingerprint"]
                    ):
                        raise PackIndexError(
                            "factory registration identity does not match index"
                        )
                except (AssertionError, OSError, ValueError):
                    record["validation_status"] = "invalid"
                    record["pack_valid"] = False
                    record["reasons"].append(
                        "factory registration commit is missing or invalid"
                    )
        return record

    def list_records(self) -> list[dict[str, Any]]:
        records = [
            self._record(source, root, expected)
            for source, root, expected in self._roots()
        ]
        keys = [
            (record["pack_id"], record["pack_version"])
            for record in records
        ]
        if len(set(keys)) != len(keys):
            raise PackIndexError("built-in and registered Pack identities conflict")
        return sorted(
            records,
            key=lambda item: (item["pack_id"], item["pack_version"]),
        )

    def get_record(self, pack_id: str, pack_version: str) -> dict[str, Any]:
        for record in self.list_records():
            if (
                record["pack_id"] == pack_id
                and record["pack_version"] == pack_version
            ):
                return record
        raise PackNotFound(f"unknown Pack: {(pack_id, pack_version)}")

    def _root_for(self, pack_id: str, pack_version: str) -> Path:
        for source, root, expected in self._roots():
            record = self._record(source, root, expected)
            if (
                record["pack_id"] == pack_id
                and record["pack_version"] == pack_version
            ):
                if not record["pack_valid"]:
                    raise PackUnavailable("; ".join(record["reasons"]))
                return root.resolve()
        raise PackNotFound(f"unknown Pack: {(pack_id, pack_version)}")

    def registry_for(self, pack_id: str, pack_version: str) -> PackRegistry:
        registry = PackRegistry()
        registry.register(self._root_for(pack_id, pack_version))
        return registry

    def register(self, pack_root: str | Path) -> dict[str, Any]:
        """Reject the pre-P19 path-only registration bypass.

        Controlled writes must use ``pack_factory.register_pack_candidate`` so
        the durable index mutation is bound to receipt, review, validation and
        named operator identities.  Existing index entries and built-ins remain
        readable and are not retroactively presented as factory-approved.
        """

        del pack_root
        raise PackIndexError(
            "direct Pack registration is disabled; use the controlled Pack Factory"
        )

    def _register_validated_path(
        self,
        pack_root: str | Path,
        *,
        expected_pack_id: str,
        expected_pack_version: str,
        expected_pack_fingerprint: str,
        factory_registration_fingerprint: str,
        factory_store_root: str,
    ) -> dict[str, Any]:
        """Write one exact factory-approved identity and fail closed on drift."""

        if not self.explicit_index_path or not self.path.is_absolute():
            raise PackIndexError("factory registration requires an explicit absolute index path")
        index_parent = self.path.parent
        if (
            index_parent.is_symlink()
            or not index_parent.is_dir()
            or index_parent.resolve(strict=True) != index_parent
            or self.path.is_symlink()
        ):
            raise PackIndexError(
                "factory registration index parent must be an existing canonical directory"
            )
        expected = (
            expected_pack_id,
            expected_pack_version,
            expected_pack_fingerprint,
        )
        if any(
            not isinstance(value, str) or not value or value.strip() != value
            for value in expected
        ):
            raise PackIndexError("expected Pack identity fields must be non-empty strings")
        for field, value in (
            ("expected Pack fingerprint", expected_pack_fingerprint),
            ("factory registration fingerprint", factory_registration_fingerprint),
        ):
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise PackIndexError(f"{field} must be lowercase SHA-256")
        if not isinstance(factory_store_root, str):
            raise PackIndexError("factory store root must be an explicit string")
        store_root = Path(factory_store_root)
        if (
            not store_root.is_absolute()
            or store_root.is_symlink()
            or not store_root.is_dir()
            or str(store_root.resolve(strict=True)) != factory_store_root
        ):
            raise PackIndexError(
                "factory store root must be an existing canonical absolute directory"
            )
        path = Path(pack_root)
        if path.is_symlink():
            raise PackIndexError("factory Pack root must not be a symlink")
        root = path.resolve(strict=True)
        record = validate_pack_summary(root, source="registered")
        observed = (
            record["pack_id"],
            record["pack_version"],
            record["pack_fingerprint"],
        )
        if observed != expected or not record["pack_valid"]:
            raise PackUnavailable("factory Pack identity or validation changed")
        key = expected[:2]
        for builtin_root in (
            builtin_pack_roots().values()
            if self.include_builtins
            else ()
        ):
            builtin = validate_pack_summary(builtin_root, source="builtin")
            if (builtin["pack_id"], builtin["pack_version"]) == key:
                raise PackIndexError(f"factory Pack identity conflicts with built-in: {key}")

        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        with lock_path.open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            entries = self._read()
            original_entries = [dict(entry) for entry in entries]
            current = validate_pack_summary(root, source="registered")
            current_identity = (
                current["pack_id"],
                current["pack_version"],
                current["pack_fingerprint"],
            )
            if current_identity != expected or not current["pack_valid"]:
                raise PackUnavailable("factory Pack changed before locked index mutation")
            wrote = False
            for entry in entries:
                entry_key = (entry["pack_id"], entry["pack_version"])
                if entry_key == key:
                    if (
                        entry["pack_fingerprint"] != expected_pack_fingerprint
                        or entry["root"] != str(root)
                    ):
                        raise PackIndexError(f"conflicting Pack identity: {key}")
                    existing_registration = entry["factory_registration_fingerprint"]
                    existing_store_root = entry["factory_store_root"]
                    if existing_registration not in {
                        None,
                        factory_registration_fingerprint,
                    } or existing_store_root not in {None, factory_store_root}:
                        raise PackIndexError(
                            "Pack identity already has a different factory registration"
                        )
                    if existing_registration is None:
                        entry["factory_registration_fingerprint"] = (
                            factory_registration_fingerprint
                        )
                        entry["factory_store_root"] = factory_store_root
                        self._write(entries)
                        wrote = True
                    break
                if entry["root"] == str(root):
                    raise PackIndexError("Pack root is already bound to another identity")
            else:
                entry = {
                    "pack_id": expected_pack_id,
                    "pack_version": expected_pack_version,
                    "pack_fingerprint": expected_pack_fingerprint,
                    "factory_registration_fingerprint": factory_registration_fingerprint,
                    "factory_store_root": factory_store_root,
                    "root": str(root),
                }
                entries.append(entry)
                self._write(entries)
                wrote = True
            try:
                result = validate_pack_summary(root, source="registered")
                if (
                    not result["pack_valid"]
                    or (
                        result["pack_id"],
                        result["pack_version"],
                        result["pack_fingerprint"],
                    )
                    != expected
                ):
                    raise PackIndexError("Pack changed during index mutation")
                return result
            except (OSError, ValueError):
                if wrote:
                    self._write(original_entries)
                raise

    def factory_registration_fingerprint(
        self,
        pack_id: str,
        pack_version: str,
    ) -> str | None:
        """Return durable factory provenance; ``None`` marks a legacy entry."""

        for entry in self._read():
            if (entry["pack_id"], entry["pack_version"]) == (
                pack_id,
                pack_version,
            ):
                return entry["factory_registration_fingerprint"]
        raise PackNotFound(f"unknown Pack: {(pack_id, pack_version)}")

    def factory_store_root(
        self,
        pack_id: str,
        pack_version: str,
    ) -> str | None:
        """Return the exact store bound to a factory registration entry."""

        for entry in self._read():
            if (entry["pack_id"], entry["pack_version"]) == (
                pack_id,
                pack_version,
            ):
                return entry["factory_store_root"]
        raise PackNotFound(f"unknown Pack: {(pack_id, pack_version)}")

    def factory_provenance(
        self,
        pack_id: str,
        pack_version: str,
    ) -> dict[str, str]:
        """Return one frozen v2 factory binding without opening Pack assets.

        Consumers that must audit metadata before materializing labels use this
        narrow accessor, then independently verify the bound store, manifest,
        and their exact allowlisted assets. Legacy entries fail closed.
        """

        for entry in self._read():
            if (entry["pack_id"], entry["pack_version"]) != (
                pack_id,
                pack_version,
            ):
                continue
            registration = entry["factory_registration_fingerprint"]
            store_root = entry["factory_store_root"]
            if registration is None or store_root is None:
                raise PackIndexError("legacy Pack index entry has no factory provenance")
            return {
                "pack_id": entry["pack_id"],
                "pack_version": entry["pack_version"],
                "pack_fingerprint": entry["pack_fingerprint"],
                "root": entry["root"],
                "factory_registration_fingerprint": registration,
                "factory_store_root": store_root,
            }
        raise PackNotFound(f"unknown Pack: {(pack_id, pack_version)}")


def _request_v2(request: dict[str, Any]) -> VirtualCellRequestV2:
    if request.get("schema_version") == "vc.request.v2":
        return VirtualCellRequestV2.from_dict(request)
    validation = validate_candidate(request)
    if not validation["schema_valid"]:
        raise InputValidationError(
            "invalid Pack request:"
            f"missing={validation['missing_fields']} errors={validation['errors']}"
        )
    return legacy_request_to_v2(
        VirtualCellRequest.from_dict(validation["normalized"])
    )


def _runtime_request_v2(request: dict[str, Any]) -> VirtualCellRequestV2:
    """Reconstruct the exact deterministic request bytes used by pack-aware runtime."""
    if request.get("schema_version") == "vc.request.v2":
        return VirtualCellRequestV2.from_dict(request)
    runtime_request = dict(request)
    if not runtime_request.get("request_id"):
        digest = hashlib.sha256(
            json.dumps(
                runtime_request,
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:16]
        runtime_request["request_id"] = f"vc-{digest}"
    normalized = asdict(VirtualCellRequest.from_dict(runtime_request))
    if normalized.get("perturbation_type") in ("gene", "gene_combination"):
        normalized["perturbation_targets"] = [
            str(target).strip().upper()
            for target in normalized.get("perturbation_targets", [])
        ]
    return legacy_request_to_v2(VirtualCellRequest.from_dict(normalized))


def _model_stack(
    model_registry_path: str | Path | None,
    model_cache_root: str | Path | None,
) -> tuple[ModelZooRegistry, ModelCache, EnvironmentSnapshot]:
    configured_registry = model_registry_path or os.environ.get(
        "PRAXIS_VC_MODEL_REGISTRY"
    )
    configured_cache = model_cache_root or os.environ.get(
        "PRAXIS_VC_MODEL_CACHE"
    )
    zoo = ModelZooRegistry(
        registry_path=(
            str(configured_registry)
            if configured_registry is not None
            else None
        ),
        enable_v2=True,
    )
    cache = ModelCache(
        root=str(configured_cache) if configured_cache is not None else None
    )
    cards = tuple(zoo.card(name) for name in zoo.capability_names())
    return zoo, cache, EnvironmentSnapshot.detect(cards)


def _public_plan(plan: dict[str, Any]) -> dict[str, Any]:
    plan_keys = {
        "vc.execution-plan.v1": (
            "schema_version",
            "plan_id",
            "request_id",
            "request_fingerprint",
            "pack_id",
            "pack_version",
            "pack_fingerprint",
            "environment_fingerprint",
            "executable",
            "legacy_adapter",
        ),
        "vc.execution-plan.v2": (
            "schema_version",
            "plan_id",
            "request_id",
            "request_fingerprint",
            "pack_id",
            "pack_version",
            "pack_fingerprint",
            "environment_snapshot_fingerprint",
            "executable",
            "legacy_adapter",
        ),
    }
    step_keys = {
        "vc.execution-plan.v1": (
            "model_name",
            "model_version",
            "model_fingerprint",
            "compatibility_fingerprint",
            "wrapper",
            "agent_name",
        ),
        "vc.execution-plan.v2": (
            "schema_version",
            "model_name",
            "model_version",
            "model_fingerprint",
            "release_fingerprint",
            "capability_fingerprint",
            "artifact_fingerprints",
            "environment_fingerprint",
            "adapter_fingerprints",
            "evidence_fingerprints",
            "policy_fingerprint",
            "compatibility_fingerprint",
            "wrapper",
            "agent_name",
        ),
    }
    report_keys = {
        "vc.execution-plan.v1": (
            "schema_version",
            "request_id",
            "request_fingerprint",
            "model_name",
            "model_version",
            "model_fingerprint",
            "pack_id",
            "pack_version",
            "pack_fingerprint",
            "environment_fingerprint",
            "pack_valid",
            "model_compatible",
            "environment_compatible",
            "assets_ready",
            "wrapper_ready",
            "executable",
            "scientifically_validated",
            "checks",
            "reasons",
        ),
        "vc.execution-plan.v2": (
            "schema_version",
            "request_id",
            "request_fingerprint",
            "model_name",
            "model_version",
            "model_fingerprint",
            "release_fingerprint",
            "capability_fingerprint",
            "pack_id",
            "pack_version",
            "pack_fingerprint",
            "environment_fingerprint",
            "environment_snapshot_fingerprint",
            "artifact_fingerprints",
            "adapter_fingerprints",
            "evidence_fingerprints",
            "policy_fingerprint",
            "cataloged",
            "artifact_ready",
            "revoked",
            "superseded_by",
            "pack_valid",
            "model_compatible",
            "environment_compatible",
            "adapter_compatible",
            "assets_ready",
            "wrapper_ready",
            "benchmark_passed",
            "scientifically_validated",
            "promotion_eligible",
            "policy_present",
            "production_promoted",
            "executable",
            "checks",
            "reasons",
        ),
    }
    schema = plan.get("schema_version")
    if schema not in plan_keys:
        raise ValueError("unsupported execution plan schema for public projection")
    public = {key: plan[key] for key in plan_keys[schema]}
    public["steps"] = [
        {key: step[key] for key in step_keys[schema]}
        for step in plan.get("steps", [])
    ]
    public["reports"] = [
        {key: report[key] for key in report_keys[schema]}
        for report in plan.get("reports", [])
    ]
    for item in (*public["steps"], *public["reports"]):
        item["model_version"] = public_model_version(item["model_version"])
    return json.loads(json.dumps(public))


def _public_provenance(provenance: dict[str, Any]) -> dict[str, Any]:
    public = json.loads(json.dumps(provenance))
    raw_plan = public.get("execution_plan")
    if raw_plan is not None:
        try:
            projected = _public_plan(raw_plan)
        except (KeyError, TypeError, ValueError):
            public["execution_plan"] = {
                "schema_version": None,
                "available": False,
                "reason": "unsupported_or_invalid_execution_plan",
            }
            public["compatibility_reports"] = []
        else:
            public["execution_plan"] = projected
            if "compatibility_reports" in public:
                public["compatibility_reports"] = projected["reports"]
    elif "compatibility_reports" in public:
        public["compatibility_reports"] = []
    raw_compilation = public.get("virtual_experiment")
    if raw_compilation is not None:
        try:
            from praxis_virtualcell.virtual_experiment import (
                VirtualExperimentCompilationV1,
            )

            public["virtual_experiment"] = (
                VirtualExperimentCompilationV1.from_dict(
                    raw_compilation
                ).to_dict()
            )
        except (KeyError, TypeError, ValueError):
            public["virtual_experiment"] = {
                "schema_version": None,
                "available": False,
                "reason": "unsupported_or_invalid_virtual_experiment",
            }
    return public


def _public_run_result(result: dict[str, Any]) -> dict[str, Any]:
    public = json.loads(json.dumps(result))
    provenance = _public_provenance(public.get("provenance") or {})
    public["provenance"] = provenance
    report = public.get("structured_report")
    if isinstance(report, dict):
        report["provenance"] = provenance
    return public


def _model_capabilities(
    zoo: ModelZooRegistry,
    registry_catalog: dict[str, Any],
) -> list[dict[str, Any]]:
    releases_by_model: dict[str, list[dict[str, Any]]] = {}
    for release in registry_catalog["releases"]:
        releases_by_model.setdefault(release["model_name"], []).append(release)
    capabilities = []
    for name in zoo.capability_names():
        card = zoo.card(name)
        capabilities.append(
            {
                "name": card.name,
                "version": public_model_version(card.version),
                "fingerprint": card.fingerprint(),
                "status": card.status,
                "species": list(card.species),
                "taxon": list(card.taxon),
                "modalities": [
                    {
                        "name": item.name,
                        "ontology_id": item.ontology_id,
                    }
                    for item in card.modality
                ],
                "cell_domain": card.cell_domain.to_dict(),
                "task": card.task,
                "outputs": list(card.output),
                "feature_namespaces": [
                    item.to_dict() for item in card.feature_namespace
                ],
                "scientifically_validated": False,
                "registry_releases": releases_by_model.get(card.name, []),
            }
        )
    return capabilities


def model_capabilities(
    model_registry_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    configured = model_registry_path or os.environ.get(
        "PRAXIS_VC_MODEL_REGISTRY"
    )
    zoo = ModelZooRegistry(
        registry_path=str(configured) if configured is not None else None,
        enable_v2=True,
    )
    assert zoo.registry_v2 is not None
    return _model_capabilities(zoo, zoo.registry_v2.public_catalog())


def pack_catalog_payload(
    *,
    index: PackIndex | None = None,
    model_registry_path: str | Path | None = None,
) -> dict[str, Any]:
    product_index = index or PackIndex()
    configured = model_registry_path or os.environ.get(
        "PRAXIS_VC_MODEL_REGISTRY"
    )
    zoo = ModelZooRegistry(
        registry_path=str(configured) if configured is not None else None,
        enable_v2=True,
    )
    assert zoo.registry_v2 is not None
    registry_catalog = zoo.registry_v2.public_catalog()
    return {
        "schema_version": "vc.pack-catalog.v1",
        "packs": product_index.list_records(),
        "model_capabilities": _model_capabilities(zoo, registry_catalog),
        "model_registry": registry_catalog,
        "scientifically_validated": False,
    }


def compatibility_payload(
    request: dict[str, Any],
    *,
    pack_id: str,
    pack_version: str,
    index: PackIndex | None = None,
    model_registry_path: str | Path | None = None,
    model_cache_root: str | Path | None = None,
) -> dict[str, Any]:
    product_index = index or PackIndex()
    registry = product_index.registry_for(pack_id, pack_version)
    zoo, cache, environment = _model_stack(
        model_registry_path,
        model_cache_root,
    )
    plan = CapabilityRegistry(zoo, cache).plan(
        _request_v2(request),
        registry.record(pack_id, pack_version),
        environment,
    )
    return {
        "schema_version": "vc.pack-compatibility-surface.v1",
        "pack": product_index.get_record(pack_id, pack_version),
        "execution_plan": _public_plan(plan.to_dict()),
    }


def virtual_experiment_payload(
    request: dict[str, Any],
    *,
    pack_id: str,
    pack_version: str,
    index: PackIndex | None = None,
    model_registry_path: str | Path | None = None,
    model_cache_root: str | Path | None = None,
    candidate_dag: object = None,
) -> dict[str, Any]:
    """Compile a direct-v2, Pack-bound experiment without executing models."""
    if (
        not isinstance(request, dict)
        or request.get("schema_version") != "vc.request.v2"
    ):
        raise InputValidationError(
            "virtual experiments require an exact vc.request.v2"
        )
    request_v2 = VirtualCellRequestV2.from_dict(request)
    product_index = index or PackIndex()
    registry = product_index.registry_for(pack_id, pack_version)
    pack = registry.record(pack_id, pack_version)
    zoo, cache, environment = _model_stack(
        model_registry_path,
        model_cache_root,
    )
    broker = ModelBrokerAgent(
        registry=zoo,
        cache=cache,
        pack_registry=registry,
        environment=environment,
    )
    plan = broker.plan(request_v2, pack)
    if not isinstance(plan, ExecutionPlanV2) or zoo.registry_v2 is None:
        raise PackUnavailable(
            "virtual experiments require the v2 model registry"
        )
    try:
        compilation = compile_virtual_experiment(
            request_v2,
            plan,
            zoo.registry_v2,
            candidate_dag=candidate_dag,
        )
    except VirtualExperimentContractError as exc:
        raise PackUnavailable(
            "virtual experiment contract is unavailable"
        ) from exc

    rejected = [report for report in plan.reports if not report.executable]
    provenance = {
        "execution_contract": "vc.virtual-experiment-compilation.v1",
        "execution_plan": plan.to_dict(),
        "compatibility_reports": [report.to_dict() for report in plan.reports],
        "virtual_experiment": compilation.to_dict(),
        "rejection_reasons": {
            report.model_name: ", ".join(report.reasons) or "not_executable"
            for report in rejected
        },
        "rules_referenced": [],
        "rules_hit": [],
        "n_messages": 0,
    }
    report = {
        "request_id": request_v2.request_id,
        "prediction": None,
        "models_used": [],
        "models_rejected": [report.model_name for report in rejected],
        "models_failed": [],
        "abstain": True,
        "abstain_reasons": [compilation.decision.reason],
        "reliability": "low",
        "provenance": provenance,
    }
    return _public_run_result(
        {
            "structured_report": report,
            "narrative": None,
            "trace": [],
            "provenance": provenance,
            "reliability_decision": {
                "abstain": True,
                "reliability": "low",
                "learned_reliability": None,
            },
            "llm_used_for_prediction": False,
            "mode": "offline",
            "llm_enabled": False,
        }
    )


def run_pack_query(
    request: dict[str, Any],
    *,
    pack_id: str,
    pack_version: str,
    index: PackIndex | None = None,
    model_registry_path: str | Path | None = None,
    model_cache_root: str | Path | None = None,
    config=None,
    enable_llm_report: bool = False,
) -> dict[str, Any]:
    if (
        isinstance(request, dict)
        and request.get("schema_version") == "vc.request.v2"
    ):
        raise InputValidationError(
            "vc.request.v2 must use the direct virtual experiment entry"
        )
    runtime_config = config or RuntimeConfig.from_env()
    if runtime_config.llm_enabled:
        raise PackUnavailable(
            "pack-aware LLM reporting is unavailable until model paths are "
            "projected before every outbound prompt"
        )
    product_index = index or PackIndex()
    registry = product_index.registry_for(pack_id, pack_version)
    zoo, cache, environment = _model_stack(
        model_registry_path,
        model_cache_root,
    )
    try:
        result = run_query(
            request,
            config=runtime_config,
            enable_llm_report=enable_llm_report,
            pack_id=pack_id,
            pack_version=pack_version,
            pack_registry=registry,
            model_registry=zoo,
            model_cache=cache,
            environment=environment,
        )
        return _public_run_result(result)
    except PackRegistryError as exc:
        raise PackUnavailable(str(exc)) from exc
