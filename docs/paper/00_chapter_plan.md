# Chapter Plan — PRAXIS-VirtualCell v0.1.0 (systems/methods paper)

> ARS `academic-paper` **plan mode** deliverable. Produced from the author-supplied blueprint
> (`docs/HANDOFF-paper-v0.1.md`) + verified evidence (`docs/findings/*`, code `praxis_virtualcell/`
> with `file:line` anchors). Every number is traced to a finding; nothing fabricated.
> Body language: **English**. Communication: 简体中文. Output: Markdown (`docs/paper/`).

---

## Paper Configuration Record (Plan Mode)

| Parameter | Value |
|-----------|-------|
| **Topic** | A brain-guided communicative agent operating system (OS) for trustworthy virtual-cell perturbation prediction |
| **Paper Type** | Systems / Methods (Nature Methods–style; IMRaD with Methods 后置 + Extended Data) |
| **Target Journal** | Nature Methods style (numbered superscript references; main ~4,500 words + Methods) |
| **Citation Format** | Nature numbered (deferred — related-work + refs are placeholders this round; citation pipeline runs before finalize) |
| **Output Format** | Markdown (primary, `docs/paper/`) |
| **Body Language** | English |
| **Abstract** | Bilingual: EN (150–200 words) + 简体中文 (~300 字) |
| **Word Count Target** | Main text ~4,500; Methods ~3,000; Limitations ~500 |
| **Existing Materials** | RELEASE notes, 11 findings (w4a–w7), full source with architecture `file:line` map; no external literature corpus this round |
| **Operational Mode** | plan → outline → full (chained) |
| **Honesty regime** | 6 honest boundaries are load-bearing; every performance/ablation claim restricted per finding |

---

## INSIGHT Collection (extracted from the author's own framing — not invented)

- **[INSIGHT: thesis_statement]** Trustworthy virtual-cell prediction is gated not by a better single
  predictor but by the *operating system around predictors*. PRAXIS-VirtualCell parses a virtual-cell
  task into a structured biological request, retrieves species-aware model-applicability and
  negative-transfer rules from a "species brain", coordinates heterogeneous predictor-agents through a
  single auditable message bus, abstains when reliability is insufficient, and emits a fully replayable
  provenance trace — **without degrading predictive accuracy and without any LLM in the prediction core**.

- **[INSIGHT: contribution_claim]** The same shared predictors, wrapped by the agent OS, move five
  reliability axes from **0 → 1** (OOD rejection, wrong-model-use prevention, provenance completeness,
  abstain correctness, trace completeness; finding_w7) while the predictive layer reproduces the donor
  Coordinator's Norman ΔPearson **0.7039** (all-5 ensemble; finding_w4b_coordinator) and the wrapper is
  element-wise identical to the underlying model (atol 1e-6; finding_w4a). The system is **fully
  reproducible offline**; optional LLM agents only assist input interpretation / routing review /
  critique / reporting and never replace a predictor.

- **[INSIGHT: methodological_honesty]** Every Week-5–7 feature passed a *dual adversarial workflow*
  (design-review + implementation-review) that caught paper-only mechanisms, dead code, and fake
  evidence before they shipped (finding_w5/w6/w7). Claims that are declarative-but-not-yet-activated in
  the offline mock path are flagged as such, with hand-written unit tests proving they *can* activate.
  The performance claim is deliberately limited to "**not harmed**", never "more accurate".

---

## Thesis crystallization (Step 1)

**What the paper argues.** Current virtual-cell predictors (foundation models and task-specific nets)
output a number for *any* input — no notion of "I should not answer this", no record of *why* a model
was used, no species-applicability check. PRAXIS-VirtualCell reframes the problem as building a
*communicative agent OS* whose components negotiate over a message bus, so that rejection, provenance,
and abstention become first-class, auditable behaviors — at zero cost to the predictor's accuracy.

**How a skeptic responds, and our answer.**
1. *"This is just an ensemble with logging."* — No: the message bus is the **only** communication
   channel; predictor-agents reject independently; a hard `retrieve-before-predict` gate makes a
   prediction physically impossible before brain retrieval (`predictors/base.py:41-43`,
   `RetrieveBeforePredictError`); the Critic checks 7 trace invariants. Ablation A↔D shows the
   reliability axes collapse to 0 when the agent OS is removed (finding_w7).
2. *"You're claiming the agent architecture improves accuracy."* — We explicitly do **not**. The
   communicative layer never touches the tensor path; Pearson is produced by shared predictors through
   one EvalAgent; the claim is *performance-neutral* (equivalence atol 1e-6).
3. *"Cross-species / reliability mechanisms are vaporware."* — Routing, ortholog projection, and
   negative-transfer rejection run deterministically and are tested (finding_w5). Mechanisms that do
   not fire in the offline mock path (disagreement / core-failure / cell-type downgrade) are honestly
   flagged and covered by activation unit tests (finding_w6).

**What the reader should think differently after reading.** For virtual cells, *trustworthiness is an
architecture problem, not only a modeling problem* — and it can be obtained without sacrificing accuracy
and without hard LLM dependence.

---

## Chapter-by-chapter plan (core argument · evidence · word budget)

### 0. Title + Abstract (~200 EN words + ~300 中文字)
- Working title: **"A brain-guided communicative agent operating system for trustworthy virtual-cell
  perturbation prediction"**.
- Abstract arc: gap (ML-only predictors can't reject / trace / abstain) → system (10-role agent OS over
  a message bus, species brain, abstain, provenance) → key results (Norman ΔPearson 0.7039 preserved;
  five reliability axes 0→1; fully offline-reproducible) → honest scope (validated on human single-cell
  perturbation; cross-species is routing-level).

### 1. Introduction (~700 words)
- **Core argument:** the trust gap in virtual-cell prediction is structural; foundation/task-specific
  models lack applicability checks, provenance, and abstention.
- **Beats:** (a) virtual cell as a prediction target; perturbation→Δexpression task. (b) The reliability
  gap: a model answers any query, including out-of-distribution species and unsupported perturbations.
  (c) Why "just a bigger model" doesn't close it — and our finding that a frozen scGPT backbone is *not*
  a silver bullet (ΔPearson 0.4407 < task-specific bases; finding_w4c_scgpt). (d) Our reframing:
  brain-guided communicative agent OS; LLM optional, never in the prediction core. (e) Four guiding
  questions = four Results sections. (f) Contribution list.
- **Evidence/anchors:** scGPT 0.4407 (finding_w4c_scgpt); positioning sentence (RELEASE §定位).
- **Citations:** PLACEHOLDER `[CIT:…]` for scGPT, GEARS, CPA, Geneformer, STATE, Norman 2019,
  multi-agent-LLM, AI-trust/abstention. (Filled in citation round.)

### 2. Results §1 — "Can the system understand a virtual-cell request?" (~600 words, Fig 1)
- **Core argument:** inputs are parsed into a typed, validated `VirtualCellRequest`; unsupported inputs
  are *rejected with a reason*, not silently answered.
- **Evidence:** `VirtualCellRequest` schema (species / perturbation_type / perturbation_targets /
  input&output_modality / task_type / optional cell_type; `core/request.py:17`); deterministic
  `InputInterpreterAgent` (`agents/input_interpreter.py:12`) + object normalization
  (`BioObjectNormalizerAgent`, `agents/object_normalizer.py:9`); optional LLM free-text parser
  (`agents_llm/llm_input_interpreter.py:24`) with offline fallback; rejection paths
  (`unsupported_perturbation`, `gene_not_in_graph_vocabulary`, empty targets → abstain). Tests
  `test_request_schema`, `test_predictor_rejection`.
- **Figure:** Fig 1 (architecture/data-flow) introduced here; gate + abstain branch annotated.

### 3. Results §2 — "Is it a *real* multi-agent system?" (~700 words, Fig 1)
- **Core argument:** coordination is *constitutively* auditable — there is no privileged back-channel.
- **Evidence:** `MessageBus` is the sole channel and records a full replayable `trace`
  (`core/bus.py:10`); `AgentMessage` lineage via `parent_message_id` (`core/message.py:14`);
  predictor-agents emit `PredictorResultMessage{status: success|rejected|failed}` and reject
  independently (`core/message.py:25`, `predictors/base.py`); **retrieve-before-predict** hard gate
  (`predictors/base.py:41-43`); no Coordinator→predictor direct call; Critic invariant #1 enforces
  brain-retrieved precedes first predictor_result (`agents/critic.py`). Tests `test_no_fake_multiagent`,
  `test_retrieve_before_predict`, `test_message_bus`/`test_trace`.
- **Honesty:** the 3 offline predictors are mocks returning constant deltas; real ML predictor-agents
  (`predictors/ml/agent_adapter.py:18`) run only on the remote GPU env.

### 4. Results §3 — "Does the communicative wrapper preserve predictive performance?" (~750 words, Fig 2)
- **Core argument:** wrapping predictors as agents is **performance-neutral**; ensembling via the donor
  Coordinator reaches ΔPearson 0.7039.
- **Evidence (Norman 2019, per-cell ΔPearson, n=18,874 test, max_cells_per_pert=200, seed=1, esm2):**
  bases cpa **0.6716** / decoder 0.6709 / gnn 0.6675 / linear 0.6639 / latent 0.6365 / pretrained(mock)
  0.6183 (finding_w4b_multi_anchor); Coordinator all-5 **0.7039**, cpa+decoder+gnn 0.7020, latent+gnn
  0.6847 (finding_w4b_coordinator); ensemble gain +0.032 over best base. Anchor reproduction: S0
  0.66385874 vs S_eval, diff **1.2e-8** (finding_w4a_norman_anchor); wrapper == donor `predict()`
  element-wise **atol 1e-6** (finding_w4a). External models: scGPT frozen head **0.4407** (cosine
  0.9808, n=7290; finding_w4c_scgpt) — honest "foundation ≠ silver bullet"; GEARS native pearson_de
  **0.8392** — *not comparable* (different metric=DE-gene absolute Pearson + different split;
  finding_w4c_gears).
- **Honesty (load-bearing):** communicative layer does not participate in tensor computation; Pearson
  comes from shared predictors via one EvalAgent; claim = "not harmed", **never** "more accurate"; A vs
  D predictor sets aligned for fairness (finding_w7).
- **Figure:** Fig 2 (base + Coordinator ΔPearson bars, 0.70 reference line).

### 5. Results §4 — "Does the agent OS improve reliability?" (~900 words, Fig 3, Fig 4, Fig 5)
- **Core argument:** reliability behaviors *emerge only with the full OS*; removing it collapses them.
- **Evidence — ablation A(ML-only Coordinator) ↔ D(Full PRAXIS), 6 seed requests, Mac offline,
  deterministic (finding_w7):** OOD_rejection 0.0→1.0 · wrong_model_use 1.0→0.0 ·
  provenance_completeness 0.0→1.0 · abstain_correctness 0.0→1.0 · trace_completeness 0.0→1.0 (Fig 3).
- **Evidence — cross-species routing as a concrete applicability instance (finding_w5, Fig 4):** human =
  3 predictors applicable, no caution; mouse = applicable **+ ortholog caution** (real `map_upper`
  projection; unmapped targets flagged `unmapped_ortholog`); bacteria = yeast = all reject → abstain
  (negative-transfer rule `mammalian_scrna_predictor_not_applicable`); martian (unknown) = abstain with
  **no fabricated evidence** (no `rules_referenced` pointing to nonexistent files).
- **Evidence — reliability/critic mechanisms (finding_w6, Fig 5):** EnsembleCoordinator computes
  pairwise-cosine model disagreement (threshold 0.5, configurable); ReliabilityAgent merges abstain
  triggers (all-rejected / species-unsupported / core-failed / disagreement) and downgrades
  (disagreement / cell-type); CriticAgent runs 7 trace-honesty invariants; ReportAgent **separates**
  `abstain_reasons` vs `downgrade_reasons`.
- **Honesty:** ablation is **A↔D two poles** (B brain-only = paper-only/unimplemented; C ≈ D same agent
  stack — both cut, finding_w7); `disagreement / core_predictor_failed / cell_type / real ortholog
  projection` do **not** fire in the offline mock e2e — flagged in yaml/comments/findings and covered by
  activation unit tests, real activation awaits a real disagreeing/failable predictor (finding_w6);
  `abstain_gain` numeric is **PLANNED** (needs `data/manifests/norman_2019.yaml` held-out OOD-pert
  split per the manifest rule; not done, finding_w7).

### 6. Discussion (~700 words)
- **Core argument:** trustworthiness for virtual cells is an *architecture* property obtainable without
  accuracy cost or LLM dependence; foundation models are components, not solutions.
- **Beats:** (a) communicative architecture value — rejection/provenance/abstain as emergent OS
  behaviors. (b) foundation-model-is-not-a-silver-bullet (scGPT evidence). (c) the adversarial-validation
  methodology as a transferable engineering practice (dual-workflow caught paper-only mechanisms). (d)
  what real predictor-agents unlock (activating the declarative mechanisms; abstain_gain on a manifest
  OOD split). (e) outlook to multi-species real predictors.

### 7. Methods (后置, ~3,000 words)
- 7.1 Agent contracts & the message bus (`MessageBus`/`AgentMessage`/`AgentRuntime`; 10 agent roles =
  12 deterministic agents incl. 3 predictor-agents + 4 optional LLM agents; the retrieve-before-predict
  gate).
- 7.2 `VirtualCellRequest` schema & parsing (deterministic + optional LLM, offline fallback).
- 7.3 Species brain schema (`brains/virtualcell/{generic,human,mouse,bacteria,yeast}/*.yaml`:
  model_applicability / object_vocabulary / ortholog_rules / negative_transfer / abstain_rules /
  genetic_interaction_rules); SpeciesBrain + ModelApplicability read paths; runtime vs declarative
  fields (honestly separated, finding_w5).
- 7.4 Norman benchmark protocol (donor ML predictors via `donor_bridge`, EvalAgent per-cell ΔPearson,
  exact reproduction recipe; Coordinator via `coordinator_bridge`).
- 7.5 Equivalence / performance-neutrality argument (wrapper == donor predict atol 1e-6; A/D
  predictor-set alignment).
- 7.6 External-model integration (scGPT frozen-head pipeline & env break; GEARS native pipeline & 6
  compatibility fixes; non-comparability statement).
- 7.7 Ablation design (A↔D arms, 6 seed requests, 5 deterministic metrics; why B/C were cut;
  abstain_gain PLANNED).
- 7.8 Reliability & Critic mechanisms (disagreement metric, 7 reliability checks, 7 Critic invariants,
  report split).
- 7.9 Reproducibility & testing (Mac 75 passed + 23 skipped; remote ML tests `@remote`; offline
  determinism; env matrix virtualcell/vc-scgpt).

### 8. Limitations (~500 words) — the 6 honest boundaries, each as one paragraph
1. Performance dimension: communicative layer not in tensor path → "not harmed" only.
2. Ablation is A↔D two poles (B paper-only, C≈D unpublished).
3. Declarative mechanisms not activated in mock e2e (activation tests exist; await real predictor).
4. `abstain_gain` numeric not done (needs manifest OOD-pert split).
5. scGPT frozen limitation / GEARS not comparable / cross-species routing-only.
6. Minimal scope: validated only on human single-cell perturbation prediction.

### 9. Data & Code Availability + mandatory statements (~150 words)
- GitHub repo at tag `v0.1.0`; Norman 2019 source; donor checkpoints (read-only). AI-usage disclosure,
  Author Contributions, Competing Interests, Funding — per ARS mandatory inclusions.

---

## Evidence map (claim → source, one row per load-bearing number)

| # | Claim | Number | Source |
|---|-------|--------|--------|
| E1 | Best single base predictor | cpa ΔPearson 0.6716 | finding_w4b_multi_anchor |
| E2 | Coordinator all-5 ensemble | ΔPearson 0.7039 | finding_w4b_coordinator |
| E3 | Ensemble gain over best base | +0.032 | finding_w4b_coordinator |
| E4 | Anchor reproduction precision | diff 1.2e-8 (n=18,874) | finding_w4a_norman_anchor |
| E5 | Wrapper ≡ donor predict | atol 1e-6 | finding_w4a (M2) |
| E6 | scGPT frozen head | ΔPearson 0.4407 (n=7290) | finding_w4c_scgpt |
| E7 | GEARS native (NOT comparable) | pearson_de 0.8392 | finding_w4c_gears |
| E8 | Ablation A↔D (5 axes) | 0↔1 each | finding_w7 |
| E9 | Cross-species routing (4 species) | applicable/caution/reject | finding_w5 |
| E10 | Reliability/Critic mechanisms | disagreement thr 0.5; 7+7 checks | finding_w6 |
| E11 | Test scale | Mac 75 passed + 23 skipped | RELEASE-v0.1.0 / HANDOFF |
| E12 | Architecture (10 roles, gate) | file:line anchors | code map (this session) |

---

## Argument stress test (Step 3 — weakest points & defenses)

- **Weakest point:** the headline reliability result is a 0↔1 ablation where arm A is a deliberately
  component-free stub. *Defense:* A is a faithful "no-OS" baseline (it genuinely lacks bus/brain/species
  checks; finding_w7), the metrics are deterministic and reproducible offline, and the claim is about
  *what the OS adds*, not a graded improvement. We state this explicitly and do not over-read 0↔1 as a
  continuous gain.
- **Reverse the argument:** if reliability were purely a modeling property, removing the OS would not
  change rejection/provenance/abstain — but it drops them all to 0. The argument holds.
- **Second weak point:** performance "neutrality" could be read as "the architecture is free but
  useless for accuracy". *Defense:* we scope the performance claim narrowly and locate value on the
  reliability axes, not accuracy.

---

## Production plan (next pipeline steps)
1. `/ars-outline` → detailed outline + evidence map per paragraph → `docs/paper/01_outline.md`.
2. `/ars-full` → write → in-pair review → revise → finalize draft → `docs/paper/PRAXIS-VirtualCell-v0.1-manuscript.md` (citations as placeholders this round).
3. `nature-figure` (Python/matplotlib) → Fig 1–5 → `docs/paper/figures/` (SVG + PDF + 600dpi TIFF).
4. (Deferred) citation pipeline once related-work is filled.
