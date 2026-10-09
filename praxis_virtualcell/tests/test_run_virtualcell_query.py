"""v0.6:统一 query 服务层 —— 离线确定性 + validator + LLM 边界。

不需网络:OFFLINE 模式 parse 用确定性 fallback、run 用 mock runtime、LLM 不碰预测。
"""

import json

import pytest

from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.workflows.run_virtualcell_query import (
    parse_query,
    run_formal_query,
    run_full_query,
    run_query,
    validate_candidate,
)

_OFFLINE = RuntimeConfig(mode=Mode.OFFLINE, llm_enabled=False)


def test_validate_valid_human_gene():
    v = validate_candidate(
        {
            "species": "human",
            "perturbation_type": "gene",
            "perturbation_targets": ["ahr"],
            "task_type": "predict_delta_expression",
        }
    )
    assert v["schema_valid"] and not v["missing_fields"] and not v["errors"]
    assert v["normalized"]["perturbation_targets"] == ["AHR"]  # 归一大写


def test_validate_unsupported_species():
    v = validate_candidate(
        {
            "species": "martian",
            "perturbation_type": "gene",
            "perturbation_targets": ["AHR"],
            "task_type": "predict_delta_expression",
        }
    )
    assert not v["schema_valid"] and any("unsupported_species" in e for e in v["errors"])


def test_validate_missing_targets():
    v = validate_candidate(
        {
            "species": "human",
            "perturbation_type": "gene",
            "perturbation_targets": [],
            "task_type": "predict_delta_expression",
        }
    )
    assert not v["schema_valid"] and "perturbation_targets" in v["missing_fields"]


def test_parse_offline_uses_deterministic_no_llm():
    p = parse_query("在 human K562 里敲掉 AHR 会怎么样", config=_OFFLINE)
    assert p["llm_used"] is False and p["fallback_used"] is True
    assert p["parser"] == "deterministic"
    assert p["candidate_request"]["species"] == "human"
    assert "AHR" in p["candidate_request"]["perturbation_targets"]


def test_parse_offline_never_populates_llm_metadata():
    p = parse_query("human AHR knockout", config=_OFFLINE)
    assert p["llm_metadata"] == {}  # OFFLINE 完全不碰 LLM


def test_parse_offline_reads_explicit_structured_description():
    structured = json.dumps(
        {
            "species": "bacteria",
            "perturbation_type": "gene",
            "perturbation_targets": ["b0720", "b1136"],
            "output_modality": "growth",
        }
    )
    p = parse_query(
        f"请运行这个结构化请求\n物种:bacteria\n结构化描述:{structured}",
        config=_OFFLINE,
    )
    assert p["schema_valid"] is True
    assert p["candidate_request"]["species"] == "bacteria"
    assert p["candidate_request"]["perturbation_targets"] == ["B0720", "B1136"]
    assert p["candidate_request"]["output_modality"] == "growth"


def test_parse_offline_rejects_structured_description_output_outside_whitelist():
    structured = json.dumps(
        {
            "species": "human",
            "perturbation_type": "gene",
            "perturbation_targets": ["AHR"],
            "output_modality": "invented_output",
        }
    )
    p = parse_query(
        f"请运行这个结构化请求\n结构化描述:{structured}",
        config=_OFFLINE,
    )
    assert p["schema_valid"] is False
    assert p["clarification_required"] is True
    assert p["errors"] == ["unsupported_output_modality:invented_output"]


def test_parse_structured_description_overrides_llm_candidate(monkeypatch):
    class _StubClient:
        def complete(self, messages, **kwargs):
            return {
                "content": json.dumps(
                    {
                        "species": "mouse",
                        "perturbation_type": "gene",
                        "perturbation_targets": ["GATA1"],
                        "output_modality": "delta_expression",
                        "task_type": "predict_delta_expression",
                    }
                ),
                "error": None,
            }

    import praxis_virtualcell.agents_llm.llm_client as llm_client

    monkeypatch.setattr(llm_client, "make_llm_client", lambda config: _StubClient())
    structured = json.dumps(
        {
            "species": "bacteria",
            "perturbation_type": "gene",
            "perturbation_targets": ["b0720"],
            "output_modality": "growth",
        }
    )
    p = parse_query(
        f"请运行任务\n结构化描述:{structured}",
        config=RuntimeConfig(mode=Mode.LLM_ASSISTED, llm_enabled=True, deepseek_api_key="stub-not-a-real-key"),
    )
    assert p["llm_used"] is True
    assert p["schema_valid"] is True
    assert p["candidate_request"]["species"] == "bacteria"
    assert p["candidate_request"]["perturbation_targets"] == ["B0720"]
    assert p["candidate_request"]["output_modality"] == "growth"


def test_parse_malformed_structured_description_forces_clarification_even_when_text_is_valid():
    p = parse_query(
        'human AHR knockout\n结构化描述:{"species":"mouse"',
        config=_OFFLINE,
    )
    assert p["schema_valid"] is False
    assert p["clarification_required"] is True
    assert p["errors"] == ["structured_description_malformed"]


def test_parse_non_object_structured_description_forces_clarification():
    p = parse_query(
        'human AHR knockout\n结构化描述:["human", "AHR"]',
        config=_OFFLINE,
    )
    assert p["schema_valid"] is False
    assert p["errors"] == ["structured_description_not_object"]


def test_parse_structured_description_rejects_unknown_fields_and_non_string_output():
    unknown = parse_query(
        'human AHR knockout\n结构化描述:{"request_id":"user-controlled"}',
        config=_OFFLINE,
    )
    assert unknown["schema_valid"] is False
    assert unknown["errors"] == ["structured_description_unknown_fields"]

    wrong_type = parse_query(
        'human AHR knockout\n结构化描述:{"output_modality":{"bad":1}}',
        config=_OFFLINE,
    )
    assert wrong_type["schema_valid"] is False
    assert wrong_type["errors"] == ["invalid_output_modality_type"]


def test_parse_structured_description_rejects_non_list_requested_outputs():
    parsed = parse_query(
        'human AHR knockout\n结构化描述:{"requested_outputs":"growth"}',
        config=_OFFLINE,
    )
    assert parsed["schema_valid"] is False
    assert parsed["errors"] == ["invalid_requested_outputs_type"]


def test_parse_structured_description_rejects_requested_outputs_outside_whitelist():
    parsed = parse_query(
        'human AHR knockout\n结构化描述:{"requested_outputs":["invented"]}',
        config=_OFFLINE,
    )
    assert parsed["schema_valid"] is False
    assert parsed["errors"] == ["unsupported_requested_outputs"]


def test_parse_structured_description_rejects_mixed_target_types():
    parsed = parse_query(
        'human AHR knockout\n结构化描述:{"perturbation_targets":[{"gene":"TP53"},"AHR"]}',
        config=_OFFLINE,
    )
    assert parsed["schema_valid"] is False
    assert parsed["errors"] == ["invalid_perturbation_targets_type"]


def test_validate_candidate_normalizes_nested_metadata_control_fields():
    validated = validate_candidate(
        {
            "species": "human",
            "perturbation_type": "gene",
            "perturbation_targets": ["AHR"],
            "task_type": "predict_delta_expression",
            "metadata": {
                "requested_outputs": {"growth": True},
                "assumptions": ["safe", {"not": "text"}],
                "note": "preserve me",
            },
        }
    )
    assert validated["schema_valid"] is True
    assert validated["normalized"]["metadata"] == {
        "requested_outputs": [],
        "assumptions": ["safe"],
        "note": "preserve me",
    }


@pytest.mark.parametrize("bad_dose", [{}, "not-a-number", True, float("inf"), 10**400])
def test_validate_candidate_rejects_invalid_perturbation_dose(bad_dose):
    validated = validate_candidate(
        {
            "species": "human",
            "perturbation_type": "drug",
            "perturbation_targets": ["geldanamycin"],
            "task_type": "predict_delta_expression",
            "perturbation_dose": bad_dose,
        }
    )
    assert validated["schema_valid"] is False
    assert validated["errors"] == ["invalid_perturbation_dose"]


def test_validate_candidate_normalizes_finite_perturbation_dose():
    validated = validate_candidate(
        {
            "species": "human",
            "perturbation_type": "drug",
            "perturbation_targets": ["geldanamycin"],
            "task_type": "predict_delta_expression",
            "perturbation_dose": 10,
        }
    )
    assert validated["schema_valid"] is True
    assert validated["normalized"]["perturbation_dose"] == 10.0


def test_run_query_offline_deterministic():
    req = {
        "species": "human",
        "perturbation_type": "gene",
        "perturbation_targets": ["AHR"],
        "input_modality": "scRNA",
        "output_modality": "delta_expression",
        "task_type": "predict_delta_expression",
    }
    out = run_query(req, config=_OFFLINE)
    assert out["llm_used_for_prediction"] is False
    assert "structured_report" in out and out["trace"]
    assert out["narrative"] is None  # offline 无 narrative
    assert out["mode"] == "offline"


def test_formal_query_without_pack_abstains_without_legacy_mock_predictors():
    req = {
        "species": "human",
        "perturbation_type": "gene",
        "perturbation_targets": ["AHR"],
        "input_modality": "scRNA",
        "output_modality": "delta_expression",
        "task_type": "predict_delta_expression",
        "metadata": {"include_legacy_mock_predictors": True},
    }

    out = run_formal_query(req, config=_OFFLINE)

    report = out["structured_report"]
    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["models_used"] == []
    assert "pack_unregistered" in report["abstain_reasons"]
    assert report["learned_reliability"] is None
    execution_plan = report["provenance"]["execution_plan"]
    assert execution_plan["schema_version"] == "vc.execution-plan.v2"
    assert execution_plan["steps"] == []
    assert all("pack.unregistered" in item["reasons"] for item in execution_plan["reports"])
    assert not any(item["receiver"] in {"MockLinear", "MockCPA", "MockGEARS", "CaseRunner"} for item in out["trace"])


def test_run_full_query_offline_end_to_end():
    out = run_full_query("在 human 细胞里敲掉 AHR", config=_OFFLINE)
    assert out["stage"] in ("done", "clarification_required")
    if out["stage"] == "done":
        assert out["llm_used_for_prediction"] is False
        assert out["structured_report"]["prediction"] is None


def test_run_full_query_clarification_on_unparseable():
    out = run_full_query("随便说点什么没有基因信息", config=_OFFLINE)
    assert out["stage"] == "clarification_required"
    assert out["missing_fields"]
