# PRAXIS-VirtualCell consolidated evidence (v0.1→v0.3, with later v0.4/v0.5 additions)

> Historical synthesis of recorded and verified results, with explicit limits on what supports a complete virtual-cell paper. All numbers come from recorded findings. Protocols and evidence types are kept separate.
> Recorded update: 2026-07-01, including L4 and v0.4/v0.5 additions, strict 15/15, and collective coverage of 5 applications × 4 species. Historical Mac verification: **203 passed + 25 skipped**. This snapshot is not current release status.
> The detailed numerical inventory is `docs/paper/v0.3/data-inventory.md`.

## 0. Positioning and supported claims

PRAXIS treats reliable virtual-cell perturbation prediction as a **control-flow and governance problem**. It integrates existing predictors as agents without retraining foundation models. Its contribution is routing, reliability, abstention, unified output, auditable provenance, and learned governance.

The strongest quantitative claim is that governance is effective on human Norman perturbations: perturbation-held-out reliability learning yields bad-pert AUROC **0.907** and risk-coverage AUC **0.746**, exceeding rule-based rankings. Paired-difference 95% CIs exclude 0, and the advantage is robust to fold assignment.

The original v0.3 evidence did not yet establish a general agent framework across representative species and applications: it centered on human Norman single-cell gene perturbation, with only a cross-species routing prototype. Later v0.4/v0.5 demonstrations broaden that evidence, as recorded below, without establishing a universal cross-species predictor.

## 1. Evidence hierarchy

| Label | Meaning | Strength |
|---|---|---|
| `[remote-witnessed deterministic]` | Remote A100 rerun with bitwise/tolerance reproduction | Strongest |
| `[remote execution]` | One remote run using the recorded recipe | Strong |
| `[Mac deterministic]` | Deterministically reproducible on Mac | Strong |
| `[OOF generalization]` | Perturbation-held-out cross-validation | Moderate; small sample |
| `[in-sample replay]` | Full-data fit replayed on the same data, not independent generalization | Behavior/integration evidence only |
| `[capability matrix]` | Capability presence/absence, not predictive performance | Qualitative |
| `[declarative]` | Unit tests activate a mechanism that mock end-to-end runs do not activate | Limited mechanism-existence evidence |

Keep three distinctions explicit:

1. **Per-cell (n=18874) differs from perturbation-level (ledger n=60/151).** v0.2 headline accuracy is per-cell; v0.3 M1/M2 results are perturbation-level.
2. **OOF generalization differs from in-sample replay.** 0.907/0.746 are OOF results; the rule-versus-learned runtime table is in-sample.
3. **Learned soft governance differs from hard-rule gating.** Learned decisions do not override hard rules.

## 2. Results organized for the paper

### R1. System architecture / agent runtime (v0.1)

The runtime combines the message bus, species brain, predictor agents, abstention, critic, provenance, and optional LLM agents. Offline execution is deterministic. Evidence: `[capability matrix]` + `[Mac deterministic]`.

### R2. Human perturbation benchmark (Table A, v0.2)

Protocol: donor Norman test split, **per-cell ΔPearson**, the same EvalAgent, n=18874. Evidence: `[remote-witnessed deterministic]`. Sources: `finding_w8_systems_comparison` and `finding_w8_provenance_reverify`.

| System/method | Type | ΔPearson | n |
|---|---|---|---|
| **PRAXIS Coordinator (all-5)** | ensemble + governance | **0.7039** | 18874 |
| 6 base predictors | single bases | 0.6716–0.6183 | 18874 |
| **GEARS (same-split donor-eval, 5ep)** | external specialized GNN | **0.4877** | 18874 |
| **mean-perturbation** | naive lower-bound baseline | **0.4615** | 18874 |
| scGPT (frozen + lightweight head) | foundation model | **0.4407** | 7290 |

Frozen scGPT 0.4407 is below mean-baseline 0.4615; model scale alone does not guarantee accuracy under this protocol. PRAXIS does not claim to defeat SOTA.

L4 adds the external matched-protocol baseline (`finding_w9_l4_gears_same_split`). GEARS native `pearson_de` 0.8392 is off-axis (absolute expression on DE genes with its own split). Under the same per-cell ΔPearson protocol and donor test split (n=18874), GEARS is **0.4877**, below all donor bases and Coordinator 0.7039. Metrics and protocols determine this comparison. GEARS condition-level predictions are broadcast to cells, which disadvantages it; see the source finding's Section 4 caveat. The leakage-free split is train62/test150; IER5L is filtered by the GEARS GO graph.

### R3. Learned reliability governance (v0.3 M1/M2.1)

**Activation (M1).** Across 60 real perturbations, disagreement changes from a mock constant 0.5 to a real continuous distribution (0.23–0.504), with automatic abstention above threshold. **corr(disagreement, per-pert ΔPearson) = −0.716**; higher disagreement corresponds to an approximately 27-point accuracy gap. Best predictors vary across perturbations: gnn75/linear39/latent37. Evidence: `[remote execution]`.

**Generalization (M2.1 OOF).** Protocol: 151 perturbations, perturbation-level metrics, perturbation-held-out 5-fold validation, and no leakage.

| Metric | learned | Rule-ranking baseline | random |
|---|---|---|---|
| Bad-pert AUROC | **0.907** | disagreement 0.774 / ood 0.788 | 0.479 |
| Risk-coverage AUC | **0.746** | disagreement 0.720 / ood 0.730 | 0.660 |
| Reliability-regression OOF correlation | **0.701** | — | — |

**Robustness (L1/B3).** Paired-difference 95% CIs exclude 0: AUROC +0.13 [0.056,0.191] and risk-coverage +0.026 [0.014,0.041]. Across 5 seeds, learned AUROC is 0.900±0.008 and risk-coverage is 0.744±0.001.

**Negative feature-enrichment result.** Adding magnitude/uncertainty features does not improve performance, so the 3 base features are retained to limit overfitting.

**OOD enrichment (L2).** Learned-flagged cases are 98% OOD, with odds ratio **74.7**. Learned scores add information beyond OOD labels: OOD-only subset risk-coverage is 0.577>0.5, and AUROC 0.907 exceeds ood-only 0.788.

**Runtime integration (in-sample).** The default mode is `learned_with_rule_fallback`. Rule-versus-learned replay changes wrong_accept **0.974→0.211** and risk_coverage **0.026→0.789**, with **hard_override=0** and complete provenance. Frozen artifacts use content_sha256 integrity checks and fail-closed fallback; decisions are individually traceable. All 7 gates and the leakage audit pass. This is integration evidence, not independent generalization.

### Governance matrix (Table B, v0.2)

The matrix records 7 governance capabilities: GEARS/CPA/scGPT/scGen/STATE lack them at this system level, while PRAXIS provides them. Entries come from paper/repository checks for each capability. This is `[capability matrix]` evidence, not a performance comparison.

## 3. Numerical verification

Remote A100 reruns checked the recorded accuracy numbers: linear bitwise 0.6638587, Coordinator 0.703874, scGPT bitwise 0.4406901964584723, and GEARS retraining 0.8461 on the same scale as its native result. No fabricated or mismatched checked number was found. Source: `finding_w8_provenance_reverify`.

## 4. Evidence limitations at the original snapshot

- **Perturbation-level differs from per-cell.** M2 AUROC/risk-coverage numbers are not the headline per-cell 0.70 result.
- **W4.5 single control.** The original disagreement analysis used a single baseline rather than per-cell controls. Later G2 recalculation is recorded in the detailed inventory and analysis summary.
- **Small sample.** The ledger contains 151 perturbations. Bootstrap CIs and multiple seeds were later added, but the AUROC interval remains wide: 0.907 [0.846,0.952]. Emphasize paired advantages rather than isolated exact point estimates.
- **No prediction-SOTA claim.** Predictors are reproduced and integrated; L4 adds the matched-protocol GEARS comparison.
- **Original cross-species scope.** mouse/bacteria/yeast initially had only routing prototypes, not a trained cross-species predictor.
- **Original application scope.** The v0.3 core centered on gene perturbation. Later representative demonstrations expand the application categories without removing their proxy/coverage limitations.

## 5. Later additions and remaining comparisons

### L4: same-split GEARS donor evaluation (completed 2026-07-01)

- GEARS same-split donor-eval, 5ep: **ΔPearson 0.4877**, cosine 0.986, n=18874, matched to Table A. Source: `finding_w9_l4_gears_same_split`.
- Custom split train62/test150, donor train∩test=∅; IER5L is filtered by the GEARS GO graph. Evaluation uses `load_norman("test",seed=1)` with 18874 cells.
- Caveats: condition→cell broadcast, 5ep aligned with the reference baseline, and a single run without a fixed GEARS seed. This resolves the historical R8 comparison gap.

| Historical gap | Impact | Recorded resolution |
|---|---|---|
| External specialized baseline missing from Table A | High | L4 adds matched-protocol GEARS 0.4877; scGen/STATE remain absent |
| W4.5 single-control disagreement | Moderate-high | A remote per-cell rerun was pending as B2 at this snapshot; later G2 resolution is recorded in the detailed inventory |
| Cross-species evidence only a routing prototype | Moderate | v0.4 adds mouse orthology (C3) and real bacteria/yeast GEM execution (C4/C5) |
| Only gene perturbation applications | High | v0.4 adds gene, metabolism (GEM), and drug (LINCS MOA) demonstrations across C1-C6 |

## 6. Publication-scope interpretation

The learned-reliability-governance evidence forms a coherent standalone result for a methods track or systems venue, with explicit small-sample and in-sample limitations.

The original three breadth/comparison gaps changed as follows:

1. No matched-protocol strong external baseline → L4 adds GEARS 0.4877; scGen/STATE remain to be evaluated.
2. Main results confined to human gene perturbation → v0.4 adds human/mouse/bacteria/yeast and gene/metabolism/drug, with 6 core demonstrations C1-C6 using real data or tools.
3. Virtual-cell application breadth absent → **5 application categories** now have demonstrations: gene, drug (LINCS MOA), state/fate (IFN activation), metabolism (GEM + expression tendency), and communication (L-R co-expression), each with a governance decision.

The narrative expands from `Norman prediction → governance → learned abstention` to `core human benchmark (+matched-protocol GEARS) → learned reliability governance → representative applications (gene/metabolism/drug) → cross-species agent routing (human/mouse/bacteria/yeast)`.

The value of each non-human/non-gene case is its governed decision, not execution alone. Weak HDAC drug signals are downgraded and missing microbial genes trigger abstention. R6 illustrates how reliability-governed reporting prevents overclaiming. Related evidence: `application-cases.md`.

> PRAXIS-VirtualCell is first quantitatively validated on human perturbation prediction, then demonstrated across representative species and applications through **reliability-governed agent workflows**.
