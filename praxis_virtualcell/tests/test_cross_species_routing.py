"""Week 5:cross-species brain 路由/拒绝/ortholog caution。断言"可见差异"(非仅 abstain)以防 §7.3 退化。"""
from praxis_virtualcell.workflows.predict_delta_expression import run_request


def _req(species, targets=("AHR",)):
    return {"request_id": "r", "species": species, "perturbation_type": "gene",
            "perturbation_targets": list(targets), "input_modality": "scRNA",
            "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


def test_human_full_applicable_no_caution():
    r = run_request(_req("human", ["AHR"]))
    assert r["abstain"] is False
    assert "MockCPA" in r["models_used"]
    assert r["caution_flags"] == {}  # human 是 native host,无 cross-species caution


def test_mouse_applicable_with_ortholog_caution():
    # §7.3:human predictor 迁 mouse → applicable(非 reject)但带 ortholog caution,且 caution 在 report 可见
    r = run_request(_req("mouse", ["TRP53"]))
    assert r["abstain"] is False
    assert r["models_used"]
    assert r["caution_flags"], "mouse 应携带 ortholog caution(否则 §7.3 退化)"
    flat = [c for flags in r["caution_flags"].values() for c in flags]
    assert "ortholog_required" in flat
    assert "human_predictor_transfer_to_mouse_requires_ortholog" in r["provenance"]["rules_hit"]


def test_bacteria_abstain_negative_transfer_rule():
    # §7.2 + §7.4 + §7.5:bacteria 拒所有 mammalian predictor → abstain,且拒因是具体 negative_transfer rule
    r = run_request(_req("bacteria", ["AHR"]))
    assert r["abstain"] is True
    assert r["models_used"] == []
    rr = r["provenance"]["rejection_reasons"]
    assert rr and all(v["reason"] == "mammalian_scrna_predictor_not_applicable" for v in rr.values())
    assert "mammalian_scrna_predictor_not_applicable" in r["provenance"]["rules_hit"]


def test_yeast_abstain_negative_transfer_rule():
    r = run_request(_req("yeast", ["AHR"]))
    assert r["abstain"] is True
    assert r["models_used"] == []
    assert "mammalian_scrna_predictor_not_applicable" in r["provenance"]["rules_hit"]


def test_martian_no_phantom_rules_referenced():
    # §7.5:未知 species 不得在 trace 写指向不存在文件的"被引用规则"
    r = run_request(_req("martian", ["AHR"]))
    assert r["abstain"] is True
    assert not any("martian" in path for path in r["provenance"]["rules_referenced"])


def test_four_species_route_differently():
    # §7.1:同一 task 在 human/mouse/bacteria/yeast 下路由结果不同
    human = run_request(_req("human", ["AHR"]))
    mouse = run_request(_req("mouse", ["TRP53"]))
    bacteria = run_request(_req("bacteria", ["AHR"]))
    yeast = run_request(_req("yeast", ["AHR"]))
    assert human["abstain"] is False and human["caution_flags"] == {}      # 全 applicable 无 caution
    assert mouse["abstain"] is False and mouse["caution_flags"]            # applicable + caution
    assert bacteria["abstain"] is True and yeast["abstain"] is True        # 全拒 → abstain
