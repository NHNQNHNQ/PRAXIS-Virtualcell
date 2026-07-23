# Phase D1a Candidate Retry 1 and CI Attempt 2 — 2026-07-23

> Status: `D1A_RETRY_1_RECORDED — CI_4_OF_5 — LOCAL_PROCESS_GROUP_FIX_VERIFIED — RETRY_2_AUTHORIZATION_PENDING`
>
> Published candidate: `ee36d7948047f346f55a02d62ccaac84391e3c20`
>
> Local implementation fix: `6a8198771581d0897a13457e93e50cfec172d59a`

This report records the first D1a retry publication, its exact-head GitHub
Actions result, and the local repair of the only remaining failure. It does not
authorize another push, GitHub `main` or tag changes, local `main` changes,
`.53` access, deployment, or remote science. The first commit that adds this
file is its report anchor:

```bash
git log --diff-filter=A --format='%H' --reverse -- \
  docs/status/PHASE-D1A-CI-RETRY-2026-07-23.md | head -n 1
```

The report-containing tip cannot name its own SHA without creating a recursive
commit. The next handoff must bind that final clean 40-hex and its post-commit
release artifact separately.

## 1. Authorized compare-and-swap publication

The user authorized only this exact fast-forward:

| Field | Bound value |
|---|---|
| Repository | `NHNQNHNQ/PRAXIS-Virtualcell` |
| Ref | `refs/heads/codex/project-consolidation` |
| Expected old SHA | `6086e6995b1c3c01ec31075ce1164a0165cb8d43` |
| Approved new SHA | `ee36d7948047f346f55a02d62ccaac84391e3c20` |
| Ancestry | strict fast-forward, two commits |
| Push boundary | exact ref, exact lease, `--no-follow-tags` |

Preflight established a clean tracked tree, the expected protected untracked
files only, unchanged local `main`/tags/stash, live GitHub candidate `6086…`,
live GitHub `main=7fc4aa5`, and `merge-base --is-ancestor 6086… ee36…`.

The first SSH-over-443 command failed host-key alias matching before any write.
Read-only authentication then reused the already verified `github.com` host key
with `HostKeyAlias=github.com`; the original exact-lease push succeeded. Fresh
GitHub API verification established:

```text
GitHub refs/heads/codex/project-consolidation
  = ee36d7948047f346f55a02d62ccaac84391e3c20
```

No GitHub `main`, tag, PR, local `main`, local tag, or `.53` state changed.

## 2. GitHub Actions attempt 2

- Workflow: `ci`
- Event: `push`
- Run ID: `29971566980`
- Run URL: <https://github.com/NHNQNHNQ/PRAXIS-Virtualcell/actions/runs/29971566980>
- Head SHA: `ee36d7948047f346f55a02d62ccaac84391e3c20`
- Aggregate: **4 passed / 1 failed jobs**

| Job | Result | Exact boundary reached |
|---|---|---|
| Python lint and VirtualCell core | PASS | environment, Ruff, dependency check, and core suite passed |
| Linux release container smoke | PASS | locked test environment and release-image smoke passed |
| Reproducible full release wheel | PASS | both builds, byte comparison, locked install, and installed verifier passed |
| Frontend build and Playwright | PASS | typecheck, lint, build, and Playwright passed |
| Legacy unit tests (external suites gated) | FAIL | `1 failed / 1135 passed / 59 skipped / 105 deselected`; only `test_huge_output_capped_not_ooming` failed |

The run also emitted non-blocking GitHub Actions warnings that Node 20-based
action implementations were being forced onto Node 24. Those warnings did not
fail a job and are not silently treated as branch-protection configuration.

## 3. Remaining root cause

The failure was not qemu slowness. GitHub's native Linux x86_64 Python 3.13.14
runner reproduced the same exact behavior previously seen in the local Linux
iteration:

```text
cat /dev/zero
  expected: read output cap, terminate immediately, ok=True/truncated=True
  actual:   command timeout after 10 seconds, ok=False
```

`asyncio.create_subprocess_shell` returned the direct `/bin/sh` process. On
Linux, dash retained that shell and forked `cat`; the existing `proc.kill()`
terminated only the shell. `cat` remained alive, inherited both output pipes,
and prevented the sibling drain from observing EOF. macOS `/bin/sh` happened to
exec the simple command directly, so killing the direct PID had hidden the bug.

Independent review then found two related lifecycle gaps in the same path:

- the timeout covered only stdout/stderr drains, not the later `proc.wait()`, so
  a command could close both pipes and continue past its deadline;
- caller cancellation after both pipes closed cancelled the wait task but could
  leave the process group alive.

These are execution-lifecycle defects, not scientific-model or test-timing
issues. The failing assertion, timeout contract, and skip policy were retained.

## 4. Implemented repair

Commit `6a8198771581d0897a13457e93e50cfec172d59a` changes only
`praxis2/tools/bash.py` and `tests/test_tools_bash.py`:

- start each POSIX command in a new session/process group;
- terminate the group, with a non-POSIX direct-process fallback, on output cap,
  timeout, drain failure, or caller cancellation;
- discard already-buffered pipe bytes after truncation without growing the
  captured buffer, so process waiting cannot be held by a paused pipe;
- put both drains and `proc.wait()` under one deadline;
- reap the process before returning a timeout/error and before re-raising caller
  cancellation;
- strengthen the infinite-output regression to force a real shell child on
  macOS and Linux;
- add regressions for timeout child cleanup, closed-pipe deadline enforcement,
  and cancellation cleanup; make the drain-error regression prove prompt group
  termination.

This is process-group containment for ordinary shell descendants. It is not
claimed to replace cgroup containment for a command that deliberately creates a
new session of its own.

## 5. Local validation of the repaired line

### macOS arm64, fresh Python 3.13.12 strict-lock environment

| Check | Result |
|---|---|
| build + dev `--require-hashes`, editable `--no-deps`, `pip check` | PASS |
| full-repository Ruff | PASS |
| VirtualCell core, `-m "not llm"` | `965 passed / 35 skipped / 9 deselected / 0 failed` |
| legacy CI isolation | `1139 passed / 59 skipped / 105 deselected / 0 failed` |

### Docker Desktop Linux/arm64, Python 3.13.14 strict-lock environment

The repository was copied into an ephemeral container from a read-only mount;
the exact build/dev hash locks were installed before the editable package.

| Check | Result |
|---|---|
| strict build + dev hash-lock install and `pip check` | PASS |
| full-repository Ruff | PASS |
| legacy CI isolation | `1139 passed / 59 skipped / 105 deselected / 0 failed` |
| forced shell-child infinite stream | `ok=True`, `truncated=True`, approximately `0.002s` |
| closed-pipe 1-second timeout | `ok=False`, timeout, approximately `1.01s` |
| caller cancellation after pipe close | cancellation propagated; no sentinel/orphan side effect |
| injected one-sided drain error | structured error returned in approximately `0.008s` |

GitHub's next native Linux x86_64 run remains the publication authority. The
local Linux full suite is evidence for the repair, not a substitute for that
run.

## 6. Protection and next gate

- Remote candidate is now `ee36d7948047f346f55a02d62ccaac84391e3c20`.
- GitHub `main=7fc4aa5`, local `main=176019e`, tags, stash, and `.53`'s D0
  last-observed detached `b9abdbd` state remain unchanged.
- Protected `.claude/`, ignored `.playwright-mcp/`, `string.jpeg`, recovery
  material, and the T7 archive remain preserved.
- D1b, D1c, D2, service actions, and remote science are not authorized.

After the final documentation commit, build the exact clean tip twice, repeat
the locked installed verifier and release-container smoke, and bind its 40-hex
and artifact digest. Then request a fresh **D1a retry 2** authorization with:

```text
expected remote candidate = ee36d7948047f346f55a02d62ccaac84391e3c20
required ancestry         = ee36d7948047f346f55a02d62ccaac84391e3c20 -> new candidate
update                     = exact-ref CAS lease + --no-follow-tags
success criterion          = all five jobs green at the new exact SHA
```

The authorization consumed by attempt 2 cannot cover another commit or push.
