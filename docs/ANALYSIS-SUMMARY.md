# PRAXIS-VirtualCell analysis summary (as of 2026-07-02)

> Historical evidence summary: the core benchmark, learned governance, 16 representative species × application cases (strict 15/15), external baselines (GEARS/scGen/STATE), per-cell W4.5 analysis, and LLM communication architecture. All numbers come from recorded findings.
> Verification at this snapshot: Mac **203 passed + 25 skipped**. These are historical counts, not current release status.

## 0. Positioning

PRAXIS treats reliable virtual-cell perturbation prediction as a **control-flow and governance problem**. Existing predictors are integrated as agents without retraining foundation models. The contribution is routing, reliability assessment, abstention, unified output, auditable provenance, and learned governance; it does not claim universally better prediction accuracy.

> First quantitatively validated on human perturbation prediction, then demonstrated across representative species and applications through **reliability-governed agent workflows**.

## 1. Core benchmark (Table A, human Norman, per-cell ΔPearson, n=18874)

| System | ΔPearson | Evidence |
|---|---|---|
| **PRAXIS Coordinator (all-5)** | **0.7039** | Remote witnessed, bitwise reproduction |
| 6 donor bases | 0.6716–0.6183 | Remote witnessed |
| **GEARS (same-split, 5ep)** | **0.4877** | Remote execution (L4) |
| mean-perturbation | 0.4615 | Remote execution |
| scGPT (frozen) | 0.4407 | Bitwise reproduction |

The matched-protocol external baseline is **GEARS 0.4877** (L4). Its native `pearson_de 0.8392` is off-axis; evaluation using the same per-cell ΔPearson protocol gives 0.4877, below all donor bases. The metric and protocol determine the comparison. This supports the competitiveness of the ensemble and governance workflow, not a claim of defeating SOTA. GEARS condition-level outputs are broadcast to cells, which disadvantages it under this protocol. Source: `finding_w9_l4_gears_same_split`.

## 2. Learned governance (v0.3)

- Disagreement is active: corr(disagreement, per-pert dp) = **−0.716** across 60 perturbations; crossing the threshold triggers abstention.
- OOF generalization uses 151 perturbations and perturbation-held-out 5-fold validation without leakage: bad-pert **learned AUROC 0.907**, risk-coverage **AUC 0.746**, and regression correlation 0.701. Learned ranking outperforms disagreement-only and random ranking.
- Paired-difference 95% CIs exclude 0. Across 5 seeds, AUROC is 0.900±0.008.
- Learned-flagged cases are 98% OOD (OR 74.7), but the learned model adds information beyond OOD labels.
- In-sample runtime replay changes wrong_accept from 0.974→0.211 and risk_cov from 0.026→0.789, with hard_override=0. Frozen artifacts use SHA-256 integrity checks and fail closed.
- Table B records 7 governance capabilities: GEARS/CPA/scGPT/scGen/STATE lack these system-level capabilities, while PRAXIS provides them. This is a capability matrix, not a predictive-performance comparison.

## 3. Representative species × applications: strict 15/15 (16 cases + L4)

The cases collectively cover **5 applications × 4 species**. Each runs public data or tools, produces a 7-part output, and receives a governed decision (accept/caution/downgrade/abstain).

| Application / species | Human | Mouse | Yeast | Bacteria |
|---|---|---|---|---|
| Gene perturbation | Norman 0.7039 (C1) + OOD (C2) | orthology caution (C3) | deletion growth (C5) | KO growth (C4) |
| Drug/chemical | drug MOA (C6) + dose (R2) | — | — | carbon source (S1) + antibiotic (R3) |
| State/fate | IFN activation (S2) + EMT (R4) | differentiation fate (R1) | — | — |
| Metabolism/flux | pathway tendency (S3) | — | yeast GEM (C5) | E. coli GEM (C4) |
| Communication/environment | L-R (S4) + spatial (R5) + co-culture (R6) | — | — | — |

| Case | Data/tool | Observed result | Decision |
|---|---|---|---|
| C1 human gene | donor Coordinator | ΔPearson 0.7039 | accept |
| C2 human OOD | learned reliability | AUROC 0.907 / OOD OR 74.7 | abstention enriched for OOD |
| C3 mouse orthology | route_table | ortholog projection | caution/downgrade |
| C4 E. coli KO | cobra e_coli_core | WT 0.874; gltA/icd essential | accept; missing genes→abstain |
| C5 yeast KO | cobra iMM904 | WT 0.288; ERG1 essential | accept |
| C6 drug MOA | LINCS L1000 signatures | HSP90 enrichment 2.6–3.5× | HSP90 accept; weak HDAC signals downgrade |
| S1 carbon-source change | cobra e_coli_core | glucose 0.874→acetate 0.173 | accept; unknown carbon source caution |
| S2 immune activation | Kang 2018 IFN | ISG d=2.49; myeloid>lymphoid>megakaryocyte | accept; weak megakaryocyte response |
| S3 metabolic tendency | Kang 2018 | glycolysis/OXPHOS d=0.10/0.28 | **downgrade** (governance contrast with S2) |
| S4 L-R communication | Kang 2018 | CXCL10→CXCR3 Mono→CD8T 51× | CD8T/NK accept; CD4T (CXCR3^low) downgrade |
| R1 differentiation fate | scanpy paul15 | erythroid vs myeloid d=4.32 | accept |
| R2 drug dose | LINCS dose series | geldanamycin Spearman 0.90 | accept; near-zero sirolimus response downgrade |
| R3 antibiotic | cobra iML1515 | trimethoprim/sulfa target inhibition is lethal | accept; non-metabolic targets abstain |
| R4 cancer EMT | pertpy mcfarland | sarcoma vs epithelial carcinoma d=1.72 | accept (state characterization, not induced transition) |
| R5 spatial niche | squidpy imc | tumor EMT adjacent to stroma d=0.74 | caution (moderate niche association) |
| R6 co-culture | Kang two-step chain | complete Mono→CD8T chain | accept; broken megakaryocyte chain downgrade |

R6 illustrates governance preventing overclaiming: the same IFN perturbation supports ISG activation but receives a downgrade for metabolic tendency; the same CXCL10 signal is accepted for CXCR3⁺ cells and downgraded for CXCR3^low cells; metabolic antibiotic targets are accepted while non-metabolic targets trigger abstention. Successful execution alone never warrants an accepted conclusion.

`GemModel`, `scoring.py`, `CaseReport`, and route-table engines are reused across cases. Changing an SBML model changes the species; changing a panel changes the scored program. Engines include donor_predictor/gem_fba/embedding/state_scoring/pathway_scoring/communication/spatial_niche/reject. No new predictive model is trained in these demonstrations.

## 4. External baselines and per-cell analysis

- **G2 resolves the W4.5 single-control limitation.** Disagreement now uses each cell's own control instead of `ds[0].control`, across 18874 cells. Recalculation on Mac changes learned AUROC 0.907→**0.869**, risk-coverage 0.746→**0.736**, and regression correlation 0.701→0.646. The single-control analysis was slightly optimistic, but the governance ranking remains robust: learned > disagreement > random; unchanged OOD/oracle controls support correct recalculation. Source: `finding_g2_percell_w45`.
- **G1 scGen/STATE remains blocked.** scgen 2.1.0 is incompatible with scvi-tools 1.4.2 because `scvi._compat` was removed; pinning an older scvi would downgrade torch and disrupt the donor environment. scGen is a condition-transfer model and cannot provide leakage-free predictions for unseen Norman perturbations under this protocol. STATE is a more suitable candidate but needs a separate environment. GEARS 0.4877 fills the matched-protocol baseline gap. No leaked or meaningless scGen/STATE numbers are reported. Source: `finding_g1_scgen_state`.

## 5. LLM communication architecture

- Agent-to-agent communication uses a **deterministic message bus** carrying structured `AgentMessage` objects, not LLM tokens. Defaults are `mode=OFFLINE` and `llm_enabled=False`. All recorded cases, predictions, governance checks, and remote runs used zero LLM tokens.
- `agents_llm/` is an optional enhancement layer (input_interpreter/router/critic/report), activated only by `mode=LLM_ASSISTED` with an available key. The recorded model is `deepseek-chat`, using the OpenAI-compatible `/chat/completions` interface, temperature 0, and max 1024 tokens; failures fall back to deterministic behavior. It never enters the numerical prediction core.

## 6. Evidence limitations

- **Perturbation-level metrics differ from per-cell metrics.** AUROC and risk-coverage are perturbation-level and must not be presented as the per-cell 0.70 result.
- **No SOTA claim.** The framework reproduces and integrates donor predictors. GEARS 0.4877 is matched-protocol; scGen/STATE have no result because G1 remains blocked.
- **Non-human/non-gene cases are governed demonstrations.** They show applicability assessment, routing, downgrade, and abstention, not complete predictors for every domain. Marker scores, co-expression, and FBA are proxies, not direct measurements of flux or signal transduction.
- Some cell-state/EMT/niche cases characterize existing state rather than perturbation-induced transitions, including R4/R5.
- Cases use curated public-data demonstration subsets and stated default thresholds, not tuned thresholds.

## 7. Historical verification and implementation

At this snapshot, tests were **203 passed + 25 skipped**, and no predictive model was trained. The packages cover `governance/` (reliability/abstain/ledger/artifacts), `predictors/` (mechanistic GEM, embedding drug, state, spatial, communication, and donor ML bridges), `agents/` (schema/route/case_report and bus communication), and optional `agents_llm/`.

Large source data were excluded from Git; curated subsets and URL/SHA-256 provenance were retained for LINCS/iMM904/iML1515/Kang/paul15/mcfarland/imc. Historical remote computation used an A100 and torch 2.6+cu124. Further scGen/STATE comparisons require an independent environment. The representative demonstrations collectively cover 5×4 species/application categories.

## 8. Evidence index

Related summaries: [consolidated results](paper/v0.4/RESULTS-CONSOLIDATED.md) and [data inventory](paper/v0.3/data-inventory.md).

Historical finding identifiers (retained as source labels in the figure scripts): `finding_w9_l4_gears_same_split`, `finding_g2_percell_w45`, `finding_g1_scgen_state`, and `finding_v0_4_*` / `finding_v0_5_*` (16 cases). Runtime implementation: `praxis_virtualcell/governance/` and `praxis_virtualcell/agents/{species_schema,route_table,case_report}.py`.
