import json

import pytest

from praxis_virtualcell.datasets.qwen_evaluation import _case_metrics, _strain_matches, score_qwen_predictions
from praxis_virtualcell.datasets.qwen_sft import prepare_qwen_sft
from tests.datasets.test_qwen_sft import fixture_components
from praxis_virtualcell.datasets.labels import ExperimentRecord
from praxis_virtualcell.datasets.species_registry import _digest
from tests.datasets.test_labels import payload


def observation(value, relation="="):
    return {"relation": relation, "value": value,
            "lower": value if relation in {"=", ">", ">="} else None,
            "upper": value if relation in {"=", "<", "<="} else None,
            "lower_closed": relation != ">", "upper_closed": relation != "<"}


def test_repeated_measurements_are_order_independent_and_extra_answers_not_ignored():
    truth = [observation(2.0), observation(16.0)]
    target = {"mic_estimate": {"value": None}, "mic_observations": list(reversed(truth))}
    result = _case_metrics("one", target, None, truth, [], "species", "strain")
    assert result["exact_list_mae_log2"] == 0
    target["mic_observations"].append(observation(1000.0))
    result = _case_metrics("one", target, None, truth, [], "species", "strain")
    assert result["observation_count_match"] is False
    assert result["exact_list_mae_log2"] is None


def test_open_censor_boundary_is_preserved_in_point_scoring():
    truth = [observation(64.0, ">")]
    target = {"mic_estimate": {"value": 64.0}, "mic_observations": []}
    result = _case_metrics("one", target, None, truth, [], "species", "strain")
    assert result["point_errors_log2"] == []
    assert result["censored_point_consistency"] == [False]
    target["mic_estimate"]["value"] = 128.0
    assert _case_metrics("one", target, None, truth, [], "species", "strain")["censored_point_consistency"] == [True]


def test_saved_prediction_scoring_opens_private_answers_only_in_scorer(tmp_path, monkeypatch):
    source, _ = fixture_components(tmp_path, monkeypatch)
    output = tmp_path / "qwen"
    prepare_qwen_sft(source, output)
    public = json.loads((output / "validation.inputs.jsonl").read_text())
    assert "777.0" not in json.dumps(public)
    predictions = tmp_path / "predictions.jsonl"
    predictions.write_text(json.dumps({"record_id": public["record_id"], "status": "completed",
                                      "response": {"endpoint": "MIC", "unit": "ug/mL",
                                                   "observations": [observation(777.0)]}}) + "\n")
    with pytest.raises(ValueError, match="native_assay_review_required"):
        score_qwen_predictions(output, predictions)
    result = score_qwen_predictions(output, predictions, allow_unaudited=True)
    assert result["status"] == "preliminary_unaudited"
    assert result["metrics"]["point_mae_log2"] == 0
    assert result["metrics"]["exact_observation_list_mae_log2"] == 0
    assert result["mechanism_accuracy"] is None
    predictions.write_text(predictions.read_text() * 2)
    with pytest.raises(ValueError, match="duplicate_or_unknown"):
        score_qwen_predictions(output, predictions, allow_unaudited=True)


def test_invalid_numeric_prediction_is_counted_as_failure(tmp_path, monkeypatch):
    source, _ = fixture_components(tmp_path, monkeypatch)
    output = tmp_path / "qwen"
    prepare_qwen_sft(source, output)
    public = json.loads((output / "validation.inputs.jsonl").read_text())
    predictions = tmp_path / "predictions.jsonl"
    predictions.write_text(json.dumps({"record_id": public["record_id"],
                                      "response": {"endpoint": "MIC", "unit": "ug/mL",
                                                   "observations": [observation("777")]}}))
    result = score_qwen_predictions(output, predictions, allow_unaudited=True)
    assert result["metrics"]["valid_report_count"] == 0
    assert result["metrics"]["invalid_or_failed_records"] == {"invalid_assessment_contract": 1}


def test_strain_normalization_uses_curated_label_and_study_namespace():
    data = payload()
    data['organism'].update(strain='ATCC-25922', native_strain_label='isolate ATCC-25922')
    native = ExperimentRecord.model_validate(data)
    assert _strain_matches(native, {'label': 'ATCC 25922', 'namespace': 'ATCC'})
    assert not _strain_matches(native, {'label': 'ATCC 17978', 'namespace': 'ATCC'})
    assert not _strain_matches(native, {'label': None, 'namespace': None})
    data['organism'].update(strain='clinical 1', native_strain_label='isolate clinical 1')
    data['source'].update(document_id='CHEMBL-STUDY-A')
    native = ExperimentRecord.model_validate(data)
    assert _strain_matches(native, {'label': 'clinical 1', 'namespace': 'study:CHEMBL-STUDY-A'})
    assert not _strain_matches(native, {'label': 'clinical 1', 'namespace': 'study:CHEMBL-STUDY-B'})


def test_same_molecule_and_taxon_do_not_accept_wrong_public_strain(tmp_path, monkeypatch):
    source, cases = fixture_components(tmp_path, monkeypatch)
    dataset_summary = json.loads((source / 'summary.json').read_text())['dataset_summary']
    from pathlib import Path
    cases[3]['strain']['label'] = 'different-validation-strain'
    (Path(dataset_summary).parent / 'cases.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in cases))
    output = tmp_path / 'qwen'
    prepare_qwen_sft(source, output)
    public = json.loads((output / 'validation.inputs.jsonl').read_text())
    predictions = tmp_path / 'predictions.jsonl'
    predictions.write_text(json.dumps({'record_id': public['record_id'], 'response': {
        'endpoint': 'MIC', 'unit': 'ug/mL', 'observations': [observation(777.0)]}}) + '\n')
    with pytest.raises(ValueError, match='private_MIC_locator_identity_mismatch'):
        score_qwen_predictions(output, predictions, allow_unaudited=True)


@pytest.mark.parametrize('mismatch', ['manifest', 'split', 'status'])
def test_unaudited_mismatched_audit_cannot_exclude_records(tmp_path, monkeypatch, mismatch):
    source, _ = fixture_components(tmp_path, monkeypatch)
    output = tmp_path / 'qwen'
    prepare_qwen_sft(source, output)
    public = json.loads((output / 'validation.inputs.jsonl').read_text())
    predictions = tmp_path / 'predictions.jsonl'
    predictions.write_text(json.dumps({'record_id': public['record_id'], 'response': {
        'endpoint': 'MIC', 'unit': 'ug/mL', 'observations': [observation(777.0)]}}) + '\n')
    audit = {'status': 'reviewed', 'split': 'validation', 'dataset_manifest_sha256': _digest(output / 'manifest.json'),
             'excluded_record_ids': [public['record_id']]}
    if mismatch == 'manifest':
        audit['dataset_manifest_sha256'] = 'other-snapshot'
    elif mismatch == 'split':
        audit['split'] = 'test'
    else:
        audit['status'] = 'pending'
    audit_path = tmp_path / 'audit.json'
    audit_path.write_text(json.dumps(audit))
    result = score_qwen_predictions(output, predictions, audit_path=audit_path, allow_unaudited=True)
    assert result['status'] == 'preliminary_unaudited'
    assert result['excluded_record_count'] == 0
    assert result['metrics']['record_count'] == 1 and result['metrics']['point_mae_log2'] == 0
    # The same exclusions only take effect after the audit is bound to this
    # exact snapshot and split and actually marked reviewed.
    audit.update(status='reviewed', split='validation', dataset_manifest_sha256=_digest(output / 'manifest.json'))
    audit_path.write_text(json.dumps(audit))
    reviewed = score_qwen_predictions(output, predictions, audit_path=audit_path)
    assert reviewed['excluded_record_count'] == 1 and reviewed['metrics']['record_count'] == 0
