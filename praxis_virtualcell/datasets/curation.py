"""Re-admit historical measured endpoints from source-linked local records.

This module never reads model predictions or calls a model. It does not infer
strain/omics pairing from a species match or replace censor bounds by midpoints.
"""
from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

from .labels import (
    Admission,
    AssayConditions,
    EndpointLabel,
    ExperimentRecord,
    MoleculeIdentity,
    OmicsPairing,
    OrganismIdentity,
    RawMeasurement,
    SourceEvidence,
)

_MASS_FACTORS = {
    "ug/mL": 1, "ug/ml": 1, "µg/mL": 1, "μg/mL": 1,
    "ug.ml-1": 1, "ug.mL-1": 1, "ug ml-1": 1, "ug/mL-1": 1,
    "ug ml(-1)": 1, "ug ml^-1": 1, "ug ml(- 1)": 1,
    "mg/L": 1, "mg/l": 1, "mg l-1": 1, "mg/mL": 1000, "mg/ml": 1000,
}
_NONINDEPENDENT = re.compile(
    r"\b(?:MIC\s*(?:50|90)|potentiat\w*|adjuvant|checkerboard|FICI?|combination|combined|"
    r"synerg\w*|predicted|calculated)\b", re.IGNORECASE,
)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


@lru_cache(maxsize=16384)
def canonical_identity(smiles: str) -> tuple[str, str]:
    """Preserve stereochemistry and every reported fragment; do not desalt."""
    from rdkit import Chem, rdBase

    with rdBase.BlockLogs():
        molecule = Chem.MolFromSmiles(smiles)
        if molecule is None:
            raise ValueError("invalid_source_structure")
        canonical = Chem.MolToSmiles(molecule, isomericSmiles=True)
        identity = Chem.MolToInchiKey(molecule)
    if not identity:
        raise ValueError("unresolved_structure_identity")
    return canonical, identity


def _measurement(value: str) -> tuple[str | None, float]:
    match = re.fullmatch(r"\s*(<=|>=|<|>|=)?\s*([0-9.]+(?:[eE][-+]?\d+)?)\s*",
                         value.replace("≤", "<=").replace("≥", ">="))
    if not match:
        raise ValueError("unsupported_measurement_value")
    number = float(match[2])
    if not math.isfinite(number) or number <= 0:
        raise ValueError("nonpositive_or_nonfinite_measurement")
    return match[1], number


def endpoint_from_curated_mic(row: dict[str, str]) -> EndpointLabel:
    """Only verified mass-unit identities; molar conversions are not guessed."""
    factor = _MASS_FACTORS.get(row.get("raw_unit", ""))
    if factor is None:
        raise ValueError("unsupported_or_unverified_unit")
    embedded_relation, raw_value = _measurement(row["raw_value"])
    relation = embedded_relation or row["relation"]
    if relation not in {"=", "<", "<=", ">", ">="} or relation != row["relation"]:
        raise ValueError("conflicting_or_unsupported_relation")
    value = raw_value * factor
    raw = RawMeasurement(value=row["raw_value"], unit=row["raw_unit"], relation=row["relation"])
    lower = float(row["lower_log2"]) if row.get("lower_log2") else None
    upper = float(row["upper_log2"]) if row.get("upper_log2") else None
    if any(bound is not None and not math.isfinite(bound) for bound in (lower, upper)):
        raise ValueError("nonfinite_curated_bounds")
    expected = (upper if relation in {"<", "<="} else lower)
    if expected is None or not math.isclose(math.log2(value), expected, rel_tol=1e-10, abs_tol=1e-10):
        raise ValueError("raw_measurement_curated_bound_mismatch")
    conversion = f"verified_mass_unit_factor:{factor}; {row['raw_unit']} -> ug/mL"
    if row["censor"] == "interval":
        if relation != "=" or lower is None or upper is None:
            raise ValueError("ambiguous_curated_interval")
        return EndpointLabel(kind="MIC", relation="interval", unit="ug/mL", lower=value,
                             upper=2.0 ** upper, lower_closed=row["lower_closed"] == "True",
                             upper_closed=row["upper_closed"] == "True", raw=raw,
                             conversion=conversion + "; upper_bound_from_curated_upper_log2")
    expected_censor = {"=": "exact", "<": "left", "<=": "left", ">": "right", ">=": "right"}[relation]
    if row["censor"] != expected_censor:
        raise ValueError("curated_censor_relation_mismatch")
    if relation == "=" and (upper is None or upper != lower):
        raise ValueError("exact_measurement_has_conflicting_bounds")
    if relation in {"<", "<="} and lower is not None or relation in {">", ">="} and upper is not None:
        raise ValueError("censored_measurement_has_conflicting_bounds")
    return EndpointLabel(kind="MIC", relation=relation, unit="ug/mL", value=value, raw=raw, conversion=conversion)


def organism_from_assay(assay: dict, row: dict[str, str]) -> OrganismIdentity:
    native = assay.get("assay_strain")
    native = native.strip() if isinstance(native, str) and native.strip() else None
    species = assay.get("assay_organism") or "Acinetobacter baumannii"
    description = row.get("assay_description", "")
    derivative = bool(re.search(r"\b(?:mutant|deleted|deletion|knockout|deficient|derivative)\b|Δ",
                                description, re.IGNORECASE))
    if native:
        # Keep aliases and derivative names intact. Only exact known references
        # receive a normalized identity; a substring is not isolate equivalence.
        label = re.sub(r"^isolate\s+", "", native, flags=re.IGNORECASE)
        if derivative and (re.fullmatch(r"AB5075", label, re.IGNORECASE)
                           or re.fullmatch(r"ATCC\s*[-:]?\s*\d+", label, re.IGNORECASE)):
            return OrganismIdentity(species=species, taxon_id=assay.get("assay_tax_id"),
                                    native_strain_label=native, identity_evidence="conflicting")
        namespace = "study:" + row.get("study", row.get("assay", "unresolved"))
        if re.fullmatch(r"AB5075", label, re.IGNORECASE):
            label = "AB5075"
            namespace = "strain_reference"
        elif re.fullmatch(r"ATCC\s*[-:]?\s*\d+", label, re.IGNORECASE):
            label = "ATCC " + re.search(r"\d+", label)[0]
            namespace = "ATCC"
        return OrganismIdentity(species=species, taxon_id=assay.get("assay_tax_id"), strain=label,
                                strain_namespace=namespace, native_strain_label=native,
                                identity_evidence="structured_assay_strain")
    if derivative:
        return OrganismIdentity(species=species, taxon_id=assay.get("assay_tax_id"), identity_evidence="unresolved")
    found = re.findall(r"\bATCC\s*[-:]?\s*(\d+)\b", description, re.IGNORECASE)
    if len(set(found)) == 1:
        label = "ATCC " + found[0]
        return OrganismIdentity(species=species, taxon_id=assay.get("assay_tax_id"), strain=label,
                                strain_namespace="ATCC", native_strain_label=label,
                                identity_evidence="explicit_assay_description")
    # Do not collapse AB5075 mutants/derivatives into the source strain.
    if re.search(r"\bAB5075\b", description, re.IGNORECASE) and not re.search(r"AB5075[-_]", description, re.IGNORECASE):
        return OrganismIdentity(species=species, taxon_id=assay.get("assay_tax_id"), strain="AB5075",
                                strain_namespace="strain_reference", native_strain_label="AB5075",
                                identity_evidence="explicit_assay_description")
    return OrganismIdentity(species=species, taxon_id=assay.get("assay_tax_id"),
                            identity_evidence="conflicting" if len(set(found)) > 1 else "unresolved")


def conditions_from_assay(assay: dict, description: str) -> AssayConditions:
    observed: dict[str, Any] = {}
    provenance: dict[str, str] = {}
    for index, parameter in enumerate(assay.get("assay_parameters") or []):
        kind = parameter.get("standard_type")
        text = parameter.get("standard_text_value")
        value, unit = parameter.get("standard_value"), parameter.get("standard_units")
        field = None
        if kind == "MEDIA" and isinstance(text, str) and text:
            field, observed_value = "medium", text
        elif kind == "TIME" and value is not None and unit in {"hr", "h", "hour", "hours"}:
            field, observed_value = "exposure_hours", float(value)
        elif kind == "TEMPERATURE" and value is not None and unit in {"C", "degC", "°C"}:
            field, observed_value = "temperature_c", float(value)
        else:
            continue
        if field:
            observed[field] = observed_value
            provenance[field] = f"assay_parameters/{index}"
    if "exposure_hours" not in observed:
        match = re.search(r"\b(?:after|incubated(?:\s+for)?|incubation(?:\s+for)?)\s+"
                          r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|days?)\b", description, re.IGNORECASE)
        if match:
            observed["exposure_hours"] = float(match[1]) * (24 if match[2].lower().startswith("day") else 1)
            provenance["exposure_hours"] = "assay_description:explicit_duration"
    supplement = re.search(r"(\d+(?:\.\d+)?)%\s+([A-Za-z][A-Za-z -]{0,50})\s+supplemented\s+(?:media|medium)",
                           description, re.IGNORECASE)
    if supplement:
        observed["medium_supplements"] = [f"{supplement[1]}% {supplement[2].strip()}"]
        provenance["medium_supplements"] = "assay_description:explicit_supplement"
    for pattern, method in ((r"\b(?:microbroth dilution|broth microdilution)\b", "broth_microdilution"),
                            (r"\bbroth dilution\b", "broth_dilution"),
                            (r"\bagar dilution\b", "agar_dilution")):
        if re.search(pattern, description, re.IGNORECASE):
            observed["method"] = method
            provenance["method"] = "assay_description:explicit_method"
            break
    return AssayConditions(**observed, provenance=provenance)


def curate_abaumannii(repo_root: str | Path) -> tuple[list[ExperimentRecord], list[dict], dict]:
    root = Path(repo_root)
    folder = root / "data/antibacterial/abaumannii/curated"
    metadata = {}
    for kind, id_field in (("assays", "assay_chembl_id"), ("documents", "document_chembl_id"),
                           ("molecules", "molecule_chembl_id")):
        values = json.loads((folder / f"chembl_{kind}.json").read_text())
        metadata[kind] = {item[id_field]: (index, item) for index, item in enumerate(values)}
    records, excluded = [], []
    rows_censor = Counter()
    with (folder / "mic_measurements.csv").open() as stream:
        for line, row in enumerate(csv.DictReader(stream), start=2):
            rows_censor[row["censor"]] += 1
            locator = {"file": "data/antibacterial/abaumannii/curated/mic_measurements.csv", "csv_line": line,
                       "native_activity_id": row["record_id"], "legacy_raw_source_file": row["source_file"]}
            reasons = []
            assay_index, assay = metadata["assays"].get(row["assay"], (None, {}))
            doc_index, document = metadata["documents"].get(row["study"], (None, {}))
            if not assay or not document or row["molecule_id"] not in metadata["molecules"]:
                reasons.append("missing_assay_document_or_molecule_metadata")
            if assay.get("document_chembl_id") != row["study"]:
                reasons.append("assay_document_identity_mismatch")
            if assay.get("assay_tax_id") != 470:
                reasons.append("assay_taxon_not_confirmed_abaumannii")
            description = row.get("assay_description", "")
            if _NONINDEPENDENT.search(description):
                reasons.append("aggregate_combination_potentiation_or_nonexperimental_context")
            try:
                endpoint = endpoint_from_curated_mic(row)
                canonical, key = canonical_identity(row["smiles"])
            except (ValueError, TypeError, OverflowError) as exc:
                reasons.append(str(exc) if isinstance(exc, ValueError) else "invalid_measurement_or_structure")
                excluded.append({"record_id": row["record_id"], "source_locator": locator, "reasons": reasons})
                continue
            if reasons:
                excluded.append({"record_id": row["record_id"], "source_locator": locator, "reasons": reasons})
                continue
            locator.update(assay_metadata_pointer=f"/{assay_index}", document_metadata_pointer=f"/{doc_index}")
            organism = organism_from_assay(assay, row)
            conditions = conditions_from_assay(assay, description)
            pairing = OmicsPairing(status="same_strain_reference", profile_ids=["AB5075-AZI000"]) \
                if organism.strain == "AB5075" else OmicsPairing()
            admission_reasons = ["historical_experimental_MIC_with_linked_source_metadata",
                                 "no_verified_same_isolate_and_condition_omics_pair"]
            if organism.identity_evidence in {"unresolved", "conflicting"}:
                admission_reasons.append("strain_identity_not_resolved")
            if row.get("potential_duplicate") not in {"", "0", "False", "false"}:
                admission_reasons.append("potential_duplicate_requires_grouped_split")
            records.append(ExperimentRecord(
                record_id=f"chembl37:activity:{row['record_id']}",
                molecule=MoleculeIdentity(source_molecule_id=row["molecule_id"], source_parent_id=row.get("parent_id") or None,
                                          canonical_smiles=canonical, identity_key=key),
                organism=organism, conditions=conditions, endpoint=endpoint,
                source=SourceEvidence(
                    source_id=f"chembl37:activity:{row['record_id']}", origin="experimental_database",
                    reported_as_measured=True,
                    measured_qualifier="Historical ChEMBL MIC curation with assay/document links; primary activity snapshot not re-fetched.",
                    native_locator=locator, activity_id=row["record_id"], assay_id=row["assay"],
                    document_id=row["study"], doi=document.get("doi"), license="CC BY-SA 3.0",
                ), pairing=pairing,
                admission=Admission(label_eligible=True, paired_omics_eligible=False, reasons=admission_reasons),
            ))
    explicit = [r for r in records if r.organism.strain is not None]
    ab = [r for r in records if r.organism.strain == "AB5075"]
    summary = {
        "source_rows": sum(rows_censor.values()), "source_censoring": dict(rows_censor),
        "experimental_labels_admitted": len(records), "excluded": len(excluded),
        "canonical_structures": len({r.molecule.canonical_smiles for r in records}),
        "source_parent_groups": len({r.molecule.source_parent_id or r.molecule.source_molecule_id for r in records}),
        "studies": len({r.source.document_id for r in records}),
        "assays": len({r.source.assay_id for r in records}),
        "admitted_censoring": dict(Counter(r.endpoint.censoring for r in records)),
        "excluded_reasons": dict(Counter(reason for r in excluded for reason in r["reasons"])),
        "explicit_strain_records": len(explicit), "unresolved_strain_records": len(records) - len(explicit),
        "strain_identity_qualification": "Source strain labels use study namespaces unless an exact reference ID is present; they are not verified cross-study isolate identities.",
        "strain_counts": dict(Counter(r.organism.strain for r in explicit)),
        "ab5075_records": len(ab), "ab5075_censoring": dict(Counter(r.endpoint.censoring for r in ab)),
        "ab5075_assays": len({r.source.assay_id for r in ab}),
        "ab5075_studies": len({r.source.document_id for r in ab}),
        "conditions_known": {name: sum(getattr(r.conditions, name) is not None for r in records)
                             for name in ("medium", "medium_supplements", "temperature_c", "exposure_hours", "method", "inoculum")},
        "same_isolate_and_condition_omics_pairs": 0,
        "qualification": "Reported historical measurements, not independently re-fetched primary activity records; no paired-omics admission.",
    }
    return records, excluded, summary


def audit_mdr_sources(repo_root: str | Path) -> dict:
    """Count raw source readiness; do not promote incomplete or predicted labels."""
    root = Path(repo_root)
    path = root / "data/mdr_gnb/raw/compound_activity/escherichia_coli_mic_raw.jsonl"
    units, relations = Counter(), Counter()
    count = 0
    if path.exists():
        for line in path.open():
            item = json.loads(line)
            count += 1
            units[str(item.get("standard_units"))] += 1
            relations[str(item.get("standard_relation"))] += 1
    ncbi = []
    for path in sorted((root / "data/mdr_gnb/raw").glob("*/ncbi_amr_phenotypes.tsv")):
        total, numeric = 0, 0
        with path.open() as stream:
            for row in csv.DictReader(stream, delimiter="\t"):
                total += 1
                numeric += bool(row.get("measurement", "").strip())
        ncbi.append({"file": str(path.relative_to(root)), "rows": total, "nonempty_measurement_rows": numeric,
                     "admitted_MIC_labels": 0, "reason": "SIR phenotypes are a separate endpoint, not numeric MIC."})
    return {"ec_compound_raw": {
        "file": "data/mdr_gnb/raw/compound_activity/escherichia_coli_mic_raw.jsonl", "rows": count,
        "units": dict(units), "relations": dict(relations), "admitted_labels": 0,
        "reason": "Missing native activity/assay/document identifiers, strain identity and conditions.",
    }, "ncbi_phenotype_sources": ncbi,
        "ignored_artifacts": ["model predictions and validation y_pred", "golden training-set optimistic anchors"],
    }


def curate_existing_labels(repo_root: str | Path, output_dir: str | Path | None = None) -> dict:
    """Create separate label/input JSONL and an auditable source-readiness record."""
    records, exclusions, ab = curate_abaumannii(repo_root)
    summary = {"schema_version": "praxis.experimental-label-readiness.v1", "abaumannii": ab,
               "mdr_sources": audit_mdr_sources(repo_root), "paired_omics_labels": 0,
               "model_predictions_used": False, "raw_assets_copied": False}
    if output_dir is not None:
        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "experimental_labels.jsonl").write_text(
            "".join(_json(record.model_dump()) + "\n" for record in records), encoding="utf-8")
        (destination / "analysis_inputs.jsonl").write_text(
            "".join(_json({"record_id": record.record_id, "input": record.analysis_input()}) + "\n" for record in records),
            encoding="utf-8")
        (destination / "paired_omics_labels.jsonl").write_text(
            "".join(_json(record.model_dump()) + "\n" for record in records if record.admission.paired_omics_eligible),
            encoding="utf-8")
        (destination / "exclusions.jsonl").write_text(
            "".join(_json(item) + "\n" for item in exclusions), encoding="utf-8")
        (destination / "readiness.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (destination / "experiment_record.schema.json").write_text(
            json.dumps(ExperimentRecord.model_json_schema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary
