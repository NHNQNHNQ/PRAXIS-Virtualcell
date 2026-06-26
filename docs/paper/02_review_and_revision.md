# Adversarial review → revision disposition (ars-full review/revise)

> 5 independent reviewers (over-claim hunter · number-fidelity · Nature Methods methodologist ·
> writing-quality · desk-reject devil's advocate) ran as a Workflow over the v0.1 draft. The synthesis
> agent died on a transient socket error, so this disposition is hand-synthesized from the 5 structured
> reviews (extracted from the run journal). Verdicts: 2× major_revision (methodologist, devil's advocate),
> 3× minor_revision. **No reviewer found a fabricated number; the over-claim hunter found 5 of 6 honesty
> boundaries handled well** — do not over-correct those.

## Disposition table

| # | Severity | Issue | Raised by | Disposition |
|---|----------|-------|-----------|-------------|
| R1 | CRITICAL | "Ablating the OS from **the same shared predictors** moves 5 axes 0→1" conflates two disjoint paths: accuracy (0.7039) uses donor ML predictors; the A↔D reliability ablation uses the **mock** predictor set. | devil's advocate; methodologist | **FIXED** — decoupled everywhere: reliability ablation stated as running on the offline mock path where A and D share the *same mock set* (which is what isolates the OS); accuracy stated as a separate evaluation on donor ML predictors. Abstract/Results§4/Methods/Fig 3 caption rewritten. |
| R2 | CRITICAL | Arm A is a 12-line stub hardcoding `abstain=False, trace=None, provenance=None` → 4 of 5 axes are 0 **by construction**, definitional not measured. | methodologist; devil's advocate | **FIXED (reframe)** — Fig 3 + Results §4 + Methods now present this as a **capability presence/absence** contrast (arm A structurally lacks bus/brain/reliability, so it cannot trace/abstain/record provenance by definition); explicitly *not* a graded improvement. A real-predictor / intermediate-arm ablation is named as future work. |
| R3 | CRITICAL | No Related Work section; all 13 citations are `[CIT:]` placeholders. | devil's advocate | **PARTIAL (by design)** — citation *resolution* was user-deferred this round. Added a **Related Work section** (positioning prose vs selective prediction / reject option / applicability domain / multi-agent systems) with `[CIT:]` placeholders, so the structural gap is closed; DOI resolution remains the deferred citation pass. |
| R4 | MAJOR | Internal contradiction: "real ortholog projection" both actively executes (Results §4, Fig 4) and is listed as "does not fire" (next para, Limitations). finding_w5 shows projection IS real + tested in routing. | over-claim hunter | **FIXED** — removed ortholog projection from the not-firing list; stated it *is* exercised in the cross-species routing/caution path (finding_w5, Fig 4) over the mock predictor set, and that what awaits a real predictor is using the projection to drive an actual cross-species *prediction*. |
| R5 | MAJOR | Sample size inconsistent / under-specified: bases & Coordinator n=18,874; scGPT n=7,290 (reduced max_cells=50); GEARS n unstated. | methodologist; devil's advocate | **FIXED** — n stated for every Pearson; scGPT reduced-sampling caveat added; GEARS n/split called out as different. |
| R6 | MAJOR | "performance-neutral by construction" / "without sacrificing accuracy" over-reads atol 1e-6 (near-tautological wrapper-identity). | methodologist; devil's advocate; over-claim hunter | **FIXED** — reworded to "the wrapper reproduces the underlying predictor's output element-wise (atol 1e-6), so wrapping changes no numbers"; demoted from a top-line contribution to a sanity check; bus-exclusion made explicit in the Abstract. |
| R7 | MAJOR | GEARS 0.8392 in the same paragraph as 0.7039 invites "GEARS wins" misread despite the disclaimer. | methodologist | **FIXED** — moved GEARS/scGPT into a separated "external-model integration sanity-check" paragraph, never on the same axis as delta-expression Pearson. |
| R8 | MAJOR | Accuracy section has no external baseline; violates the project's own ≥3-baseline invariant (all 6 are donor-stack variants). | devil's advocate | **ACKNOWLEDGED (limitation)** — added to Limitations: the six predictors are donor-stack variants; a same-protocol external baseline (mean-perturbation / GEARS / CPA on the identical split+metric) is not yet available and is future work. Not fabricated. |
| R9 | MAJOR | Norman split not reproducible as written: no `data/manifests/norman_2019.yaml` exists; violates the manifest invariant. | methodologist; devil's advocate | **ACKNOWLEDGED (honesty)** — Methods + Limitations now state the split is defined by the loader recipe but a formal DOI+sha256 manifest is not yet provided (ties to the existing abstain_gain/manifest limitation). No manifest fabricated. |
| R10 | MAJOR | "Operating system"/"brain" over-branded vs implementation (YAML files + bus + deterministic agents). | devil's advocate | **FIXED (ground the metaphor)** — kept the author's deliberate positioning but added a precise grounding sentence (the "OS" = a message-bus runtime of deterministic agents; the "brain" = per-species YAML applicability/negative-transfer rule files) early, so the metaphor is defined, not over-read. |
| R11 | MAJOR | Declarative-vs-active distinction buried in Limitations; mock predictors undercut reliability claims. | devil's advocate; over-claim hunter | **FIXED** — moved a precise "what is demonstrated end-to-end vs declarative vs evaluated-separately" statement into the Abstract and the first reliability paragraph. |
| R12 | MINOR | Test count 75/23 verified-correct in manuscript, but cited RELEASE (71) is stale. | number-fidelity; devil's advocate | **FIXED** — manuscript attributes 75 passed / 23 skipped to "the suite at tag v0.1.0" (reviewer re-ran pytest and confirmed), not to the stale RELEASE; flagged RELEASE for a separate update. |
| R13 | MINOR | scGPT head "2.5 M" rounds finding's 2.47 M. | number-fidelity | **FIXED** — "~2.47 M". |
| R14 | MINOR | Methods reliability says "all four" but lists five abstention triggers. | number-fidelity | **FIXED** — count/list reconciled. |
| R15 | MINOR | +0.032 gain lacks an explicit subject (could be misread as the agent ensemble). | over-claim hunter; methodologist | **FIXED** — attributed to the donor Coordinator's internal ensembling; "confirming" softened to "consistent with"; single-seed noted. |
| R16 | MINOR | 6 seed requests not described in the paper (only in code). | methodologist | **FIXED** — added a seed-request table to Methods. |
| R17 | MINOR/NIT | EN abstract has two ~60-word sentences; "by construction" repeated; "architecture property" repeated. | writing-quality | **FIXED** — long sentences split; repetition reduced. |
| R18 | MINOR | 中文 abstract is a literal translation, has 8 em-dashes in one paragraph, omits scGPT 0.4407. | writing-quality | **FIXED** — Chinese abstract redrafted independently, em-dashes reduced, scGPT clause added. |
| R19 | NIT | GEARS/scGPT not wired into the runtime as predictor-agents; "end-to-end" means pipeline runs. | devil's advocate; over-claim hunter | **FIXED** — clarified they are standalone native pipelines, not yet registered bus predictor-agents. |
| R20 | NIT | Abstract "five axes 0→1" lists wrong-model-use *prevention* while the rate falls 1→0. | number-fidelity | **FIXED** — inversion made explicit. |

## Deliberately NOT done (no-fabrication boundary; these are honest future work)
- A real-predictor and/or intermediate-arm ablation (R2) — requires the remote GPU; named as future work.
- An external-baseline Norman table (R8) and a formal DOI+sha256 manifest (R9) — not fabricated; stated as limitations.
- A numeric abstain-gain / risk-coverage on a held-out OOD split (R8/R9 adjacent) — already a stated limitation; unchanged.
- Bootstrap CIs on the +0.032 gain (R15) — softened the claim instead of inventing a CI.
- Full citation resolution (R3) — user-deferred; only the Related Work *structure* + placeholders added.
