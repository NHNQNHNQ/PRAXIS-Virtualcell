"""服务路径 artifact 的 CWD 无关性(部署级红线)。

生产站用 uvicorn 托管,进程 CWD 未必是仓库根。artifact 若按裸相对路径解析,在非仓库根
CWD 下会静默失效,后果三重:
  1. 违反"同输入同输出"确定性红线(同一查询两个 trace_hash);
  2. 静默降级——sir=None 但 abstained=False、abstain_reasons=[],报告不承认自己降级了;
  3. 永久闩死——_load_gsir 是 lru_cache,None 被钉住,事后 chdir 回仓库根也不恢复。

本测试把行为钉在两个不同 CWD 上:trace_hash 必须逐字相等。

两个刻意的设计约束(拆掉任一个,测试都会变成"空测"):
  - skip 守卫一律 __file__ 锚定。守卫若自己写成 CWD 相对路径,在 tmp CWD 下会
    "artifact 不存在 → skip",把本该红的测试变成绿的(空测比没测更危险)。
  - 两次 CWD 运行之间必须 cache_clear。否则第一次(仓库根)加载的模型留在 lru_cache 里,
    第二次直接命中缓存 → 修复前测试就是绿的,压根测不到路径解析。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

import praxis_virtualcell.mdr_gnb.predictors.default_registry as dr
from praxis_virtualcell.mdr_gnb.predictors.mechanistic.gem_fba import SPECIES_GEM, GemFbaPredictor


# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts

# test_artifact_path_cwd_independence.py: praxis_virtualcell/mdr_gnb/tests/
# parents[0]=tests parents[1]=mdr_gnb parents[2]=praxis_virtualcell parents[3]=仓库根
_REPO_ROOT = Path(__file__).resolve().parents[3]

# 真 artifact 是否在盘 —— 一律 __file__ 锚定判断(见模块 docstring 第一条约束)
_SIR_ARTIFACT = (_REPO_ROOT / "data" / "mdr_gnb" / "models" / "escherichia_coli"
                 / "genotype_to_sir__ceftriaxone.joblib")
_GEM_ECOLI = _REPO_ROOT / "data" / "mdr_gnb" / "gems" / "iML1515.xml.gz"
_HAS_COBRA = importlib.util.find_spec("cobra") is not None

# EC + blaCTX-M-15(ESBL)× ceftriaxone:仓库根 CWD 下真 artifact 出 sir="R"
_RAW_SIR = {
    "species": "escherichia_coli",
    "amr_profile": {"blaCTX-M-15": True},
    "drug_panel": [{"drug": "ceftriaxone", "drug_class": "beta_lactams"}],
    "requested_outputs": ["SIR"],
}


@pytest.fixture(autouse=True)
def _clear_model_caches():
    """本文件在 tests/ 根,不受 science_v2/conftest.py 的 autouse fixture 覆盖,自己清缓存。"""
    def _clear():
        for loader in (dr._load_test_sm_activity, dr._load_test_peptide_activity, dr._load_test_gsir):
            loader.cache_clear()

    _clear()
    yield
    _clear()


def test_models_root_is_absolute():
    """_MODELS_ROOT 必须是绝对路径(裸相对路径 = 按进程 CWD 解析 = 生产静默失效)。"""
    assert dr._MODELS_ROOT.is_absolute(), (
        f"_MODELS_ROOT={dr._MODELS_ROOT!r} 是相对路径,会按进程 CWD 解析"
    )
    assert dr._MODELS_ROOT == _REPO_ROOT / "data" / "mdr_gnb" / "models"


def test_species_gem_paths_are_absolute():
    """SPECIES_GEM 的值必须是绝对路径:任何消费者 .exists() 都不该依赖 CWD。"""
    assert SPECIES_GEM, "SPECIES_GEM 不该为空"
    for species, path in SPECIES_GEM.items():
        assert Path(path).is_absolute(), f"{species} 的 GEM 路径 {path!r} 是相对路径"


@pytest.mark.skipif(not _SIR_ARTIFACT.exists(), reason=f"需要真 SIR artifact({_SIR_ARTIFACT})")
def test_sir_trace_hash_identical_across_cwd(tmp_path, monkeypatch):
    """确定性红线:同一条 SIR 查询,仓库根 CWD 与非仓库根 CWD 的 trace_hash 必须逐字相等。"""
    from praxis_virtualcell.mdr_gnb.workflows.science_v2.validation import harness

    # 先跑非仓库根 CWD(生产 uvicorn 的真实情形:进程从头到尾就不在仓库根)
    monkeypatch.chdir(tmp_path)
    dr._load_test_gsir.cache_clear()
    hash_tmp = harness.trace_hash(_RAW_SIR)
    r_tmp = harness.run_query(_RAW_SIR)

    # 再跑仓库根 CWD;清缓存确保真的重新解析路径,而不是命中上一次的缓存
    monkeypatch.chdir(_REPO_ROOT)
    dr._load_test_gsir.cache_clear()
    hash_root = harness.trace_hash(_RAW_SIR)
    r_root = harness.run_query(_RAW_SIR)

    assert r_root["sir"] == "R", "前提失效:仓库根下这条查询本应出 R"
    assert r_tmp["sir"] == r_root["sir"], (
        f"CWD 一变 sir 就从 {r_root['sir']!r} 变成 {r_tmp['sir']!r}(artifact 按 CWD 解析)"
    )
    assert r_tmp["prediction_available"] == r_root["prediction_available"]
    assert hash_tmp == hash_root, "同输入不同 CWD 出了两个 trace_hash(确定性红线破了)"


@pytest.mark.skipif(not _SIR_ARTIFACT.exists(), reason=f"需要真 SIR artifact({_SIR_ARTIFACT})")
def test_no_silent_degradation_in_foreign_cwd(tmp_path, monkeypatch):
    """非仓库根 CWD 下若真丢了预测,至少必须诚实承认;不许 sir=None 还报 abstained=False。"""
    from praxis_virtualcell.mdr_gnb.workflows.science_v2.validation import harness

    monkeypatch.chdir(tmp_path)
    dr._load_test_gsir.cache_clear()
    r = harness.run_query(_RAW_SIR)

    if r["sir"] is None:  # 降级了就必须留痕(修复后本分支不该走到)
        assert r["abstained"] is True or r["abstain_reasons"], (
            "静默降级:sir=None 却 abstained=False 且 abstain_reasons=[],报告不承认降级"
        )
    assert r["sir"] == "R"


@pytest.mark.skipif(
    not (_HAS_COBRA and _GEM_ECOLI.exists()),
    reason="需要 cobra 与 iML1515;缺失时该路径由 abstain 分支覆盖",
)
def test_gem_fba_identical_across_cwd(tmp_path, monkeypatch):
    """GEM/FBA 机制层:非仓库根 CWD 下不得退化成「无可用 GEM」abstain。"""
    monkeypatch.chdir(tmp_path)
    r_tmp = GemFbaPredictor().predict(species="escherichia_coli", drug="trimethoprim")

    monkeypatch.chdir(_REPO_ROOT)
    r_root = GemFbaPredictor().predict(species="escherichia_coli", drug="trimethoprim")

    assert r_root.abstained is False, "前提失效:仓库根下 trimethoprim 本应真跑 FBA"
    assert r_tmp.abstained is False, f"CWD 一变 FBA 就 abstain:{r_tmp.abstain_reason}"
    assert r_tmp.growth_inhibition == r_root.growth_inhibition
    assert r_tmp.baseline_growth == r_root.baseline_growth
