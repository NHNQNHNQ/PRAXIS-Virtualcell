"""Local measured MIC parsing, metadata linking and conservative admission."""
import csv
import json
import math

import pytest

from praxis_virtualcell.datasets.curation import (
    canonical_identity,
    conditions_from_assay,
    curate_existing_labels,
    endpoint_from_curated_mic,
    organism_from_assay,
)


def row(**overrides):
    return {"record_id": "1", "source_file": "historical/activities_000.json", "molecule_id": "CHEMBL1",
            "parent_id": "CHEMBL1", "smiles": "OCC", "study": "DOC1", "assay": "ASSAY1",
            "strain": "", "strain_evidence": "unresolved", "assay_description": "AB5075 after 16 hrs by microbroth dilution method",
            "potential_duplicate": "0", "raw_value": "4.0", "raw_unit": "mg/L", "relation": "=",
            "lower_log2": "2.0", "upper_log2": "2.0", "censor": "exact", "lower_closed": "True",
            "upper_closed": "True", **overrides}


@pytest.mark.parametrize("relation,censor,bounds", [
    ("=", "exact", ("2.0", "2.0")), (">", "right", ("2.0", "")),
    (">=", "right", ("2.0", "")), ("<", "left", ("", "2.0")), ("<=", "left", ("", "2.0")),
])
def test_mass_units_and_native_relations_are_preserved(relation, censor, bounds):
    source = row(relation=relation, censor=censor, lower_log2=bounds[0], upper_log2=bounds[1])
    endpoint = endpoint_from_curated_mic(source)
    assert endpoint.value == 4.0
    assert endpoint.relation == relation
    assert endpoint.raw.unit == "mg/L"
    assert endpoint.unit == "ug/mL"


def test_milligram_per_ml_is_only_converted_with_confirmed_factor():
    endpoint = endpoint_from_curated_mic(row(raw_unit="mg/ml", raw_value="0.004"))
    assert endpoint.value == 4.0
    assert "factor:1000" in endpoint.conversion
    with pytest.raises(ValueError, match="unsupported_or_unverified_unit"):
        endpoint_from_curated_mic(row(raw_unit="uM"))


def test_legacy_interval_preserves_upper_bound_and_records_its_derivation():
    endpoint = endpoint_from_curated_mic(row(censor="interval", upper_log2="4.0"))
    assert (endpoint.lower, endpoint.upper, endpoint.value) == (4.0, 16.0, None)
    assert endpoint.raw.upper_value is None
    assert "upper_bound_from_curated_upper_log2" in endpoint.conversion


@pytest.mark.parametrize("changes", [
    {"lower_log2": "3.0"}, {"relation": ">", "censor": "exact"},
    {"raw_value": "8"}, {"lower_log2": "nan"}, {"raw_value": "y_pred=4"},
    {"raw_value": "4", "relation": "~"},
])
def test_inconsistent_legacy_measurements_are_not_silently_repaired(changes):
    with pytest.raises(ValueError):
        endpoint_from_curated_mic(row(**changes))


def test_canonical_identity_retains_stereo_and_salt_fragments():
    assert canonical_identity("OCC") == canonical_identity("CCO")
    left, _ = canonical_identity("C[C@H](O)C(=O)O.Cl")
    right, _ = canonical_identity("C[C@@H](O)C(=O)O.Cl")
    assert left != right
    assert ".Cl" in left


def test_assay_strain_recovers_ab5075_without_equating_mutant_or_species():
    assert organism_from_assay({"assay_strain": "isolate AB5075", "assay_tax_id": 470}, row()).strain == "AB5075"
    mutant = organism_from_assay({"assay_strain": "AB5075-derivative"}, row())
    assert mutant.strain == "AB5075-derivative"
    unresolved = organism_from_assay({}, row(assay_description="Acinetobacter baumannii mutant AB5075"))
    assert unresolved.strain is None
    assert organism_from_assay({}, row(assay_description="A. baumannii ATCC 19606")).strain == "ATCC 19606"
    first = organism_from_assay({"assay_strain": "1"}, row(study="DOC1"))
    other = organism_from_assay({"assay_strain": "1"}, row(study="DOC2"))
    assert first.strain == other.strain
    assert first.strain_namespace != other.strain_namespace
    assert organism_from_assay({}, row(assay_description="ATCC 19606 knockout mutant")).strain is None
    conflicting = organism_from_assay({"assay_strain": "AB5075"}, row(assay_description="AB5075 deletion mutant"))
    assert conflicting.identity_evidence == "conflicting"
    assert conflicting.strain is None


def test_conditions_are_observed_or_null_and_no_drug_response_text_is_input():
    conditions = conditions_from_assay({}, "MIC =64 ug/ml after 16 hrs by broth microdilution method")
    assert conditions.exposure_hours == 16
    assert conditions.medium is None
    assert conditions.temperature_c is None
    assert conditions.method == "broth_microdilution"
    conditions = conditions_from_assay({"assay_parameters": [
        {"standard_type": "MEDIA", "standard_text_value": "CAMHB"},
        {"standard_type": "TIME", "standard_value": "18", "standard_units": "hr"},
    ]}, "")
    assert conditions.medium == "CAMHB"
    assert conditions.exposure_hours == 18
    conditions = conditions_from_assay({}, "in 0.02% linoleic acid supplemented media after 2 days")
    assert conditions.exposure_hours == 48
    assert conditions.medium is None
    assert conditions.medium_supplements == ["0.02% linoleic acid"]


def fixture_sources(root):
    folder = root / "data/antibacterial/abaumannii/curated"
    folder.mkdir(parents=True)
    rows = [row(), row(record_id="2", assay="ASSAY2", assay_description="Potentiation of rifampicin MIC at 20 uM"),
            row(record_id="3", raw_value="", assay_description="Prediction only; y_pred=4")]
    with (folder / "mic_measurements.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    assays = [{"assay_chembl_id": name, "document_chembl_id": "DOC1", "assay_strain": "AB5075",
               "assay_tax_id": 470, "assay_organism": "Acinetobacter baumannii", "assay_parameters": []}
              for name in ("ASSAY1", "ASSAY2")]
    for kind, values in (("assays", assays), ("documents", [{"document_chembl_id": "DOC1", "doi": "10.0/example"}]),
                         ("molecules", [{"molecule_chembl_id": "CHEMBL1"}])):
        (folder / f"chembl_{kind}.json").write_text(json.dumps(values))
    raw = root / "data/mdr_gnb/raw/compound_activity"
    raw.mkdir(parents=True)
    (raw / "escherichia_coli_mic_raw.jsonl").write_text(json.dumps({
        "molecule_chembl_id": "CHEMBL2", "canonical_smiles": "CCO", "standard_value": "8",
        "standard_units": "ug.mL-1", "standard_relation": "=",
    }) + "\n")
    # A validation model output must never even be opened by curation.
    predictions = root / "data/mdr_gnb/reports/validation"
    predictions.mkdir(parents=True)
    (predictions / "y_pred.json").write_text("invalid JSON and fabricated measured MIC=999")


def test_source_linked_curation_excludes_potentiation_and_keeps_labels_separate(tmp_path):
    fixture_sources(tmp_path)
    output = tmp_path / "local" / "labels"
    summary = curate_existing_labels(tmp_path, output)
    assert summary["abaumannii"]["source_rows"] == 3
    assert summary["abaumannii"]["experimental_labels_admitted"] == 1
    assert summary["abaumannii"]["ab5075_records"] == 1
    assert summary["abaumannii"]["same_isolate_and_condition_omics_pairs"] == 0
    assert not summary["model_predictions_used"]
    assert summary["mdr_sources"]["ec_compound_raw"]["rows"] == 1
    assert summary["mdr_sources"]["ec_compound_raw"]["admitted_labels"] == 0
    labels = [json.loads(line) for line in (output / "experimental_labels.jsonl").read_text().splitlines()]
    inputs = [json.loads(line) for line in (output / "analysis_inputs.jsonl").read_text().splitlines()]
    assert labels[0]["endpoint"]["value"] == 4.0
    assert "endpoint" not in inputs[0]["input"]
    assert inputs[0]["input"]["omics_profile_ids"] == []
    assert labels[0]["source"]["native_locator"]["csv_line"] == 2
    assert (output / "paired_omics_labels.jsonl").read_text() == ""
    exclusions = [json.loads(line) for line in (output / "exclusions.jsonl").read_text().splitlines()]
    assert len(exclusions) == 2
    assert "aggregate_combination_potentiation_or_nonexperimental_context" in exclusions[0]["reasons"]


def test_assay_source_conflict_is_excluded_instead_of_inventing_pairing(tmp_path):
    fixture_sources(tmp_path)
    path = tmp_path / "data/antibacterial/abaumannii/curated/chembl_assays.json"
    assays = json.loads(path.read_text())
    assays[0]["document_chembl_id"] = "OTHER_DOC"
    path.write_text(json.dumps(assays))
    summary = curate_existing_labels(tmp_path)
    assert summary["abaumannii"]["experimental_labels_admitted"] == 0
    assert summary["abaumannii"]["excluded_reasons"]["assay_document_identity_mismatch"] == 2


def test_interval_overflow_is_not_an_admitted_infinite_label():
    with pytest.raises((ValueError, OverflowError)):
        endpoint_from_curated_mic(row(censor="interval", upper_log2="1024"))
    assert math.isfinite(endpoint_from_curated_mic(row()).value)
