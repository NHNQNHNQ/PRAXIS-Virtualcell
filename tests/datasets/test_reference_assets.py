import json
import io
import zipfile

import pytest

from praxis_virtualcell.datasets.reference_assets import (
    annotation_records, expression_column, genbank_xml_records, read_zip_range_member, write_reference_profile,
)
from praxis_virtualcell.omics import ProfileError, load_profile


def test_numeric_expression_requires_a_complete_native_bridge(tmp_path):
    matrix = tmp_path / "matrix.csv"
    matrix.write_text(",baseline\n0,2.5\n1,0\n")
    with pytest.raises(ProfileError, match="native gene IDs"):
        expression_column(matrix, "baseline")
    bridge = tmp_path / "bridge.csv"
    bridge.write_text("original_gene_id,locus_tag\n0,PA0001\n1,PA0002\n")
    rows = expression_column(matrix, "baseline", crosswalk=bridge)
    assert [(r["gene_id"], r["expression_value"]) for r in rows] == [("PA0001", 2.5), ("PA0002", 0)]
    assert rows[0]["source_locator"]["record_id"] == "0"
    with pytest.raises(ProfileError, match="verified gene bridge source"):
        expression_column(matrix, "baseline", crosswalk=bridge, expected_source_sha256="bad")


def test_reference_translation_is_genome_context_not_abundance(tmp_path):
    source = tmp_path / "reference.csv"
    source.write_text("reference,locus_tag,protein_id,sequence\nref,b0001,NP_1,MAK\n")
    rows = annotation_records(source, "ref")
    assert rows[0]["presence"] is True
    assert "abundance_value" not in rows[0]
    assert "sequence" not in rows[0]
    info = write_reference_profile(
        tmp_path / "profiles", profile_id="EC-reference", species="Escherichia coli", taxon_id=562,
        strain="MG1655", modality="genome", records=rows, sample_id="ref",
        condition={"condition_id": "ref", "role": "sequenced_reference", "medium": None,
                   "temperature_c": None, "time_h": None, "growth_phase": None},
        study_id="ref", source_url="https://www.ncbi.nlm.nih.gov/nuccore/NC_000913.3",
        source_assets=[], assay="assembly_annotation", feature_namespace="native locus tags",
        unit="annotation_presence", scale="boolean", value_semantics="Native CDS annotation presence only",
        selection_reason="Traceable reference coding annotations",
    )
    assert info["status"] == "ready"
    overview = load_profile("EC-reference", tmp_path / "profiles").overview()
    assert overview["available_modalities"] == ["genome"]
    receipt = json.loads((tmp_path / "profiles/EC-reference/source_receipt.json").read_text())
    assert receipt["MIC_pairing_claimed"] is False


def test_genbank_missing_sequence_or_identity_is_rejected(tmp_path):
    path = tmp_path / "record.xml"
    path.write_text("<GBSet><GBSeq><GBSeq_accession-version>NC_1.1</GBSeq_accession-version>"
                    "<GBSeq_organism>Klebsiella pneumoniae</GBSeq_organism>"
                    "<GBSeq_length>100</GBSeq_length></GBSeq></GBSet>")
    with pytest.raises(ProfileError, match="missing or truncated"):
        genbank_xml_records(path, "NC_1.1", "Klebsiella pneumoniae")
    with pytest.raises(ProfileError, match="accession or organism"):
        genbank_xml_records(path, "NC_2.1", "Klebsiella pneumoniae")


def test_split_reference_cds_keeps_one_locus_and_unknown_protein_identity(tmp_path):
    source = tmp_path / "reference.csv"
    source.write_text("reference,locus_tag,protein_id,contig\nref,b0149,NP_1,NC_1\n"
                      "ref,b0149,NP_2,NC_1\n")
    rows = annotation_records(source, "ref")
    assert len(rows) == 1
    assert rows[0]["gene_id"] == "b0149"
    assert rows[0]["protein_id"] is None
    source.write_text("reference,locus_tag,protein_id,contig\nref,b0149,NP_1,NC_1\n"
                      "ref,b0149,NP_2,NC_2\n")
    with pytest.raises(ProfileError, match="different contigs"):
        annotation_records(source, "ref")


def test_downloaded_zip_member_range_checks_native_crc_and_truncation(tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("txt/proteinGroups.txt", "Protein IDs\tLFQ intensity A1\np1\t123\n")
    with zipfile.ZipFile(buffer) as archive:
        info = archive.getinfo("txt/proteinGroups.txt")
    member = {"name": info.filename, "compression": info.compress_type, "crc32": info.CRC,
              "compressed_size": info.compress_size, "uncompressed_size": info.file_size}
    path = tmp_path / "downloaded_range.bin"
    path.write_bytes(buffer.getvalue())
    assert b"p1\t123" in read_zip_range_member(path, member)
    with pytest.raises(ProfileError, match="CRC"):
        read_zip_range_member(path, dict(member, crc32=0))
    path.write_bytes(buffer.getvalue()[:35])
    with pytest.raises(ProfileError, match="truncated"):
        read_zip_range_member(path, member)
