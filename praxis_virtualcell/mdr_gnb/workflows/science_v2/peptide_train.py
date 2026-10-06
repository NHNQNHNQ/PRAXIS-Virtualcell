"""B5-肽:把 B5 baseline 验证过的肽 QSAR(理化+组成+RF)固化成可加载 peptide_activity artifact。

B5 baseline(peptide_baseline.py)做的是序列相似度连通分量 GroupKFold OOF 评估(R²=0.29 优于均值/1-NN),
不产可部署模型。本脚本在**全部**清洗集上训一个 PeptideActivityModel(RF)+ 存训练序列 k-mer 集(供
序列 OOD),落 data/mdr_gnb/models/<species>/peptide_activity__mic.joblib(gitignore),供
default_registry._peptide_activity_predict 惰性加载,走通 run_mdr_query 全管线。

方法与 B5 baseline 一致(peptide_vector + RF n_estimators=300 + 序列 k-mer OOD 阈 0.3)——不改判据,只固化。
诚实边界:全量训练无 holdout(评估靠 baseline 的序列相似度 OOF);artifact 仅作已验证方法的部署封装。

输入:data/mdr_gnb/raw/peptide_activity/<species>_peptide_mic_clean.parquet(dbaasp_pull 产)。
用法:.venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v2.peptide_train --species "Escherichia coli"
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
_DATA = _ROOT / "data" / "mdr_gnb" / "raw" / "peptide_activity"
_MODELS = _ROOT / "data" / "mdr_gnb" / "models"

N_ESTIMATORS = 300
OOD_THRESHOLD = 0.3
SEED = 0


def train(species: str, data_dir: Path = _DATA, models_root: Path = _MODELS) -> dict:
    """训 PeptideActivityModel 并落 artifact + provenance;返回训练摘要。"""
    import pandas as pd

    from praxis_virtualcell.mdr_gnb.predictors.peptide_activity_model import PeptideActivityModel

    safe = species.lower().replace(" ", "_")
    p = data_dir / f"{safe}_peptide_mic_clean.parquet"
    if not p.exists():
        raise FileNotFoundError(
            f"清洗集不存在:{p}\n先跑 dbaasp_pull.py 拉取并清洗 {species} 的 DBAASP 肽 MIC。")
    df = pd.read_parquet(p)
    seqs = df["sequence"].astype(str).tolist()
    y = df["log10_mic"].astype(float).tolist()
    print(f"{species}: 清洗集 {len(seqs)} 肽 → 训 RF(理化+组成特征, n_estimators={N_ESTIMATORS})…",
          flush=True)

    model = PeptideActivityModel(ood_threshold=OOD_THRESHOLD, n_estimators=N_ESTIMATORS,
                                 random_state=SEED)
    model.fit(seqs, y)

    out = models_root / safe / "peptide_activity__mic.joblib"
    model.save(out)
    summary = {
        "species": species,
        "n_input": len(seqs),
        "train_size": model.train_size,
        "n_invalid_dropped": model.n_invalid_dropped,
        "n_estimators": N_ESTIMATORS, "ood_threshold": OOD_THRESHOLD, "seed": SEED,
        "artifact": str(out.relative_to(_ROOT)),
        "method": "B5 验证方法(理化+组成+RF,序列相似度 OOF R²=0.29)的全量部署封装,无 holdout",
    }
    prov = out.parent / "peptide_activity_provenance.json"
    prov.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    print(f"  train_size={model.train_size}(丢弃 invalid {model.n_invalid_dropped});"
          f"落 artifact → {out}", flush=True)
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="B5 训练 peptide_activity artifact(肽序列→活性 QSAR)")
    ap.add_argument("--species", default="Escherichia coli")
    args = ap.parse_args()
    train(args.species)
