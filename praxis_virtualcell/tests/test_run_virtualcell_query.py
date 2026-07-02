"""v0.6:统一 query 服务层 —— 离线确定性 + validator + LLM 边界。

不需网络:OFFLINE 模式 parse 用确定性 fallback、run 用 mock runtime、LLM 不碰预测。
"""
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.workflows.run_virtualcell_query import (
    parse_query,
    run_full_query,
    run_query,
    validate_candidate,
)

_OFFLINE = RuntimeConfig(mode=Mode.OFFLINE, llm_enabled=False)


def test_validate_valid_human_gene():
    v = validate_candidate({"species": "human", "perturbation_type": "gene",
                            "perturbation_targets": ["ahr"], "task_type": "predict_delta_expression"})
    assert v["schema_valid"] and not v["missing_fields"] and not v["errors"]
    assert v["normalized"]["perturbation_targets"] == ["AHR"]     # 归一大写


def test_validate_unsupported_species():
    v = validate_candidate({"species": "martian", "perturbation_type": "gene",
                            "perturbation_targets": ["AHR"], "task_type": "predict_delta_expression"})
    assert not v["schema_valid"] and any("unsupported_species" in e for e in v["errors"])


def test_validate_missing_targets():
    v = validate_candidate({"species": "human", "perturbation_type": "gene",
                            "perturbation_targets": [], "task_type": "predict_delta_expression"})
    assert not v["schema_valid"] and "perturbation_targets" in v["missing_fields"]


def test_parse_offline_uses_deterministic_no_llm():
    p = parse_query("在 human K562 里敲掉 AHR 会怎么样", config=_OFFLINE)
    assert p["llm_used"] is False and p["fallback_used"] is True
    assert p["parser"] == "deterministic"
    assert p["candidate_request"]["species"] == "human"
    assert "AHR" in p["candidate_request"]["perturbation_targets"]


def test_parse_offline_never_populates_llm_metadata():
    p = parse_query("human AHR knockout", config=_OFFLINE)
    assert p["llm_metadata"] == {}                # OFFLINE 完全不碰 LLM


def test_run_query_offline_deterministic():
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    out = run_query(req, config=_OFFLINE)
    assert out["llm_used_for_prediction"] is False
    assert "structured_report" in out and out["trace"]
    assert out["narrative"] is None               # offline 无 narrative
    assert out["mode"] == "offline"


def test_run_full_query_offline_end_to_end():
    out = run_full_query("在 human 细胞里敲掉 AHR", config=_OFFLINE)
    assert out["stage"] in ("done", "clarification_required")
    if out["stage"] == "done":
        assert out["llm_used_for_prediction"] is False


def test_run_full_query_clarification_on_unparseable():
    out = run_full_query("随便说点什么没有基因信息", config=_OFFLINE)
    assert out["stage"] == "clarification_required"
    assert out["missing_fields"]
