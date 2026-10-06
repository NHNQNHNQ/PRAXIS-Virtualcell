"""保真验证(可一键复现):golden 的 amr_profile base 名构造 → 服务端特征向量,
是否与部署模型训练特征化逐位一致。

为什么必须验证:部署 genotype_to_sir(EC/KP)用 augmented_features(gene=/mut=/mech= 机制聚合)
训练;服务端 default_registry._amr_to_X 从 amr_profile(base 名)重建 gene=/mut= 双 token + mech=。
若两者对不齐,T1A 轨A 的 accuracy 就是拿错特征跑出来的、无意义。本脚本对**真实株**逐位比对
两条特征化路径,产出实际逐位相等株数 N(不写死任何数字,N 由脚本真跑得出)。

用法(从仓库根,以 -m 运行本模块):
    python -m praxis_virtualcell.mdr_gnb.workflows.science_v2.validation.verify_amr_fidelity

同一逻辑由 tests/science_v2/validation/test_amr_fidelity.py 断言(n_agree == n_check 且 > 0)。
"""
from __future__ import annotations

import csv

import numpy as np

from praxis_virtualcell.mdr_gnb.predictors.default_registry import (
    _amr_to_X,
    _load_gsir,
    _safe_drug,
)
from praxis_virtualcell.mdr_gnb.predictors.mechanism_features import augmented_features
from praxis_virtualcell.mdr_gnb.workflows.science_v2.validation.build_golden_sir import (
    DATA,
    base_profile,
)

# 固定比对 combo(有本地 tsv + 有部署模型;覆盖 gene=/mut=/mech= 各特征形态)。确定性。
FIDELITY_COMBOS: list[tuple[str, str]] = [
    ("klebsiella_pneumoniae", "meropenem"),
    ("klebsiella_pneumoniae", "ciprofloxacin"),
    ("escherichia_coli", "ceftriaxone"),
    ("escherichia_coli", "gentamicin"),
]


def _train_vector(genostr: str, feature_names: list[str]) -> np.ndarray:
    """训练侧特征化:augmented_features(原始 genostr)→ 按 feature_names one-hot。"""
    idx = {n: i for i, n in enumerate(feature_names)}
    X = np.zeros((1, len(feature_names)), dtype=float)
    for tok in augmented_features(genostr):
        j = idx.get(tok)
        if j is not None:
            X[0, j] = 1.0
    return X


def verify(max_per_combo: int | None = None) -> dict:
    """逐 combo 比对训练侧 vs 服务侧特征向量(真实株)。确定性(按 genome_id 排序)。

    默认 max_per_combo=None → **全量**(不设上限,诚实透出总分母)。每 combo 披露
    n_available(该 combo 去重后真实可比对总数)与 n_checked(实际检查数)—— 本项目
    "安全指标必须透出分母"原则(harness.classification_metrics 同款,别让读者误以为
    抽样数=全部)。设 max_per_combo 时 n_checked=min(n_available, cap)。
    """
    per_combo = []
    n_available = n_checked = n_agree = 0
    for species, drug in FIDELITY_COMBOS:
        clf = _load_gsir(species, _safe_drug(drug))
        if clf is None:
            per_combo.append({"species": species, "drug": drug, "status": "no_model",
                              "n_available": 0, "n_checked": 0, "n_agree": 0})
            continue
        fn = clf.feature_names or []
        p = DATA / "raw" / species / "ncbi_amr_phenotypes.tsv"
        # 去重(genome_id 首次出现),按 genome_id 排序;None=全量,否则取前 max_per_combo
        seen: dict[str, str] = {}
        with p.open(encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                if row["antibiotic"] != drug or row["resistant_phenotype"] not in ("R", "S"):
                    continue
                gid = row["genome_id"]
                if gid not in seen:
                    seen[gid] = row["ncbi_amr_genotypes"]
        avail = len(seen)
        gids = sorted(seen) if max_per_combo is None else sorted(seen)[:max_per_combo]
        c_agree = 0
        for gid in gids:
            genostr = seen[gid]
            x_train = _train_vector(genostr, fn)
            x_serve = _amr_to_X(base_profile(genostr), fn)  # golden 用的同一 base_profile
            c_agree += int(np.array_equal(x_train, x_serve))
        per_combo.append({"species": species, "drug": drug, "status": "ok",
                          "n_available": avail, "n_checked": len(gids), "n_agree": c_agree})
        n_available += avail
        n_checked += len(gids)
        n_agree += c_agree
    return {"combos": FIDELITY_COMBOS, "per_combo": per_combo,
            "n_available": n_available, "n_checked": n_checked, "n_agree": n_agree,
            "all_identical": n_checked > 0 and n_agree == n_checked}


if __name__ == "__main__":
    r = verify()
    for pc in r["per_combo"]:
        print(f"  {pc['species']:24s} {pc['drug']:14s} [{pc['status']}] "
              f"逐位相等 {pc['n_agree']}/{pc['n_checked']}(共可比对 {pc['n_available']})")
    print(f"合计: {r['n_agree']}/{r['n_checked']} 逐位相等(共可比对 {r['n_available']});"
          f"all_identical={r['all_identical']}")
