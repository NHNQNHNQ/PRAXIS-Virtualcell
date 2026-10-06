"""共享 harness 单测:确定性 + 指标正确 + golden schema 校验 + 边界/写报告覆盖。"""


import pytest


from praxis_virtualcell.mdr_gnb.workflows.science_v2.validation import harness


KP_MERO = {"species": "klebsiella_pneumoniae",
           "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenem"}],
           "requested_outputs": ["SIR"], "amr_profile": {"blaKPC-2": True}}


def test_classification_metrics_basic():
    m = harness.classification_metrics(
        y_true=["R", "S", "R"], y_pred=["R", "S", None], abstained=[False, False, True])
    assert m["coverage"] == pytest.approx(2 / 3)
    assert m["accuracy"] == pytest.approx(1.0)
    assert m["very_major_error"] == pytest.approx(0.0)
    assert m["major_error"] == pytest.approx(0.0)
    # 暴露分母:covered 里 R=1(第0条)、S=1(第1条)
    assert m["n_R"] == 1
    assert m["n_S"] == 1


def test_classification_metrics_empty():
    m = harness.classification_metrics(y_true=[], y_pred=[], abstained=[])
    assert m["n"] == 0
    assert m["coverage"] == 0.0
    assert m["accuracy"] == 0.0
    assert m["n_R"] == 0
    assert m["n_S"] == 0


def test_classification_metrics_all_abstained():
    # 全弃权 → coverage=0,accuracy 兜底 0.0,分母也 0
    m = harness.classification_metrics(
        y_true=["R", "S"], y_pred=["R", "S"], abstained=[True, True])
    assert m["coverage"] == 0.0
    assert m["accuracy"] == 0.0
    assert m["n_R"] == 0
    assert m["n_S"] == 0


def test_classification_metrics_no_R_samples():
    # 只有 S 样本:n_R=0 → vme 兜底 0.0,但 n_R=0 能让调用方分清"没 R 样本"
    m = harness.classification_metrics(
        y_true=["S", "S"], y_pred=["S", "R"], abstained=None)
    assert m["n_R"] == 0
    assert m["n_S"] == 2
    assert m["very_major_error"] == pytest.approx(0.0)
    assert m["major_error"] == pytest.approx(0.5)  # 第1条预测R实际S


def test_regression_metrics_basic():
    m = harness.regression_metrics(y_true=[1.0, 2.0, 3.0], y_pred=[1.0, 2.0, 3.0])
    assert m["mae"] == pytest.approx(0.0)
    assert m["r2"] == pytest.approx(1.0)
    assert m["coverage"] == pytest.approx(1.0)
    assert m["n_scored"] == 3


def test_regression_metrics_filters_abstain_and_none():
    # 弃权 + None 样本都要滤掉,只对 covered(第0、1条)算
    m = harness.regression_metrics(
        y_true=[1.0, 2.0, 3.0, 4.0],
        y_pred=[1.0, 2.0, None, 99.0],
        abstained=[False, False, False, True])
    assert m["n"] == 4
    assert m["n_scored"] == 2
    assert m["coverage"] == pytest.approx(0.5)
    assert m["mae"] == pytest.approx(0.0)
    assert m["r2"] == pytest.approx(1.0)


def test_regression_metrics_no_scored_returns_none():
    # 全弃权 → 无可评样本,mae/rmse/r2 均 None(保证 JSON 恒标准)
    m = harness.regression_metrics(
        y_true=[1.0, 2.0], y_pred=[1.0, 2.0], abstained=[True, True])
    assert m["n_scored"] == 0
    assert m["coverage"] == 0.0
    assert m["mae"] is None
    assert m["rmse"] is None
    assert m["r2"] is None


def test_regression_metrics_zero_variance_r2_none():
    # y_true 全相等 → ss_tot=0 → r2 无定义,返回 None(不是 nan)
    m = harness.regression_metrics(y_true=[2.0, 2.0, 2.0], y_pred=[2.0, 2.1, 1.9])
    assert m["r2"] is None
    assert m["mae"] is not None  # mae 仍可算


def test_load_golden_rejects_missing_columns(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("name,smiles\nfoo,CCO\n", encoding="utf-8")
    with pytest.raises(ValueError):
        harness.load_golden(bad, required=["name", "smiles", "mic_ug_ml", "label_source"])


def test_write_report_deterministic(tmp_path, monkeypatch):
    # 把 _REPORT_ROOT 指到 tmp_path,别污染真 reports 目录
    monkeypatch.setattr(harness, "_REPORT_ROOT", tmp_path)
    payload = {"b": 2, "a": 1, "nested": {"z": [3, 2, 1]}}
    p1 = harness.write_report("t0_det", payload)
    b1 = p1.read_bytes()
    p2 = harness.write_report("t0_det", payload)
    b2 = p2.read_bytes()
    assert p1 == p2
    assert b1 == b2  # 同 payload 写两次字节逐字相等
