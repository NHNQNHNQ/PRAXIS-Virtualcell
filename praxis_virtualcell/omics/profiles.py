"""Load declared baseline profiles and return traceable native-gene evidence."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from praxis_virtualcell.data_packs.validator import resolve_asset_path


DEFAULT_PROFILE_ID = "AB5075-AZI000"
_PROFILE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")


class ProfileError(ValueError):
    """The requested measured baseline or its identity cannot be verified."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _Species(_Strict):
    scientific_name: str
    taxonomy_id: str


class _Condition(_Strict):
    condition_id: str
    role: Literal["untreated_reference", "pre_treatment_baseline"]
    medium: str | None
    time_h: float | None
    temperature_c: float | None
    growth_phase: str | None


class _Asset(_Strict):
    path: str
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class _ExpressionSource(_Strict):
    path: str
    sha256: str
    array_key: Literal["control", "expression"]
    row_index: int = Field(ge=0)
    pair_id: str
    pairs_path: str
    aggregation: str


class _MetadataSource(_Strict):
    path: str
    sha256: str
    qc_path: str
    identity_field: str
    unknown_value_policy: str


class _AnnotationSource(_Strict):
    reference_path: str
    reference_sha256: str
    mapping_path: str
    mapping_sha256: str
    reference_namespace: str
    reference_accessions: list[str]
    sequence_role: str


class _Terms(_Strict):
    usage: str
    redistribution_approved: bool
    license_status: str


class _Provenance(_Strict):
    study_id: str
    source_samples: list[str]
    expression_source: _ExpressionSource
    metadata_source: _MetadataSource
    annotation_source: _AnnotationSource
    citation: str
    terms: _Terms
    input_role: str


class _Manifest(_Strict):
    schema_version: Literal["praxis.organism-profile.v1"]
    profile_id: str
    species: _Species
    strain: str
    genotype: str | None
    modality: Literal["bulk_RNA_seq"]
    feature_namespace: str
    unit: str
    scale: str
    value_semantics: str
    observation_unit: Literal["historical_condition_mean", "measured_baseline_sample"]
    condition: _Condition
    expression: _Asset
    annotations: _Asset
    provenance: _Provenance


def _data_root(data_root=None) -> Path:
    return Path(data_root) if data_root is not None else Path(__file__).resolve().parents[2] / "data" / "organisms"


def _manifest(path: Path, expected_id: str) -> _Manifest:
    try:
        manifest = _Manifest.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        raise ProfileError(f"Invalid organism manifest: {path}") from exc
    if manifest.profile_id != expected_id or not _PROFILE_ID.fullmatch(manifest.profile_id):
        raise ProfileError("Profile ID does not match its declared directory")
    samples = manifest.provenance.source_samples
    if not samples or any(not s for s in samples):
        raise ProfileError("Baseline source sample IDs must be explicitly declared")
    if len(set(samples)) != len(samples):
        raise ProfileError("Baseline source sample IDs must be unique")
    if expected_id == DEFAULT_PROFILE_ID:
        from praxis_virtualcell.omics.npz_adapter import AB5075_CONTROL_SAMPLES, AB5075_SCALE

        expected = (
            manifest.species.scientific_name == "Acinetobacter baumannii",
            manifest.species.taxonomy_id == "NCBITaxon:470",
            manifest.strain == "AB5075", manifest.genotype is None,
            manifest.unit == "author_log2_TPM_QC", manifest.scale == AB5075_SCALE,
            manifest.observation_unit == "historical_condition_mean",
            manifest.condition.condition_id == "AZI_000", manifest.condition.medium == "CA-MHB",
            manifest.condition.role == "untreated_reference",
            all(value is None for value in (manifest.condition.time_h, manifest.condition.temperature_c, manifest.condition.growth_phase)),
            set(samples) == set(AB5075_CONTROL_SAMPLES),
            manifest.provenance.study_id == "PRJNA658638",
            manifest.provenance.expression_source.array_key == "control",
            manifest.provenance.expression_source.row_index == 0,
            manifest.provenance.expression_source.pair_id == "AZI:AZI_003",
            manifest.provenance.annotation_source.reference_namespace == "AB5075_original",
        )
        if not all(expected):
            raise ProfileError("AB5075-AZI000 identity, native scale, or baseline reference was changed")
    return manifest


def _asset(root: Path, asset: _Asset) -> Path:
    try:
        path = resolve_asset_path(root, asset.path)
    except ValueError as exc:
        raise ProfileError(str(exc)) from exc
    if path.stat().st_size != asset.size_bytes:
        raise ProfileError(f"Profile asset size mismatch: {asset.path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != asset.sha256:
        raise ProfileError(f"Profile asset hash mismatch: {asset.path}")
    return path


def _limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer from 1 to 100")
    return limit


@dataclass(frozen=True)
class OrganismProfile:
    """One verified baseline vector; no treated expression or response is retained."""

    _manifest: _Manifest = field(repr=False)
    _genes: tuple[str, ...] = field(repr=False)
    _values: tuple[float, ...] = field(repr=False)
    _annotations: dict[str, dict] = field(repr=False)

    @property
    def profile_id(self) -> str:
        return self._manifest.profile_id

    def overview(self) -> dict:
        m = self._manifest
        condition = m.condition.model_dump()
        unknown = [key for key, value in condition.items() if value is None]
        if m.genotype is None:
            unknown.append("genotype")
        return {
            "profile_id": self.profile_id,
            "source_id": f"omics:{self.profile_id}:profile",
            "species": m.species.model_dump(),
            "strain": m.strain,
            "genotype": m.genotype,
            "condition": condition,
            "modality": m.modality,
            "feature_namespace": m.feature_namespace,
            "feature_count": len(self._genes),
            "annotated_feature_count": len(self._annotations),
            "unit": m.unit,
            "scale": m.scale,
            "value_semantics": m.value_semantics,
            "observation_unit": m.observation_unit,
            "source_samples": list(m.provenance.source_samples),
            "unknown_fields": unknown,
            "source_locator": {"manifest": f"{self.profile_id}/manifest.json"},
            "provenance": m.provenance.model_dump(),
        }

    def _gene(self, index: int) -> dict:
        gene_id = self._genes[index]
        annotation = self._annotations.get(gene_id, {})
        provenance = self._manifest.provenance
        locator = {
            "expression_asset": f"{self.profile_id}/{self._manifest.expression.path}",
            "array_key": "expression",
            "feature_index": index,
            "native_source": provenance.expression_source.model_dump(),
            "source_samples": list(provenance.source_samples),
        }
        if annotation:
            locator["annotation_asset"] = f"{self.profile_id}/{self._manifest.annotations.path}"
            locator["reference_source"] = provenance.annotation_source.reference_path
            locator["reference_row"] = int(annotation["reference_row"])
            locator["mapping_source"] = provenance.annotation_source.mapping_path
            locator["mapping_row"] = int(annotation["mapping_row"])
        return {
            "source_id": f"omics:{self.profile_id}:gene:{gene_id}",
            "gene_id": gene_id,
            "expression_value": self._values[index],
            "unit": self._manifest.unit,
            "scale": self._manifest.scale,
            "gene_symbol": annotation.get("gene_symbol") or None,
            "product": annotation.get("product") or None,
            "protein_id": annotation.get("protein_id") or None,
            "contig": annotation.get("contig") or None,
            "mapping_evidence": annotation.get("mapping_evidence") or None,
            "source_locator": locator,
        }

    def query_genes(self, gene_ids: list[str], limit: int = 30) -> dict:
        limit = _limit(limit)
        if not isinstance(gene_ids, list) or any(not isinstance(g, str) or not g for g in gene_ids):
            raise ValueError("gene_ids must be a list of nonempty native gene IDs")
        positions = {gene: index for index, gene in enumerate(self._genes)}
        requested = list(dict.fromkeys(gene_ids))
        found = [positions[g] for g in requested if g in positions]
        return {
            "profile_id": self.profile_id,
            "genes": [self._gene(i) for i in found[:limit]],
            "missing_gene_ids": [g for g in requested if g not in positions],
            "truncated": len(found) > limit,
        }

    def search_annotations(self, query: str, limit: int = 30) -> dict:
        limit = _limit(limit)
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be nonempty text")
        needle = query.casefold()
        found = []
        for index, gene_id in enumerate(self._genes):
            row = self._annotations.get(gene_id, {})
            fields = (gene_id, row.get("gene_symbol", ""), row.get("product", ""), row.get("protein_id", ""))
            if any(needle in value.casefold() for value in fields):
                found.append(index)
        return {
            "profile_id": self.profile_id,
            "query": query,
            "genes": [self._gene(i) for i in found[:limit]],
            "match_count": len(found),
            "truncated": len(found) > limit,
        }


def list_profiles(data_root=None) -> list[dict]:
    root = _data_root(data_root).resolve()
    if not root.is_dir():
        return []
    profiles = []
    for path in sorted(root.glob("*/manifest.json")):
        m = _manifest(path, path.parent.name)
        profiles.append({
            "profile_id": m.profile_id,
            "name": f"{m.strain} / {m.condition.condition_id}",
            "label": f"{m.strain} · {m.condition.condition_id} · {m.condition.medium or 'medium unknown'}",
            "species": m.species.model_dump(),
            "strain": m.strain,
            "condition": m.condition.model_dump(),
            "modality": m.modality,
            "unit": m.unit,
            "scale": m.scale,
            "observation_unit": m.observation_unit,
            "source_id": f"omics:{m.profile_id}:profile",
        })
    return profiles


def load_profile(profile_id: str = DEFAULT_PROFILE_ID, data_root=None) -> OrganismProfile:
    if not isinstance(profile_id, str) or not _PROFILE_ID.fullmatch(profile_id) or profile_id in {".", ".."}:
        raise ProfileError("Invalid profile ID")
    root = _data_root(data_root).resolve()
    profile_root = root / profile_id
    if not profile_root.is_dir() or not profile_root.resolve().is_relative_to(root):
        raise ProfileError(f"Profile not found: {profile_id}")
    m = _manifest(profile_root / "manifest.json", profile_id)
    expression = _asset(profile_root, m.expression)
    annotations_path = _asset(profile_root, m.annotations)
    try:
        with np.load(expression, allow_pickle=False) as archive:
            if set(archive.files) != {"genes", "expression"}:
                raise ProfileError("Baseline NPZ must contain only genes and expression")
            genes = archive["genes"]
            values = archive["expression"]
    except (OSError, ValueError) as exc:
        raise ProfileError(f"Invalid baseline NPZ: {expression}") from exc
    if genes.ndim != 1 or genes.dtype.kind not in "SU" or values.ndim != 1 or values.shape != genes.shape:
        raise ProfileError("Baseline expression must match a one-dimensional native gene ID vector")
    if not len(genes) or values.dtype.kind not in "iuf" or not np.isfinite(values).all():
        raise ProfileError("Baseline expression must be finite numeric measured values")
    native_ids = tuple(str(gene) for gene in genes)
    if len(set(native_ids)) != len(native_ids) or any(not g or g != g.strip() for g in native_ids):
        raise ProfileError("Native gene IDs must be nonempty and unique")
    annotation_rows = {}
    native_id_set = set(native_ids)
    with annotations_path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"gene_id", "gene_symbol", "product", "protein_id", "contig", "reference_key", "mapping_evidence", "reference_row", "mapping_row"}
        if not required.issubset(reader.fieldnames or []):
            raise ProfileError("Native annotation columns are incomplete")
        for row in reader:
            gene_id = row["gene_id"]
            if gene_id not in native_id_set or gene_id in annotation_rows:
                raise ProfileError("Annotations must match unique native expression IDs")
            if not row["reference_row"].isdigit() or not row["mapping_row"].isdigit():
                raise ProfileError("Annotation source row locators are invalid")
            annotation_rows[gene_id] = row
    return OrganismProfile(m, native_ids, tuple(float(value) for value in values), annotation_rows)
