"""Rebuild seven local reference-annotation records; fetches no external assets.

Run from the repository root:
python -m examples.knowledge.build_catalog --data-root data/organisms \
  --output local/data_readiness_20261007/knowledge_catalog.json
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from praxis_virtualcell.knowledge import KnowledgeCatalog


_GENES = {
    "ABUW_0001": ("dnaA", "AKA29801.1", "chromosomal replication initiator protein DnaA"),
    "ABUW_0960": ("gyrA", "AKA30714.1", "DNA gyrase, A subunit"),
    "ABUW_0004": ("gyrB", "AKA29804.1", "DNA gyrase, B subunit"),
    "ABUW_3590": ("rpoB", "AKA33281.1", "DNA-directed RNA polymerase, beta subunit"),
    "ABUW_3421": ("folA", "AKA33117.1", "dihydrofolate reductase"),
    "ABUW_1741": ("bamA", "AKA31477.1", "outer membrane protein assembly complex BamA"),
    "ABUW_1975": ("adeB", "AKA31705.1", "multidrug efflux protein AdeB"),
}


def _indexed_csv(path: Path, key_field: str) -> dict[str, tuple[int, dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        entries: dict[str, tuple[int, dict[str, str]]] = {}
        for row in reader:
            key = row[key_field]
            if key in entries:
                raise ValueError(f"duplicate source identity: {key}")
            entries[key] = (reader.line_num, row)
        return entries


def build_catalog(data_root: str | Path) -> dict:
    root = Path(data_root)
    manifest = json.loads((root / "AB5075-AZI000/manifest.json").read_text(encoding="utf-8"))
    if manifest["species"] != {"scientific_name": "Acinetobacter baumannii", "taxonomy_id": "NCBITaxon:470"} or manifest["strain"] != "AB5075":
        raise ValueError("organism manifest must retain the exact AB5075 species/strain identity")
    provenance = manifest["provenance"]["annotation_source"]
    reference_rel = provenance["reference_path"]
    mapping_rel = provenance["mapping_path"]
    references = _indexed_csv(root / reference_rel, "key")
    # The delivered table uses one unambiguous native ID within each domain.
    with (root / mapping_rel).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        mappings = {}
        for row in reader:
            if row["domain"] != "ab5075":
                continue
            identifier = row["original_id"]
            if identifier in mappings:
                raise ValueError(f"duplicate AB5075 mapping identity: {identifier}")
            mappings[identifier] = (reader.line_num, row)
    records = []
    for gene_id, (symbol, protein_id, expected_product) in _GENES.items():
        reference_key = f"AB5075_original|{gene_id}"
        reference_row, reference = references[reference_key]
        mapping_row, mapping = mappings[gene_id]
        if (reference["reference"] != "AB5075_original" or reference["locus_tag"] != gene_id
                or reference["gene"] != symbol or reference["protein_id"] != protein_id
                or reference["product"] != expected_product or reference["contig"] != "CP008706.1"
                or mapping["reference_key"] != reference_key
                or mapping["mapping_evidence"] != "exact_unique_within_reference_annotation"):
            raise ValueError(f"source annotation identity changed: {gene_id}")
        record_id = f"AB5075:reference:{gene_id}"
        records.append({
            "record_id": record_id, "source_id": f"knowledge:{record_id}",
            "evidence_type": "gene_function", "support_level": "reference_annotation",
            "species": {"scientific_name": "Acinetobacter baumannii", "taxonomy_id": "NCBITaxon:470",
                        "strain": "AB5075", "identity_basis": "AB5075_original reference annotation; accession CP008706.1; exact native ABUW mapping"},
            "native_ids": [{"namespace": "ABUW locus tag", "id": gene_id},
                           {"namespace": "GenBank protein accession", "id": protein_id}],
            "gene_id": gene_id, "protein_id": protein_id, "gene_symbol": symbol,
            "claim": f"The AB5075 reference annotation assigns {gene_id} ({symbol}) the product: {reference['product']}.",
            "assay_type": "reference_genome_annotation", "assay": None, "compound_context": None,
            "source": {
                "citation": f"AB5075_original reference feature annotation, CP008706.1, {gene_id}, protein accession {protein_id}; frozen ortholog_response_v1 delivery.",
                "doi": None, "url": f"https://www.ncbi.nlm.nih.gov/protein/{protein_id}",
                "source_locator": {"path": f"data/organisms/{reference_rel}", "table": "reference_features.csv",
                                   "row": reference_row, "key_field": "key", "key_value": reference_key,
                                   "sha256": provenance["reference_sha256"]},
                "supporting_locators": [{"path": f"data/organisms/{mapping_rel}", "table": "expression_ortholog_mapping.csv",
                                         "row": mapping_row, "key_field": "original_id", "key_value": gene_id,
                                         "sha256": provenance["mapping_sha256"]}],
                "terms": {"usage": "local_research_copy", "license_name": None,
                          "license_status": "Frozen reference annotation delivery terms have not been independently verified; local provenance hashes do not establish redistribution permission.",
                          "redistribution_approved": False},
            },
            "limitations": ["Product is a reference annotation, not a protein function experiment in the current sample.",
                            "Reference protein identity is not measured proteomic abundance or a sequenced genotype of the current sample.",
                            "This record contains no tested compound and cannot establish a new candidate's binding or causal target."],
            "candidate_causality_supported": False,
        })
    catalog = {
        "schema_version": "praxis.mechanistic-knowledge.v1",
        "catalog_id": "AB5075-reference-seed-20261007", "created_at": "2026-10-07", "records": records,
        "limitations": ["Only seven verified AB5075 reference gene product annotations are curated; this is not an exhaustive mechanism database.",
                        "No curated pathway or experimentally supported compound–protein interaction is currently available.",
                        "The species taxon alone does not establish a native-ID map across strains; exact strain and native IDs must be retained."],
        "excluded_assets": [
            {"path": "data/antibacterial/abaumannii/curated/chembl_assays.json", "record_count": 1753,
             "reason": "All cached assays point to taxon 470 and non-molecular organism target CHEMBL614425. An assay type label, including the single B-labelled record, does not identify a measured protein target. These records are not compound–protein evidence.",
             "license_status": "ChEMBL source metadata states CC BY-SA 3.0; retain attribution and source-specific terms for any later permitted derivative."},
            {"path": "data/antibacterial/abaumannii/curated/chembl_documents.json", "record_count": 488,
             "reason": "Cached document titles and abstracts alone do not establish an exact assayed compound, AB5075 protein identity and protein-specific assay linkage. Raw abstracts are not returned to the prediction tools.",
             "license_status": "ChEMBL metadata provenance is preserved; article text may have distinct publisher terms. No abstract text is copied into this catalog."},
            {"path": "data/antibacterial/abaumannii/curated/chembl_molecules.json", "record_count": 6091,
             "reason": "Chemical identity metadata supplies structures but does not establish a protein interaction. Whole-cell labels and uncurated relationships are excluded from tool results.",
             "license_status": "ChEMBL source metadata states CC BY-SA 3.0; existing raw assets remain local."},
        ],
    }
    return KnowledgeCatalog.model_validate(catalog).model_dump(mode="json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default="data/organisms")
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    catalog = build_catalog(arguments.data_root)
    output = Path(arguments.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"catalog_id": catalog["catalog_id"], "records": len(catalog["records"]), "output": str(output)}))


if __name__ == "__main__":
    main()
