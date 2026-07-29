"""Product-facing VirtualCellPack inspection, indexing, and execution helpers."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from pathlib import Path
from typing import Any

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
)
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
from praxis_virtualcell.workflows.run_virtualcell_query import (
    run_query,
    validate_candidate,
)

_INDEX_SCHEMA = "vc.pack-index.v1"
_INDEX_ENTRY_KEYS = {
    "pack_id",
    "pack_version",
    "pack_fingerprint",
    "root",
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


def _valid_index_entry(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != _INDEX_ENTRY_KEYS:
        raise PackIndexError("Pack index entry has invalid fields")
    entry: dict[str, str] = {}
    for field in _INDEX_ENTRY_KEYS:
        item = value[field]
        if not isinstance(item, str) or not item or item.strip() != item:
            raise PackIndexError(f"Pack index {field} must be a non-empty string")
        entry[field] = item
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
        self.path = Path(
            configured
            or Path.home()
            / ".local"
            / "share"
            / "praxis-virtualcell"
            / "pack-index.json"
        ).expanduser()
        self.include_builtins = include_builtins

    def _read(self) -> list[dict[str, str]]:
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
            or raw["schema_version"] != _INDEX_SCHEMA
            or not isinstance(raw["packs"], list)
        ):
            raise PackIndexError("invalid Pack index contract")
        entries = [_valid_index_entry(item) for item in raw["packs"]]
        keys = [(item["pack_id"], item["pack_version"]) for item in entries]
        roots = [item["root"] for item in entries]
        if len(set(keys)) != len(keys) or len(set(roots)) != len(roots):
            raise PackIndexError("Pack index contains duplicate identity or root")
        return entries

    def _write(self, entries: list[dict[str, str]]) -> None:
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

    def _roots(self) -> list[tuple[str, Path, dict[str, str] | None]]:
        roots: list[tuple[str, Path, dict[str, str] | None]] = []
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
        expected: dict[str, str] | None,
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
        root = Path(pack_root).resolve(strict=True)
        record = validate_pack_summary(root, source="registered")
        if not record["pack_valid"]:
            raise PackUnavailable("; ".join(record["reasons"]))
        key = (record["pack_id"], record["pack_version"])
        for builtin_root in (
            builtin_pack_roots().values()
            if self.include_builtins
            else ()
        ):
            builtin = validate_pack_summary(builtin_root, source="builtin")
            if (builtin["pack_id"], builtin["pack_version"]) == key:
                if (
                    builtin["pack_fingerprint"]
                    != record["pack_fingerprint"]
                    or builtin_root.resolve() != root
                ):
                    raise PackIndexError(f"Pack identity conflicts with built-in: {key}")
                return builtin

        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        with lock_path.open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            entries = self._read()
            for entry in entries:
                entry_key = (entry["pack_id"], entry["pack_version"])
                if entry_key == key:
                    if (
                        entry["pack_fingerprint"] != record["pack_fingerprint"]
                        or entry["root"] != str(root)
                    ):
                        raise PackIndexError(f"conflicting Pack identity: {key}")
                    return self._record("registered", root, entry)
                if entry["root"] == str(root):
                    raise PackIndexError("Pack root is already bound to another identity")
            entry = {
                "pack_id": record["pack_id"],
                "pack_version": record["pack_version"],
                "pack_fingerprint": record["pack_fingerprint"],
                "root": str(root),
            }
            entries.append(entry)
            self._write(entries)
            return self._record("registered", root, entry)


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
        )
    )
    cache = ModelCache(
        root=str(configured_cache) if configured_cache is not None else None
    )
    cards = tuple(zoo.card(name) for name in zoo.capability_names())
    return zoo, cache, EnvironmentSnapshot.detect(cards)


def _public_plan(plan: dict[str, Any]) -> dict[str, Any]:
    public = json.loads(json.dumps(plan))
    for step in public["steps"]:
        step.pop("asset_paths", None)
    for report in public["reports"]:
        report.pop("asset_paths", None)
    return public


def model_capabilities(
    model_registry_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    configured = model_registry_path or os.environ.get(
        "PRAXIS_VC_MODEL_REGISTRY"
    )
    zoo = ModelZooRegistry(
        registry_path=str(configured) if configured is not None else None
    )
    capabilities = []
    for name in zoo.capability_names():
        card = zoo.card(name)
        capabilities.append(
            {
                "name": card.name,
                "version": card.version,
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
            }
        )
    return capabilities


def pack_catalog_payload(
    *,
    index: PackIndex | None = None,
    model_registry_path: str | Path | None = None,
) -> dict[str, Any]:
    product_index = index or PackIndex()
    return {
        "schema_version": "vc.pack-catalog.v1",
        "packs": product_index.list_records(),
        "model_capabilities": model_capabilities(model_registry_path),
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
    product_index = index or PackIndex()
    registry = product_index.registry_for(pack_id, pack_version)
    zoo, cache, environment = _model_stack(
        model_registry_path,
        model_cache_root,
    )
    try:
        return run_query(
            request,
            config=config,
            enable_llm_report=enable_llm_report,
            pack_id=pack_id,
            pack_version=pack_version,
            pack_registry=registry,
            model_registry=zoo,
            model_cache=cache,
            environment=environment,
        )
    except PackRegistryError as exc:
        raise PackUnavailable(str(exc)) from exc
