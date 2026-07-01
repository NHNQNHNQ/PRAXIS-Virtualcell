"""W1.2(v0.4):route table + applicability rules —— 按 (species × perturbation_object ×
target_output) 把请求路由到引擎 {donor_predictor | gem_fba | embedding | reject},并给出
reliability disposition(accept / caution / downgrade / abstain)。

这是**声明式能力图**(presence-absence),不是性能;核心 applicability 铁律:
哺乳类 scRNA predictor **不得**用于 bacteria/yeast growth → 必须路由 GEM 或 abstain。
"""
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.agents.route_table import route, ENGINES


def _route(species, obj, out, targets=("AHR",), **extra):
    req = normalize_request({"species": species, "perturbation_object": obj,
                             "perturbation_targets": list(targets), "target_output": out, **extra})
    return route(req)


def test_engines_defined():
    assert {"donor_predictor", "gem_fba", "embedding", "reject"} <= set(ENGINES)


def test_human_gene_expression_accept():
    d = _route("human", "gene", "expression")
    assert d.engine == "donor_predictor"
    assert d.disposition == "accept"
    assert d.caution_flags == []


def test_mouse_gene_expression_ortholog_caution():
    d = _route("mouse", "gene", "expression", targets=("TRP53",))
    assert d.engine == "donor_predictor"
    assert d.disposition in ("caution", "downgrade")
    assert any("ortholog" in c for c in d.caution_flags), "mouse 应带 ortholog caution"


def test_bacteria_growth_routes_to_gem_not_mammalian():
    # applicability 铁律:bacteria growth 绝不路由到哺乳类 predictor
    d = _route("bacteria", "gene", "growth", targets=("b0720",))
    assert d.engine == "gem_fba"
    assert d.engine != "donor_predictor"
    assert d.disposition in ("accept", "caution")


def test_yeast_growth_routes_to_gem():
    d = _route("yeast", "gene", "growth", targets=("YAL001C",))
    assert d.engine == "gem_fba"


def test_bacteria_expression_abstains_no_mammalian_transfer():
    # 细菌 expression 无适用机制/scRNA predictor → abstain(哺乳类 predictor 不适用)
    d = _route("bacteria", "gene", "expression", targets=("b0720",))
    assert d.disposition == "abstain"
    assert d.engine != "donor_predictor"
    assert "mammalian" in d.reason or "not_applicable" in d.reason


def test_drug_routes_to_embedding_data_gated_downgrade():
    # 药物扰动 → embedding 引擎;下游数据未就位 → downgrade(data-gated,不假装 accept)
    d = _route("human", "drug", "expression", targets=("aspirin",))
    assert d.engine == "embedding"
    assert d.disposition in ("downgrade", "abstain")
    assert d.data_gated is True


def test_human_gene_growth_no_mammalian_gem_downgrade():
    # human gene→growth 无接入 GEM(scFEA/Compass data-gated)→ 不得假装,downgrade/abstain
    d = _route("human", "gene", "growth")
    assert d.disposition in ("downgrade", "abstain")
    assert d.engine in ("gem_fba", "reject")


def test_route_decision_is_serializable():
    # 路由决策要能进 provenance(dict 化,审计可见)
    d = _route("bacteria", "gene", "growth", targets=("b0720",))
    dd = d.to_dict()
    assert dd["engine"] == "gem_fba"
    assert set(dd) >= {"engine", "disposition", "reason", "caution_flags", "data_gated"}
