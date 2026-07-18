# PRAXIS-VirtualCell Three-Way Sync State

> Local observed: 2026-07-18 19:42 CST (+0800); GitHub and `.53` refs last observed 2026-07-18 13:33 CST and not revalidated by C3/C4
>
> Status: `KNOWN_DIVERGENCE`
>
> External writes: **none** — no push, merge, tag, checkout, pull, deployment, or process action was performed.

## Roles and invariant

| Endpoint | Role | Authority rule |
|---|---|---|
| GitHub `NHNQNHNQ/PRAXIS-Virtualcell` | published truth | A commit is not published until it exists on the approved GitHub branch/tag |
| APFS clone `/Users/mzy/Projects/PRAXIS-virtualcell` | development truth | all code, tests, and release preparation happen here |
| `.53:/home/zkyd/data1/mzy/PRAXIS-virtualcell` | deployment/validation mirror | never develop directly here; only deploy an approved GitHub SHA |

Release synchronization invariant:

```text
local main == GitHub origin/main == .53 deployed SHA
```

Feature branches may be intentionally ahead locally or on GitHub, but every exception must be recorded here. Local tags are not published tags until `git ls-remote --tags origin` confirms them.

## Observed ledger

| Field | APFS local | GitHub | `.53` mirror |
|---|---|---|---|
| Observation method | local Git commands re-run through C4 gate | Phase A HTTPS `ls-remote`, then HTTPS-backed `fetch --prune --tags`; last observed, not re-read by C3/C4 | Phase A batch-mode read-only SSH; last observed, not re-read by C3/C4 |
| Repository | `/Users/mzy/Projects/PRAXIS-virtualcell` | `https://github.com/NHNQNHNQ/PRAXIS-Virtualcell` | `/home/zkyd/data1/mzy/PRAXIS-virtualcell` |
| Configured origin | `git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git` | same repository | `git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git` |
| Checked-out state | `codex/project-consolidation`; fixed C4 implementation evidence head `8ce42fe`; gate docs follow it; intentionally no upstream; local `1.6.0` candidate | no observed `codex/project-consolidation` branch | detached HEAD at `b9abdbd` |
| `main` | `176019e` | `7fc4aa5` | `7fc4aa5` |
| former feature branch | `24475f2` | `b9abdbd` | local branch `b9abdbd` |
| highest release tag present | local `v1.5.0 → 176019e` | `v0.8.0 → 7fc4aa5` | `v0.8.0 → 7fc4aa5` |
| worktree | C4 implementation committed through `8ce42fe`; protected `.claude/` and `string.jpeg` untracked; ignored `.playwright-mcp/` present | not applicable | last observed dirty: untracked `vc_api.log` only |
| extra refs | recovery refs and stash preserved | none beyond observed `main`/feature/tags | `remote-gears-l4-95dc764 → 95dc764` |

The `.53` log was inspected by metadata only: `vc_api.log`, 32,504 bytes, mtime `2026-07-12 12:07:01 UTC`. Its contents were not read. No process state or environment secret was inspected.

GitHub and `.53` values in this ledger are **last-observed evidence**, not a claim that C3 or C4 revalidated them. C4 performed no push, PR, merge, tag, fetch-to-`.53`, checkout, deployment, process, or other external mutation.

## Divergence explanation

### Local C4 candidate versus published/deployed truth

At the fixed C4 implementation checkpoint `8ce42fe`, local `codex/project-consolidation` is 54 commits ahead of local `main`, 396 commits ahead of the last-observed `origin/main`, and has no upstream. Relative to the last-observed remote former feature branch it is `135 left / 1 right`; C4 gate documentation follows that checkpoint locally. The single sibling divergence remains the already documented `b9abdbd` versus local `4359602` case.

The local product metadata is `1.6.0`, but no `v1.6.0` tag exists and no candidate ref has been published. This is an intentionally local feature-branch state, not synchronization drift hidden as a release. C4 is complete locally while C5 remains incomplete, so the correct status is `KNOWN_DIVERGENCE`, not `READY_TO_SYNC` and not synchronized.

### Local `main` versus GitHub `main`

`GitHub main=7fc4aa5` is an ancestor of `local main=176019e`; the graph distance is `342 left / 0 right` from local `main...origin/main`. Therefore the unpublished local history is structurally fast-forwardable to GitHub, but it must not be pushed until Phase D approval and the Phase A–C gates pass.

Local milestones `v0.9.0` through `v1.5.0` do not exist on GitHub or `.53` and must be described as **local milestones**, not published releases.

### GitHub/`.53` `b9abdbd` versus local `4359602`

The two commits have the same parent `b43851e`, subject, author timestamp, and production-code blob. They are sibling commits rather than ancestors. Local `4359602` is a strict file-tree/semantic superset: it adds one seven-line test proving `GEARS_CKPT=""` remains fail-closed even when the GEARS import probe is true. `4359602` is an ancestor of the current local history; `b9abdbd` is not.

Decision: preserve `b9abdbd` as audit/deployment history, but do not merge it into the local line. In Phase D, move `.53` through a new deployment branch to the approved GitHub SHA, preserving the old branch/ref.

### `.53`-only experimental branch

`.53` has `remote-gears-l4-95dc764=95dc7648a035cf69c0453fe11787958548ec04a2`, subject `feat(v0.3 L4): GEARS donor-eval adapter — same-split per-cell ΔPearson`. It is not descended from `b9abdbd` and adds `praxis_virtualcell/benchmarks/gears_donor_eval.py`.

Decision: treat this as a remote experimental/evidence ref, not deployed truth. Do not delete, rename, force-update, or silently replace it. Phase D must preserve it before changing `.53` state.

## Release-history map

| Milestone | Commit | Date | Publication status on 2026-07-18 |
|---|---|---|---|
| bootstrap import | `fa5f048` | 2026-06-11 | present locally/GitHub/`.53` as `praxis2-import-b124d66` |
| `v0.1.0` | `7edb931` | 2026-06-14 | present locally/GitHub/`.53` |
| `v0.2.0` | `671871a` | 2026-06-27 | present locally/GitHub/`.53` |
| `v0.3.0-alpha.1` | `c784c89` | 2026-06-29 | present locally/GitHub/`.53` |
| `v0.8.0` | `7fc4aa5` | 2026-07-04 | current published GitHub `main` and `.53 main` |
| `v0.9.0` | `69a5cc7` | 2026-07-04 | local only |
| `v1.0.0` | `f470769` | 2026-07-04 | local only |
| `v1.1.0` | `3fcd5a1` | 2026-07-04 | local only |
| `v1.2.0` | `f07e0dc` | 2026-07-04 | local only |
| `v1.3.0` | `7b51b1a` | 2026-07-06 | local only |
| `v1.4.0` | `46a3d3b` | 2026-07-07 | local only |
| `v1.5.0` | `176019e` | 2026-07-17 | local only; current local `main` |

## Read-only evidence

- Direct SSH fetch initially failed during banner exchange at proxy address `198.18.0.23:22` with exit 128.
- HTTPS `git ls-remote --heads --tags` then succeeded with exit 0.
- A one-command `insteadOf` override fetched the same GitHub repository over HTTPS; the persisted `origin` URL remains the SSH URL.
- Restored `main` upstream metadata is `branch.main.remote=origin` and `branch.main.merge=refs/heads/main`.
- `.53` read-only SSH returned exit 0 during Phase A. Its HEAD, refs, remote, and dirty state were `OBSERVED` then and are now `LAST_OBSERVED` until the Phase D read-only recheck.

## Phase D synchronization protocol

No step below is authorized yet. Before external writes, present the exact target refs, rollback refs, dirty-file disposition, and approved SHA to the user.

1. Finish the remaining local C5 classification gate on `codex/project-consolidation`; C3/C4 are complete locally and protected non-theme assets remain explicit.
2. With approval, push only the named GitHub feature branch; run/observe CI.
3. With separate merge approval, fast-forward GitHub `main` to the reviewed commit. Do not force-push.
4. Fast-forward local `main` from the now-authoritative GitHub `main`; do not rewrite local milestone history.
5. On `.53`, first preserve detached `b9abdbd`, `remote-gears-l4-95dc764`, and decide how to retain `vc_api.log`; then fetch GitHub and fast-forward a new deployment branch to the exact approved SHA.
6. Validate the deployment without developing on `.53`.
7. Record proof from all three endpoints: local `main`, `git ls-remote origin main`, `.53` deployed SHA, tag object/peeled commit, worktree status, and validation command/results.

Until those steps are explicitly authorized and completed, the correct state is `KNOWN_DIVERGENCE`, not “synchronized”.
