"""Declared, identity-checked measured feature tables for organism-profile v2."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

from pydantic import Field

from praxis_virtualcell.omics.profiles import (
    DEFAULT_PROFILE_ID, ProfileError, _Asset, _Condition, _PROFILE_ID, _Species, _Strict, _Terms, _asset, _limit,
)

MODALITIES = ("genome", "transcriptome", "proteome")


def validate_selection(modalities: list[str] | None, available: tuple[str, ...]) -> tuple[str, ...]:
    if modalities is None:
        return tuple(name for name in MODALITIES if name in available)
    if not isinstance(modalities, list) or not modalities or any(
        not isinstance(name, str) or name not in MODALITIES for name in modalities
    ):
        raise ProfileError("modalities must be a nonempty list of genome, transcriptome, or proteome")
    missing = set(modalities) - set(available)
    if missing:
        raise ProfileError(f"Requested modalities are unavailable: {', '.join(sorted(missing))}")
    return tuple(name for name in MODALITIES if name in modalities)


class _TableAsset(_Asset):
    format: Literal["csv", "json"]


class _TableCondition(_Condition):
    role: Literal["untreated_reference", "pre_treatment_baseline", "sequenced_reference"]


class _Pairing(_Strict):
    pairing_id: str = Field(min_length=1)
    relation: Literal["same_sample", "matched_samples"]
    evidence: str = Field(min_length=1)


class _TableProvenance(_Strict):
    study_id: str = Field(min_length=1)
    source_samples: list[str]
    citation: str = Field(min_length=1)
    terms: _Terms
    input_role: Literal["measured_pre_treatment", "sequenced_reference"]


class _Modality(_Strict):
    species: _Species
    strain: str = Field(min_length=1)
    genotype: str | None
    condition: _TableCondition
    sample_id: str = Field(min_length=1)
    pairing_id: str | None
    assay: Literal[
        "whole_genome_sequencing", "targeted_sequencing", "assembly_annotation",
        "RNA_seq", "microarray", "measured_transcriptomics",
        "LC_MS_MS", "SWATH_MS", "targeted_MS", "measured_proteomics",
    ]
    feature_namespace: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    scale: str = Field(min_length=1)
    value_semantics: str = Field(min_length=1)
    observation_unit: Literal["measured_baseline_sample", "measured_reference_assembly", "author_condition_summary"]
    features: _TableAsset
    provenance: _TableProvenance


class _MultiManifest(_Strict):
    schema_version: Literal["praxis.organism-profile.v2"]
    profile_id: str
    species: _Species
    strain: str = Field(min_length=1)
    genotype: str | None
    condition: _TableCondition
    pairing: _Pairing | None
    modalities: dict[str, _Modality]


class _NativeLocator(_Strict):
    path: str | None
    row: int | None = Field(ge=1)
    accession: str | None
    record_id: str | None


class _Feature(_Strict):
    feature_id: str = Field(min_length=1)
    gene_id: str | None = None
    protein_id: str | None = None
    gene_symbol: str | None = None
    product: str | None = None
    contig: str | None = None
    source_locator: _NativeLocator


class _GenomeFeature(_Feature):
    presence: bool | None
    variant: str | None = None
    copy_number: float | None = Field(default=None, ge=0)


class _TranscriptomeFeature(_Feature):
    gene_id: str
    expression_value: float | None


class _ProteomeFeature(_Feature):
    protein_id: str
    abundance_value: float | None


_FEATURE_TYPES = {"genome": _GenomeFeature, "transcriptome": _TranscriptomeFeature, "proteome": _ProteomeFeature}
_ASSAYS = {
    "genome": {"whole_genome_sequencing", "targeted_sequencing", "assembly_annotation"},
    "transcriptome": {"RNA_seq", "microarray", "measured_transcriptomics"},
    "proteome": {"LC_MS_MS", "SWATH_MS", "targeted_MS", "measured_proteomics"},
}
_NUMBERS = {"expression_value", "abundance_value", "copy_number"}
_LOCATOR_COLUMNS = {"source_path", "source_row", "source_accession", "source_record_id"}


def _valid_id(value: str | None) -> bool:
    return value is None or bool(value and value == value.strip())


def _validate_manifest(root: Path, expected_id: str) -> _MultiManifest:
    try:
        m = _MultiManifest.model_validate(json.loads((root / "manifest.json").read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        raise ProfileError(f"Invalid organism v2 manifest: {root / 'manifest.json'}") from exc
    if m.profile_id != expected_id or not _PROFILE_ID.fullmatch(m.profile_id) or expected_id == DEFAULT_PROFILE_ID:
        raise ProfileError("Profile identity does not match its directory or replaces the frozen AB5075 v1 profile")
    if not m.modalities or set(m.modalities) - set(MODALITIES):
        raise ProfileError("A v2 profile must declare one or more canonical modalities")
    if len(m.modalities) > 1 and m.pairing is None:
        raise ProfileError("Multiple modalities require explicit sample pairing and evidence")
    if m.condition.role == "sequenced_reference" and set(m.modalities) != {"genome"}:
        raise ProfileError("Sequenced reference conditions require a genome-only profile")
    identity = (m.species, m.strain, m.genotype, m.condition)
    for name, modality in m.modalities.items():
        if (modality.species, modality.strain, modality.genotype, modality.condition) != identity:
            raise ProfileError(f"{name} strain, species, genotype, or condition identity differs from the profile")
        if modality.assay not in _ASSAYS[name]:
            raise ProfileError(f"{name} assay does not establish a measured {name} input")
        if name != "genome" and modality.provenance.input_role != "measured_pre_treatment":
            raise ProfileError(f"{name} must be a measured pre-treatment sample")
        if m.condition.role == "sequenced_reference" and modality.provenance.input_role != "sequenced_reference":
            raise ProfileError("Sequenced reference conditions require reference provenance")
        samples = modality.provenance.source_samples
        if not samples or any(not _valid_id(sample) or sample is None for sample in samples) or len(set(samples)) != len(samples):
            raise ProfileError(f"{name} source sample IDs must be nonempty and unique")
        if modality.sample_id not in samples:
            raise ProfileError(f"{name} sample identity must occur in its native source sample IDs")
        if modality.pairing_id != (m.pairing.pairing_id if m.pairing else None):
            raise ProfileError(f"{name} pairing identity differs from the declared pairing")
    if m.pairing and m.pairing.relation == "same_sample":
        if len({item.sample_id for item in m.modalities.values()}) != 1:
            raise ProfileError("same_sample pairing requires the same explicit sample ID across modalities")
    return m


def _csv_records(path: Path, modality: str) -> list[dict]:
    model = _FEATURE_TYPES[modality]
    allowed = (set(model.model_fields) - {"source_locator"}) | _LOCATOR_COLUMNS
    required = {key for key, value in model.model_fields.items() if value.is_required()} - {"source_locator"}
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or not required.issubset(headers) or set(headers) - allowed:
            raise ProfileError(f"Invalid {modality} feature CSV columns")
        records = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ProfileError("Feature CSV rows must match their declared columns")
            record = {}
            for key, text in row.items():
                if key in _LOCATOR_COLUMNS:
                    continue
                value = None if text == "" else text
                if key in _NUMBERS and value is not None:
                    value = float(value)
                elif key == "presence" and value is not None:
                    if value not in {"true", "false"}:
                        raise ProfileError("Genome presence must be true, false, or empty for unknown")
                    value = value == "true"
                record[key] = value
            record["source_locator"] = {
                "path": row.get("source_path") or None,
                "row": int(row["source_row"]) if row.get("source_row") else None,
                "accession": row.get("source_accession") or None,
                "record_id": row.get("source_record_id") or None,
            }
            records.append(record)
        return records


def _load_features(root: Path, name: str, modality: _Modality) -> tuple[dict, ...]:
    path = _asset(root, modality.features)
    try:
        records = _csv_records(path, name) if modality.features.format == "csv" else json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(records, list) or not records:
            raise ProfileError("Measured feature assets must contain a nonempty record list")
        result = []
        seen = set()
        for index, record in enumerate(records):
            item = _FEATURE_TYPES[name].model_validate(record).model_dump()
            if any(not _valid_id(item.get(key)) for key in ("feature_id", "gene_id", "protein_id")):
                raise ProfileError("Feature and native gene/protein IDs must be nonempty without outer whitespace")
            if item["feature_id"] in seen:
                raise ProfileError("Feature IDs must be unique within each modality")
            seen.add(item["feature_id"])
            if any(value is not None and not math.isfinite(value) for key, value in item.items() if key in _NUMBERS):
                raise ProfileError("Measured numeric values must be finite or explicitly null")
            native = item.pop("source_locator")
            if not native["path"] and not native["accession"]:
                raise ProfileError("Each feature requires a native source path or accession")
            if not native["row"] and not native["record_id"] and not native["accession"]:
                raise ProfileError("Each feature requires a native row, record ID, or accession")
            item["source_locator"] = {
                "feature_asset": f"{root.name}/{modality.features.path}",
                "asset_record_index": index,
                "native_source": native,
                "source_samples": list(modality.provenance.source_samples),
            }
            result.append(item)
        return tuple(result)
    except (OSError, ValueError, TypeError) as exc:
        raise ProfileError(f"Invalid {name} feature asset: {path}: {exc}") from exc


@dataclass(frozen=True)
class MultiomicsProfile:
    """A selected view; unselected table rows and provenance never enter tool results."""

    _manifest: _MultiManifest = field(repr=False)
    _features: dict[str, tuple[dict, ...]] = field(repr=False)
    _selected: tuple[str, ...]

    @property
    def profile_id(self) -> str:
        return self._manifest.profile_id

    def select_modalities(self, modalities: list[str] | None = None) -> MultiomicsProfile:
        return replace(self, _selected=validate_selection(modalities, tuple(self._manifest.modalities)))

    def overview(self) -> dict:
        m = self._manifest
        summaries = {}
        for name in self._selected:
            item = m.modalities[name]
            summaries[name] = {
                "feature_count": len(self._features[name]), "feature_namespace": item.feature_namespace,
                "unit": item.unit, "scale": item.scale, "value_semantics": item.value_semantics,
                "observation_unit": item.observation_unit, "sample_id": item.sample_id,
                "assay": item.assay, "source_samples": list(item.provenance.source_samples),
                "source_id": f"omics:{self.profile_id}:{name}:profile",
                "source_locator": {"manifest": f"{self.profile_id}/manifest.json", "modality": name},
                "provenance": item.provenance.model_dump(),
            }
        condition = m.condition.model_dump()
        unknown = [key for key, value in condition.items() if value is None]
        if m.genotype is None:
            unknown.append("genotype")
        pairing = None
        if m.pairing and len(self._selected) > 1:
            pairing = {"pairing_id": m.pairing.pairing_id, "relation": m.pairing.relation}
            if set(self._selected) == set(m.modalities):
                pairing["evidence"] = m.pairing.evidence
        return {
            "profile_id": self.profile_id, "source_id": f"omics:{self.profile_id}:profile",
            "species": m.species.model_dump(), "strain": m.strain, "genotype": m.genotype,
            "condition": condition, "modality": "+".join(self._selected),
            "available_modalities": [name for name in MODALITIES if name in m.modalities],
            "selected_modalities": list(self._selected), "modalities": summaries,
            "feature_count": sum(item["feature_count"] for item in summaries.values()),
            "source_samples": sorted({sample for item in summaries.values() for sample in item["source_samples"]}),
            "unknown_fields": unknown,
            "pairing": pairing,
            "source_locator": {"manifest": f"{self.profile_id}/manifest.json"},
        }

    def _modality(self, name: str) -> _Modality:
        if name not in self._selected:
            raise ProfileError(f"Modality is unavailable or unselected: {name}")
        return self._manifest.modalities[name]

    def _feature(self, name: str, item: dict) -> dict:
        modality = self._manifest.modalities[name]
        # Copy nested locators so callers cannot mutate future evidence responses.
        result = json.loads(json.dumps(item))
        return result | {
            "modality": name, "unit": modality.unit, "scale": modality.scale,
            "value_semantics": modality.value_semantics,
            "source_id": f"omics:{self.profile_id}:{name}:feature:{item['feature_id']}",
        }

    def query_features(self, modality: str, feature_ids: list[str], limit: int = 30) -> dict:
        self._modality(modality)
        limit = _limit(limit)
        if not isinstance(feature_ids, list) or any(not isinstance(item, str) or not item for item in feature_ids):
            raise ValueError("feature_ids must be a list of nonempty native feature IDs")
        positions = {item["feature_id"]: item for item in self._features[modality]}
        requested = list(dict.fromkeys(feature_ids))
        found = [positions[item] for item in requested if item in positions]
        return {
            "profile_id": self.profile_id, "modality": modality,
            "features": [self._feature(modality, item) for item in found[:limit]],
            "missing_feature_ids": [item for item in requested if item not in positions], "truncated": len(found) > limit,
        }

    def search_features(self, modality: str, query: str, limit: int = 30) -> dict:
        self._modality(modality)
        limit = _limit(limit)
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be nonempty text")
        needle = query.casefold()
        found = [item for item in self._features[modality] if any(
            needle in (item.get(key) or "").casefold()
            for key in ("feature_id", "gene_id", "protein_id", "gene_symbol", "product", "variant")
        )]
        return {"profile_id": self.profile_id, "modality": modality, "query": query,
                "features": [self._feature(modality, item) for item in found[:limit]],
                "match_count": len(found), "truncated": len(found) > limit}

    def query_genes(self, gene_ids: list[str], limit: int = 30) -> dict:
        limit = _limit(limit)
        if not isinstance(gene_ids, list) or any(not isinstance(item, str) or not item for item in gene_ids):
            raise ValueError("gene_ids must be a list of nonempty native gene IDs")
        requested = list(dict.fromkeys(gene_ids))
        found = [(name, item) for gene in requested for name in self._selected for item in self._features[name]
                 if item.get("gene_id") == gene]
        present = {item["gene_id"] for _, item in found}
        return {"profile_id": self.profile_id, "genes": [self._feature(name, item) for name, item in found[:limit]],
                "missing_gene_ids": [gene for gene in requested if gene not in present], "truncated": len(found) > limit}

    def search_annotations(self, query: str, limit: int = 30) -> dict:
        limit = _limit(limit)
        results = [self.search_features(name, query, 100) for name in self._selected]
        hits = [item for result in results for item in result["features"]]
        count = sum(result["match_count"] for result in results)
        return {"profile_id": self.profile_id, "query": query, "genes": hits[:limit],
                "match_count": count, "truncated": count > limit}


def load_multiomics_profile(root: Path, expected_id: str) -> MultiomicsProfile:
    manifest = _validate_manifest(root, expected_id)
    features = {name: _load_features(root, name, modality) for name, modality in manifest.modalities.items()}
    return MultiomicsProfile(manifest, features, validate_selection(None, tuple(features)))
