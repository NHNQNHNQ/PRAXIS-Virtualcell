"""Phase 17 接线测试:证明 cc_map 真的流过生产 sweep 调用链(闭合两病灶)。

关键:接线可能"形式上传了参数但没生效"。这些测试用合成数据端到端跑 sweep_combo /
_oof_predict / nested_cv_verdict / feasible_combos,断言 CC 分组真的改变了分母(n_R_ST)
和可行性判据——每个都做变异验证(把透传断掉 → 该测试红)。

本地无 mlst_raw.tsv(load_cc_map 返回 {}),故用**合成 cc_map** 证明管道通(真实 cc_map
只能在 .53 拿)。
"""
import numpy as np
import pytest

from praxis_virtualcell.mdr_gnb.predictors.mechanism_features import augmented_features
from praxis_virtualcell.mdr_gnb.predictors.rule_baseline import RuleBaselineSIR
from praxis_virtualcell.mdr_gnb.workflows import run_g2r_evidence_sweep as sweep
from praxis_virtualcell.mdr_gnb.workflows import run_g2r_nested_cv as ncv

# CC258 形状:5 个链 ST 聚成 1 个 CC(CC11);两个独立 R 单例、两个 S 单例。
_CHAIN = ["ST258", "ST11", "ST340", "ST437", "ST512"]
_CC_MAP = {s: "CC11" for s in _CHAIN}   # 链 → CC11;其余 ST 回退自身


def _synth_rows():
    """合成 meropenem combo:链 5 ST(全 R,blaKPC)+ 2 独立 R 单例 + 2 S 单例。

    R 单元数:按 ST = 5(链)+ 2 = 7;按 CC = 1(CC11)+ 2 = 3。
    """
    amr, st_map = [], {}

    def add(st, n, pheno, geno):
        for k in range(n):
            gid = f"{st}_g{k}"
            amr.append({
                "genome_id": gid, "antibiotic": "meropenem",
                "resistant_phenotype": pheno, "ncbi_amr_genotypes": geno,
            })
            st_map[gid] = st

    for st in _CHAIN:
        add(st, 3, "R", "blaKPC-3")          # rule→R,carbapenemase 特征
    add("ST700", 3, "R", "blaNDM-1")         # 独立 R 单例
    add("ST701", 3, "R", "blaNDM-1")
    add("ST800", 4, "S", "aac(6')-Ib")       # 非 mero 家族 → rule→S,良性特征
    add("ST801", 4, "S", "aac(6')-Ib")
    return amr, st_map


# ── 1. cc_map 真流过 sweep_combo → n_R_ST 变小(核心接线证据)────────────────────
def test_sweep_combo_cc_map_changes_n_rst(monkeypatch):
    amr, st_map = _synth_rows()
    monkeypatch.setattr(sweep, "load_inputs_from_disk", lambda sp, data: (amr, st_map, {}))

    r_st = sweep.sweep_combo("klebsiella_pneumoniae", "meropenem", cc_map=None)
    r_cc = sweep.sweep_combo("klebsiella_pneumoniae", "meropenem", cc_map=_CC_MAP)

    assert r_st["n_R_ST"] == 7, "按 ST:链 5 + 2 独立 = 7 个 R 单元"
    assert r_cc["n_R_ST"] == 3, "按 CC:链聚成 1(CC11)+ 2 独立 = 3 个 R 单元"
    assert r_cc["n_R_ST"] < r_st["n_R_ST"], "CC 分组下独立 R 单元更少(伪重复消除)"


def test_sweep_combo_none_is_backward_compatible(monkeypatch):
    # cc_map=None(默认)= 旧 ST 行为:不传与显式传 None 结果一致。
    amr, st_map = _synth_rows()
    monkeypatch.setattr(sweep, "load_inputs_from_disk", lambda sp, data: (amr, st_map, {}))
    default = sweep.sweep_combo("klebsiella_pneumoniae", "meropenem")
    explicit_none = sweep.sweep_combo("klebsiella_pneumoniae", "meropenem", cc_map=None)
    assert default["n_R_ST"] == explicit_none["n_R_ST"] == 7
    assert default == explicit_none


# ── 1b. sweep_combo 把 cc_map 喂进 _oof_predict(切分那一跳,单独钉死)─────────────
def test_sweep_combo_forwards_cc_map_to_oof(monkeypatch):
    # n_R_ST 7→3 由**聚合**透传驱动、与切分无关;切分透传(sweep_combo→_oof_predict)是
    # 活代码(真改分折→改 OOF 预测)但无断言钉住 → 存活变异。此测试专钉这一跳。
    amr, st_map = _synth_rows()
    monkeypatch.setattr(sweep, "load_inputs_from_disk", lambda sp, data: (amr, st_map, {}))
    captured = []
    real_oof = sweep._oof_predict

    def rec(*args, cc_map=None, **kw):
        captured.append(cc_map)
        return real_oof(*args, cc_map=cc_map, **kw)   # 委托真 _oof_predict,sweep_combo 照常跑完

    monkeypatch.setattr(sweep, "_oof_predict", rec)
    sweep.sweep_combo("klebsiella_pneumoniae", "meropenem", cc_map=_CC_MAP)
    # 变异验证:若 sweep_combo 的 _oof_predict(...) 调用漏传 cc_map,rec 收到默认 None → 断言红。
    assert captured == [_CC_MAP], "sweep_combo 应把 cc_map 喂进 _oof_predict(切分透传)"


# ── 2. _oof_predict 把 cc_map 透传给 make_lineage_splits(切分病灶接线)──────────
def test_oof_predict_forwards_cc_map_to_splits(monkeypatch):
    amr, st_map = _synth_rows()
    rule = RuleBaselineSIR(db_version=sweep.DB)
    captured = []
    real = ncv.make_lineage_splits

    def rec(ids, st_map, n_splits=5, group_key="ST", cc_map=None):
        captured.append(cc_map)
        return real(ids, st_map, n_splits=n_splits, group_key=group_key, cc_map=cc_map)

    monkeypatch.setattr(ncv, "make_lineage_splits", rec)
    ncv._oof_predict(amr, st_map, rule, "meropenem", augmented_features, 0, cc_map=_CC_MAP)
    # 变异验证:若 _oof_predict 内部不透传 cc_map,captured 里会是 None → 断言红。
    assert captured and all(c == _CC_MAP for c in captured), "cc_map 应透传到 make_lineage_splits"


# ── 3. nested_cv_verdict 把 cc_map 透传到外层切分(锚点确认路径接线)──────────────
def _balanced_cc_data():
    """6 个均衡 CC(每 CC 2 个 SLV ST、每 ST 1R1S),供嵌套 CV(内外层都要够组数)。"""
    amr, st_map, cc_map = [], {}, {}
    for c in range(6):
        for pair in range(2):
            st = f"ST{c}_{pair}"
            cc_map[st] = f"CC{c}"
            for k in range(2):
                gid = f"{st}_g{k}"
                amr.append({"genome_id": gid, "antibiotic": "meropenem",
                            "resistant_phenotype": "R" if k == 0 else "S",
                            "ncbi_amr_genotypes": "blaKPC-3"})
                st_map[gid] = st
    return amr, st_map, cc_map


def test_nested_cv_verdict_forwards_cc_map(monkeypatch):
    amr, st_map, cc_map = _balanced_cc_data()
    rule = RuleBaselineSIR(db_version=sweep.DB)
    captured = []
    real = ncv.make_lineage_splits

    def rec(ids, st_map, n_splits=5, group_key="ST", cc_map=None):
        captured.append(cc_map)
        return real(ids, st_map, n_splits=n_splits, group_key=group_key, cc_map=cc_map)

    monkeypatch.setattr(ncv, "make_lineage_splits", rec)
    ncv.nested_cv_verdict(amr, st_map, rule, "meropenem", seed=0,
                          n_outer=2, n_inner=2, n_perm=50, cc_map=cc_map)
    assert captured and all(c == cc_map for c in captured), \
        "外层切分 + 内层 OOF 都应带上 cc_map"


# ── 4. feasible_combos 可行性判据改按 R-CC(否则把"CC 数不够"误判可行)──────────
def test_feasible_combos_counts_r_cc(monkeypatch):
    # 13 个 ST 全属一个 CC、全 R、52 株:R-ST=13≥12(旧判可行),R-CC=1<12(新判不可行)。
    sts = [f"ST{i}" for i in range(1, 14)]
    cc_map = {s: "CC1" for s in sts}
    amr, st_map = [], {}
    for st in sts:
        for k in range(4):
            gid = f"{st}_g{k}"
            amr.append({"genome_id": gid, "antibiotic": "meropenem",
                        "resistant_phenotype": "R", "ncbi_amr_genotypes": "blaKPC-3"})
            st_map[gid] = st

    def fake_load(sp, data):
        return (amr, st_map, {}) if sp == "klebsiella_pneumoniae" else ([], {}, {})

    monkeypatch.setattr(sweep, "load_inputs_from_disk", fake_load)
    monkeypatch.setattr(sweep, "_trained_drugs",
                        lambda sp: ["meropenem"] if sp == "klebsiella_pneumoniae" else [])

    without_cc = sweep.feasible_combos()                     # 旧:按 R-ST=13 → 可行
    with_cc = sweep.feasible_combos(cc_maps={"klebsiella_pneumoniae": cc_map})  # 新:R-CC=1 → 不可行
    assert without_cc == [("klebsiella_pneumoniae", "meropenem")]
    assert with_cc == [], "R-CC=1<12 → CC 判据下该组合不可行"


# ── 5. _worker 兼容 3 元组(sp, dr, cc_map)且把 cc_map 传进 sweep_combo ──────────
def test_worker_passes_cc_map(monkeypatch):
    seen = {}
    monkeypatch.setattr(sweep, "sweep_combo",
                        lambda sp, dr, cc_map=None: seen.update(sp=sp, dr=dr, cc_map=cc_map) or {})
    sweep._worker(("klebsiella_pneumoniae", "meropenem", _CC_MAP))
    assert seen == {"sp": "klebsiella_pneumoniae", "dr": "meropenem", "cc_map": _CC_MAP}
    # 兼容旧 2 元组
    seen.clear()
    sweep._worker(("klebsiella_pneumoniae", "meropenem"))
    assert seen["cc_map"] is None


# ── 6. select_tstar 接受 cc_map 且不破坏旧行为 ──────────────────────────────────
def test_select_tstar_accepts_cc_map():
    rng = np.random.RandomState(0)
    n = 200
    y = (rng.rand(n) < 0.4).astype(int)
    ru = np.where(y == 1, (rng.rand(n) < 0.6).astype(int), (rng.rand(n) < 0.1).astype(int))
    p = np.clip(y * 0.6 + rng.rand(n) * 0.5, 0, 1)
    st = np.array([f"ST{i % 20}" for i in range(n)])
    rule_me = float((ru[y == 0] == 1).mean())
    # cc_map=None 与不传逐字相同(向后兼容)
    a = ncv.select_tstar(p, ru, y, st, rule_me=rule_me)
    b = ncv.select_tstar(p, ru, y, st, rule_me=rule_me, cc_map=None)
    assert a == b
    # 传 cc_map(把 20 个 ST 折成 2 个 CC)可跑通、返回有限 t*
    cc = {f"ST{i}": ("CCa" if i % 2 == 0 else "CCb") for i in range(20)}
    t, pv, me = ncv.select_tstar(p, ru, y, st, rule_me=rule_me, cc_map=cc)
    assert 0.02 <= t <= 0.98 and np.isfinite(pv) == (pv == pv)  # pv 有限或 inf 均合法
