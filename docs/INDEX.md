# PRAXIS-VirtualCell Documentation Index

> Audited: 2026-08-06
>
> Status: `CURRENT_DOCUMENT_MAP — P15E_ENGINEERING_COMPLETE_P16E_ELIGIBLE`

This is the navigation authority for the repository. It does not make every linked document current: each section explicitly distinguishes live truth, frozen evidence, active plans, drafts, and history.

## Truth precedence

When documents disagree, use this order:

1. Exact local bytes, `git rev-parse` identity, immutable artifacts and the current work-unit completion report.
2. [README](../README.md), the [current integration guide](PRAXIS-VIRTUALCELL-CURRENT-PROJECT-AND-INTEGRATION-GUIDE.md), the [P15E completion report](../reports/phase15e/PHASE15E_COMPLETION.md), the preserved [P14E completion report](../reports/phase14e/PHASE14E_COMPLETION.md), [P13 completion report](../reports/phase13/PHASE13_COMPLETION.md), [P12 completion report](../reports/phase12/PHASE12_COMPLETION.md), and the [P12–P30 execution plan](PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md) for current phase selection and boundaries.
3. The latest completed phase ADR/runbook—P15E uses [ADR-0012](ADR-0012-virtualcell-yeast-deletion-fitness-contract.md) and the [yeast deletion-fitness runbook](runbooks/VIRTUALCELL-YEAST-DELETION-FITNESS-CONTRACT.md); P14E remains documented by [ADR-0011](ADR-0011-virtualcell-ecoli-k12-growth-contract.md) and the [E. coli K-12 growth-contract runbook](runbooks/VIRTUALCELL-ECOLI-K12-GROWTH-CONTRACT.md), P13 by [ADR-0010](ADR-0010-virtualcell-model-adapter-sdk.md), and P12 by [ADR-0009](ADR-0009-virtualcell-model-zoo-v2.md)—for implemented contract and validation boundaries.
4. [Phase 10 Gate](../reports/phase10/PHASE10_GATE.md) for frozen scientific capability and claim boundaries.
5. [Three-Way Sync State](status/SYNC-STATE.md) only for its dated local/GitHub/`.53` observations; it is not fresh remote authorization.
6. Dated plans, handoffs, findings, papers, release notes and [Project State 2026-07-18](status/PROJECT-STATE-2026-07-18.md) as historical evidence for their stated commit/date only.

Plans describe intended work. A task is not complete merely because a plan says it should happen; only checked gates plus recorded verification count as completion.

P15E is complete only as a local engineering contract at code
`62480a3951173a2aa7b006403af9b169521db138` and tree
`64906691c4c989a843df4da97f0a93f32cd65ad2`, starting from P14E docs-closure
`0ff6870a70a04d71098a16875e633f909e31cc5a`. Its exact S288C deletion-fitness
adapter is contract-only, local-registration-only, absent from the default registry and fixed to
negative compatibility `p15r_not_authorized`. P15E did not read or run real assets/GEM, establish
scientific evidence, make a policy decision, publish a release, bump a version or deploy. P15R
remains `AUTHORIZATION_REQUIRED / NOT_RUN`, P15B remains `NOT_RUN`, and P16E is the next eligible
local gate; it is not complete.

## Current state

| Document | Authority |
|---|---|
| [README](../README.md) | current product promise, P15E completion boundary and primary operator entry points |
| [Current Project and Integration Guide](PRAXIS-VIRTUALCELL-CURRENT-PROJECT-AND-INTEGRATION-GUIDE.md) | current project ledger, protected paths and P13–P15E boundary |
| [P15E Completion Report](../reports/phase15e/PHASE15E_COMPLETION.md) | exact P15E code/tree, local contract validation, reproducible wheel and P15R/P15B non-claims |
| [P15E S. cerevisiae Deletion-Fitness Contract ADR](ADR-0012-virtualcell-yeast-deletion-fitness-contract.md) | exact S288C scope, strict prepared binding, negative compatibility and local-only registration |
| [P15E S. cerevisiae Deletion-Fitness Runbook](runbooks/VIRTUALCELL-YEAST-DELETION-FITNESS-CONTRACT.md) | local contract audit, directed validation, P15R authorization gate and fail-closed interpretation |
| [P14E Completion Report](../reports/phase14e/PHASE14E_COMPLETION.md) | exact P14E start/code/tree, contract-only validation, packaging evidence and P14R/P14B non-claims |
| [P14E E. coli K-12 Growth Contract ADR](ADR-0011-virtualcell-ecoli-k12-growth-contract.md) | exact scope, nine strict contracts, prepared-bound output and default-registry isolation |
| [P14E E. coli K-12 Growth Contract Runbook](runbooks/VIRTUALCELL-ECOLI-K12-GROWTH-CONTRACT.md) | local contract audit, directed validation, P14R authorization gate and fail-closed interpretation |
| [P13 Completion Report](../reports/phase13/PHASE13_COMPLETION.md) | preserved historical P13 start/code/tree, Adapter SDK validation and science/policy non-claims |
| [P13 Model Adapter SDK ADR](ADR-0010-virtualcell-model-adapter-sdk.md) | preserved P13 SDK schemas, exact identity/input/output binding, delta reference path and fail-closed decisions |
| [P13 Model Adapter SDK Runbook](runbooks/VIRTUALCELL-MODEL-ADAPTER-SDK.md) | preserved P13 adapter registration, conformance, runtime audit and directed local verification |
| [P12 Completion Report](../reports/phase12/PHASE12_COMPLETION.md) | exact P12 code SHA, validation, artifact fingerprints and science/policy non-claims |
| [P12–P30 Sequential Master Prompt](PHASE12-30-SEQUENTIAL-MASTER-PROMPT.md) | superseded per-phase authorization prompt; historical only |
| [P12–P30 Execution Plan](PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md) | phase scopes, dependencies and exact authorization templates |
| [P12 Model Zoo v2 ADR](ADR-0009-virtualcell-model-zoo-v2.md) | completed layered identities, v1 migration, fail-closed execution and safe-load decisions |
| [P12 Model Zoo v2 Runbook](runbooks/VIRTUALCELL-MODEL-ZOO-V2.md) | read-only catalog/API interpretation and P12 validation commands |
| [Project State](status/PROJECT-STATE-2026-07-18.md) | historical APFS migration and phase restart snapshot; not current branch/ref authority |
| [Phase A Completion Gate](status/PHASE-A-GATE-2026-07-18.md) | proof that migration/organization protections passed before baseline testing |
| [Post-consolidation Quality Baseline](../reports/quality/BASELINE-2026-07-18.md) | Phase B commands, exact results, failure ownership, and `PHASE_B_COMPLETE` gate |
| [Phase D0 Sync Proposal](status/PHASE-D0-SYNC-PROPOSAL-2026-07-18.md) | frozen pre-publication ledger, exact D1/D2 protocol, protected exceptions, and rollback plan; not the current live sync ledger |
| [Phase D1a CI Report](status/PHASE-D1A-CI-2026-07-22.md) | first exact candidate-branch publication, run `29894971142`, `1/5` diagnosis, local remediation evidence, and retry authorization boundary |
| [Phase D1a CI Retry Report](status/PHASE-D1A-CI-RETRY-2026-07-23.md) | exact `6086… → ee36…` retry, run `29971566980`, `4/5` result, Linux process-group diagnosis, and locally verified repair |
| [Phase C5 Scientific Gate](status/PHASE-C5-GATE-2026-07-18.md) | frozen 2026-07-18 scientific classification, Gate A seam evidence, explicit remote pending, and D0 handoff |
| [Scientific Assets](status/SCIENTIFIC-ASSETS-2026-07-18.md) | wheel/container/source/private asset matrix, provenance, licence gaps, and permitted claims |
| [Phase C4 Completion Gate](status/PHASE-C4-GATE-2026-07-18.md) | frozen local dependency/bundle/wheel/API/Linux-container evidence and `C4_COMPLETE_LOCAL` boundary |
| [Phase C3 Completion Gate](status/PHASE-C3-GATE-2026-07-18.md) | frozen local theme/full-E2E/request-boundary evidence, exact C3 counts, honest S10 skip, and `C3_COMPLETE_LOCAL` boundary |
| [Three-Way Sync State](status/SYNC-STATE.md) | three-way ledger with explicit freshness labels and the Phase D synchronization protocol |
| [Worktree Asset Classification](status/WORKTREE-ASSETS.md) | accepted theme disposition plus continuing protection of `.claude/`, Playwright MCP output, screenshot, and stash |
| [Versioning Contract](VERSIONING.md) | implemented product/protocol/schema/artifact version boundaries and release invariants |
| [Testing Guide](TESTING.md) | current local commands, exact scopes, external gates, and GitHub-CI evidence boundary |
| [VirtualCellPack P5 → P6 Handoff](HANDOFF-VIRTUALCELLPACK-P5-TO-P6.md) | local P5 implementation, exact strict-lock evidence, limitations and next exact-SHA authorization gate |
| [VirtualCellPack P6 → P7 Handoff](HANDOFF-VIRTUALCELLPACK-P6-TO-P7.md) | local P6 capability-runtime implementation, exact tests, limitations and next exact-SHA authorization gate |
| [VirtualCellPack P7 → P8 Handoff](HANDOFF-VIRTUALCELLPACK-P7-TO-P8.md) | local P7 strict data catalog, verified external files, controlled quarantine upload, exact tests and next exact-SHA authorization gate |
| [VirtualCellPack P8 → P9 Handoff](HANDOFF-VIRTUALCELLPACK-P8-TO-P9.md) | Golden Norman evidence plus P8 product surfaces, three tiny Packs, fail-closed matrix, exact tests and next exact-SHA authorization gate |
| [VirtualCellPack P9 → P10 Handoff](HANDOFF-VIRTUALCELLPACK-P9-TO-P10.md) | local P0–P9 closure, negative scientific gate, preview boundary, exact evidence and remaining publication gate |
| [Repository Layout](REPOSITORY-LAYOUT.md) | tracked-tree responsibilities and evidence-versus-generated policy |
| [Phase 10 Gate](../reports/phase10/PHASE10_GATE.md) | highest authority for met/narrowed/needs-new/unsupported scientific claims |

## User and operator documents

| Document | Status |
|---|---|
| [README](../README.md) | current product overview, quick start, capability limits, tests, and synchronization flow |
| [Installation Guide](INSTALL.md) | source, full release wheel, Docker container, portable checkout, and optional-extra contracts |
| [User Guide](USER-GUIDE.md) | CLI, five-stage/six-tab UI, output, modes, packaged web entry, and same-origin React flow |
| [Examples](EXAMPLES.md) | offline accept/caution/abstain examples and interpretation boundaries |
| [LLM Interface Guide](USAGE-llm-interface.md) | v0.6-era optional LLM/API interface; deterministic-runtime red lines remain applicable |
| [Remote Science Validation](runbooks/REMOTE-SCIENCE-VALIDATION.md) | approved-SHA `.53` W4B/Gate A procedure; currently `REMOTE_NOT_RUN` and not synchronization authorization |
| [VirtualCellPack Data Portal](runbooks/VIRTUALCELLPACK-DATA-PORTAL.md) | P7 external data-root layout, fixed inventory, upload quarantine, verification and update procedure |
| [Golden Norman/K562](runbooks/VIRTUALCELLPACK-GOLDEN-NORMAN.md) | P8 source verification, deterministic Pack derivation, simple baseline build, formal evaluation and remote hash audit |
| [VirtualCellPack Product Surfaces](runbooks/VIRTUALCELLPACK-PRODUCT-SURFACES.md) | P8 tiny built-in Packs, CLI/API/UI discovery, local registration, compatibility planning and immutable job identity |
| [VirtualCellPack P9 OOD Validation](runbooks/VIRTUALCELLPACK-P9-OOD-VALIDATION.md) | frozen multi-axis split contract, grouped leakage audit, validation-only abstention threshold and adaptation-free GSE67402→GSE94117 reproduction |
| [Virtual Cell Model Zoo v2](runbooks/VIRTUALCELL-MODEL-ZOO-V2.md) | P12 read-only registry/catalog projection, legacy migration audit, v2 fail-closed plan and safe-load boundary |
| [Virtual Cell Model Adapter SDK](runbooks/VIRTUALCELL-MODEL-ADAPTER-SDK.md) | P13 delta reference adapter, exact prepared-input/output provenance, conformance and fail-closed runtime interpretation |
| [E. coli K-12 Growth Contract](runbooks/VIRTUALCELL-ECOLI-K12-GROWTH-CONTRACT.md) | P14E local contract-only adapter, exact prepared binding, P14R authorization prerequisites and default-registry isolation |
| [S. cerevisiae Deletion-Fitness Contract](runbooks/VIRTUALCELL-YEAST-DELETION-FITNESS-CONTRACT.md) | P15E local contract-only adapter, exact S288C prepared binding, P15R authorization prerequisites and default-registry isolation |

The Chinese `项目说明*`, `项目交接报告`, and `学生使用指南` files describe the older PRAXIS-2 classroom/deployment system, including `.40/.53` service topology. They are not VirtualCell current-user entry points.

## Architecture and capability boundaries

| Document | Status |
|---|---|
| [Phase 10 Gate](../reports/phase10/PHASE10_GATE.md) | current claim boundary: real engine-level coverage remains four families; narrowed/unsupported items stay explicit |
| [Phase 10 Summary](../reports/phase10/PHASE10_SUMMARY.md) | generated test-count evidence for the Phase 10 package scope |
| [Phase 10 Cases](../reports/phase10/PHASE10_CASES.md) | 16-case routing/governance evidence |
| [Phase 10 Failures](../reports/phase10/PHASE10_FAILURES.md) | abstain and negative-case evidence |
| [Phase 10 Trace Audit](../reports/phase10/PHASE10_TRACE_AUDIT.md) | trace/provenance evidence |
| [Scientific Assets](status/SCIENTIFIC-ASSETS-2026-07-18.md) | packaged advisory assets versus source-only research data and non-distributable remote checkpoints |
| [v0.8 Architecture Baseline](ARCHITECTURE-v0.8-baseline.md) | frozen historical baseline at `7fc4aa5`; not the current test count or full Phase 10 architecture |
| [VirtualCellPack P5 ADR](ADR-0003-virtualcellpack-p5-multiomics-alignment.md) | H5MU paired/partially-paired semantics, strict model feature contracts, explicit alignment and three-layer validity boundary |
| [VirtualCellPack P6 ADR](ADR-0004-virtualcellpack-p6-capability-runtime.md) | strict model cards, four-factor compatibility, deterministic execution plans, plugin runtime and explicit legacy boundary |
| [VirtualCellPack P7 ADR](ADR-0005-virtualcellpack-p7-data-portal.md) | strict public data catalog, allowlisted hash-verified download, byte-preserving quarantine and three-layer non-escalation |
| [VirtualCellPack P8 ADR](ADR-0006-virtualcellpack-p8-golden-norman.md) | frozen Norman/K562 data/split/metric/bootstrap, three simple baselines, formal runtime path and scientific claim boundary |
| [VirtualCellPack P8 Product ADR](ADR-0007-virtualcellpack-p8-product-surfaces.md) | three tiny Packs, product index/CLI/API/UI, fail-closed acceptance and immutable historical execution identity |
| [VirtualCellPack P9 ADR](ADR-0008-virtualcellpack-p9-ood-validation.md) | eight-axis OOD contract, biological-group leakage boundary, external validation, selective metrics and baseline promotion gate |
| [Virtual Cell Model Zoo v2 ADR](ADR-0009-virtualcell-model-zoo-v2.md) | layered model/artifact/environment/adapter/evidence/policy identities, append-only lifecycle, legacy migration and exact v2 execution gate |
| [Virtual Cell Model Adapter SDK ADR](ADR-0010-virtualcell-model-adapter-sdk.md) | six versioned SDK contracts, delta-only default registry, strict output envelope and P0-compatible execution flow |
| [E. coli K-12 Growth Contract ADR](ADR-0011-virtualcell-ecoli-k12-growth-contract.md) | P14E exact scope, typed negative compatibility, prepared-bound projection and contract-only local registration |
| [S. cerevisiae Deletion-Fitness Contract ADR](ADR-0012-virtualcell-yeast-deletion-fitness-contract.md) | P15E exact S288C scope, typed negative compatibility, prepared-bound scalar fitness and local-only registration |
| [Community Readiness Checklist](COMMUNITY-READINESS-CHECKLIST.md) | P10 model-free CommunityPack gates, two tiny microbial Packs, fail-closed planning and explicitly missing experimental validation |
| [VirtualCellPack Capability Matrix](VIRTUALCELLPACK-CAPABILITY-MATRIX.md) | P0–P15E implementation/status matrix; separates registry, Pack, adapter/runtime compatibility, scientific evidence and product policy |
| [VirtualCellPack Multiomics Runbook](runbooks/VIRTUALCELLPACK-MULTIOMICS.md) | tiny RNA+protein fixture generation, hash binding, P5 tests and asset-update rules |
| [VirtualCellPack Capability Runtime Runbook](runbooks/VIRTUALCELLPACK-CAPABILITY-RUNTIME.md) | local model card/cache/Pack assembly, execution-plan audit and fail-closed reason handling |
| [VirtualCellPack Data Portal Runbook](runbooks/VIRTUALCELLPACK-DATA-PORTAL.md) | external public-file inventory, service configuration, upload quarantine and operator review boundary |
| [Golden Norman Runbook](runbooks/VIRTUALCELLPACK-GOLDEN-NORMAN.md) | exact source/Pack/baseline/evaluation hashes and fail-closed reproduction procedure |
| [VirtualCellPack Product Runbook](runbooks/VIRTUALCELLPACK-PRODUCT-SURFACES.md) | inspect/validate/register/list/compatibility/run operations, read-only API and status interpretation |
| [VirtualCellPack P9 OOD Runbook](runbooks/VIRTUALCELLPACK-P9-OOD-VALIDATION.md) | exact public input hashes, deterministic external replay, risk-coverage metrics and fail-closed scientific interpretation |
| [Virtual Cell Model Zoo v2 Runbook](runbooks/VIRTUALCELL-MODEL-ZOO-V2.md) | P12 migration, public projection, lifecycle, path-redaction and directed validation procedure |
| [Virtual Cell Model Adapter SDK Runbook](runbooks/VIRTUALCELL-MODEL-ADAPTER-SDK.md) | P13 registration allowlist, adapter conformance, prepared-input binding, output envelope and directed validation procedure |
| [E. coli K-12 Growth Contract Runbook](runbooks/VIRTUALCELL-ECOLI-K12-GROWTH-CONTRACT.md) | P14E local contract audit, fail-closed tests, P14R asset/run prerequisites and scientific non-claim boundary |
| [S. cerevisiae Deletion-Fitness Contract Runbook](runbooks/VIRTUALCELL-YEAST-DELETION-FITNESS-CONTRACT.md) | P15E local contract audit, fail-closed tests, P15R asset/run prerequisites and scientific non-claim boundary |
| [Provenance](../PROVENANCE.md) | repository derivation from PRAXIS-2 and bootstrap evidence |

## Release and version history

- The dated publication ledger and bootstrap-through-v1.5 map are in [Three-Way Sync State](status/SYNC-STATE.md); refresh requires a separately authorized remote window.
- [v0.1.0 Release Notes](RELEASE-v0.1.0.md) and [v0.6–v0.8 Delivery Report](STATUS-2026-07-03-v0.6-v0.8-delivery.md) are historical release records.
- Local `v0.9.0` through `v1.5.0` tags are local milestones on 2026-07-18; fresh D0 read-only checks found GitHub and `.53` still only through `v0.8.0`.
- GitHub candidate branch `codex/project-consolidation` is published at exact SHA `ee36d7948047f346f55a02d62ccaac84391e3c20`; retry run `29971566980` reached `4/5` and did not change GitHub `main` or release tags.
- [CHANGELOG](../CHANGELOG.md) records the unreleased 1.6.0 candidate and publication boundary without rewriting old tags.

## Active plans

| Plan | Status |
|---|---|
| [P12–P30 Sequential Master Prompt](PHASE12-30-SEQUENTIAL-MASTER-PROMPT.md) | superseded historical per-phase authorization prompt; do not use as current action authority |
| [P12–P30 Execution Plan](PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md) | active phase scopes and external-action boundaries |
| [P12–P30 Detailed Completion Checklist](PHASE12-30-DETAILED-COMPLETION-CHECKLIST.md) | active engineering/science/policy acceptance ledger |
| [Project consolidation, test, and improvement plan](superpowers/plans/2026-07-18-project-consolidation-test-improvement.md) | historical D1a orchestration; its old retry text is not current authorization |
| [Consolidation goal prompt](superpowers/plans/2026-07-18-project-consolidation-goal-prompt.md) | historical restart/persistence protocol; not current action authority |
| [Full frontend E2E plan](superpowers/plans/2026-07-17-frontend-full-e2e-test-plan.md) | historical C3 design; S10 remains an explicit external gate in its own scope |

Other files under [superpowers/plans](superpowers/plans/) and top-level `PLAN-*` documents are dated implementation history unless the current P12–P30 route explicitly references them.

## Test and quality reports

| Report | Scope |
|---|---|
| [P15E Completion Report](../reports/phase15e/PHASE15E_COMPLETION.md) | exact engineering closure, 98 contract tests, safe directed/legacy validation, reproducible wheel and P15R/P15B non-runs |
| [P14E Completion Report](../reports/phase14e/PHASE14E_COMPLETION.md) | exact engineering closure, directed and legacy validation, reproducible full wheel, P14R/P14B non-runs and P15E eligibility |
| [Post-consolidation Quality Baseline](../reports/quality/BASELINE-2026-07-18.md) | frozen B0–B4 environment, static, core, frontend, wheel/CLI, legacy, and remote-boundary evidence |
| [Phase D1a CI Report](status/PHASE-D1A-CI-2026-07-22.md) | actual old-SHA GitHub run, job-by-job failure boundary, lock/frontend remediation, honest QEMU limitation, and retry gate |
| [Phase D1a CI Retry Report](status/PHASE-D1A-CI-RETRY-2026-07-23.md) | exact attempt-2 run, four passing jobs, authoritative Linux failure, process-group repair, and next CAS boundary |
| [Phase C5 Scientific Gate](status/PHASE-C5-GATE-2026-07-18.md) | frozen local C5 gate: Python 3.13 core 965, Gate A adapter seam, honest 2-test remote pending, asset/claim classification |
| [Phase C4 Completion Gate](status/PHASE-C4-GATE-2026-07-18.md) | frozen C4 gate: Python 3.13 core 957, Playwright 56+1, reproducible full wheel, and Linux-container smoke |
| [Phase C3 Completion Gate](status/PHASE-C3-GATE-2026-07-18.md) | frozen C3 gate: core 947, Playwright 54+1, theme acceptance, mutation evidence, and then-remaining C4/C5 ownership |
| [Testing Guide](TESTING.md) | current P15E local commands and counts; preserves prior exact-SHA and historical CI/Linux evidence plus remote scientific-validation boundaries |
| [Phase 10 Gate](../reports/phase10/PHASE10_GATE.md) | capability gate plus `.53` evidence and remaining remote backlog |
| [Phase 10 Summary](../reports/phase10/PHASE10_SUMMARY.md) | `952 tests = 912 passed + 40 skipped` for the non-LLM package scope; 9 LLM tests are deselected in the `912/40/9` reporting style |
| [Phase 10 UI E2E](../reports/phase10/PHASE10_UI_E2E.md) | three structural Playwright specs; explicitly excludes CSS/pixel and deep abstain assertions |
| [Phase 10 Cases](../reports/phase10/PHASE10_CASES.md), [Failures](../reports/phase10/PHASE10_FAILURES.md), [Trace Audit](../reports/phase10/PHASE10_TRACE_AUDIT.md) | supporting case, negative, and trace evidence |

The post-consolidation baseline under `reports/quality/` is current as of `PHASE_B_COMPLETE`. Pre-migration anchors remain historical and must not override it.

## Paper and research evidence

| Document area | Status |
|---|---|
| [NMI manuscript draft](paper/v0.8-NMI/manuscript.md) | latest manuscript draft; not released, subordinate to Phase 10, and has five C5-recorded author-review gaps before submission |
| [NMI review round 1](paper/v0.8-NMI/review-round1.md) | historical adversarial review of that draft |
| [Consolidated v0.1–v0.5 results](paper/v0.4/RESULTS-CONSOLIDATED.md) | historical evidence synthesis with dated test numbers |
| [Findings](findings/) | versioned experimental evidence, JSON/JSONL ledgers, and scientific anchors; preserve |
| [Paper tree](paper/) | drafts, plans, figures, and literature evidence; no draft status implies publication |

## Historical material

- [docs/history](history/) contains inherited PRAXIS-2 status, deployment, and handoff records.
- Top-level `HANDOFF-*`, old `STATUS-*`, `PROJECT-SUMMARY.md`, `ANALYSIS-SUMMARY.md`, and old `PLAN-*` files retain provenance but do not override current state.
- `docs/superpowers/HANDOFF-*` and `docs/superpowers/plans/UPGRADE-PROGRESS.md` are historical agent-workflow records. Old `push_authorized` text is not authorization for this consolidation.
- `_audit/`, `reports/phase10/`, and `docs/findings/` are versioned evidence, not generated-cache cleanup targets.

## Known stale entry points

| Location | Stale fact | Planned correction |
|---|---|---|
| `docs/PROJECT-SUMMARY.md` / `docs/ANALYSIS-SUMMARY.md` | old HEADs and `105+25` / `203+25` test counts | keep historical; do not patch numbers in place as if the old reports were rerun |
| `docs/ARCHITECTURE-v0.8-baseline.md` | frozen `277+25` baseline | keep frozen and label through this index |

Do not bulk-move or rewrite old documents during consolidation. Update this index when a document's authority or lifecycle changes.

Repository storage maintenance must follow [External-Disk Git Maintenance](runbooks/EXTERNAL-DISK-GIT-MAINTENANCE.md); its optional cleanup section always requires separate approval.
