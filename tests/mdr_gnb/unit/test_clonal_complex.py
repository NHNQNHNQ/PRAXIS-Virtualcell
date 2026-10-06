"""克隆复合体(CC)SLV 分组测试:goeBURST 单连锁派生 + 修两处克隆群泄漏病灶。

覆盖 Phase 17 交付:
1. CC 派生正确性(SLV 单位点变异体聚一起,>1 位点差不聚)。
2. CC258 形状负对照(5 成员链聚成 1 CC;喂 make_lineage_splits → 同折;
   cc_map=None 退回 ST 分组 → 分散多折,证明分组真的改了行为)。
3. 确定性(打乱 dict 顺序输出逐字相同;CC id = 最小 ST 号规范名,非并查集 rep)。
4. 向后兼容(cc_map=None 与旧行为逐字相同)。
5. 等位谱解析(locus(NN) 抽号,缺失位点=0)。
6. fail-soft(不存在的文件 → {})。
"""
import numpy as np
import pytest

from praxis_virtualcell.mdr_gnb.evaluators.clonal_complex import (
    derive_cc_slv,
    load_cc_map,
    parse_mlst_alleles,
)
from praxis_virtualcell.mdr_gnb.evaluators.lineage_split import make_lineage_splits
from praxis_virtualcell.mdr_gnb.evaluators.significance import st_level_vme


# ── 合成等位谱 ────────────────────────────────────────────────────────────────
# CC258 五成员链:相邻两两 SLV(单位点差),单连锁串成一个连通分量。
_CC258_CHAIN = {
    "ST258": (1, 1, 1, 1, 1, 1, 1),
    "ST11": (1, 1, 1, 1, 1, 1, 2),   # 与 258 差 pos6 → SLV
    "ST340": (1, 1, 1, 1, 1, 2, 2),  # 与 11 差 pos5 → SLV
    "ST437": (1, 1, 1, 1, 2, 2, 2),  # 与 340 差 pos4 → SLV
    "ST512": (1, 1, 1, 2, 2, 2, 2),  # 与 437 差 pos3 → SLV
}
# 5 个互不相干的单例 ST(两两共享 0 位点,也不是链的 SLV)。
_SINGLETONS = {
    "ST900": (10, 10, 10, 10, 10, 10, 10),
    "ST901": (20, 20, 20, 20, 20, 20, 20),
    "ST902": (30, 30, 30, 30, 30, 30, 30),
    "ST903": (40, 40, 40, 40, 40, 40, 40),
    "ST904": (50, 50, 50, 50, 50, 50, 50),
}


# ── 1. CC 派生正确性 ─────────────────────────────────────────────────────────
def test_derive_cc_slv_basic():
    profiles = {
        "ST1": (1, 1, 1, 1, 1, 1, 1),
        "ST2": (1, 1, 1, 1, 1, 1, 2),   # 与 ST1 单位点差 → SLV → 同 CC
        "ST3": (9, 9, 9, 1, 1, 1, 1),   # 与 ST1 差 3 位点 → 不同 CC
    }
    cc = derive_cc_slv(profiles, max_diff=1)
    assert cc["ST1"] == cc["ST2"], "SLV 应聚同一 CC"
    assert cc["ST1"] != cc["ST3"], "差 3 位点不应同 CC"


def test_derive_cc_slv_ignores_zero_loci():
    # 缺失位点(0)不参与相邻判定:两 ST 仅靠 0 位点"相同"不算共享。
    profiles = {
        "STA": (0, 0, 0, 0, 0, 0, 1),  # 只有 pos6 非 0
        "STB": (0, 0, 0, 0, 0, 0, 1),  # 同 pos6,但其余全 0
    }
    cc = derive_cc_slv(profiles, max_diff=1)
    # 仅 1 个非 0 且相等 < 7-1=6 → 不聚
    assert cc["STA"] != cc["STB"]


# ── 2. CC258 形状负对照(核心)────────────────────────────────────────────────
def test_cc258_five_members_collapse_to_one_cc():
    cc = derive_cc_slv(_CC258_CHAIN, max_diff=1)
    ccs = {cc[s] for s in _CC258_CHAIN}
    assert len(ccs) == 1, f"CC258 五成员应聚成 1 个 CC,实得 {ccs}"
    # 规范名 = 最小 ST 号 → CC11
    assert cc["ST258"] == "CC11", f"CC id 应为最小 ST 号 CC11,实得 {cc['ST258']}"


def _chain_split_data():
    """构造:CC258 链 5 ST(每 2 株)+ 5 单例 ST(每 2 株),供 make_lineage_splits。"""
    profiles = {**_CC258_CHAIN, **_SINGLETONS}
    genome_ids, st_map = [], {}
    for st in profiles:
        for k in range(2):
            gid = f"{st}_g{k}"
            genome_ids.append(gid)
            st_map[gid] = st
    return genome_ids, st_map, profiles


def _chain_leaks_in_some_fold(specs, st_map, chain_sts):
    """某折里链 ST 同时出现在 train 和 test → 该折发生跨折泄漏。"""
    for spec in specs:
        tr = {st_map[g] for g in spec.train_ids} & chain_sts
        te = {st_map[g] for g in spec.test_ids} & chain_sts
        if tr and te:
            return True
    return False


def test_cc_grouping_keeps_chain_in_one_fold():
    # CC 分组:5 链 ST 聚成 1 CC → GroupKFold 整组同侧,任何折都不跨 train/test。
    genome_ids, st_map, profiles = _chain_split_data()
    cc_map = derive_cc_slv(profiles, max_diff=1)
    specs = make_lineage_splits(genome_ids, st_map, n_splits=5, cc_map=cc_map)
    assert specs, "应产出 fold"
    chain = set(_CC258_CHAIN)
    assert not _chain_leaks_in_some_fold(specs, st_map, chain), \
        "CC 分组下链 5 成员不应跨 train/test"
    # 且这 5 个 ST 确实同在某一折的 test 里(整组一起被留出)
    together = any(
        chain <= {st_map[g] for g in spec.test_ids} for spec in specs
    )
    assert together, "CC 分组下 5 链 ST 应整组落在同一折 test"


def test_st_grouping_scatters_chain_across_folds():
    # 变异:cc_map=None 退回精确 ST 分组 → 5 链 ST 是 5 个独立组 → 分散多折 → 跨折泄漏。
    genome_ids, st_map, _ = _chain_split_data()
    specs = make_lineage_splits(genome_ids, st_map, n_splits=5, cc_map=None)
    assert specs
    chain = set(_CC258_CHAIN)
    assert _chain_leaks_in_some_fold(specs, st_map, chain), \
        "ST 分组下链成员应分散到多折并跨 train/test(证明 CC 分组真的改了行为)"


# ── 3. 确定性 ────────────────────────────────────────────────────────────────
def test_derive_cc_slv_deterministic_under_shuffle():
    import random
    base = derive_cc_slv(_CC258_CHAIN, max_diff=1)
    items = list(_CC258_CHAIN.items())
    for seed in (1, 7, 42):
        random.Random(seed).shuffle(items)
        shuffled = dict(items)
        out = derive_cc_slv(shuffled, max_diff=1)
        assert out == base, f"打乱输入顺序(seed={seed})CC 映射应逐字不变"
    # 规范化必须走最小 ST 号,不是并查集任意 rep
    assert set(base.values()) == {"CC11"}


def test_singleton_is_its_own_cc():
    cc = derive_cc_slv({"ST777": (1, 2, 3, 4, 5, 6, 7)}, max_diff=1)
    assert cc == {"ST777": "CC777"}


# ── 4. 向后兼容 ──────────────────────────────────────────────────────────────
def test_make_lineage_splits_none_equals_legacy():
    genome_ids, st_map, _ = _chain_split_data()
    with_none = make_lineage_splits(genome_ids, st_map, n_splits=5, cc_map=None)
    legacy = make_lineage_splits(genome_ids, st_map, n_splits=5)
    assert len(with_none) == len(legacy)
    for a, b in zip(with_none, legacy):
        assert a.train_ids == b.train_ids
        assert a.test_ids == b.test_ids
        assert a.group_key == b.group_key


def test_st_level_vme_none_equals_legacy():
    st = np.array(["A", "A", "B", "B"])
    yt = np.array([1, 1, 1, 1])
    yp = np.array([1, 1, 0, 1])
    assert st_level_vme(st, yt, yp, cc_map=None) == st_level_vme(st, yt, yp)


def test_st_level_vme_aggregates_by_cc():
    # 用**不平衡**样本钉住"汇总"语义(而非"先按 ST 算再平均"):
    # A(2 真R 全对)+ B(4 真R,1 株判 S),同属 CC1。
    #   汇总(pooled)     = 1/6 ≈ 0.1667   ← 正确语义(把 CC 内所有株一起算)
    #   avg-of-ST(退化法)= (0/2 + 1/4)/2 = 0.125   ← 若代码退化成平均会得这个
    # 平衡样本(A=2,B=2)下两者恰都 0.25,区分不了 → 必须用不平衡。
    st = np.array(["A", "A", "B", "B", "B", "B"])
    yt = np.array([1, 1, 1, 1, 1, 1])
    yp = np.array([1, 1, 0, 1, 1, 1])   # 仅 B 的第 1 株判 S
    cc_map = {"A": "CC1", "B": "CC1"}
    per = st_level_vme(st, yt, yp, cc_map=cc_map)
    assert set(per) == {"CC1"}
    # 变异验证:若聚合退化成 avg-of-ST(0.125),此断言必红 → 钉死"汇总"语义。
    assert per["CC1"] == pytest.approx(1 / 6)
    assert per["CC1"] != pytest.approx(0.125)
    # 对照:不给 cc_map → 按 ST 聚,A=0.0、B=1/4
    per_st = st_level_vme(st, yt, yp)
    assert per_st["A"] == 0.0 and per_st["B"] == pytest.approx(0.25)


# ── 5. 等位谱解析 ────────────────────────────────────────────────────────────
def test_parse_mlst_alleles(tmp_path):
    p = tmp_path / "mlst_raw.tsv"
    p.write_text(
        # ST258:含一个缺失位点 phoE(~) → 记 0;一个多等位 tonB(3,4) → 记 0
        "data/x/GCA_000401195.1.fna\tklebsiella\t258\t"
        "gapA(3)\tinfB(3)\tmdh(1)\tpgi(1)\tphoE(~)\trpoB(1)\ttonB(3,4)\n"
        # ST '-' → 跳过
        "data/x/GCA_000000000.1.fna\tklebsiella\t-\t"
        "gapA(1)\tinfB(1)\tmdh(1)\tpgi(1)\tphoE(1)\trpoB(1)\ttonB(1)\n"
        # 同 ST258 再来一行 → 取首见,不覆盖
        "data/x/GCA_999999999.1.fna\tklebsiella\t258\t"
        "gapA(9)\tinfB(9)\tmdh(9)\tpgi(9)\tphoE(9)\trpoB(9)\ttonB(9)\n",
        encoding="utf-8",
    )
    prof = parse_mlst_alleles(p)
    assert set(prof) == {"ST258"}, "ST '-' 应被跳过"
    assert prof["ST258"] == (3, 3, 1, 1, 0, 1, 0), "缺失/多等位位点应记 0,首见优先"


# ── 6. fail-soft ─────────────────────────────────────────────────────────────
def test_load_cc_map_missing_file_returns_empty(tmp_path):
    assert load_cc_map("nosuchsp", tmp_path) == {}
