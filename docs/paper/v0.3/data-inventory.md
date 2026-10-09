# PRAXIS-VirtualCell evidence inventory (v0.2 + v0.3)

> Historical inventory of recorded results, metrics, evidence types, sample sizes, finding identifiers, and verification status. It includes limitations and an assessment of the evidence available for different publication scopes. Numbers are copied from recorded findings rather than inferred.
> Recorded source snapshot: `c784c89`; Mac tests **93 passed + 25 skipped**. Later L1/B3/L2/L4/G2 additions are identified below. Historical planning judgments are not current release claims.

## 0. Evidence conventions

| Label | Meaning | Strength |
|---|---|---|
| `[remote-witnessed deterministic]` | Re-executed on a remote A100; bitwise or tolerance-based reproduction | Strongest |
| `[remote execution]` | One remote run using the recorded recipe | Strong |
| `[Mac deterministic]` | Deterministically reproducible on Mac | Strong |
| `[OOF generalization]` | Perturbation-held-out cross-validation | Moderate: small sample; early results lacked CIs |
| `[in-sample replay]` | A model fitted on all data is replayed on that same data; not independent generalization | Integration/behavior evidence only |
| `[capability matrix]` | Presence or absence of a capability, not predictive performance | Qualitative |
| `[declarative]` | Unit tests show a mechanism can activate; mock end-to-end runs do not activate it | Limited mechanism-existence evidence |

Keep these distinctions explicit:

- **Per-cell (n=18874) differs from perturbation-level (ledger n=60/151).** v0.2 accuracy is per-cell; all v0.3 M1/M2 governance results are perturbation-level.
- **OOF generalization differs from in-sample replay.** 0.907/0.746 are OOF results; the rule-versus-learned runtime comparison is in-sample.
- **Learned soft governance differs from hard-rule gating.** The learned layer changes only soft decisions; hard rules remain authoritative.

## 1. v0.2 accuracy (Table A)

Protocol: donor Norman test split, **per-cell ΔPearson**, the same EvalAgent, n=18874 except scGPT. Evidence: `[remote-witnessed deterministic]`. Sources: `finding_w8_systems_comparison` (Table A) and `finding_w8_provenance_reverify` (bitwise verification).

| System/method | Type | ΔPearson | n | Verification |
|---|---|---|---|---|
| **PRAXIS Coordinator (all-5)** | ensemble + governance | **0.7039** | 18874 | 0.703874 ✓ |
| PRAXIS Coordinator (cpa+decoder+gnn) | ensemble | 0.7020 | 18874 | 0.701951 ✓ |
| PRAXIS Coordinator (latent+gnn) | ensemble | 0.6847 | 18874 | 0.684678 ✓ |
| cpa_style | single base | 0.6716 | 18874 | ✓ |
| decoder_only | single base | 0.6709 | 18874 | ✓ |
| gnn_pert | single base | 0.6675 | 18874 | ✓ |
| linear_additive | single base | 0.6639 | 18874 | **bitwise** 0.6638587363779742 ✓ |
| latent_additive | single base | 0.6365 | 18874 | ✓ |
| pretrained-mock | single base | 0.6183 | 18874 | ✓ |
| **GEARS (same-split donor-eval, 5ep)** | external specialized GNN | **0.4877** | 18874 | remote execution ✓ (L4) |
| **mean-perturbation** | naive lower-bound baseline | **0.4615** | 18874 | remote execution ✓ |
| scGPT (frozen backbone + lightweight head) | foundation model | **0.4407** | 7290 | **bitwise** 0.4406901964584723 ✓ |

The external matched-protocol baseline was added in L4 (`finding_w9_l4_gears_same_split`). Native GEARS pearson_de 0.8392 (retrained 0.8461) is off-axis: absolute-expression Pearson on differentially expressed genes with its own split. Under the same per-cell ΔPearson protocol, donor test split, and n=18874, GEARS is **0.4877**, below every donor base and Coordinator 0.7039. The leakage-free split is train62/test150; IER5L is filtered by the GEARS GO graph. GEARS produces condition-level outputs that are broadcast to cells, so this evaluation disadvantages it. These numbers do not establish a claim that PRAXIS defeats SOTA.

Frozen scGPT 0.4407 is below mean-baseline 0.4615. Larger model scale alone does not guarantee better performance under this protocol.

## 2. v0.2 governance capability matrix (Table B)

Evidence: `[capability matrix]`, a presence/absence comparison based on papers and repositories for 5 systems, with recorded support for each entry. Source: `finding_w8_systems_comparison` (S1).

| Governance capability | GEARS | CPA | scGPT | scGen | STATE | **PRAXIS** |
|---|---|---|---|---|---|---|
| 1. OOD/cross-species input rejection | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| 2. Applicability checks | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| 3. Active abstention | ✗ | ✗ | ✗ | ✗ | ✗ | **✓**¹ |
| 4. Provenance + replayable trace | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| 5. Auditable communication across heterogeneous models (bus) | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| 6. Retrieve-before-predict gate + critic | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| 7. Offline deterministic reproducibility | partial | partial | partial | partial | partial | **✓** |

¹ Primary abstention paths (unsupported species, empty targets, all models rejected) activate at runtime. In v0.2, secondary triggers (model disagreement, core failure, cell-type downgrade) were `[declarative]`: unit tests activated them, but mock end-to-end runs did not. v0.3 M1 addresses this limitation (Section 6).

## 3. v0.2 abstention value / risk-coverage (Table C)

Protocol: real donor predictors (cpa primary + 4 auxiliary bases), Norman test split, **per-cell ΔPearson**, abstention ranked by disagreement. Full-coverage reference: cpa 0.6716. Evidence: `[remote execution]`. Source: `finding_w8_systems_comparison` (Table C).

| tau | coverage | Retained-set ΔPearson | Gain vs full coverage 0.6716 |
|---|---|---|---|
| 1.0 | 1.00 | 0.6716 | — (reference) |
| 0.4 | 0.96 | 0.6830 | +0.011 |
| 0.3 | 0.88 | 0.7071 | +0.036 |
| 0.25 | 0.82 | 0.7320 | +0.060 |
| 0.2 | 0.74 | 0.7536 | **+0.082** |

- Real OOD split: among 151 test perturbations, **82 are unseen** (13056 cells) and 69 are seen (5818 cells). Manifest: `data/manifests/norman_2019.yaml`, including the h5ad SHA-256 record.
- The positive trend is robust, but GPU floating-point differences near the threshold cause approximately ±0.01 variation across runs. Report the trend rather than claiming exact single-run threshold values.
- The early analysis applies abstention across the entire test split without separately verifying enrichment of the 82 unseen OOD perturbations.
- These per-cell results complement the M2 perturbation-level risk-coverage results in Section 7. Their absolute values are not directly comparable.

## 4. v0.2 runtime contribution (A↔D ablation, five axes)

Protocol: identical mock predictors; A=ML-only stub, D=full PRAXIS; deterministic offline execution. Evidence: `[capability matrix]`. Arm A structurally lacks four capabilities, making their values 0 by construction. Sources: v0.2 manuscript Section 3.4 and `finding_w7_ablation`.

| Axis | Arm A (ML-only) | Arm D (full PRAXIS) |
|---|---|---|
| OOD rejection rate | 0.0 | 1.0 |
| Wrong-model use rate | 1.0 | 0.0 |
| Provenance completeness | 0.0 | 1.0 |
| Abstention correctness | 0.0 | 1.0 |
| Trace completeness | 0.0 | 1.0 |

Limitation: this is an extreme-arm comparison against a stub. It lacks graded intermediate-arm ablations with real predictors.

## 5. v0.2 numerical verification

Evidence: `[remote-witnessed deterministic]` + `[Mac deterministic]`. Source: `finding_w8_provenance_reverify`.

| Number family | Verification method | Result |
|---|---|---|
| 6 bases (0.6716…0.6183) | deterministic remote re-evaluation | linear bitwise; other differences match the recorded finding ✓ |
| Coordinator 0.7039/0.7020/0.6847 | remote re-evaluation | all-5=0.703874, n=18874 ✓ |
| scGPT 0.4407 | re-evaluation of archived checkpoint | bitwise 0.4406901964584723 ✓ |
| GEARS pearson_de 0.8392 | stochastic retraining | 0.8461, same scale; still off-axis |
| A↔D five axes + cross-species checks | Mac rerun | matching results (75 passed) ✓ |

The verification found no fabricated or mismatched quantitative result among the recorded results checked at that snapshot.

## 6. v0.3 M1 governance activation and evaluation ledger

### 6.1 Real disagreement/abstention activation

This resolves the `[declarative]` limitation in the v0.2 Table B discussion in Section 2. Protocol: 60 real Norman perturbations, real donor predictors (linear/latent/gnn), and real 2000-dimensional deltas. Evidence: `[remote execution]`. Source: `finding_w9_m1_activation`.

| Metric | Value |
|---|---|
| Perturbations | 60 (test split) |
| disagreement.score distribution | min 0.23 / median 0.375 / **max 0.504** / mean 0.359 |
| n_models | 3 (all real donor bases participate) |
| Threshold >0.5 → automatic abstention | **1 case**, counts `{high:59, low:1}` |

Disagreement changes from the mock constant 0.5 to a real continuous distribution. `ReliabilityAgent` automatically abstains when the threshold is exceeded. The rate is low (1/60) because the 3 donor bases agree relatively well; more heterogeneous predictors may disagree more.

### 6.2 Disagreement versus accuracy

Protocol: **perturbation-level** per-pert ΔPearson using mean aggregation, not per-cell evaluation. Evidence: `[remote execution]`. Source: `finding_w9_m1_ledger_enriched`.

| Metric | Value |
|---|---|
| **corr(disagreement, per-pert ΔPearson)** | **−0.716** (n=60) |
| Mean dp, higher-disagreement half | 0.571 (n=30) |
| Mean dp, lower-disagreement half | 0.841 (n=30) |

Higher disagreement corresponds to lower accuracy, a difference of approximately 27 percentage points. This provides empirical support for abstention and downgrade.

### 6.3 The best predictor varies by perturbation

Protocol: perturbation-level. Sources: `finding_w9_m1_ledger_enriched` and `finding_w9_m2_router_oracle`.

- Across 151 perturbations, best predictors are **gnn 75 / linear 39 / latent 37**; none is uniformly best.
- Across the 60-sample subset: gnn 28 / latent 20 / linear 12.

### 6.4 Evaluation ledger (stage 2 training data)

The pure-Python ledger implementation is `benchmarks/eval_ledger.py`; source: `finding_w9_m1_eval_ledger`. The enriched, leakage-audited 151-record ledger is `docs/findings/m1_ledger_151.jsonl`.

## 7. v0.3 M2.1 learned governance

Evidence is separated into OOF generalization, in-sample runtime integration, and safety/provenance.

### 7.0 Routing oracle comparison

Protocol: 151 perturbations, **perturbation-level ΔPearson**. Evidence: `[remote execution]`. Sources: `finding_w9_m2_router_oracle` and `finding_w9_m2_ensemble_compare`.

| Strategy | Perturbation-level dp | Relative gain |
|---|---|---|
| Fixed latent | 0.6360 | — |
| Fixed linear | 0.6639 | — |
| Best single model: gnn | 0.6702 | Reference |
| **Fixed ensemble (mean of 3 predictions)** | **0.693** | +0.023 vs single model |
| Oracle router (best predictor per perturbation; **upper bound**) | 0.7043 | **Only +0.011 vs ensemble** |

The ensemble captures most available routing gain. Remaining hard-routing headroom is +0.011, so the work prioritized abstention/selective prediction and deferred Router.

### 7A. Generalization evidence (OOF/CV)

Evidence: `[OOF generalization]`. Protocol: 151 perturbations, perturbation-level, perturbation-held-out 5-fold validation, OOF predictions, and no leakage; only INFERENCE_FEATURES are used.

**(a) Reliability model.** Source: `finding_w9_m2_reliability_model`.

| Task | Metric | Value |
|---|---|---|
| Reliability regression | OOF corr(predicted dp, true dp) | **0.701** |
| Bad-pert detection (bottom 25%, threshold 0.455, 38 bad/113 good) | **learned AUROC** | **0.907** |
| | ood-only AUROC | 0.788 |
| | disagreement-only AUROC | 0.774 |
| | random AUROC | 0.479 |

**(b) Abstention head / risk-coverage.** Source: `finding_w9_m2_abstain_head`.

| Ranking signal | Risk-coverage AUC |
|---|---|
| oracle (true dp; upper bound) | 0.7822 |
| **learned (reliability OOF)** | **0.7460** |
| ood-only | 0.7297 |
| disagreement-only (used in v0.2) | 0.7196 |
| random | 0.6595 |

Retained-set dp at coverage 1.0 / 0.8 / 0.6: oracle 0.657/0.772/0.842; **learned 0.657/0.733/0.796**; disagreement 0.657/0.713/0.749. At coverage 0.6, learned improves over the rule signal by +0.047.

**(c) Feature enrichment: negative result.** Source: `finding_w9_m2_feature_enrich`.

| Feature set | reg_corr | Bad-pert AUROC | Risk-coverage AUC |
|---|---|---|---|
| **base (3)** | **0.701** | **0.907** | **0.7460** |
| base + 6 raw features (norm/std×3) | 0.686 | 0.891 | 0.7378 |
| base + 2 derived features | 0.699 | 0.905 | 0.7450 |

Magnitude/uncertainty features reduce performance (raw features) or leave it approximately unchanged (derived features). The model retains the 3 base features to limit overfitting; disagreement dominates.

**(d) Robustness: bootstrap CIs and multiple seeds.** L1/B3; source: `finding_w9_m2_bootstrap_ci.md`.

| Metric | Point estimate | 95% CI / across seeds |
|---|---|---|
| Paired AUROC difference (learned − disagreement) | +0.1325 | **[0.056, 0.191]**, excludes 0 |
| Paired risk-coverage AUC difference (learned − disagreement) | +0.0264 | **[0.014, 0.041]**, excludes 0 |
| Learned AUROC | 0.907 | [0.846, 0.952], wide with the small sample |
| Learned AUROC across 5 seeds | — | 0.900 ± 0.008 [0.885, 0.907] |
| Learned risk-coverage AUC across 5 seeds | — | 0.744 ± 0.001 |

Paired advantages are statistically supported and robust to fold assignment. Wide intervals reflect the 151-sample limitation; emphasize paired advantages rather than an exact isolated point estimate.

**(e) OOD enrichment.** L2; source: `finding_w9_m2_ood_enrichment.md`.

| Metric | Value |
|---|---|
| OOD fraction among learned-flagged cases / base rate | 0.981 (51/52) / 0.543 |
| OOD enrichment odds ratio | **74.7** |
| OOD-only / seen-only subset risk-coverage AUC | 0.577 / 0.861 |
| Learned AUROC vs ood-only | 0.907 vs 0.788 |

Learned flags strongly enrich for OOD while adding information beyond OOD labels: selective ranking remains above 0.5 within the OOD-only subset (0.577>0.5).

### 7B. Runtime integration evidence (in-sample replay)

Evidence: `[in-sample replay]`. A model fitted on all 151 ledger records is frozen and replayed on the **same 151 records**. This is not independent generalization; it demonstrates changed decisions, preserved hard rules, and full provenance. Sources: `finding_w9_m2_mode_compare` and `finding_w9_m2_runtime_integration`.

**(a) rule_only versus learned.** n=151, bottom 25% bad, threshold 0.455, 38 bad/113 good.

| Mode | wrong_accept ↓ | unnec_abstain ↓ | risk_coverage ↑ | retained_util ↑ | n_flagged | hard_override | provenance |
|---|---|---|---|---|---|---|---|
| rule_only | **0.974** | 0.018 | **0.026** | 0.982 | 3 | 0 | — |
| **learned_with_rule_fallback** | **0.211** | 0.195 | **0.789** | 0.805 | 52 | **0** | **complete** |

Learned governance recovers 79% of bad cases missed by rules, with hard_override=0 and complete provenance. This remains an in-sample integration comparison, not a generalization benchmark.

**(b) Frozen artifacts and runtime end-to-end checks.** Source: `finding_w9_m2_runtime_integration`.

- `reliability_model_v0_3.json`: standardized ridge weights disagreement **−0.118**, seen **+0.136**, n_zero **0**; training ledger SHA-256 `548c444f…`, n_train 151.
- `abstain_head_v0_3.json`: abstain<0.448, downgrade<0.549, risk_cov_auc 0.746; plus `feature_schema_v0_3.json`.
- Default runtime mode is `learned_with_rule_fallback`; observed report score is **0.717**, version `reliability_v0.3.0`.
- Hard rules remain authoritative for species, empty input, all models rejected, and core failures. Learned governance handles soft decisions only. `test_hard_abstain_not_overridden_by_learned` independently checks this boundary.

### 7C. Safety and provenance evidence

Evidence: `[Mac deterministic]`. Sources: `finding_w9_m2_runtime_integration` and `finding_w9_m2_ledger_audit`.

All 7 gates pass: 1. Mac tests; 2. learned mode execution; 3. missing artifact→rule fallback; 4. schema mismatch→fallback; 5. labels entering runtime features→assertion failure; 6. learned decisions present in reports; 7. risk-coverage AUC 0.746 reproducible from the ledger. Hard abstention is also never overridden by learned governance.

- **Fail closed:** missing artifacts, wrong schemas, incomplete fields, and modified weights (`content_sha256` integrity check) trigger rule fallback.
- **Traceability:** every learned decision records `artifact_sha256`, `abstain_artifact_sha256`, model_version, feature_schema_version, features_used, and fallback.
- **Leakage prevention:** ledger_features asserts features∩labels=∅; perturbation-level splits avoid cell leakage.

## 8. Historical verification snapshot

Mac **93 passed + 25 skipped** in `praxis_virtualcell/tests`. Tests from the separate parent project are outside this project scope. Governance modules include ledger_features/reliability_model/abstain_head/learned_reliability/freeze_artifacts/mode_compare and artifacts.

Recorded data: `docs/findings/m1_ledger_151.jsonl`, `m1_per_pert_dp.json`, and `m1_pred_features.json`. The historical source snapshot was `c784c89`, tagged `v0.3.0-alpha.1`; this does not describe current release status.

## 9. Limitations and later resolutions

| Gap | Affected evidence | Severity at the time | Recorded status / remedy |
|---|---|---|---|
| 151-sample analysis initially lacked bootstrap CIs | 0.907 / 0.746 / comparison table | High; resolved by L1 | Paired CIs exclude 0: AUROC +0.13 [0.056,0.191], risk-coverage +0.026 [0.014,0.041]; wrong-accept reduction/risk-coverage improvement [0.59,0.92]. Source: `finding_w9_m2_bootstrap_ci.md`. |
| External specialized baseline absent from Table A | Complete virtual-cell comparison | High; partly resolved by L4 | GEARS same-split 0.4877 added; scGen/STATE remain absent. Source: `finding_w9_l4_gears_same_split`. |
| W4.5 single-control disagreement | Disagreement baseline | Moderate-high; resolved by G2 | Per-cell recalculation: AUROC 0.907→**0.869**, risk-coverage 0.746→**0.736**. Single-control estimates were slightly optimistic; the governance conclusion remains robust. Source: `finding_g2_percell_w45`. |
| mode_compare is in-sample | R7 is not independent generalization | Moderate | OOF Section 7A provides separate generalization evidence; describe the runtime comparison explicitly as in-sample. |
| Thresholds are not tuned end-to-end | unnecessary_abstain depends on thresholds | Moderate | Thresholds use training quantiles; later operational feedback could inform them. |
| One deterministic 5-fold split initially lacked multiple seeds | OOF robustness | Moderate; resolved by B3 | Across 5 seeds, AUROC 0.900±0.008 and risk-coverage 0.744±0.001; each seed exceeds disagreement. Source: `finding_w9_m2_bootstrap_ci.md`. |
| Router / Delta-Adapter not implemented | — | Low | Router deferred because the ensemble is near the oracle; Delta-Adapter deferred because of leakage risk. |
| Cross-species evidence at this snapshot is a routing prototype | mouse/bacteria/yeast | Low with explicit scope | No real cross-species predictor was claimed. |

## 10. Historical publication-scope assessment

The contribution is reliable, learned governance rather than prediction SOTA.

**A. Standalone learned-reliability-governance result or short paper** (`learned-governance.md`): the evidence chain is coherent—hard-error rejection, learned soft-risk signal (−0.716), OOF generalization (AUROC 0.907 / AUC 0.746), negative feature-enrichment results, frozen runtime integration, fail-closed provenance, and the in-sample comparison (0.974→0.211). The early concern was 151 samples without CIs; bootstrap CIs later strengthened this scope. The historical assessment was that this evidence was broadly sufficient for a workshop, methods track, or systems venue with explicit limitations.

**B. Complete virtual-cell paper** (v0.2 main text + v0.3 supplement): strengths were the 5-system governance matrix, verified accuracy numbers, and learned governance. The original three concerns were ① no matched-protocol external strong baseline, ② W4.5 single-control disagreement, and ③ missing CIs. These could invite criticism about weak accuracy controls and small-sample uncertainty. The governance contribution was promising, but a broad paper needed those improvements or a narrower systems/methods scope without SOTA claims.

The historical priority order was ① bootstrap CIs (completed through L1/B3/L2), ② same-split GEARS in Table A (later completed by L4), and ③ per-cell W4.5 recalculation (later completed by G2). The later resolutions are recorded in Section 9; this sequence is an evidence-history record, not an outstanding execution plan.
