# PRAXIS-VirtualCell Three-Way Sync State

> Local, GitHub, and `.53` re-observed read-only: 2026-07-18 20:38–20:43 CST (+0800)
>
> Status: `KNOWN_DIVERGENCE`
>
> External writes: **none** — no push, PR, merge, tag, `.53` fetch/checkout/pull, deployment, or process action was performed.

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
| Observation method | local Git commands plus final-candidate rehearsal, freshly re-run in D0 | fresh D0 HTTPS `git ls-remote --heads --tags`; no fetch or write | fresh D0 batch-mode read-only SSH with `GIT_OPTIONAL_LOCKS=0`; no fetch/checkout/process action |
| Repository | `/Users/mzy/Projects/PRAXIS-virtualcell` | `https://github.com/NHNQNHNQ/PRAXIS-Virtualcell` | `/home/zkyd/data1/mzy/PRAXIS-virtualcell` |
| Configured origin | `git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git` | same repository | `git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git` |
| Checked-out state | `codex/project-consolidation`; audit anchor `d39b4a9`; the first commit adding the D0 proposal is its immutable report anchor; the approval handoff separately binds the current clean 40-hex tip; intentionally no upstream; product `1.6.0` | no `codex/project-consolidation` branch | detached HEAD at `b9abdbd` |
| `main` | `176019e` | `7fc4aa5` | `7fc4aa5` |
| former feature branch | `24475f2` | `b9abdbd` | local branch `b9abdbd` |
| highest release tag present | local `v1.5.0 → 176019e` | `v0.8.0 → 7fc4aa5` | `v0.8.0 → 7fc4aa5` |
| worktree | tracked candidate line clean; protected `.claude/` and `string.jpeg` untracked; ignored `.playwright-mcp/` present | not applicable | fresh dirty observation: untracked `vc_api.log` only |
| extra refs | recovery refs and stash preserved | none beyond observed `main`/feature/tags | `remote-gears-l4-95dc764 → 95dc764` |

The `.53` log was freshly inspected by metadata only: `vc_api.log`, 32,504 bytes, mtime `2026-07-12 12:07:01 UTC`. Its contents were not read. No process state or environment secret was inspected.

GitHub and `.53` values above are fresh D0 observations. They happened to match Phase A's last-observed values exactly. C3–D0 performed no push, PR, merge, tag, fetch-to-`.53`, checkout, deployment, process, or other external mutation.

## Divergence explanation

### Local C5 candidate versus published/deployed truth

At D0 audit anchor `d39b4a9`, local `codex/project-consolidation` is 57 commits ahead of local `main`, 399 commits ahead of fresh GitHub `main`, and has no upstream. Relative to the fresh GitHub former feature branch it is `138 left / 1 right`. The D0 close commit that first adds [the synchronization proposal](PHASE-D0-SYNC-PROPOSAL-2026-07-18.md) adds one more local commit; the approval handoff must recompute and state its exact graph. The single sibling divergence remains the documented `b9abdbd` versus local `4359602` case.

The local product metadata is `1.6.0`, but no `v1.6.0` tag exists and no candidate ref has been published. This is an intentionally local feature-branch state, not synchronization drift hidden as a release. D0 has refreshed the external ledger and written the exact proposal, but the containing commit still requires post-commit artifact binding and user authorization. The state remains `KNOWN_DIVERGENCE`, never “synchronized”.

### Local `main` versus GitHub `main`

Fresh `GitHub main=7fc4aa5` is an ancestor of `local main=176019e`; the graph distance is `342 left / 0 right` from local `main...origin/main`. Local main is in turn an ancestor of the D0 candidate line. Therefore the unpublished local history is structurally fast-forwardable to GitHub, but it must not be pushed until the named D1 authorization.

Local milestones `v0.9.0` through `v1.5.0` do not exist on GitHub or `.53` and must be described as **local milestones**, not published releases.

### GitHub/`.53` `b9abdbd` versus local `4359602`

The two commits have the same parent `b43851e`, subject, author timestamp, and production-code blob. They are sibling commits rather than ancestors. Local `4359602` is a strict file-tree/semantic superset: it adds one seven-line test proving `GEARS_CKPT=""` remains fail-closed even when the GEARS import probe is true. `4359602` is an ancestor of the current local history; `b9abdbd` is not.

Decision: preserve `b9abdbd` as audit/deployment history, but do not merge it into the local line. In Phase D, move `.53` through a new deployment branch to the approved GitHub SHA, preserving the old branch/ref.

### `.53`-only experimental branch

`.53` has `remote-gears-l4-95dc764=95dc7648a035cf69c0453fe11787958548ec04a2`, subject `feat(v0.3 L4): GEARS donor-eval adapter — same-split per-cell ΔPearson`. It is not descended from `b9abdbd`, adds `praxis_virtualcell/benchmarks/gears_donor_eval.py`, and is `1 left / 343 right` relative to `b9abdbd` with merge base `2c9e73f`.

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

- D0 HTTPS `git ls-remote --heads --tags` returned exit 0 and exactly the same GitHub heads/tags as Phase A.
- D0 `.53` batch SSH returned exit 0 with `GIT_OPTIONAL_LOCKS=0`; path, origin, HEAD, branches, tags, dirty status, and log metadata matched Phase A.
- Local tracking refs were not fetched in D0; their `7fc4aa5`/`b9abdbd` values already matched the fresh HTTPS heads.
- The persisted local origin URL remains SSH; the recovery bundle remote remains unchanged.
- No process, service, secret, donor code, checkpoint, or Norman data was inspected in this D0 ledger refresh.

## Phase D synchronization protocol

No step below is authorized yet. The exact refs, rollback anchors, dirty-file disposition, CI order, `.53` branch path, and stop conditions are in [Phase D0 Three-End Audit and Synchronization Proposal](PHASE-D0-SYNC-PROPOSAL-2026-07-18.md).

1. Commit the D0 ledger/proposal locally, record its self-identifying report-anchor SHA, then bind the current clean branch-tip 40-hex to post-commit double-wheel/clean-install proof.
2. Present that exact SHA/digest and request D1a authorization for the named candidate branch only.
3. With D1a approval, push only that branch using the proposal's exact-ref compare-and-swap lease plus ancestry guard and `--no-follow-tags`, then observe all five CI jobs. The lease does not authorize a non-fast-forward update.
4. With separate D1b approval and green CI, use the same exact old-ref CAS plus ancestry guard to non-force fast-forward GitHub `main`; after exact tag-conflict checks, create/push only `v1.6.0` at the same SHA with implicit tag following disabled.
5. With separate D1c approval, fetch only the exact main ref and fast-forward local `main` from the now-authoritative GitHub `main`; D1b does not imply D1c.
6. With separate D2 approval, preserve detached `b9abdbd`, `remote-gears-l4-95dc764`, and `vc_api.log`; fetch GitHub and create `codex/deploy-v1.6.0` at the exact approved SHA.
7. Validate deployment/service/science only within their separately approved boundaries, then record three-end SHA/tag/worktree/CI/artifact/smoke proof.

Until those steps are explicitly authorized and completed, the correct state is `KNOWN_DIVERGENCE`, not “synchronized”.
