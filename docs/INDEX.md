# PRAXIS-VirtualCell Documentation Index

> Audited: 2026-07-23
>
> Status: `CURRENT_DOCUMENT_MAP`

This is the navigation authority for the repository. It does not make every linked document current: each section explicitly distinguishes live truth, frozen evidence, active plans, drafts, and history.

## Truth precedence

When documents disagree, use this order:

1. [Project State](status/PROJECT-STATE-2026-07-18.md) for the active path, Git checkpoint, protected worktree, and phase gate.
2. [Three-Way Sync State](status/SYNC-STATE.md) for local/GitHub/`.53` SHAs, tag publication, dirty state, and synchronization authorization.
3. [Phase 10 Gate](../reports/phase10/PHASE10_GATE.md) for scientific capability and claim boundaries.
4. [README](../README.md), installation, user, and examples documents for product use, subject to the stale-item register below.
5. Dated plans, handoffs, findings, papers, and release notes as historical evidence for their stated commit/date only.

Plans describe intended work. A task is not complete merely because a plan says it should happen; only checked gates plus recorded verification count as completion.

## Current state

| Document | Authority |
|---|---|
| [Project State](status/PROJECT-STATE-2026-07-18.md) | APFS migration, current branch/ref facts, protected assets, phase restart point |
| [Phase A Completion Gate](status/PHASE-A-GATE-2026-07-18.md) | proof that migration/organization protections passed before baseline testing |
| [Post-consolidation Quality Baseline](../reports/quality/BASELINE-2026-07-18.md) | Phase B commands, exact results, failure ownership, and `PHASE_B_COMPLETE` gate |
| [Phase D0 Sync Proposal](status/PHASE-D0-SYNC-PROPOSAL-2026-07-18.md) | frozen pre-publication ledger, exact D1/D2 protocol, protected exceptions, and rollback plan; not the current live sync ledger |
| [Phase D1a CI Report](status/PHASE-D1A-CI-2026-07-22.md) | first exact candidate-branch publication, run `29894971142`, `1/5` diagnosis, local remediation evidence, and retry authorization boundary |
| [Phase D1a CI Retry Report](status/PHASE-D1A-CI-RETRY-2026-07-23.md) | exact `6086… → ee36…` retry, run `29971566980`, `4/5` result, Linux process-group diagnosis, and locally verified repair |
| [Phase C5 Scientific Gate](status/PHASE-C5-GATE-2026-07-18.md) | current local scientific classification, Gate A seam evidence, explicit remote pending, and D0 handoff |
| [Scientific Assets](status/SCIENTIFIC-ASSETS-2026-07-18.md) | wheel/container/source/private asset matrix, provenance, licence gaps, and permitted claims |
| [Phase C4 Completion Gate](status/PHASE-C4-GATE-2026-07-18.md) | frozen local dependency/bundle/wheel/API/Linux-container evidence and `C4_COMPLETE_LOCAL` boundary |
| [Phase C3 Completion Gate](status/PHASE-C3-GATE-2026-07-18.md) | frozen local theme/full-E2E/request-boundary evidence, exact C3 counts, honest S10 skip, and `C3_COMPLETE_LOCAL` boundary |
| [Three-Way Sync State](status/SYNC-STATE.md) | three-way ledger with explicit freshness labels and the Phase D synchronization protocol |
| [Worktree Asset Classification](status/WORKTREE-ASSETS.md) | accepted theme disposition plus continuing protection of `.claude/`, Playwright MCP output, screenshot, and stash |
| [Versioning Contract](VERSIONING.md) | implemented product/protocol/schema/artifact version boundaries and release invariants |
| [Testing Guide](TESTING.md) | current local commands, exact scopes, external gates, and GitHub-CI evidence boundary |
| [VirtualCellPack P5 → P6 Handoff](HANDOFF-VIRTUALCELLPACK-P5-TO-P6.md) | local P5 implementation, exact strict-lock evidence, limitations and next exact-SHA authorization gate |
| [VirtualCellPack P6 → P7 Handoff](HANDOFF-VIRTUALCELLPACK-P6-TO-P7.md) | local P6 capability-runtime implementation, exact tests, limitations and next exact-SHA authorization gate |
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
| [VirtualCellPack Capability Matrix](VIRTUALCELLPACK-CAPABILITY-MATRIX.md) | P0–P6 implementation/status matrix; separates `pack_valid`, `model_compatible`, executable and `scientifically_validated` |
| [VirtualCellPack Multiomics Runbook](runbooks/VIRTUALCELLPACK-MULTIOMICS.md) | tiny RNA+protein fixture generation, hash binding, P5 tests and asset-update rules |
| [VirtualCellPack Capability Runtime Runbook](runbooks/VIRTUALCELLPACK-CAPABILITY-RUNTIME.md) | local model card/cache/Pack assembly, execution-plan audit and fail-closed reason handling |
| [Provenance](../PROVENANCE.md) | repository derivation from PRAXIS-2 and bootstrap evidence |

## Release and version history

- The current publication ledger and bootstrap-through-v1.5 map are in [Three-Way Sync State](status/SYNC-STATE.md).
- [v0.1.0 Release Notes](RELEASE-v0.1.0.md) and [v0.6–v0.8 Delivery Report](STATUS-2026-07-03-v0.6-v0.8-delivery.md) are historical release records.
- Local `v0.9.0` through `v1.5.0` tags are local milestones on 2026-07-18; fresh D0 read-only checks found GitHub and `.53` still only through `v0.8.0`.
- GitHub candidate branch `codex/project-consolidation` is published at exact SHA `ee36d7948047f346f55a02d62ccaac84391e3c20`; retry run `29971566980` reached `4/5` and did not change GitHub `main` or release tags.
- [CHANGELOG](../CHANGELOG.md) records the unreleased 1.6.0 candidate and publication boundary without rewriting old tags.

## Active plans

| Plan | Status |
|---|---|
| [Project consolidation, test, and improvement plan](superpowers/plans/2026-07-18-project-consolidation-test-improvement.md) | the only active orchestration plan; D1a attempt 2 reached `4/5`, the final local repair is verified, and another exact-SHA retry remains approval-gated |
| [Consolidation goal prompt](superpowers/plans/2026-07-18-project-consolidation-goal-prompt.md) | restart/persistence protocol for final candidate binding and the D1a retry-2 hard gate |
| [Full frontend E2E plan](superpowers/plans/2026-07-17-frontend-full-e2e-test-plan.md) | subordinate C3 design implemented locally for S1–S9/S11–S13; S10 real-LLM gate remains pending, and active-plan orchestration overrides its historical mechanics |

Other files under [superpowers/plans](superpowers/plans/) and top-level `PLAN-*` documents are dated implementation history unless the active plan explicitly references them.

## Test and quality reports

| Report | Scope |
|---|---|
| [Post-consolidation Quality Baseline](../reports/quality/BASELINE-2026-07-18.md) | current B0–B4 environment, static, core, frontend, wheel/CLI, legacy, and remote-boundary evidence |
| [Phase D1a CI Report](status/PHASE-D1A-CI-2026-07-22.md) | actual old-SHA GitHub run, job-by-job failure boundary, lock/frontend remediation, honest QEMU limitation, and retry gate |
| [Phase D1a CI Retry Report](status/PHASE-D1A-CI-RETRY-2026-07-23.md) | exact attempt-2 run, four passing jobs, authoritative Linux failure, process-group repair, and next CAS boundary |
| [Phase C5 Scientific Gate](status/PHASE-C5-GATE-2026-07-18.md) | current local C5 gate: Python 3.13 core 965, Gate A adapter seam, honest 2-test remote pending, asset/claim classification |
| [Phase C4 Completion Gate](status/PHASE-C4-GATE-2026-07-18.md) | frozen C4 gate: Python 3.13 core 957, Playwright 56+1, reproducible full wheel, and Linux-container smoke |
| [Phase C3 Completion Gate](status/PHASE-C3-GATE-2026-07-18.md) | frozen C3 gate: core 947, Playwright 54+1, theme acceptance, mutation evidence, and then-remaining C4/C5 ownership |
| [Testing Guide](TESTING.md) | current local commands and counts; distinguishes both exact-head GitHub runs, repaired local Linux evidence, and remote scientific validation |
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
