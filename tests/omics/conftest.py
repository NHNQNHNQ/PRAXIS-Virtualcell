"""Small, explicitly synthetic source tables for the baseline import contract."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from praxis_virtualcell.omics.prepare_ab5075 import prepare_ab5075_profile


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def baseline_sources(tmp_path):
    root = tmp_path / "sources"
    arrays = root / "abwm/delta_response_v1/ab5075/arrays.npz"
    arrays.parent.mkdir(parents=True)
    # Accessing any forbidden array with allow_pickle=False would raise.
    poison = np.array([{"not_baseline": True}], dtype=object)
    np.savez_compressed(arrays, genes=np.array(["ABUW_0001", "ABUW_0002"]),
                        control=np.array([[0.0, 4.5]], dtype=np.float32),
                        treated=poison, delta=poison, mic=poison)
    write_csv(root / "abwm/delta_response_v1/ab5075/pairs.csv", [{
        "pair_id": "AZI:AZI_003", "strain": "AB5075", "study": "PRJNA658638",
        "control_ids": json.dumps(["Abaum_0017", "Abaum_0023"]),
        "pairing": "untreated reference", "time_h": "", "control_expression_row": "0",
    }])
    write_csv(root / "abaumprecise/raw_data/metadata.csv", [{
        "Experiment": sample, "strain_description": "AB5075", "reference_sequence": "AB5075",
        "base_media": "CA-MHB", "condition_name": "AZI_000", "reference_condition": "AZI_000",
        "time": "0", "temperature": "0", "growth_phase": "0", "genotype": "0",
    } for sample in ("Abaum_0017", "Abaum_0023")])
    write_csv(root / "abaumprecise/interim/metadata_qc.csv", [{"fixture": "synthetic"}])
    write_csv(root / "abwm/ortholog_response_v1/orthology/reference_features.csv", [{
        "reference": "AB5075_original", "key": f"AB5075_original|{gene}", "locus_tag": gene,
        "gene": symbol, "product": product, "protein_id": protein, "contig": "CP008706.1",
    } for gene, symbol, product, protein in [
        ("ABUW_0001", "dnaA", "fixture replication protein", "fixture-protein-1"),
        ("ABUW_0002", "", "fixture unannotated symbol", ""),
    ]])
    write_csv(root / "abwm/ortholog_response_v1/expression_ortholog_mapping.csv", [{
        "domain": "ab5075", "original_id": gene, "reference_key": f"AB5075_original|{gene}",
        "mapping_evidence": "fixture_exact_reference",
    } for gene in ("ABUW_0001", "ABUW_0002")])
    return root


@pytest.fixture
def tiny_profile_root(tmp_path, baseline_sources):
    root = tmp_path / "profiles"
    prepare_ab5075_profile(root, baseline_sources)
    return root
