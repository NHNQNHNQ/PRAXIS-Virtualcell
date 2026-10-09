"""Small, strictly scoped cell-structure facts; no sequence-based localization."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CellStructureError(ValueError):
    """A structure catalog or its source scope cannot be verified."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


_UNKNOWN = {"unknown", "unknown strain", "unspecified", "unidentified", "unidentified isolate", "unclassified",
            "not reported", "not provided", "not specified", "none", "null", "n/a", "na", "n.a.", "wt",
            "wild type", "wild-type", "未知", "未报告", "未注明", "野生型"}


def _explicit(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip() and value.casefold() not in _UNKNOWN


class StructureScope(_Strict):
    taxonomy_id: str = Field(pattern=r"^NCBITaxon:[1-9][0-9]*$")
    strain: str | None
    strain_namespace: str | None
    genotype: str | None
    genotype_scope: Literal["not_reported", "declared"]

    @model_validator(mode="after")
    def genotype_is_explicit(self):
        if (self.genotype_scope == "not_reported") != (self.genotype is None):
            raise ValueError("Genotype scope must retain whether a source explicitly declared the genotype")
        if self.genotype is not None and (not self.genotype.strip() or self.genotype != self.genotype.strip()):
            raise ValueError("Declared genotype cannot be blank")
        if self.genotype is not None and self.genotype.casefold() in _UNKNOWN - {"wt", "wild type", "wild-type", "野生型"}:
            raise ValueError("Unreported genotype must remain null")
        return self


class SourceContext(_Strict):
    source_strains: list[str]
    method: str = Field(min_length=1)
    interpretation: str = Field(min_length=1)


class StructureFact(_Strict):
    structure_id: str = Field(min_length=1, max_length=200)
    kind: Literal["compartment", "adjacency", "protein_localization"]
    compartment: str = Field(min_length=1, max_length=100)
    adjacent_to: str | None
    protein_id: str | None
    protein_namespace: str | None
    statement: str = Field(min_length=1)
    evidence_scope: Literal["species_prior", "strain_evidence"]
    scope: StructureScope
    evidence_type: Literal["reference_knowledge", "source_annotation", "measured"]
    source_id: str = Field(min_length=1)
    source_url: str = Field(pattern=r"^https?://[^\s]+$")
    source_locator: dict[str, str] = Field(min_length=1)
    source_context: SourceContext
    condition: dict[str, str | int | float | None] | None

    @model_validator(mode="after")
    def identity_and_kind(self):
        scope = self.scope
        if self.evidence_scope == "species_prior":
            if any(value is not None for value in (scope.strain, scope.strain_namespace, scope.genotype)):
                raise ValueError("Species priors cannot assert a request strain or genotype")
            if self.evidence_type != "reference_knowledge":
                raise ValueError("A species template is reference knowledge, not a measured request cell")
        elif not _explicit(scope.strain) or not _explicit(scope.strain_namespace):
            raise ValueError("Strain evidence requires an explicit strain and namespace")
        if self.kind == "adjacency":
            if not _explicit(self.adjacent_to) or self.adjacent_to == self.compartment:
                raise ValueError("Adjacency requires two distinct compartments")
        elif self.adjacent_to is not None:
            raise ValueError("Only adjacency facts may declare adjacent_to")
        if self.kind == "protein_localization":
            if not _explicit(self.protein_id) or not _explicit(self.protein_namespace):
                raise ValueError("Localization requires native protein identity and namespace")
            if self.evidence_scope != "strain_evidence" or self.evidence_type == "reference_knowledge":
                raise ValueError("Protein localization requires exact-strain source annotation or measurement")
        elif self.protein_id is not None or self.protein_namespace is not None:
            raise ValueError("Compartment membership cannot be inferred from a gene or protein ID")
        if any(not key.strip() or not value.strip() for key, value in self.source_locator.items()):
            raise ValueError("Source locators must contain explicit locations")
        return self


class StructureCatalog(_Strict):
    schema_version: Literal["praxis.cell-structure-catalog.v1"]
    catalog_id: str = Field(min_length=1)
    structures: list[StructureFact]

    @model_validator(mode="after")
    def unique_and_connected(self):
        ids = [item.structure_id for item in self.structures]
        if len(ids) != len(set(ids)):
            raise ValueError("Structure IDs must be unique")
        nodes = {(item.scope.model_dump_json(), item.evidence_scope, item.compartment)
                 for item in self.structures if item.kind == "compartment"}
        for item in self.structures:
            if item.kind == "adjacency":
                for compartment in (item.compartment, item.adjacent_to):
                    if (item.scope.model_dump_json(), item.evidence_scope, compartment) not in nodes:
                        raise ValueError("Adjacency endpoints require compartments with the same source scope")
        return self


def load_catalog(*, data_root: str | Path | None = None,
                 catalog_path: str | Path | None = None) -> StructureCatalog:
    path = Path(catalog_path) if catalog_path is not None else (
        Path(data_root) if data_root is not None else Path(__file__).resolve().parents[2] / "data" / "cell_structure"
    ) / "catalog.json"
    try:
        return StructureCatalog.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CellStructureError(f"Invalid cell structure catalog: {path}") from exc


def _request_scope(overview: dict) -> dict:
    if not isinstance(overview, dict):
        raise ValueError("profile_overview must be an object")
    species = overview.get("species")
    return {"taxonomy_id": species.get("taxonomy_id") if isinstance(species, dict) else None,
            "strain": overview.get("strain"), "strain_namespace": overview.get("strain_namespace"),
            "genotype": overview.get("genotype")}


def _applicable(fact: StructureFact, overview: dict, scope: dict) -> bool:
    if fact.scope.taxonomy_id != scope["taxonomy_id"]:
        return False
    if fact.evidence_scope == "species_prior":
        return True
    if overview.get("input_role") == "species_reference":
        return False
    return (_explicit(scope["strain"]) and _explicit(scope["strain_namespace"])
            and fact.scope.strain == scope["strain"] and fact.scope.strain_namespace == scope["strain_namespace"]
            and fact.scope.genotype == scope["genotype"])


def _result(overview: dict, catalog: StructureCatalog, facts: list[StructureFact], *, match_count: int,
            missing_structure_ids: list[str] | None = None, missing_protein_ids: list[str] | None = None) -> dict:
    scope = _request_scope(overview)
    strain_count = sum(item.evidence_scope == "strain_evidence" for item in facts)
    localization_count = sum(item.kind == "protein_localization" for item in facts)
    gaps = []
    if not facts:
        gaps.append("No cell-structure facts match this exact taxon and query scope.")
    if not strain_count:
        gaps.append("No exact-strain structure evidence was retrieved; species priors do not verify this strain.")
    if not localization_count:
        gaps.append("No native protein localization evidence was retrieved; gene presence does not establish location.")
    if not _explicit(scope["strain_namespace"]) and scope["strain"] is not None:
        gaps.append("The profile has no verified strain namespace; strain evidence cannot be matched.")
    if scope["genotype"] is None:
        gaps.append("Genotype is not reported; wild-type status is unknown.")
    return {"profile_id": overview.get("profile_id"),
            "source_id": f"cell-structure:{catalog.catalog_id}:{scope['taxonomy_id'] or 'unknown'}",
            "catalog_id": catalog.catalog_id, "status": "available" if facts else "unknown",
            "request_scope": scope, "structures": [item.model_dump() for item in facts],
            "match_count": match_count, "truncated": match_count > len(facts),
            "missing_structure_ids": missing_structure_ids or [], "missing_protein_ids": missing_protein_ids or [],
            "coverage": {"species_prior_count": len(facts) - strain_count, "strain_evidence_count": strain_count,
                         "protein_localization_count": localization_count, "current_state_supported": False},
            "gaps": gaps,
            "limitations": ["Source conditions are independent of the profile and prediction conditions.",
                            "Species priors are topology context, not measurements of the requested cell.",
                            "No drug permeability, target engagement, or current structural state is inferred."]}


def cell_structure_overview(profile_overview: dict, *, data_root: str | Path | None = None,
                            catalog_path: str | Path | None = None) -> dict:
    """Return the traceable topology and exact-source coverage for a profile."""
    scope = _request_scope(profile_overview)
    catalog = load_catalog(data_root=data_root, catalog_path=catalog_path)
    facts = [item for item in catalog.structures if _applicable(item, profile_overview, scope)]
    return _result(profile_overview, catalog, facts, match_count=len(facts))


def _ids(values: list[str] | None, name: str) -> list[str] | None:
    if values is None:
        return None
    if (not isinstance(values, list) or not 1 <= len(values) <= 30
            or any(not _explicit(value) or len(value) > 200 for value in values)):
        raise ValueError(f"{name} must contain 1 to 30 explicit IDs")
    return list(dict.fromkeys(values))


def query_cell_structure(profile_overview: dict, *, structure_ids: list[str] | None = None,
                         protein_ids: list[str] | None = None, protein_namespace: str | None = None,
                         compartment: str | None = None, limit: int = 30,
                         data_root: str | Path | None = None, catalog_path: str | Path | None = None) -> dict:
    """Query native localization or topology without alias or species fallback."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 30:
        raise ValueError("limit must be an integer from 1 to 30")
    structure_ids, protein_ids = _ids(structure_ids, "structure_ids"), _ids(protein_ids, "protein_ids")
    if (protein_ids is not None and not _explicit(protein_namespace)
            or protein_namespace is not None and (not _explicit(protein_namespace) or protein_ids is None)):
        raise ValueError("Native protein IDs require their explicit protein_namespace")
    if compartment is not None and not _explicit(compartment):
        raise ValueError("compartment must be an explicit name")
    scope = _request_scope(profile_overview)
    catalog = load_catalog(data_root=data_root, catalog_path=catalog_path)
    facts = [item for item in catalog.structures if _applicable(item, profile_overview, scope)
             and (structure_ids is None or item.structure_id in structure_ids)
             and (protein_ids is None or item.kind == "protein_localization" and item.protein_id in protein_ids
                  and item.protein_namespace == protein_namespace)
             and (compartment is None or item.compartment == compartment)]
    found_structures = {item.structure_id for item in facts}
    found_proteins = {item.protein_id for item in facts}
    return _result(profile_overview, catalog, facts[:limit], match_count=len(facts),
                   missing_structure_ids=[value for value in structure_ids or [] if value not in found_structures],
                   missing_protein_ids=[value for value in protein_ids or [] if value not in found_proteins])
