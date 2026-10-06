"""Select the verified historical AB5075 AZI_000 untreated reference only."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from praxis_virtualcell.omics.profiles import ProfileError


AB5075_CONTROL_SAMPLES = ("Abaum_0017", "Abaum_0023")
AB5075_SCALE = "author_log2_tpm_qc_unscaled_ABUW_namespace"


def extract_ab5075_azi000(arrays_path: str | Path, pairs_path: str | Path, metadata_path: str | Path) -> dict:
    """Read only genes and one control row; never read treated, delta, or MIC."""
    with Path(pairs_path).open(encoding="utf-8", newline="") as stream:
        pairs = list(csv.DictReader(stream))
    selected = [row for row in pairs if row["pair_id"] == "AZI:AZI_003"]
    if len(selected) != 1:
        raise ProfileError("The verified AZI_000 reference pair must be unique")
    pair = selected[0]
    controls = json.loads(pair["control_ids"])
    if (pair["strain"] != "AB5075" or pair["study"] != "PRJNA658638"
            or set(controls) != set(AB5075_CONTROL_SAMPLES) or len(controls) != 2
            or "untreated reference" not in pair["pairing"]):
        raise ProfileError("The pair does not identify the verified untreated AB5075 reference")
    if pair["time_h"].strip():
        raise ProfileError("AZI_000 reference exposure time is unreported, not an inferred endpoint")
    row_index = int(pair["control_expression_row"])
    with Path(metadata_path).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    meta = [row for row in rows if row["Experiment"] in controls]
    if len(meta) != 2 or {row["Experiment"] for row in meta} != set(controls):
        raise ProfileError("Untreated source sample metadata is missing or duplicated")
    for row in meta:
        expected = {"strain_description": "AB5075", "reference_sequence": "AB5075",
                    "base_media": "CA-MHB", "condition_name": "AZI_000", "reference_condition": "AZI_000"}
        if any(row[key] != value for key, value in expected.items()):
            raise ProfileError("Source strain, medium, or untreated condition does not match AZI_000")
    try:
        with np.load(arrays_path, allow_pickle=False) as archive:
            genes = archive["genes"].copy()
            control = archive["control"]
            if control.ndim != 2 or len(control) != len(pairs) or not 0 <= row_index < len(control):
                raise ProfileError("Control row cannot be matched to its source pair")
            expression = control[row_index].copy()
    except (OSError, ValueError, KeyError) as exc:
        raise ProfileError("The source measured control array cannot be read") from exc
    if genes.ndim != 1 or expression.shape != genes.shape or not np.isfinite(expression).all():
        raise ProfileError("Control expression and native gene IDs are inconsistent")
    return {"genes": genes, "expression": expression, "source_samples": list(AB5075_CONTROL_SAMPLES),
            "condition_id": "AZI_000", "medium": "CA-MHB", "scale": AB5075_SCALE,
            "source_array_key": "control", "source_row_index": row_index,
            "observation_unit": "historical_condition_mean"}


def native_annotations(genes, reference_path: str | Path, mapping_path: str | Path) -> list[dict]:
    """Join exact AB5075 original reference keys, retaining source table line numbers."""
    with Path(reference_path).open(encoding="utf-8", newline="") as stream:
        reference_rows = list(csv.DictReader(stream))
    references = {}
    for line, row in enumerate(reference_rows, start=2):
        if row["reference"] == "AB5075_original":
            if row["key"] in references:
                raise ProfileError("AB5075 original reference keys are ambiguous")
            references[row["key"]] = (line, row)
    mappings = {}
    with Path(mapping_path).open(encoding="utf-8", newline="") as stream:
        for line, row in enumerate(csv.DictReader(stream), start=2):
            if row["domain"] == "ab5075":
                if row["original_id"] in mappings:
                    raise ProfileError("Native AB5075 feature mapping is ambiguous")
                mappings[row["original_id"]] = (line, row)
    result = []
    for gene_id in genes:
        if gene_id not in mappings:
            raise ProfileError(f"Native AB5075 mapping missing: {gene_id}")
        mapping_line, mapping = mappings[gene_id]
        if not mapping["reference_key"].startswith("AB5075_original|") or mapping["reference_key"] not in references:
            raise ProfileError(f"Mapping has no exact original AB5075 reference: {gene_id}")
        reference_line, reference = references[mapping["reference_key"]]
        if reference["locus_tag"] != gene_id:
            raise ProfileError(f"Native locus does not agree with its reference annotation: {gene_id}")
        result.append({"gene_id": str(gene_id), "gene_symbol": reference["gene"],
                       "product": reference["product"], "protein_id": reference["protein_id"],
                       "contig": reference["contig"], "reference_key": mapping["reference_key"],
                       "mapping_evidence": mapping["mapping_evidence"],
                       "reference_row": reference_line, "mapping_row": mapping_line})
    return result
