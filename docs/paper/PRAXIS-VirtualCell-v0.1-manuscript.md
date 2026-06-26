# A brain-guided communicative agent operating system for trustworthy virtual-cell perturbation prediction

**Authors:** [Author list — TBD] · **Corresponding author:** [TBD]

> **Manuscript status:** v0.1 draft, revised after a 5-reviewer adversarial pass (ARS `academic-paper`
> full mode: write → review → revise; disposition in `02_review_and_revision.md`). Body in English;
> bilingual abstract. Target format: Nature Methods (numbered references). **Citations are placeholders this
> round** (`[CIT:key]`); the reference list is populated in a dedicated citation pass. Every quantitative
> claim is traced to a finding in `docs/findings/` and to source `file:line` anchors (see `00_chapter_plan.md`).

---

## Abstract

Computational models that predict how a cell responds to genetic or chemical perturbation are central to
the virtual-cell program, yet they share a structural weakness. A trained predictor returns a number for
any input, whether an out-of-distribution species, an unsupported perturbation type, or a gene outside its
vocabulary, with no applicability check, no record of which model was used, and no option to decline. We
present PRAXIS-VirtualCell, a multi-agent runtime that reframes trustworthy prediction as a control-flow
problem. A task is parsed into a typed request and routed through a species "brain" — per-species YAML
rules for model applicability and negative transfer — to heterogeneous predictor-agents that communicate
only over an auditable message bus. A hard retrieve-before-predict gate, an abstention policy, a trace
critic, and a provenance assembler make rejection, abstention, and auditability first-class, enforced
behaviors. We evaluate two questions separately. On the offline deterministic path, ablating the runtime
(arm A, a stub with no bus, brain, or reliability agents) from the full system (arm D), both running the
same mock predictor set, moves five capability axes from absent to present: out-of-distribution rejection,
wrong-model use (its error rate falling from 1 to 0), provenance completeness, abstention correctness, and
trace completeness. Separately, on the Norman 2019 benchmark, the predictive layer reproduces the donor
Coordinator's delta-expression Pearson of 0.7039. The agent wrapper reproduces the underlying model's
output element-wise (atol 1e-6), so the communicative layer, which never runs a forward pass, changes none
of the numbers a predictor produces. A frozen scGPT backbone reaches only 0.4407, below every
task-specific base, indicating that scale alone is not the fix. The end-to-end reliability path runs on
mock predictors; several declarative mechanisms (model disagreement, core-failure, and cell-type
downgrades) are covered by activation unit tests and await real predictors. This release is validated on
human single-cell perturbation prediction, with cross-species behavior at the routing level and no
language model in the prediction core.

**Keywords:** virtual cell; perturbation prediction; multi-agent systems; model applicability; abstention;
provenance; reproducibility

## 摘要

预测细胞对基因或化学扰动响应的计算模型是虚拟细胞研究的核心,但它们有一个结构性缺陷:训练好的预测器对任何
输入(分布外物种、不支持的扰动类型、词表外基因)都会给出一个数值,既不检查适用性,也不记录用了哪个模型,
更没有"拒绝回答"的选项。我们提出 PRAXIS-VirtualCell,一个把可信预测重述为控制流问题的多智能体运行时。系统
把任务解析为结构化请求,经物种"脑"(逐物种的 YAML 适用性与负迁移规则)路由到异构 predictor-agent;这些智能体
只通过一条可审计的消息总线通讯。一个硬性的"先检索再预测"门、一套弃权策略、一个轨迹批判者与一个溯源装配器,
把拒绝、弃权、可审计性变为强制执行的一等行为。我们分两路评测。离线确定性路径上,从完整系统(D 臂)移除该
运行时(A 臂:无总线、无脑、无可靠性智能体),两臂共用同一组 mock predictor,使五个能力指标从"无"变为
"有":分布外拒绝、错误模型使用(其错误率由 1 降到 0)、溯源完整性、弃权正确性、轨迹完整性。另一路在
Norman 2019 基准上,预测层复现 donor Coordinator 的 delta 表达 Pearson 0.7039;智能体包装与底层模型输出
逐元素一致(atol 1e-6),通讯层从不执行前向,因而不改变预测器产出的任何数值。作为对照,冻结的 scGPT 骨架
(轻量 head)只达 0.4407,低于所有任务专用 base,说明基础模型并非银弹。可靠性端到端路径用 mock predictor
跑通;若干声明式机制(模型分歧、核心失败与细胞类型降级)由激活单元测试覆盖、待真实预测器激活。本版仅在
人类单细胞扰动预测上验证,跨物种为路由级,预测核心不含任何大语言模型。

**关键词:** 虚拟细胞;扰动预测;多智能体系统;模型适用性;弃权;可追溯;可复现

---

## Introduction

A virtual cell is an in-silico model of a cell that can be queried for its response to interventions. A
tractable and well-studied instance is single-cell perturbation prediction: given a genetic or chemical
perturbation, predict the change in gene expression relative to an unperturbed control. The last few years
have produced a dense field of predictors for this task, spanning task-specific neural networks and large
pretrained "foundation" models `[CIT:GEARS]` `[CIT:CPA]` `[CIT:scGPT]` `[CIT:Geneformer]` `[CIT:STATE]`,
typically benchmarked on combinatorial CRISPR screens such as Norman 2019 `[CIT:Norman2019]`.

These predictors share a blind spot that becomes critical the moment they are used for discovery rather
than for benchmarking. A trained model emits a delta-expression vector for whatever input it receives. It
will answer a query about a mouse gene, a bacterial operon, or a small-molecule drug even when it was
trained only on human single-gene knockdowns; it will answer a query about a gene outside its graph
vocabulary; and it does so with no applicability check, no record of which model produced the answer or
under which rule, and no option to decline. In a discovery loop a confident wrong answer is more damaging
than an explicit "I cannot answer this", because the wrong answer is acted upon `[CIT:abstention]`
`[CIT:selective-prediction]`.

A natural response is to reach for a larger model. Our own measurements argue against treating scale as the
fix. A frozen scGPT backbone with a light task head reaches a delta-expression Pearson of 0.4407 on Norman,
below every task-specific base predictor we evaluated (the strongest base reaches 0.6716); the head
saturates during training, indicating that a frozen foundation encoder is not, by itself, a better
perturbation predictor here `[CIT:scGPT]` `[CIT:foundation-models]`. Foundation models are useful
components, not a substitute for the missing machinery of applicability and abstention.

We therefore reframe the problem. Rather than asking for a better predictor, we ask what runtime a
predictor must sit inside to be trustworthy. PRAXIS-VirtualCell is that runtime: heterogeneous predictors
are wrapped as agents that communicate over a single auditable message bus, guided by a species "brain"
and governed by reliability and critic agents that abstain and audit. We use two deliberately load-bearing
metaphors and ground each in its implementation. The "operating system" is concretely a message-bus
runtime of a dozen deterministic agents with an enforced control-flow gate; the species "brain" is
concretely a set of per-species YAML files that encode model applicability, negative transfer, ortholog
mapping, and abstention rules. Optional language-model agents assist input interpretation, routing review,
critique, and reporting, but no language model sits in the prediction core, and the entire prediction loop
runs offline and reproducibly.

We organize the evaluation around four questions, each answered in one Results section. Can the system
understand a virtual-cell request, and reject what it cannot serve (Q1)? Is the coordination a genuine,
auditable multi-agent system rather than an orchestrator with logging (Q2)? Does wrapping predictors as
communicating agents preserve predictive performance (Q3)? And does the runtime actually add reliability
behaviors (Q4)? Our contributions are: (i) a typed request contract and a species-brain schema that make
applicability and rejection explicit; (ii) a message-bus runtime with an enforced retrieve-before-predict
gate and a trace critic, so auditability is a control-flow property rather than a convention; (iii) a
demonstration that the communicative wrapper changes no numbers, reproducing the donor Coordinator's 0.7039
Norman ensemble element-wise (atol 1e-6), so the runtime is performance-neutral; and (iv) a capability
ablation on the offline path showing that five reliability behaviors are present only when the runtime is
present, with a candid account of which behaviors are demonstrated end-to-end versus declarative and
unit-test-activated.

### Related work

PRAXIS-VirtualCell sits at the intersection of three lines of work. The first is single-cell
perturbation prediction, where task-specific models such as GEARS `[CIT:GEARS]` and the compositional
perturbation autoencoder `[CIT:CPA]` and large pretrained models such as scGPT `[CIT:scGPT]`,
Geneformer `[CIT:Geneformer]`, and STATE `[CIT:STATE]` predict expression change from perturbation, and
where benchmarks such as Norman 2019 `[CIT:Norman2019]` standardize evaluation. These methods supply the
predictors we wrap; none of them carries an applicability check, a rejection path, or a provenance
record, which is precisely the gap our runtime targets. The second line is selective prediction and the
reject option, including risk-coverage analysis and abstention with a guarantee `[CIT:selective-prediction]`
`[CIT:abstention]`, together with the applicability-domain notion from cheminformatics and QSAR
`[CIT:applicability-domain]`. Our abstention policy and species-aware applicability rules are concrete,
domain-specific instances of these ideas, and we adopt their vocabulary deliberately; what we add is the
control-flow enforcement (a predictor cannot run before applicability is retrieved) and the auditable
trace. The third line is multi-agent and tool-using LLM systems `[CIT:multi-agent-llm]`. We borrow the
agent-and-message-bus structure but invert the usual dependency: the language model is optional and
peripheral, while the deterministic predictors and rules are the load-bearing core. To our knowledge the
combination — an enforced retrieve-before-predict gate, a trace critic, and species-brain applicability
rules wrapping heterogeneous perturbation predictors, with abstention as a first-class outcome — has not
been assembled before for virtual-cell prediction.

## Results

### A typed request contract turns rejection into a first-class outcome

Every task entering PRAXIS-VirtualCell is normalized into a `VirtualCellRequest`, a typed structure whose
required fields are the species, the perturbation type, the perturbation targets, the input and output
modalities, and the task type, with optional fields for cell type, tissue, dose, and time
(`core/request.py:17`). Structured inputs are validated by a deterministic interpreter
(`agents/input_interpreter.py:12`), gene symbols are normalized (`agents/object_normalizer.py:9`), and
free-text inputs can be parsed by an optional language-model interpreter that falls back to the
deterministic path when no API key is present (`agents_llm/llm_input_interpreter.py:24`). The request is the
sole interface between the outside world and the prediction machinery, which means every downstream decision
is made against a single explicit object rather than against loosely typed arguments.

Because the contract is explicit, so is its boundary. An unsupported species, modality, or task type, an
unsupported perturbation type (a small-molecule drug submitted to a gene-only model, for example), and a
gene outside the model's graph vocabulary each produce a rejection carrying a machine-readable reason
rather than a silent prediction; an empty target list triggers abstention with the reason
`no_perturbation_specified`. The drug case is instructive: an early implementation mishandled a mouse
aspirin request by treating the drug name as a gene symbol, which an adversarial implementation review
caught and which now rejects cleanly as `unsupported_perturbation`. Rejection is not an error path bolted
on at the edges; it is a typed outcome that the rest of the system is built to consume.

Figure 1 shows the full data flow, from request through interpretation, normalization, species-brain
retrieval, applicability decision, predictor fan-out, ensembling, reliability assessment, critique,
provenance assembly, and reporting, with the retrieve-before-predict gate and the abstention branch marked.
The remaining Results sections trace this path.

### Coordination is auditable by construction, not by convention

A system can route a task through many functions and still be a monolith with extra logging. PRAXIS-
VirtualCell is not, and the difference is enforced rather than asserted. All inter-agent communication is an
`AgentMessage` placed on a single `MessageBus`, which records a complete, replayable trace and preserves
message lineage through a parent-message identifier (`core/bus.py:10`, `core/message.py:14`). There is no
private channel by which a coordinator can call a predictor directly; the bus is the only way agents reach
one another, so the trace is a faithful and complete account of what happened.

Each predictor is an agent that decides its own applicability and reports a `PredictorResultMessage` whose
status is success, rejected, or failed (`core/message.py:25`, `predictors/base.py`). A rejected agent never
contributes to the ensemble, and the rejection, with its reason, remains in the trace. The system's
multi-agent character is thus visible in the message record: independent agents, independent decisions,
recorded outcomes.

The load-bearing mechanism is a hard retrieve-before-predict gate. Any predictor invoked before a
`brain_retrieved` message has been published raises `RetrieveBeforePredictError` and aborts
(`predictors/base.py:41-43`); the trace critic additionally verifies, as its first invariant, that the
brain-retrieved message precedes the first predictor result (`agents/critic.py`). This converts "retrieve
applicability knowledge before predicting" from a guideline that a careless caller could skip into a
control-flow property that the runtime physically enforces. A predictor cannot run on a species before the
brain has had its say.

In this offline release the three predictor-agents are mocks that return constant delta vectors, chosen so
that routing, rejection, and abstention can be exercised deterministically on a laptop. Real
machine-learning predictor-agents wrap donor checkpoints and run on a GPU server
(`predictors/ml/agent_adapter.py:18`). The next section evaluates those GPU agents for predictive
performance only; the end-to-end reliability behaviors are exercised on the deterministic mock path and,
for declarative mechanisms, by activation unit tests (Q4 and Limitations).

### Wrapping predictors as agents does not cost accuracy

To test whether the communicative layer degrades prediction, we evaluated the underlying predictors on the
Norman 2019 benchmark using per-cell delta-expression Pearson on the held-out test split (n = 18,874 cells;
sampling fixed at 200 cells per perturbation, seed 1, ESM2 perturbation features). Six donor predictors
reproduce their recorded scores: CPA-style 0.6716, decoder-only 0.6709, GNN 0.6675, linear-additive 0.6639,
latent-additive 0.6365, and a pretrained-backbone control 0.6183 (Fig. 2; finding_w4b_multi_anchor; all at
n = 18,874). The donor Coordinator, reused through a bridge that preserves its sub-agent ensembling logic,
reaches 0.7039 with all five trainable predictors, 0.7020 with the CPA, decoder, and GNN combination, and
0.6847 with the latent-plus-GNN pair (finding_w4b_coordinator). The donor Coordinator's internal
ensembling, not the communicative wrapper, improves on the strongest single base by 0.032 Pearson. This
single-seed gain is consistent with the ensemble adding signal rather than tracking its best member; we do
not attach a confidence interval to it.

The performance claim here is deliberately narrow, and it rests on equivalence rather than on a head-to-head
accuracy comparison. The agent wrapper's prediction equals the donor model's native `predict()` output
element-wise to a tolerance of 1e-6, and the linear-additive anchor reproduces its recorded benchmark score
to a difference of 1.2e-8 (finding_w4a). This is a wrapper-identity check: because the wrapper reproduces
the model's numbers exactly, any score the agent system reports is the score the underlying predictor would
have produced on its own. The communicative layer never participates in tensor computation and the message
bus does not run a forward pass, so the runtime neither helps nor harms accuracy. We do not claim the
architecture predicts more accurately.

Two external models were integrated as standalone native pipelines, not yet as registered bus
predictor-agents, and we report them as integration checks rather than as comparators on the
delta-expression axis. A frozen scGPT backbone (53.8 M parameters) with a light trainable head (~2.47 M
parameters) reaches a delta-expression Pearson of 0.4407 (cosine 0.9808) under reduced cell sampling (50
cells per perturbation, n = 7,290), so it is not on the same sampling protocol as the bases above. Even so
it sits below every task-specific base predictor, and its training loss barely moves, indicating a
saturated head (finding_w4c_scgpt). This is direct evidence that a frozen foundation backbone is not, by
itself, a better perturbation predictor here. GEARS, run in its native pipeline, reaches a DE-gene Pearson
of 0.8392, but this number is measured on a different quantity (absolute-expression Pearson over
differentially expressed genes) and a different split, so it is not comparable to the delta-expression
scores and we keep it off the same axis (finding_w4c_gears).

We note one boundary that the accuracy comparison does not yet meet: the six predictors above are all
variants of the donor stack, so this is not a comparison against independent external baselines under the
identical split and metric. We return to this in Limitations.

### The runtime adds reliability behaviors the predictors lack

The reliability evaluation is separate from the accuracy evaluation of the previous section, and it runs on
the offline deterministic path where both arms execute the same three mock predictors, so that the only
difference between the arms is the runtime itself. Arm A is an ML-only Coordinator stub with no message
bus, no species brain, no applicability checks, and no reliability or critic agents; arm D is the full
PRAXIS-VirtualCell system. Across six seed requests, five capability axes separate the arms completely
(Fig. 3; finding_w7): the out-of-distribution rejection rate is 0.0 for A and 1.0 for D; the wrong-model-use
rate is 1.0 for A and 0.0 for D; and provenance completeness, abstention correctness, and trace
completeness are each 0.0 for A and 1.0 for D. This is a capability presence/absence contrast, not a graded
improvement. Arm A cannot emit a trace, record provenance, or abstain because it lacks the components that
produce them, so four of the five axes are zero for A by construction. The experiment therefore shows that
these behaviors require the runtime; it does not show that the runtime improves them along a continuous
scale. A graded comparison would need an intermediate arm and real predictors, which we leave as future
work.

The species brain makes applicability concrete. Routing one fixed task across four species (Fig. 4;
finding_w5) produces four distinct behaviors. For a human request all three predictors are applicable with
no caution. For a mouse request the predictors are applicable but carry an ortholog caution: the system
projects each target back to the native host through an explicit mapping and flags any target it cannot map
as `unmapped_ortholog`, so the caution is computed and visible rather than nominal. For bacteria and yeast
every predictor is rejected and the system abstains, citing the negative-transfer rule
`mammalian_scrna_predictor_not_applicable`. For an unknown "martian" species the system also abstains, and
critically it does so without fabricating evidence: it does not write rule references that point to
non-existent files. The distinction between "understood but rejected" and "unknown" is preserved in the
reasons.

Reliability is decided by an explicit policy and audited by a critic. The ensemble agent computes a
pairwise-cosine disagreement estimate over the contributing predictions, with a configurable threshold of
0.5 (`brains/virtualcell/generic/default_abstain_rules.yaml`). The reliability agent merges abstention
triggers — all predictors rejected, species unsupported, a core predictor failed, or disagreement above
threshold — with downgrade triggers for high disagreement or an unsupported cell type, keeping the two
classes separate. The critic agent then checks seven trace-honesty invariants, among them that the brain
was retrieved before any prediction, that no rejected predictor entered the ensemble, that a non-abstaining
answer cites at least one rule, that successful predictors report uncertainty, and that an abstaining
decision carries no surviving prediction. The report agent separates `abstain_reasons` from
`downgrade_reasons` so that a reliability downgrade is never misread downstream as an abstention
(finding_w6). Figure 5 summarizes these mechanisms.

Several of these mechanisms warrant an honest boundary, stated here and revisited in Limitations. The
ablation is a two-pole comparison: a brain-guided-without-bus arm (B) was not implemented, and a
communicative-without-reliability arm (C) shares the agent stack with D closely enough that it was not
published separately (finding_w7). Ortholog projection is real and runs in the cross-species routing path
described above: it maps mouse targets to the native host and flags unmapped ones, and is covered by
routing tests (finding_w5, Fig. 4); what awaits a real predictor is using those projected orthologs to
drive an actual cross-species prediction. Three other mechanisms do not fire on the end-to-end mock path.
Model disagreement evaluates below the 0.5 abstain threshold on the mock predictions, and its value is
partly a zero-vector artifact that the system records in an audit field rather than mistaking for a
directional conflict; the mock predictors never raise, so core-predictor failure never triggers; and the
seed requests carry no cell type, so the cell-type downgrade never triggers. These three are flagged as
declarative in the configuration and exercised by hand-written activation unit tests, with end-to-end
activation awaiting real, disagreeing, failable predictors (finding_w6). A numeric abstain-gain is
deliberately not reported, because it requires a declared held-out out-of-distribution perturbation split
under the project's manifest rule, which this release does not yet provide (finding_w7).

## Discussion

The central argument is that, for virtual-cell prediction, rejection, provenance, and abstention belong to
the runtime around a predictor rather than to the predictor itself. This is partly true by construction: a
predictor with no applicability rules cannot reject, and a stub with no bus cannot trace. What is not
automatic, and is the contribution, is making those behaviors enforced and auditable rather than optional —
the message bus as the only channel, the retrieve-before-predict gate as control flow, and the trace critic
as a check that the runtime did what it claims. The ablation shows these behaviors are absent without the
runtime and present with it; the predictors are unchanged across arms. This is a different lever from the
one the field usually pulls. Most effort goes into the predictor; comparatively little goes into the system
that decides when a predictor should be trusted, records why, and declines when it should not answer.

Our scGPT measurement supports treating foundation models as components rather than solutions. A frozen
foundation encoder, attached to a light head, underperformed task-specific networks on this benchmark. In
the operating-system view this is unremarkable: a foundation model is simply one predictor among several,
applicable or not according to the brain, and worth ensembling only when it adds signal. The architecture
does not need any single predictor to be best; it needs to know which predictors are applicable and to
combine them auditably.

The way these claims were built is itself part of the contribution. Each reliability feature passed a dual
adversarial validation, a design review that stress-tested the proposed mechanism and an implementation
review that ran the code, and together these caught paper-only mechanisms, dead code, and fabricated
evidence before they entered the release (finding_w5, finding_w6, finding_w7). For a systems paper that
makes reliability claims, this practice is transferable: a mechanism that exists in a diagram but never
executes is a liability, and naming that gap explicitly is more useful than hiding it.

What real predictor-agents unlock is the obvious next step. Substituting genuinely disagreeing and failable
predictors for the offline mocks would activate the disagreement, core-failure, and cell-type mechanisms on
the end-to-end path; declaring a held-out out-of-distribution perturbation split would let us report a
numeric abstain-gain; and training real cross-species predictors would turn the routing-level cross-species
behavior into cross-species prediction. The destination is a multi-species, multi-task virtual-cell
operating system in which every answer is either trustworthy and traceable or an explicit, reasoned refusal.

## Methods

### Agent contracts and the message bus

The runtime is built from three core types. A `MessageBus` (`core/bus.py`) routes `AgentMessage` objects
(`core/message.py`) between agents and records every message in an ordered, replayable trace; it exposes
queries over message types and a lineage pointer (`parent_message_id`) so any decision can be traced to its
antecedents. An `AgentRuntime` (`core/runtime.py`) registers agents, constructs messages, dispatches them,
and runs the end-to-end workflow. The pipeline comprises ten agent roles realized as twelve deterministic
agents — input interpreter, object normalizer, species brain, model applicability, three predictor-agents,
ensemble coordinator, reliability, critic, provenance, and report — plus four optional language-model agents
(input interpreter, router, critic, report) that activate only when an API key is configured and never
participate in the prediction or evaluation of tensors. Message types name each hop (`request_parsed`,
`object_normalized`, `brain_retrieved`, `applicability_decided`, `predictor_result`, `ensemble_done`,
`reliability_decided`, `critic_done`, `provenance_done`, `report_done`). The retrieve-before-predict gate
is implemented in the predictor base class (`predictors/base.py:41-43`): a predictor that handles a message
before a `brain_retrieved` message exists on the bus raises `RetrieveBeforePredictError`.

### Request schema and parsing

`VirtualCellRequest` (`core/request.py:17`) carries required fields (request id, species, perturbation
type, perturbation targets, input modality, output modality, task type) and optional fields (cell type,
tissue, dose, time, baseline context, metadata, constraints). The deterministic interpreter validates and
constructs the request; the object normalizer upper-cases and de-spaces gene symbols and reserves a slot
for alias resolution. The optional language-model interpreter converts free text to the same request via a
JSON-mode call and, absent a key, the system uses the deterministic path so that no behavior depends on an
external service.

### Species-brain schema

The brain is a directory of YAML rule files under `brains/virtualcell/`, with a `generic/` group
(task schema, default abstain rules including the disagreement threshold, core-predictor declaration,
general negative-transfer rules) and one group per species (`human/`, `mouse/`, `bacteria/`, `yeast/`). Each
species group provides a `model_applicability.yaml` (supported species, modalities, tasks, perturbations,
cell types, native host, and caution entries per predictor), an `object_vocabulary.yaml` (the gene
vocabulary used for out-of-vocabulary rejection), and, where relevant, `ortholog_rules.yaml`,
`negative_transfer.yaml`, `abstain_rules.yaml`, or `genetic_interaction_rules.yaml`. The species-brain agent
(`agents/species_brain.py`) loads the applicable files into a brain context and records the referenced rule
files for audit, writing references only for files that exist. The model-applicability agent
(`agents/model_applicability.py`) reads the applicability map, vocabulary, negative-transfer rules, and
ortholog mapping to partition predictors into applicable and rejected, to compute ortholog cautions by
projecting targets through the mapping, and to attach machine-readable rejection reasons. We distinguish
fields that participate in runtime routing from declarative knowledge that is recorded for audit and human
reading but does not yet drive routing decisions (finding_w5); this separation is documented so that the
brain's declarative content is not over-read as active logic.

### Norman benchmark protocol

Donor predictor checkpoints are reconstructed by a bridge that loads the checkpoint bundle and rebuilds the
predictor (`predictors/ml/donor_bridge`), with `weights_only=False` to match the donor's serialization. The
benchmark split is obtained with `load_vcbench_split("norman_2019", "test", max_cells_per_pert=200,
rng_seed=1)` using ESM2 perturbation features; the linear-additive predictor is deterministic and
non-trainable, so it reproduces its recorded score bit-for-bit. Scoring uses the donor evaluation agent,
which reports per-cell delta-expression Pearson and cosine over the test cells; batch size does not affect
the metric. The Coordinator is reconstructed through a coordinator bridge that reuses the donor sub-agent
and Coordinator classes rather than reimplementing the ensembling. All machine-learning measurements run on
a remote server with eight NVIDIA A100-40GB GPUs in a `virtualcell` conda environment (torch 2.6.0+cu124).
The split is currently defined operationally by the loader call above; a formal data manifest (DOI, sha256,
and an explicit split definition, including which perturbations are seen versus held out) under the
project's manifest rule is not yet provided and is planned work (Limitations).

### Equivalence and the performance-neutrality claim

We support the narrow performance-neutrality claim through equivalence rather than through a head-to-head
accuracy comparison. The agent wrapper's prediction equals the donor model's `predict()` output element-wise
to a tolerance of 1e-6 across the test set, and the linear anchor reproduces the recorded benchmark score to
a difference of 1.2e-8. This is a wrapper-identity check, not a measurement of an effect; it shows only that
the wrapper does not mutate the model's outputs. Separately, within the offline reliability ablation, arms A
and D run the same mock predictor set, so any difference between those arms is attributable to the runtime
and not to a different model mixture. Together these license the narrow claim that the communicative layer
changes none of the numbers the predictors produce, and nothing stronger.

### External-model integration

The scGPT integration runs in a separate `vc-scgpt` environment (torch 2.3.1 with torchtext 0.18.0), which
resolves a torchtext/torch ABI conflict that blocked the package; a frozen scGPT encoder is paired with a
light trainable head, trained on the donor Norman data with reduced batch size and cell sampling to avoid
out-of-memory failures in the absence of fused attention. The GEARS integration runs in the `virtualcell`
environment with PyTorch Geometric; the donor Norman data is adapted to the GEARS `PertData` format using
local auxiliary files, and six compatibility issues between the GEARS package and current scientific Python
libraries are resolved (a slow upstream download replaced by local data, a removed pandas `Series.nonzero`
restored by a minimal monkey-patch, sparse-view handling, and filtering of a gene absent from the GEARS
ontology graph). The GEARS metric (DE-gene absolute Pearson) and split differ from the delta-expression
protocol above, so its score is reported as non-comparable.

### Ablation design

The ablation compares arm A (ML-only Coordinator stub) against arm D (full PRAXIS-VirtualCell). Both arms
run the same three mock predictors; arm A is a stub that returns a fixed result dictionary
(`abstain=False`, `trace=None`, `provenance=None`, models used = the three mocks), which is a faithful model
of a system that lacks a bus, a brain, and reliability agents. The six seed requests span the outcomes the
metrics depend on:

| # | Request | Expected outcome |
|---|---------|------------------|
| 1 | human, in-vocabulary gene target | predict |
| 2 | human, out-of-vocabulary gene target | reject (`gene_not_in_graph_vocabulary`) |
| 3 | empty perturbation-target list | abstain (`no_perturbation_specified`) |
| 4 | mouse, mappable gene target | predict with ortholog caution |
| 5 | bacteria | abstain (negative transfer) |
| 6 | unknown ("martian") species | abstain (species unknown) |

Five deterministic metrics are computed offline over these requests: out-of-distribution rejection rate,
wrong-model-use rate, provenance completeness, abstention correctness, and trace completeness. Four of the
five are zero for arm A by construction, because a stub with no bus cannot emit a trace or provenance and
never abstains; the contrast therefore measures the presence or absence of the runtime's components, not a
graded improvement. Two intermediate arms were considered and dropped: a brain-guided arm without a bus (B)
had no implementation and would have required inferred rather than measured metrics, and a communicative arm
without reliability (C) shared the agent stack with D on the metrics that matter here. A numeric abstain-gain
is not reported because it requires a declared held-out out-of-distribution perturbation split under the
manifest rule, which is left as planned work.

### Reliability and critic mechanisms

The ensemble agent computes a pairwise-cosine disagreement over the contributing predictions and records an
audit field counting zero-vector pairs so that a disagreement value cannot be misread as a genuine
directional conflict when it arises from degenerate inputs; the threshold is configured in the abstain-rules
file rather than hard-coded. The reliability agent applies seven checks. Four can lead to abstention: empty
targets, a core-predictor failure, all-predictors-rejected (which includes an unsupported species), and
disagreement above threshold. Two can lead to a one-step downgrade: high disagreement and an unsupported
cell type. The seventh sets a baseline reliability from the number of contributing predictors. The critic
agent applies seven trace invariants covering the
retrieve-first ordering, exclusion of rejected predictors, presence of a prediction when not abstaining,
rule references when not abstaining, uncertainty reporting, species support within the ensemble, and
abstention-prediction consistency. The report agent separates abstention reasons from downgrade reasons. A
known limitation of the current mock path is that delta vectors are one-dimensional, so the cosine
disagreement detects sign flips but not magnitude conflicts; multi-dimensional deltas from real predictors
are required to exercise this fully.

### Reproducibility and testing

The offline system is covered by a deterministic test suite that runs on a laptop without a GPU. The suite
at tag `v0.1.0` comprises 75 passing and 23 skipped tests on macOS, where the skipped tests are the
machine-learning tests marked to run only on the remote GPU server and the optional language-model tests.
(The earlier release note that records 71 predates the Week-7 additions and is superseded by this count.)
The prediction loop has no dependency on any language-model API. Two GPU environments are used: `virtualcell`
(torch 2.6) for the donor predictors, Coordinator, and GEARS, and `vc-scgpt` (torch 2.3) for scGPT.

## Limitations

**Performance is a neutrality claim, not an accuracy claim.** The communicative layer does not participate
in tensor computation; delta-expression Pearson is produced by the shared predictors through one evaluation
agent. We show that wrapping predictors as communicating agents does not change their numbers (atol 1e-6),
not that the architecture predicts more accurately. No result should be read as the message bus producing
0.7039.

**The ablation is a capability presence/absence contrast, not a graded comparison.** We report arm A
(ML-only stub) against arm D (full system); both run the same mock predictors. The intermediate
brain-guided-without-bus arm (B) is unimplemented, and the communicative-without-reliability arm (C) is
close enough to D on the relevant metrics that it was not published separately. Four of the five axes are
zero for arm A by construction, because a component-free stub cannot trace, record provenance, or abstain.
The result therefore demonstrates that these behaviors require the runtime; it is not a fine-grained
decomposition of which component contributes which fraction, and it does not establish a graded improvement.
A graded comparison would need an intermediate arm and an end-to-end run with real predictors.

**Several mechanisms are declarative in the offline path.** Model disagreement, core-predictor failure, and
cell-type downgrade do not fire on the end-to-end mock path, because the mock predictors return constant
deltas that do not disagree above threshold, never raise, and carry no cell type. (Ortholog projection is an
exception: it does run, in the cross-species routing path, and is tested; what is not yet demonstrated is
using its output to drive a real cross-species prediction.) The declarative mechanisms are exercised by
hand-written activation unit tests and flagged as declarative in configuration and comments; their
end-to-end activation awaits real, disagreeing, failable predictors.

**Abstain-gain is not quantified.** A numeric measure of how much abstention improves a downstream decision
requires a declared held-out out-of-distribution perturbation split under the project's manifest rule, which
this release does not provide. The same manifest gap means the Norman split here is defined operationally by
the loader recipe rather than by a DOI- and checksum-pinned manifest. We report the abstention mechanism and
its correctness on seed requests, not a benchmark abstain-gain.

**The accuracy comparison lacks independent external baselines.** The six predictors compared on Norman are
all variants of the donor stack, so the table does not yet satisfy a same-protocol comparison against
independent baselines (for example a mean-perturbation control, GEARS, or CPA evaluated under the identical
split and metric). The scGPT and GEARS numbers we do report are an underperforming frozen baseline and a
non-comparable native-pipeline score, respectively, and neither is wired into the runtime as a bus
predictor-agent. Cross-species behavior is routing and rejection only, with no trained high-performance
mouse, bacterial, or yeast predictor.

**The validated scope is human single-cell perturbation prediction.** This release validates its first
implementation on human single-cell perturbation prediction. The mouse, bacterial, and yeast brains are
routing prototypes; we do not claim completed cross-species prediction.

## Data and code availability

Source code is available in the project repository at release tag `v0.1.0`. The Norman 2019 dataset is
publicly available `[CIT:Norman2019]`. Donor predictor checkpoints are used read-only for reproduction. The
offline test suite reproduces all laptop-deterministic results; the machine-learning benchmark results are
reproduced on a GPU server using the environments described in Methods.

## Statements

**AI-usage disclosure.** [Placeholder — venue-specific statement to be generated with the ARS `disclosure`
mode before submission. The drafting, review, and figure code for this manuscript were produced with AI
assistance under author supervision; the predictive results were produced by the offline-reproducible system
described herein and do not depend on any language model.]

**Author contributions.** [Placeholder — CRediT roles TBD.]

**Competing interests.** [Placeholder — TBD.]

**Funding.** [Placeholder — TBD.]

## References

> Citations are deferred this round. The following keys are cited in-text as `[CIT:key]` and will be
> resolved to verified references (with DOIs) in the citation pass. None are fabricated; each is a slot for
> a real work to be verified.

- `[CIT:virtual-cell]` — virtual cell program / position.
- `[CIT:Norman2019]` — Norman et al., combinatorial CRISPR perturbation atlas.
- `[CIT:scGPT]` — scGPT foundation model.
- `[CIT:GEARS]` — GEARS perturbation graph model.
- `[CIT:CPA]` — Compositional Perturbation Autoencoder.
- `[CIT:Geneformer]` — Geneformer.
- `[CIT:STATE]` — STATE / state-transition perturbation model.
- `[CIT:foundation-models]` — single-cell foundation-model evaluation/critique.
- `[CIT:abstention]` — abstention / reject option in ML.
- `[CIT:selective-prediction]` — selective prediction / risk-coverage.
- `[CIT:applicability-domain]` — applicability domain (QSAR / cheminformatics).
- `[CIT:AI-trust]` — trustworthy ML / reliability in scientific ML.
- `[CIT:multi-agent-llm]` — multi-agent LLM systems (for related work / optional-agent context).

---

## Figure legends

**Figure 1 | Architecture and data flow of PRAXIS-VirtualCell.** A virtual-cell task is parsed into a typed
`VirtualCellRequest`, normalized, and routed through the species brain and model-applicability agent before
fan-out to predictor-agents, whose results are ensembled and then assessed by the reliability, critic,
provenance, and report agents. The single message bus is the only communication channel; the
retrieve-before-predict gate (red) makes prediction impossible before brain retrieval; the abstention branch
(amber) is taken when reliability is insufficient. Optional language-model agents (dashed) assist input
interpretation, routing review, critique, and reporting without entering the prediction core.

**Figure 2 | The agent wrapper reproduces the predictors' Norman 2019 scores.** Per-cell delta-expression
Pearson for six donor base predictors and three Coordinator ensembles (per-cell, n = 18,874 test cells;
200 cells per perturbation; seed 1). The all-five Coordinator reaches 0.7039, above the strongest single
base (CPA, 0.6716); the reference line marks 0.70. The gain is a property of the donor Coordinator's
ensembling; the agent wrapper is element-wise identical to the donor models (atol 1e-6), so these are the
predictors' own scores and the communicative layer changes none of them. Source: finding_w4b_multi_anchor,
finding_w4b_coordinator, finding_w4a.

**Figure 3 | Reliability behaviors are present only with the runtime: a capability presence/absence
contrast.** Five system-level metrics for arm A (ML-only Coordinator stub) and arm D (full
PRAXIS-VirtualCell), over six seed requests, offline and deterministic; both arms run the same mock
predictor set, so the only difference is the runtime. Out-of-distribution rejection, provenance
completeness, abstention correctness, and trace completeness are 0.0 for A and 1.0 for D; wrong-model use is
1.0 for A and 0.0 for D. Four of the five are zero for A by construction (a stub with no bus, brain, or
reliability agents cannot trace, record provenance, or abstain), so the figure shows the presence versus
absence of the runtime's components, not a graded improvement. Source: finding_w7.

**Figure 4 | Species-aware routing of one fixed task.** For each species (rows: human, mouse, bacteria,
yeast, and an unknown "martian" species) and predictor (columns), the cell shows applicable,
applicable-with-caution, or rejected, and the right-hand column gives the system outcome. Human is
applicable without caution; mouse is applicable with an ortholog caution (targets projected to the native
host, with unmapped targets flagged); bacteria and yeast are rejected, triggering abstention under the
negative-transfer rule; the unknown species also abstains, without writing fabricated rule references.
Source: finding_w5.

**Figure 5 | Reliability and audit mechanisms.** Schematic of the disagreement estimate (pairwise cosine,
threshold 0.5), the abstention and downgrade triggers merged by the reliability agent, the seven trace
invariants checked by the critic, and the separation of abstention reasons from downgrade reasons in the
report. Mechanisms that are declarative in the offline path are marked. Source: finding_w6.
