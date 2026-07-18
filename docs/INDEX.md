# PRAXIS-VirtualCell Documentation Index

> Audited: 2026-07-18
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
| [Three-Way Sync State](status/SYNC-STATE.md) | live local/GitHub/`.53` ledger and Phase D synchronization protocol |
| [Worktree Asset Classification](status/WORKTREE-ASSETS.md) | disposition of CSS WIP, `.claude/`, Playwright MCP output, screenshot, and stash |
| [Versioning Contract](VERSIONING.md) | version namespaces and the planned single-source release contract; design only until C2 |
| [Repository Layout](REPOSITORY-LAYOUT.md) | tracked-tree responsibilities and evidence-versus-generated policy |
| [Phase 10 Gate](../reports/phase10/PHASE10_GATE.md) | highest authority for met/narrowed/needs-new/unsupported scientific claims |

## User and operator documents

| Document | Status |
|---|---|
| [README](../README.md) | current product overview and quick start; developer test count is stale pending Phase B/C2 |
| [Installation Guide](INSTALL.md) | pip, Docker, and install-check workflow; wheel metadata must be revalidated in Phase B |
| [User Guide](USER-GUIDE.md) | CLI and product behavior; UI section still describes the older three-stage/three-tab interface |
| [Examples](EXAMPLES.md) | offline accept/caution/abstain examples and interpretation boundaries |
| [LLM Interface Guide](USAGE-llm-interface.md) | v0.6-era optional LLM/API interface; deterministic-runtime red lines remain applicable |

The Chinese `项目说明*`, `项目交接报告`, and `学生使用指南` files describe the older PRAXIS-2 classroom/deployment system, including `.40/.53` service topology. They are not VirtualCell current-user entry points.

## Architecture and capability boundaries

| Document | Status |
|---|---|
| [Phase 10 Gate](../reports/phase10/PHASE10_GATE.md) | current claim boundary: real engine-level coverage remains four families; narrowed/unsupported items stay explicit |
| [Phase 10 Summary](../reports/phase10/PHASE10_SUMMARY.md) | generated test-count evidence for the Phase 10 package scope |
| [Phase 10 Cases](../reports/phase10/PHASE10_CASES.md) | 16-case routing/governance evidence |
| [Phase 10 Failures](../reports/phase10/PHASE10_FAILURES.md) | abstain and negative-case evidence |
| [Phase 10 Trace Audit](../reports/phase10/PHASE10_TRACE_AUDIT.md) | trace/provenance evidence |
| [v0.8 Architecture Baseline](ARCHITECTURE-v0.8-baseline.md) | frozen historical baseline at `7fc4aa5`; not the current test count or full Phase 10 architecture |
| [Provenance](../PROVENANCE.md) | repository derivation from PRAXIS-2 and bootstrap evidence |

## Release and version history

- The current publication ledger and bootstrap-through-v1.5 map are in [Three-Way Sync State](status/SYNC-STATE.md).
- [v0.1.0 Release Notes](RELEASE-v0.1.0.md) and [v0.6–v0.8 Delivery Report](STATUS-2026-07-03-v0.6-v0.8-delivery.md) are historical release records.
- Local `v0.9.0` through `v1.5.0` tags are local milestones on 2026-07-18; GitHub and `.53` were live-observed only through `v0.8.0`.
- The repository does not yet have a current `CHANGELOG.md` or v1.5 release note. C2 must add a release-facing history without rewriting old tags.

## Active plans

| Plan | Status |
|---|---|
| [Project consolidation, test, and improvement plan](superpowers/plans/2026-07-18-project-consolidation-test-improvement.md) | the only active orchestration plan |
| [Consolidation goal prompt](superpowers/plans/2026-07-18-project-consolidation-goal-prompt.md) | restart/persistence protocol for the active plan |
| [Full frontend E2E plan](superpowers/plans/2026-07-17-frontend-full-e2e-test-plan.md) | subordinate C3 test design; its orchestration is overridden where the active plan says so |

Other files under [superpowers/plans](superpowers/plans/) and top-level `PLAN-*` documents are dated implementation history unless the active plan explicitly references them.

## Test and quality reports

| Report | Scope |
|---|---|
| [Post-consolidation Quality Baseline](../reports/quality/BASELINE-2026-07-18.md) | current B0–B4 environment, static, core, frontend, wheel/CLI, legacy, and remote-boundary evidence |
| [Phase 10 Gate](../reports/phase10/PHASE10_GATE.md) | capability gate plus `.53` evidence and remaining remote backlog |
| [Phase 10 Summary](../reports/phase10/PHASE10_SUMMARY.md) | `952 tests = 912 passed + 40 skipped` for the non-LLM package scope; 9 LLM tests are deselected in the `912/40/9` reporting style |
| [Phase 10 UI E2E](../reports/phase10/PHASE10_UI_E2E.md) | three structural Playwright specs; explicitly excludes CSS/pixel and deep abstain assertions |
| [Phase 10 Cases](../reports/phase10/PHASE10_CASES.md), [Failures](../reports/phase10/PHASE10_FAILURES.md), [Trace Audit](../reports/phase10/PHASE10_TRACE_AUDIT.md) | supporting case, negative, and trace evidence |

The post-consolidation baseline under `reports/quality/` is current as of `PHASE_B_COMPLETE`. Pre-migration anchors remain historical and must not override it.

## Paper and research evidence

| Document area | Status |
|---|---|
| [NMI manuscript draft](paper/v0.8-NMI/manuscript.md) | latest manuscript draft; not a released paper and all claims remain subordinate to the Phase 10 gate |
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
| `README.md` | says `277 passed` and “main is production”; live GitHub `main` is v0.8 while local `main` is v1.5 | refresh from Phase B numbers and current sync model in C2 |
| `praxis_vc_react/README.md` | untouched React/Vite template | replace with project-specific frontend setup/test guide in C2 |
| `docs/USER-GUIDE.md` | UI describes three stages/three tabs | update to five stages/six tabs after frontend baseline in C2/C3 |
| `docs/PROJECT-SUMMARY.md` / `docs/ANALYSIS-SUMMARY.md` | old HEADs and `105+25` / `203+25` test counts | keep historical; do not patch numbers in place as if the old reports were rerun |
| `docs/ARCHITECTURE-v0.8-baseline.md` | frozen `277+25` baseline | keep frozen and label through this index |
| API/UI version surfaces | Python/frontend `0.0.0`, OpenAPI `0.6`, runtime `v0.3` | implement the contract in [Versioning](VERSIONING.md) during C2 |

Do not bulk-move or rewrite old documents during consolidation. Update this index when a document's authority or lifecycle changes.

Repository storage maintenance must follow [External-Disk Git Maintenance](runbooks/EXTERNAL-DISK-GIT-MAINTENANCE.md); its optional cleanup section always requires separate approval.
