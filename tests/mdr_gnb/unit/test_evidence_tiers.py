"""证据面 sweep 后处理:no_baseline 重分类。"""
from praxis_virtualcell.mdr_gnb.workflows.write_evidence_tiers import reclassify


def test_reclassify_no_baseline():
    rs = [
        {"tier": "error", "error": "规则基线未收录药物 'foo'"},
        {"tier": "error", "error": "KeyError: bar"},
        {"tier": "error", "error": "some other crash"},
        {"tier": "strong", "delta_vme": -0.1},
    ]
    out = reclassify(rs)
    assert out[0]["tier"] == "no_baseline"     # 未收录 → no_baseline
    assert out[1]["tier"] == "no_baseline"     # KeyError → no_baseline
    assert out[2]["tier"] == "error"           # 真崩溃 → 仍 error
    assert out[3]["tier"] == "strong"          # 不动


def test_strong_combos_beat_rule():
    # strong 语义自洽:delta_vme<0(融合优于规则)
    import json, os
    os.chdir("/Volumes/T7/PRAXIS-MDR-GNB")
    p = "reports/antibacterial/mdr_gnb/g2r_locked/evidence_sweep.json"
    if os.path.exists(p):
        rs = json.load(open(p))
        for r in [x for x in rs if x.get("tier") == "strong"]:
            assert r["delta_vme"] < 0 and r["p_value"] < 0.05
