"""Reference annotation is traceable sequence context, never measured proteomics."""
from __future__ import annotations

from pathlib import Path

import pytest

from praxis_virtualcell.omics import ProfileError
from praxis_virtualcell.omics.prepare_genome import inspect_genome


def _genome(root: Path, *, strain="AR_SYNTHETIC", taxon="562", end=5, circular=False):
    fasta = root / "genome.fna"
    fasta.write_text(">TEST000001.1 synthetic fixture\nAAAAAAAAAA\n")
    gff = root / "genome.gff3"
    gff.write_text(
        "##gff-version 3\n#!genome-build-accession NCBI_Assembly:GCA_TEST.1\n"
        f"TEST000001.1\tNCBI\tregion\t1\t10\t.\t+\t.\tID=region;strain={strain};Dbxref=taxon:{taxon}"
        + (";Is_circular=true" if circular else "") + "\n"
        f"TEST000001.1\tNCBI\tgene\t2\t{end}\t.\t+\t.\tID=gene-A;locus_tag=LOCUS_A;gene=symbolA\n"
        f"TEST000001.1\tNCBI\tCDS\t2\t{end}\t.\t+\t0\tID=cds-A;Parent=gene-A;protein_id=PROTEIN_A;product=Synthetic%3B%20product\n"
        "TEST000001.1\tNCBI\tpseudogene\t6\t8\t.\t-\t.\tID=gene-B;locus_tag=LOCUS_B\n"
    )
    return fasta, gff


def test_reference_genome_preserves_exact_gff_rows_and_cds_annotation(tmp_path):
    fasta, gff = _genome(tmp_path)
    result = inspect_genome(fasta, gff, "GCA_TEST.1")
    assert result["strain"] == "AR_SYNTHETIC"
    assert result["gene_pseudogene_count"] == 2
    row, pseudo = result["features"]
    assert row["source_locator"] == {"path": str(gff), "row": 4, "accession": "GCA_TEST.1", "record_id": "gene-A"}
    assert row["presence"] is True and row["copy_number"] is None and row["variant"] is None
    assert row["product"] == "Synthetic; product" and row["protein_id"] == "PROTEIN_A"
    assert "abundance_value" not in row and "expression_value" not in row
    assert pseudo["product"] == "pseudogene annotation"


@pytest.mark.parametrize("taxon,assembly", [("1", "GCA_TEST.1"), ("562", "different-assembly")])
def test_unresolved_species_or_assembly_identity_is_rejected(tmp_path, taxon, assembly):
    fasta, gff = _genome(tmp_path, taxon=taxon)
    with pytest.raises(ProfileError, match="identity"):
        inspect_genome(fasta, gff, assembly)


def test_circular_origin_is_validated_without_filling_absence_calls(tmp_path):
    fasta, gff = _genome(tmp_path, end=11, circular=True)
    assert inspect_genome(fasta, gff, "GCA_TEST.1")["origin_spanning_gene_count"] == 1
    fasta, gff = _genome(tmp_path, end=11, circular=False)
    with pytest.raises(ProfileError, match="circular-origin"):
        inspect_genome(fasta, gff, "GCA_TEST.1")


def test_ambiguous_cds_protein_annotation_is_not_arbitrarily_selected(tmp_path):
    fasta, gff = _genome(tmp_path)
    with gff.open("a") as stream:
        stream.write("TEST000001.1\tNCBI\tCDS\t2\t5\t.\t+\t0\tID=cds-A2;Parent=gene-A;protein_id=OTHER;product=Other\n")
    row = inspect_genome(fasta, gff, "GCA_TEST.1")["features"][0]
    assert row["protein_id"] is None and row["product"] is None
