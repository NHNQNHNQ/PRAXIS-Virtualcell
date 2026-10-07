"""Prepare verified AB5075 AZI_000 expression columns from the author QC matrix.

Original files are referenced, never copied. Author columns are observations;
distinct columns/runs are not asserted to be independent biological replicates.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path

import numpy as np

from praxis_virtualcell.omics.npz_adapter import AB5075_CONTROL_SAMPLES, AB5075_SCALE
from praxis_virtualcell.omics.profiles import ProfileError, load_profile

_QC_FLAGS = ("passed_fastqc", "passed_reads_mapped_to_CDS", "passed_global_correlation",
             "passed_similar_replicates", "passed_number_replicates")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rows(path: Path) -> tuple[list[str], list[tuple[int, dict]]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if not fields or len(fields) != len(set(fields)):
            raise ProfileError(f"Missing or duplicate CSV columns: {path}")
        result = []
        for line, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                raise ProfileError(f"CSV row does not match its header: {path}:{line}")
            result.append((line, row))
        return fields, result


def _sample_metadata(raw_rows, qc_rows, sample_id: str) -> dict:
    raw = [(line, row) for line, row in raw_rows if row.get("Experiment") == sample_id]
    qc = [(line, row) for line, row in qc_rows if row.get("") == sample_id]
    if len(raw) != 1 or len(qc) != 1:
        raise ProfileError(f"Native raw/QC metadata must identify {sample_id} exactly once")
    raw_line, metadata = raw[0]
    qc_line, quality = qc[0]
    expected = {"reference_sequence": "AB5075", "strain_description": "AB5075", "base_media": "CA-MHB",
                "reference_condition": "AZI_000"}
    if (any(metadata.get(key) != value or quality.get(key) != value for key, value in expected.items())
            or metadata.get("project_name") != "AB5075_AZI" or metadata.get("condition_name") != "AZI_000"
            or quality.get("project") != "AB5075_AZI" or quality.get("condition") != "AZI_000"
            or metadata.get("BioProject") != "PRJNA658638"):
        raise ProfileError(f"{sample_id} does not match the verified untreated AB5075 AZI_000 identity")
    if any(quality.get(flag) != "TRUE" for flag in _QC_FLAGS):
        raise ProfileError(f"{sample_id} does not pass all declared author QC checks")
    run, biosample = metadata.get("Run", ""), metadata.get("BioSample", "")
    if not run or run in {"0", "unknown"} or not biosample or biosample in {"0", "unknown"}:
        raise ProfileError(f"{sample_id} requires an explicit source run and BioSample")
    # Keep uncertainty instead of turning author's metadata placeholders into zeros.
    return {"author_sample_id": sample_id, "run_accession": run, "biosample_accession": biosample,
            "raw_metadata_line": raw_line, "qc_metadata_line": qc_line,
            "biological_replicate_independence": "not_established",
            "metadata_unknown_policy": "Author 0 placeholders are unknown, not measured biological zeros."}


def prepare_baseline_samples(source_root: str | Path, data_root: str | Path,
                             sample_ids: list[str] | None = None,
                             reference_baseline: str | Path | None = None) -> list[Path]:
    """Export the two verified AZI_000 columns; never infer samples from a mean."""
    sources, root = Path(source_root).resolve(), Path(data_root).resolve()
    selected = list(AB5075_CONTROL_SAMPLES) if sample_ids is None else sample_ids
    if (not isinstance(selected, list) or not selected or len(set(selected)) != len(selected)
            or any(sample not in AB5075_CONTROL_SAMPLES for sample in selected)):
        raise ProfileError("Only explicitly verified Abaum_0017 and Abaum_0023 columns are supported")
    paths = {"expression": sources / "interim/log_tpm_qc.csv", "raw_metadata": sources / "raw_data/metadata.csv",
             "qc_metadata": sources / "interim/metadata_qc.csv", "gene_info": sources / "external/gene_info.csv"}
    if any(not path.is_file() for path in paths.values()):
        raise ProfileError("Missing author source files: " + ", ".join(str(path) for path in paths.values() if not path.is_file()))
    raw_fields, raw_rows = _rows(paths["raw_metadata"])
    qc_fields, qc_rows = _rows(paths["qc_metadata"])
    identities = {sample: _sample_metadata(raw_rows, qc_rows, sample) for sample in selected}
    gene_fields, gene_rows = _rows(paths["gene_info"])
    if not {"locus_tag", "gene_name", "gene_product"}.issubset(gene_fields):
        raise ProfileError("Author gene_info requires native locus_tag, gene_name, and gene_product")
    annotations = {}
    for line, row in gene_rows:
        native_id = row["locus_tag"]
        if native_id in annotations:
            raise ProfileError("Author native locus tag annotation is ambiguous")
        annotations[native_id] = (line, row)
    fields, expression_rows = _rows(paths["expression"])
    if fields[0] != "Geneid" or not set(AB5075_CONTROL_SAMPLES).issubset(fields):
        raise ProfileError("Author QC matrix must have Geneid rows and the two verified individual columns")
    genes, values = [], {sample: [] for sample in AB5075_CONTROL_SAMPLES}
    seen = set()
    for line, row in expression_rows:
        gene_id = row["Geneid"]
        if not gene_id.startswith("ABUW_") or gene_id != gene_id.strip() or gene_id in seen or gene_id not in annotations:
            raise ProfileError("Expression features must be unique, annotated native ABUW locus tags")
        seen.add(gene_id)
        genes.append(gene_id)
        for sample in AB5075_CONTROL_SAMPLES:
            try:
                number = float(row[sample])
            except ValueError as exc:
                raise ProfileError(f"Invalid measured expression: {sample}/{gene_id}") from exc
            if not math.isfinite(number):
                raise ProfileError("Author expression must be finite; missing values cannot be filled")
            values[sample].append(number)
    if not genes:
        raise ProfileError("Author QC expression matrix is empty")
    comparison = {"performed": False, "reason": "Frozen historical mean was not supplied; no mean was split or invented."}
    frozen = Path(reference_baseline) if reference_baseline is not None else root / "AB5075-AZI000/baseline.npz"
    if frozen.is_file():
        with np.load(frozen, allow_pickle=False) as archive:
            if set(archive.files) != {"genes", "expression"}:
                raise ProfileError("Reference baseline must be the baseline-only NPZ, not a response archive")
            ids = archive["genes"].tolist()
            positions = {gene: index for index, gene in enumerate(genes)}
            if set(ids) != set(genes) or len(ids) != len(genes):
                raise ProfileError("Author native features do not match the frozen AZI_000 reference")
            mean = np.mean([values[sample] for sample in AB5075_CONTROL_SAMPLES], axis=0)
            actual = np.asarray([mean[positions[gene]] for gene in ids])
            if not np.allclose(actual, archive["expression"], rtol=1e-6, atol=1e-6):
                raise ProfileError("Individual author columns do not reproduce the frozen baseline mean")
            comparison = {"performed": True, "matches": True, "reference_path": str(frozen.resolve()),
                          "reference_sha256": _sha256(frozen), "max_absolute_difference":
                          float(np.max(np.abs(actual - archive["expression"])))}
    targets = [root / f"AB5075-{sample}" for sample in selected]
    if any(target.exists() for target in targets):
        raise ProfileError("Profile already exists; this preparer never overwrites source or profile files")
    hashes = {key: _sha256(path) for key, path in paths.items()}
    species = {"scientific_name": "Acinetobacter baumannii", "taxonomy_id": "NCBITaxon:470"}
    condition = {"condition_id": "AZI_000", "role": "untreated_reference", "medium": "CA-MHB",
                 "time_h": None, "temperature_c": None, "growth_phase": None}
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ab-individual-build-", dir=root, ignore_cleanup_errors=True) as temporary:
        stage_root = Path(temporary)
        for sample, target in zip(selected, targets):
            staged = stage_root / target.name
            staged.mkdir()
            table = staged / "transcriptome.json"
            records = []
            for index, (line, row) in enumerate(expression_rows):
                gene = genes[index]
                annotation_line, annotation = annotations[gene]
                records.append({"feature_id": gene, "gene_id": gene,
                                "gene_symbol": annotation["gene_name"] or None,
                                "product": annotation["gene_product"] or None,
                                "expression_value": values[sample][index],
                                "source_locator": {"path": str(paths["expression"]), "row": line,
                                                   "accession": None, "record_id": sample}})
            table.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            identity = identities[sample]
            citation = (f"AbaumPRECISE PRJNA658638 author QC matrix; native column {sample}, "
                        f"Run {identity['run_accession']}, BioSample {identity['biosample_accession']}; "
                        f"raw metadata {paths['raw_metadata']}:{identity['raw_metadata_line']}; "
                        f"QC metadata {paths['qc_metadata']}:{identity['qc_metadata_line']}; "
                        f"annotation by exact locus_tag in {paths['gene_info']}. "
                        "Distinct author columns/runs are not verified independent biological replicates.")
            modality = {
                "species": species, "strain": "AB5075", "genotype": None, "condition": condition,
                "sample_id": sample, "pairing_id": None, "assay": "RNA_seq", "feature_namespace": "ABUW native locus tags",
                "unit": "author_log2_TPM_QC", "scale": AB5075_SCALE,
                "value_semantics": "Individual author QC expression column; unscaled; logarithm offset not independently verified.",
                "observation_unit": "measured_baseline_sample",
                "features": {"path": table.name, "format": "json", "size_bytes": table.stat().st_size,
                             "sha256": _sha256(table)},
                "provenance": {"study_id": "PRJNA658638", "source_samples": [sample], "citation": citation,
                               "terms": {"usage": "local_research_copy", "redistribution_approved": False,
                                         "license_status": "Upstream dataset redistribution terms have not been verified."},
                               "input_role": "measured_pre_treatment"},
            }
            manifest = {"schema_version": "praxis.organism-profile.v2", "profile_id": target.name,
                        "species": species, "strain": "AB5075", "genotype": None, "condition": condition,
                        "pairing": None, "modalities": {"transcriptome": modality}}
            (staged / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
            receipt = {"schema_version": "praxis.baseline-column-source-receipt.v1", **identity,
                       "source_assets": {key: {"path": str(path), "sha256": hashes[key], "size_bytes": path.stat().st_size}
                                         for key, path in paths.items()},
                       "frozen_mean_crosscheck": comparison,
                       "native_annotation_join": "Exact author locus_tag; protein abundance is not inferred."}
            (staged / "source_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
            load_profile(target.name, stage_root)
        for target in targets:
            os.rename(stage_root / target.name, target)
    return targets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, help="AbaumPRECISE author repository/data directory")
    parser.add_argument("--data-root", required=True, help="Organism profile output directory")
    parser.add_argument("--sample", action="append", help="Verified author column; default: both AZI_000 columns")
    parser.add_argument("--reference-baseline", help="Optional existing baseline-only NPZ for numerical mean crosscheck")
    args = parser.parse_args()
    try:
        targets = prepare_baseline_samples(args.source_root, args.data_root, args.sample, args.reference_baseline)
    except (ProfileError, OSError) as exc:
        parser.exit(2, f"{exc}\n")
    print(json.dumps({"profiles": [str(path) for path in targets], "observation_count": len(targets),
                      "biological_replicate_independence": "not_established"}))


if __name__ == "__main__":
    main()
