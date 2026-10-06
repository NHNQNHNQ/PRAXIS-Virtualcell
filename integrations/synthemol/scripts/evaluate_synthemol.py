"""Frozen, retrospective validation of the published SyntheMol activity models."""
import argparse
from functools import lru_cache
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import AllChem
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.Chem.Scaffolds import MurckoScaffold
from scipy.stats import spearmanr
from sklearn.metrics import average_precision_score, roc_auc_score

RDLogger.DisableLog("rdApp.warning")


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


@lru_cache(maxsize=None)
def identity(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None or not any(a.GetAtomicNum() == 6 for a in mol.GetAtoms()):
        return ("", "", "")
    # Features retain the full tested SMILES. These keys are for exclusion only.
    parent = max(Chem.GetMolFrags(mol, asMols=True), key=lambda m: m.GetNumHeavyAtoms())
    parent = rdMolStandardize.Uncharger().uncharge(parent)
    key = Chem.MolToSmiles(parent, isomericSmiles=False)
    connectivity = Chem.MolToInchiKey(parent).split("-")[0]
    scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=parent, includeChirality=False) or "ACYCLIC"
    return key, connectivity, scaffold


def identity_frame(smiles):
    return pd.DataFrame([identity(str(s)) for s in smiles], columns=["parent", "connectivity", "audit_scaffold"])


def mic_label(lower, upper, lower_closed, cutoff):
    """Classify only when the whole measured interval is on one side."""
    if np.isfinite(upper) and upper <= cutoff:
        return 1.0
    if np.isfinite(lower) and (lower > cutoff or (lower == cutoff and not lower_closed)):
        return 0.0
    return np.nan


def prepare(project, output, generator_root, data_root, prediction_root, seeds):
    output.mkdir(parents=True, exist_ok=False)
    base = generator_root
    source = base / "assets/Data/1_training_data"
    protocol = dict(
        author_models=["antibiotic_chemprop", "antibiotic_chemprop_rdkit", "antibiotic_random_forest"],
        weights="published fixed weights; no fitting or selection on evaluation labels",
        exposure_reference=["antibiotics.csv", "library_1.csv", "library_2.csv", "library_3.csv"],
        overlap="exclude matching uncharged largest-fragment stereo-free parent OR InChI connectivity; also raw SMILES and ChEMBL group closure",
        scaffold="Murcko scaffold without chirality; all acyclic structures form one conservative group",
        screen_endpoint="Mean/Mean_Growth < 0.2 at 50 uM, ATCC17978, LB; Activity columns are predictions and never labels",
        mic_endpoint="MIC <= 8 ug/mL exploratory research cutoff; 4 and 16 sensitivity analyses; not clinical breakpoints",
        mic_censoring="unknown if the interval crosses the cutoff; no imputation of censored values",
        comparisons="all author-unseen compounds; stricter author-unseen scaffolds; project frozen compound/scaffold/study test predictions",
        primary_metrics=["parent-weighted ROC-AUC", "parent-weighted average precision", "weighted positive prevalence"],
        bootstrap="200 parent-cluster and 200 study-cluster resamples, seed 17; exploratory intervals",
        limitations=["MIC is a different endpoint from the authors' inhibition labels",
                     "Retrospective benchmark; author-unseen identity is not proof of an independent laboratory",
                     "SD3 was selected by a prior model and is reported separately",
                     "No test-driven threshold, hyperparameter, or checkpoint adjustment"],
        baseline="fixed 5-nearest-neighbor mean training label using 2048-bit Morgan radius 2, no chirality",
        generation_seed=17, project_mic_seeds=list(seeds))
    dump(output / "protocol.json", protocol)
    training = pd.read_csv(source / "antibiotics.csv")
    exposure = pd.concat([pd.read_csv(source / name)[["smiles"]].assign(source=name)
                         for name in protocol["exposure_reference"]], ignore_index=True)
    unique = exposure.drop_duplicates("smiles").reset_index(drop=True)
    ref_keys = identity_frame(unique.smiles)
    reference = pd.concat([unique, ref_keys], axis=1)
    reference.to_csv(output / "author_exposure.csv", index=False)
    parents = set(reference.parent) - {""}
    connectivity = set(reference.connectivity) - {""}
    scaffolds = set(reference.audit_scaffold) - {""}
    raw_seen = set(reference.smiles)
    mic = pd.read_csv(data_root / "curated/mic_measurements.csv", dtype={"record_id": str})
    assert mic.record_id.is_unique and mic.unit.eq("ug/mL").all()
    mic["mic_record_id"] = mic.record_id
    mic["record_id"] = "mic:" + mic.record_id
    mic["cohort"] = "MIC"
    mic["source_sheet"] = "MIC"
    mic["mean_growth"] = np.nan
    for cutoff in (4, 8, 16):
        mic[f"label_{cutoff}"] = [mic_label(lo, hi, str(closed).lower() == "true", math.log2(cutoff))
            for lo, hi, closed in zip(mic.lower_log2, mic.upper_log2, mic.lower_closed)]
    mic["label"] = mic.label_8
    screen = pd.read_csv(data_root / "curated/abaucin_observed_growth.csv")
    screen["cohort"] = "screen_50uM"
    screen["assay"] = screen.source_sheet
    records = pd.concat([mic, screen], ignore_index=True)
    keys = identity_frame(records.smiles)
    records = pd.concat([records, keys], axis=1)
    records["seen_author"] = (records.parent.isin(parents) | records.connectivity.isin(connectivity)
                              | records.smiles.isin(raw_seen))
    seen_groups = set(records.loc[records.seen_author & records.cohort.eq("MIC"), "compound_group"].dropna())
    records.loc[records.compound_group.isin(seen_groups), "seen_author"] = True
    records["unseen_scaffold"] = ~records.audit_scaffold.isin(scaffolds) & records.parent.ne("")
    records["eligibility"] = np.select([records.parent.eq(""), records.seen_author],
                                        ["invalid_or_nonorganic_structure", "author_seen"], default="eligible")
    # No labels or experimental values are passed into inference.
    infer = records.loc[records.eligibility.eq("eligible"), ["smiles"]].drop_duplicates().reset_index(drop=True)
    infer.insert(0, "inference_id", np.arange(len(infer)))
    infer = pd.concat([infer, identity_frame(infer.smiles)], axis=1)
    train_fps = [AllChem.GetMorganFingerprintAsBitVect(Chem.MolFromSmiles(s), 2, nBits=2048)
                 for s in training.smiles]
    train_labels = training.antibiotic_activity.to_numpy(float)
    similarities, nn_scores = [], []
    for i, s in enumerate(infer.smiles):
        fp = AllChem.GetMorganFingerprintAsBitVect(Chem.MolFromSmiles(s), 2, nBits=2048)
        sim = np.array(DataStructs.BulkTanimotoSimilarity(fp, train_fps))
        idx = np.argsort(-sim, kind="stable")[:5]
        similarities.append(float(sim.max()))
        nn_scores.append(float(train_labels[idx].mean()))
        if i % 1000 == 0:
            print(f"Overlap/nearest-neighbor audit: {i}/{len(infer)}", flush=True)
    infer["nearest_author_tanimoto"] = similarities
    infer["knn5_score"] = nn_scores
    infer.to_csv(output / "inference_input.csv", index=False)
    records.to_csv(output / "evaluation_records.csv", index=False)
    counts = records.groupby(["cohort", "source_sheet", "eligibility"], dropna=False).agg(
        rows=("record_id", "size"), parents=("parent", "nunique"), positives=("label", "sum"))
    counts.to_csv(output / "coverage.csv")
    summary = dict(author_training_rows=len(training), reference_raw_rows=len(exposure),
                   reference_unique_smiles=len(reference), reference_parents=len(parents),
                   reference_invalid_or_nonorganic=int(reference.parent.eq("").sum()),
                   project_mic_rows=len(mic), screen_rows=len(screen), inference_unique_smiles=len(infer),
                   eligible_rows=int(records.eligibility.eq("eligible").sum()),
                   eligible_parents=records.loc[records.eligibility.eq("eligible"), "parent"].nunique())
    dump(output / "coverage.json", summary)
    print(json.dumps(summary), flush=True)
    print(counts.to_string(), flush=True)


def predict(project, output, generator_root, data_root, prediction_root, seeds):
    import torch
    from chemfunc import compute_fingerprint
    from synthemol.models import chemprop_load, sklearn_load, sklearn_predict
    sys.path.insert(0, str(generator_root / "code/scripts/models"))
    from chemprop_models import chemprop_predict
    torch.set_num_threads(2)
    torch.manual_seed(17)
    torch.use_deterministic_algorithms(True)
    infer = pd.read_csv(output / "inference_input.csv")
    smiles = infer.smiles.tolist()
    fps_path = output / "rdkit_features.npy"
    if fps_path.exists():
        features = np.load(fps_path, allow_pickle=False)
    else:
        features = np.stack([compute_fingerprint(s, fingerprint_type="rdkit") for s in smiles])
        np.save(fps_path, features)
    assert features.shape == (len(smiles), 200) and np.isfinite(features).all()
    output_scores = infer.copy()
    replay = {}
    for name in ("antibiotic_chemprop", "antibiotic_chemprop_rdkit", "antibiotic_random_forest"):
        scores_path = output / f"{name}_members.npy"
        base = generator_root / "assets/Models" / name
        is_rf = name.endswith("random_forest")
        paths = sorted(base.glob("*.pkl" if is_rf else "*.pt"))
        assert len(paths) == 10
        values = []
        for index, path in enumerate(paths):
            print(f"Predicting {name}: member {index+1}/10", flush=True)
            if is_rf:
                model = sklearn_load(path)
                model.n_jobs = 2
                score = sklearn_predict(model, features)
                check = sklearn_predict(sklearn_load(path), features[:4])
            else:
                model = chemprop_load(path)
                feats = features if name.endswith("rdkit") else None
                with torch.inference_mode():
                    score = chemprop_predict(model, smiles, fingerprints=feats)
                    check = chemprop_predict(chemprop_load(path), smiles[:4],
                                             fingerprints=feats[:4] if feats is not None else None)
            assert np.allclose(score[:4], check, atol=1e-6, rtol=1e-6)
            assert np.isfinite(score).all() and ((score >= 0) & (score <= 1)).all()
            values.append(score)
        values = np.stack(values)
        np.save(scores_path, values)
        output_scores[name] = values.mean(axis=0)
        output_scores[name + "_ensemble_std"] = values.std(axis=0)
        replay[name] = dict(members=10, replay_passed=True, rows=len(smiles))
        output_scores.to_csv(output / "predictions.csv", index=False)
    dump(output / "inference_replay.json", replay)


def weighted_metrics(df, score_name, bootstrap=False):
    data = df.loc[df.label.notna() & df[score_name].notna()].copy()
    n = len(data)
    result = dict(rows=n, parents=data.parent.nunique(), studies=data.study.nunique())
    if n == 0 or data.label.nunique() < 2:
        return dict(result, status="not_evaluable_two_classes_required")
    y = data.label.to_numpy(int)
    scores = data[score_name].to_numpy(float)
    weights = (1 / data.groupby("parent").parent.transform("size")).to_numpy(float)
    auc = roc_auc_score(y, scores, sample_weight=weights)
    ap = average_precision_score(y, scores, sample_weight=weights)
    prevalence = np.average(y, weights=weights)
    result.update(status="evaluated", positives=int(y.sum()),
                  roc_auc=float(auc), average_precision=float(ap),
                  positive_prevalence=float(prevalence), ap_over_prevalence=float(ap / prevalence))
    exact = data.loc[data.cohort.eq("MIC") & data.censor.eq("exact")]
    if len(exact) >= 3 and exact[score_name].nunique() > 1:
        corr = spearmanr(exact[score_name], -exact.lower_log2).statistic
        result["spearman_vs_negative_log2_mic_rows"] = float(corr) if np.isfinite(corr) else None
    if bootstrap:
        for group in ("parent", "study"):
            labels, groups = pd.factorize(data[group])
            if len(groups) < 2:
                continue
            rng = np.random.default_rng(17)
            estimates = []
            for _ in range(200):
                multiplicity = np.bincount(rng.integers(len(groups), size=len(groups)), minlength=len(groups))
                w = weights * multiplicity[labels]
                if w[y == 0].sum() > 0 and w[y == 1].sum() > 0:
                    estimates.append([roc_auc_score(y, scores, sample_weight=w),
                                      average_precision_score(y, scores, sample_weight=w)])
            if estimates:
                intervals = np.quantile(estimates, [0.025, 0.975], axis=0)
                result[group + "_bootstrap_auc_low"] = float(intervals[0, 0])
                result[group + "_bootstrap_auc_high"] = float(intervals[1, 0])
                result[group + "_bootstrap_ap_low"] = float(intervals[0, 1])
                result[group + "_bootstrap_ap_high"] = float(intervals[1, 1])
    return result


def report(project, output, generator_root, data_root, prediction_root, seeds):
    records = pd.read_csv(output / "evaluation_records.csv", dtype={"mic_record_id": str}).fillna({"parent": ""})
    scores = pd.read_csv(output / "predictions.csv")
    score_cols = ["antibiotic_chemprop", "antibiotic_chemprop_rdkit", "antibiotic_random_forest", "knn5_score"]
    evaluated = records.loc[records.eligibility.eq("eligible")].merge(
        scores[["smiles", "nearest_author_tanimoto"] + score_cols], on="smiles", how="left", validate="many_to_one")
    assert evaluated[score_cols].notna().all().all()
    assert not evaluated.seen_author.any()
    evaluated.to_csv(output / "scored_evaluation_records.csv", index=False)
    rows = []
    for cohort, sub in evaluated.groupby("cohort"):
        subsets = {"all_unseen_parents": sub, "unseen_scaffolds": sub.loc[sub.unseen_scaffold],
                   "nearest_training_tanimoto_le_0.4": sub.loc[sub.nearest_author_tanimoto <= 0.4]}
        if cohort == "screen_50uM":
            subsets.update({f"sheet:{name}": part for name, part in sub.groupby("source_sheet")})
        for subset, part in subsets.items():
            for score in score_cols:
                rows.append(dict(cohort=cohort, subset=subset, score=score, cutoff=8 if cohort == "MIC" else "80pct",
                                 **weighted_metrics(part, score, bootstrap=True)))
        if cohort == "MIC":
            for cutoff in (4, 16):
                part = sub.copy()
                part["label"] = part[f"label_{cutoff}"]
                for score in score_cols:
                    rows.append(dict(cohort=cohort, subset="cutoff_sensitivity", score=score, cutoff=cutoff,
                                     **weighted_metrics(part, score)))
    # Equal evaluation records for pretrained generators and existing project baselines.
    comparisons = []
    mic = evaluated.loc[evaluated.cohort.eq("MIC")].copy()
    for scheme in ("compound", "scaffold", "study"):
        pieces = []
        for seed in seeds:
            pred = pd.read_csv(prediction_root / f"direct_mic_{scheme}_seed{seed}_test.csv", dtype={"record_id": str})
            assert pred.record_id.is_unique
            pieces.append(pred[["record_id", "pred_log2"]].rename(columns={"record_id": "mic_record_id", "pred_log2": f"mu_{seed}"}))
        baseline = pieces[0]
        for part in pieces[1:]:
            baseline = baseline.merge(part, on="mic_record_id", validate="one_to_one")
        baseline["direct_mic_score"] = -baseline[[f"mu_{s}" for s in seeds]].mean(axis=1)
        common = mic.merge(baseline, on="mic_record_id", validate="one_to_one")
        common.to_csv(output / f"common_{scheme}_test.csv", index=False)
        for score in score_cols + ["direct_mic_score"]:
            comparisons.append(dict(split=scheme, score=score, **weighted_metrics(common, score, bootstrap=True)))
    # Within-study checks expose pooled scores that merely separate laboratories.
    studies = []
    for study, part in mic.groupby("study"):
        if part.parent.nunique() >= 10 and part.label.nunique() == 2:
            for score in score_cols:
                studies.append(dict(study=study, score=score, **weighted_metrics(part, score)))
    pd.DataFrame(rows).to_csv(output / "metrics.csv", index=False)
    pd.DataFrame(comparisons).to_csv(output / "baseline_comparison.csv", index=False)
    pd.DataFrame(studies).to_csv(output / "within_study_metrics.csv", index=False)
    dump(output / "status.json", dict(completed=True, training_performed=False, integrated_with_v1=False,
        evaluation_records=len(evaluated), metric_rows=len(rows), comparison_rows=len(comparisons)))
    print(pd.DataFrame(rows)[["cohort", "subset", "score", "rows", "parents", "roc_auc", "average_precision", "positive_prevalence"]].to_string(index=False))
    print(pd.DataFrame(comparisons)[["split", "score", "rows", "parents", "roc_auc", "average_precision", "positive_prevalence"]].to_string(index=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["prepare", "predict", "report"])
    ap.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[3])
    ap.add_argument("--generator-root", type=Path)
    ap.add_argument("--data-root", type=Path)
    ap.add_argument("--prediction-root", type=Path)
    ap.add_argument("--seeds", nargs="+", type=int, default=[17, 42, 314159], help="Frozen 09-23 comparison seeds; use 17 42 2026 only for a separately named 09-13 replay")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    project = args.project.resolve()
    generator_root = (args.generator_root or project / "integrations/synthemol/external/SyntheMol-MCTS").resolve()
    data_root = (args.data_root or project / "data/antibacterial/abaumannii").resolve()
    prediction_root = (args.prediction_root or project / "reports/antibacterial/direct_mic/predictions").resolve()
    if args.stage in ("prepare", "predict") and not (generator_root / "assets").exists():
        raise FileNotFoundError("SyntheMol assets are not bundled; pass --generator-root to a verified existing installation")
    globals()[args.stage](project, args.output.resolve(), generator_root, data_root, prediction_root, args.seeds)


if __name__ == "__main__":
    main()
