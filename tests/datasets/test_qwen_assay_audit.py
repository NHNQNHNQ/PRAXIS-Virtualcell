import json

from praxis_virtualcell.datasets.qwen_assay_audit import audit_qwen_assays
from praxis_virtualcell.datasets.qwen_sft import prepare_qwen_sft
from tests.datasets.test_qwen_sft import fixture_components


def test_unencoded_plasmid_is_isolated_without_exporting_MIC(tmp_path, monkeypatch):
    source, _ = fixture_components(tmp_path, monkeypatch)
    output = tmp_path / "qwen"
    prepare_qwen_sft(source, output)
    # Fixture sources have no assay ID. An explicit metadata fixture provides
    # that same source key; the audit still reads no MIC into its report.
    assays = tmp_path / "assays.json"
    assays.write_text(json.dumps([{"assay_chembl_id": None, "assay_tax_id": 470,
                                  "description": "Activity against strain B harboring plasmid pX by broth dilution"}]))
    result = audit_qwen_assays(output, split="validation", historical_assays=assays)
    assert result["eligible_record_count"] == 0
    assert result["reason_counts"] == {"derived_genetic_background_requires_review": 1}
    assert result["human_reviewed"] is False
    assert result["MIC_values_exported"] is False
    assert "777.0" not in json.dumps(result)
    assert result["frozen_split_changed"] is False
    assays.write_text(json.dumps([{"assay_chembl_id": None, "assay_tax_id": 470,
                                  "description": "Activity against strain B by broth dilution"}]))
    ordinary = audit_qwen_assays(output, split="validation", historical_assays=assays)
    assert ordinary["eligible_record_count"] == 1
    # An unstated plasmid is not annotated as absent or wild type.
    assert "wild_type" not in json.dumps(ordinary)


def test_missing_native_context_does_not_silently_pass_formal_scoring(tmp_path, monkeypatch):
    source, _ = fixture_components(tmp_path, monkeypatch)
    output = tmp_path / "qwen"
    prepare_qwen_sft(source, output)
    result = audit_qwen_assays(output, split="validation", historical_assays=tmp_path / "missing")
    assert result["reason_counts"] == {"native_assay_metadata_unavailable": 1}
    assert len(result["excluded_record_ids"]) == 1
