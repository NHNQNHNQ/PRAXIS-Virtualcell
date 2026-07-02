"""确定性 report.md 渲染器测试:9 段齐全 / verdict 正确 / abstain 不出数值 /
缺字段防御 / 无 LLM / 可复现。"""
from praxis_virtualcell.io.report_markdown import render_report_md

_ACCEPT = {
    "mode": "offline",
    "request": {"request_id": "ahr_k562_demo", "species": "human", "cell_type": "K562",
                "perturbation_type": "gene", "perturbation_targets": ["AHR"],
                "task_type": "predict_delta_expression"},
    "report": {
        "request_id": "ahr_k562_demo", "abstain": False, "reliability": "high",
        "prediction": {"delta": [0.3]},
        "models_used": ["MockLinear", "MockCPA", "MockGEARS"],
        "models_rejected": [], "models_failed": [],
        "abstain_reasons": [], "downgrade_reasons": [], "failed_checks": [],
        "model_disagreement": {"score": 0.33, "metric": "pairwise_cosine_distance", "triggered": False},
        "critic_violations": [], "caution_flags": {},
        "learned_reliability": {"reliability_mode": "learned_with_rule_fallback", "fallback": False,
                                "reliability_score": 0.7167, "abstain_decision": "accept",
                                "model_version": "reliability_v0.3.0", "feature_schema_version": "v0.3.0",
                                "artifact_sha256": "abc123", "abstain_artifact_sha256": "def456"},
        "provenance": {"n_messages": 21, "rules_referenced": ["r1.yaml", "r2.yaml"],
                       "rules_hit": [], "ortholog_cautions": {}, "rejection_reasons": {}},
    },
}

_ABSTAIN = {
    "mode": "offline",
    "request": {"request_id": "noab", "species": "human", "cell_type": None,
                "perturbation_type": "gene", "perturbation_targets": [],
                "task_type": "predict_delta_expression"},
    "report": {"request_id": "noab", "abstain": True, "reliability": "low", "prediction": None,
               "models_used": [], "models_rejected": [], "models_failed": [],
               "abstain_reasons": ["no_perturbation_specified"], "downgrade_reasons": [],
               "failed_checks": [], "model_disagreement": None, "critic_violations": [],
               "caution_flags": {}, "learned_reliability": None,
               "provenance": {"n_messages": 5, "rules_referenced": [], "rules_hit": [],
                              "ortholog_cautions": {}, "rejection_reasons": {}}},
}

_DOWNGRADE = {
    "mode": "offline",
    "request": {"request_id": "dg", "species": "mouse", "cell_type": "T cell",
                "perturbation_type": "gene", "perturbation_targets": ["GATA1"],
                "task_type": "predict_delta_expression"},
    "report": {"request_id": "dg", "abstain": False, "reliability": "medium",
               "prediction": {"delta": [0.1]}, "models_used": ["MockLinear", "MockCPA"],
               "models_rejected": ["MockGEARS"], "models_failed": [],
               "abstain_reasons": [], "downgrade_reasons": ["downgrade:model_disagreement_too_high"],
               "failed_checks": ["model_disagreement"], "model_disagreement": {"score": 0.9, "triggered": True},
               "critic_violations": [], "caution_flags": {"GATA1": "ortholog_projected"},
               "learned_reliability": None,
               "provenance": {"n_messages": 18, "rules_referenced": ["r1.yaml"], "rules_hit": [],
                              "ortholog_cautions": {"GATA1": "ortholog_projected"},
                              "rejection_reasons": {"MockGEARS": "cell_type_unsupported"}}},
}

_SECTIONS = ["## 1. Question", "## 2. Cell Context", "## 3. Routing Decision",
             "## 4. Result Summary", "## 5. Governance Verdict",
             "## 6. Evidence and Provenance", "## 7. Biological Interpretation",
             "## 8. Limitations", "## 9. Reproducibility"]


def test_accept_has_all_nine_sections():
    md = render_report_md(_ACCEPT)
    assert md.startswith("# PRAXIS-VirtualCell Report")
    for s in _SECTIONS:
        assert s in md, f"缺段:{s}"
    assert "verdict: **accept**" in md
    assert "AHR" in md and "MockLinear" in md
    assert "0.3" in md  # prediction 数值出现


def test_abstain_shows_no_prediction_number():
    md = render_report_md(_ABSTAIN)
    assert "verdict: **abstain**" in md
    assert "弃权" in md
    assert "no_perturbation_specified" in md  # 出现在 Governance/Limitations
    # abstain 不得 dump prediction:无 json 代码块、无预测数值
    assert "```json" not in md
    assert "不产出预测数值" in md


def test_downgrade_reasons_in_output():
    md = render_report_md(_DOWNGRADE)
    assert "verdict: **downgrade**" in md
    assert "downgrade:model_disagreement_too_high" in md
    # 跨物种(mouse) + caution flags 应进 Limitations
    assert "mouse" in md


def test_mock_predictor_flagged_in_limitations():
    md = render_report_md(_ACCEPT)
    assert "mock" in md.lower()  # Limitations 标注 mock predictor 非真跑数值


def test_minimal_job_does_not_crash():
    md = render_report_md({"report": {}})
    assert "# PRAXIS-VirtualCell Report" in md
    assert "N/A" in md
    for s in _SECTIONS:
        assert s in md


def test_no_llm_import_in_module():
    import praxis_virtualcell.io.report_markdown as m
    src = open(m.__file__, encoding="utf-8").read()
    assert "agents_llm" not in src and "llm_client" not in src
    assert "import openai" not in src and "litellm" not in src


def test_reproducible_byte_identical():
    assert render_report_md(_ACCEPT) == render_report_md(_ACCEPT)
    assert render_report_md(_ABSTAIN) == render_report_md(_ABSTAIN)
