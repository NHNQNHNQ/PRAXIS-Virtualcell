"""Prepare genome-only reference profiles from verified local NCBI FASTA/GFF.

This reuses sequence annotation as context. It does not admit historical MIC
pairings, make negative gene calls, or imply sample-specific protein abundance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import unquote

from praxis_virtualcell.omics.profiles import ProfileError, load_profile

CURRENT19 = "2026-08-17-m1b1-current19-local-gene-feature-observation-ecoli-meropenem"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_path(repo_root: Path, declared: str) -> Path:
    if declared.startswith("research/mic_discovery/"):
        declared = "research/mdr_gnb/" + declared.removeprefix("research/")
    relative = Path(declared)
    if relative.is_absolute() or ".." in relative.parts:
        raise ProfileError("Unsafe source identity path")
    path = (repo_root / relative).resolve()
    if not path.is_relative_to(repo_root) or not path.is_file():
        raise ProfileError(f"Missing local source: {declared}")
    return path


def _attributes(text: str) -> dict[str, str]:
    result = {}
    for part in text.split(";"):
        if "=" in part:
            key, value = part.split("=", 1)
            result[unquote(key)] = unquote(value)
    return result


def _fasta_lengths(path: Path) -> dict[str, int]:
    lengths = {}
    current = None
    with path.open(encoding="utf-8") as stream:
        for text in stream:
            if text.startswith(">"):
                current = text[1:].split()[0]
                if current in lengths:
                    raise ProfileError("Duplicate FASTA sequence accession")
                lengths[current] = 0
            elif text.strip():
                if current is None:
                    raise ProfileError("FASTA sequence precedes accession header")
                lengths[current] += len(text.strip())
    if not lengths or any(length == 0 for length in lengths.values()):
        raise ProfileError("Reference FASTA contains missing sequence data")
    return lengths


def inspect_genome(fasta: Path, gff: Path, assembly: str) -> dict:
    """Verify coordinates/identity and retain exact gene/CDS source associations."""
    lengths = _fasta_lengths(fasta)
    genes, coding, strains, taxons, circular = [], {}, set(), set(), set()
    declared_assembly = None
    with gff.open(encoding="utf-8") as stream:
        for line, text in enumerate(stream, 1):
            if text.startswith("#!genome-build-accession "):
                declared_assembly = text.strip().split(":")[-1]
            if text.startswith("#") or not text.strip():
                continue
            fields = text.rstrip("\r\n").split("\t")
            if len(fields) != 9 or fields[0] not in lengths:
                raise ProfileError("GFF features must match local FASTA accessions")
            seqid, _, kind, start, end, _, strand, _, attributes = fields
            attr = _attributes(attributes)
            if kind == "region":
                if attr.get("strain"):
                    strains.add(attr["strain"])
                taxons.update(value.removeprefix("taxon:") for value in attr.get("Dbxref", "").split(",")
                              if value.startswith("taxon:"))
                if attr.get("Is_circular") == "true":
                    circular.add(seqid)
            if kind in {"gene", "pseudogene"}:
                if not attr.get("ID"):
                    raise ProfileError("GFF gene feature has no original identity")
                start, end = int(start), int(end)
                if start < 1 or end < start or start > lengths[seqid]:
                    raise ProfileError("Invalid reference gene coordinates")
                genes.append((line, seqid, kind, start, end, attr))
            elif kind == "CDS":
                for parent in attr.get("Parent", "").split(","):
                    if parent:
                        coding.setdefault(parent, []).append(attr)
    if declared_assembly != assembly or taxons != {"562"} or len(strains) != 1:
        raise ProfileError("Assembly, E. coli taxon, or strain identity is not uniquely established by the GFF")
    records, observed_ids = [], set()
    origin_spanning = 0
    for line, seqid, kind, start, end, attr in genes:
        if end > lengths[seqid]:
            if seqid not in circular or end - start + 1 > lengths[seqid]:
                raise ProfileError("Out-of-range reference gene without valid circular-origin semantics")
            origin_spanning += 1
        feature_id = attr["ID"]
        if feature_id in observed_ids:
            raise ProfileError("Duplicate original GFF gene identity")
        observed_ids.add(feature_id)
        links = {(row.get("protein_id"), row.get("product")) for row in coding.get(feature_id, [])}
        protein_id, product = next(iter(links)) if len(links) == 1 else (None, None)
        records.append({"feature_id": feature_id, "gene_id": attr.get("locus_tag") or feature_id,
                        "protein_id": protein_id, "gene_symbol": attr.get("gene") or None,
                        "product": attr.get("product") or product or ("pseudogene annotation" if kind == "pseudogene" else None),
                        "contig": seqid, "presence": True, "variant": None, "copy_number": None,
                        "source_locator": {"path": str(gff), "row": line, "accession": assembly, "record_id": feature_id}})
    if not records:
        raise ProfileError("No genome gene/pseudogene annotations found")
    return {"strain": next(iter(strains)), "taxonomy_id": "NCBITaxon:562", "sequence_count": len(lengths),
            "gene_pseudogene_count": len(records), "origin_spanning_gene_count": origin_spanning, "features": records}


def current19_sources(repo_root: str | Path) -> list[dict]:
    root = Path(repo_root).resolve()
    manifest_path = root / "research/mdr_gnb/mic_discovery" / CURRENT19 / "input-manifest-v1.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources = []
    assemblies = set()
    biosamples = set()
    for triple in manifest["frozen_triples"]:
        assembly, biosample = triple["assembly_accession"], triple["biosample_accession"]
        if assembly in assemblies or biosample in biosamples:
            raise ProfileError("Genome reference identity binding is not unique")
        assemblies.add(assembly)
        biosamples.add(biosample)
        assets = {}
        for kind, expected in manifest["package_file_identities"][assembly].items():
            path = _source_path(root, expected["path"])
            if path.stat().st_size != expected["size_bytes"] or _sha256(path) != expected["sha256"]:
                raise ProfileError(f"Genome source byte identity mismatch: {assembly}/{kind}")
            assets[kind] = {"path": str(path), "size_bytes": expected["size_bytes"], "sha256": expected["sha256"]}
        sources.append({"assembly_accession": assembly, "biosample_accession": biosample,
                        "assets": assets, "source_identity_manifest": str(manifest_path),
                        "source_identity_manifest_sha256": _sha256(manifest_path)})
    return sources


def prepare_genome_profiles(repo_root: str | Path, data_root: str | Path) -> list[Path]:
    """Prepare verified genome-only contexts; associated MIC labels stay excluded."""
    root = Path(data_root).resolve()
    sources = current19_sources(repo_root)
    targets = [root / f"ECOLI-{source['biosample_accession']}-{source['assembly_accession']}" for source in sources]
    if any(target.exists() for target in targets):
        raise ProfileError("Genome profile already exists; output will not be overwritten")
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".genome-reference-build-", dir=root, ignore_cleanup_errors=True) as temporary:
        stage_root = Path(temporary)
        for source, target in zip(sources, targets):
            assembly, biosample = source["assembly_accession"], source["biosample_accession"]
            observation = inspect_genome(Path(source["assets"]["fasta"]["path"]), Path(source["assets"]["gff3"]["path"]), assembly)
            staged = stage_root / target.name
            staged.mkdir()
            table = staged / "genome.json"
            table.write_text(json.dumps(observation.pop("features"), ensure_ascii=False, separators=(",", ":")) + "\n")
            species = {"scientific_name": "Escherichia coli", "taxonomy_id": "NCBITaxon:562"}
            condition = {"condition_id": f"sequenced_reference:{assembly}", "role": "sequenced_reference",
                         "medium": None, "time_h": None, "temperature_c": None, "growth_phase": None}
            # The reference role does not establish collection/AST culture conditions.
            semantics = ("Presence means a gene/pseudogene feature was observed in the source assembly annotation; "
                         "not a functional gene or negative gene call, RNA expression, protein abundance, or measured drug activity.")
            modality = {
                "species": species, "strain": observation["strain"], "genotype": None, "condition": condition,
                "sample_id": biosample, "pairing_id": None, "assay": "assembly_annotation",
                "feature_namespace": f"NCBI GFF gene IDs and native locus tags / {assembly}",
                "unit": "source_annotation_presence", "scale": "boolean_annotation_observation",
                "value_semantics": semantics, "observation_unit": "measured_reference_assembly",
                "features": {"path": table.name, "format": "json", "size_bytes": table.stat().st_size, "sha256": _sha256(table)},
                "provenance": {"study_id": f"NCBI_Assembly:{assembly}", "source_samples": [biosample],
                               "citation": (f"Official NCBI FASTA/GFF for assembly {assembly}, BioSample {biosample}; "
                                            "source size/SHA-256 and header/sequence/coordinate identities verified locally. "
                                            "Reference collection and AST culture conditions are unknown. "
                                            "Historical MIC candidate linkage is not admitted by this genome-context export. "
                                            "No RNA sample pairing, measured proteome, or new genotype sequencing is implied."),
                               "terms": {"usage": "local_research_copy", "redistribution_approved": False,
                                         "license_status": "Redistribution and phenotype record-level terms are not asserted by this export."},
                               "input_role": "sequenced_reference"},
            }
            manifest = {"schema_version": "praxis.organism-profile.v2", "profile_id": target.name,
                        "species": species, "strain": observation["strain"], "genotype": None,
                        "condition": condition, "pairing": None, "modalities": {"genome": modality}}
            (staged / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
            receipt = {"schema_version": "praxis.genome-reference-source-receipt.v1", **source, **observation,
                       "source_assets_copied": False, "phenotype_labels_loaded": False,
                       "historical_mic_admission_status": "not_admitted",
                       "condition_role_semantics": "Reference context only; no evidence of original culture/exposure conditions."}
            (staged / "source_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
            load_profile(target.name, stage_root)
        for target in targets:
            os.rename(stage_root / target.name, target)
    return targets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, help="Project root holding the frozen current19 package")
    parser.add_argument("--data-root", required=True, help="Genome-only profile output root")
    args = parser.parse_args()
    try:
        targets = prepare_genome_profiles(args.repo_root, args.data_root)
    except (ProfileError, OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"{exc}\n")
    print(json.dumps({"profiles": [str(path) for path in targets], "genome_context_count": len(targets),
                      "phenotype_pairing_admitted": False}))


if __name__ == "__main__":
    main()
