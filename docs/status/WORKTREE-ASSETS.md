# PRAXIS-VirtualCell Worktree Asset Classification

> Classified: 2026-07-18
>
> Status: `CLASSIFIED_NO_DELETION`

This ledger assigns one of the plan's four dispositions to every protected worktree/stash asset. Classification is not permission to delete, move, restore, publish, or stage a file.

## Classification table

| Asset | Observed evidence | Classification | Next allowed action |
|---|---|---|---|
| Four theme CSS files | 51 additions / 44 deletions across `base.css`, `fonts.css`, `themes.css`, and `tokens.css`; exact binary patch SHA-256 `2c300a...aff7e`; prior structural frontend checks passed, but no visual acceptance is recorded | `pending-user-decision` | keep as protected WIP; perform C3 visual review, then either make one theme-only commit or continue the WIP |
| `.claude/launch.json` | 12-line JSON config that launches `npm --prefix praxis_vc_react run dev` on port 5173; no credential or host-specific secret | `pending-user-decision` | recommend `keep-and-commit` as a team launch profile only after confirming `.claude/` is intended to be shared; do not stage it during Phase A |
| `.playwright-mcp/` | one 3,940-byte console log, two identical 24,864-byte page snapshots, and one empty snapshot; tool-generated names and content shape | `archive-with-provenance` | checksummed copy is in the APFS recovery directory; keep the live files untouched, propose `.playwright-mcp/` ignore rule in A4, and delete only with later approval |
| `string.jpeg` | 198,758-byte, 1200×780 RGB JPEG; visual inspection shows STRING v12 protein mapping selections for human `TP53` and `EGFR`; file mtime 2026-07-10; SHA-256 `ff3739...b0fd` | `archive-with-provenance` | retain recovery copy and live original; do not commit until source URL, capture purpose, and reuse/licensing note are recorded; if accepted, rename to a semantic `docs/assets/evidence/` path |
| `stash@{0}` overview document | `refs/stash=77cb06d`; sole third-parent file is `docs/PRAXIS-生物科学智能体-总介绍.md`; exported SHA-256 `6dacab...d20`; document labels VirtualCell v1.4 and includes broad platform/remote-tool claims | `archive-with-provenance` | preserve stash and exported recovery copy; if resumed, create a separate draft branch and audit every capability claim against `PHASE10_GATE.md`; never publish the stashed text unchanged |

## CSS theme boundary

The four CSS files are one indivisible theme workstream for this consolidation. They are not part of repository migration, synchronization, documentation architecture, CI cleanup, version alignment, or baseline measurement commits.

The last known frontend structural evidence was typecheck/lint/build success and three passing Playwright specs before migration. That does not constitute pixel, contrast, responsive, font-loading, or light/dark visual acceptance. C3 must perform visual review before the theme can become `keep-and-commit`.

## Backup versus authority

- `/Users/mzy/Projects/PRAXIS-virtualcell` is the active development working copy.
- `/Volumes/T7/PRAXIS-virtualcell` is a read-only source archive.
- `/Users/mzy/Projects/PRAXIS-virtualcell-recovery-20260718/untracked/` and `stash-untracked/` are checksum-addressed backups, not editable authority copies.
- Ignored scientific data mirrored into APFS use their in-repository ignored paths for local reproducibility; the recovery manifest records exact source/target hashes.

No asset has been deleted, renamed, popped, dropped, overwritten, ignored, or staged as a result of this classification.
