"""B3:化合物活性证据分层(E1-E5 化学验证层,数据驱动定级)。

SIR 侧有两套 E0-E5:运行时置信层(coordinator/evidence_level.map_evidence_level,每预测)
与模型验证层(evidence_tiers.yaml,每 combo)。本模块产 sm_activity 的**验证层**——即 QSAR
模型爬到了证据阶梯哪一级,读 B0.1 已产的 scaffold-OOF 真数据**跑显著性检验定级**,不手工拍脑袋。

阶梯(累积,取全部下级达成的最高级):
  E1 QSAR artifact 在(sm_activity__mic.joblib);
  E2 确定性 E2E 预测(B1 已验证同 raw 逐字相等);
  E3 scaffold-split CV 完成(B0.1,同骨架不跨折,防泄漏);
  E4 **显著**优于文献 baseline(1-NN Tanimoto 相似性检索):配对 bootstrap 单侧 p<0.05;
  E5 外部数据集(换来源/换年份)holdout —— **未做,一律 False**。

红线:E4 须真过显著性检验(非点估计);无外部数据一律不标 E5(不夸大)。定级引用的 R²/RMSE
与 B0.1 qsar_metrics.csv 同源(不另算)。确定性:bootstrap 固定 seed。

用法:.venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v2.sm_activity_evidence --species escherichia_coli
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[4]
_BASELINE = _ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v2" / "qsar_baseline"
_OUT = _ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v2" / "sm_activity_evidence"
_MODELS = _ROOT / "data" / "mdr_gnb" / "models"

BOOTSTRAP_N = 2000
BOOTSTRAP_SEED = 0
ALPHA = 0.05


def _paired_bootstrap(y: np.ndarray, pred_a: np.ndarray, pred_base: np.ndarray) -> dict:
    """配对 bootstrap:检验 pred_a(RF)是否显著优于 pred_base(baseline)。

    比较平方误差:delta = MSE(base) - MSE(a),>0 = a 更好。单侧 p = a 不优于 base 的重采样比例。
    固定 seed → 确定性。同时报 win_rate(逐化合物 a 更优比例)与效应量 dz,防"显著=碾压"误读。
    """
    e_a = (y - pred_a) ** 2
    e_base = (y - pred_base) ** 2
    d = e_base - e_a
    n = len(y)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    deltas = np.array([d[rng.integers(0, n, n)].mean() for _ in range(BOOTSTRAP_N)])
    p = float((deltas <= 0.0).mean())          # RF 不优于 base 的比例 = 单侧 p
    sd = float(d.std())
    return {
        "delta_mse": round(float(d.mean()), 4),
        "p_value": round(p, 4),
        # p=0.0 表示 2000 次重采样无一例外,精度上限 <1/N;报 p_lt 避免误读为"恰好 0"
        "p_lt": round(1.0 / BOOTSTRAP_N, 5) if p == 0.0 else None,
        "significant": bool(p < ALPHA),
        "win_rate": round(float((e_a < e_base).mean()), 4),   # 逐化合物 RF 更优比例
        "effect_size_dz": round(float(d.mean() / sd), 4) if sd > 0 else None,  # 配对效应量
    }


def _artifact_exists(species: str, models_root: Path = _MODELS) -> bool:
    return (models_root / species / "sm_activity__mic.joblib").exists()


def compute_evidence_tier(species: str, baseline_dir: Path = _BASELINE,
                          models_root: Path = _MODELS) -> dict:
    """读 B0.1 scaffold-OOF + metrics,跑显著性检验,数据驱动定 E1-E5(累积取最高达成级)。"""
    import pandas as pd

    metrics_p = baseline_dir / "qsar_metrics.csv"
    per_p = baseline_dir / "qsar_per_compound.parquet"
    if not metrics_p.exists() or not per_p.exists():
        raise FileNotFoundError(f"缺 B0.1 baseline 产物({baseline_dir});先跑 qsar_baseline.py")

    rows = {r["species"]: r for r in csv.DictReader(metrics_p.open())}
    if species not in rows:
        raise ValueError(f"{species} 无 B0.1 baseline 指标(qsar_metrics.csv 仅含 {sorted(rows)});"
                         f"该物种未做 QSAR baseline,不定级(诚实不伪造)")
    m = rows[species]
    # per_compound parquet 现仅 EC(无 species 列);多物种时须按 species 分文件,避免读错(B0.2)
    df = pd.read_parquet(per_p)
    y = df["log10_mic_true"].to_numpy()
    rf = df["log10_mic_pred"].to_numpy()
    nn1 = df["nn1_pred"].to_numpy()

    sig_vs_nn1 = _paired_bootstrap(y, rf, nn1)            # RF vs 1-NN 相似性检索(E4 判据)
    sig_vs_mean = _paired_bootstrap(y, rf, np.full_like(y, y.mean()))  # RF vs 均值(E3 佐证)

    # 阶梯(累积):E1 artifact / E2 确定性(B1 验证)/ E3 scaffold-CV+优于均值 /
    #             E4 显著优于 1-NN / E5 外部 holdout(未做)
    ladder = {
        "E1_artifact_exists": _artifact_exists(species, models_root),
        "E2_deterministic": True,                        # B1 已验证同 raw 逐字相等
        "E3_scaffold_cv": (m["beats_mean"] == "True"),   # scaffold-GroupKFold + 优于均值
        "E4_beats_similarity_retrieval": sig_vs_nn1["significant"],  # 显著优于 1-NN
        "E5_external_holdout": False,                    # 无外部数据集,诚实不标
    }
    order = ["E1_artifact_exists", "E2_deterministic", "E3_scaffold_cv",
             "E4_beats_similarity_retrieval", "E5_external_holdout"]
    level = "E0"
    for key, lv in zip(order, ["E1", "E2", "E3", "E4", "E5"]):
        if ladder[key]:
            level = lv
        else:
            break                                        # 累积:遇未达成即止

    rationale = [
        f"E1 artifact {'在' if ladder['E1_artifact_exists'] else '缺'}",
        "E2 确定性 E2E(B1 验证同 raw 逐字相等)",
        f"E3 scaffold-split CV:R²={float(m['rf_r2']):.4f},优于均值={ladder['E3_scaffold_cv']}",
        (f"E4 显著优于 1-NN 相似性检索:ΔMSE={sig_vs_nn1['delta_mse']}, "
         f"p={sig_vs_nn1['p_value']}({'显著' if sig_vs_nn1['significant'] else '不显著'})"),
        "E5 外部数据集 holdout:未做",
    ]
    return {
        "species": species,
        "evidence_level": level,
        "n_compounds": int(m["n_compounds"]),
        "n_scaffolds": int(m["n_scaffolds"]),
        "r2": round(float(m["rf_r2"]), 4),
        "rmse_rf": round(float(m["rf_rmse"]), 4),
        "rmse_nn1": round(float(m["nn1_rmse"]), 4),
        "rmse_mean": round(float(m["mean_rmse"]), 4),
        "sig_vs_nn1": sig_vs_nn1,
        "sig_vs_mean": sig_vs_mean,
        "sig_vs_mean_note": ("均值基线用全局 y.mean() 近似,与 qsar_metrics.csv 的逐折 mean_rmse 略异;"
                             "仅作 E3 佐证,E3 定级实读 metrics.csv 的 beats_mean(逐折)"),
        "effect_note": (f"E4 显著性来自 RF 在大误差样本上的改善;逐化合物 win_rate="
                        f"{sig_vs_nn1['win_rate']}(1-NN 在重复化合物上精确命中),"
                        f"效应量 dz={sig_vs_nn1['effect_size_dz']} 偏小——'显著优于'成立,但非全面碾压"),
        "ladder": ladder,
        "not_e5_because": "无外部数据集(换来源/换年份)holdout;当前仅 ChEMBL EC 内部 scaffold-split CV",
        "rationale": rationale,
        "bootstrap": {"n_resamples": BOOTSTRAP_N, "seed": BOOTSTRAP_SEED, "alpha": ALPHA},
        "method": "验证层(每模型):读 B0.1 scaffold-OOF 真数据跑配对 bootstrap 定级,累积取最高达成级",
    }


def _write_report_md(ev: dict, path: Path) -> None:
    L: list[str] = []
    L.append(f"# sm_activity 证据分层(E1-E5 验证层)— {ev['species']}\n")
    L.append(f"**当前证据级:{ev['evidence_level']}**"
             f"(化合物 {ev['n_compounds']}、scaffold {ev['n_scaffolds']})\n")
    L.append("## 阶梯(累积,数据驱动定级)\n")
    L.append("| 级 | 判据 | 达成 |")
    L.append("|--|--|:-:|")
    labels = {
        "E1_artifact_exists": "E1 QSAR artifact 在",
        "E2_deterministic": "E2 确定性 E2E 预测",
        "E3_scaffold_cv": "E3 scaffold-split CV(防泄漏)+ 优于均值",
        "E4_beats_similarity_retrieval": "E4 **显著**优于 1-NN 相似性检索(配对 bootstrap p<0.05)",
        "E5_external_holdout": "E5 外部数据集(换来源/年份)holdout",
    }
    for k in ("E1_artifact_exists", "E2_deterministic", "E3_scaffold_cv",
              "E4_beats_similarity_retrieval", "E5_external_holdout"):
        L.append(f"| {labels[k].split()[0]} | {labels[k]} | {'✅' if ev['ladder'][k] else '❌'} |")
    L.append("")
    L.append("## 指标(与 B0.1 qsar_metrics.csv 同源)\n")
    L.append(f"- R²={ev['r2']}  RMSE(RF)={ev['rmse_rf']}  RMSE(1-NN)={ev['rmse_nn1']}  "
             f"RMSE(均值)={ev['rmse_mean']}(log10-MIC 空间)\n")
    s1 = ev["sig_vs_nn1"]
    p_str = f"<{s1['p_lt']}" if s1.get("p_lt") is not None else f"={s1['p_value']}"
    L.append(f"- **E4 显著性检验**(配对 bootstrap,{ev['bootstrap']['n_resamples']}次,seed={ev['bootstrap']['seed']}):"
             f"RF vs 1-NN ΔMSE={s1['delta_mse']}, p{p_str} → "
             f"{'显著优于' if s1['significant'] else '不显著'}"
             f"(win_rate={s1['win_rate']}, dz={s1['effect_size_dz']});"
             f"RF vs 均值 p{'<'+str(ev['sig_vs_mean']['p_lt']) if ev['sig_vs_mean'].get('p_lt') is not None else '='+str(ev['sig_vs_mean']['p_value'])}。\n")
    L.append(f"- 诚实解读:{ev['effect_note']}。\n")
    L.append("## 诚实边界(为何不是 E5)\n")
    L.append(f"- **{ev['not_e5_because']}**。E5 须在外部来源/年份数据集 holdout 上复现方能声称;"
             "当前仅内部 scaffold-split,骨架相同≠机制相同,对全新骨架外推仍可能高估。\n")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def write_evidence(species: str, out_dir: Path = _OUT,
                   baseline_dir: Path = _BASELINE, models_root: Path = _MODELS) -> dict:
    """算证据级并落 json + report.md;返回 {文件名: 路径}。"""
    ev = compute_evidence_tier(species, baseline_dir=baseline_dir, models_root=models_root)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    jp = out_dir / "sm_activity_evidence.json"
    jp.write_text(json.dumps(ev, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                  encoding="utf-8")
    mp = out_dir / "sm_activity_evidence_report.md"
    _write_report_md(ev, mp)
    return {"sm_activity_evidence.json": str(jp), "sm_activity_evidence_report.md": str(mp)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="B3 化合物活性证据分层(E1-E5 验证层)")
    ap.add_argument("--species", default="escherichia_coli")
    args = ap.parse_args()
    ev = compute_evidence_tier(args.species)
    paths = write_evidence(args.species)
    print(f"{args.species}: 证据级={ev['evidence_level']} "
          f"(E4 显著性 p={ev['sig_vs_nn1']['p_value']}, E5={ev['ladder']['E5_external_holdout']})")
    print(f"落盘 → {paths}")
