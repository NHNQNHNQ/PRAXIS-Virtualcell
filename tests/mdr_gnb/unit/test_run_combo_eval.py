"""单 species×drug G2 评估 runner 测试(NCBI-native,fixture,不联网)。"""
import numpy as np

from praxis_virtualcell.mdr_gnb.workflows.run_combo_eval import run_combo_eval
from praxis_virtualcell.mdr_gnb.evaluators.combo_gate import GatePrereg

_PRE = GatePrereg(min_effect_size=0.05, alpha=0.05, min_st_with_R=8, min_strains=50)


def _fixture(n_st=20, per_st=6, seed=0):
    """构造 n_st 个 ST,每 ST per_st 株;含耐药基因 blaTESTCARBA=R,否则 S。
    规则表 meropenem 未收录 blaTESTCARBA → 规则法全判 S(VME 高);ML 能学到 → ML 更优。
    """
    rng = np.random.RandomState(seed)
    rows, st_map = [], {}
    k = 0
    for i in range(n_st):
        st = f"ST{i}"
        for _ in range(per_st):
            gid = f"g{k}"; k += 1
            has = rng.rand() < 0.5
            geno = "blaTESTCARBA,acrB" if has else "acrB"
            rows.append({"genome_id": gid, "antibiotic": "meropenem",
                         "ncbi_amr_genotypes": geno,
                         "resistant_phenotype": "R" if has else "S"})
            st_map[gid] = st
    return rows, st_map


def test_run_combo_eval_end_to_end_structure():
    rows, st_map = _fixture()
    out = run_combo_eval("klebsiella_pneumoniae", "meropenem", rows, st_map,
                         prereg=_PRE, db_version="2025-07-16.1", n_splits=5, seed=0)
    assert out["gate"].status in {"pass", "degrade_classification", "abstain_only", "excluded"}
    assert out["gate"].species == "klebsiella_pneumoniae"
    assert out["n_strains"] == len(rows)
    # 全局 VME/ME 为 0..1 浮点
    assert 0.0 <= out["vme_model"] <= 1.0
    assert 0.0 <= out["vme_rule"] <= 1.0


def test_ml_beats_blind_rule():
    # 规则表未收录 blaTESTCARBA(规则法对 meropenem 全判 S)→ 真R全漏 → rule VME=1.0;
    # ML 能从基因型学到 → ML VME 应显著更低,effect_size 明显为负
    rows, st_map = _fixture(n_st=24, per_st=8, seed=1)
    out = run_combo_eval("klebsiella_pneumoniae", "meropenem", rows, st_map,
                         prereg=_PRE, db_version="2025-07-16.1", n_splits=5, seed=1)
    assert out["vme_rule"] > 0.9        # 规则法几乎全漏真R
    assert out["vme_model"] < out["vme_rule"]
    assert out["effect_size"] < 0       # ML per-ST VME 更低
