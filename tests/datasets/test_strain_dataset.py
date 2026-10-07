"""Strain associations preserve exact identities, source versions and private MICs."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from praxis_virtualcell.datasets.labels import ExperimentRecord
from praxis_virtualcell.datasets.species_evaluation import freeze_species_evaluation
from praxis_virtualcell.datasets.strain_dataset import build_strain_dataset, validate_strain_dataset
from praxis_virtualcell.omics import load_profile
from tests.datasets.test_evaluation import rows, write_records
from tests.datasets.test_species_evaluation import build_database, sample
from tests.omics.test_multiomics_profiles import PROFILE_ID, _build


def record(name, *, label="AB5075", namespace="strain_reference", study="DOC1", taxon=470,
           smiles="CCO", value=4.0, evidence="structured_assay_strain"):
    data = sample(name, smiles, study=study, taxon=taxon, value=value).model_dump()
    data["organism"].update(strain=label, strain_namespace=namespace, native_strain_label=label, identity_evidence=evidence)
    data["source"]["doi"] = f"10.0000/{study}"
    data["source"]["measured_qualifier"] = "MIC_SECRET_LABEL_SENTINEL"
    data["conditions"]["provenance"] = {"medium": "PRIVATE_MIC=4_SENTINEL"}
    return ExperimentRecord.model_validate(data)


def prepare(root, records):
    database, sources = build_database(root, records + [record("filler1", smiles="c1ccccc1"), record("filler2", smiles="c1ccncc1")])
    profiles = root / "profiles"
    # The v2 species freeze binds these original manifests and features.
    for path in profiles.glob("source-470-*/manifest.json"):
        data = json.loads(path.read_text())
        data["strain"] = "AB5075"
        for native in data["modalities"].values():
            native["strain"] = "AB5075"
        path.write_text(json.dumps(data))
    frozen = root / "frozen"
    freeze_species_evaluation(database, frozen, grouping="scaffold")
    return database, frozen / "manifest.json", profiles, sources


def build(root, records, *, enrichment=None):
    db, frozen, profiles, sources = prepare(root, records)
    summary = build_strain_dataset(db, frozen, root / "strain", profile_root=profiles, enrichments_path=enrichment)
    return summary, root / "strain" / "summary.json", profiles, sources


def keyed(path):
    return {row["private_answer"]["record_id"]: row for row in rows(path.parent / "cases.jsonl")}


def add_native(profiles, label, modality, *, taxon=470, anchored=False, genotype=None, suffix=""):
    raw = _build(profiles, [modality])
    profile_id = "native-" + label.replace(" ", "-") + "-" + modality + suffix
    raw.update(profile_id=profile_id, strain=label, genotype=genotype)
    from praxis_virtualcell.datasets.species_registry import SPECIES
    identity = {"scientific_name": SPECIES[taxon][0], "taxonomy_id": f"NCBITaxon:{taxon}"}
    raw["species"] = identity
    native = raw["modalities"][modality]
    native.update(strain=label, genotype=genotype, species=identity)
    if anchored:
        native["provenance"].update(study_id="NCBI_Assembly:GCA_000000001.1", citation="Official fixture assembly GCA_000000001.1")
    directory = profiles / PROFILE_ID
    (directory / "manifest.json").write_text(json.dumps(raw))
    directory.rename(profiles / profile_id)
    return profile_id


def test_exact_strain_reference_joins_native_modalities_and_never_reads_another_strain(tmp_path):
    summary, path, profiles, sources = build(tmp_path, [record("same"), record("other", label="AB5075 mutant", namespace="study:D1"),
        record("unknown", label=None, namespace=None, evidence="unresolved"), record("foreign", label="AB5075", taxon=562)])
    cases = keyed(path)
    same = cases["same"]
    assert same["task_scope"] == "strain_reference_omics"
    assert set(same["reference_profiles"]) == {"genome", "transcriptome", "proteome"}
    assert all(item["strain"] == "AB5075" for item in same["reference_profiles"].values())
    overview = load_profile(same["profile_id"], profiles).overview()
    assert overview["strain"] == "AB5075" and overview["input_role"] == "strain_reference" and overview["genotype"] is None
    for name in ("other", "unknown", "foreign"):
        assert cases[name]["reference_profiles"] == {} and cases[name]["profile_id"] is None
    assert cases["unknown"]["task_scope"] == "species_auxiliary_strain_unknown"
    assert cases["other"]["strain"]["label"] == "AB5075 mutant"
    assert summary["strain_omics_records"] == 3  # same plus the two independent filler cases
    assert validate_strain_dataset(path) == summary
    assert sources[0].is_file()


def test_study_local_names_do_not_merge_across_documents_or_borrow_mapping_genome(tmp_path):
    db, frozen, profiles, _ = prepare(tmp_path, [record("a", label="K26", study="D1"), record("b", label="K26", study="D2")])
    # A reference accession appears only as this RNA's mapping namespace.
    profile_id = add_native(profiles, "K26", "transcriptome")
    path = profiles / profile_id / "manifest.json"
    raw = json.loads(path.read_text())
    raw["modalities"]["transcriptome"]["feature_namespace"] = "Mapped against HS11286 GCA_000240185.2"
    path.write_text(json.dumps(raw))
    build_strain_dataset(db, frozen, tmp_path / "strain", profile_root=profiles)
    cases = keyed(tmp_path / "strain" / "summary.json")
    assert cases["a"]["strain"]["strain_id"] != cases["b"]["strain"]["strain_id"]
    assert cases["a"]["strain"]["namespace"] == "study:D1"
    assert cases["b"]["strain"]["namespace"] == "study:D2"
    assert cases["a"]["reference_profiles"] == cases["b"]["reference_profiles"] == {}


def test_native_assembly_anchors_exact_reference_name_across_papers_without_aliases(tmp_path):
    db, frozen, profiles, _ = prepare(tmp_path, [record("a", label="PAO1", taxon=287, study="D1"),
        record("b", label="PAO1", taxon=287, study="D2"), record("alias", label="PA01", taxon=287)])
    add_native(profiles, "PAO1", "genome", taxon=287, anchored=True)
    add_native(profiles, "PAO1", "transcriptome", taxon=287)
    add_native(profiles, "PAO1", "proteome", taxon=287)
    build_strain_dataset(db, frozen, tmp_path / "strain", profile_root=profiles)
    cases = keyed(tmp_path / "strain" / "summary.json")
    assert cases["a"]["strain"]["strain_id"] == cases["b"]["strain"]["strain_id"]
    assert cases["a"]["strain"]["namespace"] == "strain_reference"
    assert "assembly_accession" in cases["a"]["strain"]["identity_basis"]
    assert len(cases["a"]["reference_profiles"]) == 3
    assert cases["alias"]["reference_profiles"] == {}


def test_genotype_mismatch_and_duplicate_native_modality_are_not_combined(tmp_path):
    db, frozen, profiles, _ = prepare(tmp_path, [record("a", label="ExactRef")])
    first = add_native(profiles, "ExactRef", "genome", anchored=True)
    second = add_native(profiles, "ExactRef", "genome", anchored=True, suffix="-second")
    add_native(profiles, "ExactRef", "transcriptome", genotype="knockout")
    build_strain_dataset(db, frozen, tmp_path / "strain", profile_root=profiles)
    case = keyed(tmp_path / "strain" / "summary.json")["a"]
    assert set(case["reference_profiles"]) == {"genome"}
    assert case["reference_profiles"]["genome"]["profile_id"] == first
    assert case["reference_profiles"]["genome"]["alternative_profile_ids"] == [second]
    assert load_profile(case["profile_id"], profiles).overview()["genotype"] is None


def test_native_platform_choices_exist_without_mic_matches_and_kp_strains_stay_separate(tmp_path):
    db, frozen, profiles, _ = prepare(tmp_path, [record("unknown", label=None, namespace=None, evidence="unresolved")])
    for taxon, label in ((562, "MG1655"), (287, "PAO1")):
        for modality in ("genome", "transcriptome", "proteome"):
            add_native(profiles, label, modality, taxon=taxon, anchored=modality == "genome")
    for label, modality in (("HS11286", "genome"), ("K26", "transcriptome"), ("NCTC418", "proteome")):
        add_native(profiles, label, modality, taxon=573, anchored=modality == "genome")
    summary = build_strain_dataset(db, frozen, tmp_path / "strain", profile_root=profiles)
    ids = {item["profile_id"] for item in summary["collections"]}
    assert {"AB5075-STRAIN-REFERENCE", "EC-MG1655-STRAIN-REFERENCE", "PA-PAO1-STRAIN-REFERENCE",
            "KP-HS11286-STRAIN-REFERENCE", "KP-K26-STRAIN-REFERENCE", "KP-NCTC418-STRAIN-REFERENCE"} <= ids
    for label, modality in (("HS11286", "genome"), ("K26", "transcriptome"), ("NCTC418", "proteome")):
        overview = load_profile(f"KP-{label}-STRAIN-REFERENCE", profiles).overview()
        assert overview["strain"] == label and overview["selected_modalities"] == [modality]
    case = keyed(tmp_path / "strain" / "summary.json")["unknown"]
    assert case["profile_id"] is None and case["reference_profiles"] == {}


def test_same_strain_multiple_mic_records_keep_private_locations_and_frozen_splits(tmp_path):
    summary, path, _, _ = build(tmp_path, [record("first", value=4.0), record("second", value=16.0)])
    cases = keyed(path)
    first, second = cases["first"], cases["second"]
    assert first["strain"]["strain_id"] == second["strain"]["strain_id"]
    assert first["split"] == second["split"] and first["group_id"] == second["group_id"]
    assert first["private_answer"]["byte_offset"] != second["private_answer"]["byte_offset"]
    assert first["candidate"]["id"] == first["case_id"]
    assert set(first["conditions"]) == {"medium", "medium_supplements", "temperature_c", "exposure_hours", "method", "inoculum"}
    assert first["literature"] == {"doi": "10.0000/DOC1", "document_id": "DOC1"}
    public = {key: first[key] for key in ("candidate", "strain", "conditions", "reference_profiles", "profile_id", "task_scope")}
    for sentinel in ("MIC_SECRET_LABEL_SENTINEL", "PRIVATE_MIC=4_SENTINEL", '"endpoint"', '"value"', '"private_answer"'):
        assert sentinel not in json.dumps(public)
    assert summary["MIC_values_copied"] is False and summary["omics_assets_copied"] is False
    with sqlite3.connect(path.parent / "strain_dataset.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == 4
        assert not {row[1] for row in db.execute("PRAGMA table_info(cases)")} & {"MIC", "value", "endpoint"}


def enrichment_file(root, entries):
    path = root / "enrichments.json"
    path.write_text(json.dumps({"schema_version": "praxis.strain-enrichments.v1", "enrichments": entries}))
    return path


def test_source_grounded_enrichment_updates_only_derived_conditions_and_strain(tmp_path):
    db, frozen, profiles, sources = prepare(tmp_path, [record("unknown", label=None, namespace=None, evidence="unresolved")])
    before = sources[0].read_bytes()
    enrichment = enrichment_file(tmp_path, [{"record_id": "unknown", "source": {"citation": "https://example.org/paper", "locator": "Methods, strain and AST paragraphs"},
        "strain": {"label": "AB5075", "identity_basis": "explicit_publication_strain"},
        "conditions": {"medium": "CA-MHB", "temperature_c": 37.0}}])
    summary = build_strain_dataset(db, frozen, tmp_path / "strain", profile_root=profiles, enrichments_path=enrichment)
    case = keyed(tmp_path / "strain" / "summary.json")["unknown"]
    assert case["strain"]["label"] == "AB5075" and case["profile_id"] is not None
    assert case["conditions"]["medium"] == "CA-MHB" and case["conditions"]["temperature_c"] == 37
    assert case["conditions"]["inoculum"] is None and sources[0].read_bytes() == before
    assert summary["enriched_records"] == 1


@pytest.mark.parametrize("change", ["endpoint", "no_source", "duplicate", "unknown_record", "erase_mutant"])
def test_unsupported_or_untraceable_enrichment_is_rejected(tmp_path, change):
    db, frozen, profiles, _ = prepare(tmp_path, [record("mutant", label="AB5075 mutant")])
    row = {"record_id": "mutant", "source": {"citation": "https://example.org/paper", "locator": "Methods"}, "conditions": {"medium": "LB"}}
    entries = [row]
    if change == "endpoint":
        row["endpoint"] = {"value": 1.0}
    elif change == "no_source":
        del row["source"]
    elif change == "duplicate":
        entries = [row, row]
    elif change == "unknown_record":
        row["record_id"] = "not-in-frozen"
    elif change == "erase_mutant":
        row["strain"] = {"label": "AB5075", "identity_basis": "unsupported_alias"}
    with pytest.raises((ValueError, ValidationError)):
        build_strain_dataset(db, frozen, tmp_path / "strain", profile_root=profiles, enrichments_path=enrichment_file(tmp_path, entries))
    assert not (tmp_path / "strain" / "cases.jsonl").exists()


@pytest.mark.parametrize("source", ["frozen_label", "frozen_inputs", "native_manifest", "cases", "collection"])
def test_changed_frozen_or_derived_sources_are_rejected(tmp_path, source):
    summary, path, _, sources = build(tmp_path, [record("a")])
    target = {"frozen_label": sources[0], "frozen_inputs": Path(summary["frozen_manifest"]["path"]).parent / "inputs.jsonl",
              "native_manifest": Path(summary["reference_sources"][0]["manifest"]["path"]),
              "cases": path.parent / "cases.jsonl", "collection": Path(summary["collections"][0]["manifest"]["path"])}[source]
    with target.open("ab") as stream:
        stream.write(b"\n")
    with pytest.raises(ValueError, match="frozen_source_changed"):
        validate_strain_dataset(path)


def test_destination_is_never_overwritten_and_frozen_change_blocks_rebuild(tmp_path):
    summary, path, profiles, sources = build(tmp_path, [record("a")])
    original = (path.parent / "cases.jsonl").read_bytes()
    with pytest.raises(ValueError, match="destination_exists"):
        build_strain_dataset(summary["source_database"]["path"], summary["frozen_manifest"]["path"], path.parent, profile_root=profiles)
    assert (path.parent / "cases.jsonl").read_bytes() == original
    sources[0].write_text(sources[0].read_text() + "\n")
    with pytest.raises(ValueError, match="frozen_source_changed"):
        build_strain_dataset(summary["source_database"]["path"], summary["frozen_manifest"]["path"], tmp_path / "second", profile_root=profiles)
