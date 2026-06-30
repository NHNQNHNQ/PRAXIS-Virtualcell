# Learned reliability governance: from rule-based to learned, runtime-active selective reliability

*A v0.3 addendum to "A brain-guided multi-agent runtime for trustworthy virtual-cell perturbation prediction" (PRAXIS-VirtualCell v0.2). This addendum extends the v0.2 Results; it does not modify the v0.2 manuscript. Citation footnote numbers below refer to the v0.2 reference list.*

## Scope and reading guide

The v0.2 manuscript established that a governance **runtime** — not a better predictor — is what supplies rejection, abstention, provenance, and auditability for virtual-cell perturbation prediction, and it did so with **rule-based** governance: hard gates that reject unsupported species, empty targets, all-rejected ensembles, and core-predictor failures, plus a disagreement-threshold abstention with a positive risk–coverage curve (v0.2 §3.4). This addendum reports the next step: a **learned** reliability layer that handles the *soft* reliability risk the rules cannot, that is frozen into immutable artifacts and wired into the runtime as the default, and that we evaluate honestly against the rule baseline and several single-signal heuristics.

Three distinctions are load-bearing throughout, and we keep them separate by construction rather than by claim:

1. **Generalization vs. runtime integration.** The learned model's *generalization* is evaluated only by perturbation-level out-of-fold (OOF) cross-validation (§A, R2, R3). The rule-vs-learned runtime comparison (R7) is an **in-sample integration replay** — the frozen model is fit on all 151 ledger entries and the comparison replays those same entries — so we read it strictly as evidence that the learned layer *changes runtime decisions and preserves hard rules and provenance*, **not** as an independent generalization benchmark.
2. **Perturbation-level vs. per-cell.** Every number here is **perturbation-level** selective-reliability behaviour over an evaluation ledger (per-perturbation Δ-Pearson as the reliability target). None of it is the v0.2 headline **per-cell** Δ-Pearson (0.7039). We never claim learned governance improves per-cell prediction accuracy; it improves perturbation-level selective-reliability decisions.
3. **Soft learned governance vs. hard rule gates.** Hard invalidity (unsupported species, empty targets, all predictors rejected, core failure, and — added here — missing/tampered/schema-mismatched artifacts) is governed by rules and fail-closed defaults. The learned layer governs only the *soft* decision (given applicable predictors, is this perturbation reliable enough to answer, downgrade, or abstain). The learned layer never overrides a hard rule.

This is the PRAXIS-VirtualCell governance line in its own terms. A parallel question — whether learned governance generalizes to other agentic settings such as LLM code-gating — is out of scope and not evaluated here (see Discussion).

## A. Evidence stratification (read this first)

To prevent the in-sample integration replay from being mistaken for a generalization result, we label every quantitative claim by the kind of evidence it is:

| Evidence type | What it shows | Headline numbers | How it is produced |
|---|---|---|---|
| **Generalization (OOF/CV)** | The learned model is not just memorizing the training ledger; it ranks unseen-fold perturbations by reliability better than single-signal heuristics. | bad-perturbation AUROC **0.907**; abstention risk–coverage AUC **0.746**; reliability-regression OOF corr **0.701** | Perturbation-level leave-perturbation-out 5-fold CV; each fold's model is fit on training folds only and scores held-out folds (`reliability_model.cv_reliability`). |
| **Runtime integration (in-sample replay)** | After freezing and wiring the model into the runtime, the default mode actually changes soft-risk decisions versus rules, while leaving hard rules and provenance intact. | wrong-accept **0.974 → 0.211**; risk-coverage **0.026 → 0.789**; hard-rule-override **0**; provenance **complete** | The frozen production model (fit on all 151 entries) is replayed over those same 151 entries (`mode_compare.compare`). In-sample by construction. |
| **Safety / provenance** | Learned scoring cannot leak labels, degrades to rules when artifacts are absent/altered, and every decision is traceable to an immutable artifact hash. | leakage assertion; fail-closed fallback on missing/schema/incomplete/tampered artifacts; `artifact_sha256` on every decision | Compile-time feature/label separation; content-hash self-check; fail-closed loader; 7 integration gates. |

Generalization is carried by the OOF rows. The runtime row is an integration test. We do not average across these rows or present the in-sample replay numbers as out-of-sample performance.

## Results

### R1. Rules block hard invalidity, but soft reliability risk needs a learned signal

The rule gates from v0.2 are necessary and we keep them: they catch categorical invalidity (unsupported species, empty targets, all-rejected ensembles, core failure). But they are weak on *soft* risk — a perturbation where the predictors are applicable yet the answer is likely unreliable. The v0.2 abstention used a single hand-set rule (ensemble pairwise-cosine disagreement above a fixed 0.5 threshold).

Two findings motivate learning this soft signal instead of hand-setting it. First, on the M1 evaluation ledger the per-perturbation disagreement score is a genuine, strong predictor of accuracy: corr(disagreement, per-perturbation Δ-Pearson) = **−0.716** (n = 60); the high-disagreement half averages Δ-Pearson **0.571** versus **0.841** for the low-disagreement half — roughly 27 points lower accuracy on the perturbations the predictors disagree on. Second, no single base predictor is best everywhere: across 151 perturbations the most-accurate predictor is the GNN on 75, the linear model on 39, and the latent model on 37. The disagreement signal is real, and reliability is heterogeneous across perturbations — exactly the regime where a learned reliability head can beat a single fixed threshold.

### R2. A learned reliability model beats single-signal heuristics (OOF generalization)

We train a deliberately light reliability model — a pure-Python ridge regressor over three inference-time features (ensemble disagreement, an out-of-distribution flag `seen_in_train`, and a zero-vector-pair count) — to regress the per-perturbation reliability target (Δ-Pearson) and to flag the bottom-quartile "bad" perturbations (bad threshold Δ-Pearson 0.455; 38 bad / 113 good of 151). Evaluation is perturbation-level leave-perturbation-out 5-fold CV with out-of-fold predictions, and is leakage-controlled: the feature extractor asserts at compile time that no label column (Δ-Pearson, per-predictor Δ-Pearson, best-predictor) can enter the feature matrix.

| Bad-perturbation detector (OOF) | AUROC |
|---|---|
| **Learned (disagreement + OOD + zero-pairs)** | **0.907** |
| OOD-only | 0.788 |
| Disagreement-only (the v0.2 signal) | 0.774 |
| Random | 0.479 |

The learned model also regresses the reliability target with OOF corr(predicted, true) = **0.701**. Learning a three-feature combination improves bad-perturbation detection by **+0.13 AUROC** over the strong disagreement-only heuristic that already drove v0.2. Because these are out-of-fold predictions, this is a generalization result, not memorization.

### R3. Learned abstention dominates the rule-based abstain (OOF; upgrades v0.2 Table C)

We convert the OOF reliability predictions into a selective-prediction (abstention) policy and measure risk–coverage — for each ranking signal, abstain on the least-reliable perturbations first and track retained accuracy as coverage falls. v0.2 Table C used disagreement to rank; here learned reliability ranks.

| Abstention ranking signal | Risk–coverage AUC |
|---|---|
| Oracle (true Δ-Pearson; upper bound) | 0.7822 |
| **Learned (reliability OOF)** | **0.7460** |
| OOD-only | 0.7297 |
| Disagreement-only (v0.2) | 0.7196 |
| Random | 0.6595 |

Retained Δ-Pearson at coverage 1.0 / 0.8 / 0.6 is 0.657 / 0.733 / 0.796 for learned versus 0.657 / 0.713 / 0.749 for disagreement-only: at 60% coverage the learned policy retains **+0.047** Δ-Pearson over the v0.2 rule, capturing roughly half of the rule→oracle gap. The selective-reliability decision is now learned and strictly better than the v0.2 hand-set rule, while remaining well below the oracle ceiling (which we report to avoid over-claiming).

### R4. Adding prediction-magnitude/uncertainty features does not help — a negative result

Before committing the model we tested whether richer inference features help. We computed per-predictor prediction-delta norms (magnitude) and per-predictor standard deviations (uncertainty) for all 151 perturbations and re-ran the same OOF CV.

| Feature set | Reg. corr | Bad-pert AUROC | Risk-cov AUC |
|---|---|---|---|
| **Base (3: disagreement + OOD + zero-pairs)** | **0.701** | **0.907** | **0.7460** |
| Base + 6 raw (norm/std × 3 predictors) | 0.686 | 0.891 | 0.7378 |
| Base + 2 derived (norm-spread + mean-std) | 0.699 | 0.905 | 0.7450 |

The six raw features *reduced* every metric (added noise / mild overfitting on 151 samples); the two derived features were flat. We therefore **do not** add them: the model keeps its three base features. This reinforces the central point — inter-model disagreement (cosine) is the dominant reliability signal, consistent with the −0.716 of R1, and raw prediction magnitude/uncertainty adds no orthogonal gain at this data scale. Reporting the negative result is a guard against feature-driven overfitting; the conclusion is explicitly scoped to the current 151-perturbation ledger and three donor-stack predictors and should be re-tested as the ledger grows or more heterogeneous predictors are added.

### R5. Frozen artifacts wired into the runtime (default `learned_with_rule_fallback`)

The learned layer is not a side analysis: it is the runtime default. We freeze the full-fit model into immutable, reproducible artifacts — `reliability_model_v0_3.json` (features = disagreement / `seen_in_train` / zero-pairs; standardized ridge weights disagreement **−0.118**, `seen_in_train` **+0.136**, zero-pairs **0**; plus the training-ledger sha256 and `n_train` = 151), `abstain_head_v0_3.json` (abstain below predicted Δ-Pearson 0.448, downgrade below 0.549; recorded risk-cov AUC 0.746), and `feature_schema_v0_3.json` (model features and forbidden-label list). The `ReliabilityAgent` gains a `mode` parameter; the workflow injects `reliability_mode = learned_with_rule_fallback` by default. End-to-end, the report carries the learned decision (e.g. mode `learned_with_rule_fallback`, reliability score 0.717, version `reliability_v0.3.0`).

Crucially, the hard rules remain rule-authoritative in every mode: species/empty/all-rejected/core decisions are taken by the rule gates, and the learned layer only takes over the *soft* downgrade/soft-abstain decision. A unit test (`test_hard_abstain_not_overridden_by_learned`) independently confirms a hard abstention is not overridden when the learned mode is active.

### R6. Fail-closed and auditable

The learned scorer is safe by construction:

- **No leakage.** The runtime scorer asserts that the inference feature dict contains no label key (`delta_pearson`, `per_predictor_delta_pearson`, `best_predictor`); a label entering runtime features raises rather than silently scores.
- **Fail-closed fallback.** Missing artifacts, a feature-schema-version mismatch, incomplete required fields, or a content-hash mismatch (we recompute a `content_sha256` over the model's features/mean/std/weights/lam and compare) all return `fallback=True`, and the caller reverts to the rule path. Tampering with the frozen weights therefore demotes the system to rules rather than executing an altered model.
- **Auditable.** Every learned decision carries `artifact_sha256` (and the abstain-head hash), `model_version`, `feature_schema_version`, `features_used`, and the `fallback` flag, so each soft decision is traceable to the exact immutable artifact that produced it.

Seven integration gates cover these behaviours (model runs; missing artifact → rule; schema mismatch → rule; label-in-features → assertion; report contains the learned decision; risk-coverage AUC 0.746 reproduces from the ledger; hard abstention not overridden), alongside the full Mac suite.

### R7. Rule-only vs. learned, head-to-head — a runtime integration replay (not a generalization benchmark)

Finally we ask whether switching the default from rule-only to `learned_with_rule_fallback` actually changes runtime soft-risk decisions. We replay the 151-entry ledger through both modes (real disagreement, real Δ-Pearson labels; bad = bottom-quartile, threshold 0.455; 38 bad / 113 good).

| Mode | wrong-accept ↓ | unnecessary-abstain ↓ | risk-coverage ↑ | retained-utility ↑ | n flagged | hard-rule-override | provenance |
|---|---|---|---|---|---|---|---|
| rule-only | **0.974** | 0.018 | **0.026** | 0.982 | 3 | 0 | — |
| **learned_with_rule_fallback** | **0.211** | 0.195 | **0.789** | 0.805 | 52 | **0** | **complete** |

Rule-only barely engages soft risk: it only flags when disagreement exceeds 0.5, but most ledger perturbations sit below 0.5, so it flags 3 of 151 and accepts 97.4% of the bad perturbations (risk-coverage 0.026). The learned default flags 52, catching 79% of the bad perturbations (wrong-accept 0.974 → **0.211**, risk-coverage 0.026 → **0.789**), at the cost of more unnecessary abstentions (0.018 → 0.195) and lower retained utility (0.982 → 0.805) — a sensible risk/availability trade. Hard-rule-override is **0** and provenance is **complete** in the learned mode.

> Because this comparison replays the curated perturbation ledger used to freeze and audit the governance artifacts — and the frozen model is fit on all 151 of those entries — we interpret it as a runtime-integration and decision-behaviour test, **not** an independent generalization benchmark. Generalization is evaluated separately by the perturbation-level out-of-fold reliability (R2) and abstention (R3) analyses. The rule-only arm scores poorly here largely because its fixed 0.5 threshold is conservative and ledger disagreement is mostly below it; the learned arm extracts more decision signal from the *same* feature.

The takeaway, stated narrowly: with the learned default the runtime recovers soft reliability risk that the rules let through, while preserving hard-rule authority and full auditability.

## Methods (brief)

**Leakage-controlled features and splits.** `governance/ledger_features.py` classifies every ledger column as an inference feature (available at prediction time), a label (true accuracy, forbidden as a feature), or a diagnostic (the rule decision itself, used only as a baseline). `extract_features` asserts feature ∩ label = ∅ at compile time; `leave_perturbation_out_folds(k=5)` splits one entry = one perturbation, giving a perturbation-level split with no cell leakage.

**Learned model.** `governance/reliability_model.py` is a pure-Python standardized ridge (no numpy/sklearn), chosen as a light model appropriate to 151 samples. `cv_reliability` produces the OOF predictions used for all generalization numbers (R2, R3); `fit_full` produces the full-fit parameters frozen for the runtime (R5, R7). `governance/abstain_head.py` turns OOF reliability into the risk–coverage curve.

**Freeze and runtime.** `governance/freeze_artifacts.py` exports the artifacts with the training-ledger hash and version (reproducible). `governance/learned_reliability.py` loads them, asserts no-leakage, self-checks the content hash, fails closed, and returns the scored decision with provenance. `governance/mode_compare.py` runs the in-sample R7 replay.

**Honesty of the comparison.** R7 uses the full-fit frozen model replayed over its own training ledger; R2/R3 use out-of-fold predictions. These are reported as different evidence types (§A) and never merged.

## Limitations

- **Perturbation-level, not per-cell.** All numbers (≈0.5–0.9 Δ-Pearson, AUROC, risk-coverage) are perturbation-level selective-reliability statistics over the evaluation ledger; they are not, and are not comparable to, the v0.2 per-cell headline (0.7039).
- **R7 is in-sample by construction.** The rule-vs-learned table replays the same 151 entries the frozen model was fit on. It demonstrates decision-behaviour change and hard-rule/provenance preservation, not out-of-sample performance; the generalization claim rests on R2/R3.
- **Single control (W4.5).** Disagreement is currently computed against a single baseline rather than the full per-cell control; the −0.716 and downstream signals are established under that single-control setting, and a per-cell control is expected to sharpen them.
- **Small sample, no CI.** The ledger is 151 perturbations with a single deterministic 5-fold; we report no bootstrap confidence intervals. The cross-fold OOF gaps (0.907 vs 0.774; 0.746 vs 0.720) are clear but uninterval'd; a perturbation-level bootstrap CI on the headline numbers is a clean, planned refinement.
- **Three features.** The learned model uses three inference features; richer features did not help at this scale (R4) but the conclusion is scoped to the current ledger and predictor set.
- **Runtime `seen_in_train` is mostly None.** The training-set lookup is not yet wired into the runtime, so `seen_in_train` is usually absent and `predict_dp` imputes the training mean (recorded honestly in `features_used`); disagreement is the dominant feature, so the effect is limited.
- **Thresholds are not end-to-end tuned.** Abstain/downgrade thresholds are set from training-prediction quantiles (15% / 35%), not end-to-end optimized; `unnecessary-abstain` will move with the threshold.
- **No hard-rule trigger in the ledger.** The ledger is entirely human / in-vocabulary soft-decision cases, so `hard_rule_override = 0` in R7 holds by construction; hard-rule preservation is proven independently by unit test, not by this table.
- **Predictive performance does not beat SOTA.** The base predictors are donor-stack variants; a strong external task-specific baseline on the identical split (e.g. GEARS / scGen / STATE) is future work and does not bear on the learned-governance claims here.

## Discussion

PRAXIS-VirtualCell's reliability governance moves from rule-based to learned: a light, leakage-controlled reliability model generalizes better than the single-signal disagreement heuristic that drove v0.2 (bad-perturbation AUROC 0.907 vs 0.774; abstention risk–coverage AUC 0.746 vs 0.720, out of fold), and once frozen and wired in as the default it measurably recovers soft reliability risk the rules let through (wrong-accept 0.974 → 0.211 in runtime replay) while preserving hard-rule authority, fail-closed safety, and per-decision auditability. This sharpens the v0.2 thesis: applicability and abstention belong in the pipeline as enforced control flow[^13][^14][^15][^16][^17], and that control flow can itself be *learned* without surrendering the hard guarantees — an extension of the trustworthy-AI-for-science[^21] and reproducibility[^22] stance, with the predictive core still offline and deterministic. The same learned-governance pattern (a frozen, auditable, fail-closed reliability head over heterogeneous predictors) plausibly generalizes to other agentic settings such as code-gating LLM agents, but we do not evaluate that here and make no claim about it.

## Evidence sources (internal traceability)

Every number above is reproduced from a logged finding; nothing is hand-entered:

| Claim | Source finding |
|---|---|
| corr −0.716; 0.571 vs 0.841; best-predictor gnn 75 / lin 39 / lat 37 | `docs/findings/finding_w9_m1_ledger_enriched.md` |
| Reliability AUROC 0.907 / 0.788 / 0.774 / 0.479; reg corr 0.701; bad thr 0.455 | `docs/findings/finding_w9_m2_reliability_model.md` |
| Abstain risk-cov AUC 0.746 / 0.730 / 0.720 / 0.660; retained dp by coverage | `docs/findings/finding_w9_m2_abstain_head.md` |
| Feature-enrichment negative result (base vs +6 raw vs +2 derived) | `docs/findings/finding_w9_m2_feature_enrich.md` |
| Ridge weights; artifacts; runtime e2e (score 0.717, v0.3.0); 7 gates; fail-closed | `docs/findings/finding_w9_m2_runtime_integration.md` |
| Rule-vs-learned table (n=151; 0.974→0.211; 0.026→0.789; override 0; provenance complete) | `docs/findings/finding_w9_m2_mode_compare.md` |
| Leakage-controlled feature/label/diagnostic classification | `docs/findings/finding_w9_m2_ledger_audit.md` |
| Oracle router 0.7043; ensemble near oracle → Router deferred | `docs/findings/finding_w9_m2_router_oracle.md` |

## References

*Footnote numbers follow the PRAXIS-VirtualCell v0.2 reference list; cited here are [^13]–[^17] (reject option / selective classification / applicability domain), [^21] (trustworthy AI for science), and [^22] (reproducible computational research).*
