"""P10.D T10.3 端到端 16 case —— 8 单模块 + 8 跨模块,走完整管线 run_query。

**harness = run_query(request_dict)**(非 run_full_query(text)):spec §2.1 —— OFFLINE 确定性
解析无法设 output_modality,只能路由 gene→expression;故 16 case 用 request_dict 驱动。

**断言全部来自控制器实测的真实 run_query 输出**(非 grounding agent 声称;spec 阶段已证伪
agent 一条假 bug)。三条 paper 级诚实事实钉死:
1. M1/M5/M8 rule-based advisory:基因集成员 OOV → 请求自身 abstain,断言是 module_plan
   **secondary advisory entry**(caution_flags rule_based:*+evidence_limited, downgrade)
   **不是**非 abstain 预测(spec §2.2)。
2. module_plan.overall_verdict 是**路由级声明**,可与引擎实际执行**背离**——X8:overall=='accept'
   YET abstain==True。断言同时断两者,把背离文档化(spec §2.2)。
3. C1 跨模块一致性 gate 自然输入**从不触发**:cross_module_consistency 键在一致 plan 上缺席;
   gate 触发只能 monkeypatch(先例 test_t10_5)。X6 断 NO-OP,不声称自然触发(spec §2.2)。

**只有 S2b(M2 真实 GEARS)需 .53**,本计划延后;此文件的 16 core case 全本地。
"""

from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.workflows.run_virtualcell_query import run_query

_CFG = RuntimeConfig(mode=Mode.OFFLINE)
_BASE = {"input_modality": "scRNA", "task_type": "predict_delta_expression"}


def _req(species, ptype, targets, out="delta_expression"):
    return {**_BASE, "species": species, "perturbation_type": ptype,
            "perturbation_targets": targets, "output_modality": out}


def _run(req):
    """跑完整管线,返回 (structured_report, provenance, module_plan, out)。"""
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    mp = out["provenance"].get("module_plan")
    return sr, out["provenance"], mp, out


def _entry(mp, module):
    """取 module_plan 里某模块的 entry(找不到返 None)。"""
    for e in (mp or {}).get("entries", []):
        if e.get("module") == module:
            return e
    return None


# ============ 8 单模块 ============

def test_S1_M1_membrane_advisory():
    """M1 膜系统 rule-based advisory:human gene FASN(∈膜基因集,mock OOV)。
    实测:请求自身 abstain(learned_abstain),primary genetic_hub verdict=accept,
    membrane_system 作 secondary advisory downgrade,overall downgrade。
    **断言的是 advisory entry 不是预测**(FASN OOV → prediction None)。"""
    sr, prov, mp, out = _run(_req("human", "gene", ["FASN"]))
    assert sr["abstain"] is True
    assert "learned_abstain_low_reliability" in sr["abstain_reasons"]
    assert sr["prediction"] is None
    assert mp["primary"] == "genetic_hub"
    assert "membrane_system" in mp["secondary"]
    e = _entry(mp, "membrane_system")
    assert e["role"] == "secondary" and e["verdict"] == "downgrade"
    assert "rule_based:membrane_system_gene_set" in e["caution_flags"]
    assert "evidence_limited" in e["caution_flags"]
    assert mp["overall_verdict"] == "downgrade"
    assert out["llm_used_for_prediction"] is False


def test_S2_M2_genetic_hub_mock_accept():
    """M2 基因枢纽 mock donor accept:human gene AHR(in-vocab)。
    实测:abstain=False, reliability=high, models_used 三 Mock*, prediction {'delta':[0.3]},
    primary genetic_hub donor_predictor accept, secondary 空。(.53 真实 GEARS 变体 S2b 延后)"""
    sr, prov, mp, out = _run(_req("human", "gene", ["AHR"]))
    assert sr["abstain"] is False
    assert sr["reliability"] == "high"
    assert sr["models_used"] == ["MockLinear", "MockCPA", "MockGEARS"]
    assert sr["prediction"] == {"delta": [0.3]}
    assert mp["primary"] == "genetic_hub" and mp["secondary"] == []
    e = _entry(mp, "genetic_hub")
    assert e["engine"] == "donor_predictor" and e["verdict"] == "accept"
    assert mp["overall_verdict"] == "accept"
    assert out["llm_used_for_prediction"] is False


def test_S3_M3_mito_secondary_downgrade():
    """M3 线粒体能量:从不是 primary,只作 mammalian growth 的 secondary。
    human gene MYC growth。实测:primary cytoplasmic_metabolism verdict=downgrade
    (mammalian growth GEM 未 wire → CaseRunner rejected → abstain),M3 secondary downgrade。"""
    sr, prov, mp, out = _run(_req("human", "gene", ["MYC"], "growth"))
    assert sr["abstain"] is True
    assert "CaseRunner" in sr["models_rejected"]
    assert sr["prediction"] is None
    assert mp["primary"] == "cytoplasmic_metabolism"
    assert "mitochondrial_energy_metabolism" in mp["secondary"]
    e = _entry(mp, "mitochondrial_energy_metabolism")
    assert e["role"] == "secondary" and e["engine"] == "gem_fba" and e["verdict"] == "downgrade"
    assert mp["overall_verdict"] == "downgrade"


def test_S4_M4_cobra_fba_accept():
    """M4 胞质代谢真 cobra FBA:bacteria gene [b0720 gltA, b1136 icd] growth(双 essential)。
    实测:abstain=False, reliability=medium, models_used [CaseRunner], prediction {'delta':[-1.0,-1.0]}
    (双 essential → ratio 0 → delta -1.0), gem_fba accept。真实机制模型,非 mock。"""
    sr, prov, mp, out = _run(_req("bacteria", "gene", ["b0720", "b1136"], "growth"))
    assert sr["abstain"] is False
    assert sr["reliability"] == "medium"
    assert sr["models_used"] == ["CaseRunner"]
    assert sr["prediction"] == {"delta": [-1.0, -1.0]}
    assert mp["primary"] == "cytoplasmic_metabolism"
    e = _entry(mp, "cytoplasmic_metabolism")
    assert e["engine"] == "gem_fba" and e["verdict"] == "accept"
    assert mp["overall_verdict"] == "accept"
    assert out["llm_used_for_prediction"] is False
