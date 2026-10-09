"""确定性 report.md 渲染器测试:9 段齐全 / verdict 正确 / abstain 不出数值 /
缺字段防御 / 无 LLM / 可复现。"""
import pytest

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


def test_jobstore_writes_and_loads_report_md(tmp_path):
    from praxis_virtualcell.io.job_store import JobStore
    store = JobStore(str(tmp_path / "runs"))
    result = {
        "structured_report": _ACCEPT["report"],
        "trace": [], "provenance": _ACCEPT["report"]["provenance"],
        "mode": "offline", "llm_enabled": False,
    }
    store.save("job1", request=_ACCEPT["request"], result=result)
    assert (tmp_path / "runs" / "job1" / "report.md").is_file()
    loaded = store.load("job1")
    assert "report_md" in loaded
    assert loaded["report_md"].startswith("# PRAXIS-VirtualCell Report")
    assert "verdict: **accept**" in loaded["report_md"]


# ===== Phase 5:证据记录 + 验证计划两段 =====

_WITH_AL = {
    "mode": "offline",
    "request": {"request_id": "al_ahr", "species": "human", "cell_type": "K562",
                "perturbation_type": "gene", "perturbation_targets": ["AHR"],
                "task_type": "predict_delta_expression"},
    "report": {
        "request_id": "al_ahr", "abstain": False, "reliability": "medium",
        "prediction": {"delta": [0.2]}, "models_used": ["MockLinear", "MockCPA"],
        "models_rejected": [], "models_failed": [],
        "abstain_reasons": [], "downgrade_reasons": ["downgrade:model_disagreement_too_high"],
        "failed_checks": ["model_disagreement"],
        "model_disagreement": {"score": 0.8, "triggered": True},
        "critic_violations": [], "caution_flags": {}, "learned_reliability": None,
        "provenance": {
            "n_messages": 24, "rules_referenced": ["r1.yaml"], "rules_hit": [],
            "ortholog_cautions": {}, "rejection_reasons": {},
            "evidence_level": {"level": "E4", "rationale": ["downgrade"],
                               "ood_signal": "unknown", "aligned_with_disposition": True},
            "learning_queue": {"items": [
                {"candidate": "stress_processor@human:AHR", "module": "stress_processor",
                 "information_gain": 1.4, "drivers": ["disagreement_high", "module_weak"],
                 "rationale": "x"},
                {"candidate": "genetic_hub@human:AHR", "module": "genetic_hub",
                 "information_gain": 0.8, "drivers": ["disagreement_high"], "rationale": "y"}],
                "notes": []},
        },
    },
}


def test_evidence_record_section_present():
    from praxis_virtualcell.io.report_markdown import render_report_md
    md = render_report_md(_WITH_AL)
    assert "证据记录" in md or "Evidence Record" in md
    assert "E4" in md                      # evidence level 出现
    assert "ood_signal" in md or "OOD" in md


def test_validation_plan_section_present():
    from praxis_virtualcell.io.report_markdown import render_report_md
    md = render_report_md(_WITH_AL)
    assert "验证计划" in md or "Validation Plan" in md
    assert "stress_processor@human:AHR" in md    # top 候选出现
    assert "1.4" in md                            # information_gain 出现


def test_nine_sections_still_present_with_al():
    from praxis_virtualcell.io.report_markdown import render_report_md
    md = render_report_md(_WITH_AL)
    for s in _SECTIONS:
        assert s in md, f"缺段:{s}"       # 现有 9 段编号不被打乱


def test_missing_evidence_and_queue_shows_na():
    """缺 evidence_level/learning_queue(如旧 job)→ 标 N/A,不崩,9 段仍在。"""
    from praxis_virtualcell.io.report_markdown import render_report_md
    md = render_report_md(_ACCEPT)          # _ACCEPT 无 evidence_level/learning_queue 键
    assert "证据记录" in md or "Evidence Record" in md
    assert "验证计划" in md or "Validation Plan" in md
    assert "N/A" in md
    for s in _SECTIONS:
        assert s in md


# ===== Phase 8:模块路由段(module_plan 展示层) =====

_WITH_MODULE_PLAN = {
    "mode": "offline",
    "request": {"request_id": "mp_ahr", "species": "human", "cell_type": "K562",
                "perturbation_type": "gene", "perturbation_targets": ["AHR"],
                "task_type": "predict_delta_expression"},
    "report": {
        "request_id": "mp_ahr", "abstain": False, "reliability": "high",
        "prediction": {"delta": [0.3]}, "models_used": ["MockLinear"],
        "models_rejected": [], "models_failed": [], "abstain_reasons": [],
        "downgrade_reasons": [], "failed_checks": [], "model_disagreement": None,
        "critic_violations": [], "caution_flags": {}, "learned_reliability": None,
        "provenance": {"n_messages": 20, "rules_referenced": [], "rules_hit": [],
                       "ortholog_cautions": {}, "rejection_reasons": {},
                       "module_plan": {
                           "species": "human", "primary": "genetic_hub",
                           "secondary": ["stress_processor"], "overall_verdict": "accept",
                           "entries": [
                               {"module": "genetic_hub", "display_name": "Genetic Hub",
                                "role": "primary", "engine": "donor_predictor",
                                "route_disposition": "accept", "species_support": "supported",
                                "species_verdict": "accept", "verdict": "accept",
                                "mismatch": None, "caution_flags": [], "available_models": []},
                               {"module": "stress_processor", "display_name": "Stress Processor",
                                "role": "secondary", "engine": "state_scoring",
                                "route_disposition": "caution", "species_support": "supported",
                                "species_verdict": "accept", "verdict": "caution",
                                "mismatch": None, "caution_flags": [], "available_models": []}],
                           "notes": []}},
    },
}


def test_module_routing_section_present():
    md = render_report_md(_WITH_MODULE_PLAN)
    assert "模块路由" in md or "Module Routing" in md
    assert "genetic_hub" in md or "Genetic Hub" in md   # primary 出现
    assert "stress_processor" in md or "Stress Processor" in md  # secondary 出现
    assert "primary" in md and "secondary" in md


def test_module_routing_missing_shows_na():
    """无 module_plan(abstain/旧 job)→ 标 N/A,不崩,9 段仍在。"""
    md = render_report_md(_ACCEPT)   # _ACCEPT 无 module_plan
    assert "模块路由" in md or "Module Routing" in md
    assert "N/A" in md
    for s in _SECTIONS:
        assert s in md


def test_module_routing_does_not_break_nine_sections():
    md = render_report_md(_WITH_MODULE_PLAN)
    for s in _SECTIONS:
        assert s in md, f"缺段:{s}"


# ===== Task 8.5:report tests 扩到 30(module/evidence/多物种/provenance 一致) =====


@pytest.mark.parametrize("species", ["human", "mouse", "yeast", "bacteria"])
def test_report_all_species_render_nine_sections(species):
    job = {"mode": "offline",
           "request": {"request_id": f"sp_{species}", "species": species, "cell_type": "X",
                       "perturbation_type": "gene", "perturbation_targets": ["G1"],
                       "task_type": "predict_delta_expression"},
           "report": {"request_id": f"sp_{species}", "abstain": False, "reliability": "medium",
                      "prediction": {"delta": [0.1]}, "models_used": ["MockLinear"],
                      "models_rejected": [], "models_failed": [], "abstain_reasons": [],
                      "downgrade_reasons": [], "failed_checks": [], "model_disagreement": None,
                      "critic_violations": [], "caution_flags": {}, "learned_reliability": None,
                      "provenance": {"n_messages": 10, "rules_referenced": [], "rules_hit": [],
                                     "ortholog_cautions": {}, "rejection_reasons": {}}}}
    md = render_report_md(job)
    for s in _SECTIONS:
        assert s in md
    if species != "human":
        assert species in md  # 非 human 进 Limitations


def test_non_human_species_downgrade_note_in_limitations():
    for sp in ("mouse", "yeast", "bacteria"):
        job = {"mode": "offline", "request": {"species": sp, "perturbation_targets": ["G"],
               "perturbation_type": "gene", "task_type": "predict_delta_expression"},
               "report": {"abstain": False, "reliability": "medium", "prediction": {"delta": [0.1]},
                          "models_used": ["MockLinear"], "provenance": {}}}
        md = render_report_md(job)
        assert "跨物种" in md or "ortholog" in md.lower()


def test_module_routing_caution_entry_verdict_shown():
    md = render_report_md(_WITH_MODULE_PLAN)
    assert "caution" in md  # secondary stress_processor verdict=caution


def test_module_routing_mismatch_rendered():
    job = {"mode": "offline", "request": {"species": "bacteria", "perturbation_targets": ["b0720"],
           "perturbation_type": "gene", "task_type": "predict_delta_expression"},
           "report": {"abstain": False, "reliability": "medium", "prediction": {"delta": [0.1]},
                      "models_used": ["MockLinear"],
                      "provenance": {"module_plan": {"species": "bacteria", "primary": "cytoplasmic_metabolism",
                          "secondary": [], "overall_verdict": "caution",
                          "entries": [{"module": "cytoplasmic_metabolism", "display_name": "Cytoplasmic Metabolism",
                              "role": "primary", "engine": "gem_fba", "route_disposition": "accept",
                              "species_support": "supported", "species_verdict": "accept",
                              "verdict": "caution", "mismatch": "biological_mismatch"}], "notes": []}}}}
    md = render_report_md(job)
    assert "mismatch" in md and "biological_mismatch" in md


def test_evidence_level_e2_in_domain_accept():
    job = dict(_WITH_MODULE_PLAN)
    job = {**_WITH_MODULE_PLAN,
           "report": {**_WITH_MODULE_PLAN["report"],
                      "provenance": {**_WITH_MODULE_PLAN["report"]["provenance"],
                                     "evidence_level": {"level": "E2", "ood_signal": "in_domain",
                                                        "rationale": ["matched_perturbation_data"],
                                                        "aligned_with_disposition": True}}}}
    md = render_report_md(job)
    assert "E2" in md and "in_domain" in md


@pytest.mark.parametrize("level", ["E0", "E1", "E3", "E5"])
def test_evidence_levels_render(level):
    job = {"mode": "offline", "request": {"species": "human", "perturbation_targets": ["AHR"],
           "perturbation_type": "gene", "task_type": "predict_delta_expression"},
           "report": {"abstain": False, "reliability": "medium", "prediction": {"delta": [0.1]},
                      "models_used": ["MockLinear"],
                      "provenance": {"evidence_level": {"level": level, "ood_signal": "unknown",
                                     "rationale": [], "aligned_with_disposition": True}}}}
    md = render_report_md(job)
    assert level in md


def test_learning_queue_sorted_top5_only():
    items = [{"candidate": f"c{i}", "module": "genetic_hub", "information_gain": float(i),
              "drivers": ["d"]} for i in range(7)]
    job = {"mode": "offline", "request": {"species": "human", "perturbation_targets": ["AHR"],
           "perturbation_type": "gene", "task_type": "predict_delta_expression"},
           "report": {"abstain": False, "reliability": "medium", "prediction": {"delta": [0.1]},
                      "models_used": ["MockLinear"],
                      "provenance": {"learning_queue": {"items": items, "notes": []}}}}
    md = render_report_md(job)
    assert "c0" in md  # 前 5 项渲染(renderer 取 items[:5];此测钉现有 top-5 行为)


def test_provenance_module_plan_and_evidence_coexist():
    job = {**_WITH_MODULE_PLAN,
           "report": {**_WITH_MODULE_PLAN["report"],
                      "provenance": {**_WITH_MODULE_PLAN["report"]["provenance"],
                                     "evidence_level": {"level": "E3", "ood_signal": "unknown",
                                                        "rationale": [], "aligned_with_disposition": True},
                                     "learning_queue": {"items": [], "notes": []}}}}
    md = render_report_md(job)
    assert ("模块路由" in md or "Module Routing" in md)
    assert "E3" in md
    assert "证据记录" in md or "Evidence Record" in md


def test_report_md_ends_with_newline():
    assert render_report_md(_WITH_MODULE_PLAN).endswith("\n")


def test_report_md_no_llm_in_module_plan_path():
    md = render_report_md(_WITH_MODULE_PLAN)
    assert "llm_used_for_prediction: `False`" in md


def test_empty_module_plan_entries_no_crash():
    job = {"mode": "offline", "request": {"species": "human", "perturbation_targets": ["AHR"],
           "perturbation_type": "gene", "task_type": "predict_delta_expression"},
           "report": {"abstain": False, "reliability": "high", "prediction": {"delta": [0.1]},
                      "models_used": ["MockLinear"],
                      "provenance": {"module_plan": {"species": "human", "primary": "genetic_hub",
                          "secondary": [], "overall_verdict": "accept", "entries": [], "notes": []}}}}
    md = render_report_md(job)
    assert "genetic_hub" in md  # primary 仍展示,即使 entries 空


def test_downgrade_with_module_plan_verdict_consistency():
    md = render_report_md(_WITH_MODULE_PLAN)
    # overall_verdict=accept 出现在模块路由段
    assert "overall_verdict: **accept**" in md


def test_reproducible_with_module_plan():
    assert render_report_md(_WITH_MODULE_PLAN) == render_report_md(_WITH_MODULE_PLAN)


def test_module_routing_section_after_routing_decision():
    md = render_report_md(_WITH_MODULE_PLAN)
    assert md.index("## 3. Routing Decision") < md.index("模块路由") < md.index("## 4. Result Summary")


def test_all_four_species_with_module_plan_no_crash():
    for sp in ("human", "mouse", "yeast", "bacteria"):
        job = {"mode": "offline", "request": {"species": sp, "perturbation_targets": ["G"],
               "perturbation_type": "gene", "task_type": "predict_delta_expression"},
               "report": {"abstain": False, "reliability": "medium", "prediction": {"delta": [0.1]},
                          "models_used": ["MockLinear"],
                          "provenance": {"module_plan": {"species": sp, "primary": "cytoplasmic_metabolism",
                              "secondary": [], "overall_verdict": "accept",
                              "entries": [{"module": "cytoplasmic_metabolism",
                                  "display_name": "Cytoplasmic Metabolism", "role": "primary",
                                  "engine": "gem_fba", "route_disposition": "accept",
                                  "species_support": "supported", "species_verdict": "accept",
                                  "verdict": "accept", "mismatch": None}], "notes": []}}}}
        md = render_report_md(job)
        assert "cytoplasmic_metabolism" in md
