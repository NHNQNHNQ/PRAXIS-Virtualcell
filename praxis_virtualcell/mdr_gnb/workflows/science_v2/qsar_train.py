"""B1:把 B0.1 验证过的 QSAR(Morgan+RF)固化成可加载 sm_activity artifact。

B0.1(qsar_baseline.py)做的是 scaffold-GroupKFold OOF 评估(证明可预测:R²=0.565 优于均值/1-NN),
不产可部署模型。本脚本在**全部**清洗集上训一个 SmallMoleculeModel(RF)+ 存训练指纹(供化学 OOD),
落 data/mdr_gnb/models/<species>/sm_activity__mic.joblib(joblib gitignore,留本地/53),供
default_registry._sm_activity_predict 惰性加载,走通 run_mdr_query 全管线。

方法与 B0.1 一致(Morgan r=2/2048 + RF n_estimators=300 + OOD 阈 0.3)——不改判据,只固化。
诚实边界:全量训练无 holdout(评估靠 B0.1 的 scaffold-OOF);artifact 仅作**已验证方法的部署封装**。

输入:data/mdr_gnb/raw/compound_activity/<species>_mic_clean.parquet(chembl_pull.py 产出)。
用法:.venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v2.qsar_train --species escherichia_coli
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
_DATA = _ROOT / "data" / "mdr_gnb" / "raw" / "compound_activity"
_MODELS = _ROOT / "data" / "mdr_gnb" / "models"

N_BITS = 2048
RADIUS = 2
N_ESTIMATORS = 300
OOD_THRESHOLD = 0.3
SEED = 0


def train(species: str, data_dir: Path = _DATA, models_root: Path = _MODELS) -> dict:
    """训 SmallMoleculeModel 并落 artifact + provenance;返回训练摘要。"""
    import pandas as pd

    from praxis_virtualcell.mdr_gnb.predictors.small_molecule_model import SmallMoleculeModel

    p = data_dir / f"{species}_mic_clean.parquet"
    if not p.exists():
        raise FileNotFoundError(
            f"清洗集不存在:{p}\n先跑 chembl_pull.py 拉取并清洗 {species} 的 ChEMBL MIC。")
    df = pd.read_parquet(p)
    smiles = df["smiles"].astype(str).tolist()
    y = df["log10_mic"].astype(float).tolist()
    print(f"{species}: 清洗集 {len(smiles)} 化合物 → 训 RF(Morgan r={RADIUS}/{N_BITS}bit, "
          f"n_estimators={N_ESTIMATORS})…", flush=True)

    model = SmallMoleculeModel(n_bits=N_BITS, radius=RADIUS, ood_threshold=OOD_THRESHOLD,
                               n_estimators=N_ESTIMATORS, random_state=SEED)
    model.fit(smiles, y)

    out = models_root / species / "sm_activity__mic.joblib"
    model.save(out)
    summary = {
        "species": species,
        "n_input": len(smiles),
        "train_size": model.train_size,
        "n_invalid_dropped": model.n_invalid_dropped,
        "n_bits": N_BITS, "radius": RADIUS, "n_estimators": N_ESTIMATORS,
        "ood_threshold": OOD_THRESHOLD, "seed": SEED,
        "artifact": str(out.relative_to(_ROOT)),
        "method": "B0.1 验证方法(Morgan+RF,scaffold-OOF R²=0.565)的全量部署封装,无 holdout",
    }
    # provenance(可入库:gitignore 放行 provenance.json)
    prov = out.parent / "sm_activity_provenance.json"
    prov.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    print(f"  train_size={model.train_size}(丢弃 invalid {model.n_invalid_dropped});"
          f"落 artifact → {out}", flush=True)
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="B1 训练 sm_activity artifact(化合物→活性 QSAR)")
    ap.add_argument("--species", default="escherichia_coli")
    args = ap.parse_args()
    train(args.species)
