"""A curated mechanism contract without whole-cell efficacy measurements.

Reference gene annotations and measurements on identified proteins are separate
evidence types. Neither type proves a new candidate's intracellular target.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SpeciesIdentity(Contract):
    scientific_name: str = Field(min_length=1)
    taxonomy_id: str = Field(pattern=r"^NCBITaxon:[1-9][0-9]*$")
    strain: str | None
    identity_basis: str = Field(min_length=1)


class NativeIdentifier(Contract):
    namespace: str = Field(min_length=1)
    id: str = Field(min_length=1)


class SourceLocator(Contract):
    path: str = Field(min_length=1)
    table: str = Field(min_length=1)
    row: int | None = Field(default=None, ge=1, description="Physical CSV line, including header, when applicable")
    key_field: str = Field(min_length=1)
    key_value: str = Field(min_length=1)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class LicenseBoundary(Contract):
    usage: Literal["local_research_copy", "redistribution_permitted"]
    license_name: str | None
    license_status: str = Field(min_length=1)
    redistribution_approved: bool

    @model_validator(mode="after")
    def require_redistribution_basis(self) -> "LicenseBoundary":
        if self.usage == "redistribution_permitted" and (not self.redistribution_approved or not self.license_name):
            raise ValueError("redistribution requires an explicitly verified named license")
        return self


class EvidenceSource(Contract):
    citation: str = Field(min_length=1)
    doi: str | None = Field(default=None, pattern=r"^10\.[0-9]{4,9}/\S+$")
    url: str = Field(pattern=r"^https://[^\s]+$")
    source_locator: SourceLocator
    supporting_locators: list[SourceLocator] = Field(default_factory=list)
    terms: LicenseBoundary


class CompoundContext(Contract):
    source_compound_id: str = Field(min_length=1)
    tested_smiles: str = Field(min_length=1)
    structure_context: str = Field(min_length=1, description="Tested chemical form, stereochemistry, salt and identity limitations")
    inchikey: str | None = Field(default=None, pattern=r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$")
    match_policy: Literal["exact_stereochemical_graph"] = "exact_stereochemical_graph"

    @field_validator("tested_smiles")
    @classmethod
    def require_tested_structure(cls, smiles: str) -> str:
        try:
            from rdkit import Chem
        except ImportError as exc:
            raise ValueError("protein interaction records require the chemistry optional dependency") from exc
        if Chem.MolFromSmiles(smiles) is None:
            raise ValueError("tested_smiles must encode a valid molecular structure")
        return smiles


class ProteinMeasurement(Contract):
    # Deliberately excludes MIC, growth, bacterial survival and organism labels.
    endpoint: Literal["Kd", "Ki", "IC50", "EC50", "occupancy", "complex_observed"]
    value: float | None = Field(default=None, allow_inf_nan=False, ge=0)
    unit: Literal["M", "mM", "uM", "nM", "pM", "fraction", "not_applicable"]
    relation: Literal["=", "<", "<=", ">", ">=", "not_applicable"] = "="


class ProteinAssay(Contract):
    assay_id: str = Field(min_length=1)
    assay_type: Literal["protein_binding", "protein_biochemical", "protein_structure"]
    target_entity: Literal["purified_protein", "recombinant_protein", "identified_protein_complex"]
    target_identity_confirmed: Literal[True]
    assay_species_confirmed: Literal[True]
    interaction_mode: Literal["direct_binding", "biochemical_modulation", "structural_complex"]
    measurement: ProteinMeasurement | None = None

    @model_validator(mode="after")
    def match_assay_to_interpretation(self) -> "ProteinAssay":
        modes = {"protein_binding": "direct_binding", "protein_biochemical": "biochemical_modulation",
                 "protein_structure": "structural_complex"}
        if self.interaction_mode != modes[self.assay_type]:
            raise ValueError("assay type does not establish the claimed interaction mode")
        return self


class MechanisticRecord(Contract):
    record_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9:_.-]*$")
    source_id: str = Field(pattern=r"^knowledge:[A-Za-z0-9][A-Za-z0-9:_.-]*$")
    evidence_type: Literal["gene_function", "pathway", "compound_protein_interaction"]
    support_level: Literal["reference_annotation", "experimental_protein_measurement"]
    species: SpeciesIdentity
    native_ids: list[NativeIdentifier] = Field(min_length=1)
    gene_id: str | None = None
    protein_id: str | None = None
    gene_symbol: str | None = None
    claim: str = Field(min_length=1)
    assay_type: Literal["reference_genome_annotation", "reference_pathway_annotation", "protein_binding", "protein_biochemical", "protein_structure"]
    assay: ProteinAssay | None = None
    compound_context: CompoundContext | None = None
    source: EvidenceSource
    limitations: list[str] = Field(min_length=1)
    candidate_causality_supported: Literal[False] = False

    @field_validator("claim")
    @classmethod
    def reject_whole_cell_labels(cls, claim: str) -> str:
        if re.search(r"\bMIC\b|minimum\s+inhibitory\s+concentration|minimum\s+bactericidal\s+concentration|\bMBC\b|整菌药效|最[小低]抑菌浓度", claim, re.IGNORECASE):
            raise ValueError("whole-cell efficacy labels are not mechanistic evidence")
        return claim

    @model_validator(mode="after")
    def separate_annotation_from_interaction(self) -> "MechanisticRecord":
        if self.source_id != f"knowledge:{self.record_id}":
            raise ValueError("source_id must identify this exact curated record")
        ids = [item.id for item in self.native_ids]
        if len({(item.namespace, item.id) for item in self.native_ids}) != len(self.native_ids):
            raise ValueError("duplicate native identifiers")
        for identifier in (self.gene_id, self.protein_id):
            if identifier is not None and identifier not in ids:
                raise ValueError("gene/protein ID must be explicitly present in native_ids")
        if self.evidence_type == "compound_protein_interaction":
            if (self.support_level != "experimental_protein_measurement" or self.assay is None
                    or self.compound_context is None or not self.protein_id):
                raise ValueError("compound interactions require an identified protein, tested structure and protein assay")
            if self.assay_type != self.assay.assay_type:
                raise ValueError("record assay_type must match the protein assay")
        else:
            expected = "reference_genome_annotation" if self.evidence_type == "gene_function" else "reference_pathway_annotation"
            if self.support_level != "reference_annotation" or self.assay_type != expected:
                raise ValueError("reference annotations must retain their annotation evidence type")
            if self.assay is not None or self.compound_context is not None:
                raise ValueError("a reference annotation cannot establish a compound interaction")
            if self.evidence_type == "gene_function" and not self.gene_id:
                raise ValueError("gene function annotation requires a native gene ID")
        return self


class CatalogExclusion(Contract):
    path: str
    record_count: int | None = Field(default=None, ge=0)
    reason: str = Field(min_length=1)
    license_status: str = Field(min_length=1)


class KnowledgeCatalog(Contract):
    schema_version: Literal["praxis.mechanistic-knowledge.v1"]
    catalog_id: str = Field(min_length=1)
    created_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    records: list[MechanisticRecord]
    limitations: list[str] = Field(min_length=1)
    excluded_assets: list[CatalogExclusion] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_records(self) -> "KnowledgeCatalog":
        if len({record.record_id for record in self.records}) != len(self.records):
            raise ValueError("catalog record IDs must be unique")
        return self
