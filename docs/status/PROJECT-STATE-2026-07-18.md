# PRAXIS-VirtualCell Project State — 2026-07-18

> Captured: 2026-07-18 13:33 CST (+0800)
>
> Overall status: `PHASE_A_COMPLETE — Phase B0 next`
>
> Migration gate: `PHASE_A0_COMPLETE`

This file is the restart authority for the consolidation goal. It records observed facts, not desired end state. Re-run the listed read-only checks before relying on any value that may change.

## Canonical locations

| Role | Location | Rule |
|---|---|---|
| Active local development truth | `/Users/mzy/Projects/PRAXIS-virtualcell` | All Phase A–D work happens here |
| Read-only source archive | `/Volumes/T7/PRAXIS-virtualcell` | Do not stage, clean, reset, stash, gc, prune, or edit |
| Recovery material | `/Users/mzy/Projects/PRAXIS-virtualcell-recovery-20260718` | Preserve through final synchronization and release verification |
| Published truth | GitHub `NHNQNHNQ/PRAXIS-Virtualcell` | Live-observed at `main=7fc4aa5`, tags through `v0.8.0` |
| Deployment/validation mirror | `.53` | Live-observed detached at `b9abdbd`; details in `SYNC-STATE.md` |

The source volume is ExFAT and was 93% full. The active clone and recovery directory are on APFS with approximately 46 GiB available at migration time.

## Git state

| Item | Observed value |
|---|---|
| Audit anchor / current branch base | `24475f2eb14c27c7cfbb82b016b881e88e98b17c` |
| Active branch | `codex/project-consolidation`, created locally at `24475f2`; intentionally no upstream yet; Phase A evidence parent `a55ee8b` |
| Preserved former working branch | `feat/v0.9-phase0-module-core=24475f2` |
| Local `main` | `176019ebd9c198f93a5a645f1ecefce9baaf0522` |
| Annotated tag `v1.5.0` | tag object `df04e74`; peeled commit `176019e` |
| Live-fetched `origin/main` tracking ref | `7fc4aa5b3bd03871358385f1d467a515be15aafe` |
| Live-fetched `origin/feat/v0.9-phase0-module-core` | `b9abdbdf733406853c4a338b29b705ca801d7ac7` |
| `refs/stash` | `77cb06d392a8a547e37c390d86769de23437cc83` |
| GitHub origin URL | `git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git` |
| Recovery remote URL | `/Users/mzy/Projects/PRAXIS-virtualcell-recovery-20260718/praxis-all.bundle` |

Observed graph relationships at local checkpoint `620b4d5` after live fetch:

```text
HEAD...main                                      3 left / 0 right
HEAD...origin/feat/v0.9-phase0-module-core      84 left / 1 right
main...origin/main                              342 left / 0 right
```

The two `origin/*` values now match a 2026-07-18 HTTPS `ls-remote` and an HTTPS-backed `fetch --prune --tags`. The persisted origin URL remains SSH. No pull, merge, rebase, push, PR, tag, or remote write has occurred.

The `.53` host was live-checked read-only at 2026-07-18 13:12 CST. It is detached at `b9abdbd`, has `main=7fc4aa5`, tags through `v0.8.0`, and one untracked 32,504-byte `vc_api.log`. It also preserves `.53`-only branch `remote-gears-l4-95dc764=95dc764`. No process or environment check was performed. See `docs/status/SYNC-STATE.md`.

## Protected worktree state

The APFS clone intentionally reproduces the source's dirty worktree:

| Asset | State | Protection |
|---|---|---|
| `praxis_vc_react/src/styles/base.css` | modified | do not modify or stage before C3 |
| `praxis_vc_react/src/styles/fonts.css` | modified | do not modify or stage before C3 |
| `praxis_vc_react/src/styles/themes.css` | modified | do not modify or stage before C3 |
| `praxis_vc_react/src/styles/tokens.css` | modified | do not modify or stage before C3 |
| `.claude/launch.json` | untracked | classify in A2; do not delete |
| `.playwright-mcp/` (4 files) | untracked | classify in A2; do not delete |
| `string.jpeg` | untracked | classify in A2; do not delete |
| `docs/superpowers/plans/2026-07-18-*.md` (2 files) | untracked task artifacts | commit only with consolidation documentation |

The exact four-file CSS diff matches the recovery patch at SHA-256 `2c300a185c97f3821edc2e08d91a4d52f6ea1e00bcf52a55f1a1121173eaff7e`.

`refs/stash^3` contains only `docs/PRAXIS-生物科学智能体-总介绍.md`. The stash commit has the same `77cb06d` OID in source, bundle, and clone. It was not popped or dropped. Its exported copy is in the recovery directory and has SHA-256 `6dacab11a753fda58b6c2b926a098648d4becf18dcef5b7cc148909431360d20`.

The ignored root `.env` existed in the source archive and was 252 bytes. Its contents were not read, displayed, or copied. No secret is included in the recovery manifest.

The recovery audit also found ignored reproducibility data and Phase 10 evidence that Git bundle could not carry. The following non-secret files were copied from T7 into the same ignored paths in the APFS clone and verified by source/target SHA-256: three `.h5ad` files (1,499,342,078 bytes total), `data/paul15/paul15.h5`, both LINCS L1000 up/down signature files, two JUnit XML files, and `reports/phase10/trace_bundle.json`. Exact hashes are in the recovery manifest. Rebuildable `.venv`, `node_modules`, caches, `dist`, `test-results`, `runs`, `egg-info`, and `__pycache__` were not copied.

Every protected CSS/untracked/stash item now has an explicit four-way disposition in `docs/status/WORKTREE-ASSETS.md`. No disposition was implemented destructively; the original dirty/untracked/stash state remains intact.

## Migration integrity evidence

| Check | Result |
|---|---|
| `git bundle verify praxis-all.bundle` | PASS; complete history, 19 named refs plus `HEAD` |
| source vs clone protected ref object IDs | PASS; all 19 matched before creating the planned local branch |
| `git rev-list --objects --all --missing=print` | PASS; 0 missing |
| `git fsck --full` in APFS clone | PASS; exit 0, no corrupt/missing diagnostics |
| `.git` AppleDouble count in APFS clone | 0 |
| AppleDouble count in ExFAT archive | 1,039 overall; 324 under `.git` |
| CSS patch/source/clone SHA-256 | PASS; all `2c300a...aff7e` |
| stash ref and third-parent file | PASS; exact ref restored and file separately exported |
| GitHub origin URL | PASS; explicitly set to the source-recorded SSH URL |

Recovery artifact SHA-256 values:

```text
6656d81e69032a502b49a099409289473b72ad3ea4c8ba5a740a6fdb15bff106  praxis-all.bundle
2c300a185c97f3821edc2e08d91a4d52f6ea1e00bcf52a55f1a1121173eaff7e  wip-styles.patch
```

The complete asset inventory and checksums are in `/Users/mzy/Projects/PRAXIS-virtualcell-recovery-20260718/RECOVERY-MANIFEST.md`.

## Pre-migration quality anchors

These are historical audit anchors and must be re-run only after Phase A5:

| Layer | Last observed result | Interpretation |
|---|---|---|
| VirtualCell core pytest | `912 passed / 40 skipped / 9 deselected / 0 failed` | authoritative core scope: `praxis_virtualcell/tests -m "not llm"` |
| Legacy root pytest | `1136 passed / 163 skipped / 1 failed` | separate legacy scope; failure was `.53:7788/api/info` timeout |
| Frontend | typecheck/lint/build PASS; Playwright `3 passed` | pre-migration evidence only |
| Ruff | 13 errors | measurement to reproduce in Phase B, not fix in Phase A |
| Frontend bundle | about 632 KB main chunk with warning | optimization candidate, not an A-phase task |
| Version surfaces | tag `v1.5.0`; Python/frontend `0.0.0`; API `0.6`; UI runtime `v0.3` | needs versioning design before changes |

Scientific claims remain bounded by `reports/phase10/PHASE10_GATE.md`: real engine-level coverage is four families, and narrowed/unsupported items may not be upgraded without new reproducible evidence.

## Phase A completion

`PHASE_A_COMPLETE`

- Gate report: `docs/status/PHASE-A-GATE-2026-07-18.md`
- Evidence parent: `a55ee8be20e2383a541dc2dd87277dd3cb855e4f`
- Completion commit: `PENDING_PHASE_A_GATE_COMMIT`
- Result: all APFS, ref, WIP, asset, link, change-boundary, and three-way-ledger checks passed.
- External writes: none.

## Next authorized work

Continue Phase B0 in this APFS clone:

1. Create a fresh `.venv` on APFS and install the declared development/API/mechanistic dependencies; do not reuse the T7 environment.
2. Recreate frontend dependencies with `npm ci`; do not copy the T7 `node_modules`.
3. Record tool/dependency versions, `pip check`, `npm audit`, Ruff output, and connectivity-only fsck results without fixing anything.
4. Keep all B0 measurements separate by command, exit code, and scope.

No Phase B baseline test may start before `PHASE_A_COMPLETE` is written at A5. No external synchronization is authorized before the Phase D approval gate.
