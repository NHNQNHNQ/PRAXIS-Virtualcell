"""Native source identity and conservative MIC admission, without network access."""
from copy import deepcopy
import json

import pytest

from praxis_virtualcell.datasets.chembl_import import (
    AdmissionError, NativeCache, acquire_species_mic, curate_activity, metadata_index, mic_endpoint, write_import,
)
from praxis_virtualcell.datasets.labels import ExperimentRecord


@pytest.fixture
def source():
    return {
        "activity": {"activity_id": 123, "assay_chembl_id": "CHEMBL100", "document_chembl_id": "CHEMBL200",
                     "molecule_chembl_id": "CHEMBL300", "target_chembl_id": "CHEMBL400", "src_id": 1,
                     "standard_type": "MIC", "type": "MIC", "standard_value": "4", "standard_units": "ug.mL-1",
                     "standard_relation": ">", "value": "4", "units": "mg/L", "relation": ">"},
        "assay": {"assay_chembl_id": "CHEMBL100", "document_chembl_id": "CHEMBL200",
                  "target_chembl_id": "CHEMBL400", "assay_tax_id": 562, "assay_organism": "Escherichia coli",
                  "assay_strain": None, "description": "Minimum inhibitory concentration against Escherichia coli by broth microdilution after 24 hours"},
        "document": {"document_chembl_id": "CHEMBL200", "doc_type": "PUBLICATION", "doi": "10.0000/example"},
        "molecule": {"molecule_chembl_id": "CHEMBL300", "molecule_hierarchy": {"parent_chembl_id": "CHEMBL301"},
                     "molecule_structures": {"canonical_smiles": "C[C@H](N)O.Cl"}},
    }


def admit(source, **kwargs):
    return curate_activity(**source, taxon_id=562, native_locator={"file": "native.json", "pointer": "/activities/0"}, **kwargs)


def test_unknown_strain_valid_species_label_without_pairing(source):
    record = admit(source)
    assert record.admission.label_eligible
    assert not record.admission.paired_omics_eligible
    assert record.organism.strain is None
    assert record.organism.taxon_id == 562
    assert record.pairing.status == "unpaired"
    assert record.endpoint.relation == ">"
    assert record.endpoint.lower == 4 and not record.endpoint.lower_closed
    assert record.endpoint.raw.unit == "mg/L"
    assert record.conditions.exposure_hours == 24
    assert record.source.activity_id == "123"
    assert record.source.assay_id == "CHEMBL100"
    assert record.source.document_id == "CHEMBL200"
    assert record.source.doi == "10.0000/example"
    assert record.source.native_locator["pointer"] == "/activities/0"
    assert record.molecule.source_parent_id == "CHEMBL301"
    assert ".Cl" in record.molecule.canonical_smiles
    assert "@" in record.molecule.canonical_smiles
    assert record.analysis_input()["omics_profile_ids"] == []
    assert "endpoint" not in record.analysis_input()


def test_stereochemistry_and_salt_are_not_collapsed(source):
    first = admit(source)
    changed = deepcopy(source)
    changed["molecule"]["molecule_structures"]["canonical_smiles"] = "C[C@@H](N)O.Cl"
    assert first.molecule.identity_key != admit(changed).molecule.identity_key
    changed["molecule"]["molecule_structures"]["canonical_smiles"] = "C[C@H](N)O"
    assert first.molecule.identity_key != admit(changed).molecule.identity_key


@pytest.mark.parametrize("field,key,value,reason", [
    ("activity", "activity_id", None, "missing_native_activity_id"),
    ("activity", "activity_id", True, "missing_native_activity_id"),
    ("activity", "activity_id", 0, "missing_native_activity_id"),
    ("assay", "assay_chembl_id", "CHEMBL999", "missing_or_mismatched_assay_chembl_id"),
    ("document", "document_chembl_id", "CHEMBL999", "missing_or_mismatched_document_chembl_id"),
    ("molecule", "molecule_chembl_id", "CHEMBL999", "missing_or_mismatched_molecule_chembl_id"),
    ("assay", "document_chembl_id", "CHEMBL999", "assay_document_identity_mismatch"),
    ("assay", "target_chembl_id", "CHEMBL999", "assay_target_identity_mismatch"),
    ("assay", "assay_tax_id", 573, "assay_species_taxon_not_exact"),
    ("assay", "assay_organism", "Klebsiella pneumoniae", "assay_species_taxon_not_exact"),
    ("activity", "target_tax_id", "573", "activity_species_taxon_conflict"),
    ("activity", "target_organism", "Klebsiella pneumoniae", "activity_species_taxon_conflict"),
    ("document", "doc_type", "DATASET", "not_source_linked_primary_report"),
    ("activity", "src_id", 7, "not_source_linked_primary_report"),
    ("activity", "data_validity_comment", "Potential transcription error", "source_data_validity_flag"),
    ("assay", "description", "", "missing_assay_description"),
])
def test_source_chain_failures_are_explicit(source, field, key, value, reason):
    source[field][key] = value
    with pytest.raises(AdmissionError) as exc:
        admit(source)
    assert reason in exc.value.reasons


@pytest.mark.parametrize("description", ["MIC50 against E. coli", "MIC90", "checkerboard FIC",
    "Potentiation of gentamicin", "MIC in combination with colistin", "MIC in the presence of SPR741",
    "predicted MIC", "calculated MIC", "MIC with avibactam", "in silico MIC"])
def test_non_single_or_model_endpoints_excluded(source, description):
    source["assay"]["description"] = description
    with pytest.raises(AdmissionError, match="aggregate_combination"):
        admit(source)


@pytest.mark.parametrize("relation,lower,upper,closed", [
    ("=", 4.0, 4.0, True), (">", 4.0, None, False), (">=", 4.0, None, True),
    ("<", None, 4.0, False), ("<=", None, 4.0, True),
])
def test_censoring_keeps_open_and_closed_bounds(source, relation, lower, upper, closed):
    source["activity"]["relation"] = source["activity"]["standard_relation"] = relation
    endpoint = mic_endpoint(source["activity"])
    assert (endpoint.lower, endpoint.upper) == (lower, upper)
    assert (endpoint.lower_closed if lower is not None else endpoint.upper_closed) is closed


@pytest.mark.parametrize("change,reason", [
    ({"units": "nM"}, "unsupported_or_unverified_mass_unit"),
    ({"relation": None}, "missing_or_invalid_native_measurement"),
    ({"relation": "~"}, "unsupported_or_missing_relation"),
    ({"type": "MIC50"}, "not_single_MIC_endpoint"),
    ({"standard_type": "MIC90"}, "not_single_MIC_endpoint"),
    ({"value": "0"}, "nonpositive_or_nonfinite_measurement"),
    ({"value": "nan"}, "invalid_or_conflicting_native_measurement"),
    ({"value": "<4"}, "invalid_or_conflicting_native_measurement"),
    ({"standard_relation": "<"}, "native_standard_relation_mismatch"),
    ({"standard_value": "2"}, "native_standard_value_mismatch"),
    ({"upper_value": "8"}, "unsupported_native_interval_requires_explicit_bound_import"),
])
def test_unverified_units_and_inconsistent_native_values_rejected(source, change, reason):
    source["activity"].update(change)
    with pytest.raises(AdmissionError) as exc:
        mic_endpoint(source["activity"])
    assert reason in exc.value.reasons


def test_explicit_source_strain_has_study_namespace(source):
    source["assay"]["assay_strain"] = "Clinical-1"
    record = admit(source)
    assert record.organism.strain == "Clinical-1"
    assert record.organism.native_strain_label == "Clinical-1"
    assert record.organism.strain_namespace == "study:CHEMBL200"
    assert not record.admission.paired_omics_eligible


def test_contradictory_latin_species_in_assay_description_excluded(source):
    source["assay"]["description"] = "Inhibitory activity against Enterobacter aerogenes was determined"
    with pytest.raises(AdmissionError, match="assay_description_species_conflict"):
        admit(source)


def test_no_native_structure_guess_or_activity_salt_mismatch(source):
    source["activity"]["canonical_smiles"] = "C[C@H](N)O"
    with pytest.raises(AdmissionError, match="activity_molecule_structure_mismatch"):
        admit(source)
    del source["activity"]["canonical_smiles"]
    source["molecule"]["molecule_structures"] = None
    with pytest.raises(AdmissionError, match="missing_native_molecule_structure"):
        admit(source)


def test_write_import_native_id_duplicates_and_conflicts(source, tmp_path):
    record = admit(source)
    duplicate = admit(source, source_version="another-snapshot")
    other = deepcopy(source)
    other["activity"]["activity_id"] = 124
    changed = deepcopy(other)
    changed["activity"]["value"] = changed["activity"]["standard_value"] = "8"
    summary = write_import([record, duplicate, admit(other), admit(changed)], [], tmp_path,
                          reused_existing_labels=[{"path": "/canonical/ab.jsonl", "record_count": 11650, "taxon_id": 470}])
    assert summary["new_label_count"] == 1
    assert summary["identical_native_activity_duplicates_removed"] == 1
    assert summary["exclusion_reason_counts"] == {"conflicting_native_activity_id": 1}
    assert summary["reused_existing_labels"] == ["/canonical/ab.jsonl"]
    assert len(summary["label_files"]) == 2
    loaded = ExperimentRecord.model_validate_json((tmp_path / "taxon_562.experiments.jsonl").read_text())
    assert loaded.record_id == record.record_id
    assert not (tmp_path / "taxon_470.experiments.jsonl").exists()


def test_metadata_index_exact_ids_and_locator(tmp_path):
    path = tmp_path / "molecules.json"
    path.write_text(json.dumps({"molecules": [{"molecule_chembl_id": "CHEMBL300", "pref_name": "A"}]}))
    index = metadata_index([path], kind="molecules")
    assert set(index) == {"CHEMBL300"}
    assert index["CHEMBL300"][1] == {"file": str(path.resolve()), "pointer": "/molecules/0"}


def test_native_cache_uses_verified_response_without_network(tmp_path, monkeypatch):
    import hashlib
    import praxis_virtualcell.datasets.chembl_import as module
    url = module.BASE_URL + "status.json"
    key = hashlib.sha256(url.encode()).hexdigest()[:24]
    body = b'{"chembl_db_version":"ChEMBL_37"}'
    path = tmp_path / f"{key}.json"
    receipt = tmp_path / f"{key}.receipt.json"
    path.write_bytes(body)
    receipt.write_text(json.dumps({"url": url, "sha256": hashlib.sha256(body).hexdigest()}))
    monkeypatch.setattr(module, "urlopen", lambda *a, **k: pytest.fail("cached response must not download again"))
    assert NativeCache(tmp_path).fetch("status")[0]["chembl_db_version"] == "ChEMBL_37"
    path.write_bytes(body + b" ")
    with pytest.raises(ValueError, match="native_cache_integrity_mismatch"):
        NativeCache(tmp_path).fetch("status")


def test_native_cache_rejects_arbitrary_url_and_incomplete_cache(tmp_path):
    import hashlib
    import praxis_virtualcell.datasets.chembl_import as module
    cache = NativeCache(tmp_path)
    with pytest.raises(ValueError, match="unsupported_public"):
        cache.fetch("https://example.com/upload")
    key = hashlib.sha256((module.BASE_URL + "status.json").encode()).hexdigest()[:24]
    (tmp_path / f"{key}.json").write_text("{}")
    with pytest.raises(ValueError, match="incomplete_native_cache"):
        cache.fetch("status")


def test_bounded_acquisition_complete_links_partial_coverage_and_legacy_exclusion(source, tmp_path, monkeypatch):
    calls = []
    payloads = {"status": {"chembl_db_version": "ChEMBL_37"},
                "target": {"targets": [{"tax_id": 562, "organism": "Escherichia coli", "target_type": "ORGANISM",
                                        "target_chembl_id": "CHEMBL400"}], "page_meta": {"next": None, "total_count": 1}},
                "activity": {"activities": [source["activity"]], "page_meta": {"next": "/next", "total_count": 10000}},
                "assay": {"assays": [source["assay"]], "page_meta": {"next": None}},
                "document": {"documents": [source["document"]], "page_meta": {"next": None}},
                "molecule": {"molecules": [source["molecule"]], "page_meta": {"next": None}}}

    def fetch(cache, resource, params=None):
        calls.append((resource, params))
        path = cache.root / (resource + ".json")
        path.write_text(json.dumps(payloads[resource]))
        return payloads[resource], {"file": str(path), "url": "https://www.ebi.ac.uk/chembl/api/data/" + resource,
                                    "sha256": "fixture", "page_meta": payloads[resource].get("page_meta")}

    monkeypatch.setattr(NativeCache, "fetch", fetch)
    legacy = tmp_path / "data/mdr_gnb/raw/compound_activity/escherichia_coli_mic_raw.jsonl"
    legacy.parent.mkdir(parents=True)
    legacy.write_text('{"molecule_chembl_id":"CHEMBL300","standard_value":"4"}\n')
    canonical = tmp_path / "existing.jsonl"
    canonical.write_text(admit(source).model_dump_json() + "\n")
    summary = acquire_species_mic(tmp_path, tmp_path / "out", taxon_ids=(562,), per_species_limit=1)
    assert summary["new_taxon_counts"] == {"562": 1}
    assert summary["excluded_legacy_source_rows"] == 1
    assert summary["coverage"].startswith("Bounded first pages")
    page = next(row for row in summary["source_acquisition"] if row["resource"] == "MIC_activities")
    assert page["complete"] is False and page["reported_total_count"] == 10000
    assert calls[2] == ("activity", {"target_chembl_id__in": "CHEMBL400", "standard_type": "MIC", "limit": 1})
    assert calls[3] == ("assay", {"assay_chembl_id__in": "CHEMBL100", "limit": 100})
    loaded = ExperimentRecord.model_validate_json((tmp_path / "out/taxon_562.experiments.jsonl").read_text())
    locator = loaded.source.native_locator
    assert locator["pointer"] == "/activities/0"
    assert locator["assay_metadata"]["pointer"] == "/assays/0"
    assert locator["document_metadata"]["pointer"] == "/documents/0"
    assert locator["molecule_metadata"]["pointer"] == "/molecules/0"
    # A canonical native activity is referenced, never written a second time.
    reused = acquire_species_mic(tmp_path, tmp_path / "out", taxon_ids=(562,), per_species_limit=1,
                                  reused_label_paths=(canonical,))
    assert reused["new_label_count"] == 0
    assert reused["reused_existing_labels"] == [str(canonical)]
    assert reused["local_source_inventory"]["new_activities_already_present_in_canonical_labels"] == 1
    assert not (tmp_path / "out/taxon_562.experiments.jsonl").exists()
    changed = admit(source).model_copy(deep=True)
    changed.endpoint = changed.endpoint.model_copy(update={"value": 8.0, "lower": 8.0})
    canonical.write_text(changed.model_dump_json() + "\n")
    conflict = acquire_species_mic(tmp_path, tmp_path / "out", taxon_ids=(562,), per_species_limit=1,
                                    reused_label_paths=(canonical,))
    assert conflict["new_label_count"] == 0
    assert conflict["exclusion_reason_counts"]["native_activity_conflicts_with_existing_canonical_label"] == 1


@pytest.mark.parametrize("taxon_ids,limit", [((562, 562), 1), ((562,), 0), ((562,), 501), ((999,), 1)])
def test_acquisition_rejects_unbounded_or_untrusted_taxa(tmp_path, taxon_ids, limit):
    with pytest.raises(ValueError):
        acquire_species_mic(tmp_path, tmp_path / "out", taxon_ids=taxon_ids, per_species_limit=limit)
