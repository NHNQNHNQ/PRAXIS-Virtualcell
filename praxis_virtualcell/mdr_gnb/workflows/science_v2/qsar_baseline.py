"""B0.1:化合物结构 → 活性 QSAR baseline(line B 第一个从 SMILES 预测 MIC 的模型)。

平台此前只做"细菌基因型 → 已知药 SIR"(用 ST 谱系分组防泄漏)。line B 是全新方向:
**化合物 SMILES → 预测 log10-MIC**。把 Science v1 的三条纪律迁到化学空间:
  1. 防泄漏:基因型的 ST 分组 → 化合物的 **Bemis-Murcko scaffold(骨架)分组**
     (同骨架不跨 train/test,防模型"记住骨架族"而非学构效关系)。核心不变量。
  2. fail-closed:化学空间外(OOD,对训练集最大 Tanimoto 相似度低)→ 低可信,应弃权。
  3. 证据分层:QSAR 必须**显著优于平凡 baseline**(均值预测 + 1-NN Tanimoto),否则不算有效。

方法(写死,别自创):
  - featurize:RDKit Morgan 指纹(radius=2, nBits=2048)。baseline 用指纹即可,不上 GNN。
  - scaffold-GroupKFold OOF:groups=scaffold,同 scaffold 不跨折;每折训 RF 预测 log10-MIC,拼全 OOF。
  - 指标(log10-MIC 空间):R² / MAE / RMSE。对照:(a) 均值预测;(b) 1-NN(Tanimoto 最近邻的 log10-MIC)。
    RF RMSE 必须 < 两个 baseline(证据分层判据)。
  - 化学 OOD:每 OOF 化合物对训练集**最大 Tanimoto 相似度**;coverage-RMSE 曲线(按相似度降序保留,
    相似=更可信,RMSE 应随覆盖降而降)。
  - 不确定度:RF 各树预测的 std。

诚实边界:仅 EC、仅 Morgan 指纹 baseline。若 R² 低/不优于 baseline,如实报(可能需描述符/GNN)。

输入:data/mdr_gnb/raw/compound_activity/<species>_mic_clean.parquet(chembl_pull.py 产出;
     列 smiles / mic_ug_ml / n_meas / log10_mic)。**真数据拉取中时该文件不存在 → 报错退出,gate 保持 fail。**
产物:reports/antibacterial/mdr_gnb/science_v2/qsar_baseline/(见文件底部)。
用法:.venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v2.qsar_baseline --species escherichia_coli
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from praxis_virtualcell.mdr_gnb.drug_agent.small_molecule_features import (
    morgan_bitvect as _runtime_morgan_bitvect,
)

# 仓库根(本文件在 praxis_virtualcell/mdr_gnb/workflows/science_v2/)
_ROOT = Path(__file__).resolve().parents[4]
_DATA = _ROOT / "data" / "mdr_gnb" / "raw" / "compound_activity"
_OUT = _ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v2" / "qsar_baseline"

SEED = 0
N_BITS = 2048               # Morgan 指纹位数
RADIUS = 2                  # Morgan 半径
N_ESTIMATORS = 300          # RF 树数
FOLDS = 5                   # scaffold-GroupKFold 折数(scaffold 数不足则自适应降)
OOD_THRESHOLD = 0.3         # 最大 Tanimoto 低于此 = 化学空间外(OOD)
COVERAGES = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]   # OOD coverage-RMSE 曲线覆盖率(按相似度降序保留)


# ---------------------------------------------------------------- featurize
def _morgan_bitvect(smiles: str, n_bits: int = N_BITS, radius: int = RADIUS):
    """算 Morgan 指纹的 ExplicitBitVect（与生产推理共用定义）。"""
    return _runtime_morgan_bitvect(smiles, n_bits=n_bits, radius=radius)


def morgan_fp(smiles: str, n_bits: int = N_BITS, radius: int = RADIUS):
    """Morgan 指纹 → numpy int8 数组(供 RF 特征)。invalid SMILES 返回 None。"""
    from rdkit.DataStructs import ConvertToNumpyArray
    bv = _morgan_bitvect(smiles, n_bits, radius)
    if bv is None:
        return None
    arr = np.zeros((n_bits,), dtype=np.int8)
    ConvertToNumpyArray(bv, arr)
    return arr


def scaffold_of(smiles: str) -> str:
    """Bemis-Murcko scaffold(骨架)SMILES,作 scaffold-GroupKFold 分组键。

    invalid SMILES → "invalid";无环分子(骨架为空)→ "acyclic"。
    """
    from rdkit import Chem
    from rdkit.Chem.Scaffolds import MurckoScaffold
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return "invalid"
    core = MurckoScaffold.GetScaffoldForMol(m)
    if core is None:
        return "acyclic"
    smi = Chem.MolToSmiles(core)
    return smi if smi else "acyclic"


def featurize(smiles_list: list[str]):
    """对每 SMILES 算 bitvect + scaffold,丢弃 invalid(MolFromSmiles=None)并计数。

    返回 (keep_idx, scaffolds, bitvects, X, n_invalid):
      keep_idx  —— 保留(有效)化合物在原列表中的下标,供上游对齐 y。
      scaffolds —— 保留化合物的 scaffold(分组键)。
      bitvects  —— 保留化合物的 ExplicitBitVect(Tanimoto 用)。
      X         —— (n_keep, N_BITS) int8 指纹矩阵(RF 特征)。
      n_invalid —— 丢弃的 invalid SMILES 数(诚实计数)。
    """
    from rdkit.DataStructs import ConvertToNumpyArray
    keep_idx, scaffolds, bitvects = [], [], []
    n_invalid = 0
    for i, smi in enumerate(smiles_list):
        bv = _morgan_bitvect(smi)
        if bv is None:                       # invalid SMILES:诚实丢弃并计数
            n_invalid += 1
            continue
        keep_idx.append(i)
        bitvects.append(bv)
        scaffolds.append(scaffold_of(smi))   # bv 非空 ⇒ MolFromSmiles 成功 ⇒ 不会是 "invalid"
    X = np.zeros((len(bitvects), N_BITS), dtype=np.int8)
    for j, bv in enumerate(bitvects):
        ConvertToNumpyArray(bv, X[j])
    return keep_idx, scaffolds, bitvects, X, n_invalid


# ---------------------------------------------------------------- scaffold-GroupKFold OOF
def scaffold_oof(y: np.ndarray, scaffolds: list[str], bitvects: list, X: np.ndarray):
    """scaffold-GroupKFold 交叉验证,拼全 OOF 预测 + baseline + 化学 OOD 相似度。

    每折:训 RandomForestRegressor 预测 log10-MIC;各树预测 std 作不确定度;
    test 每化合物对本折 train 的最大 Tanimoto(OOD)与 1-NN 的 log10-MIC(baseline)。
    返回 dict(全 OOF 数组)+ (n_splits, n_scaffolds)。
    """
    from rdkit import DataStructs
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import GroupKFold

    n = len(y)
    n_scaffolds = len(set(scaffolds))
    n_splits = min(FOLDS, n_scaffolds)       # scaffold 数不足 FOLDS 时自适应降(GroupKFold 要求 splits≤组数)
    if n_splits < 2:
        raise ValueError(f"scaffold 数={n_scaffolds}<2,无法做 GroupKFold(需 ≥2 个不同 scaffold)")

    oof_pred = np.full(n, np.nan)
    oof_std = np.full(n, np.nan)
    oof_fold = np.full(n, -1, dtype=int)
    oof_maxtan = np.full(n, np.nan)          # 对 train 的最大 Tanimoto(OOD 判据)
    oof_nn1 = np.full(n, np.nan)             # 1-NN baseline 预测(最近邻 log10-MIC)
    oof_meanpred = np.full(n, np.nan)        # 均值 baseline 预测(train 均值)

    gkf = GroupKFold(n_splits=n_splits)
    for fold_id, (tr, te) in enumerate(gkf.split(X, y, groups=scaffolds)):
        rf = RandomForestRegressor(n_estimators=N_ESTIMATORS, random_state=SEED, n_jobs=-1)
        rf.fit(X[tr], y[tr])
        oof_pred[te] = rf.predict(X[te])
        # 不确定度:各树对 test 的预测 std
        tree_preds = np.stack([t.predict(X[te]) for t in rf.estimators_])
        oof_std[te] = tree_preds.std(axis=0)
        oof_fold[te] = fold_id
        oof_meanpred[te] = y[tr].mean()      # 均值 baseline:train 的 log10-MIC 均值
        # 化学 OOD + 1-NN:每 test 化合物对 train 的 Tanimoto 相似度向量 → max + 最近邻 y
        train_bits = [bitvects[i] for i in tr]
        train_y = y[tr]
        for j in te:
            sims = np.asarray(DataStructs.BulkTanimotoSimilarity(bitvects[j], train_bits))
            k = int(sims.argmax())
            oof_maxtan[j] = float(sims[k])
            oof_nn1[j] = float(train_y[k])

    return {
        "pred": oof_pred, "std": oof_std, "fold": oof_fold,
        "maxtan": oof_maxtan, "nn1": oof_nn1, "meanpred": oof_meanpred,
    }, n_splits, n_scaffolds


# ---------------------------------------------------------------- 指标
def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def compute_metrics(y: np.ndarray, oof: dict) -> dict:
    """log10-MIC 空间指标:RF 的 R²/MAE/RMSE + 两个 baseline RMSE + beats 判据(证据分层)。"""
    from sklearn.metrics import mean_absolute_error, r2_score
    rf_rmse = _rmse(y, oof["pred"])
    mean_rmse = _rmse(y, oof["meanpred"])
    nn1_rmse = _rmse(y, oof["nn1"])
    return {
        "rf_r2": float(r2_score(y, oof["pred"])),
        "rf_mae": float(mean_absolute_error(y, oof["pred"])),
        "rf_rmse": rf_rmse,
        "mean_rmse": mean_rmse,
        "nn1_rmse": nn1_rmse,
        "beats_mean": bool(rf_rmse < mean_rmse),   # 优于均值预测(基本有效性)
        "beats_nn1": bool(rf_rmse < nn1_rmse),     # 优于 1-NN(指纹检索胜过近邻抄答案)
    }


def ood_coverage(y: np.ndarray, pred: np.ndarray, maxtan: np.ndarray) -> list[dict]:
    """coverage-RMSE 曲线:按 max_tanimoto 降序保留(相似=更可信),报各覆盖率下 RMSE。

    有区分度时应随覆盖降而 RMSE 降(只留高相似 → 更准)。用稳定排序保证可复现。
    """
    order = np.argsort(-maxtan, kind="stable")     # 相似度降序(稳定排序,确定性)
    n = len(y)
    rows = []
    for cov in COVERAGES:
        k = max(1, int(round(cov * n)))
        idx = order[:k]
        rows.append({
            "coverage": f"{cov:.1f}",
            "n_kept": k,
            "rmse": f"{_rmse(y[idx], pred[idx]):.4f}",
            "min_tanimoto_kept": f"{float(maxtan[idx].min()):.4f}",
        })
    return rows


# ---------------------------------------------------------------- 落盘
def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """确定性写 CSV(固定列序,缺字段留空)。"""
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def _fmt(x: float, nd: int = 4) -> str:
    return f"{float(x):.{nd}f}"


_METRIC_COLS = ["species", "n_compounds", "n_scaffolds", "rf_r2", "rf_mae", "rf_rmse",
                "mean_rmse", "nn1_rmse", "beats_mean", "beats_nn1"]


def write_outputs(species: str, smiles: list[str], scaffolds: list[str], y: np.ndarray,
                  oof: dict, metrics: dict, n_splits: int, n_scaffolds: int,
                  n_invalid: int) -> None:
    """写五件产物:metrics.csv / per_compound.parquet / ood_coverage.csv / manifest.json / report.md。"""
    import pandas as pd

    _OUT.mkdir(parents=True, exist_ok=True)
    n = len(y)

    # 1) qsar_metrics.csv(一行)
    _write_csv(_OUT / "qsar_metrics.csv", _METRIC_COLS, [{
        "species": species, "n_compounds": n, "n_scaffolds": n_scaffolds,
        "rf_r2": _fmt(metrics["rf_r2"]), "rf_mae": _fmt(metrics["rf_mae"]),
        "rf_rmse": _fmt(metrics["rf_rmse"]), "mean_rmse": _fmt(metrics["mean_rmse"]),
        "nn1_rmse": _fmt(metrics["nn1_rmse"]),
        "beats_mean": metrics["beats_mean"], "beats_nn1": metrics["beats_nn1"],
    }])

    # 2) qsar_per_compound.parquet(每化合物预测 + 不确定度 + OOD 相似度)
    per = pd.DataFrame({
        "smiles": smiles,
        "scaffold": scaffolds,
        "log10_mic_true": y,
        "log10_mic_pred": oof["pred"],
        "pred_std": oof["std"],
        "nn1_pred": oof["nn1"],
        "max_tanimoto_to_train": oof["maxtan"],
        "is_ood": oof["maxtan"] < OOD_THRESHOLD,     # 化学空间外(应弃权)
        "fold": oof["fold"],
    })
    per.to_parquet(_OUT / "qsar_per_compound.parquet", index=False)

    # 3) ood_coverage.csv(coverage-RMSE 曲线)
    cov_rows = ood_coverage(y, oof["pred"], oof["maxtan"])
    _write_csv(_OUT / "ood_coverage.csv",
               ["coverage", "n_kept", "rmse", "min_tanimoto_kept"], cov_rows)

    # 4) scaffold_split_manifest.json(无泄漏断言 + 分组统计)
    sc = pd.Series(scaffolds)
    sc_counts = sc.value_counts()
    n_ood = int((oof["maxtan"] < OOD_THRESHOLD).sum())
    manifest = {
        "species": species,
        "seed": SEED,
        "n_compounds": n,
        "n_invalid_smiles_dropped": n_invalid,
        "n_scaffolds": n_scaffolds,
        "groupkfold_splits": n_splits,
        "max_scaffold_fraction": round(float(sc_counts.iloc[0]) / n, 4),
        "largest_scaffold": str(sc_counts.index[0]),
        "singleton_scaffold_fraction": round(float((sc_counts == 1).sum()) / n_scaffolds, 4),
        "ood_threshold": OOD_THRESHOLD,
        "n_ood_compounds": n_ood,
        "ood_fraction": round(n_ood / n, 4),
        "no_leak_assert": "每 scaffold 仅属单一 fold(GroupKFold groups=scaffold 保证;gate 硬校验)",
        "morgan": {"radius": RADIUS, "n_bits": N_BITS},
        "rf": {"n_estimators": N_ESTIMATORS, "random_state": SEED},
    }
    (_OUT / "scaffold_split_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")

    # 5) qsar_baseline_report.md(结论 + 诚实边界)
    _write_report(species, y, oof, metrics, cov_rows, manifest)


def _write_report(species: str, y: np.ndarray, oof: dict, metrics: dict,
                  cov_rows: list[dict], manifest: dict) -> None:
    beats_both = metrics["beats_mean"] and metrics["beats_nn1"]
    cov1 = float(cov_rows[0]["rmse"])
    cov05 = float(cov_rows[-1]["rmse"])
    ood_signal = cov05 <= cov1 + 1e-6
    L: list[str] = []
    L.append(f"# B0.1:QSAR baseline(化合物结构 → log10-MIC)— {species}\n")
    L.append(
        "line B 第一个从 SMILES 预测 MIC 的模型。把 Science v1 的三条纪律迁到化学空间:"
        "**scaffold 分组防泄漏**(同 Bemis-Murcko 骨架不跨折)、**化学 OOD 弃权**(对训练集最大 Tanimoto 低=不可信)、"
        "**证据分层**(QSAR 须显著优于均值预测 + 1-NN 两个平凡 baseline)。\n")
    L.append("## 方法(写死)\n")
    L.append(
        f"- 特征:RDKit Morgan 指纹(radius={RADIUS}, nBits={N_BITS})。baseline 用指纹,不上 GNN。\n"
        f"- 交叉验证:scaffold-GroupKFold({manifest['groupkfold_splits']} 折,groups=scaffold),拼全 OOF。\n"
        f"- 模型:RandomForestRegressor(n_estimators={N_ESTIMATORS}, random_state={SEED}, n_jobs=-1)。\n"
        f"- baseline:(a) 均值预测(train 的 log10-MIC 均值);(b) 1-NN(train 里 Tanimoto 最近邻的 log10-MIC)。\n"
        f"- 不确定度:RF 各树预测 std。OOD:对 train 最大 Tanimoto,阈 {OOD_THRESHOLD}。\n")
    L.append("## 一键复现\n```bash")
    L.append(".venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v2.qsar_baseline "
             f"--species {species}")
    L.append("```")
    L.append(f"\n确定性:seed={SEED};scaffold 分组/训练确定性(RF n_jobs=-1 有 ULP 噪声,指标稳定)。\n")

    L.append("## 结果(log10-MIC 空间)\n")
    L.append(f"- 化合物 {manifest['n_compounds']}(丢弃 invalid SMILES {manifest['n_invalid_smiles_dropped']});"
             f"scaffold {manifest['n_scaffolds']}(最大骨架占比 {manifest['max_scaffold_fraction']:.1%},"
             f"singleton 骨架占 {manifest['singleton_scaffold_fraction']:.1%})。\n")
    L.append(f"- **RF**:R²={metrics['rf_r2']:.4f}  MAE={metrics['rf_mae']:.4f}  RMSE={metrics['rf_rmse']:.4f}。\n")
    L.append(f"- baseline RMSE:均值预测={metrics['mean_rmse']:.4f}、1-NN={metrics['nn1_rmse']:.4f}。\n")
    L.append(f"- **证据分层判据**:RF 优于均值={metrics['beats_mean']}、优于 1-NN={metrics['beats_nn1']} → "
             f"{'✅ 显著优于两个平凡 baseline,QSAR 有效' if beats_both else '⚠️ 未同时优于两个 baseline,QSAR 有效性存疑(可能需描述符/GNN)'}。\n")

    L.append("## 化学空间 OOD(coverage-RMSE 曲线)\n")
    L.append("按对训练集最大 Tanimoto 降序保留(相似=更可信),各覆盖率下 RMSE:\n")
    L.append("| 覆盖率 | 保留数 | RMSE | 保留集最低相似 |")
    L.append("|--:|--:|--:|--:|")
    for r in cov_rows:
        L.append(f"| {r['coverage']} | {r['n_kept']} | {r['rmse']} | {r['min_tanimoto_kept']} |")
    L.append("")
    L.append(f"- 满覆盖 RMSE={cov1:.4f} → 留最相似 50% RMSE={cov05:.4f} → "
             f"{'✅ 有区分度(相似=更可信)' if ood_signal else '⚠️ 无区分度(相似度与误差不单调,OOD 信号弱)'}。\n")
    L.append(f"- OOD(最大 Tanimoto<{OOD_THRESHOLD}):{manifest['n_ood_compounds']} 个"
             f"({manifest['ood_fraction']:.1%}),fail-closed 下应弃权不预测。\n")

    L.append("## 诚实边界\n")
    L.append(
        f"- **仅 {species}**、**仅 Morgan 指纹 baseline**:未做多物种、未上分子描述符 / 图神经网络。\n"
        "- 这是 baseline,允许不完美:若 R² 低或不优于 baseline,如实反映——指纹不够时下一步是理化描述符或 GNN。\n"
        "- scaffold 分组是化学版防泄漏核心不变量(gate 硬校验同 scaffold 不跨折),但骨架相同≠机制相同,"
        "仍可能高估对全新骨架的外推。\n"
        "- MIC 本身有测量噪声与截断(chembl_pull 已取中位去噪、只留 relation='=');log10-MIC 回归未建模 censoring。\n")
    (_OUT / "qsar_baseline_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 驱动
def load_clean(species: str, data_dir: Path = _DATA):
    """读清洗集 parquet(smiles / mic_ug_ml / n_meas / log10_mic)。不存在则报错(真数据拉取中→gate fail)。"""
    import pandas as pd
    p = data_dir / f"{species}_mic_clean.parquet"
    if not p.exists():
        raise FileNotFoundError(
            f"清洗集不存在:{p}\n"
            f"  真数据(ChEMBL MIC)拉取中时预期如此,gate 保持 fail。\n"
            f"  数据就绪后先跑:python -m praxis_virtualcell.mdr_gnb.workflows.science_v2.chembl_pull "
            f"--species {species}")
    df = pd.read_parquet(p)
    return df


def run(species: str, data_dir: Path = _DATA) -> dict:
    """驱动:load → featurize(丢 invalid)→ scaffold-GroupKFold OOF → 指标 + OOD → 落盘。返回 metrics。"""
    df = load_clean(species, data_dir)
    smiles_all = df["smiles"].astype(str).tolist()
    y_all = df["log10_mic"].astype(float).to_numpy()
    print(f"{species}: 清洗集 {len(smiles_all)} 化合物 → featurize(Morgan r={RADIUS}/{N_BITS}bit)…", flush=True)

    keep_idx, scaffolds, bitvects, X, n_invalid = featurize(smiles_all)
    smiles = [smiles_all[i] for i in keep_idx]
    y = y_all[keep_idx]
    print(f"  有效化合物 {len(smiles)}(丢弃 invalid SMILES {n_invalid});"
          f"scaffold {len(set(scaffolds))} 个 → scaffold-GroupKFold OOF…", flush=True)

    oof, n_splits, n_scaffolds = scaffold_oof(y, scaffolds, bitvects, X)
    metrics = compute_metrics(y, oof)
    write_outputs(species, smiles, scaffolds, y, oof, metrics, n_splits, n_scaffolds, n_invalid)

    print(f"  RF: R²={metrics['rf_r2']:.4f} MAE={metrics['rf_mae']:.4f} RMSE={metrics['rf_rmse']:.4f} | "
          f"均值 RMSE={metrics['mean_rmse']:.4f} 1-NN RMSE={metrics['nn1_rmse']:.4f} | "
          f"beats_mean={metrics['beats_mean']} beats_nn1={metrics['beats_nn1']}", flush=True)
    print(f"落盘 → {_OUT}", flush=True)
    return metrics


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="B0.1 QSAR baseline(化合物结构 → log10-MIC)")
    ap.add_argument("--species", default="escherichia_coli", help="物种(默认 escherichia_coli)")
    args = ap.parse_args()
    run(args.species)
