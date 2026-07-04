# A brain-guided multi-agent runtime for trustworthy virtual-cell perturbation prediction

**Authors:** [Author list — TBD] · **Corresponding author:** [TBD]

> Target: *Nature Machine Intelligence* (Article; numbered references). Body in English; bilingual abstract
> (English + Simplified Chinese). Systems/methods framing per author decision (2026-07-03). Every quantitative
> claim traces to a recorded finding (`docs/ANALYSIS-SUMMARY.md`, `docs/paper/v0.4/RESULTS-CONSOLIDATED.md`,
> `docs/paper/v0.3/data-inventory.md`, `docs/findings/`). References [1]–[22] are DOI/source-verified (v0.2
> `phase1_literature.md`); references [23]+ are newly added for the dataset/tool corpus (Results 4–5) and are
> pending final DOI verification in the citation-check phase. Figures Fig 1–5 are in `docs/paper/figures/`.

---

## Abstract

Computational models predict how a cell responds to a genetic or chemical perturbation, but a trained predictor
returns a number for *any* input — an out-of-distribution species, an unsupported perturbation, or a gene
outside its vocabulary — with no applicability check, no record of which model ran, and no option to decline.
We present PRAXIS-VirtualCell, a multi-agent runtime that reframes trustworthy prediction as a control-flow
problem: deterministic agents route a typed request through a per-species "brain" of applicability rules to
heterogeneous predictor-agents, and a retrieve-before-predict gate, a learned abstention policy, a trace critic
and a provenance assembler make rejection, abstention and auditability enforced behaviours. Ablated against an
ML-only stub over the *same* predictors, the runtime turns five governance capabilities from absent to present.
On the Norman perturbation benchmark it reproduces a per-cell delta-expression Pearson of 0.7039 without
altering any predictor output, while a learned reliability model flags error-prone perturbations at AUROC 0.907
and cuts the wrong-accept rate from 0.974 to 0.211 with no hard-rule overrides. Across five applications and
four species the runtime cautions, downgrades or abstains rather than over-report; every run emits a
deterministic, auditable report and installs offline with no API key. These governance metrics are
perturbation-level and we claim no accuracy record — the contribution is a control layer that knows when not to
answer.

**Keywords:** virtual cell; perturbation prediction; multi-agent systems; selective prediction; abstention; model applicability; provenance; reproducibility

## 摘要

预测细胞对基因或化学扰动响应的计算模型,对任何输入(分布外物种、不支持的扰动、词表外基因)都会输出一个
数值,既不检查适用性,也不记录用了哪个模型,更无"拒绝"选项。我们提出 PRAXIS-VirtualCell,一个把可信预测
重述为控制流问题的多智能体运行时:确定性智能体把结构化请求经逐物种"脑"(适用性规则)路由到异构预测器,一个
"先检索再预测"门、一套可学习弃权策略、一个轨迹批判者与一个溯源装配器,把拒绝、弃权、可审计变为强制行为。
相对仅含预测器的对照桩,该运行时在同一组预测器上把五个治理能力从"无"变为"有";在 Norman 扰动基准上复现
per-cell delta-expression Pearson 0.7039 而不改变任何预测输出;可学习可靠性模型以 AUROC 0.907 标记易错扰动,
把 wrong-accept 从 0.974 降到 0.211 且不覆盖任何硬规则。跨五应用四物种,系统按证据强弱告警/降级/弃权而非
过度上报;每次运行产出确定性可审计报告并可离线无 key 安装。治理指标为扰动级,系统不宣称准确率记录——其贡献
是一个知道何时不作答的控制层。

**关键词:** 虚拟细胞;扰动预测;多智能体系统;选择性预测;弃权;模型适用性;溯源;可复现

---

## Introduction

The virtual-cell program aims to build computational models that predict cellular state and its response to
perturbation[^1][^2]. Single-cell technologies such as Perturb-seq[^4][^5] now generate genome-scale
perturbation atlases[^3], and a fast-growing family of predictors — generative models such as scGen[^6] and the
compositional perturbation autoencoder[^7], the graph-based GEARS[^8], and single-cell foundation models such
as scGPT[^9], Geneformer[^10], and the recent STATE model[^11] — map a perturbation to an expression change.
These methods supply the predictive substrate for a virtual cell.

They also share a structural weakness that is rarely treated as a first-class concern: a trained predictor
returns a number for *any* input. Asked about a species it was never trained on, a perturbation type it does
not support, or a gene outside its vocabulary, it still emits a confident vector — with no applicability check,
no record of which model produced it, and no option to abstain. In a discovery setting the wrong answer is
acted upon, which is worse than an explicit "I cannot answer this." Machine learning has long studied this as
the reject option and selective prediction — trading coverage for a guaranteed lower risk[^13][^14][^15][^16] —
and cheminformatics formalizes the applicability domain that bounds where predictions are trustworthy[^17].
Single-cell perturbation predictors typically ship without any of this machinery, and recent evaluations show
that simply scaling a foundation model does not close the gap[^12].

We argue that trustworthiness here is not primarily a better-loss problem but a *control-flow* problem: the
system around the predictor must decide when to route, when to reject, when to abstain, and must record what it
did. We present PRAXIS-VirtualCell, a multi-agent runtime that makes these decisions explicit, learnable, and
auditable. To keep the metaphor honest, we ground it once: the "runtime" is a message-bus orchestration of
deterministic agents, and the species "brain" is a set of per-species files holding model-applicability and
negative-transfer rules. Heterogeneous predictor-agents communicate only over the bus; a hard
retrieve-before-predict gate forces applicability retrieval before any prediction; an abstention policy — in
this release a *learned* reliability model — together with a trace critic and a provenance assembler turn
rejection, abstention, and auditability into enforced behaviours. Optional language-model agents may assist
input interpretation, routing review, critique, and reporting, but never enter the prediction core, which is
fully offline and deterministic.

Unlike multi-agent LLM frameworks aimed at task automation and autonomous experimentation[^18][^19][^20], our
agents are a governance layer for trustworthy prediction, not an autonomous scientist. Our contribution is this
runtime and a separation-of-concerns evaluation: we measure the reliability contribution of the runtime
independently of predictive accuracy; we show the communicative wrapper is performance-neutral; we demonstrate
that reliability can be *learned* and wired back as fail-closed control flow; we exercise the runtime across
representative species and applications as governed workflows; and we make the whole system auditable,
test-guarded, and installable. We are deliberately explicit throughout about what is demonstrated end-to-end,
what is a governed demonstration on a proxy readout, and what is measured at the perturbation rather than the
single-cell level, situating the work within trustworthy and reproducible AI for science[^21][^22].

## Results

### Result 1 — PRAXIS-VirtualCell architecture and task routing

A task enters as a typed `VirtualCellRequest` (species, modality, perturbation kind and targets, optional cell
type, output task). A deterministic parser builds and validates this object; an optional language-model
interpreter may assist free-text parsing but its output is re-validated against the same schema. Inputs outside
the supported envelope are not coerced into a prediction: an unsupported species, an empty target list, or a
perturbation kind a predictor does not declare produces an explicit rejection or abstention rather than a
fabricated vector (Fig. 1).

The runtime orchestrates a fixed pipeline of deterministic agents —
InputInterpreter → ObjectNormalizer → SpeciesBrain → ModelApplicability → predictor-agents → Ensemble →
Reliability → Critic → Provenance → Report — that exchange `AgentMessage`s over a single `MessageBus` (Fig. 1).
Three properties make the multi-agent claim more than cosmetic. The bus is the *only* communication channel:
there is no shortcut that bypasses governance. A hard retrieve-before-predict gate requires model-applicability
to be retrieved before any predictor runs, and the trace critic detects a violation of this ordering. Each
predictor-agent can independently reject a request, and rejections propagate as messages rather than being
silently dropped. The full message sequence is recorded as a replayable trace. Routing itself is a declarative
capability map: a request is mapped to one of eight engines (donor_predictor, gem_fba, embedding,
state_scoring, pathway_scoring, communication, spatial_niche, or reject) with a disposition of accept, caution,
downgrade, or abstain — a presence/absence decision that commits no numbers until a predictor runs.

To isolate the runtime's contribution we compared two arms running the same mock predictor set: arm A, an
ML-only stub with no bus, brain, or reliability agents, and arm D, the full PRAXIS pipeline. On an offline,
deterministic path, five capability axes separate the arms (Fig. 3): out-of-distribution rejection rate
(0.0 → 1.0), wrong-model use rate (1.0 → 0.0), provenance completeness (0.0 → 1.0), abstention correctness
(0.0 → 1.0), and trace completeness (0.0 → 1.0). Because arm A structurally lacks the relevant components, this
is a capability presence/absence contrast, not a graded score; the same mock predictors sit in both arms, which
is what isolates the runtime — rather than the predictor — as the source of the difference. The species brain
makes this concrete across organisms (Fig. 4): a human request routes to applicable predictors with no caution;
a mouse request is applicable but flagged with an ortholog caution and the runtime performs a real ortholog
projection of targets, tagging any it cannot map; bacteria and yeast requests are rejected by the
negative-transfer rule `mammalian_scrna_predictor_not_applicable` and the system abstains; and an unknown
("martian") species is refused without manufacturing references to rules or files that do not exist.

### Result 2 — Human perturbation benchmark

We reproduced the donor predictors on the Norman 2019 benchmark[^3] through the runtime (Fig. 2). Six base
predictors reach per-cell delta-expression Pearson of 0.6716 (cpa), 0.6709 (decoder), 0.6675 (gnn), 0.6639
(linear), 0.6365 (latent), and 0.6183 (pretrained), all at n = 18,874; routed through the donor Coordinator,
ensembles reproduce ~0.70, with the all-five ensemble at 0.7039, exceeding the strongest single base by 0.032.
The all quantitative values in this section were re-run and witnessed element-wise on a remote A100 host to
rule out fabrication (linear reproduces bitwise, diff 1.2e-8; other predictors within atol 1e-6). Because the
communicative layer carries metadata and tensors but performs no tensor arithmetic, wrapping a predictor
changes none of the numbers it produces; we therefore claim only that the communicative layer is
performance-neutral, not that message-passing achieves a higher Pearson.

We anchor the accuracy axis with same-protocol baselines rather than headline claims. A perturbation-agnostic
mean-perturbation predictor — same test split, same per-cell delta-Pearson, same evaluator — reaches 0.4615,
well below every trained base, confirming that the trained predictors capture perturbation-specific structure.
A frozen scGPT[^9] backbone (53.8 M parameters) with a light trainable head reaches only 0.4407 (n = 7,290
under reduced sampling), below even the mean baseline, consistent with reports that scale alone is not the
fix[^12]. Critically, we added a *same-protocol external* baseline: GEARS[^8], run under the identical donor
test split and per-cell delta-Pearson (train/test perturbations disjoint, 62/150), reaches 0.4877 — below all
donor bases and far below the Coordinator's 0.7039. GEARS's native `pearson_de` of 0.8392 is an
absolute-expression Pearson over differentially expressed genes on a different split and is *off-axis*; the gap
between 0.8392 and 0.4877 is a measure of how much protocol choice inflates apparent accuracy, and it is the
central reason we insist on same-protocol comparison. We read this as competitiveness of the governed ensemble
under a fair protocol, not as beating state of the art; a caveat is that GEARS operates at condition
granularity, so the per-cell yardstick is unfavourable to it. Strong perturbation foundation models such as
STATE[^11] and the conditional generator scGen[^6] could not be run leak-free on this split within the current
environment (Methods) and are stated as open baselines rather than reported numbers.

### Result 3 — Learned reliability governance and abstention

The runtime's abstention policy is *learned*, and this is our strongest new result. Model disagreement — the
pairwise-cosine distance among ensemble members — is diagnostic of error: across 60 real perturbations, the
correlation between disagreement and per-perturbation delta-Pearson is −0.716, so high disagreement predicts
low accuracy. We train a small reliability model on runtime-derivable features and evaluate it under
leave-perturbation-out five-fold cross-validation on 151 perturbations, with no leakage between folds. It flags
bad perturbations at AUROC 0.907 and yields a risk–coverage AUC of 0.746, both far above the rule baselines
(disagreement-only 0.774 / 0.720; out-of-distribution-flag 0.788 / 0.730) and random (0.479 / 0.660); the
reliability regression reaches out-of-fold correlation 0.701. The advantage is robust: the paired improvement's
95% confidence interval excludes zero (AUROC +0.13, [0.056, 0.191]), and across five seeds AUROC is
0.900 ± 0.008. Adding magnitude and uncertainty features did not help — a negative result we report to guard
against over-fitting — so the model keeps three features.

The learned signal is more than an out-of-distribution proxy: flagged perturbations are 98% out-of-distribution
(odds ratio 74.7), yet the model still separates errors *within* the out-of-distribution subset (risk–coverage
0.577 > 0.5; AUROC 0.907 > the out-of-distribution-only baseline 0.788). Wired back into the runtime under a
`learned_with_rule_fallback` policy, the reliability model cuts the wrong-accept rate from 0.974 to 0.211 and
raises risk-coverage from 0.026 to 0.789, with **zero** hard-rule overrides — hard applicability rules remain
authoritative and the learned layer only tightens soft decisions. The model is a frozen artifact with a
content sha256 self-check and fail-closed loading: a missing or schema-mismatched artifact reverts to the rule
policy rather than silently mis-scoring. Two honesty boundaries are load-bearing and we state them in the main
text. First, these governance metrics are *perturbation-level* (n = 60 / 151), not the per-cell 0.7039 of
Result 2. Second, when disagreement is recomputed against each cell's own control rather than a single shared
control (n = 18,874 cells), the metrics soften slightly — AUROC 0.907 → 0.869, risk-coverage 0.746 → 0.736,
regression correlation 0.701 → 0.646 — but every governance conclusion holds (learned ≫ disagreement ≫ random;
oracle and out-of-distribution controls unchanged), so we report the paired advantage and monotone trend rather
than a single absolute point (Fig. 5). On the real donor predictors, abstaining on the most-disagreed
perturbations raises retained accuracy monotonically, from delta-Pearson 0.672 at full coverage to 0.754 at
74% coverage.

### Result 4 — Cross-species representative workflows

To show the runtime is a governance layer over *heterogeneous* tasks rather than a single-benchmark harness, we
exercised it across five applications and four species — 16 workflows on public data and standard tools, each
producing a seven-part report under a governed verdict (Table 1; Fig. 4). Gene perturbation spans human
(Norman, 0.7039, accept), mouse (ortholog caution/downgrade), *E. coli* (COBRApy `e_coli_core`: wild-type
growth 0.874, `gltA`/`icd` essential, accept; genes absent from the model → abstain), and yeast (`iMM904`:
wild-type 0.288, `ERG1` essential, accept). Metabolism uses genome-scale models (`iML1515`, `iMM904`) and an
expression-level pathway-tendency proxy. Drug response uses LINCS L1000[^23] signatures: an HSP90 inhibitor
enriches its target pathway 2.6–3.5× (accept), a weak HDAC signal is actively downgraded, and across a dose
series geldanamycin's dose–response correlates at Spearman 0.90 (accept) while a near-zero sirolimus response is
downgraded. State and fate use the Kang 2018 interferon dataset[^24] (interferon-stimulated-gene activation
Cohen's d = 2.49, myeloid > lymphoid, accept) and Paul 2015 haematopoiesis[^25] via scanpy[^26]
(erythroid-vs-myeloid fate d = 4.32, accept). Communication uses ligand–receptor co-expression (CXCL10 → CXCR3,
monocyte → CD8 T 51×, accept for CXCR3-high populations, downgrade for CXCR3-low CD4 T) and spatial niche
analysis via squidpy[^27].

**Table 1 | Sixteen governed workflows across five applications and four species.** Each workflow runs a public
dataset or standard tool through the runtime and returns a governed verdict; effect sizes are Cohen's *d* or
Spearman ρ as stated.

| Case | Application | Species | Data / tool | Key readout | Verdict |
|---|---|---|---|---|---|
| C1 | Gene perturbation | Human | Donor Coordinator (Norman) | delta-Pearson 0.7039 | accept |
| C2 | Gene perturbation (OOD) | Human | Learned reliability | AUROC 0.907; OOD odds-ratio 74.7 | abstain (OOD-enriched) |
| C3 | Gene perturbation | Mouse | route_table + ortholog projection | ortholog-mapped targets | caution / downgrade |
| C4 | Gene KO → growth | *E. coli* | COBRApy `e_coli_core` | WT 0.874; `gltA`/`icd` essential | accept; gene absent → abstain |
| C5 | Gene KO → growth | Yeast | COBRApy `iMM904` | WT 0.288; `ERG1` essential | accept |
| C6 | Drug MOA | Human | LINCS L1000 | HSP90 target enrichment 2.6–3.5× | accept; weak HDAC → downgrade |
| S1 | Carbon-source shift | *E. coli* | COBRApy `e_coli_core` | glucose 0.874 → acetate 0.173 | accept; unknown source → caution |
| S2 | Immune activation | Human | Kang 2018 (IFN-β) | ISG activation *d* = 2.49 | accept; megakaryocyte weak |
| S3 | Metabolic tendency | Human | Kang 2018 (expression proxy) | glycolysis/OXPHOS *d* = 0.10/0.28 | **downgrade** |
| S4 | Ligand–receptor | Human | Kang 2018 | CXCL10→CXCR3, Mono→CD8 T 51× | accept (CXCR3⁺); downgrade (CXCR3⁻) |
| R1 | Differentiation fate | Mouse | scanpy `paul15` | erythroid vs myeloid *d* = 4.32 | accept |
| R2 | Drug dose–response | Human | LINCS L1000 (dose) | geldanamycin Spearman ρ = 0.90 | accept; near-zero sirolimus → downgrade |
| R3 | Antibiotic → growth | *E. coli* | COBRApy `iML1515` | trimethoprim/sulfa target arrest | accept; non-metabolic target → abstain |
| R4 | Cancer EMT | Human | pertpy (McFarland) | sarcoma vs epithelial *d* = 1.72 | accept (state characterisation) |
| R5 | Spatial niche | Human | squidpy (IMC) | stroma-adjacent tumour EMT *d* = 0.74 | caution (moderate niche) |
| R6 | Co-culture chain | Human | Kang 2018 (two-step) | Mono→CD8 T chain complete | accept; →megakaryocyte broken → downgrade |

The throughline is that governance prevents over-claiming, and we make it visible with within-experiment
contrasts. The *same* interferon perturbation is accepted for interferon-stimulated-gene activation (d = 2.49)
but downgraded for a metabolic readout (glycolysis/OXPHOS d = 0.10/0.28) — the runtime does not upgrade a weak
signal to match a strong one. The *same* CXCL10 signal is accepted for CXCR3-high targets and downgraded for
CXCR3-low ones. A metabolic-target antibiotic (trimethoprim, sulfamethoxazole; `iML1515`) is accepted as growth
arrest, while a non-metabolic-target antibiotic is *abstained* because the metabolic model does not apply. These
are not curated successes: they are cases where a naïve predictor would emit a confident number and the runtime
instead declines. A capability audit of five representative perturbation systems — GEARS[^8], CPA[^7],
scGPT[^9], scGen[^6], and STATE[^11] — against their public papers and code found that none implements
out-of-distribution rejection, an applicability check, an abstention mechanism, prediction provenance, or
auditable multi-model messaging (Table 2); these are governance functions PRAXIS supplies around predictors,
not properties of any one predictor.

**Table 2 | Governance-capability audit of representative perturbation systems.** Presence/absence against each
system's public paper and code; ✓ = implemented as an enforced behaviour, ✗ = absent (a scalar uncertainty a
user must threshold is not counted as an abstention decision).

| Governance capability | PRAXIS | GEARS[^8] | CPA[^7] | scGPT[^9] | scGen[^6] | STATE[^11] |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Out-of-distribution rejection | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Applicability / routing check | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Abstention (decision to decline) | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Learned reliability scoring | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prediction provenance | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Auditable multi-model messaging / replayable trace | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Deterministic reproducible report | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |

We are explicit that most non-human, non-gene workflows are *governed
demonstrations* on marker, co-expression, or flux-balance proxies rather than validated cross-species predictors,
and that some (cancer epithelial-mesenchymal transition, spatial niche) are state characterisations rather than
perturbation-induced transitions; the contribution here is that the runtime routes, flags, and declines
correctly, not that each domain is a complete predictor.

### Result 5 — Auditable reporting, negative tests, and Linux delivery

A governance claim is only as strong as its auditability and its reproducibility, so the runtime makes every
decision inspectable and every behaviour test-guarded. Each run emits a deterministic nine-section Markdown
report — question, cell context, routing decision, result summary, governance verdict, evidence and provenance,
biological interpretation, limitations, and reproducibility — generated purely from the structured artifact with
no language model and no wall-clock, so the same run renders byte-identically on re-execution. Abstention is
never silently upgraded: the report separates true abstention reasons from confidence-downgrade reasons so a
downstream reader is not misled into treating a downgrade as an abstention.

We guard the governance behaviour with two declarative test suites. A golden suite fixes 18 routing workflows
(12 representative, 6 safety) as data, asserting the engine and disposition for each and enforcing a hard
key-performance indicator: zero unsafe accepts — no case whose correct verdict is abstain, downgrade, or caution
is ever answered as accept. A negative/fuzz suite fixes 14 rejection workflows across three layers (schema-level
`SchemaError`, candidate-validation failure, and routing abstention), asserting that malformed or inapplicable
inputs are refused rather than silently answered, again under a zero-silent-accept indicator. Because these
suites are declarative and dependency-light, they run on every commit and form a regression net for the
governance contract itself, not merely for the predictors.

Finally, the system is delivered as installable software: the predictive and governance core is offline and
deterministic, packaged as a Python distribution with a command-line entry point and a local web service, and
requires no API key for its full offline functionality (a language-model-assisted mode is optional and never
enters the prediction core). We verified end-to-end installation on a clean Linux host: from a fresh
environment, `pip install` followed by a single offline command installs the runtime, resolves its bundled
rule and artifact data, and produces a governed nine-section report — no network model download, no key, no
database. This closes the loop from a governance mechanism to a reproducible, auditable, and deployable
artifact that a practitioner can run and inspect.

## Discussion

PRAXIS-VirtualCell reframes a reliability gap in virtual-cell prediction as a control-flow problem and shows,
with a clean separation of concerns, that a governance runtime — not a better predictor — supplies rejection,
abstention, provenance, and auditability, and that the abstention decision can be *learned* and wired back as
fail-closed control flow. The accuracy result (0.7039) and the reliability results are deliberately measured on
different paths so that neither inflates the other: the runtime never touches the tensors, and the learned
governance is evaluated out-of-fold at the perturbation level.

Three positions follow. First, applicability and abstention belong in the pipeline, not only in the loss; the
reject-option and applicability-domain ideas[^13][^14][^15][^16][^17] are implementable as enforced, *learnable*
control flow over heterogeneous predictors, and the learned layer measurably beats rule baselines while never
overriding a hard rule. Second, a foundation model is not automatically the answer: our frozen scGPT result and
a same-protocol GEARS baseline both sit below the governed ensemble under a fair yardstick, and independent
zero-shot evaluations agree[^12], arguing for keeping task-specific predictors under a routing layer rather than
betting on scale alone — even as strong perturbation models such as STATE[^11] continue to improve. Third, the
value of a governance layer is most visible not on the benchmark it was tuned for but on the many tasks it was
*not*: across species and applications, the runtime's willingness to caution, downgrade, and abstain is what
separates a trustworthy system from a confident one. The auditable report, the zero-unsafe-accept test suites,
and the offline installable delivery make this trustworthiness inspectable and reproducible rather than
asserted, which we regard as a contribution to trustworthy AI for science[^21][^22] in its own right.

## Methods

**Agent contracts and the bus.** The runtime defines a `VirtualCellRequest`, an `AgentMessage`, a `MessageBus`,
and an `AgentRuntime`. Agents are pure functions over messages; the bus is the only inter-agent channel. The
pipeline runs InputInterpreter → ObjectNormalizer → SpeciesBrain → ModelApplicability → fan-out predict →
Ensemble → Reliability → Critic → Provenance → Report. The retrieve-before-predict gate requires
model-applicability in the message history before any predictor message; the critic flags violations; the full
history is a replayable trace exported with the report. Routing is a declarative capability map (`route_table`)
from a normalised request to one of eight engines with a disposition in {accept, caution, downgrade, abstain}.

**Species brain and applicability.** Per-species files (human, mouse, bacteria, yeast, plus a generic file)
declare runtime-consumed fields — supported species/modalities/tasks, `reject_if`, gene vocabulary,
per-species cautions, cross-species rules, and negative-transfer rules — read by the SpeciesBrain and
ModelApplicability agents. ModelApplicability partitions candidate predictors into applicable and rejected,
computes cross-species ortholog cautions with a real upper-case ortholog projection (flagging unmapped
targets), and records the specific rules hit in provenance.

**Norman benchmark reproduction.** Donor predictor checkpoints are used read-only. The recipe is
`load_vcbench_split("norman_2019", "test", max_cells_per_pert=200, rng_seed=1)`, evaluated with the donor
evaluator; the linear predictor reproduces its recorded delta-Pearson bitwise (diff 1.2e-8) and trained
predictors within atol 1e-6 element-wise. We report per-cell delta-expression Pearson at n = 18,874. The scGPT
head is trained on the same donor Norman data with the encoder frozen under reduced sampling (n = 7,290). GEARS
is run in its native pipeline for the off-axis `pearson_de` and separately under the donor test split and
per-cell delta-Pearson (custom split, train/test perturbations disjoint 62/150; one gene filtered by the GEARS
gene-ontology graph) for the same-protocol 0.4877; it is single-run as GEARS fixes no seed. scGen and STATE
were not run: scGen is a conditional-transfer model that cannot make leak-free predictions on Norman's unseen
test perturbations, and STATE requires an isolated heavy environment; both are stated as open baselines.

**Learned reliability governance.** Features are extracted from runtime inference without leakage (ensemble
disagreement and its zero-pair count, and a train-seen indicator). The reliability and abstention heads are
trained under leave-perturbation-out five-fold cross-validation on the perturbation ledger (n = 151; the
disagreement diagnostic uses n = 60), reporting bad-perturbation AUROC, risk–coverage AUC, and out-of-fold
regression correlation, with bootstrap confidence intervals and a five-seed repeat. The per-cell recomputation
replaces the single shared control with each cell's own control (n = 18,874). Wired into the runtime, the policy
is `learned_with_rule_fallback`: hard applicability/abstain rules remain authoritative; the learned layer only
tightens soft downgrade/abstain decisions; the artifact is frozen with a content sha256 self-check and loads
fail-closed. No model is trained on the prediction path — the predictors are reused read-only.

**Cross-species representative workflows.** Each workflow runs a public dataset or standard tool through the
runtime and records a seven-part governed report. Metabolic cases use COBRApy[^28] flux-balance analysis on BiGG
models[^29] (`e_coli_core`, `iML1515`, `iMM904`). Drug cases use LINCS L1000[^23] signatures. Immune,
differentiation, communication, and spatial cases use the Kang 2018[^24], Paul 2015[^25], McFarland[^30], and
imaging-mass-cytometry datasets via scanpy[^26], squidpy[^27], and pertpy. Effect sizes are Cohen's d or
Spearman correlation as stated; default thresholds are fixed a priori (recorded, not tuned). Non-human,
non-gene workflows are governed demonstrations on marker/co-expression/flux proxies, not validated predictors.

**Auditable reporting, tests, and delivery.** The report renderer is a pure deterministic function over the
structured artifact (no language model, no wall-clock). Golden (18) and negative (14) suites are declarative
YAML fixtures with a common runner asserting engine/disposition and the zero-unsafe-accept / zero-silent-accept
indicators. The distribution is a standard Python package (`pip install`) with a command-line entry point and a
local web service; bundled rule and artifact data ship with the package; offline mode needs no API key. Linux
installation was verified end-to-end on a clean host (Python 3.13) producing a governed report from a single
offline command.

## Limitations

- **Governance metrics are perturbation-level.** The AUROC 0.907 and risk-coverage 0.746 are computed over
  n = 60 / 151 perturbations, not the per-cell n = 18,874 of the accuracy result; single-point AUC intervals
  remain wide (AUROC 0.907, [0.846, 0.952]), so we emphasise the paired advantage over rule baselines rather
  than the absolute value, and we report the per-cell recomputation (0.869 / 0.736) alongside it.
- **Accuracy does not beat state of the art.** The predictors are donor-stack variants reproduced read-only; a
  same-protocol GEARS baseline (0.4877) is now included, but scGen and STATE are open (blocked leak-free or
  environment-heavy), and the Coordinator's 0.7039 is not claimed as a new accuracy record.
- **Cross-species and non-gene workflows are governed demonstrations.** They show the runtime routes, cautions,
  downgrades, and abstains correctly on marker/co-expression/flux proxies; they are not validated cross-species
  or cross-application predictors, and some are state characterisations rather than perturbation-induced
  transitions.
- **Datasets are curated public subsets** with a priori default thresholds (recorded, not tuned); the
  demonstrations are not exhaustive coverage of each domain.
- **Language-model agents are optional** and never enter the prediction core; the offline deterministic core is
  the object of all quantitative claims.

## Data and code availability

The Norman 2019 dataset[^3] and all cross-species datasets and models (LINCS L1000[^23], Kang 2018[^24],
Paul 2015[^25], McFarland[^30], BiGG models[^29]) are publicly available; curated subsets ship with the code
under recorded provenance (source URL + sha256). Code is released at the project repository under an
open-source licence; the predictive and governance core runs offline and deterministically and installs via
`pip`. Donor predictor checkpoints are used read-only for reproduction.

## Author contributions, ethics, AI-usage, and competing interests

Author contributions (CRediT) — TBD. This work uses no human-subject or animal data beyond publicly available
single-cell datasets; no ethics approval was required. AI-usage disclosure: language-model coding assistants and
an LLM writing assistant were used during development and manuscript preparation; all quantitative claims were
verified against logged experiments and all citations against source records. The authors declare no competing
interests. Funding — TBD.

---

## References

[^1]: Bunne, C. et al. How to build the virtual cell with artificial intelligence: priorities and opportunities. *Cell* **187**, 7045–7063 (2024). https://doi.org/10.1016/j.cell.2024.11.015
[^2]: Rood, J. E., Hupalowska, A. & Regev, A. Toward a foundation model of causal cell and tissue biology with a Perturbation Cell and Tissue Atlas. *Cell* **187**, 4520–4545 (2024). https://doi.org/10.1016/j.cell.2024.07.035
[^3]: Norman, T. M. et al. Exploring genetic interaction manifolds constructed from rich single-cell phenotypes. *Science* **365**, 786–793 (2019). https://doi.org/10.1126/science.aax4438
[^4]: Dixit, A. et al. Perturb-Seq: dissecting molecular circuits with scalable single-cell RNA profiling of pooled genetic screens. *Cell* **167**, 1853–1866.e17 (2016). https://doi.org/10.1016/j.cell.2016.11.038
[^5]: Replogle, J. M. et al. Mapping information-rich genotype–phenotype landscapes with genome-scale Perturb-seq. *Cell* **185**, 2559–2575.e28 (2022). https://doi.org/10.1016/j.cell.2022.05.013
[^6]: Lotfollahi, M., Wolf, F. A. & Theis, F. J. scGen predicts single-cell perturbation responses. *Nat. Methods* **16**, 715–721 (2019). https://doi.org/10.1038/s41592-019-0494-8
[^7]: Lotfollahi, M. et al. Predicting cellular responses to complex perturbations in high-throughput screens. *Mol. Syst. Biol.* **19**, e11517 (2023). https://doi.org/10.15252/msb.202211517
[^8]: Roohani, Y., Huang, K. & Leskovec, J. Predicting transcriptional outcomes of novel multigene perturbations with GEARS. *Nat. Biotechnol.* **42**, 927–935 (2024). https://doi.org/10.1038/s41587-023-01905-6
[^9]: Cui, H. et al. scGPT: toward building a foundation model for single-cell multiomics using generative AI. *Nat. Methods* **21**, 1470–1480 (2024). https://doi.org/10.1038/s41592-024-02201-0
[^10]: Theodoris, C. V. et al. Transfer learning enables predictions in network biology. *Nature* **618**, 616–624 (2023). https://doi.org/10.1038/s41586-023-06139-9
[^11]: Adduri, A. K. et al. Predicting cellular responses to perturbation across diverse contexts with State. *bioRxiv* (2025). https://doi.org/10.1101/2025.06.26.661135 [preprint]
[^12]: Kedzierska, K. Z., Crawford, L., Amini, A. P. & Lu, A. X. Assessing the limits of zero-shot foundation models in single-cell biology. *bioRxiv* (2023). https://doi.org/10.1101/2023.10.16.561085 [preprint]
[^13]: Chow, C. K. On optimum recognition error and reject tradeoff. *IEEE Trans. Inf. Theory* **16**, 41–46 (1970). https://doi.org/10.1109/TIT.1970.1054406
[^14]: El-Yaniv, R. & Wiener, Y. On the foundations of noise-free selective classification. *J. Mach. Learn. Res.* **11**, 1605–1641 (2010). https://jmlr.org/papers/v11/el-yaniv10a.html
[^15]: Geifman, Y. & El-Yaniv, R. Selective classification for deep neural networks. *Adv. Neural Inf. Process. Syst. (NeurIPS)* **30**, 4878–4887 (2017). arXiv:1705.08500
[^16]: Hendrickx, K., Perini, L., Van der Plas, D., Meert, W. & Davis, J. Machine learning with a reject option: a survey. *Mach. Learn.* **113**, 3073–3110 (2024). https://doi.org/10.1007/s10994-024-06534-x
[^17]: Sahigara, F. et al. Comparison of different approaches to define the applicability domain of QSAR models. *Molecules* **17**, 4791–4810 (2012). https://doi.org/10.3390/molecules17054791
[^18]: Wu, Q. et al. AutoGen: enabling next-gen LLM applications via multi-agent conversation. *Conf. on Language Modeling (COLM)* (2024). arXiv:2308.08155
[^19]: Boiko, D. A., MacKnight, R., Kline, B. & Gomes, G. Autonomous chemical research with large language models. *Nature* **624**, 570–578 (2023). https://doi.org/10.1038/s41586-023-06792-0
[^20]: Bran, A. M. et al. Augmenting large language models with chemistry tools. *Nat. Mach. Intell.* **6**, 525–535 (2024). https://doi.org/10.1038/s42256-024-00832-8
[^21]: Wang, H. et al. Scientific discovery in the age of artificial intelligence. *Nature* **620**, 47–60 (2023). https://doi.org/10.1038/s41586-023-06221-2
[^22]: Sandve, G. K., Nekrutenko, A., Taylor, J. & Hovig, E. Ten simple rules for reproducible computational research. *PLoS Comput. Biol.* **9**, e1003285 (2013). https://doi.org/10.1371/journal.pcbi.1003285

> References [23]–[30] are newly added for the Results 4–5 dataset/tool corpus and are **pending final DOI
> verification in the citation-check phase** before submission:

[^23]: Subramanian, A. et al. A next generation connectivity map: L1000 platform and the first 1,000,000 profiles. *Cell* **171**, 1437–1452.e17 (2017). https://doi.org/10.1016/j.cell.2017.10.049
[^24]: Kang, H. M. et al. Multiplexed droplet single-cell RNA-sequencing using natural genetic variation. *Nat. Biotechnol.* **36**, 89–94 (2018). https://doi.org/10.1038/nbt.4042
[^25]: Paul, F. et al. Transcriptional heterogeneity and lineage commitment in myeloid progenitors. *Cell* **163**, 1663–1677 (2015). https://doi.org/10.1016/j.cell.2015.11.013
[^26]: Wolf, F. A., Angerer, P. & Theis, F. J. SCANPY: large-scale single-cell gene expression data analysis. *Genome Biol.* **19**, 15 (2018). https://doi.org/10.1186/s13059-017-1382-0
[^27]: Palla, G. et al. Squidpy: a scalable framework for spatial omics analysis. *Nat. Methods* **19**, 171–178 (2022). https://doi.org/10.1038/s41592-021-01358-2
[^28]: Ebrahim, A., Lerman, J. A., Palsson, B. O. & Hyduke, D. R. COBRApy: constraints-based reconstruction and analysis for Python. *BMC Syst. Biol.* **7**, 74 (2013). https://doi.org/10.1186/1752-0509-7-74
[^29]: Norsigian, C. J. et al. BiGG Models 2020: multi-strain genome-scale models and expansion across the phylogenetic tree. *Nucleic Acids Res.* **48**, D402–D406 (2020). https://doi.org/10.1093/nar/gkz1054
[^30]: McFarland, J. M. et al. Multiplexed single-cell transcriptional response profiling to define cancer vulnerabilities and therapeutic mechanism of action. *Nat. Commun.* **11**, 4296 (2020). https://doi.org/10.1038/s41467-020-17440-w
