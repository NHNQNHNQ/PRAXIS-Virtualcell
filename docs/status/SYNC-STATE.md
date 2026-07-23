# PRAXIS-VirtualCell Three-Way Sync State

> Local/GitHub candidate state updated: 2026-07-23 09:55 CST (+0800); `.53` remains D0 last-observed at 2026-07-18 20:38–20:43 CST (+0800)
>
> Status: `KNOWN_DIVERGENCE — D1A_RETRY_1_CI_4_OF_5 — RETRY_2_AUTHORIZATION_PENDING`
>
> External writes: **two approved candidate-ref operations only** — creation at `6086e6995b1c3c01ec31075ce1164a0165cb8d43`, then strict fast-forward to `ee36d7948047f346f55a02d62ccaac84391e3c20`. No GitHub `main`/tag/PR, local `main`/tag, `.53` fetch/checkout/pull, deployment, or process action was performed.

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
| Observation method | local Git commands and D1a retry repair validation | 2026-07-23 GitHub API ref/run refresh after the approved exact-ref fast-forward | D0 batch-mode read-only SSH with `GIT_OPTIONAL_LOCKS=0`; **last observed**, not re-read in D1a |
| Repository | `/Users/mzy/Projects/PRAXIS-virtualcell` | `https://github.com/NHNQNHNQ/PRAXIS-Virtualcell` | `/home/zkyd/data1/mzy/PRAXIS-virtualcell` |
| Configured origin | `git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git` | same repository | `git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git` |
| Checked-out state | `codex/project-consolidation`; published attempt-2 SHA `ee36d79`; local process-group fix `6a81987`; final report-containing tip is named only by the next handoff; intentionally no upstream; product `1.6.0` | candidate branch `ee36d7948047f346f55a02d62ccaac84391e3c20`; CI run `29971566980` failed `4/5` | detached HEAD at `b9abdbd` (D0 last-observed) |
| `main` | `176019e` | `7fc4aa5` | `7fc4aa5` |
| former feature branch | `24475f2` | `b9abdbd` | local branch `b9abdbd` |
| highest release tag present | local `v1.5.0 → 176019e` | `v0.8.0 → 7fc4aa5` | `v0.8.0 → 7fc4aa5` |
| worktree | implementation was clean before the current ledger/report edits; final handoff requires tracked clean with only protected `.claude/` and `string.jpeg` untracked; ignored `.playwright-mcp/` present | not applicable | D0 last-observed dirty exception: untracked `vc_api.log` only |
| extra refs | recovery refs and stash preserved; `origin/codex/project-consolidation=ee36d79`; current branch still has no upstream | candidate branch `ee36d79`; no D1a tag | `remote-gears-l4-95dc764 → 95dc764` (D0 last-observed) |

The `.53` log was inspected by metadata only during D0: `vc_api.log`, 32,504 bytes, mtime `2026-07-12 12:07:01 UTC`. Its contents were not read. No D1a `.53` access occurred, so these values remain explicitly **last observed**, not a 2026-07-23 fresh claim.

The 2026-07-23 GitHub API refresh confirms candidate `ee36d79`, unchanged `main=7fc4aa5`, and failed exact-head run `29971566980` at `4/5`. D1a writes were limited to the approved candidate creation and approved strict fast-forward. `.53`, tags, both main refs, deployment, and process state were not changed.

## Divergence explanation

### Local repaired candidate versus published/deployed truth

At D0 audit anchor `d39b4a9`, local `codex/project-consolidation` was 57 commits ahead of local `main`, 399 commits ahead of GitHub `main`, and had no upstream. D1a published `6086e69`, then its first retry fast-forwarded the same ref to `ee36d79`. Local repair `6a81987` and the report-containing commit remain local-only and must be identified by the next exact handoff. The branch intentionally remains ahead of the remote candidate. The single sibling divergence remains the documented `b9abdbd` versus local `4359602` case.

The local product metadata is `1.6.0`, but no `v1.6.0` tag exists. The candidate ref is published only at the failed attempt-2 SHA `ee36d79`; the repaired tip is intentionally local until fresh artifact binding and D1a retry-2 authorization. This is recorded divergence, not a release and never “synchronized”.

Attempt-1 run [29894971142](https://github.com/NHNQNHNQ/PRAXIS-Virtualcell/actions/runs/29894971142) passed only the reproducible release-wheel job. Three Python jobs stopped during dev hash-lock installation because Linux-marked greenlet was absent; frontend build gates passed but its lean runtime environment omitted Cobra, producing one honest FBA fail-closed E2E failure. Local repair also closes the subsequently exposed non-Darwin watchdog marker. Full diagnosis and validation are in [PHASE-D1A-CI-2026-07-22.md](PHASE-D1A-CI-2026-07-22.md).

Attempt-2 run [29971566980](https://github.com/NHNQNHNQ/PRAXIS-Virtualcell/actions/runs/29971566980) passed Python core, frontend/Playwright, reproducible wheel, and Linux release container. Legacy alone failed because Linux dash left `cat` alive after the direct shell was killed. Local commit `6a81987` closes process-group, deadline, drain-error, and caller-cancellation cleanup; fresh macOS/Linux strict-lock legacy suites are `1139/59/105/0`. Full evidence is in [PHASE-D1A-CI-RETRY-2026-07-23.md](PHASE-D1A-CI-RETRY-2026-07-23.md).

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
- 2026-07-22 GitHub API reads returned candidate `6086e6995b1c3c01ec31075ce1164a0165cb8d43`, `main=7fc4aa5b3bd03871358385f1d467a515be15aafe`, and run `29894971142` as completed/failure at exact head `6086e69`.
- 2026-07-23 GitHub API reads returned candidate `ee36d7948047f346f55a02d62ccaac84391e3c20`, unchanged `main=7fc4aa5b3bd03871358385f1d467a515be15aafe`, and run `29971566980` as completed/failure at exact head `ee36d79` with four passing jobs.

## Phase D synchronization protocol

The first D1a publication and first retry authorizations are both spent; neither can cover a new commit. The exact refs, rollback anchors, dirty-file disposition, CI order, `.53` branch path, and stop conditions remain frozen in [Phase D0 Three-End Audit and Synchronization Proposal](PHASE-D0-SYNC-PROPOSAL-2026-07-18.md).

1. Commit the D1a report/current ledgers, then bind the exact clean report-containing 40-hex to post-commit double-wheel, clean-install verifier, and release-container smoke proof.
2. Present that exact SHA/digest and request a **fresh D1a retry-2 authorization**. Expected remote candidate must be `ee36d7948047f346f55a02d62ccaac84391e3c20`, and `merge-base --is-ancestor ee36… <new>` must pass.
3. With fresh D1a approval, update only that candidate branch using exact-ref compare-and-swap lease plus ancestry guard and `--no-follow-tags`, then require all five CI jobs green at the new exact SHA. The lease does not authorize a non-fast-forward update.
4. With separate D1b approval and green CI, use the same exact old-ref CAS plus ancestry guard to non-force fast-forward GitHub `main`; after exact tag-conflict checks, create/push only `v1.6.0` at the same SHA with implicit tag following disabled.
5. With separate D1c approval, fetch only the exact main ref and fast-forward local `main` from the now-authoritative GitHub `main`; D1b does not imply D1c.
6. With separate D2 approval, preserve detached `b9abdbd`, `remote-gears-l4-95dc764`, and `vc_api.log`; fetch GitHub and create `codex/deploy-v1.6.0` at the exact approved SHA.
7. Validate deployment/service/science only within their separately approved boundaries, then record three-end SHA/tag/worktree/CI/artifact/smoke proof.

Until those steps are explicitly authorized and completed, the correct state is `KNOWN_DIVERGENCE`, not “synchronized”.
