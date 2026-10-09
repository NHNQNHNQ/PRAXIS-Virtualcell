# PRAXIS-VirtualCell Worktree Asset Classification

> Classified: 2026-07-18
>
> Status: `CSS_ACCEPTED — OTHER_ASSETS_PROTECTED`

This ledger assigns one of the plan's four dispositions to every protected worktree/stash asset. The theme row records its completed C3 implementation; all other classifications are not permission to delete, move, restore, publish, or stage a file.

## Classification table

| Asset | Observed evidence | Classification | Next allowed action |
|---|---|---|---|
| Four theme CSS files | Original recovery patch SHA-256 `2c300a...aff7e` remains archived; C3 visually reviewed and refined the theme, then committed the accepted four files with the wider theme system in `92ab4ee`; current worktree diff is empty | `keep-and-commit` — implemented | preserve the recovery patch as provenance and the tracked theme as authority; do not claim the original patch was committed byte-for-byte |
| `.claude/launch.json` | 11-line JSON config that launches `npm --prefix praxis_vc_react run dev` on port 5173; no credential or host-specific secret | `pending-user-decision` | recommend `keep-and-commit` only after confirming `.claude/` is intended to be shared; do not stage without that decision |
| `.playwright-mcp/` | one 3,940-byte console log, two identical 24,864-byte page snapshots, and one empty snapshot; tool-generated names and content shape | `archive-with-provenance` | checksummed copy is in the APFS recovery directory; live files remain present and are now ignored by `.gitignore`; delete only with later approval |
| `string.jpeg` | 198,758-byte, 1200×780 RGB JPEG; visual inspection shows STRING v12 protein mapping selections for human `TP53` and `EGFR`; file mtime 2026-07-10; SHA-256 `ff3739...b0fd` | `archive-with-provenance` | retain recovery copy and live original; do not commit until source URL, capture purpose, and reuse/licensing note are recorded; if accepted, rename to a semantic `docs/assets/evidence/` path |
| `stash@{0}` overview document | `refs/stash=77cb06d`; sole third-parent file is `docs/PRAXIS-生物科学智能体-总介绍.md`; exported SHA-256 `6dacab...d20`; document labels VirtualCell v1.4 and includes broad platform/remote-tool claims | `archive-with-provenance` | preserve stash and exported recovery copy; if resumed, create a separate draft branch and audit every capability claim against `PHASE10_GATE.md`; never publish the stashed text unchanged |

## CSS theme boundary

The four CSS files were one indivisible theme workstream for this consolidation. They were not mixed into repository migration, CI cleanup, or baseline measurement commits; the accepted theme landed in the dedicated `92ab4ee` commit after C3 review.

C3 completed light/dark visual and accessibility review, removed the unused Newsreader dependency, and verified actual theme state plus responsive workflow reachability. The frozen C3 theme-acceptance evidence is typecheck/lint/build/audit PASS and 55 Playwright cases with 54 passed plus the honest S10 external-gate skip. C4's broader current suite is 57 cases with 56 passed plus the same honest skip; see the [C4 gate](PHASE-C4-GATE-2026-07-18.md) and [testing guide](../TESTING.md). Geometry/pixel equivalence is not claimed beyond the documented narrow Results-toolbar regression.

## Backup versus authority

- `/Users/mzy/Projects/PRAXIS-virtualcell` is the active development working copy.
- `/Volumes/T7/PRAXIS-virtualcell` is a read-only source archive.
- `/Users/mzy/Projects/PRAXIS-virtualcell-recovery-20260718/untracked/` and `stash-untracked/` are checksum-addressed backups, not editable authority copies.
- Ignored scientific data mirrored into APFS use their in-repository ignored paths for local reproducibility; the recovery manifest records exact source/target hashes.

Only the approved theme disposition has been implemented. `.claude/launch.json`, `string.jpeg`, `.playwright-mcp/`, stash, recovery copies, and the T7 archive have not been deleted, renamed, popped, dropped, overwritten, staged, or committed. The working tree has no CSS diff and no staged files; protected `.claude/` and `string.jpeg` remain untracked.
