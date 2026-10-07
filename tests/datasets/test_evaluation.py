"""Freeze and score contract-shaped temporary experiments, without inference."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from praxis_virtualcell.datasets.evaluation import freeze_evaluation, read_experiments, score_evaluation
from praxis_virtualcell.datasets.labels import ExperimentRecord


def experiment(identifier: str, smiles: str = "CCO", *, relation: str = "=", value: float = 4.0,
               kind: str = "MIC", unit: str = "ug/mL", strain: str = "AB5075",
               namespace: str | None = "public:AB5075", study: str | None = "TEST_DOCUMENT",
               eligible: bool = True, paired: bool = False) -> ExperimentRecord:
    """A source-linked schema fixture; not an assertion of a real experiment."""
    endpoint = {"kind": kind, "relation": relation, "unit": unit, "value": value,
                "raw": {"value": str(value), "unit": unit, "relation": relation},
                "conversion": "fixture identity units"}
    if relation == "interval":
        endpoint.update(value=None, lower=2.0, upper=8.0, lower_closed=False, upper_closed=True)
        endpoint["raw"].update(value="2", upper_value="8")
    return ExperimentRecord.model_validate({
        "record_id": identifier,
        "molecule": {"source_molecule_id": f"TEST_MOLECULE:{identifier}", "source_parent_id": None,
                     "canonical_smiles": smiles, "identity_key": f"TEST_IDENTITY:{identifier}"},
        "organism": {"species": "Acinetobacter baumannii", "taxon_id": 470, "strain": strain,
                     "strain_namespace": namespace, "isolate_id": None,
                     "identity_evidence": "structured_assay_strain"},
        "conditions": {"medium": "CA-MHB", "exposure_hours": 18.0,
                       "provenance": {"medium": "DO_NOT_EXPOSE_LABEL_SENTINEL"}},
        "endpoint": endpoint,
        "source": {"source_id": f"test-only:{identifier}", "origin": "experimental_database",
                   "reported_as_measured": True, "measured_qualifier": "DO_NOT_EXPOSE_LABEL_SENTINEL",
                   "native_locator": {"file": "fixture-only.csv", "row_id": identifier},
                   "activity_id": f"TEST_ACTIVITY:{identifier}", "assay_id": f"TEST_ASSAY:{identifier}",
                   "document_id": study, "doi": None, "license": "Synthetic test fixture"},
        "pairing": {"status": "matched_isolate_and_condition" if paired else "same_strain_reference",
                    "profile_ids": ["TEST_MATCHED_PROFILE"] if paired else ["TEST_UNPAIRED_REFERENCE"],
                    "isolate_evidence_source_ids": ["test-only:isolate"] if paired else [],
                    "condition_evidence_source_ids": ["test-only:condition"] if paired else []},
        "admission": {"label_eligible": eligible, "paired_omics_eligible": paired,
                      "reasons": ["Synthetic test-only admission fixture"]},
    })


def write_records(path: Path, records: list[ExperimentRecord]) -> Path:
    path.write_text("".join(record.model_dump_json() + "\n" for record in records), encoding="utf-8")
    return path


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def focus_cohort(tmp_path: Path, records: list[ExperimentRecord]) -> tuple[Path, list[dict], str]:
    """Keep desired score cases in one compound group, with two other groups."""
    labels = write_records(tmp_path / "labels.jsonl", records + [
        experiment("filler-benzene", "c1ccccc1"), experiment("filler-pyridine", "c1ccncc1"),
    ])
    folder = tmp_path / "frozen"
    manifest = freeze_evaluation(labels, folder)
    assert manifest["status"] == "ready"
    wanted = {record.record_id for record in records}
    selected = [row for row in rows(folder / "answers.index.jsonl") if row["record_id"] in wanted]
    assert len({row["split"] for row in selected}) == 1
    return folder / "manifest.json", selected, selected[0]["split"]


def prediction(case_id: str, value: float | None, **changes) -> dict:
    result = {"case_id": case_id, "status": "completed",
              "assessment": {"mic_estimate": {"value": value, "unit": "ug/mL", "basis": "llm_estimate"}}}
    result.update(changes)
    return result


def write_predictions(path: Path, predictions: list[dict]) -> Path:
    path.write_text("".join(json.dumps(item) + "\n" for item in predictions), encoding="utf-8")
    return path


def test_compound_and_salt_parent_never_cross_splits_or_merge_labels(tmp_path):
    records = [experiment("free-base", "CCN", value=4.0),
               experiment("chloride", "CC[NH3+].[Cl-]", value=8.0),
               experiment("bromide", "CC[NH3+].[Br-]", value=16.0),
               experiment("ethanol", "CCO"), experiment("benzene", "c1ccccc1"),
               experiment("pyridine", "c1ccncc1")]
    source = write_records(tmp_path / "labels.jsonl", records)
    original = source.read_bytes()
    frozen = tmp_path / "frozen"
    result = freeze_evaluation(source, frozen)
    assert result["independent_groups"] == 4
    index = rows(frozen / "answers.index.jsonl")
    family = [row for row in index if row["record_id"] in {"free-base", "chloride", "bromide"}]
    assert len({row["group_id"] for row in family}) == 1
    assert len({row["split"] for row in family}) == 1
    assert source.read_bytes() == original
    restored = read_experiments(source)
    assert [record.endpoint.value for record in restored[:3]] == [4.0, 8.0, 16.0]
    inputs = {row["case_id"]: row["input"] for row in rows(frozen / "inputs.jsonl")}
    assert {inputs[row["case_id"]]["candidate"]["smiles"] for row in family} == {"CCN", "CC[NH3+].[Cl-]", "CC[NH3+].[Br-]"}


def test_compound_grouping_keeps_stereoisomers_distinct(tmp_path):
    source = write_records(tmp_path / "labels.jsonl", [experiment("left", "C[C@H](O)C(=O)O"),
                                                     experiment("right", "C[C@@H](O)C(=O)O"),
                                                     experiment("third", "c1ccccc1")])
    assert freeze_evaluation(source, tmp_path / "frozen")["independent_groups"] == 3


def test_split_assignment_is_deterministic_when_source_order_changes(tmp_path):
    records = [experiment(f"row-{index}", smiles) for index, smiles in enumerate(
        ["CCO", "CCN", "c1ccccc1", "c1ccncc1", "C1CCCCC1", "CC(=O)O", "COC", "CCS"])]
    first = tmp_path / "first"
    second = tmp_path / "second"
    freeze_evaluation(write_records(tmp_path / "first.jsonl", records), first, seed=12345)
    freeze_evaluation(write_records(tmp_path / "second.jsonl", list(reversed(records))), second, seed=12345)
    assert rows(first / "inputs.jsonl") == rows(second / "inputs.jsonl")
    assert rows(first / "answers.index.jsonl") == rows(second / "answers.index.jsonl")


def test_joint_transitive_connections_can_prevent_an_independent_split(tmp_path):
    records = [experiment("A", "CCO", strain="S1", namespace="test-global", study="DOC1"),
               experiment("B", "CCO", strain="S2", namespace="test-global", study="DOC2"),
               experiment("C", "CCN", strain="S2", namespace="test-global", study="DOC3"),
               experiment("D", "c1ccccc1", strain="S3", namespace="test-global", study="DOC3"),
               experiment("E", "c1ccncc1", strain="S4", namespace="test-global", study="DOC4")]
    frozen = tmp_path / "frozen"
    manifest = freeze_evaluation(write_records(tmp_path / "labels.jsonl", records), frozen, grouping="joint")
    assert manifest["status"] == "insufficient_groups"
    assert manifest["independent_groups"] == 2 and manifest["largest_group_records"] == 4
    assert manifest["split_counts"] == {"unassigned": 5}
    family = [item for item in rows(frozen / "answers.index.jsonl") if item["record_id"] != "E"]
    assert len({item["group_id"] for item in family}) == 1
    with pytest.raises(ValueError, match="evaluation_not_ready"):
        score_evaluation(frozen / "manifest.json", write_predictions(tmp_path / "predictions.jsonl", []))


def test_strain_grouping_respects_source_namespace_and_excludes_unknown_namespaces(tmp_path):
    records = [experiment("doc-one", "CCO", strain="1", namespace="study:DOC1"),
               experiment("doc-two", "CCN", strain="1", namespace="study:DOC2"),
               experiment("public", "c1ccccc1"),
               experiment("unknown-namespace", "c1ccncc1", namespace=None)]
    folder = tmp_path / "frozen"
    manifest = freeze_evaluation(write_records(tmp_path / "labels.jsonl", records), folder, grouping="strain")
    assert manifest["independent_groups"] == 3 and manifest["excluded_records"] == 1
    index = rows(folder / "answers.index.jsonl")
    assert next(item for item in index if item["record_id"] == "doc-one")["group_id"] != next(item for item in index if item["record_id"] == "doc-two")["group_id"]
    assert rows(folder / "excluded.jsonl") == [{"record_id": "unknown-namespace", "reason": "strain_namespace_required"}]


def test_scaffold_grouping_does_not_claim_novel_scaffolds_for_acyclic_structures(tmp_path):
    source = write_records(tmp_path / "labels.jsonl", [experiment("alcohol", "CCO"), experiment("amine", "CCN"),
                                                     experiment("benzene", "c1ccccc1"), experiment("pyridine", "c1ccncc1")])
    folder = tmp_path / "frozen"
    manifest = freeze_evaluation(source, folder, grouping="scaffold")
    assert manifest["independent_groups"] == 3
    acyclic = [item for item in rows(folder / "answers.index.jsonl") if item["record_id"] in {"alcohol", "amine"}]
    assert len({item["group_id"] for item in acyclic}) == 1


def test_model_visible_inputs_do_not_contain_endpoint_or_source_labels(tmp_path):
    records = [experiment("private-label-1", "CCO", relation=">", value=64.0),
               experiment("private-label-2", "CCN"), experiment("private-label-3", "c1ccccc1")]
    folder = tmp_path / "frozen"
    freeze_evaluation(write_records(tmp_path / "labels.jsonl", records), folder)
    text = (folder / "inputs.jsonl").read_text()
    for item in rows(folder / "inputs.jsonl"):
        assert set(item["input"]) == {"candidate", "organism", "conditions", "omics_profile_ids"}
        assert item["input"]["candidate"]["id"] == item["case_id"]
        assert item["input"]["omics_profile_ids"] == []
    for forbidden in ["private-label", "DO_NOT_EXPOSE_LABEL_SENTINEL", "endpoint", "raw", "conversion",
                      "activity_id", "native_locator", "measured_qualifier", "admission", "MIC", "64.0", "TEST_UNPAIRED_REFERENCE"]:
        assert forbidden not in text
    # The private answer index only locates canonical records; it has no label copy.
    assert all(set(item) == {"case_id", "split", "group_id", "record_id"} for item in rows(folder / "answers.index.jsonl"))


def test_paired_only_freeze_requires_explicit_matched_pair_admission(tmp_path):
    records = [experiment("paired-alcohol", "CCO", paired=True), experiment("paired-amine", "CCN", paired=True),
               experiment("paired-benzene", "c1ccccc1", paired=True), experiment("reference-only", "c1ccncc1"),
               experiment("inadmitted", "C1CCCCC1", eligible=False)]
    folder = tmp_path / "frozen"
    manifest = freeze_evaluation(write_records(tmp_path / "labels.jsonl", records), folder, paired_only=True)
    assert manifest["records"] == manifest["matched_omics_records"] == 3
    assert manifest["excluded_records"] == 2
    assert all(item["input"]["omics_profile_ids"] == ["TEST_MATCHED_PROFILE"] for item in rows(folder / "inputs.jsonl"))


@pytest.mark.parametrize("relation,boundary,expected", [("<", 4.0, False), ("<=", 4.0, True),
                                                     (">", 4.0, False), (">=", 4.0, True),
                                                     ("<", 2.0, True), (">", 8.0, True)])
def test_one_sided_censoring_preserves_open_closed_boundaries(tmp_path, relation, boundary, expected):
    manifest, cases, split = focus_cohort(tmp_path, [experiment("focus", relation=relation)])
    report = score_evaluation(manifest, write_predictions(tmp_path / "predictions.jsonl", [prediction(cases[0]["case_id"], boundary)]), split=split)
    assert report["censored_answered_cases"] == 1
    assert report["censored_interval_consistency"] == float(expected)
    assert report["exact_answered_cases"] == 0 and report["mean_absolute_log2_error"] is None


@pytest.mark.parametrize("value,expected", [(2.0, False), (2.01, True), (8.0, True), (8.01, False)])
def test_two_sided_interval_is_not_scored_as_a_midpoint(tmp_path, value, expected):
    manifest, cases, split = focus_cohort(tmp_path, [experiment("focus", relation="interval")])
    report = score_evaluation(manifest, write_predictions(tmp_path / "predictions.jsonl", [prediction(cases[0]["case_id"], value)]), split=split)
    assert report["censored_interval_consistency"] == float(expected)
    assert report["mean_absolute_log2_error"] is None and report["within_one_twofold_step"] is None


def test_exact_error_and_coverage_use_only_eligible_answered_cases(tmp_path):
    desired = [experiment("answer-one", value=4.0), experiment("answer-two", value=4.0),
               experiment("abstained"), experiment("missing"),
               experiment("protein-endpoint", kind="target_binding"), experiment("molar-MIC", unit="uM")]
    manifest, cases, split = focus_cohort(tmp_path, desired)
    ids = {item["record_id"]: item["case_id"] for item in cases}
    forecasts = [prediction(ids["answer-one"], 8.0), prediction(ids["answer-two"], 16.0),
                 prediction(ids["abstained"], None), prediction(ids["protein-endpoint"], 4.0),
                 prediction(ids["molar-MIC"], 4.0)]
    report = score_evaluation(manifest, write_predictions(tmp_path / "predictions.jsonl", forecasts), split=split)
    assert report["cases"] == 6 and report["eligible_mic_cases"] == 4
    assert report["answered_mic_cases"] == 2 and report["numeric_answer_coverage"] == 0.5
    assert report["mean_absolute_log2_error"] == 1.5 and report["within_one_twofold_step"] == 0.5
    assert report["matched_omics_cases"] == 0
    details = {item["record_id"]: item for item in report["details"]}
    assert details["protein-endpoint"]["reason"] == "endpoint_not_mic_mass_concentration"
    assert details["molar-MIC"]["reason"] == "endpoint_not_mic_mass_concentration"
    assert details["missing"]["reason"] == "unanswered_or_invalid_estimate"


@pytest.mark.parametrize("value,status,unit,basis", [
    (True, "completed", "ug/mL", "llm_estimate"), (0.0, "completed", "ug/mL", "llm_estimate"),
    (-1.0, "completed", "ug/mL", "llm_estimate"), (float("nan"), "completed", "ug/mL", "llm_estimate"),
    (float("inf"), "completed", "ug/mL", "llm_estimate"), ("4", "completed", "ug/mL", "llm_estimate"),
    (4.0, "failed", "ug/mL", "llm_estimate"), (4.0, "completed", "uM", "llm_estimate"),
    (4.0, "completed", "ug/mL", "retrieved_label"),
])
def test_invalid_or_non_llm_estimates_are_unanswered_not_good_accuracy(tmp_path, value, status, unit, basis):
    manifest, cases, split = focus_cohort(tmp_path, [experiment("focus")])
    forecast = prediction(cases[0]["case_id"], value, status=status)
    forecast["assessment"]["mic_estimate"].update(unit=unit, basis=basis)
    report = score_evaluation(manifest, write_predictions(tmp_path / "predictions.jsonl", [forecast]), split=split)
    assert report["answered_mic_cases"] == 0 and report["numeric_answer_coverage"] == 0.0
    assert report["mean_absolute_log2_error"] is None


def test_zero_eligible_endpoints_have_null_coverage(tmp_path):
    manifest, _, split = focus_cohort(tmp_path, [experiment("focus", kind="target_binding")])
    report = score_evaluation(manifest, write_predictions(tmp_path / "predictions.jsonl", []), split=split)
    assert report["eligible_mic_cases"] == 0 and report["numeric_answer_coverage"] is None


@pytest.mark.parametrize("assessment", [None, {"mic_estimate": None}])
def test_null_report_sections_are_counted_as_unanswered(tmp_path, assessment):
    manifest, cases, split = focus_cohort(tmp_path, [experiment("focus")])
    forecast = prediction(cases[0]["case_id"], 4.0, assessment=assessment)
    report = score_evaluation(manifest, write_predictions(tmp_path / "predictions.jsonl", [forecast]), split=split)
    assert report["answered_mic_cases"] == 0 and report["numeric_answer_coverage"] == 0.0
    assert report["details"][0]["reason"] == "unanswered_or_invalid_estimate"


def test_prediction_report_candidate_id_is_accepted_and_duplicates_rejected(tmp_path):
    manifest, cases, split = focus_cohort(tmp_path, [experiment("focus")])
    forecast = prediction(cases[0]["case_id"], 4.0)
    forecast["candidate"] = {"id": forecast.pop("case_id")}
    path = write_predictions(tmp_path / "predictions.jsonl", [forecast])
    assert score_evaluation(manifest, path, split=split)["mean_absolute_log2_error"] == 0.0
    write_predictions(path, [forecast, forecast])
    with pytest.raises(ValueError, match="duplicate_prediction_case"):
        score_evaluation(manifest, path, split=split)


def test_prediction_from_another_split_or_unknown_case_is_rejected(tmp_path):
    manifest, cases, split = focus_cohort(tmp_path, [experiment("focus")])
    all_index = rows(manifest.parent / "answers.index.jsonl")
    other = next(item for item in all_index if item["split"] != split)
    for case_id in [other["case_id"], "unknown-case"]:
        with pytest.raises(ValueError, match="prediction_case_outside_requested_split"):
            score_evaluation(manifest, write_predictions(tmp_path / "predictions.jsonl", [prediction(case_id, 4.0)]), split=split)


def test_frozen_destination_cannot_be_overwritten(tmp_path):
    source = write_records(tmp_path / "labels.jsonl", [experiment("one", "CCO"), experiment("two", "CCN"), experiment("three", "c1ccccc1")])
    folder = tmp_path / "frozen"
    freeze_evaluation(source, folder)
    snapshot = {item.name: item.read_bytes() for item in folder.iterdir()}
    with pytest.raises(ValueError, match="frozen_evaluation_destination_exists"):
        freeze_evaluation(source, folder, seed=999)
    assert {item.name: item.read_bytes() for item in folder.iterdir()} == snapshot


def test_changed_canonical_source_is_rejected_before_scoring(tmp_path):
    manifest, cases, split = focus_cohort(tmp_path, [experiment("focus")])
    original = json.loads(manifest.read_text())["label_source"]
    source = Path(original)
    source.write_text(source.read_text() + "\n")
    with pytest.raises(ValueError, match="frozen_label_source_changed"):
        score_evaluation(manifest, write_predictions(tmp_path / "predictions.jsonl", [prediction(cases[0]["case_id"], 4.0)]), split=split)


def test_duplicate_records_cannot_be_frozen_as_independent_experiments(tmp_path):
    source = write_records(tmp_path / "labels.jsonl", [experiment("duplicate"), experiment("duplicate")])
    with pytest.raises(ValueError, match="duplicate_experiment_record_ids"):
        freeze_evaluation(source, tmp_path / "frozen")


@pytest.mark.parametrize("parameters", [{"seed": True}, {"test_fraction": 0.0}, {"validation_fraction": 0.0},
                                      {"test_fraction": 0.6, "validation_fraction": 0.4}, {"grouping": "row"}])
def test_invalid_freeze_parameters_are_not_written(tmp_path, parameters):
    source = write_records(tmp_path / "labels.jsonl", [experiment("one")])
    with pytest.raises(ValueError, match="invalid_split"):
        freeze_evaluation(source, tmp_path / "frozen", **parameters)
    assert not (tmp_path / "frozen").exists()
