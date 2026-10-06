"""B5-肽 baseline gate:序列相似度分组防泄漏 + RF + OOD + 优于 baseline。

harness 逻辑用**合成数据**验证(无网、确定性、始终可跑):聚类把相似序列归一族、GroupKFold 无泄漏、
RF 学到信号优于均值。真 DBAASP 数据 gate 用 skip-if-missing(拉取前不 fail,拉取后校验)。
真数据拉取:python -m praxis_virtualcell.mdr_gnb.workflows.science_v2.dbaasp_pull --species 'Escherichia coli'
"""


import csv


from pathlib import Path


import numpy as np


import pytest


from praxis_virtualcell.mdr_gnb.workflows.science_v2 import peptide_baseline as pb


OUT = Path("reports/antibacterial/mdr_gnb/science_v2/peptide_baseline")


def test_kmers_and_jaccard():
    a = pb.kmers("ACDEFG")
    b = pb.kmers("ACDEFG")
    assert pb.jaccard(a, b) == 1.0                 # 自身
    c = pb.kmers("WWWWWW")
    assert pb.jaccard(a, c) == 0.0                 # 无共享 k-mer
    assert 0.0 < pb.jaccard(a, pb.kmers("ACDEFH")) < 1.0


def test_cluster_groups_similar_separates_different():
    # 两族:KKKK... 家族 与 DDDD... 家族,组内相似组间不同
    fam1 = ["KKKKAAAA", "KKKKAAAG", "KKKKAAGA"]     # 高度相似
    fam2 = ["DDDDWWWW", "DDDDWWWY", "DDDDWWYW"]
    seqs = fam1 + fam2
    g = pb.cluster_by_similarity(seqs)
    assert len(set(g[:3])) == 1                     # fam1 同族
    assert len(set(g[3:])) == 1                     # fam2 同族
    assert g[0] != g[3]                             # 两族不同组


def test_cluster_transitivity_no_cross_cluster_leak():
    # 连通分量聚类核心:相似⇒必同组(传递闭包)。梯队序列(A~B~C 链式相似)须全归一族,
    # 且跨簇最大 Jaccard < 阈(真泄漏度量,非"每簇单一 fold"的恒真空断言)。
    import random
    rng = random.Random(0)
    seqs = []
    base = list("KLWKKLLKKLLKKLLKKAAA")
    for _ in range(40):                             # 40 条点突变梯队(近重复,应聚成极少数族)
        s = base[:]
        i = rng.randrange(len(s))
        s[i] = rng.choice("AGLK")
        seqs.append("".join(s))
    g = pb.cluster_by_similarity(seqs)
    # 真泄漏度量:任何跨簇序列对的 k-mer Jaccard 都 < 聚类阈(相似的都被并进同族)
    assert pb.max_cross_cluster_similarity(seqs, g) < pb.CLUSTER_THRESHOLD


def _synthetic():
    # 6 个序列族,每族 ~7 成员(族内近似);信号:净电荷(K 越多)→ log10-MIC 越低
    import random
    rng = random.Random(0)
    seqs, y = [], []
    bases = ["KKKKKKAAAA", "KKKAAAAAAA", "RRRRGGGGLL", "DDEEAAAAAA",
             "WWFFYYAAAA", "LLIIVVAAAA"]
    for b in bases:
        pos = b.count("K") + b.count("R")
        for _ in range(7):
            s = list(b)
            # 族内小扰动(替换 1 个位置为相邻同类),保持相似 → 同族
            i = rng.randrange(len(s))
            s[i] = rng.choice("AG")
            seq = "".join(s)
            seqs.append(seq)
            # 信号:正电荷高→MIC 低(log10 小)+ 小噪声
            y.append(2.0 - 0.3 * pos + rng.gauss(0, 0.1))
    return seqs, np.array(y, dtype=float)


def test_synthetic_pipeline_no_leak_and_beats_mean():
    seqs, y = _synthetic()
    X = np.stack([pb.peptide_vector(s) for s in seqs])
    kms = [pb.kmers(s) for s in seqs]
    groups = pb.cluster_by_similarity(seqs)
    assert len(set(groups)) >= 2                    # 多族才能 GroupKFold
    oof, n_splits, n_clusters = pb.scaffold_oof(y, groups, kms, X)
    # 无泄漏(GroupKFold 保证每族单一 fold)
    fold_by_group = {}
    for g, f in zip(groups, oof["fold"]):
        fold_by_group.setdefault(g, set()).add(int(f))
    assert all(len(fs) == 1 for fs in fold_by_group.values())
    # **真泄漏度量**:跨簇最大相似度 < 阈 → 近重复序列没被拆到不同折(连通分量聚类保证)
    assert pb.max_cross_cluster_similarity(seqs, groups) < pb.CLUSTER_THRESHOLD
    # RF 学到电荷信号 → 优于均值 baseline(在无残余泄漏前提下)
    m = pb.compute_metrics(y, oof)
    assert m["beats_mean"] is True


def test_synthetic_oof_deterministic():
    seqs, y = _synthetic()
    X = np.stack([pb.peptide_vector(s) for s in seqs])
    kms = [pb.kmers(s) for s in seqs]
    groups = pb.cluster_by_similarity(seqs)
    a = pb.scaffold_oof(y, groups, kms, X)[0]["pred"]
    b = pb.scaffold_oof(y, groups, kms, X)[0]["pred"]
    assert np.array_equal(a, b)                     # tree_preds.mean 固定顺序 → 确定


def _artifacts_exist():
    return (OUT / "peptide_metrics.csv").exists() and (OUT / "peptide_per_seq.parquet").exists()
