"""机制特征重训 EC+KP 的 genotype_to_sir 模型(follow-up:把生产抬到 G2R strong 幅度)。

用 augmented_features(gene=/mut=/mech= 机制聚合)重训并**覆盖**现有 joblib,重写 MANIFEST(新 nfeat)。
之后须 re-run ingest 更新 registry sha256。仅 EC/KP(有本地评估数据);PA/AB/SE 保持基线(无数据)。

红线:确定性(random_state=0);feature_names 自包含随模型存;_amr_to_X 已支持 mech= 推理(向后兼容)。
"""
from __future__ import annotations

import re
from pathlib import Path

from ..predictors.genotype_to_sir import GenotypeToSIR
from ..predictors.mechanism_features import augmented_features
from .build_data_foundation import _modelable_ids, load_inputs_from_disk
from .run_g2r_evidence_sweep import _combo_rows
from .run_g2r_lever_a import build_X, fit_vocab
from .run_g2r_locked import _y

DATA = Path("data/mdr_gnb")
RETRAIN_SPECIES = ("escherichia_coli", "klebsiella_pneumoniae")


def _manifest_drugs(sp: str) -> list[tuple[str, str]]:
    """MANIFEST OK 行 → [(drug, filename)]。"""
    out = []
    for line in (DATA / "models" / sp / "MANIFEST.txt").read_text().splitlines():
        m = re.match(r"OK (.+?): n=\d+ R=\d+ S=\d+ nfeat=\d+ -> (\S+)", line.strip())
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def retrain_species(sp: str) -> list[str]:
    amr, st_map, _ = load_inputs_from_disk(sp, DATA)
    model_dir = DATA / "models" / sp
    ok_lines = []
    for drug, fname in _manifest_drugs(sp):
        rows = _combo_rows(amr, st_map, drug)
        y = _y(rows)
        R, S = int((y == 1).sum()), int((y == 0).sum())
        vocab = fit_vocab(rows, augmented_features)
        X = build_X(rows, vocab, augmented_features)
        clf = GenotypeToSIR(random_state=0, model="rf").fit(X, y)
        clf.feature_names = vocab
        clf.save(model_dir / fname)                    # 覆盖生产 joblib
        ok_lines.append(f"OK {drug}: n={len(rows)} R={R} S={S} nfeat={len(vocab)} -> {fname}")
    # 重写 MANIFEST(机制特征标注)
    header = [f"# {sp} genotype_to_sir artifacts (RandomForest, feature_names 自包含)",
              f"# 机制特征重训(augmented: gene=/mut=/mech= 聚合;carbapenem_R_pathway 等交互)",
              f"# 训练={len(ok_lines)} 药物  seed=0  门槛沿用原 modelable 集"]
    (model_dir / "MANIFEST.txt").write_text("\n".join(header + ok_lines) + "\n", encoding="utf-8")
    return ok_lines


if __name__ == "__main__":
    import os
    os.chdir(Path(__file__).resolve().parents[3])
    for sp in RETRAIN_SPECIES:
        lines = retrain_species(sp)
        print(f"{sp}: 重训 {len(lines)} 个模型(机制特征)")
    print("完成。下一步:re-run ingest 更新 registry sha256。")
