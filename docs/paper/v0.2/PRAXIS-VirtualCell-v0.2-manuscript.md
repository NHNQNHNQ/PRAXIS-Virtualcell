# A brain-guided multi-agent runtime for trustworthy virtual-cell perturbation prediction

**Authors:** [Author list — TBD] · **Corresponding author:** [TBD]

> Methods/systems paper. Body in English; bilingual abstract (English + Simplified Chinese). Target
> format: Nature Methods (numbered references). Every quantitative claim traces to a finding in
> `docs/findings/`; all 22 references are DOI/source-verified (see `v0.2/phase1_literature.md`). Figures
> Fig 1–5 are in `docs/paper/figures/`.

---

## Abstract

Models that predict how a cell responds to a genetic or chemical perturbation are central to the virtual-cell
program[^1][^2], but they share a structural weakness. A trained predictor returns a number for any input —
an out-of-distribution species, an unsupported perturbation type, or a gene outside its vocabulary — with no
applicability check, no record of which model ran, and no option to decline. We present PRAXIS-VirtualCell, a
multi-agent runtime that reframes trustworthy prediction as a control-flow problem. Concretely, the "runtime"
is a message-bus system of deterministic agents and the "brain" is a set of per-species YAML files encoding
model-applicability and negative-transfer rules. A task is parsed into a typed request, routed through the
species brain to heterogeneous predictor-agents that communicate only over an auditable message bus, and a
hard retrieve-before-predict gate, an abstention policy, a trace critic, and a provenance assembler make
rejection, abstention, and auditability enforced behaviors rather than optional add-ons. We evaluate two
questions separately. First, on an offline deterministic path, ablating the runtime (arm A — a stub with no
bus, brain, or reliability agents) from the full system (arm D), both running the *same* mock predictor set,
moves five capability axes from absent to present: out-of-distribution rejection (0→1.0), wrong-model use
(rate 1.0→0), provenance completeness (0→1.0), abstention correctness (0→1.0), and trace completeness
(0→1.0). Because arm A structurally lacks the relevant components, this is a capability presence/absence
contrast, not a graded improvement. Second, on the Norman 2019 benchmark[^3], the predictive layer reproduces
the donor Coordinator's delta-expression Pearson of 0.7039 (n = 18,874). The agent wrapper reproduces each
underlying predictor's output element-wise (atol 1e-6); the communicative layer never runs a forward pass, so
wrapping changes none of the numbers a predictor produces. A frozen scGPT backbone with a light head reaches
only 0.4407, below every task-specific base — and below even a same-protocol mean-perturbation baseline (0.4615)
— consistent with reports that scale alone is not the fix[^12]. The end-to-end reliability path runs on mock
predictors, where a few declarative mechanisms (core-failure and cell-type downgrades) are covered by
activation unit tests and await real predictors. On the real donor predictors, however, a disagreement-based
abstention policy already delivers a positive risk–coverage curve: retained delta-expression Pearson rises from
0.67 to 0.75 as the system declines its most-disagreed perturbations. This release is validated on human
single-cell perturbation prediction, with cross-species behavior demonstrated at the routing level and no
language model in the prediction core.

**Keywords:** virtual cell; perturbation prediction; multi-agent systems; model applicability; abstention; provenance; reproducibility

## 摘要

预测细胞对基因或化学扰动响应的计算模型是虚拟细胞研究的核心[^1][^2],却有一个结构性缺陷:训练好的预测器
对任何输入(分布外物种、不支持的扰动类型、词表外基因)都会输出一个数值,既不检查适用性,也不记录用了
哪个模型,更没有"拒绝回答"的选项。我们提出 PRAXIS-VirtualCell,一个把可信预测重述为控制流问题的多智能体
运行时。这里的"运行时"是一套由确定性智能体构成的消息总线系统,"脑"是逐物种的 YAML 文件,编码模型适用性
与负迁移规则。系统把任务解析为结构化请求,经物种脑路由到异构 predictor-agent;这些智能体只通过一条可审计
的消息总线通讯;一个硬性的"先检索再预测"门、一套弃权策略、一个轨迹批判者和一个溯源装配器,把拒绝、弃权、
可审计性变为强制执行的行为。我们分两路评测。其一,在离线确定性路径上,从完整系统(D 臂)移除该运行时
(A 臂:无总线、无脑、无可靠性智能体),两臂共用同一组 mock predictor,使五个能力指标从"无"变为"有":分布外
拒绝(0→1.0)、错误模型使用(率 1.0→0)、溯源完整性(0→1.0)、弃权正确性(0→1.0)、轨迹完整性(0→1.0);
由于 A 臂在结构上缺少相应组件,这是能力"有/无"的对比,而非程度上的改进。其二,在 Norman 2019 基准[^3]上,
预测层复现了 donor Coordinator 的 delta-expression Pearson 0.7039(n = 18,874);智能体包装逐元素复现底层
预测器输出(atol 1e-6),通讯层从不执行前向计算,因此不改变任何预测数值。一个冻结的 scGPT backbone 加轻量
head 仅达 0.4407,低于所有任务专用基线、也低于同协议的 mean-perturbation 基线(0.4615),印证了"单靠规模并非
解药"[^12]。端到端可靠性路径运行在 mock predictor 上,其中若干声明式机制(核心失败、细胞类型降级)由激活
单元测试覆盖、真实激活待接入真预测器;但在真实 donor predictor 上,基于模型分歧的弃权策略已给出正向的
risk–coverage 曲线:当系统弃权分歧最大的扰动时,保留集的 delta-expression Pearson 从 0.67 升到 0.75。
本版在人类单细胞扰动预测上验证,跨物种行为在路由层面给出,预测核心不含任何语言模型。

**关键词:** 虚拟细胞;扰动预测;多智能体系统;模型适用性;弃权;溯源;可复现

---

## 1. Introduction

The virtual-cell program aims to build computational models that predict cellular state and its response to
perturbation[^1][^2]. Single-cell technologies such as Perturb-seq[^4][^5] now generate genome-scale,
rich-phenotype perturbation atlases[^3], and a fast-growing family of predictors — from generative models such
as scGen[^6] and the compositional perturbation autoencoder[^7], to the graph-based GEARS[^8], to large
single-cell foundation models such as scGPT[^9], Geneformer[^10], and the recent STATE model[^11] — map a
perturbation to an expression change. These methods supply the predictive substrate for a virtual cell.

They also share a structural weakness that is rarely treated as a first-class concern: a trained predictor
returns a number for *any* input. Asked about a species it was never trained on, a perturbation type it does
not support, or a gene outside its vocabulary, it still emits a confident vector — with no applicability
check, no record of which model produced it, and no option to abstain. In a discovery setting the wrong
answer is acted upon, which is worse than an explicit "I cannot answer this." The machine-learning literature
has long studied this as the reject option and selective prediction — trading coverage for a guaranteed lower
risk[^13][^14][^15][^16] — and cheminformatics formalizes the related idea of an applicability domain that
bounds where a model's predictions are trustworthy[^17]. Single-cell perturbation predictors, however,
typically ship without any of this machinery, and recent evaluations show that simply scaling a foundation
model does not close the gap[^12].

We argue that trustworthiness here is not primarily a better-loss problem but a *control-flow* problem: the
system around the predictor must decide when to route, when to reject, when to abstain, and must record what
it did. We present PRAXIS-VirtualCell, a multi-agent runtime that makes these decisions explicit and
auditable. To avoid over-reading the metaphor, we state the grounding once: the "operating-system/runtime"
layer is a message-bus orchestration of deterministic agents, and the species "brain" is a set of per-species
YAML files holding model-applicability and negative-transfer rules. Heterogeneous predictor-agents communicate
only over the bus; a hard retrieve-before-predict gate forces applicability retrieval before any prediction;
an abstention policy, a trace critic, and a provenance assembler turn rejection, abstention, and auditability
into enforced behaviors. Optional language-model agents may assist input interpretation, routing review,
critique, and reporting, but never enter the prediction core — the predictive path is fully offline and
reproducible.

Unlike multi-agent LLM frameworks aimed at task automation and autonomous experimentation[^18][^19][^20], our
agents are a governance layer for trustworthy prediction, not an autonomous scientist. Our contribution is
this runtime and a separation-of-concerns evaluation: we measure the reliability contribution of the runtime
independently of predictive accuracy, and we show that the communicative wrapper is performance-neutral on the
numbers a predictor produces. We organize the results around four questions — can the system understand a
virtual-cell input, is it genuinely multi-agent, does it preserve predictive performance, and does it improve
reliability — and we are deliberately explicit about what is demonstrated end-to-end versus declarative versus
evaluated separately.

## 2. Related work

**Perturbation prediction.** scGen[^6] and CPA[^7] cast perturbation response as latent-space arithmetic;
GEARS[^8] uses a gene-gene graph to generalize to unseen multigene perturbations; single-cell foundation
models — scGPT[^9], Geneformer[^10] — pretrain on large corpora, and STATE[^11] is a recent perturbation
foundation model across contexts. Benchmarks such as Norman 2019[^3], built on Perturb-seq[^4][^5], standardize
evaluation. None of these methods carries a built-in applicability check or reject option, and zero-shot
evaluations indicate that scale does not by itself confer reliable out-of-distribution behavior[^12]. PRAXIS
treats these models as interchangeable predictor-agents behind a governance layer rather than competing with
them on loss.

**Selective prediction and applicability.** The reject option dates to Chow's error–reject tradeoff[^13]; the
modern theory of selective classification formalizes risk–coverage[^14][^15], recently surveyed for machine
learning broadly[^16]. QSAR modeling uses the applicability-domain concept to bound trustworthy
predictions[^17]. Our abstention policy and species-aware applicability rules are concrete, auditable
instances of these ideas wired into a perturbation-prediction pipeline.

**Multi-agent and tool-using LLM systems.** Frameworks for multi-agent LLM conversation[^18] and autonomous
LLM-driven science[^19][^20] target task automation. We borrow the message-passing and tool-use vocabulary but
invert the goal: agents enforce governance over a deterministic predictive core, and reproducibility[^22] is a
design constraint rather than an afterthought, situating the work within trustworthy AI for science[^21].

## 3. Results

### 3.1 The system parses and normalizes virtual-cell inputs, and refuses unsupported ones

A task enters as a typed `VirtualCellRequest` (species, modality, perturbation kind and targets, optional cell
type, output task). A deterministic parser builds and validates this object; when an API key is present, an
optional LLM input-interpreter assists free-text interpretation but its output is re-validated against the
same schema, and an object-normalizer canonicalizes perturbation targets and aliases. Inputs that fall outside
the supported envelope are not coerced into a prediction: an unsupported species, an empty target list, or a
perturbation kind a predictor does not declare leads to an explicit rejection or abstention rather than a
fabricated vector (Fig. 1). This behavior is what later sections measure quantitatively.

### 3.2 The system is genuinely multi-agent, with the message bus as the sole channel

The runtime orchestrates a fixed pipeline of deterministic agents —
InputInterpreter → ObjectNormalizer → SpeciesBrain → ModelApplicability → predictor-agents → Ensemble →
Reliability → Critic → Provenance → Report — that exchange `AgentMessage`s over a single `MessageBus` (Fig. 1).
Three properties make the multi-agent claim more than cosmetic. First, the bus is the *only* communication
channel; there is no Coordinator-to-predictor shortcut that bypasses governance. Second, a hard
retrieve-before-predict gate requires that model-applicability be retrieved before any predictor runs, and the
trace critic can detect a violation of this ordering. Third, each predictor-agent can independently reject a
request (e.g., a target outside its gene vocabulary), and these rejections propagate as messages rather than
being silently dropped. The full message sequence is recorded as a replayable trace, so any prediction can be
reconstructed from the bus history.

### 3.3 The communicative wrapper preserves predictive performance

We reproduced the donor predictors on the Norman 2019 benchmark[^3] through the runtime. The six base
predictors reach per-cell delta-expression Pearson of 0.6716 (cpa), 0.6709 (decoder), 0.6675 (gnn), 0.6639
(linear), 0.6365 (latent), and 0.6183 (pretrained, a mock-backbone identity projection), all at n = 18,874
(Fig. 2). Routed through the donor Coordinator, ensembles reproduce ~0.70: 0.6847 (latent+gnn), 0.7020
(cpa+decoder+gnn), and 0.7039 (all five). The all-five ensemble (0.7039) exceeds the strongest single base
(cpa, 0.6716) by 0.032, consistent with the donor Coordinator's internal ensembling (single seed).

The key methodological point is separation of concerns. Each predictor-agent wraps an underlying donor
predictor and reproduces its output *element-wise* to atol 1e-6 (the deterministic linear predictor matches
bitwise, diff 1.2e-8). Because the communicative layer never executes a forward pass — the message bus carries
metadata and tensors but performs no tensor arithmetic — wrapping a predictor changes none of the numbers it
produces. We therefore claim only that the communicative layer is performance-neutral, not that
message-passing achieves a higher Pearson.

As a same-protocol naive baseline — same Norman test split, same per-cell delta-Pearson, same EvalAgent — a
perturbation-agnostic mean-perturbation predictor that returns the average training delta for every input
reaches delta-Pearson 0.4615 (n = 18,874). It sits well below every trained base (0.6183–0.6716), confirming
that the trained predictors capture perturbation-specific structure rather than a shared mean response, and it
provides a floor for the accuracy comparison.

We also ran two foundation models. A frozen scGPT backbone (53.8 M parameters) with a light trainable head
(~2.47 M) reaches delta-Pearson 0.4407 (cosine 0.9808, n = 7,290 under reduced sampling) — below every
task-specific base and, notably, below even the trivial mean-perturbation baseline; the training loss barely
moves, indicating the frozen encoder plus light head saturates on this task. GEARS, run in its native pipeline,
reports pearson_de 0.8392, but this is *not comparable* to the delta-Pearson numbers above — it is an
absolute-expression Pearson over differentially expressed genes on a different split — so we keep it off this
axis. Both observations are consistent with the view that a large pretrained model is not automatically the
strongest perturbation predictor[^12].

### 3.4 The runtime, not the predictor, is what improves reliability

To isolate the runtime's contribution we compared two arms running the same mock predictor set: arm A, an
ML-only stub with no bus, brain, or reliability agents, and arm D, the full PRAXIS pipeline. On an offline,
deterministic path, five capability axes separate the arms (Fig. 3):

| Axis | Arm A (ML-only) | Arm D (Full PRAXIS) |
|---|---|---|
| Out-of-distribution rejection rate | 0.0 | 1.0 |
| Wrong-model use rate | 1.0 | 0.0 |
| Provenance completeness | 0.0 | 1.0 |
| Abstention correctness | 0.0 | 1.0 |
| Trace completeness | 0.0 | 1.0 |

Arm A structurally lacks the bus, brain, and reliability agents, so it cannot trace, abstain, or record
provenance; this is a capability presence/absence contrast, not a graded score. The same mock predictors sit
in both arms, which is what isolates the runtime as the source of the difference rather than the predictor.

The species brain makes this concrete across organisms (Fig. 4). For a human request, three predictors are
applicable with no caution. For mouse, predictors are applicable but flagged with an ortholog caution: the
runtime performs a real ortholog projection of targets and tags any target it cannot map with an
`unmapped_ortholog` flag. For bacteria and yeast, all predictors are rejected by the negative-transfer rule
`mammalian_scrna_predictor_not_applicable`, and the system abstains. For an unknown ("martian") species, the
system abstains without writing references to rules or files that do not exist — it does not manufacture
evidence.

Beyond routing, the reliability and critic agents add defenses (Fig. 5): the ensemble computes pairwise-cosine
model disagreement; the reliability agent can abstain or downgrade confidence; a trace critic runs seven
checks (including retrieve-before-predict ordering, rejected-model-in-ensemble, missing provenance, missing
uncertainty, unsupported species, and abstain/prediction consistency); and the report separates true
abstention reasons from confidence-downgrade reasons so a downstream reader is not misled into treating a
downgrade as an abstention.

We quantify the value of abstention with a risk–coverage analysis on the Norman test split, using the real
donor predictors (manifest `data/manifests/norman_2019.yaml`, which records the data fingerprint and declares a
held-out out-of-distribution split — 82 of the 151 test perturbations are unseen in training). Using the
ensemble-disagreement signal to abstain on the most-disagreed perturbations, retained accuracy rises
monotonically as coverage falls: from delta-Pearson 0.672 at full coverage to 0.683 at 96% coverage, 0.707 at
88%, 0.732 at 82%, and 0.754 at 74% — up to +0.08 on the perturbations the system chooses to answer. Because
per-perturbation disagreement values near the abstention threshold are sensitive to GPU floating-point
non-determinism, we report the gain against a fixed full-coverage reference and emphasize the monotone trend
rather than any single point. This is the abstention policy delivering a measurable reliability benefit on real
predictors, not merely a declared capability.

The suite at tag v0.1.0 runs 75 passed and 23 skipped on a machine without a GPU (ML tests are tagged
`remote` and skipped when torch is absent; all ML tests pass remotely).

## 4. Discussion

PRAXIS-VirtualCell reframes a reliability gap in virtual-cell prediction as a control-flow problem and shows,
with a clean separation of concerns, that a governance runtime — not a better predictor — is what supplies
rejection, abstention, provenance, and auditability. The accuracy result (0.7039) and the reliability result
(the A↔D capability contrast) are deliberately measured on different paths so that neither inflates the other:
the runtime never touches the tensors, and the reliability arms share the same mock predictors.

Three positions follow. First, applicability and abstention belong in the pipeline, not only in the loss; the
reject option and applicability-domain ideas[^13][^14][^15][^16][^17] are implementable as enforced control
flow over heterogeneous predictors. A capability audit of five representative perturbation systems — GEARS[^8],
CPA[^7], scGPT[^9], scGen[^6], and STATE[^11] — against their public papers and code found that none
implements out-of-distribution rejection, an applicability check, an abstention mechanism, prediction
provenance, or auditable multi-model messaging; uncertainty outputs, where present, are scalars a user must
threshold, not a decision to decline. These are governance functions PRAXIS supplies around predictors rather
than properties of any one predictor. Second, a foundation model is not automatically the answer: our frozen
scGPT result and independent zero-shot evaluations[^12] both argue for keeping task-specific predictors under
a routing layer rather than betting on scale alone — even as strong perturbation foundation models such as
STATE[^11] continue to improve. Third, the adversarial, honesty-first methodology we used during development
(separating declarative mechanisms from runtime-active ones) is itself a contribution to trustworthy AI for
science[^21], and reproducibility[^22] is built in: the predictive core is fully offline and deterministic.

## 5. Methods

**Agent contracts and the bus.** The runtime defines a `VirtualCellRequest`, an `AgentMessage`, a `MessageBus`,
and an `AgentRuntime`. Agents are pure functions over messages; the bus is the only inter-agent channel.
`run_request` executes the pipeline
InputInterpreter → ObjectNormalizer → SpeciesBrain → ModelApplicability → fan-out predict → Ensemble →
Reliability → Critic → Provenance → Report. The retrieve-before-predict gate requires model-applicability in
the message history before any predictor message; the critic flags violations. The full message history is a
replayable trace and is exported alongside the report.

**Species brain schema.** Per-species YAML files (human, mouse, bacteria, yeast, plus a generic file) declare
runtime-consumed fields — `supported_species`, `supported_modalities`, `supported_tasks`, `reject_if`,
`object_vocabulary.genes`, `caution.<species>` (a list), `cross_species.rule`, and
`generic.negative_transfer` — that the SpeciesBrain and ModelApplicability agents read to drive routing and
trace. The brain files also hold declarative knowledge (supported perturbations/cell types, native host,
per-species ortholog/interaction/abstain rule files) that is recorded in the trace's `rules_referenced` for
audit but does not, in this release, drive the routing decision; we mark this distinction explicitly to avoid
over-claiming that these files participate in the decision.

**Norman benchmark reproduction.** Donor predictor checkpoints are used read-only. The reproduction recipe is
`load_vcbench_split("norman_2019", "test", max_cells_per_pert=200, rng_seed=1)`, evaluated with the donor
EvalAgent; the deterministic linear predictor reproduces its recorded delta-Pearson bitwise (diff 1.2e-8) and
the trained predictors within atol 1e-6 element-wise, confirming the wrapper is faithful. We report per-cell
delta-expression Pearson at n = 18,874 for bases and Coordinator ensembles. The scGPT head is trained on the
same donor Norman data with the encoder frozen, under reduced sampling (`max_cells=50`, n = 7,290) to fit
memory; GEARS is run in its native pipeline and its metric/split are stated as non-comparable.

**Ablation design.** We compare arm A (an ML-only Coordinator stub that hardcodes no-bus/no-brain/no-reliability
behavior, faithfully modeling the absence of these components) and arm D (full PRAXIS) on a Mac-offline,
deterministic path, both over the same mock predictor set. We report five axes: OOD-rejection rate,
wrong-model-use rate, provenance completeness, abstention correctness, and trace completeness. Two further
arms were considered and dropped: arm B (brain-guided without the bus) had no implementation and would yield
inferred-only numbers, and arm C (communicative without reliability) was effectively equal to D on the primary
axes; we therefore report the A↔D poles only. A numeric risk–coverage analysis of the abstention policy is
reported separately in §3.4, using the `data/manifests/norman_2019.yaml` manifest that records the data
fingerprint (sha256) and declares a held-out OOD-perturbation split; that analysis runs on the real donor
predictors, not the mock set.

**Reliability and critic.** The ensemble computes pairwise-cosine disagreement (with a configurable
`disagreement_threshold`, default 0.5, and an audit field counting zero-vector pairs). The reliability agent
merges abstention and downgrade logic: abstention reasons (e.g., unsupported species, empty targets, all
predictors rejected) and downgrade reasons (e.g., model disagreement, cell-type not supported) occupy separate
namespaces and the report exposes them separately. The deterministic critic audits the reliability payload and
provenance before the report; semantic review of an LLM-written narrative, when present, is the separate
LLM-critic's job.

**Cross-species routing.** ModelApplicability reads `caution.<species>` and `generic.negative_transfer` to
emit cautions and rejection reasons; the SpeciesBrain loads per-species ortholog rules and performs a real
upper-case ortholog projection of targets, flagging unmapped targets. Routing decisions, cautions, and the
specific rules hit are written to provenance and surfaced in the report's `caution_flags`,
`rejection_reasons`, and `rules_hit`.

**Software and tests.** The predictive core is offline and deterministic; optional LLM agents (input
interpretation, routing review, critic, report) use a single HTTP client and degrade gracefully without an API
key. The test suite runs 75 passed and 23 skipped without a GPU (ML tests tagged `remote`); all ML tests pass
on the remote GPU host.

## 6. Limitations

- **The communicative layer does no tensor computation.** Arm D's Pearson is produced by the shared predictor
  through the same EvalAgent; the ablation's performance statement is only that the runtime *does not harm*
  accuracy, never that it is *more accurate*. We do not claim message-passing achieves 0.7039.
- **The ablation is two poles.** Arm A is a stub, so four of the five axes are zero by construction; we present
  this as a capability presence/absence contrast, not a graded improvement, and a real-predictor and/or
  intermediate-arm ablation is future work.
- **Declarative mechanisms are not all activated end-to-end on mock predictors.** Model disagreement,
  core-predictor failure, and cell-type downgrade do not fire in the current mock pipeline; activation unit
  tests prove the mechanisms are real and can fire, and real activation awaits real predictors with
  multi-dimensional, failable outputs.
- **Ortholog projection is exercised in routing/caution but not yet in a real cross-species prediction.** The
  projection runs and flags unmapped targets; using it to drive an actual mouse/bacteria/yeast prediction
  awaits a real cross-species predictor.
- **Abstain-gain is measured over the full test split, not yet OOD-restricted.** A DOI+sha256 manifest and a
  held-out OOD-perturbation split are now provided (`data/manifests/norman_2019.yaml`), and §3.4 reports a
  positive risk–coverage curve from disagreement-based abstention on the real predictors. That abstention
  operates over the whole test split; an OOD-restricted abstain-gain — and a test of whether the abstained
  perturbations are enriched for the unseen split — is a clean refinement we have not yet run.
- **External baselines are partial.** The six predictors are donor-stack variants. We add a same-protocol
  mean-perturbation naive baseline (0.4615) and a frozen-scGPT foundation baseline (0.4407), but a strong
  external task-specific baseline on the identical split and metric (e.g., GEARS or scGen adapted to the donor
  split) is still future work.
- **External-model caveats.** The scGPT result uses a frozen backbone with a light head under reduced sampling;
  GEARS's metric and split are not comparable to the delta-Pearson axis.
- **Scope.** This release validates human single-cell perturbation prediction; mouse, bacteria, and yeast are
  brain-routing prototypes, and we do not claim full cross-species prediction. Language-model agents are
  optional and never enter the prediction core.

## Data and code availability

The Norman 2019 dataset is publicly available[^3]. Code is released at the project repository, tagged v0.1.0;
the predictive core runs offline and deterministically. Donor predictor checkpoints are used read-only for
reproduction.

## Author contributions, ethics, AI-usage, and competing interests

Author contributions (CRediT) — TBD. This work uses no human-subject or animal data beyond publicly available
single-cell datasets; no ethics approval was required. AI-usage disclosure: language-model coding assistants
and an LLM writing assistant were used during development and manuscript preparation; all quantitative claims
were verified against logged experiments and all citations against CrossRef/source records. The authors
declare no competing interests. Funding — TBD.

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
