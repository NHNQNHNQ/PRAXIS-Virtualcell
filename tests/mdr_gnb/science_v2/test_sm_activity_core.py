"""B1 gate:化合物活性(sm_activity)作为一等 predictor 插进核心,走通 run_mdr_query 全管线。

覆盖插入缝(每条对应设计蓝本 §一的一个"缝"):
  1. ensembler 加 sm_activity 聚合(log10-MIC 尺度均值 + 分歧),纯函数。
  2. router _OUTPUT_MAP 加 "activity"→sm_activity。
  3. report_builder 加 activity 字段(sm_activity 的预测 MIC 浮出)。
  4. SmallMoleculeModel(SMILES→log10-MIC,自带化学 OOD)真预测 + OOD 判据(需 rdkit)。
  5. default_registry 注册 sm_activity spec;predict 闭包 fail-closed(缺 artifact/缺 smiles/OOD→abstain)。
  6. run_mdr_query 端到端:化合物查询走通全管线,确定性(同 raw 逐字相等),OOD→abstain(需 rdkit)。

不依赖大 EC artifact / raw 数据:rdkit 相关用例现训微型模型到 tmp_path(仿 genotype 真加载测试)。
无 rdkit 环境(如 53)自动 skip;纯函数用例始终跑。
"""
import json

import pytest

from praxis_virtualcell.mdr_gnb.ensembler import MDRPredictorResult, aggregate
from tests.mdr_gnb.mic_invariant import assert_report_mic_matches_log10


def _r(name, kind, pred, status="success"):
    return MDRPredictorResult(agent_name=name, status=status, output_kind=kind,
                              prediction=pred, uncertainty={"sigma": 0.5},
                              evidence=[], provenance={"src": name})


# ---------------------------------------------------------------- 缝1:ensembler
def test_sm_activity_log10_mean():
    # log10-MIC 尺度均值:log10=0(1) 与 log10=2(100) → 均值 log10=1(mic=10)
    res = aggregate([_r("a", "sm_activity", {"log10_mic": 0.0}),
                     _r("b", "sm_activity", {"log10_mic": 2.0})])
    assert res.output_kind == "sm_activity"
    assert abs(res.ensemble["log10_mic"] - 1.0) < 1e-9
    assert abs(res.ensemble["mic_ug_ml"] - 10.0) < 1e-9
    assert res.disagreement["metric"] == "log10_range"
    assert abs(res.disagreement["log10_range"] - 2.0) < 1e-9


def test_sm_activity_single_model_no_disagreement():
    res = aggregate([_r("a", "sm_activity", {"log10_mic": 0.5})])
    assert abs(res.ensemble["log10_mic"] - 0.5) < 1e-9
    assert res.disagreement["log10_range"] == 0.0


# ---------------------------------------------------------------- 缝2:router
def test_router_output_map_activity():
    from praxis_virtualcell.mdr_gnb.coordinator.mdr_router import _OUTPUT_MAP
    assert _OUTPUT_MAP["activity"] == "sm_activity"


# ---------------------------------------------------------------- 缝3:report
def test_report_activity_field():
    from praxis_virtualcell.mdr_gnb.coordinator.report_builder import build_report
    rep = build_report(
        task_id="t", drug="cmp",
        ensemble_result={"output_kind": "sm_activity",
                         "ensemble": {"log10_mic": 1.0, "mic_ug_ml": 10.0}},
        abstain=False, abstain_reasons=[], downgrade_reasons=[], caution_flags=[],
        breakpoint_source="n/a", critic_violations=[], provenance={})
    assert rep["activity"] is not None
    assert abs(rep["activity"]["mic_ug_ml"] - 10.0) < 1e-6
    # abstain 时隐藏预测
    rep2 = build_report(
        task_id="t", drug="cmp",
        ensemble_result={"output_kind": "sm_activity",
                         "ensemble": {"log10_mic": 1.0, "mic_ug_ml": 10.0}},
        abstain=True, abstain_reasons=["x"], downgrade_reasons=[], caution_flags=[],
        breakpoint_source="n/a", critic_violations=[], provenance={})
    assert rep2["activity"] is None


# ---------------------------------------------------------------- rdkit 相关(缝4-6)
# 训练用微型多样化合物集(SMILES + 造一个可学信号:芳香环数 → log10-MIC)
_TRAIN_SMILES = [
    "c1ccccc1", "c1ccccc1C", "c1ccccc1CC", "c1ccc(cc1)O", "c1ccc(cc1)N",
    "c1ccc2ccccc2c1", "c1ccc2c(c1)cccc2C", "c1ccc(cc1)c1ccccc1",
    "CCO", "CCCO", "CCCCO", "CC(=O)O", "CCN", "CCCN", "CC(C)O", "CCCCCC",
]
# 造信号:含苯环(芳香)→ 低 MIC(log10=-1),脂肪链→高 MIC(log10=2);RF 应学到
_TRAIN_Y = [-1.0, -1.0, -0.8, -1.2, -0.9, -1.5, -1.4, -1.6,
            2.0, 2.1, 2.2, 1.8, 2.0, 2.1, 1.9, 2.3]


def _make_tiny_model(path):
    from praxis_virtualcell.mdr_gnb.predictors.small_molecule_model import SmallMoleculeModel
    m = SmallMoleculeModel(n_bits=512, radius=2, ood_threshold=0.3, n_estimators=50)
    m.fit(_TRAIN_SMILES, _TRAIN_Y)
    m.save(path)
    return m


def test_sm_model_predict_and_ood(tmp_path):
    pytest.importorskip("rdkit")
    p = tmp_path / "sm.joblib"
    m = _make_tiny_model(p)
    # in-distribution:训练里的芳香化合物 → 有效预测,max_tanimoto=1.0(自身在训练集)
    r = m.predict_one("c1ccccc1")
    assert r["ok"] is True
    assert r["max_tanimoto"] > 0.99          # 自身在训练集
    assert r["is_ood"] is False
    assert -3.0 < r["log10_mic"] < 3.0
    # OOD:甲烷(与药物样训练集极不相似)→ max_tanimoto 低,判 OOD
    r2 = m.predict_one("C")
    assert r2["max_tanimoto"] < 0.3
    assert r2["is_ood"] is True
    # invalid SMILES → ok False
    r3 = m.predict_one("这不是SMILES((((")
    assert r3["ok"] is False


def test_sm_model_mic_matches_log10(tmp_path):
    """predictor 自产的 mic_ug_ml 必须与自产的 log10_mic 自洽。

    为什么单元层要单独守(实测结论,非推理):ensembler 聚合时**不读** predictor 的
    mic_ug_ml,而是自己从 log10 重算(ensembler.py:102),trace 载荷也只带
    {"spec","status"}(run_mdr_query.py:141)——故这个字段**每条路径都死**,
    到不了用户,只守汇合点也抓不到它。它是本仓 6 处 MIC 生产者里唯一真逃逸的两处之一
    (改错 1000 倍曾 614 全绿穿过)。
    注:若将来落地「report_builder 从 log10 单一来源派生、predictor 不产 mic」,
    本守卫连同它守的那个死字段一起删除即可(是取代,不是叠加)。
    容差:单元层无舍入介入(predict_one 返回未舍入的 log10_mic 和 float(10.0**log10_mic)),
    同一 IEEE 运算 + 同一输入 → 确定性,故要求**逐位相等**,不留容差余地。
    (报告层因两数各自舍入到 4 位,须用 mic_invariant.report_mic_tolerance 的推导容差。)
    """
    pytest.importorskip("rdkit")
    m = _make_tiny_model(tmp_path / "sm.joblib")
    for smi in ("c1ccccc1", "c1ccccc1CC", "CCO"):
        r = m.predict_one(smi)
        assert r["ok"] is True
        assert r["mic_ug_ml"] == 10.0 ** r["log10_mic"], (
            f"{smi}: mic_ug_ml={r['mic_ug_ml']!r} != 10**log10_mic="
            f"{10.0 ** r['log10_mic']!r}")


def test_sm_model_save_load_roundtrip(tmp_path):
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.predictors.small_molecule_model import SmallMoleculeModel
    p = tmp_path / "sm.joblib"
    _make_tiny_model(p)
    m2 = SmallMoleculeModel.load(p)
    assert m2.train_size == len(_TRAIN_SMILES)
    a = m2.predict_one("c1ccccc1")["log10_mic"]
    b = SmallMoleculeModel.load(p).predict_one("c1ccccc1")["log10_mic"]
    assert a == b                            # 加载确定性


# ---------------------------------------------------------------- 缝5:default_registry 闭包
def test_sm_activity_predict_missing_artifact(tmp_path, monkeypatch):
    import praxis_virtualcell.mdr_gnb.predictors.default_registry as dr
    monkeypatch.setattr(dr, "_MODELS_ROOT", tmp_path)
    dr._load_test_sm_activity.cache_clear()
    # 缺 artifact → fail-closed abstain(诚实不伪造)
    r = dr._sm_activity_predict({"species": "escherichia_coli", "smiles": "c1ccccc1"})
    assert r["abstained"] is True
    assert r["output_kind"] == "sm_activity"


def test_sm_activity_predict_missing_smiles(tmp_path, monkeypatch):
    import praxis_virtualcell.mdr_gnb.predictors.default_registry as dr
    monkeypatch.setattr(dr, "_MODELS_ROOT", tmp_path)
    dr._load_test_sm_activity.cache_clear()
    r = dr._sm_activity_predict({"species": "escherichia_coli"})    # 无 smiles
    assert r["abstained"] is True


def test_sm_activity_registered_in_default():
    from praxis_virtualcell.mdr_gnb.predictors.default_registry import build_default_registry
    reg = build_default_registry()
    specs = reg.discover(species="escherichia_coli", drug_class="novel_compound",
                         output_kind="sm_activity")
    assert specs, "sm_activity 应注册进 default_registry(EC)"
    assert "smiles" in specs[0].requires


# ---------------------------------------------------------------- 缝6:run_mdr_query 端到端
def _compound_raw(smiles):
    return {"species": "escherichia_coli", "smiles": smiles,
            "drug_panel": [{"drug": "novel_compound_X", "drug_class": "novel_compound"}],
            "requested_outputs": ["activity"]}


def _wire_tiny_model(tmp_path, monkeypatch):
    import praxis_virtualcell.mdr_gnb.predictors.default_registry as dr
    monkeypatch.setattr(dr, "_MODELS_ROOT", tmp_path)
    dr._load_test_sm_activity.cache_clear()
    art = tmp_path / "escherichia_coli" / "sm_activity__mic.joblib"
    art.parent.mkdir(parents=True, exist_ok=True)
    _make_tiny_model(art)


def test_pipeline_compound_activity(tmp_path, monkeypatch):
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    _wire_tiny_model(tmp_path, monkeypatch)

    out = run_mdr_query(_compound_raw("c1ccccc1"), seed_task_id="c1")
    rep = out["report"]
    assert rep["output_kind"] == "sm_activity"
    assert rep["abstained"] is False
    assert rep["activity"] is not None
    assert rep["activity"]["mic_ug_ml"] > 0
    # >0 太弱(错 1000 倍照样 >0)。报告层是用户看到的汇合点:ensembler 算错不会被
    # report_builder 的 .get(fallback) 掩盖(fallback 只在 key 缺失时才触发,实测坐实),
    # 故这条断言同时守住 ensembler:102 与 report_builder:28 两处。
    assert_report_mic_matches_log10(rep["activity"], "mic_ug_ml")
    # sm_activity 走了 predictor → ensemble 链
    assert "predictor_result" in [m.message_type for m in out["trace"]]
    assert "ensemble_done" in [m.message_type for m in out["trace"]]


def test_pipeline_compound_determinism(tmp_path, monkeypatch):
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    _wire_tiny_model(tmp_path, monkeypatch)
    a = run_mdr_query(_compound_raw("c1ccccc1CC"), seed_task_id="cd")["report"]
    b = run_mdr_query(_compound_raw("c1ccccc1CC"), seed_task_id="cd")["report"]
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


def test_pipeline_compound_ood_abstains(tmp_path, monkeypatch):
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    _wire_tiny_model(tmp_path, monkeypatch)
    # 甲烷:化学空间外 → 报告应弃权,原因含 out_of_training_distribution
    out = run_mdr_query(_compound_raw("C"), seed_task_id="cood")
    rep = out["report"]
    assert rep["abstained"] is True
    assert any("training_distribution" in r for r in rep["abstain_reasons"])
    assert rep["activity"] is None            # 弃权隐藏预测


# ---- Spec-I1/I2:非 OOD 的 fail-closed 也须报告级诚实弃权(不返回"空但标称未弃权")----
def test_pipeline_invalid_smiles_abstains(tmp_path, monkeypatch):
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    _wire_tiny_model(tmp_path, monkeypatch)
    out = run_mdr_query(_compound_raw("这不是SMILES(((("), seed_task_id="cinv")
    rep = out["report"]
    assert rep["abstained"] is True                       # 不得空成功
    assert "compound_featurization_failed" in rep["abstain_reasons"]
    assert rep["activity"] is None


def test_pipeline_missing_smiles_abstains(tmp_path, monkeypatch):
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    _wire_tiny_model(tmp_path, monkeypatch)
    raw = {"species": "escherichia_coli",       # 无 smiles
           "drug_panel": [{"drug": "novel_compound_X", "drug_class": "novel_compound"}],
           "requested_outputs": ["activity"]}
    rep = run_mdr_query(raw, seed_task_id="cms")["report"]
    assert rep["abstained"] is True
    assert "compound_smiles_missing" in rep["abstain_reasons"]
    assert rep["activity"] is None


def test_pipeline_missing_artifact_abstains(tmp_path, monkeypatch):
    # 缺 artifact(未 wire 模型)→ 报告级诚实弃权,不空成功
    import praxis_virtualcell.mdr_gnb.predictors.default_registry as dr
    monkeypatch.setattr(dr, "_MODELS_ROOT", tmp_path)
    dr._load_test_sm_activity.cache_clear()
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    rep = run_mdr_query(_compound_raw("c1ccccc1"), seed_task_id="cna")["report"]
    assert rep["abstained"] is True
    assert "sm_activity_model_unavailable" in rep["abstain_reasons"]
    assert rep["activity"] is None


def test_pipeline_predict_crash_fail_closed(tmp_path, monkeypatch):
    # CG-I2:predict 时抛异常(如无 rdkit 环境 featurize 崩)→ 管线不崩,fail-closed 弃权
    pytest.importorskip("rdkit")
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    import praxis_virtualcell.mdr_gnb.predictors.small_molecule_model as smm
    _wire_tiny_model(tmp_path, monkeypatch)

    def _boom(*a, **k):
        raise ImportError("No module named 'rdkit'")   # 模拟 53 无 rdkit
    monkeypatch.setattr(smm, "morgan_bits", _boom)

    rep = run_mdr_query(_compound_raw("c1ccccc1"), seed_task_id="cboom")["report"]  # 不应抛
    assert rep["abstained"] is True
    # 泛化 fail-closed 码(活性类 predict 崩溃的兜底,B5 起 sm/peptide 共用)
    assert "activity_prediction_failed" in rep["abstain_reasons"]
    assert rep["activity"] is None


def test_sm_activity_predict_reason_codes(tmp_path, monkeypatch):
    # 强化:闭包对四种失败返回明确 reason_code(诚实机器码,供报告级弃权)
    import praxis_virtualcell.mdr_gnb.predictors.default_registry as dr
    monkeypatch.setattr(dr, "_MODELS_ROOT", tmp_path)
    dr._load_test_sm_activity.cache_clear()
    assert dr._sm_activity_predict({"species": "escherichia_coli"})["reason_code"] \
        == "compound_smiles_missing"
    assert dr._sm_activity_predict(
        {"species": "escherichia_coli", "smiles": "c1ccccc1"})["reason_code"] \
        == "sm_activity_model_unavailable"
