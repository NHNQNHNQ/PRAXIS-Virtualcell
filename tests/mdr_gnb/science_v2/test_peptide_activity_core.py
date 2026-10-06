"""B5-肽注册 gate:peptide_activity 作一等 predictor 插进核心,走通 run_mdr_query 全管线。

逐缝仿 B1 sm_activity(test_sm_activity_core):
  1. ensembler 加 peptide_activity 聚合(log10 均值 + 不确定度/OOD 浮出)。
  2. router _OUTPUT_MAP 加 "peptide_activity"→peptide_activity。
  3. report_builder 加 peptide_activity 报告字段。
  4. PeptideActivityModel 真预测 + 序列 OOD(需 sklearn,不需 rdkit)。
  5. default_registry 注册 peptide_activity spec + fail-closed 闭包(缺 sequence/缺 artifact/invalid/OOD)。
  6. run_mdr_query 端到端:肽查询走通全管线,确定性,OOD→abstain,非 OOD fail-closed 报告级弃权。
"""
import json

from praxis_virtualcell.mdr_gnb.ensembler import MDRPredictorResult, aggregate
from tests.mdr_gnb.mic_invariant import assert_report_mic_matches_log10


def _r(name, kind, pred, status="success"):
    return MDRPredictorResult(agent_name=name, status=status, output_kind=kind,
                              prediction=pred, uncertainty={"sigma": 0.5},
                              evidence=[], provenance={"src": name})


# ---------------------------------------------------------------- 缝1:ensembler
def test_peptide_activity_log10_mean():
    res = aggregate([_r("a", "peptide_activity", {"log10_mic": 0.0, "max_jaccard": 0.8, "is_ood": False}),
                     _r("b", "peptide_activity", {"log10_mic": 2.0, "max_jaccard": 0.6, "is_ood": False})])
    assert res.output_kind == "peptide_activity"
    assert abs(res.ensemble["log10_mic"] - 1.0) < 1e-9
    assert abs(res.ensemble["mic_um"] - 10.0) < 1e-9
    assert res.ensemble["max_jaccard"] == 0.6           # 取最保守(min)
    assert res.disagreement["metric"] == "log10_range"


# ---------------------------------------------------------------- 缝2:router
def test_router_output_map_peptide_activity():
    from praxis_virtualcell.mdr_gnb.coordinator.mdr_router import _OUTPUT_MAP
    assert _OUTPUT_MAP["peptide_activity"] == "peptide_activity"


# ---------------------------------------------------------------- 缝3:report
def test_report_peptide_activity_field():
    from praxis_virtualcell.mdr_gnb.coordinator.report_builder import build_report
    rep = build_report(
        task_id="t", drug="pep",
        ensemble_result={"output_kind": "peptide_activity",
                         "ensemble": {"log10_mic": 1.0, "mic_um": 10.0,
                                      "uncertainty_std": 0.3, "max_jaccard": 0.7, "is_ood": False}},
        abstain=False, abstain_reasons=[], downgrade_reasons=[], caution_flags=[],
        breakpoint_source="n/a", critic_violations=[], provenance={})
    assert rep["peptide_activity"] is not None
    assert abs(rep["peptide_activity"]["mic_um"] - 10.0) < 1e-6
    assert "max_jaccard" in rep["peptide_activity"]
    rep2 = build_report(
        task_id="t", drug="pep",
        ensemble_result={"output_kind": "peptide_activity",
                         "ensemble": {"log10_mic": 1.0, "mic_um": 10.0}},
        abstain=True, abstain_reasons=["x"], downgrade_reasons=[], caution_flags=[],
        breakpoint_source="n/a", critic_violations=[], provenance={})
    assert rep2["peptide_activity"] is None             # abstain 隐藏预测


# ---------------------------------------------------------------- 缝4:PeptideActivityModel
_TRAIN_SEQS = [
    "KKKKLLLLKKKK", "KKKLLLLKKKKA", "RRRRWWWWLLLL", "RRRWWWWLLLLA",
    "DDEEAAAAGGGG", "DDEEAAAGGGGA", "LLIIVVAAAALL", "LLIIVVAAALLA",
    "GLFDIVKKVVGA", "GLFDIVKKVVGL", "ALWKTLLKKVLK", "ALWKTLLKKVLA",
    "FLPIIAKLLGKL", "FLPIIAKLLGKA", "GIGKFLHSAKKF", "GIGKFLHSAKKA",
]
_TRAIN_Y = [0.5, 0.6, 0.4, 0.5, 2.0, 2.1, 1.8, 1.9, 0.8, 0.9, 0.3, 0.4, 0.7, 0.8, 0.6, 0.7]


def _make_tiny_model(path):
    from praxis_virtualcell.mdr_gnb.predictors.peptide_activity_model import PeptideActivityModel
    m = PeptideActivityModel(ood_threshold=0.3, n_estimators=50)
    m.fit(_TRAIN_SEQS, _TRAIN_Y)
    m.save(path)
    return m


def test_peptide_model_predict_and_ood(tmp_path):
    p = tmp_path / "pep.joblib"
    m = _make_tiny_model(p)
    r = m.predict_one("KKKKLLLLKKKK")                   # 训练里的序列 → 高 Jaccard,非 OOD
    assert r["ok"] is True
    assert r["max_jaccard"] > 0.99
    assert r["is_ood"] is False
    r2 = m.predict_one("PPPPPPPPPPPP")                  # 与训练集极不同 → 低 Jaccard,OOD
    assert r2["max_jaccard"] < 0.3
    assert r2["is_ood"] is True
    r3 = m.predict_one("XZ123")                         # 非标准 AA → invalid
    assert r3["ok"] is False


def test_peptide_model_mic_matches_log10(tmp_path):
    """predictor 自产的 mic_um 必须与自产的 log10_mic 自洽(仿 sm 侧同名守卫)。

    同 sm:ensembler 不读 predictor 的 mic_um,自己从 log10 重算(ensembler.py:120),
    trace 载荷也不带 prediction → 该字段每条路径都死、到不了用户,只守汇合点抓不到,
    必须单元层守(改错 1000 倍曾 614 全绿穿过)。单元层无舍入 → 要求逐位相等。
    注:同 sm 侧,「单一来源派生」落地后本守卫随死字段一并删除即可。
    """
    m = _make_tiny_model(tmp_path / "pep.joblib")
    for seq in ("KKKKLLLLKKKK", "RRRRWWWWLLLL", "DDEEAAAAGGGG"):
        r = m.predict_one(seq)
        assert r["ok"] is True
        assert r["mic_um"] == 10.0 ** r["log10_mic"], (
            f"{seq}: mic_um={r['mic_um']!r} != 10**log10_mic={10.0 ** r['log10_mic']!r}")


def test_peptide_model_load_deterministic(tmp_path):
    from praxis_virtualcell.mdr_gnb.predictors.peptide_activity_model import PeptideActivityModel
    p = tmp_path / "pep.joblib"
    _make_tiny_model(p)
    a = PeptideActivityModel.load(p).predict_one("KKKKLLLLKKKK")["log10_mic"]
    b = PeptideActivityModel.load(p).predict_one("KKKKLLLLKKKK")["log10_mic"]
    assert a == b


# ---------------------------------------------------------------- 缝5:default_registry 闭包
def test_peptide_activity_predict_missing_artifact(tmp_path, monkeypatch):
    import praxis_virtualcell.mdr_gnb.predictors.default_registry as dr
    monkeypatch.setattr(dr, "_MODELS_ROOT", tmp_path)
    dr._load_test_peptide_activity.cache_clear()
    r = dr._peptide_activity_predict({"species": "escherichia_coli", "sequence": "KKKKLLLL"})
    assert r["abstained"] is True
    assert r["output_kind"] == "peptide_activity"


def test_peptide_activity_predict_missing_sequence(tmp_path, monkeypatch):
    import praxis_virtualcell.mdr_gnb.predictors.default_registry as dr
    monkeypatch.setattr(dr, "_MODELS_ROOT", tmp_path)
    dr._load_test_peptide_activity.cache_clear()
    r = dr._peptide_activity_predict({"species": "escherichia_coli"})
    assert r["abstained"] is True
    assert r["reason_code"] == "peptide_sequence_missing"


def test_peptide_activity_registered():
    from praxis_virtualcell.mdr_gnb.predictors.default_registry import build_default_registry
    reg = build_default_registry()
    specs = reg.discover(species="escherichia_coli", drug_class="antimicrobial_peptide",
                         output_kind="peptide_activity")
    assert specs
    assert "sequence" in specs[0].requires


# ---------------------------------------------------------------- 缝6:run_mdr_query 端到端
def _pep_raw(sequence):
    return {"species": "escherichia_coli", "sequence": sequence,
            "drug_panel": [{"drug": "novel_peptide", "drug_class": "antimicrobial_peptide"}],
            "requested_outputs": ["peptide_activity"]}


def _wire(tmp_path, monkeypatch):
    import praxis_virtualcell.mdr_gnb.predictors.default_registry as dr
    monkeypatch.setattr(dr, "_MODELS_ROOT", tmp_path)
    dr._load_test_peptide_activity.cache_clear()
    art = tmp_path / "escherichia_coli" / "peptide_activity__mic.joblib"
    art.parent.mkdir(parents=True, exist_ok=True)
    _make_tiny_model(art)


def test_pipeline_peptide_activity(tmp_path, monkeypatch):
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    _wire(tmp_path, monkeypatch)
    rep = run_mdr_query(_pep_raw("KKKKLLLLKKKK"), seed_task_id="p1")["report"]
    assert rep["output_kind"] == "peptide_activity"
    assert rep["abstained"] is False
    assert rep["peptide_activity"] is not None
    assert rep["peptide_activity"]["mic_um"] > 0
    # >0 太弱(错 1000 倍照样 >0);同守 ensembler:120 与 report_builder:45
    assert_report_mic_matches_log10(rep["peptide_activity"], "mic_um")


def test_pipeline_peptide_determinism(tmp_path, monkeypatch):
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    _wire(tmp_path, monkeypatch)
    a = run_mdr_query(_pep_raw("RRRRWWWWLLLL"), seed_task_id="pd")["report"]
    b = run_mdr_query(_pep_raw("RRRRWWWWLLLL"), seed_task_id="pd")["report"]
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


def test_pipeline_peptide_ood_abstains(tmp_path, monkeypatch):
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    _wire(tmp_path, monkeypatch)
    rep = run_mdr_query(_pep_raw("PPPPPPPPPPPP"), seed_task_id="poo")["report"]
    assert rep["abstained"] is True
    assert any("training_distribution" in r for r in rep["abstain_reasons"])
    assert rep["peptide_activity"] is None


def test_pipeline_peptide_invalid_abstains(tmp_path, monkeypatch):
    from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query
    _wire(tmp_path, monkeypatch)
    rep = run_mdr_query(_pep_raw("XZ123"), seed_task_id="pinv")["report"]
    assert rep["abstained"] is True
    assert "peptide_featurization_failed" in rep["abstain_reasons"]
    assert rep["peptide_activity"] is None
