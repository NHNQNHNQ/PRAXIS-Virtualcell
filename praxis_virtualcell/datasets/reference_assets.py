"""Build single-modality species reference inputs from traceable source tables.

Reference CDS annotations are genome context, never measured protein abundance.
The caller explicitly selects a baseline sample; species-level association does
not imply that a reference sample is paired to an experimental MIC record.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import struct
import tempfile
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

from praxis_virtualcell.omics import ProfileError, load_profile


def source_receipt(path: str | Path, url: str | None = None) -> dict:
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "source_url": url, "size_bytes": path.stat().st_size,
            "sha256": digest.hexdigest()}


def read_zip_range_member(path: str | Path, member: dict) -> bytes:
    """Read a downloaded ZIP local-header range and verify native member CRC/size.

    This validates this member, not the checksum of an undownloaded full archive.
    The range must begin at the central directory's local-header offset.
    """
    data = Path(path).read_bytes()
    if len(data) < 30 or data[:4] != b"PK\x03\x04":
        raise ProfileError("Downloaded ZIP range does not begin at a member header")
    header = struct.unpack_from("<4s5H3I2H", data)
    flags, method, name_length, extra_length = header[2], header[3], header[-2], header[-1]
    if len(data) < 30 + name_length + extra_length:
        raise ProfileError("ZIP member header is truncated")
    name = data[30:30 + name_length].decode("utf-8")
    if name != member["name"] or method != member["compression"] or flags & 1:
        raise ProfileError("ZIP range differs from the declared unencrypted member")
    start = 30 + name_length + extra_length
    payload = data[start:start + member["compressed_size"]]
    if len(payload) != member["compressed_size"]:
        raise ProfileError("ZIP member download is truncated")
    try:
        result = zlib.decompress(payload, -15) if method == 8 else payload if method == 0 else None
    except zlib.error as exc:
        raise ProfileError("ZIP member decompression failed") from exc
    if result is None or len(result) != member["uncompressed_size"] or zlib.crc32(result) != member["crc32"]:
        raise ProfileError("ZIP member size or CRC differs from the source directory")
    return result


def annotation_records(path: str | Path, reference: str) -> list[dict]:
    """Reuse native CDS/locus annotations without copying nucleotide/protein sequences."""
    path = Path(path).resolve()
    result, seen = [], {}
    with path.open(newline="", encoding="utf-8") as stream:
        for line, row in enumerate(csv.DictReader(stream), 2):
            if row["reference"] != reference:
                continue
            locus = row["locus_tag"]
            if not locus or locus.isdigit():
                raise ProfileError("Reference annotation must have native locus IDs")
            if locus in seen:
                # Split CDS/translations may repeat one native gene. Presence is
                # still one locus; ambiguous protein/function identity stays null.
                item = seen[locus]
                if item["contig"] != (row.get("contig") or None):
                    raise ProfileError("Repeated native locus occurs on different contigs")
                for field, source in (("protein_id", "protein_id"), ("gene_symbol", "gene"), ("product", "product")):
                    if item[field] != (row.get(source) or None):
                        item[field] = None
                continue
            item = {"feature_id": locus, "gene_id": locus,
                           "protein_id": row.get("protein_id") or None,
                           "gene_symbol": row.get("gene") or None,
                           "product": row.get("product") or None,
                           "contig": row.get("contig") or None, "presence": True,
                           "source_locator": {"path": str(path), "row": line,
                                              "accession": reference, "record_id": locus}}
            seen[locus] = item
            result.append(item)
    if not result:
        raise ProfileError(f"Reference not present in annotation table: {reference}")
    return result


def genbank_xml_records(path: str | Path, accession: str, organism_prefix: str) -> list[dict]:
    """Read actual gene/CDS annotation from one official nucleotide record."""
    path = Path(path).resolve()
    root = ET.parse(path).getroot()
    sequences = root.findall("GBSeq")
    if len(sequences) != 1:
        raise ProfileError("Expected one explicit GenBank sequence record")
    record = sequences[0]
    if record.findtext("GBSeq_accession-version") != accession or not (
        record.findtext("GBSeq_organism", "").startswith(organism_prefix)
    ):
        raise ProfileError("GenBank accession or organism differs from selected reference")
    sequence = record.findtext("GBSeq_sequence", "")
    if len(sequence) != int(record.findtext("GBSeq_length", "0")):
        raise ProfileError("GenBank sequence is missing or truncated")
    records = {}
    for feature in record.findall("GBSeq_feature-table/GBFeature"):
        kind = feature.findtext("GBFeature_key")
        if kind not in {"gene", "CDS", "rRNA", "tRNA", "ncRNA"}:
            continue
        qualifiers = {q.findtext("GBQualifier_name"): q.findtext("GBQualifier_value")
                      for q in feature.findall("GBFeature_quals/GBQualifier")}
        locus = qualifiers.get("locus_tag")
        if not locus:
            continue
        item = records.setdefault(locus, {"feature_id": locus, "gene_id": locus,
                                         "contig": accession, "presence": True,
                                         "source_locator": {"path": str(path), "row": None,
                                                            "accession": accession, "record_id": locus}})
        for target, source in (("protein_id", "protein_id"), ("gene_symbol", "gene"), ("product", "product")):
            if qualifiers.get(source):
                item[target] = qualifiers[source]
    if not records:
        raise ProfileError("GenBank record contains no native gene annotations")
    return list(records.values())


def expression_column(path: str | Path, sample: str, *, crosswalk: str | Path | None = None,
                      expected_source_sha256: str | None = None, annotations: list[dict] = ()) -> list[dict]:
    """Select one measured RNA column; numeric row IDs require a verified bridge."""
    path = Path(path).resolve()
    if expected_source_sha256 and source_receipt(path)["sha256"] != expected_source_sha256:
        raise ProfileError("Expression matrix differs from the verified gene bridge source")
    mapping = {}
    if crosswalk:
        with Path(crosswalk).open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                original, locus = row["original_gene_id"], row["locus_tag"]
                if original in mapping or not locus or locus.isdigit():
                    raise ProfileError("Invalid native gene bridge")
                mapping[original] = locus
        if len(set(mapping.values())) != len(mapping):
            raise ProfileError("Native gene bridge is not one-to-one")
    info = {item["gene_id"]: item for item in annotations}
    result, seen = [], set()
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or sample not in reader.fieldnames:
            raise ProfileError(f"Measured sample column not found: {sample}")
        identity = reader.fieldnames[0]
        for line, row in enumerate(reader, 2):
            original = row[identity]
            locus = mapping.get(original) if mapping else original
            if not locus or locus.isdigit() or locus in seen:
                raise ProfileError("Expression rows require unique, verified native gene IDs")
            seen.add(locus)
            value = float(row[sample])
            if not math.isfinite(value):
                raise ProfileError("Expression values must be finite")
            annotation = info.get(locus, {})
            result.append({"feature_id": locus, "gene_id": locus,
                           "protein_id": annotation.get("protein_id"),
                           "gene_symbol": annotation.get("gene_symbol"), "product": annotation.get("product"),
                           "contig": annotation.get("contig"), "expression_value": value,
                           "source_locator": {"path": str(path), "row": line,
                                              "accession": sample, "record_id": original}})
    if not result or (mapping and len(result) != len(mapping)):
        raise ProfileError("Expression matrix and native bridge coverage differ")
    return result


def write_reference_profile(data_root: str | Path, *, profile_id: str, species: str, taxon_id: int,
                            strain: str, modality: str, records: list[dict], sample_id: str,
                            condition: dict, study_id: str, source_url: str, source_assets: list[dict],
                            assay: str, feature_namespace: str, unit: str, scale: str,
                            value_semantics: str, selection_reason: str,
                            observation_unit: str | None = None) -> dict:
    """Write derived observations and validate the loadable profile before publication."""
    data_root = Path(data_root).resolve()
    target = data_root / profile_id
    if target.exists():
        raise ProfileError("Reference profile already exists; source-derived data will not be overwritten")
    data_root.mkdir(parents=True, exist_ok=True)
    identity = {"scientific_name": species, "taxonomy_id": f"NCBITaxon:{taxon_id}"}
    is_genome = modality == "genome"
    with tempfile.TemporaryDirectory(prefix=".reference-build-", dir=data_root) as temporary:
        stage_root = Path(temporary)
        staged = stage_root / profile_id
        staged.mkdir()
        feature_path = staged / f"{modality}.json"
        feature_path.write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")) + "\n")
        receipt = source_receipt(feature_path)
        table = {"species": identity, "strain": strain, "genotype": None, "condition": condition,
                 "sample_id": sample_id, "pairing_id": None, "assay": assay,
                 "feature_namespace": feature_namespace, "unit": unit, "scale": scale,
                 "value_semantics": value_semantics,
                 "observation_unit": observation_unit or (
                     "measured_reference_assembly" if is_genome else "measured_baseline_sample"),
                 "features": {"path": feature_path.name, "format": "json",
                              "size_bytes": receipt["size_bytes"], "sha256": receipt["sha256"]},
                 "provenance": {"study_id": study_id, "source_samples": [sample_id],
                                "citation": source_url + "; " + selection_reason,
                                "terms": {"usage": "local_research_copy", "redistribution_approved": False,
                                          "license_status": "Source-specific redistribution terms are not asserted."},
                                "input_role": "sequenced_reference" if is_genome else "measured_pre_treatment"}}
        manifest = {"schema_version": "praxis.organism-profile.v2", "profile_id": profile_id,
                    "species": identity, "strain": strain, "genotype": None, "condition": condition,
                    "pairing": None, "modalities": {modality: table}}
        (staged / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        (staged / "source_receipt.json").write_text(json.dumps({
            "schema_version": "praxis.reference-assets-receipt.v1", "sources": source_assets,
            "source_assets_copied": False, "derived_feature_count": len(records),
            "selection_reason": selection_reason, "relation": "species_level_reference",
            "MIC_pairing_claimed": False, "cross_modality_sample_pairing_claimed": False,
        }, ensure_ascii=False, indent=2) + "\n")
        profile = load_profile(profile_id, stage_root)
        if profile.overview()["feature_count"] != len(records):
            raise ProfileError("Loaded reference feature count differs from source observations")
        staged.rename(target)
    return {"species": species, "taxon_id": taxon_id, "modality": modality, "profile_id": profile_id,
            "reference_strain": strain, "sample_id": sample_id, "source_path": str(target / "manifest.json"),
            "source_url": source_url, "status": "ready", "condition": condition,
            "selection_reason": selection_reason, "feature_count": len(records)}
