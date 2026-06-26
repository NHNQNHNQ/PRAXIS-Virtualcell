# Paper Outline — PRAXIS-VirtualCell v0.1.0

> ARS `academic-paper` **outline-only mode** deliverable (Phase 2, structure_architect).
> Structure: **IMRaD, Nature Methods variant** (Results-forward main text, Methods 后置, Limitations
> explicit, Extended-Data-style supplementary). Each lowest-level node carries a 2–3 sentence content
> summary + the exact verified numbers/anchors + citation PLACEHOLDERs. Citations deferred this round.

### Structure Pattern: IMRaD (Nature Methods variant)

### Overview
The paper opens by framing virtual-cell perturbation prediction as gated by a *trust* deficit rather
than a modeling deficit, then presents PRAXIS-VirtualCell — a brain-guided communicative agent OS — and
answers four questions in four Results sections (understand input → real multi-agent → performance
neutrality → reliability emergence), each tied to one figure. Discussion argues trustworthiness is an
architecture property obtainable without accuracy cost or LLM dependence; Methods (后置) gives the agent
contracts, brain schema, Norman protocol, equivalence argument, external-model integration, ablation
design, and reproducibility; an explicit Limitations section states the six honest boundaries.

---

## Detailed Outline

### 0. Title + Abstract (~200 EN words + ~300 中文字)
**Working title:** *A brain-guided communicative agent operating system for trustworthy virtual-cell
perturbation prediction.*
- **Abstract (EN), 4 moves:**
  1. *Gap* — ML predictors for perturbation→Δexpression answer any input; no applicability check, no
     provenance, no abstention.
  2. *System* — a 10-role agent OS (single message bus, species brain, predictor-agents, ensemble,
     reliability, critic, provenance, report; optional LLM agents) parses tasks into typed requests,
     retrieves species applicability/negative-transfer rules, abstains, traces.
  3. *Results* — reproduces donor Coordinator Norman ΔPearson **0.7039** (wrapper element-wise identical,
     atol 1e-6); the same predictors under the full OS move five reliability axes **0→1** vs an ML-only
     baseline; fully offline-reproducible.
  4. *Scope* — validated on **human single-cell perturbation**; cross-species is routing-level; LLM
     never in the prediction core.
- **Abstract (中文 ~300字):** independent composition, same 4 moves.
- **Keywords (EN):** virtual cell; perturbation prediction; multi-agent systems; model applicability;
  abstention; provenance; reproducibility. **关键词(中文):** 虚拟细胞;扰动预测;多智能体系统;模型适用性;弃权;可追溯。

### 1. Introduction (~700 words)
**Purpose:** establish the trust gap and the OS reframing; preview the four questions.
- **1.1 The prediction target (~180w).** Virtual cell = in-silico prediction of a cell's response;
  concrete task here is single-gene/combination perturbation → delta-expression. Recent predictors span
  task-specific nets and foundation models. *Sources:* `[CIT:virtual-cell]`, `[CIT:Norman2019]`,
  `[CIT:scGPT]`, `[CIT:GEARS]`, `[CIT:CPA]`, `[CIT:Geneformer]`, `[CIT:STATE]`.
- **1.2 The trust gap (~200w).** These models emit a number for *any* query — including out-of-
  distribution species, unsupported perturbation types, and OOV genes — with no rejection, no provenance,
  no abstain. In a discovery setting a confident wrong answer is worse than a declared "cannot answer".
  *Sources:* `[CIT:AI-trust]`, `[CIT:abstention]`, `[CIT:selective-prediction]`.
- **1.3 Why a bigger model is not the fix (~150w).** Our own evidence: a frozen scGPT backbone with a
  light head reaches ΔPearson **0.4407**, *below* task-specific bases (cpa 0.6716) — foundation models
  are components, not a silver bullet (finding_w4c_scgpt). *Sources:* `[CIT:scGPT]`, `[CIT:foundation-models]`.
- **1.4 The reframing (~120w).** PRAXIS-VirtualCell: a brain-guided *communicative agent OS* — heterogeneous
  predictors as agents that negotiate over an auditable message bus, guided by a species brain, abstaining
  when unreliable; LLM agents optional and never in the prediction core.
- **1.5 Four questions (~50w).** (Q1) understand input? (Q2) real multi-agent? (Q3) preserve performance?
  (Q4) improve reliability? → four Results sections, Fig 1–5.
- **Transition →** Q1 begins by showing what enters the system and how it is rejected.

### 2. Results §1 — Structured request understanding and principled rejection (~600 words; Fig 1)
**Purpose:** show inputs become typed/validated requests; unsupported inputs are rejected *with a reason*.
- **2.1 The VirtualCellRequest contract (~200w).** Every task is a typed `VirtualCellRequest` (species,
  perturbation_type, perturbation_targets, input/output_modality, task_type; optional cell_type/tissue/
  dose/time) validated at intake (`core/request.py:17`, `agents/input_interpreter.py:12`). Gene symbols
  normalized (`agents/object_normalizer.py:9`). Free-text is optionally parsed by an LLM interpreter that
  *falls back* offline (`agents_llm/llm_input_interpreter.py:24`). *Evidence:* E12; `test_request_schema`.
- **2.2 Rejection is first-class (~250w).** Unsupported species/modality/task, unsupported perturbation
  type (e.g., drug to a gene-only model), and OOV genes (`gene_not_in_graph_vocabulary`) produce a
  *rejection with reason*, not a silent prediction; empty targets → abstain (`no_perturbation_specified`).
  Concretely, a mouse `aspirin` (drug) request is rejected as `unsupported_perturbation`, not mis-handled
  as a gene (finding_w5 implement-review fix). *Evidence:* E9; `test_predictor_rejection`.
- **2.3 What Fig 1 shows (~150w).** Introduce the architecture/data-flow figure: request → interpreter →
  normalizer → species brain → applicability → predictor fan-out → ensemble → reliability → critic →
  provenance → report, with the retrieve-before-predict gate and the abstain branch annotated.
- **Transition →** if requests are understood and rejectable, is the *coordination* itself trustworthy?

### 3. Results §2 — A constitutively auditable multi-agent system (~700 words; Fig 1)
**Purpose:** show coordination has no privileged back-channel; everything is on the bus and replayable.
- **3.1 One bus, full trace (~200w).** All inter-agent communication is `AgentMessage` on a single
  `MessageBus` that records a complete, replayable `trace` with message lineage (`parent_message_id`)
  (`core/bus.py:10`, `core/message.py:14`). There is no Coordinator→predictor direct call. *Evidence:*
  E12; `test_message_bus`, `test_trace`, `test_no_fake_multiagent`.
- **3.2 Independent predictor-agent rejection (~180w).** Each predictor-agent returns a
  `PredictorResultMessage{status: success|rejected|failed}` and decides applicability for itself
  (`core/message.py:25`, `predictors/base.py`); rejected agents never enter the ensemble. *Evidence:* E12.
- **3.3 The retrieve-before-predict gate (~200w).** A hard gate makes prediction *physically impossible*
  before brain retrieval: any predictor invoked before a `brain_retrieved` message raises
  `RetrieveBeforePredictError` (`predictors/base.py:41-43`); Critic invariant #1 verifies brain-retrieved
  precedes the first predictor_result. This converts "retrieve before predict" from a guideline into an
  enforced control-flow property. *Evidence:* E12; `test_retrieve_before_predict`, `agents/critic.py`.
- **3.4 Honest boundary inline (~120w).** The three offline predictors are mocks returning constant
  deltas (chosen to exercise routing/rejection deterministically on a laptop); real ML predictor-agents
  (`predictors/ml/agent_adapter.py:18`) run on the remote GPU env (§Results 3, Methods 7.4).
- **Transition →** does wrapping real predictors as bus agents cost any accuracy?

### 4. Results §3 — Communicative wrapping is performance-neutral (~750 words; Fig 2)
**Purpose:** the agent layer does not degrade prediction; ensembling reaches 0.7039; foundation ≠ silver bullet.
- **4.1 Norman base predictors (~180w).** Six donor predictors reproduced on Norman 2019 test (per-cell
  ΔPearson, n=18,874, max_cells_per_pert=200, seed=1, esm2): cpa **0.6716** / decoder 0.6709 / gnn 0.6675
  / linear 0.6639 / latent 0.6365 / pretrained(mock) 0.6183 (finding_w4b_multi_anchor; E1).
- **4.2 Coordinator ensemble (~180w).** The donor Coordinator (reused via `coordinator_bridge`) reaches
  all-5 **0.7039**, cpa+decoder+gnn 0.7020, latent+gnn 0.6847 — a +0.032 gain over the best single base
  (finding_w4b_coordinator; E2/E3). Fig 2 plots base + Coordinator bars with a 0.70 reference line.
- **4.3 The wrapper is element-wise identical (~190w).** The agent wrapper's prediction equals the donor
  model's `predict()` element-wise (atol **1e-6**); the linear anchor reproduces the recorded score to
  diff **1.2e-8** (finding_w4a; E4/E5). This is the formal basis for the performance-neutrality claim.
- **4.4 External models, honestly (~120w).** A frozen scGPT backbone + light head reaches ΔPearson
  **0.4407** (cosine 0.9808, n=7290; head saturates, finding_w4c_scgpt) — below task-specific bases.
  GEARS native gives pearson_de **0.8392** but is **not comparable** (DE-gene absolute Pearson + different
  split; finding_w4c_gears).
- **4.5 Honest boundary (load-bearing) (~80w).** The communicative layer never participates in tensor
  computation; ΔPearson is produced by shared predictors through one EvalAgent; the claim is "**not
  harmed**", never "more accurate"; A/D predictor sets are aligned for fairness (finding_w7).
- **Transition →** if accuracy is preserved, what does the OS *add*? Reliability.

### 5. Results §4 — Reliability emerges only with the full agent OS (~950 words; Fig 3, 4, 5)
**Purpose:** removing the OS collapses rejection/provenance/abstain/trace to zero; show the mechanisms.
- **5.1 The A↔D ablation (~260w).** Arm A (ML-only Coordinator stub, no bus/brain/species checks) vs Arm D
  (full PRAXIS), 6 seed requests, Mac offline, deterministic: OOD_rejection **0.0→1.0**, wrong_model_use
  **1.0→0.0**, provenance_completeness **0.0→1.0**, abstain_correctness **0.0→1.0**, trace_completeness
  **0.0→1.0** (finding_w7; E8). Fig 3 = grouped bars. Read as *what the OS adds*, not a graded gain.
- **5.2 Species-aware applicability & negative transfer (~260w).** A concrete instance: the same task
  routed across 4 species (finding_w5; Fig 4). human = 3 predictors applicable, no caution; mouse =
  applicable **+ ortholog caution** (real `map_upper` projection of targets to the native host; unmapped
  targets flagged `unmapped_ortholog`); bacteria = yeast = all reject → abstain (negative-transfer rule
  `mammalian_scrna_predictor_not_applicable`); martian (unknown) = abstain with **no fabricated evidence**
  (no rules_referenced pointing to nonexistent files). *Evidence:* E9.
- **5.3 Disagreement, abstention, and the Critic (~270w).** EnsembleCoordinator computes pairwise-cosine
  model disagreement (threshold 0.5, configurable in `default_abstain_rules.yaml`); ReliabilityAgent
  merges abstain triggers (all-rejected / species-unsupported / core-failed / disagreement) and downgrades
  (disagreement / cell-type); CriticAgent runs **7** trace-honesty invariants (retrieve-first, no rejected
  in ensemble, no prediction without success, missing-provenance, missing-uncertainty, unsupported-species,
  abstain-inconsistency); ReportAgent **separates** `abstain_reasons` from `downgrade_reasons` so a
  downgrade is never misread as an abstention (finding_w6; E10). Fig 5 = mechanism schematic.
- **5.4 Honest boundary (load-bearing) (~160w).** Ablation is **A↔D two poles** (B brain-only is
  paper-only/unimplemented; C ≈ D shares the agent stack — both cut, finding_w7). `disagreement /
  core_predictor_failed / cell_type / real ortholog projection` do **not** fire in the offline mock e2e —
  flagged in yaml/comments/findings and covered by hand-written activation unit tests; real activation
  awaits a real disagreeing/failable predictor (finding_w6). `abstain_gain` numeric is **PLANNED** (needs
  a `data/manifests/norman_2019.yaml` held-out OOD-pert split per the manifest rule; finding_w7).
- **Transition →** Discussion: what this means for trustworthy virtual-cell modeling.

### 6. Discussion (~700 words)
**Purpose:** generalize — trustworthiness is architecture, obtainable without accuracy cost or LLM dependence.
- **6.1 Architecture as the trust substrate (~200w).** Rejection, provenance, and abstention are *emergent
  OS behaviors*, not predictor features; the bus + gate + critic make them auditable by construction.
- **6.2 Foundation models are components (~150w).** scGPT-frozen underperforming task-specific nets
  supports treating foundation models as one applicable-or-not predictor among many, gated by the brain.
- **6.3 Adversarial validation as method (~180w).** Each W5–W7 feature passed a dual workflow
  (design-review + implementation-review) that caught paper-only mechanisms, dead code, and fake evidence
  before shipping — a transferable practice for systems papers making reliability claims (finding_w5/6/7).
- **6.4 What real predictor-agents unlock (~100w).** Activating disagreement/core-failure/cell-type;
  computing abstain_gain on a manifest OOD split; multi-species real predictors.
- **6.5 Outlook (~70w).** Toward a multi-species, multi-task virtual-cell OS.

### 7. Methods (后置, ~3,000 words)
- **7.1 Agent contracts & message bus (~450w).** `MessageBus`/`AgentMessage`/`AgentRuntime`
  (`core/bus.py`, `core/message.py`, `core/runtime.py`); 10 agent roles = 12 deterministic agents incl. 3
  predictor-agents + 4 optional LLM agents; message-type vocabulary; retrieve-before-predict gate.
- **7.2 Request schema & parsing (~250w).** Field-by-field `VirtualCellRequest`; deterministic vs LLM
  parsing; offline fallback; normalization rules.
- **7.3 Species brain schema (~500w).** `brains/virtualcell/{generic,human,mouse,bacteria,yeast}/*.yaml`
  (model_applicability / object_vocabulary / ortholog_rules / negative_transfer / abstain_rules /
  genetic_interaction_rules); SpeciesBrain + ModelApplicability read paths; **runtime vs declarative**
  fields explicitly separated (finding_w5).
- **7.4 Norman benchmark protocol (~400w).** Donor ML predictors via `donor_bridge`; EvalAgent per-cell
  ΔPearson; exact reproduction recipe (`load_vcbench_split("norman_2019","test",max_cells_per_pert=200,
  rng_seed=1)`, esm2, weights_only=False); Coordinator via `coordinator_bridge`; remote A100 env.
- **7.5 Equivalence / performance-neutrality (~250w).** Wrapper == donor predict atol 1e-6; anchor diff
  1.2e-8; A/D predictor-set alignment; why this licenses "not harmed".
- **7.6 External-model integration (~400w).** scGPT frozen-head pipeline + torchtext ABI break (vc-scgpt
  env, torch 2.3.1 + torchtext 0.18); GEARS native pipeline + PyG + 6 compatibility fixes; explicit
  non-comparability statement.
- **7.7 Ablation design (~300w).** A↔D arms; 6 seed requests; 5 deterministic metrics; why B/C were cut;
  `abstain_gain` PLANNED and gated on the manifest rule.
- **7.8 Reliability & Critic mechanisms (~300w).** Pairwise-cosine disagreement (zero-vector audit field;
  threshold config); 7 reliability checks; 7 Critic invariants; report split; honest 1-D-delta limit.
- **7.9 Reproducibility & testing (~150w).** Mac 75 passed + 23 skipped; remote ML tests `@pytest.mark.
  remote`; offline determinism; env matrix (virtualcell torch 2.6 / vc-scgpt torch 2.3).

### 8. Limitations (~500 words) — six honest boundaries, one paragraph each
L1 performance not in tensor path ("not harmed" only) · L2 ablation A↔D two poles · L3 declarative
mechanisms not activated in mock e2e (activation tests exist) · L4 abstain_gain not done (needs manifest) ·
L5 scGPT frozen / GEARS not comparable / cross-species routing-only · L6 minimal scope (human single-cell).

### 9. Data & Code Availability + statements (~150 words)
GitHub repo @ `v0.1.0`; Norman 2019; donor checkpoints (read-only). AI-usage disclosure; Author
Contributions (CRediT); Competing Interests; Funding — per ARS mandatory inclusions.

---

## Evidence Map (section ← evidence id; see 00_chapter_plan.md for the E# → finding table)

| Section | Assigned evidence | Type |
|---------|------------------|------|
| 1 Introduction | E6 (scGPT<base); PLACEHOLDER lit | problem framing |
| 2 Results §1 | E9, E12 | schema + rejection |
| 3 Results §2 | E12 | bus / gate / trace |
| 4 Results §3 | E1, E2, E3, E4, E5, E6, E7 | performance |
| 5 Results §4 | E8, E9, E10 | reliability |
| 6 Discussion | E6, E8 + methodology | synthesis |
| 7 Methods | E11, E12 + all | protocol |
| 8 Limitations | E5, E8 + boundaries | honesty |

## Word Count Summary
| Section | Target |
|---------|--------|
| Abstract (EN+中文) | 200 + 300字 |
| 1 Introduction | 700 |
| 2 Results §1 | 600 |
| 3 Results §2 | 700 |
| 4 Results §3 | 750 |
| 5 Results §4 | 950 |
| 6 Discussion | 700 |
| **Main subtotal** | **~4,400** |
| 7 Methods | ~3,000 |
| 8 Limitations | ~500 |
| 9 Availability | ~150 |
| References | (deferred) |

## Figure ↔ section binding
- **Fig 1** architecture/data-flow → §1 (intro'd), §2.3, §3 (bus/gate).
- **Fig 2** Norman base + Coordinator ΔPearson bars → §4.2.
- **Fig 3** ablation A↔D 5-metric grouped bars → §5.1.
- **Fig 4** cross-species 4×3 routing heatmap (applicable/caution/reject) → §5.2.
- **Fig 5** reliability mechanism schematic (disagreement / abstain triggers / provenance-trace) → §5.3.
