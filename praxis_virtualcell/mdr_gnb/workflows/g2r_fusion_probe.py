"""G2R 探针:复现两锚点 G2 + rule-first 融合(rule=R→R,否则 ML)。
诚实:每折重训(不用生产 joblib),ST 分组,操作点对齐,per-ST VME + 置换检验。
融合 VME 数学上 ≤ 规则法 → 验 EC ceftriaxone 能否从 degrade 拉到 practical/strong-pass。"""
import os, sys, numpy as np
from pathlib import Path
os.chdir(Path(__file__).resolve().parents[3])
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from praxis_virtualcell.mdr_gnb.workflows.build_data_foundation import load_inputs_from_disk, _modelable_ids
from praxis_virtualcell.mdr_gnb.workflows.run_combo_eval import _y, _rule_pred, _me
from praxis_virtualcell.mdr_gnb.evaluators.lineage_split import make_lineage_splits
from praxis_virtualcell.mdr_gnb.evaluators.ast_metrics import compute_ast_metrics
from praxis_virtualcell.mdr_gnb.evaluators.significance import st_level_vme, align_st_vme, paired_permutation_test
from praxis_virtualcell.mdr_gnb.predictors.features import FeatureSpec, build_feature_matrix
from praxis_virtualcell.mdr_gnb.predictors.genotype_to_sir import GenotypeToSIR
from praxis_virtualcell.mdr_gnb.predictors.rule_baseline import RuleBaselineSIR

DB = "2024-01-frozen"
DATA = Path("data/mdr_gnb")

def eval_anchor(species_dir, drug, model="rf", seed=0):
    amr, st_map, _ = load_inputs_from_disk(species_dir, DATA)
    mids = set(_modelable_ids(amr, drug))
    seen, rows = set(), []
    for r in amr:
        if r.get("antibiotic") == drug:
            g = (r.get("genome_id") or "").strip()
            if g in mids and g not in seen:
                seen.add(g); rows.append(r)
    id2row = {(r.get("genome_id") or "").strip(): r for r in rows}
    ids = [(r.get("genome_id") or "").strip() for r in rows]
    rule = RuleBaselineSIR(db_version=DB)
    specs = make_lineage_splits(ids, st_map, n_splits=5)
    oof_st, oof_y, oof_ml, oof_rule, oof_fuse = [], [], [], [], []
    for s in specs:
        tr = [id2row[g] for g in s.train_ids]; te = [id2row[g] for g in s.test_ids]
        fm = build_feature_matrix(tr, st_map); ytr = fm.y_sir
        Xte = FeatureSpec.transform(fm.spec, te); yte = _y(te)
        stte = np.array([st_map.get((r.get("genome_id") or "").strip(), "unknown") for r in te])
        ml = GenotypeToSIR(random_state=seed, model=model).fit(fm.X, ytr)
        p_tr = ml.predict_proba_r(fm.X); p_te = ml.predict_proba_r(Xte)
        target_me = _me(ytr, _rule_pred(rule, drug, tr))
        ths = np.linspace(0.01, 0.99, 99)
        me_tr = np.array([_me(ytr, (p_tr >= t).astype(int)) for t in ths])
        t_star = float(ths[int(np.argmin(np.abs(me_tr - target_me)))])
        ml_pred = (p_te >= t_star).astype(int)
        ru_pred = _rule_pred(rule, drug, te)
        fuse_pred = np.where(ru_pred == 1, 1, ml_pred)   # rule-first 融合
        oof_st.append(stte); oof_y.append(yte)
        oof_ml.append(ml_pred); oof_rule.append(ru_pred); oof_fuse.append(fuse_pred)
    st = np.concatenate(oof_st); y = np.concatenate(oof_y)
    mlp = np.concatenate(oof_ml); rup = np.concatenate(oof_rule); fup = np.concatenate(oof_fuse)

    def per_st_and_p(pred):
        v_p = st_level_vme(st, y, pred); v_r = st_level_vme(st, y, rup)
        keys, mm, rr = align_st_vme(v_p, v_r)
        if len(keys) < 1: return float('nan'), float('nan'), None, 0
        perm = paired_permutation_test(mm, rr, keys, n_perm=10000, seed=seed)
        return float(mm.mean()), float(rr.mean()), perm["p_value"], len(keys)

    ml_vme, ru_vme, ml_p, nst = per_st_and_p(mlp)
    fu_vme, ru_vme2, fu_p, _  = per_st_and_p(fup)
    m_ml = compute_ast_metrics(y, mlp, st); m_ru = compute_ast_metrics(y, rup, st); m_fu = compute_ast_metrics(y, fup, st)
    print(f"\n===== {species_dir} × {drug}  (model={model}, n={len(rows)}, n_ST(R)={nst}) =====")
    print(f"  per-ST VME:  rule={ru_vme:.3f}   ML={ml_vme:.3f} (Δ={ml_vme-ru_vme:+.3f}, p={ml_p:.4f})   "
          f"FUSION={fu_vme:.3f} (Δ={fu_vme-ru_vme:+.3f}, p={fu_p:.4f})")
    print(f"  global ME:   rule={m_ru['me']:.3f}   ML={m_ml['me']:.3f}   FUSION={m_fu['me']:.3f}")
    def verdict(dv, p):
        if dv < 0 and p < 0.05: return "STRONG-pass(显著优于规则)"
        if dv <= 0.001: return "practical-pass(不劣于规则)"
        return "FAIL(劣于规则)"
    print(f"  ML 判定:     {verdict(ml_vme-ru_vme, ml_p)}")
    print(f"  融合判定:    {verdict(fu_vme-ru_vme, fu_p)}")

for sp, dr in [("klebsiella_pneumoniae","meropenem"), ("escherichia_coli","ceftriaxone")]:
    eval_anchor(sp, dr, model="rf")
