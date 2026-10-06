"""B4 gate:化合物活性(QSAR)+ 虚拟细胞机制(GEM/FBA)同 report 分栏融合。

红线:
  1. 活性≠机制:report 里 activity(QSAR MIC)与 mechanism(FBA growth 抑制)分栏,互不冒充。
  2. 机制只在 G3 门后声称:FBA 结果照实报(可证伪模拟),但"已验证机制解释"仅 G3 passed 才声称;
     未评估/未过 → claim_allowed=False,标"候选未验证"。
  3. FBA 真跑或诚实 abstain:非代谢靶/cobra 缺/GEM 缺 → mechanism unavailable,绝不伪造通量。
  4. 确定性:FBA 输出四舍五入,报告逐字相等。

大部分用例用注入的假 predictor/g3(不真跑 cobra,确定);真 FBA 用例 importorskip cobra + GEM 存在才跑。
"""
import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------- fuse_mechanism 单元
class _FakeFbaResult:
    def __init__(self, abstained, reason=None, gi=None, base=None, cons=None,
                 mech=None, blocked=None):
        self.abstained = abstained
        self.abstain_reason = reason
        self.growth_inhibition = gi
        self.baseline_growth = base
        self.constrained_growth = cons
        self.mechanism = mech
        self.evidence = [{"kind": "fba", "reactions_blocked": blocked or [],
                          "reactions_missing": []}] if not abstained else []


class _FakePredictor:
    def __init__(self, result):
        self._r = result

    def predict(self, *, species, drug):
        return self._r


def test_fuse_mechanism_fba_success_g3_not_evaluated():
    from praxis_virtualcell.mdr_gnb.coordinator.mechanism_fusion import fuse_mechanism
    pred = _FakePredictor(_FakeFbaResult(
        abstained=False, gi=1.0, base=0.877, cons=0.0,
        mech="抑制 DHFR", blocked=["DHFR"]))
    m = fuse_mechanism("escherichia_coli", "trimethoprim", predictor=pred,
                       g3_status_fn=lambda s, d: "not_evaluated")
    assert m["available"] is True
    assert m["engine"] == "gem_fba"
    # FBA 模拟结果照实报
    assert m["fba_simulation"]["growth_inhibition"] == 1.0
    assert m["fba_simulation"]["reactions_blocked"] == ["DHFR"]
    # G3 未评估 → 不声称已验证机制
    assert m["g3_gate"]["status"] == "not_evaluated"
    assert m["g3_gate"]["claim_allowed"] is False
    assert m["mechanism_claim"] is None            # 红线:G3 未过不声称
    assert "候选" in m["disclaimer"] or "未验证" in m["disclaimer"]


def test_fuse_mechanism_g3_passed_allows_claim():
    from praxis_virtualcell.mdr_gnb.coordinator.mechanism_fusion import fuse_mechanism
    pred = _FakePredictor(_FakeFbaResult(
        abstained=False, gi=0.8, base=0.9, cons=0.18, mech="抑制 DHPS2", blocked=["DHPS2"]))
    m = fuse_mechanism("escherichia_coli", "sulfamethoxazole", predictor=pred,
                       g3_status_fn=lambda s, d: "passed")
    assert m["g3_gate"]["status"] == "passed"
    assert m["g3_gate"]["claim_allowed"] is True
    assert m["mechanism_claim"] is not None         # G3 过 → 可声称机制解释


def test_fuse_mechanism_non_metabolic_unavailable():
    from praxis_virtualcell.mdr_gnb.coordinator.mechanism_fusion import fuse_mechanism
    pred = _FakePredictor(_FakeFbaResult(abstained=True, reason="非代谢靶抗生素,FBA 不适用"))
    m = fuse_mechanism("escherichia_coli", "some_novel_compound", predictor=pred,
                       g3_status_fn=lambda s, d: "not_evaluated")
    assert m["available"] is False
    assert "fba_simulation" not in m or m.get("fba_simulation") is None   # 不伪造通量
    assert m["mechanism_claim"] is None


def test_fuse_mechanism_rounds_for_determinism():
    from praxis_virtualcell.mdr_gnb.coordinator.mechanism_fusion import fuse_mechanism
    pred = _FakePredictor(_FakeFbaResult(
        abstained=False, gi=0.9999999999999688, base=0.8771234567, cons=1e-14,
        mech="抑制 DHFR", blocked=["DHFR"]))
    m = fuse_mechanism("escherichia_coli", "trimethoprim", predictor=pred,
                       g3_status_fn=lambda s, d: "not_evaluated")
    # 四舍五入到 4 位 → 逐字确定
    assert m["fba_simulation"]["growth_inhibition"] == 1.0
    assert m["fba_simulation"]["baseline_growth"] == 0.8771


# ---------------------------------------------------------------- 接进 run_mdr_query(分栏)
_TRAIN_SMILES = [
    "c1ccccc1", "c1ccccc1C", "c1ccccc1CC", "c1ccc(cc1)O", "c1ccc(cc1)N",
    "c1ccc2ccccc2c1", "c1ccc2c(c1)cccc2C", "c1ccc(cc1)c1ccccc1",
    "CCO", "CCCO", "CCCCO", "CC(=O)O", "CCN", "CCCN", "CC(C)O", "CCCCCC",
]
_TRAIN_Y = [-1.0, -1.0, -0.8, -1.2, -0.9, -1.5, -1.4, -1.6,
            2.0, 2.1, 2.2, 1.8, 2.0, 2.1, 1.9, 2.3]


def _wire_tiny_model(tmp_path, monkeypatch):
    from praxis_virtualcell.mdr_gnb.predictors.small_molecule_model import SmallMoleculeModel
    import praxis_virtualcell.mdr_gnb.predictors.default_registry as dr
    monkeypatch.setattr(dr, "_MODELS_ROOT", tmp_path)
    dr._load_test_sm_activity.cache_clear()
    art = tmp_path / "escherichia_coli" / "sm_activity__mic.joblib"
    art.parent.mkdir(parents=True, exist_ok=True)
    m = SmallMoleculeModel(n_bits=512, radius=2, ood_threshold=0.3, n_estimators=50)
    m.fit(_TRAIN_SMILES, _TRAIN_Y)
    m.save(art)


def _fake_mech(species, drug):
    # 注入的机制融合器:trimethoprim 出 FBA,其余 unavailable(不真跑 cobra)
    if drug == "trimethoprim":
        return {"available": True, "engine": "gem_fba",
                "fba_simulation": {"growth_inhibition": 1.0, "baseline_growth": 0.877,
                                   "constrained_growth": 0.0, "reactions_blocked": ["DHFR"],
                                   "note": "FBA 模拟"},
                "g3_gate": {"status": "not_evaluated", "claim_allowed": False},
                "mechanism_claim": None, "disclaimer": "候选机制,G3 未验证"}
    return {"available": False, "reason": "非代谢靶", "engine": "gem_fba",
            "mechanism_claim": None}


def _compound_raw(smiles, drug):
    return {"species": "escherichia_coli", "smiles": smiles,
            "drug_panel": [{"drug": drug, "drug_class": "novel_compound"}],
            "requested_outputs": ["activity", "mechanism"]}


def test_pipeline_fuses_activity_and_mechanism_separate(tmp_path, monkeypatch):
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    _wire_tiny_model(tmp_path, monkeypatch)
    rep = run_mdr_query(_compound_raw("c1ccccc1", "trimethoprim"), seed_task_id="f1",
                        fuse_mech=_fake_mech)["report"]
    # 活性与机制分栏,互不冒充
    assert rep["activity"] is not None and "mic_ug_ml" in rep["activity"]
    assert rep["mechanism"] is not None and rep["mechanism"]["available"] is True
    assert "growth_inhibition" in rep["mechanism"]["fba_simulation"]
    # 活性字段里没有机制字段,机制字段里没有 MIC(不互相冒充)
    assert "growth_inhibition" not in rep["activity"]
    assert "mic_ug_ml" not in rep["mechanism"].get("fba_simulation", {})
    # G3 未过 → 机制不作已验证声称
    assert rep["mechanism"]["mechanism_claim"] is None


def test_pipeline_mechanism_unavailable_for_non_metabolic(tmp_path, monkeypatch):
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    _wire_tiny_model(tmp_path, monkeypatch)
    rep = run_mdr_query(_compound_raw("c1ccccc1", "novel_x"), seed_task_id="f2",
                        fuse_mech=_fake_mech)["report"]
    assert rep["activity"] is not None                # 活性照出
    assert rep["mechanism"]["available"] is False      # 机制诚实 unavailable
    assert rep["activity"] is not None and rep["mechanism"].get("mechanism_claim") is None


def test_pipeline_sir_query_no_mechanism_field(tmp_path, monkeypatch):
    # 既有 SIR 查询不受影响:非化合物查询不加 mechanism(零污染)
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    raw = {"species": "escherichia_coli", "amr_profile": {"blaKPC-2": True},
           "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenems"}],
           "requested_outputs": ["SIR"]}
    rep = run_mdr_query(raw, seed_task_id="f3")["report"]
    assert rep.get("mechanism") is None               # SIR 查询无 mechanism 段


# ---------------------------------------------------------------- critic 兜底红线
def test_critic_catches_mechanism_claim_without_g3(tmp_path, monkeypatch):
    # 红线兜底:若融合回归(声称机制却未过 G3),critic 不变量#7 须抓到 mechanism_claim_without_g3
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    _wire_tiny_model(tmp_path, monkeypatch)

    def _bad_mech(species, drug):     # 畸形:声称机制但 G3 未过(模拟融合逻辑回归)
        return {"available": True, "engine": "gem_fba",
                "fba_simulation": {"growth_inhibition": 1.0, "baseline_growth": 0.9,
                                   "constrained_growth": 0.0, "reactions_blocked": ["DHFR"]},
                "g3_gate": {"status": "not_evaluated", "claim_allowed": False},
                "mechanism_claim": "抑制 DHFR(越权声称)", "disclaimer": "x"}
    rep = run_mdr_query(_compound_raw("c1ccccc1", "trimethoprim"), seed_task_id="cbad",
                        fuse_mech=_bad_mech)["report"]
    assert "mechanism_claim_without_g3" in rep["critic_violations"]


def test_critic_ok_when_g3_passed(tmp_path, monkeypatch):
    # G3 过 + 声称机制 → 无违规(合规声称)
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    _wire_tiny_model(tmp_path, monkeypatch)

    def _ok_mech(species, drug):
        return {"available": True, "engine": "gem_fba",
                "fba_simulation": {"growth_inhibition": 1.0, "baseline_growth": 0.9,
                                   "constrained_growth": 0.0, "reactions_blocked": ["DHFR"]},
                "g3_gate": {"status": "passed", "claim_allowed": True},
                "mechanism_claim": "抑制 DHFR(G3 已验证)", "disclaimer": "x"}
    rep = run_mdr_query(_compound_raw("c1ccccc1", "trimethoprim"), seed_task_id="cok",
                        fuse_mech=_ok_mech)["report"]
    assert "mechanism_claim_without_g3" not in rep["critic_violations"]


def test_pipeline_abstained_compound_no_mechanism(tmp_path, monkeypatch):
    # 弃权的化合物查询不跑机制融合(OOD→abstain 时 mechanism=None,省 GEM 载入)
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    _wire_tiny_model(tmp_path, monkeypatch)

    def _should_not_call(species, drug):
        raise AssertionError("弃权查询不应跑机制融合")
    # 甲烷 → 化学 OOD → abstain
    rep = run_mdr_query(_compound_raw("C", "trimethoprim"), seed_task_id="cab",
                        fuse_mech=_should_not_call)["report"]
    assert rep["abstained"] is True
    assert rep.get("mechanism") is None


# ---------------------------------------------------------------- 真 FBA(cobra 存在才跑)
def test_real_fba_trimethoprim_deterministic():
    pytest.importorskip("cobra")
    if not Path("data/mdr_gnb/gems/iML1515.xml.gz").exists():
        pytest.skip("iML1515 GEM 不在盘")
    from praxis_virtualcell.mdr_gnb.coordinator.mechanism_fusion import fuse_mechanism
    a = fuse_mechanism("escherichia_coli", "trimethoprim")
    b = fuse_mechanism("escherichia_coli", "trimethoprim")
    assert a["available"] is True
    assert a["fba_simulation"]["reactions_blocked"] == ["DHFR"]
    assert 0.0 <= a["fba_simulation"]["growth_inhibition"] <= 1.0
    # 四舍五入后逐字相等(cobra LP ULP 噪声被吸收)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
