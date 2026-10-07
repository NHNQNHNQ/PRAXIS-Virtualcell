"""Species backgrounds that point to independently verified source profiles.

These collections deliberately do not assert matching strains, samples or culture
conditions. Source assets and their evidence identifiers remain unchanged.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from .multiomics import MODALITIES, validate_selection
from .profiles import ProfileError, _PROFILE_ID, _Species, _Strict, _limit


class _ReferenceManifest(_Strict):
    schema_version: Literal["praxis.species-reference.v1"]
    profile_id: str
    species: _Species
    reference_profiles: dict[str, str]
    input_role: Literal["species_reference"]
    relation: Literal["species_level_reference"]
    prediction_scope: Literal["species_reference"]
    selection_reasons: dict[str, str] = Field(default_factory=dict)


@dataclass(frozen=True)
class SpeciesReferenceProfile:
    """Selected reference sources; no cross-source biological pairing is implied."""

    _manifest: _ReferenceManifest = field(repr=False)
    _sources: dict[str, Any] = field(repr=False)
    _selected: tuple[str, ...]

    @property
    def profile_id(self) -> str:
        return self._manifest.profile_id

    def select_modalities(self, modalities: list[str] | None = None) -> SpeciesReferenceProfile:
        return replace(self, _selected=validate_selection(modalities, tuple(self._sources)))

    def overview(self) -> dict:
        m = self._manifest
        summaries = {name: self._sources[name].overview() for name in self._selected}
        return {
            "profile_id": self.profile_id, "source_id": f"omics:{self.profile_id}:profile",
            "species": m.species.model_dump(), "strain": None, "genotype": None,
            "condition": {"condition_id": "species_reference", "role": "species_reference",
                          "medium": None, "time_h": None, "temperature_c": None, "growth_phase": None},
            "input_role": m.input_role, "relation": m.relation, "prediction_scope": m.prediction_scope,
            "modality": "+".join(self._selected),
            "available_modalities": [name for name in MODALITIES if name in self._sources],
            "selected_modalities": list(self._selected), "modalities": summaries,
            "reference_profiles": {name: m.reference_profiles[name] for name in self._selected},
            "selection_reasons": {name: m.selection_reasons[name] for name in self._selected if name in m.selection_reasons},
            "feature_count": sum(item["feature_count"] for item in summaries.values()),
            "source_samples": sorted({sample for item in summaries.values() for sample in item.get("source_samples", [])}),
            "unknown_fields": ["prediction_strain", "prediction_condition", "genotype"],
            "pairing": None,
            "source_locator": {"manifest": f"{self.profile_id}/manifest.json"},
            "limitations": [
                "Reference modalities may come from different strains, samples and culture conditions; they are not a matched biological sample.",
                "Source observations describe their recorded reference strains and conditions, not every strain or current state of this species.",
            ],
        }

    def _source(self, name: str):
        if name not in self._selected:
            raise ProfileError(f"Modality is unavailable or unselected: {name}")
        return self._sources[name]

    def _rows(self, name: str, rows: list[dict]) -> list[dict]:
        source = self._sources[name].overview()
        return [copy.deepcopy(row) | {
            "modality": name, "input_role": "species_reference",
            "source_profile_id": source["profile_id"], "source_species": source["species"],
            "source_strain": source["strain"], "source_condition": source["condition"],
        } for row in rows]

    def query_features(self, modality: str, feature_ids: list[str], limit: int = 30) -> dict:
        result = self._source(modality).query_features(modality, feature_ids, limit=limit)
        return result | {"profile_id": self.profile_id, "input_role": "species_reference",
                         "features": self._rows(modality, result["features"])}

    def search_features(self, modality: str, query: str, limit: int = 30) -> dict:
        result = self._source(modality).search_features(modality, query, limit=limit)
        return result | {"profile_id": self.profile_id, "input_role": "species_reference",
                         "features": self._rows(modality, result["features"])}

    def query_genes(self, gene_ids: list[str], limit: int = 30) -> dict:
        limit = _limit(limit)
        results = [(name, self._sources[name].query_genes(gene_ids, limit=100)) for name in self._selected]
        hits = [row for name, result in results for row in self._rows(name, result["genes"])]
        found = {row["gene_id"] for row in hits if row.get("gene_id")}
        return {"profile_id": self.profile_id, "input_role": "species_reference", "genes": hits[:limit],
                "missing_gene_ids": [gene for gene in dict.fromkeys(gene_ids) if gene not in found],
                "truncated": len(hits) > limit or any(result["truncated"] for _, result in results)}

    def search_annotations(self, query: str, limit: int = 30) -> dict:
        limit = _limit(limit)
        results = [(name, self._sources[name].search_annotations(query, limit=100)) for name in self._selected]
        hits = [row for name, result in results for row in self._rows(name, result["genes"])]
        count = sum(result["match_count"] for _, result in results)
        return {"profile_id": self.profile_id, "input_role": "species_reference", "query": query,
                "genes": hits[:limit], "match_count": count, "truncated": count > limit}


def load_species_reference(root: Path, expected_id: str) -> SpeciesReferenceProfile:
    from .profiles import load_profile

    try:
        m = _ReferenceManifest.model_validate_json((root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProfileError(f"Invalid species reference manifest: {root / 'manifest.json'}") from exc
    if m.profile_id != expected_id or not _PROFILE_ID.fullmatch(m.profile_id):
        raise ProfileError("Species reference profile identity differs from its directory")
    if not m.reference_profiles or set(m.reference_profiles) - set(MODALITIES):
        raise ProfileError("Species references require one profile pointer per declared canonical modality")
    if set(m.selection_reasons) - set(m.reference_profiles) or any(not value.strip() for value in m.selection_reasons.values()):
        raise ProfileError("Selection reasons must describe declared reference modalities")
    sources = {}
    for name, profile_id in m.reference_profiles.items():
        if not _PROFILE_ID.fullmatch(profile_id) or profile_id == expected_id:
            raise ProfileError("Invalid source profile pointer")
        # References only point to native profiles, preventing cycles and nested
        # references that would conceal the original biological source identity.
        path = root.parent / profile_id / "manifest.json"
        try:
            version = json.loads(path.read_text(encoding="utf-8")).get("schema_version")
        except (OSError, ValueError, AttributeError) as exc:
            raise ProfileError(f"Reference source profile not readable: {profile_id}") from exc
        if version not in {"praxis.organism-profile.v1", "praxis.organism-profile.v2"}:
            raise ProfileError("Species references must point to native organism profiles")
        source = load_profile(profile_id, root.parent).select_modalities([name])
        if source.overview()["species"] != m.species.model_dump():
            raise ProfileError(f"{name} reference species differs from the declared species")
        sources[name] = source
    return SpeciesReferenceProfile(m, sources, validate_selection(None, tuple(sources)))
