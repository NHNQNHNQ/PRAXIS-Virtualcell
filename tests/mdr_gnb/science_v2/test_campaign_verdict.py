"""Campaign verdict rules on synthetic evidence; no dataset or model execution."""
from __future__ import annotations

import pytest
from praxis_virtualcell.mdr_gnb.workflows.science_v2.validation import run_campaign

def _mk_layers(
    gate_overrides: dict[str, dict[str, bool]] | None = None,
    findings_by_layer: dict[str, list[dict]] | None = None,
) -> dict[str, dict]:
    """造合成 layers(默认全绿),pass 由 gates 推导(与实现同口径,不手写 pass)。"""
    gate_overrides = gate_overrides or {}
    findings_by_layer = findings_by_layer or {}
    layers = {}
    for k in run_campaign.LAYER_KEYS:
        gates = gate_overrides.get(k, {"ok": True})
        layers[k] = {
            "layer": k,
            "hard_red_line": k in run_campaign.HARD_RED_LINE_LAYERS,
            "gates": gates,
            "pass": all(gates.values()),
            "findings": findings_by_layer.get(k, []),
        }
    return layers


def _flatten_findings(layers: dict[str, dict]) -> list[dict]:
    return [{"layer": k, **f} for k in run_campaign.LAYER_KEYS for f in layers[k]["findings"]]


def test_compute_verdict_all_green() -> None:
    """全绿:两条读数都 True,无 red_flags。"""
    layers = _mk_layers()
    v = run_campaign.compute_verdict(layers, _flatten_findings(layers))
    assert v["campaign_pass"] is True
    assert v["all_gates_pass"] is True
    assert v["red_flags"] == []


def test_soft_gate_fail_does_not_blacken_campaign_pass() -> None:
    """**两条读数的定义差异**:T1 软门槛失败 → campaign_pass 仍 True,all_gates_pass False。

    这是本战役真实处境的镜像(T1A 轨B VME 未达门槛),也是唯一能证明两条读数**不是同一个东西**
    的组合。若实现把 all_gates_pass 写成 campaign_pass 的别名,本测试即红。
    """
    layers = _mk_layers(gate_overrides={"t1a": {"gen.vme_le_0.10": False, "gen.auc_ge_0.85": True}})
    v = run_campaign.compute_verdict(layers, _flatten_findings(layers))
    assert v["campaign_pass"] is True, "T1 是软指标,不得拉黑硬红线语义的 campaign_pass"
    assert v["all_gates_pass"] is False, "含软门槛的读数必须反映 T1 门槛失败"
    assert v["red_flags"] == [], "软门槛失败不是红旗(如实记为科学发现,不是红线事故)"


@pytest.mark.parametrize("hard_layer", run_campaign.HARD_RED_LINE_LAYERS)
def test_hard_red_line_layer_fail_blackens_campaign_pass(hard_layer: str) -> None:
    """任一硬红线层失败 → campaign_pass=False 且该层列入 red_flags(逐层参数化,无遗漏)。"""
    layers = _mk_layers(gate_overrides={hard_layer: {"some_gate": False}})
    v = run_campaign.compute_verdict(layers, _flatten_findings(layers))
    assert v["campaign_pass"] is False
    assert v["all_gates_pass"] is False
    flags = [f for f in v["red_flags"] if f["layer"] == hard_layer]
    assert len(flags) == 1
    assert flags[0]["kind"] == "hard_red_line_layer_fail"
    assert flags[0]["failed_gates"] == ["some_gate"]


def test_red_line_finding_blackens_even_when_all_layers_pass() -> None:
    """red_line severity 的 finding 单独即可拉黑两条读数(规则2),即便所有层 gates 全绿。"""
    layers = _mk_layers(findings_by_layer={
        "t5": [{"id": "ood_gap_long_homopolymer", "severity": "red_line", "summary": "x"}],
    })
    v = run_campaign.compute_verdict(layers, _flatten_findings(layers))
    assert v["campaign_pass"] is False
    assert v["all_gates_pass"] is False
    flags = [f for f in v["red_flags"] if f["kind"] == "red_line_finding"]
    assert [f["id"] for f in flags] == ["ood_gap_long_homopolymer"]
    assert flags[0]["layer"] == "t5"


def test_non_red_line_finding_does_not_blacken() -> None:
    """severity=important 的 finding 不拉黑(证明规则是按 severity 过滤,不是"有 finding 就红")。"""
    layers = _mk_layers(findings_by_layer={
        "t7": [{"id": "task_id_mismatch", "severity": "important", "detail": "x"}],
    })
    v = run_campaign.compute_verdict(layers, _flatten_findings(layers))
    assert v["campaign_pass"] is True
    assert v["all_gates_pass"] is True
    assert v["red_flags"] == []


def test_compute_verdict_missing_hard_layer_raises() -> None:
    """硬红线层缺失必须炸(而非被 all() 当空集判 True)——防"漏跑一层反而全绿"。"""
    layers = _mk_layers()
    del layers["t6"]
    with pytest.raises(KeyError):
        run_campaign.compute_verdict(layers, [])


def test_empty_gates_layer_raises() -> None:
    """层的 gates 为空必须炸:all({}) 恒 True,空 gates 会造出**假绿**。"""
    layers = _mk_layers(gate_overrides={"t3": {}})
    with pytest.raises(ValueError, match="gates"):
        run_campaign.compute_verdict(layers, [])
