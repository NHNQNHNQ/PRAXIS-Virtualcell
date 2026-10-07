"""Exact declared-strain reference sources, with independent culture conditions."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator

from .multiomics import MODALITIES, validate_selection
from .profiles import ProfileError, _PROFILE_ID, _Species, _Strict
from .species_reference import SpeciesReferenceProfile


_UNKNOWN = {"unknown", "unknown strain", "unspecified", "unidentified", "unidentified isolate",
            "unclassified", "not reported", "not provided", "not specified", "none", "null", "n/a",
            "na", "n.a.", "wt", "wild type", "wild-type", "未知", "未报告", "未注明", "野生型"}


class _StrainManifest(_Strict):
    schema_version: Literal["praxis.strain-reference.v1"]
    profile_id: str
    species: _Species
    strain: str = Field(min_length=1)
    label: str = Field(min_length=1)
    strain_namespace: str = Field(min_length=1)
    identity_basis: str = Field(min_length=1)
    genotype: str | None = None
    reference_profiles: dict[str, str]
    input_role: Literal["strain_reference"]
    relation: Literal["same_strain_reference"]
    prediction_scope: Literal["strain_reference"]
    selection_reasons: dict[str, str] = Field(default_factory=dict)

    @field_validator("strain", "strain_namespace", "identity_basis", "label")
    @classmethod
    def require_explicit_identity(cls, value: str) -> str:
        if value != value.strip() or value.casefold() in _UNKNOWN:
            raise ValueError("Strain identity and its basis must be explicit; aliases are not inferred")
        return value


@dataclass(frozen=True)
class StrainReferenceProfile(SpeciesReferenceProfile):
    """Reuse native tools without borrowing other strains or relabeling evidence."""

    _manifest: _StrainManifest = field(repr=False)

    def select_modalities(self, modalities: list[str] | None = None) -> StrainReferenceProfile:
        return replace(self, _selected=validate_selection(modalities, tuple(self._sources)))

    def overview(self) -> dict:
        result = super().overview()
        m = self._manifest
        result.update({
            "strain": m.strain, "label": m.label, "strain_namespace": m.strain_namespace,
            "identity_basis": m.identity_basis, "genotype": m.genotype,
            "condition": {"condition_id": "strain_reference", "role": "strain_reference",
                          "medium": None, "time_h": None, "temperature_c": None, "growth_phase": None},
            "unknown_fields": ["prediction_condition"] + (["genotype"] if m.genotype is None else []),
            "limitations": [
                "All selected native sources declare this exact strain and genotype identity; no strain alias, mutant or derivative is inferred.",
                "Reference modalities may have different samples and culture conditions; they are not a matched biological sample or current cellular state.",
                "The reference does not identify an arbitrary isolate of this species; unknown genotype remains unknown, not verified wild type.",
            ],
        })
        return result

    def _rows(self, name: str, rows: list[dict]) -> list[dict]:
        return [row | {"input_role": "strain_reference"} for row in super()._rows(name, rows)]

    def query_features(self, modality: str, feature_ids: list[str], limit: int = 30) -> dict:
        return super().query_features(modality, feature_ids, limit) | {"input_role": "strain_reference"}

    def search_features(self, modality: str, query: str, limit: int = 30) -> dict:
        return super().search_features(modality, query, limit) | {"input_role": "strain_reference"}

    def query_genes(self, gene_ids: list[str], limit: int = 30) -> dict:
        return super().query_genes(gene_ids, limit) | {"input_role": "strain_reference"}

    def search_annotations(self, query: str, limit: int = 30) -> dict:
        return super().search_annotations(query, limit) | {"input_role": "strain_reference"}


def load_strain_reference(root: Path, expected_id: str) -> StrainReferenceProfile:
    from .profiles import load_profile

    try:
        m = _StrainManifest.model_validate_json((root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProfileError(f"Invalid strain reference manifest: {root / 'manifest.json'}") from exc
    if m.profile_id != expected_id or not _PROFILE_ID.fullmatch(m.profile_id):
        raise ProfileError("Strain reference profile identity differs from its directory")
    if not m.reference_profiles or set(m.reference_profiles) - set(MODALITIES):
        raise ProfileError("Strain references require one native pointer per declared canonical modality")
    if set(m.selection_reasons) - set(m.reference_profiles) or any(not reason.strip() for reason in m.selection_reasons.values()):
        raise ProfileError("Selection reasons must describe declared strain reference modalities")
    sources = {}
    for name, profile_id in m.reference_profiles.items():
        if not _PROFILE_ID.fullmatch(profile_id) or profile_id == expected_id:
            raise ProfileError("Invalid native strain reference pointer")
        path = root.parent / profile_id / "manifest.json"
        try:
            version = json.loads(path.read_text(encoding="utf-8")).get("schema_version")
        except (OSError, ValueError, AttributeError) as exc:
            raise ProfileError(f"Native strain reference not readable: {profile_id}") from exc
        if version not in {"praxis.organism-profile.v1", "praxis.organism-profile.v2"}:
            raise ProfileError("Strain references must point directly to native organism profiles")
        source = load_profile(profile_id, root.parent).select_modalities([name])
        overview = source.overview()
        if overview["species"] != m.species.model_dump():
            raise ProfileError(f"{name} reference species differs from the declared strain species")
        if overview["strain"] != m.strain or m.strain == m.species.scientific_name:
            raise ProfileError(f"{name} reference strain differs or is unknown; aliases are not inferred")
        if overview["genotype"] != m.genotype:
            raise ProfileError(f"{name} reference genotype differs; mutants and derivatives cannot be combined")
        sources[name] = source
    return StrainReferenceProfile(m, sources, validate_selection(None, tuple(sources)))
