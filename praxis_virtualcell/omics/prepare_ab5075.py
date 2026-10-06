"""Rebuild a baseline-only AB5075 profile from the declared local source tables."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np

from praxis_virtualcell.omics.npz_adapter import extract_ab5075_azi000, native_annotations
from praxis_virtualcell.omics.profiles import DEFAULT_PROFILE_ID, ProfileError, _data_root, load_profile


_SOURCE_PATHS = {
    "arrays": "abwm/delta_response_v1/ab5075/arrays.npz",
    "pairs": "abwm/delta_response_v1/ab5075/pairs.csv",
    "reference": "abwm/ortholog_response_v1/orthology/reference_features.csv",
    "mapping": "abwm/ortholog_response_v1/expression_ortholog_mapping.csv",
    "metadata": "abaumprecise/raw_data/metadata.csv",
    "metadata_qc": "abaumprecise/interim/metadata_qc.csv",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare_ab5075_profile(data_root=None, source_root=None) -> Path:
    """Build and verify one new profile without altering its source files."""
    root = _data_root(data_root).resolve()
    sources = Path(source_root).resolve() if source_root is not None else root / "_sources"
    paths = {key: sources / relative for key, relative in _SOURCE_PATHS.items()}
    for path in paths.values():
        if not path.is_file():
            raise ProfileError(f"Declared local source file is missing: {path}")
    target = root / DEFAULT_PROFILE_ID
    if target.exists():
        raise ProfileError(f"Profile already exists; choose a new output data root: {target}")
    baseline = extract_ab5075_azi000(paths["arrays"], paths["pairs"], paths["metadata"])
    annotations = native_annotations(baseline["genes"], paths["reference"], paths["mapping"])
    hashes = {key: _sha256(path) for key, path in paths.items()}

    def locator(key):
        path = paths[key]
        return str(path.relative_to(root)) if path.is_relative_to(root) else str(path)

    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ab5075-build-", dir=root, ignore_cleanup_errors=True) as temporary:
        staged = Path(temporary) / DEFAULT_PROFILE_ID
        staged.mkdir()
        np.savez_compressed(staged / "baseline.npz", genes=baseline["genes"], expression=baseline["expression"])
        with (staged / "annotations.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(annotations[0]))
            writer.writeheader()
            writer.writerows(annotations)

        def asset(name):
            path = staged / name
            return {"path": name, "size_bytes": path.stat().st_size, "sha256": _sha256(path)}

        manifest = {
            "schema_version": "praxis.organism-profile.v1", "profile_id": DEFAULT_PROFILE_ID,
            "species": {"scientific_name": "Acinetobacter baumannii", "taxonomy_id": "NCBITaxon:470"},
            "strain": "AB5075", "genotype": None, "modality": "bulk_RNA_seq",
            "feature_namespace": "ABUW native locus tags", "unit": "author_log2_TPM_QC", "scale": baseline["scale"],
            "value_semantics": "Unscaled author log2 TPM QC expression; arithmetic mean of the two declared untreated source profiles; offset not independently verified.",
            "observation_unit": "historical_condition_mean",
            "condition": {"condition_id": "AZI_000", "role": "untreated_reference", "medium": "CA-MHB",
                          "time_h": None, "temperature_c": None, "growth_phase": None},
            "expression": asset("baseline.npz"), "annotations": asset("annotations.csv"),
            "provenance": {
                "study_id": "PRJNA658638", "source_samples": baseline["source_samples"],
                "expression_source": {"path": locator("arrays"), "sha256": hashes["arrays"],
                                      "array_key": "control", "row_index": baseline["source_row_index"], "pair_id": "AZI:AZI_003",
                                      "pairs_path": locator("pairs"), "aggregation": "historical arithmetic condition mean; source members explicitly retained"},
                "metadata_source": {"path": locator("metadata"), "sha256": hashes["metadata"], "qc_path": locator("metadata_qc"),
                                    "identity_field": "Experiment", "unknown_value_policy": "Author placeholders 0 in time/temperature/growth/genotype metadata are not measured biological values."},
                "annotation_source": {"reference_path": locator("reference"), "reference_sha256": hashes["reference"],
                                      "mapping_path": locator("mapping"), "mapping_sha256": hashes["mapping"], "reference_namespace": "AB5075_original",
                                      "reference_accessions": sorted({row["contig"] for row in annotations}),
                                      "sequence_role": "Reference annotation/translation; not sample-specific measured proteomics or a newly sequenced isolate."},
                "citation": "AbaumPRECISE author expression and source metadata, PRJNA658638; frozen delta_response_v1 and ortholog_response_v1 local delivery.",
                "terms": {"usage": "local_research_copy", "redistribution_approved": False, "license_status": "Upstream dataset redistribution terms have not been verified."},
                "input_role": "Historical unexposed reference in a specified medium; not an observed state for a new candidate after treatment.",
            },
        }
        (staged / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        load_profile(DEFAULT_PROFILE_ID, data_root=temporary)
        os.rename(staged, target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", help="Output root for the new AB5075-AZI000 profile")
    parser.add_argument("--source-root", help="Local source directory containing abwm/ and abaumprecise/")
    args = parser.parse_args()
    try:
        profile = prepare_ab5075_profile(args.data_root, args.source_root)
    except ProfileError as exc:
        parser.exit(2, f"{exc}\n")
    print(profile)


if __name__ == "__main__":
    main()
