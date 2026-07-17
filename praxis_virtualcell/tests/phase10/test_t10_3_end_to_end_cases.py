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


def test_S5_M5_biosynthetic_advisory():
    """M5 生物合成 rule-based advisory:human gene RPL5(∈生物合成基因集,OOV)。
    实测同 S1 形状:请求 abstain,primary genetic_hub accept,biosynthetic_network secondary
    advisory downgrade,overall downgrade。断 advisory entry 非预测。"""
    sr, prov, mp, out = _run(_req("human", "gene", ["RPL5"]))
    assert sr["abstain"] is True
    assert sr["prediction"] is None
    assert mp["primary"] == "genetic_hub"
    assert "biosynthetic_network" in mp["secondary"]
    e = _entry(mp, "biosynthetic_network")
    assert e["verdict"] == "downgrade"
    assert "rule_based:biosynthetic_network_gene_set" in e["caution_flags"]
    assert "evidence_limited" in e["caution_flags"]
    assert mp["overall_verdict"] == "downgrade"


def test_S6_M6_spatial_niche_pipeline_limitation():
    """M6 细胞骨架/spatial_niche:管线**完全不可达**(∉ REAL_ENGINES ∉ dispatch_runner,
    _is_routable 门掉 medium 请求 → applicable 空)。诚实 limitation:
    human medium stromal_niche state → module_plan is None + abstain。
    (引擎级真值另在 tests/test_spatial_niche_case.py cohens_d~0.74,非本管线 case。)"""
    sr, prov, mp, out = _run(_req("human", "medium", ["stromal_niche"], "state"))
    assert sr["abstain"] is True
    assert mp is None                      # 管线不可达 = module_plan None
    assert sr["prediction"] is None
    assert sr["models_used"] == []


def test_S7_M7_state_scoring_accept():
    """M7 应激处理器真 state_scoring:human ligand IFNB1 state(Kang 2018 ISG)。
    实测:abstain=False, reliability=medium, models_used [CaseRunner], prediction {'delta':[2.485]}
    (ISG 强激活 cohens_d~2.5 映射), state_scoring accept。真实机制,非 mock。"""
    sr, prov, mp, out = _run(_req("human", "ligand", ["IFNB1"], "state"))
    assert sr["abstain"] is False
    assert sr["reliability"] == "medium"
    assert sr["models_used"] == ["CaseRunner"]
    assert sr["prediction"] == {"delta": [2.485]}
    assert mp["primary"] == "stress_processor"
    e = _entry(mp, "stress_processor")
    assert e["engine"] == "state_scoring" and e["verdict"] == "accept"
    assert mp["overall_verdict"] == "accept"


def test_S8_M8_degradation_advisory_mismatch():
    """M8 降解机器 rule-based advisory + 物种 mismatch:bacteria gene UBB growth。
    实测:primary cytoplasmic_metabolism(gem_fba)accept,degradation_machinery secondary
    verdict=downgrade **且 mismatch=='caution'**(bacteria_autophagy:原核无真核自噬),
    请求 abstain(UBB 非真实 E.coli 位点)。"""
    sr, prov, mp, out = _run(_req("bacteria", "gene", ["UBB"], "growth"))
    assert sr["abstain"] is True
    assert mp["primary"] == "cytoplasmic_metabolism"
    assert "degradation_machinery" in mp["secondary"]
    e = _entry(mp, "degradation_machinery")
    assert e["verdict"] == "downgrade"
    assert e["mismatch"] == "caution"
    assert "rule_based:degradation_machinery_gene_set" in e["caution_flags"]
    assert mp["overall_verdict"] == "downgrade"


# ============ 8 跨模块 ============

def test_X1_M4_M3_flux_positive():
    """跨模块正例:human ligand IFNB1 flux → primary cytoplasmic_metabolism + secondary
    mitochondrial_energy_metabolism,**均 pathway_scoring caution**,真实 prediction
    {'delta':[0.101,0.281]}(IFN 弱代谢信号 |d|<0.8), abstain=False。旗舰跨模块正例。"""
    sr, prov, mp, out = _run(_req("human", "ligand", ["IFNB1"], "flux"))
    assert sr["abstain"] is False
    assert sr["models_used"] == ["CaseRunner"]
    assert sr["prediction"] == {"delta": [0.101, 0.281]}
    assert mp["primary"] == "cytoplasmic_metabolism"
    assert mp["secondary"] == ["mitochondrial_energy_metabolism"]
    for m in ("cytoplasmic_metabolism", "mitochondrial_energy_metabolism"):
        e = _entry(mp, m)
        assert e["engine"] == "pathway_scoring" and e["verdict"] == "caution"
    assert mp["overall_verdict"] == "caution"


def test_X2_M4_M3_growth_negative_abstain():
    """跨模块应 abstain 负例:human gene_combination [MYC,KRAS] growth → 2-entry 均 downgrade,
    abstain(mammalian growth GEM 未 wire), prediction None。"""
    sr, prov, mp, out = _run(_req("human", "gene_combination", ["MYC", "KRAS"], "growth"))
    assert sr["abstain"] is True
    assert "CaseRunner" in sr["models_rejected"]
    assert sr["prediction"] is None
    assert mp["primary"] == "cytoplasmic_metabolism"
    assert mp["secondary"] == ["mitochondrial_energy_metabolism"]
    for m in ("cytoplasmic_metabolism", "mitochondrial_energy_metabolism"):
        assert _entry(mp, m)["verdict"] == "downgrade"
    assert mp["overall_verdict"] == "downgrade"


def test_X3_quad_four_module_advisory():
    """最富 module_plan(4 entry):human gene [SLC2A1,RPL5,PSMB5] 一次命中 3 个基因集 →
    primary genetic_hub + 3 advisory secondary(membrane/biosynthetic/degradation,MODULE_ORDER 序),
    全 downgrade,请求 abstain(全 OOV)。"""
    sr, prov, mp, out = _run(_req("human", "gene", ["SLC2A1", "RPL5", "PSMB5"]))
    assert sr["abstain"] is True
    assert sr["prediction"] is None
    assert mp["primary"] == "genetic_hub"
    assert mp["secondary"] == ["membrane_system", "biosynthetic_network", "degradation_machinery"]
    assert len(mp["entries"]) == 4
    for m in ("membrane_system", "biosynthetic_network", "degradation_machinery"):
        e = _entry(mp, m)
        assert e["verdict"] == "downgrade"
        assert f"rule_based:{m}_gene_set" in e["caution_flags"]
        assert "evidence_limited" in e["caution_flags"]
    assert mp["overall_verdict"] == "downgrade"


def test_X4_M4_M8_bacteria_mismatch():
    """跨模块 + 物种 mismatch:bacteria gene UBB growth → M4 primary(gem_fba)+ M8 secondary
    携 mismatch=='caution'(bacteria 无真核自噬),abstain。跨模块与 mismatch 治理同 plan。"""
    sr, prov, mp, out = _run(_req("bacteria", "gene", ["UBB"], "growth"))
    assert sr["abstain"] is True
    assert mp["primary"] == "cytoplasmic_metabolism"
    assert _entry(mp, "cytoplasmic_metabolism")["engine"] == "gem_fba"
    assert "degradation_machinery" in mp["secondary"]
    e = _entry(mp, "degradation_machinery")
    assert e["mismatch"] == "caution"
    assert "rule_based:degradation_machinery_gene_set" in e["caution_flags"]
    assert mp["overall_verdict"] == "downgrade"
