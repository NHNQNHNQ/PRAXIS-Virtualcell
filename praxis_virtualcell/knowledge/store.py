"""Read-only retrieval of exact, locally curated mechanistic evidence."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .schemas import KnowledgeCatalog, MechanisticRecord


DEFAULT_CATALOG_PATH = Path(__file__).resolve().parents[2] / "local/data_readiness_20261007/knowledge_catalog.json"
_LIMITATIONS = [
    "Reference gene function/pathway annotations are not experimental compound–protein interactions.",
    "No orthology, compound similarity, or organism activity label is used to infer a new candidate's causal target.",
    "An exact tested compound structure match describes the cited protein assay only, not intracellular target engagement or killing.",
]


def _validate_scope(taxonomy_id: str, strain: str | None, limit: int) -> None:
    if not isinstance(taxonomy_id, str) or not re.fullmatch(r"NCBITaxon:[1-9][0-9]*", taxonomy_id):
        raise ValueError("taxonomy_id must be an exact NCBITaxon identifier")
    if strain is not None and (not isinstance(strain, str) or not strain.strip()):
        raise ValueError("strain must be an exact nonempty identifier or None")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer from 1 through 100")


def _string_ids(value: list[str], name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{name} must be a list of exact nonempty identifiers")
    return list(dict.fromkeys(value))


def _load(path: str | Path | None) -> tuple[KnowledgeCatalog | None, str | None]:
    try:
        content = (Path(path) if path is not None else DEFAULT_CATALOG_PATH).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, "catalog_not_found"
    except (OSError, UnicodeError):
        return None, "catalog_unreadable"
    try:
        return KnowledgeCatalog.model_validate_json(content), None
    except (ValidationError, ValueError):
        # Never return an invalid catalog's raw data, which could contain labels.
        return None, "catalog_invalid"


def _response(catalog: KnowledgeCatalog | None, reason: str | None, records: list[MechanisticRecord]) -> dict[str, Any]:
    return {
        "schema_version": "praxis.mechanistic-query.v1",
        "status": "unavailable" if catalog is None else "available" if records else "empty",
        "reason": reason,
        "catalog_id": catalog.catalog_id if catalog is not None else None,
        "records": [record.model_dump(mode="json") for record in records],
        "limitations": list(dict.fromkeys(_LIMITATIONS + (catalog.limitations if catalog is not None else []))),
        "candidate_causality_supported": False,
    }


def _scope(record: MechanisticRecord, taxonomy_id: str, strain: str | None) -> bool:
    return record.species.taxonomy_id == taxonomy_id and (strain is None or record.species.strain == strain)


def _canonical_structure(smiles: str) -> str:
    if not isinstance(smiles, str) or not smiles.strip():
        raise ValueError("compound_smiles must be a nonempty structure string")
    try:
        from rdkit import Chem
    except ImportError as exc:
        raise RuntimeError("exact compound matching requires the chemistry optional dependency") from exc
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        raise ValueError("compound_smiles is invalid")
    # Do not remove salts, normalize tautomers, strip stereo or use similarity.
    return Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)


def search_mechanistic_evidence(
    taxonomy_id: str, query: str, *, native_ids: list[str] | None = None,
    compound_smiles: str | None = None, strain: str | None = None,
    limit: int = 30, catalog_path: str | Path | None = None,
) -> dict[str, Any]:
    """Search a confirmed taxon/strain; compound queries require exact tested graph.

    A query may be empty when IDs or a compound structure supply the filter.
    Gene symbols are searchable text, but are never accepted as native-ID maps.
    """
    _validate_scope(taxonomy_id, strain, limit)
    if not isinstance(query, str):
        raise ValueError("query must be text")
    ids = _string_ids(native_ids, "native_ids") if native_ids is not None else None
    if not query.strip() and not ids and compound_smiles is None:
        raise ValueError("provide a text query, native IDs, or an exact compound structure")
    candidate_structure = _canonical_structure(compound_smiles) if compound_smiles is not None else None
    catalog, reason = _load(catalog_path)
    found: list[MechanisticRecord] = []
    terms = query.casefold().split()
    if catalog is not None:
        for record in catalog.records:
            if not _scope(record, taxonomy_id, strain):
                continue
            if ids is not None and not set(ids).intersection(item.id for item in record.native_ids):
                continue
            if candidate_structure is not None:
                if record.evidence_type != "compound_protein_interaction":
                    continue
                if _canonical_structure(record.compound_context.tested_smiles) != candidate_structure:
                    continue
            text = " ".join([record.claim, record.gene_symbol or "", record.gene_id or "",
                             record.protein_id or "", record.record_id,
                             *[item.id for item in record.native_ids]]).casefold()
            if not all(term in text for term in terms):
                continue
            found.append(record)
            if len(found) == limit:
                break
    result = _response(catalog, reason, found)
    result["requested_scope"] = {"taxonomy_id": taxonomy_id, "strain": strain, "native_ids": ids}
    result["compound_match_policy"] = "exact_stereochemical_graph" if candidate_structure is not None else None
    return result


def query_mechanistic_evidence(
    taxonomy_id: str, record_ids: list[str], *, strain: str | None = None,
    limit: int = 30, catalog_path: str | Path | None = None,
) -> dict[str, Any]:
    """Retrieve record identities only within the exact requested organism scope."""
    _validate_scope(taxonomy_id, strain, limit)
    ids = _string_ids(record_ids, "record_ids")
    catalog, reason = _load(catalog_path)
    eligible = {record.record_id: record for record in catalog.records
                if _scope(record, taxonomy_id, strain)} if catalog is not None else {}
    found = [eligible[identifier] for identifier in ids if identifier in eligible][:limit]
    result = _response(catalog, reason, found)
    result["requested_scope"] = {"taxonomy_id": taxonomy_id, "strain": strain}
    result["missing_record_ids"] = [identifier for identifier in ids if identifier not in eligible]
    result["truncated"] = sum(identifier in eligible for identifier in ids) > limit
    return result


def catalog_overview(catalog_path: str | Path | None = None) -> dict[str, Any]:
    """Report local readiness without leaking cached assay or document content."""
    catalog, reason = _load(catalog_path)
    result = _response(catalog, reason, [])
    if catalog is not None:
        result["status"] = "available" if catalog.records else "empty"
    result["record_count"] = len(catalog.records) if catalog is not None else 0
    result["evidence_type_counts"] = {
        kind: sum(record.evidence_type == kind for record in catalog.records) if catalog is not None else 0
        for kind in ("gene_function", "pathway", "compound_protein_interaction")
    }
    return result
