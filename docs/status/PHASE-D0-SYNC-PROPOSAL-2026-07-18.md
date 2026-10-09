# Phase D0 Three-End Audit and Synchronization Proposal — 2026-07-18

> Status: `D0_READ_ONLY_AUDIT_COMPLETE — KNOWN_DIVERGENCE — EXTERNAL_WRITES_NOT_AUTHORIZED`
>
> Read-only observation window: 2026-07-18 20:38–20:43 CST (+0800)
>
> Audit anchor before this report: `d39b4a980c469e0b4546eaab5f09325e6527368a`

This report closes the read-only part of D0. It does not authorize a push, PR, merge, tag, `.53` fetch/checkout, deployment, service action, or remote scientific test. The first commit that adds this report is the immutable **D0 report anchor** and can be recovered without chat history:

```bash
git log --diff-filter=A --format='%H' --reverse -- \
  docs/status/PHASE-D0-SYNC-PROPOSAL-2026-07-18.md | head -n 1
```

The authoritative candidate is always the explicit 40-hex clean tip of `codex/project-consolidation` named in the current approval handoff, with a matching post-commit double-wheel/clean-install record. For the first handoff it should equal the D0 report anchor. Any later commit supersedes it, invalidates its artifact/CI approval, and requires a fresh 40-hex handoff; the recovery command intentionally continues to identify only the report anchor. A branch name, `HEAD`, “latest”, or an old handoff is never sufficient authority. No commit is allowed between artifact binding/approval and its exact-SHA push.

## 1. Fresh live ledger

| Endpoint | Fresh observation | Worktree/ref boundary |
|---|---|---|
| APFS local | `codex/project-consolidation=d39b4a9` at audit time; no upstream; `main=176019e`; protected `.claude/` and `string.jpeg` remain untracked | tracked worktree clean; stash `77cb06d`, recovery material, tags, and T7 archive preserved |
| GitHub HTTPS | `main=7fc4aa5`; `feat/v0.9-phase0-module-core=b9abdbd`; tags through `v0.8.0`; no `codex/project-consolidation` | `git ls-remote --heads --tags` exit 0; no GitHub write or local tracking-ref update |
| `.53` read-only SSH | detached `HEAD=b9abdbd`; `main=7fc4aa5`; feature branch `b9abdbd`; `remote-gears-l4-95dc764=95dc764` | only untracked `vc_api.log`, 32,504 bytes, mtime `2026-07-12 12:07:01 UTC`; contents not read; no fetch/checkout/process action |

Both persisted origins identify `git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git`. Local historical tags `v0.9.0` through `v1.5.0` remain intentionally unpublished and must not be included in a broad tag push.

## 2. Ancestry and sibling-ref decision

At audit anchor `d39b4a9`:

```text
HEAD...local main                              57 left / 0 right
HEAD...GitHub main                            399 left / 0 right
HEAD...GitHub former feature                 138 left / 1 right
local main...GitHub main                      342 left / 0 right
```

- `GitHub main=7fc4aa5` is an ancestor of local `main=176019e`, and local `main` is an ancestor of the candidate line. Updating GitHub main to the final candidate can therefore be a non-force fast-forward if no remote change occurs first.
- `b9abdbd` and the candidate are siblings with merge base `b43851e`; neither is the other's ancestor. The two-file tree at local `4359602` contains the same `gears_available()` production behavior as `b9abdbd` plus the explicit empty-`GEARS_CKPT` fail-closed test, and later local commits add the governed GEARS dispatch/tests. Do not merge the older sibling merely to make the graph linear.
- `.53`'s `95dc764` is one commit unique relative to its merge base and adds `praxis_virtualcell/benchmarks/gears_donor_eval.py`; relative to `b9abdbd` its range is `1 left / 343 right`. It is experimental evidence, not deployment truth. Preserve the ref and do not merge, delete, rename, or push it implicitly.

## 3. Release artifact binding

The pre-report audit anchor `d39b4a9` passed a full D0 rehearsal:

- two clean-archive Python 3.13 builds were byte-identical;
- wheel: `praxis_virtualcell-1.6.0-py3-none-any.whl`, 923,687 bytes;
- SHA-256: `d1d536022bae9d67d14c806d889934a89e8119b0feb8219db458f15311bc0500`;
- hash-locked runtime install, `pip check`, `praxis-vc --version`, installed offline run, API health/job, same-origin root/hashed asset, packaged web entry, and test-tree exclusion passed from outside the checkout.

This is a rehearsal, not the final release digest, because adding this D0 report changes the candidate commit and `SOURCE_DATE_EPOCH`. After the D0 close commit, repeat the same double build and clean install. Only that post-commit digest may appear in the user approval handoff.

## 4. Proposed D1 — GitHub in two approvals

### D1a: branch publication only

The first and narrowest requested authorization should cover only the exact SHA in the handoff. `expected_remote_candidate_sha` is `ABSENT` for the first publication; a retry must name the previously approved remote branch SHA and prove it is an ancestor of the new candidate:

```bash
set -euo pipefail
approved_candidate_sha='<APPROVED_40_HEX_SHA>'
expected_remote_candidate_sha='<ABSENT_OR_PREVIOUS_APPROVED_40_HEX_SHA>'
github_https='https://github.com/NHNQNHNQ/PRAXIS-Virtualcell.git'
candidate_ref='refs/heads/codex/project-consolidation'

test "$(git rev-parse HEAD)" = "$approved_candidate_sha"
test "$(git rev-parse refs/heads/codex/project-consolidation)" = "$approved_candidate_sha"
test "$(git remote get-url --push origin)" = \
  'git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git'
git diff --quiet
git diff --cached --quiet
expected_untracked="$(printf '?? .claude/\n?? string.jpeg')"
test "$(git status --porcelain=v1 --untracked-files=normal)" = \
  "$expected_untracked"

remote_candidate_sha="$(git ls-remote "$github_https" \
  "$candidate_ref" | awk '{print $1}')"
if test "$expected_remote_candidate_sha" = 'ABSENT'; then
  test -z "$remote_candidate_sha"
  lease_expected_sha=''
else
  test "$remote_candidate_sha" = "$expected_remote_candidate_sha"
  git cat-file -e "$expected_remote_candidate_sha^{commit}"
  git merge-base --is-ancestor \
    "$expected_remote_candidate_sha" "$approved_candidate_sha"
  lease_expected_sha="$expected_remote_candidate_sha"
fi

git push --no-follow-tags \
  --force-with-lease="$candidate_ref:$lease_expected_sha" origin \
  "$approved_candidate_sha:$candidate_ref"
test "$(git ls-remote "$github_https" \
  "$candidate_ref" | awk '{print $1}')" = \
  "$approved_candidate_sha"
```

The tracked worktree must be clean; the separately protected `.claude/` and `string.jpeg` may remain untracked exactly as recorded. The explicit lease is a compare-and-swap guard against a check/push race, not permission for a non-fast-forward update: the retry path separately proves the approved previous SHA is an ancestor. `--no-follow-tags` is mandatory even if local Git configuration enables `push.followTags`. Do not update `main` or any tag in D1a. Upstream metadata is optional and may be set only after the live exact-SHA verification; it is not part of publication truth.

Observe all five configured candidate jobs (`python-core`, `frontend`, `release-wheel`, `release-container`, `legacy-unit`). A workflow file existing locally is not CI evidence; record the actual run URL/ID, SHA, conclusion, and each job result. Any failure returns to a new local commit and restarts candidate/artifact binding.

### D1b: reviewed main fast-forward and release tag

After green CI on the exact approved candidate, fresh ancestry recheck, and a separate user approval, require an approval-ledger value for the old GitHub main. The execution skeleton is:

```bash
set -euo pipefail
approved_candidate_sha='<CI_GREEN_APPROVED_40_HEX_SHA>'
expected_old_main_sha='<D1B_APPROVED_LIVE_MAIN_40_HEX_SHA>'
github_https='https://github.com/NHNQNHNQ/PRAXIS-Virtualcell.git'
main_ref='refs/heads/main'

test "$(git rev-parse HEAD)" = "$approved_candidate_sha"
test "$(git rev-parse refs/heads/codex/project-consolidation)" = \
  "$approved_candidate_sha"
test "$(git remote get-url --push origin)" = \
  'git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git'
git diff --quiet
git diff --cached --quiet
expected_untracked="$(printf '?? .claude/\n?? string.jpeg')"
test "$(git status --porcelain=v1 --untracked-files=normal)" = \
  "$expected_untracked"
test "$(git ls-remote "$github_https" "$main_ref" | awk '{print $1}')" = \
  "$expected_old_main_sha"
test "$(git ls-remote "$github_https" \
  refs/heads/codex/project-consolidation | awk '{print $1}')" = \
  "$approved_candidate_sha"
test -z "$(git ls-remote --tags "$github_https" \
  refs/tags/v1.6.0 'refs/tags/v1.6.0^{}')"
test -z "$(git show-ref --verify --hash refs/tags/v1.6.0 || true)"
git cat-file -e "$expected_old_main_sha^{commit}"
git merge-base --is-ancestor "$expected_old_main_sha" "$approved_candidate_sha"

git push --no-follow-tags \
  --force-with-lease="$main_ref:$expected_old_main_sha" origin \
  "$approved_candidate_sha:$main_ref"
test "$(git ls-remote "$github_https" "$main_ref" | awk '{print $1}')" = \
  "$approved_candidate_sha"

git tag -a v1.6.0 "$approved_candidate_sha" -m 'PRAXIS-VirtualCell 1.6.0'
test "$(git rev-parse 'refs/tags/v1.6.0^{}')" = "$approved_candidate_sha"
local_tag_object_sha="$(git rev-parse refs/tags/v1.6.0)"
git push --no-follow-tags origin refs/tags/v1.6.0
test "$(git ls-remote --tags "$github_https" refs/tags/v1.6.0 | \
  awk '{print $1}')" = "$local_tag_object_sha"
test "$(git ls-remote --tags "$github_https" \
  'refs/tags/v1.6.0^{}' | awk '{print $1}')" = "$approved_candidate_sha"
```

The approval ledger must also bind the visible CI run's `head_sha` to `approved_candidate_sha`; matching branch names are insufficient. The main lease is a compare-and-swap guard, while the separate ancestry check enforces a fast-forward; neither the lease nor this proposal authorizes a non-fast-forward update.

The intended state transitions are:

1. update GitHub `main` by non-force fast-forward to the exact candidate;
2. verify live `refs/heads/main` equals that SHA;
3. create annotated `v1.6.0` at that same SHA and push only `refs/tags/v1.6.0`;
4. do not push local `v0.9.0`–`v1.5.0` or use `--tags`/`--all`.

If branch protection requires a GitHub-generated merge/rebase/squash commit, that new SHA becomes a new candidate. Stop, rebuild/retest/rebind artifacts and request approval again; never tag or deploy a SHA that was not the tested candidate.

If main updates successfully but local tag creation or tag push fails, do not move main backward. Record `MAIN_UPDATED_TAG_PENDING`, preserve the exact successful main SHA, and request/perform only the missing exact-tag recovery step after rechecking that no conflicting tag exists. Never force, delete, or replace a tag.

Under this proposal, `v1.6.0` means “source release passed GitHub candidate CI”; it does not claim `.53` deployment validation. If the user requires `.53` smoke before publication, D1b approval must explicitly defer the tag and D2 must be redesigned around an untagged candidate; do not silently change the order during execution.

### D1c: local main

Only after GitHub main/tag are authoritative and a **separate D1c authorization** is granted, fetch the exact main ref locally and use an explicit fast-forward-only merge:

```bash
(
  set -euo pipefail
  approved_candidate_sha='<APPROVED_40_HEX_SHA>'
  expected_local_main_sha='<D1C_APPROVED_OLD_LOCAL_MAIN_40_HEX_SHA>'
  github_https='https://github.com/NHNQNHNQ/PRAXIS-Virtualcell.git'

  test "$(git rev-parse HEAD)" = "$approved_candidate_sha"
  test "$(git rev-parse refs/heads/codex/project-consolidation)" = \
    "$approved_candidate_sha"
  test "$(git rev-parse refs/heads/main)" = "$expected_local_main_sha"
  test "$(git remote get-url origin)" = \
    'git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git'
  test "$(git ls-remote "$github_https" refs/heads/main | awk '{print $1}')" = \
    "$approved_candidate_sha"
  git merge-base --is-ancestor "$expected_local_main_sha" "$approved_candidate_sha"
  git diff --quiet
  git diff --cached --quiet
  expected_untracked="$(printf '?? .claude/\n?? string.jpeg')"
  test "$(git status --porcelain=v1 --untracked-files=normal)" = \
    "$expected_untracked"
  test -z "$(git ls-tree -r --name-only "$approved_candidate_sha" -- \
    .claude string.jpeg)"

  git fetch --no-tags origin \
    refs/heads/main:refs/remotes/origin/main
  test "$(git rev-parse refs/remotes/origin/main)" = "$approved_candidate_sha"
  git switch main
  git merge --ff-only origin/main
  test "$(git rev-parse HEAD)" = "$approved_candidate_sha"
  test "$(git status --porcelain=v1 --untracked-files=normal)" = \
    "$expected_untracked"
  git switch codex/project-consolidation
  test "$(git rev-parse HEAD)" = "$approved_candidate_sha"
  test "$(git rev-parse refs/heads/main)" = "$approved_candidate_sha"
  test "$(git status --porcelain=v1 --untracked-files=normal)" = \
    "$expected_untracked"
)
```

D1b authorization does not imply D1c. After D1c, require:

```text
local main == GitHub main == approved candidate SHA
```

Keep `codex/project-consolidation`, the local milestone tags, stash, recovery refs, protected untracked assets, and T7 archive. Do not rebase, reset, clean, or delete them.

## 5. Proposed D2 — `.53` deployment branch

Before any `.53` change, repeat path/origin/HEAD/branch/status/ref/log-metadata checks with `GIT_OPTIONAL_LOCKS=0`, confirm the approved candidate/tag still exist on GitHub, inspect service state in a separately approved maintenance window, and require the only untracked path to be the approved `vc_api.log`.

Preserve these exact anchors:

```text
previous detached HEAD / feature branch  b9abdbdf733406853c4a338b29b705ca801d7ac7
previous .53 main                        7fc4aa5b3bd03871358385f1d467a515be15aafe
remote experiment branch                 95dc7648a035cf69c0453fe11787958548ec04a2
untracked log                             vc_api.log (preserve in place; never clean)
```

Because `b9abdbd` is not an ancestor of the candidate, do not merge or reset it. D2 must use only the two approved refspecs, never broad tag fetch:

```bash
(
  set -euo pipefail
  export GIT_OPTIONAL_LOCKS=0
  approved_candidate_sha='<APPROVED_40_HEX_SHA>'
  approved_tag_object_sha='<D2_APPROVED_TAG_OBJECT_40_HEX_SHA>'
  cd /home/zkyd/data1/mzy/PRAXIS-virtualcell

  test "$(git remote get-url origin)" = \
    'git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git'
  test "$(git rev-parse HEAD)" = \
    'b9abdbdf733406853c4a338b29b705ca801d7ac7'
  test "$(git rev-parse refs/heads/feat/v0.9-phase0-module-core)" = \
    'b9abdbdf733406853c4a338b29b705ca801d7ac7'
  test "$(git rev-parse refs/heads/main)" = \
    '7fc4aa5b3bd03871358385f1d467a515be15aafe'
  test "$(git rev-parse refs/heads/remote-gears-l4-95dc764)" = \
    '95dc7648a035cf69c0453fe11787958548ec04a2'
  test -z "$(git symbolic-ref -q HEAD || true)"
  git diff --quiet
  git diff --cached --quiet
  test "$(git status --porcelain=v1 --untracked-files=all)" = '?? vc_api.log'
  test -z "$(git show-ref --verify --hash \
    refs/heads/codex/deploy-v1.6.0 || true)"
  test -z "$(git show-ref --verify --hash refs/tags/v1.6.0 || true)"

  test "$(git ls-remote origin refs/heads/main | awk '{print $1}')" = \
    "$approved_candidate_sha"
  test "$(git ls-remote --tags origin refs/tags/v1.6.0 | \
    awk '{print $1}')" = "$approved_tag_object_sha"
  test "$(git ls-remote --tags origin 'refs/tags/v1.6.0^{}' | \
    awk '{print $1}')" = "$approved_candidate_sha"

  git fetch --atomic --no-tags origin \
    refs/heads/main:refs/remotes/origin/main \
    refs/tags/v1.6.0:refs/tags/v1.6.0
  test "$(git rev-parse refs/remotes/origin/main)" = "$approved_candidate_sha"
  test "$(git rev-parse refs/tags/v1.6.0)" = "$approved_tag_object_sha"
  test "$(git rev-parse 'refs/tags/v1.6.0^{}')" = "$approved_candidate_sha"
  if git cat-file -e "$approved_candidate_sha:vc_api.log" 2>/dev/null; then
    exit 2
  fi
  test "$(git status --porcelain=v1 --untracked-files=all)" = '?? vc_api.log'

  git switch -c codex/deploy-v1.6.0 --track origin/main
  test "$(git rev-parse HEAD)" = "$approved_candidate_sha"
  test "$(git status --porcelain=v1 --untracked-files=all)" = '?? vc_api.log'
)
```

If any precondition fails, stop. The fetch may update only `origin/main` and the exact `v1.6.0` tag; never merge/reset the old line or delete/prune any ref.

Service restart/reload, Docker/API smoke, and W4B science are separate operational actions. The W4B runbook additionally requires approved clean donor origin/SHA and an independently trusted six-file digest set before donor import or `weights_only=False` PT loading. Sync success must not be inferred from a checkout alone.

## 6. Proof and rollback

Final proof must capture in one window:

- local `main`, GitHub live `main`, and `.53` deployed branch at the same approved SHA;
- local/GitHub/`.53` `v1.6.0` tag object and peeled commit;
- branch/worktree status, preserved exception refs/log, CI run, release artifact digest, and approved smoke results;
- remaining scientific pending items without upgrading them to pass.

Rollback is endpoint-specific and never uses a force or lease operation:

- before GitHub main changes, delete nothing; the published state is still `v0.8.0/7fc4aa5`;
- after publication, a GitHub defect is corrected by a reviewed forward revert/fix commit and the same CI/sync flow, not by moving main backward;
- `.53` may return, in an approved service window, to detached `b9abdbd` or its existing `main=7fc4aa5` only when tracked state is clean and the sole approved untracked path remains `vc_api.log`; any source/test artifact dirtiness stops the rollback, with no clean/stash/reset. Keep the failed deployment branch for evidence and record the three ends as deployment-rolled-back/divergent; GitHub main/tag remain forward and must not be moved backward merely to recreate equality;
- local `v1.5.0→176019e`, GitHub `v0.8.0→7fc4aa5`, `.53` feature `b9abdbd`, and `.53` experiment `95dc764` are already immutable rollback/audit anchors.

The recommended next authorization is **D1a only: push the exact candidate SHA to the named candidate branch and observe CI**. D1b main/tag, D1c local-main fast-forward, D2 `.53` fetch/checkout, service action, and remote science are separate authorization gates.
