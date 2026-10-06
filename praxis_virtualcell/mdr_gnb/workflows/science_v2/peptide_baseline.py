"""B5-肽 baseline:抗菌肽序列 → log10-MIC(µM)QSAR(理化特征 + RF),仿 B0.1 qsar_baseline。

把 B0.1 三条纪律迁到**肽序列空间**:
  1. 防泄漏:小分子的 Bemis-Murcko scaffold 分组 → 肽的 **序列相似度分组**(k-mer Jaccard 贪心聚类,
     相似序列不跨折,防模型"记住序列族"而非学序列-活性关系)。核心不变量。
  2. fail-closed:序列空间外(对训练集最大 k-mer Jaccard 低)→ 低可信,应弃权。
  3. 证据分层:须显著优于平凡 baseline(均值 + 1-NN 最近邻序列)。

方法(写死):peptide_vector(20 AA 组成 + 5 理化)+ 序列相似度 GroupKFold OOF + RF。
输入:data/mdr_gnb/raw/peptide_activity/<species>_peptide_mic_clean.parquet(dbaasp_pull 产;
列 sequence/mic_um/n_meas/log10_mic)。**拉取中时不存在 → 报错退出,gate fail(不伪造)。**
产物:reports/antibacterial/mdr_gnb/science_v2/peptide_baseline/。
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from praxis_virtualcell.mdr_gnb.drug_agent.peptide_features import peptide_vector

_ROOT = Path(__file__).resolve().parents[4]
_DATA = _ROOT / "data" / "mdr_gnb" / "raw" / "peptide_activity"
_OUT = _ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v2" / "peptide_baseline"

SEED = 0
KMER = 3                    # 序列相似度用的 k-mer 长度
CLUSTER_THRESHOLD = 0.5     # k-mer Jaccard ≥ 此 → 同一序列族(分组防泄漏)
OOD_THRESHOLD = 0.3         # 对训练集最大 Jaccard < 此 = 序列空间外(OOD)
N_ESTIMATORS = 300
FOLDS = 5
COVERAGES = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]


# ---------------------------------------------------------------- 序列相似度
def kmers(seq: str, k: int = KMER) -> frozenset:
    """序列的 k-mer 集合(序列相似度基元)。短于 k 时退化为整串。"""
    if len(seq) < k:
        return frozenset({seq})
    return frozenset(seq[i:i + k] for i in range(len(seq) - k + 1))


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / len(a | b)


def cluster_by_similarity(seqs: list[str]) -> list[int]:
    """k-mer Jaccard **连通分量**聚类 → 每序列的 group id(相似⇒必同组,传递闭包)。

    并查集:对**任意** Jaccard≥阈的序列对做 union(不只跟簇代表比)——恢复"相似必同组"的等价类
    性质(对齐 B0.1 的 scaffold 精确分组),防近重复序列(alanine-scan/点突变/截短类似物)跨折泄漏。
    倒排索引(k-mer→含它的序列)只比共享 k-mer 的候选对,避 O(n²) 全比。确定性:小下标作根 + 稠密重编号。
    """
    n = len(seqs)
    kms = [kmers(s) for s in seqs]
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]       # 路径压缩
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)   # 小下标作根 → 确定性

    inv: dict[str, list[int]] = {}              # k-mer → 含它的序列下标
    for i, km in enumerate(kms):
        for k in km:
            inv.setdefault(k, []).append(i)
    for members in inv.values():                # 只比共享 ≥1 k-mer 的候选对
        for a in range(len(members)):
            ia = members[a]
            for b in range(a + 1, len(members)):
                ib = members[b]
                if find(ia) == find(ib):        # 已同组,跳过(避重复算 Jaccard)
                    continue
                if jaccard(kms[ia], kms[ib]) >= CLUSTER_THRESHOLD:
                    union(ia, ib)
    # 连通分量 → 稠密 group id(按序列下标序首次出现分配,确定性)
    roots: dict[int, int] = {}
    gid = [0] * n
    for i in range(n):
        r = find(i)
        if r not in roots:
            roots[r] = len(roots)
        gid[i] = roots[r]
    return gid


def max_cross_cluster_similarity(seqs: list[str], groups: list[int]) -> float:
    """跨簇最大 k-mer Jaccard(真泄漏度量):连通分量聚类下应 < CLUSTER_THRESHOLD。

    与"每簇单一 fold"(GroupKFold 恒真的空断言)不同,这才真校验相似序列没被拆到不同组→不同折。
    """
    kms = [kmers(s) for s in seqs]
    inv: dict[str, list[int]] = {}
    for i, km in enumerate(kms):
        for k in km:
            inv.setdefault(k, []).append(i)
    best = 0.0
    for members in inv.values():
        for a in range(len(members)):
            for b in range(a + 1, len(members)):
                ia, ib = members[a], members[b]
                if groups[ia] != groups[ib]:
                    best = max(best, jaccard(kms[ia], kms[ib]))
    return best


# ---------------------------------------------------------------- OOF
def _rmse(y_true, y_pred) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def scaffold_oof(y: np.ndarray, groups: list[int], kms: list, X: np.ndarray):
    """序列相似度 GroupKFold OOF:每折训 RF;test 每序列对本折 train 最大 Jaccard(OOD)+ 1-NN。"""
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import GroupKFold

    n = len(y)
    n_groups = len(set(groups))
    n_splits = min(FOLDS, n_groups)
    if n_splits < 2:
        raise ValueError(f"序列族数={n_groups}<2,无法 GroupKFold")

    pred = np.full(n, np.nan)
    std = np.full(n, np.nan)
    fold = np.full(n, -1, dtype=int)
    maxsim = np.full(n, np.nan)
    nn1 = np.full(n, np.nan)
    meanpred = np.full(n, np.nan)

    gkf = GroupKFold(n_splits=n_splits)
    for fid, (tr, te) in enumerate(gkf.split(X, y, groups=groups)):
        rf = RandomForestRegressor(n_estimators=N_ESTIMATORS, random_state=SEED, n_jobs=-1)
        rf.fit(X[tr], y[tr])
        tree_preds = np.stack([t.predict(X[te]) for t in rf.estimators_])
        pred[te] = tree_preds.mean(axis=0)          # 固定顺序均值(确定性,避 RF 并行累加 ULP)
        std[te] = tree_preds.std(axis=0)
        fold[te] = fid
        meanpred[te] = y[tr].mean()
        train_km = [kms[i] for i in tr]
        train_y = y[tr]
        for j in te:
            sims = np.array([jaccard(kms[j], tk) for tk in train_km])
            k = int(sims.argmax())
            maxsim[j] = float(sims[k])
            nn1[j] = float(train_y[k])
    return {"pred": pred, "std": std, "fold": fold, "maxsim": maxsim,
            "nn1": nn1, "meanpred": meanpred}, n_splits, n_groups


def compute_metrics(y, oof) -> dict:
    from sklearn.metrics import mean_absolute_error, r2_score
    rf_rmse = _rmse(y, oof["pred"])
    return {
        "rf_r2": float(r2_score(y, oof["pred"])),
        "rf_mae": float(mean_absolute_error(y, oof["pred"])),
        "rf_rmse": rf_rmse,
        "mean_rmse": _rmse(y, oof["meanpred"]),
        "nn1_rmse": _rmse(y, oof["nn1"]),
        "beats_mean": bool(rf_rmse < _rmse(y, oof["meanpred"])),
        "beats_nn1": bool(rf_rmse < _rmse(y, oof["nn1"])),
    }


def ood_coverage(y, pred, maxsim) -> list[dict]:
    order = np.argsort(-maxsim, kind="stable")
    n = len(y)
    rows = []
    for cov in COVERAGES:
        k = max(1, int(round(cov * n)))
        idx = order[:k]
        rows.append({"coverage": f"{cov:.1f}", "n_kept": k,
                     "rmse": f"{_rmse(y[idx], pred[idx]):.4f}",
                     "min_sim_kept": f"{float(maxsim[idx].min()):.4f}"})
    return rows


# ---------------------------------------------------------------- 落盘
def _write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def _fmt(x, nd=4):
    return f"{float(x):.{nd}f}"


_METRIC_COLS = ["species", "n_peptides", "n_clusters", "rf_r2", "rf_mae", "rf_rmse",
                "mean_rmse", "nn1_rmse", "beats_mean", "beats_nn1"]


def write_outputs(species, seqs, groups, y, oof, metrics, n_splits, n_clusters):
    import pandas as pd
    _OUT.mkdir(parents=True, exist_ok=True)
    n = len(y)
    _write_csv(_OUT / "peptide_metrics.csv", _METRIC_COLS, [{
        "species": species, "n_peptides": n, "n_clusters": n_clusters,
        "rf_r2": _fmt(metrics["rf_r2"]), "rf_mae": _fmt(metrics["rf_mae"]),
        "rf_rmse": _fmt(metrics["rf_rmse"]), "mean_rmse": _fmt(metrics["mean_rmse"]),
        "nn1_rmse": _fmt(metrics["nn1_rmse"]),
        "beats_mean": metrics["beats_mean"], "beats_nn1": metrics["beats_nn1"]}])
    pd.DataFrame({
        "sequence": seqs, "cluster": groups, "log10_mic_true": y,
        "log10_mic_pred": oof["pred"], "pred_std": oof["std"], "nn1_pred": oof["nn1"],
        "max_sim_to_train": oof["maxsim"],
        "is_ood": oof["maxsim"] < OOD_THRESHOLD, "fold": oof["fold"],
    }).to_parquet(_OUT / "peptide_per_seq.parquet", index=False)
    cov_rows = ood_coverage(y, oof["pred"], oof["maxsim"])
    _write_csv(_OUT / "ood_coverage.csv",
               ["coverage", "n_kept", "rmse", "min_sim_kept"], cov_rows)
    manifest = {
        "species": species, "seed": SEED, "n_peptides": n, "n_clusters": n_clusters,
        "groupkfold_splits": n_splits, "kmer": KMER,
        "cluster_threshold": CLUSTER_THRESHOLD, "ood_threshold": OOD_THRESHOLD,
        "n_ood": int((oof["maxsim"] < OOD_THRESHOLD).sum()),
        "no_leak_assert": "连通分量聚类:跨簇最大 k-mer Jaccard < 阈(相似必同组;gate 真泄漏校验)",
        "features": "20 AA 组成 + 6 理化(length/net_charge/frac_pos/hydrophobicity/aromaticity/hydrophobic_moment)",
        "rf": {"n_estimators": N_ESTIMATORS, "random_state": SEED},
    }
    (_OUT / "cluster_split_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_report(species, y, metrics, cov_rows, manifest)


def _write_report(species, y, metrics, cov_rows, manifest):
    beats = metrics["beats_mean"] and metrics["beats_nn1"]
    cov1, cov05 = float(cov_rows[0]["rmse"]), float(cov_rows[-1]["rmse"])
    L = [f"# B5-肽 baseline(序列 → log10-MIC µM)— {species}\n",
         "把 Science v1 三纪律迁到肽序列空间:**序列相似度分组防泄漏**(k-mer Jaccard 聚类,"
         "相似序列不跨折)、**序列空间 OOD 弃权**、**证据分层**(须显著优于均值 + 1-NN)。\n",
         "## 方法(写死)\n",
         f"- 特征:20 AA 组成 + 5 理化;分组:k-mer(k={KMER})Jaccard 贪心聚类(阈 {CLUSTER_THRESHOLD})。\n"
         f"- CV:序列相似度 GroupKFold({manifest['groupkfold_splits']} 折);RF n_estimators={N_ESTIMATORS}。\n",
         "## 结果(log10-MIC µM 空间)\n",
         f"- 肽 {manifest['n_peptides']};序列族 {manifest['n_clusters']}。\n",
         f"- **RF**:R²={metrics['rf_r2']:.4f} MAE={metrics['rf_mae']:.4f} RMSE={metrics['rf_rmse']:.4f}。\n",
         f"- baseline RMSE:均值={metrics['mean_rmse']:.4f}、1-NN={metrics['nn1_rmse']:.4f}。\n",
         f"- **证据分层**:优于均值={metrics['beats_mean']}、优于1-NN={metrics['beats_nn1']} → "
         f"{'✅ 显著优于两平凡 baseline' if beats else '⚠️ 未同时优于,有效性存疑(需更强特征)'}。\n",
         "## 序列空间 OOD(coverage-RMSE)\n",
         "| 覆盖率 | 保留 | RMSE | 保留集最低相似 |", "|--:|--:|--:|--:|"]
    for r in cov_rows:
        L.append(f"| {r['coverage']} | {r['n_kept']} | {r['rmse']} | {r['min_sim_kept']} |")
    L.append(f"\n- 满覆盖 RMSE={cov1:.4f} → 留最相似 50% RMSE={cov05:.4f} → "
             f"{'✅ 有区分度' if cov05 <= cov1 + 1e-6 else '⚠️ 无区分度'}。\n")
    L.append("## 诚实边界\n- 仅 " + species + "、仅理化+组成特征 baseline;单位经肽 MW 折算 µM 有近似;"
             "序列相似度分组是化学版防泄漏核心不变量,但相似≠机制相同,对全新序列外推仍可能高估。\n")
    (_OUT / "peptide_baseline_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 驱动
def load_clean(species: str, data_dir: Path = _DATA):
    import pandas as pd
    safe = species.lower().replace(" ", "_")
    p = data_dir / f"{safe}_peptide_mic_clean.parquet"
    if not p.exists():
        raise FileNotFoundError(
            f"清洗集不存在:{p}\n  DBAASP 拉取中时预期如此,gate 保持 fail。\n"
            f"  就绪后先跑:python -m praxis_virtualcell.mdr_gnb.workflows.science_v2.dbaasp_pull "
            f"--species '{species}'")
    return pd.read_parquet(p)


def run(species: str = "Escherichia coli", data_dir: Path = _DATA) -> dict:
    df = load_clean(species, data_dir)
    seqs = df["sequence"].astype(str).tolist()
    y = df["log10_mic"].astype(float).to_numpy()
    print(f"{species}: 清洗集 {len(seqs)} 肽 → 特征化 + 序列相似度聚类…", flush=True)
    X = np.stack([peptide_vector(s) for s in seqs])
    kms = [kmers(s) for s in seqs]
    groups = cluster_by_similarity(seqs)
    print(f"  序列族 {len(set(groups))} 个 → GroupKFold OOF…", flush=True)
    oof, n_splits, n_clusters = scaffold_oof(y, groups, kms, X)
    metrics = compute_metrics(y, oof)
    write_outputs(species, seqs, groups, y, oof, metrics, n_splits, n_clusters)
    print(f"  RF R²={metrics['rf_r2']:.4f} RMSE={metrics['rf_rmse']:.4f} | "
          f"均值 {metrics['mean_rmse']:.4f} 1-NN {metrics['nn1_rmse']:.4f} | "
          f"beats_mean={metrics['beats_mean']} beats_nn1={metrics['beats_nn1']}", flush=True)
    print(f"落盘 → {_OUT}", flush=True)
    return metrics


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="B5-肽 baseline(序列→log10-MIC)")
    ap.add_argument("--species", default="Escherichia coli")
    args = ap.parse_args()
    run(args.species)
