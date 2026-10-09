"""Phase 2:GemWrapper —— 真实 GemModel 包成 ModelWrapper,证明契约在真模型上跑通。
cobra-gated(无 cobra → 整文件 skip,延续 test_ecoli_gem_case 惯例)。
断言:declare_scope 正确;真跑 KO(b0720 essential);基因不在 GEM → 不虚构(in_model=False)。"""
import pytest

cobra = pytest.importorskip("cobra")   # 无 cobra → skip

from praxis_virtualcell.model_zoo.wrappers.gem_wrapper import GemWrapper  # noqa: E402


@pytest.fixture(scope="module")
def wrapper():
    return GemWrapper()  # 默认 e_coli_core textbook(cobra 自带,无需外部数据)


def test_declare_scope_growth_bacteria_yeast(wrapper):
    scope = wrapper.declare_scope()
    assert scope["module"] == "cytoplasmic_metabolism"
    assert "bacteria" in scope["species"]
    assert "growth" in scope["task"]


def test_run_prediction_real_ko_essential(wrapper):
    # b0720 (gltA) 在 e_coli_core 中 essential → growth≈0
    out = wrapper.run_prediction({"targets": ["b0720"]})
    kos = {k["gene"]: k for k in out["prediction"]["knockouts"]}
    assert kos["b0720"]["in_model"] is True
    assert kos["b0720"]["essential"] is True


def test_gene_not_in_gem_not_fabricated(wrapper):
    # 基因不在 GEM → in_model=False,growth=None(不虚构生长)
    out = wrapper.run_prediction({"targets": ["ZZZ_notagene"]})
    ko = out["prediction"]["knockouts"][0]
    assert ko["in_model"] is False
    assert ko["growth"] is None


def test_uncertainty_contract(wrapper):
    out = wrapper.run_prediction({"targets": ["b0720"]})
    unc = wrapper.estimate_uncertainty({"targets": ["b0720"]}, out["prediction"])
    # GEM 是确定性 FBA:声明 method=deterministic_fba,available 明确(不假造随机 CI)
    assert "available" in unc
