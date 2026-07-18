# PRAXIS-VirtualCell Phase C4 Completion Gate — 2026-07-18

> Status: `C4_COMPLETE_LOCAL`
>
> Fixed implementation evidence HEAD: `8ce42fe5d167bc4f41bbee596cdc9ab255591056`
>
> Candidate product version: `1.6.0` — local, unpublished, untagged, undeployed
>
> Captured: 2026-07-18 19:42 CST (+0800)

This gate closes the local dependency, bundle, package, API, and release-container work assigned to C4. It does not publish the candidate, certify GitHub Actions, validate `.53`, or change the scientific capability boundary.

## 1. Candidate identity and change boundary

- Branch: `codex/project-consolidation`, intentionally without an upstream.
- C4 implementation range: `b573f01..8ce42fe`, 11 commits. `b573f01` is the C3 documentation closure and is not part of the C4 implementation range.
- Evidence HEAD is committed. `git status --short --branch` showed only the protected untracked `.claude/` and `string.jpeg`; ignored `.playwright-mcp/`, recovery material, stash, and the T7 source archive remain preserved.
- No push, pull, PR, merge, tag, release, deployment, `.53` mutation, or GitHub Actions run occurred.

The C4 commits are:

```text
3a1137c perf(ui): lazy-load results bundle
4822a65 test(ui): enforce lazy bundle budgets
734ae9f build(deps): lock Python 3.13 environments
ae388fb fix(package): ship default routing data
f174753 build(release): package web assets in wheel
a6b68ba fix(api): hide internal job errors
925da06 build(release): harden wheel and container reproduction
a4138c7 docs(release): document C4 package contract
2991bf8 fix(package): exclude test data from release
5d91b11 test(container): probe offline image via loopback
8ce42fe fix(container): retain legacy frontend ignore
```

## 2. C4 acceptance results

### 2.1 Python dependency and API boundary

- Added hash-locked Python 3.13 build, runtime, and development environments. Release builds install the build-backend lock and use `--no-build-isolation`; runtime and development installs use `--require-hashes`.
- Replaced the deprecated Starlette `TestClient` dependency path with the declared `httpx2` compatibility path. The final Python 3.13 core run emitted no prior Starlette/httpx deprecation warning.
- `/api/jobs` maps request validation failures to HTTP 400 with the stable public code `invalid_request`; unexpected exceptions are logged server-side and return HTTP 500 with `job_execution_failed`. Regression tests prove internal exception text is not reflected to clients.

### 2.2 Frontend split and budgets

C3 reported a single main JavaScript chunk of 635.51 kB raw / 185.40 kB gzip. C4 moves Results/Recharts behind an explicit lazy boundary and enforces initial, lazy, and font budgets in the build:

| Asset group | Raw bytes | Gzip bytes | Loading boundary |
|---|---:|---:|---|
| initial JavaScript aggregate | 226,046 | 70,320 | initial route |
| `ResultsStage` JavaScript | 410,889 | 114,914 | loaded only on Results |
| eight local font assets | 214,292 | not a JS budget | static assets |

The final build transformed 612 modules and passed the bundle-budget script. Playwright verifies that the Results code is absent initially and loads from both the live workflow and history paths with an accessible loading state.

### 2.3 Full release wheel

`scripts/build_release_wheel.sh` builds from a clean `git archive HEAD`, rebuilds React assets in the temporary source tree, installs the hash-locked build backend, and rejects tracked dirty state. Two independent builds at the fixed evidence HEAD were byte-identical:

| Artifact | Result |
|---|---|
| filename | `praxis_virtualcell-1.6.0-py3-none-any.whl` |
| size | 922,334 bytes |
| SHA-256 | `78e5287a5dd61478b041fd1a28783732cb75a250de02eec306d3803b3128fd4f` |
| reproducibility | two clean builds; `cmp` exit 0 |

A fresh Python 3.13.12 environment installed the hash-locked runtime plus this wheel from outside the checkout. `pip check` passed. `scripts/verify_release_install.py` then proved:

- package version `1.6.0`;
- the installed package's CLI main/offline run path produced non-empty `report.md`, `report.json`, `trace.json`, and `provenance.json`;
- API health and an offline job returned HTTP 200;
- the same-origin root and a hashed React asset were served from the installed package;
- package test trees are absent from the wheel.

Separately, from `/tmp`, the installed console script itself reported `praxis-vc 1.6.0` and `praxis-vc run` produced the same four non-empty offline artifacts. Package guards and wheel-content inspection prove that `praxis_vc_web/app.py` and the three reviewed default gene-set JSON files are present, while root research datasets and package test trees are excluded.

### 2.4 Linux release container

The release Dockerfile uses digest-pinned multi-stage Node 24 Alpine and Python 3.13.14 slim-bookworm bases, hash-locked build/runtime dependencies, a network-disabled final install, a non-root `10001:10001` runtime, a persistent runs path, and mandatory full Git SHA / commit epoch build arguments. The final image contains the installed wheel environment rather than the source tree or build wheelhouse.

The opt-in smoke built the candidate image and ran the container with `--network none`. HTTP checks execute inside the container against loopback, so no host port or external network is needed. All five checks passed in 36.81 seconds:

1. OCI revision, healthcheck, environment, and non-root image contract;
2. runtime UID/GID and installed-wheel offline CLI outputs;
3. candidate version/SHA/mode in health plus Docker health state;
4. root HTML and hashed JavaScript/CSS assets;
5. offline API job, structured report, and Markdown report.

The smoke image and container used a unique ownership label and immutable ID check before cleanup; the container was removed with its anonymous volume. The smoke creates no custom network, and no owned image or container remained after the run.

## 3. Final local verification matrix

Python checks used a fresh hash-locked Python 3.13.12 development environment created under `/tmp`; the active source archive on T7 was not modified. Frontend checks used local Node 26.4.0 / npm 11.17.0. After the normal full frontend gate, the same 57-case browser suite was repeated against an explicitly prestarted API from the locked Python 3.13.12 environment and again returned 56 passed / 1 real-LLM skip. The Docker build independently exercised the pinned Linux build/runtime images.

| Layer | Exact scope | Result |
|---|---|---|
| dependency integrity | build/dev locks, editable install without build isolation, `python -m pip check` | PASS; 0 broken requirements |
| Python lint | `ruff check .` | PASS; 0 diagnostics |
| VirtualCell core | `python -m pytest praxis_virtualcell/tests -m "not llm" -o addopts='' -q -ra` | `957 passed / 35 skipped / 9 deselected / 0 failed` in 10.44 s |
| legacy CI isolation | `python -m pytest tests -m "not (integration or llm or remote)" -o addopts='' -q -ra` | `1136 passed / 59 skipped / 105 deselected / 0 failed` in 16.50 s |
| legacy broad non-LLM | `python -m pytest tests -m "not llm" -o addopts='' -q -ra` | `1136 passed / 158 skipped / 6 deselected / 0 failed` in 17.29 s |
| frontend supply/static/build | `npm audit --audit-level=high`, typecheck, Oxlint, Vite build, bundle budget | PASS; 0 vulnerabilities |
| Playwright | 14 specs / 57 collected, Chromium, one worker; final repeat used locked Python 3.13.12 API | `56 passed / 1 skipped / 0 failed` in 37.2 s |
| release wheel | two clean builds, `cmp`, locked clean install, `pip check`, installed console entry, installed-package verifier | PASS; hash and size above |
| Docker Desktop Linux container | explicit `PRAXIS_RUN_DOCKER_SMOKE=1` plus `--run-integration` | `5 passed / 0 failed` in 36.81 s |
| diff/worktree | `git diff --check`; explicit status and owned-resource checks | PASS; only protected untracked assets remain |

The Playwright skip is S10, the deliberately unexecuted real-LLM path. The 35 core skips are explicit remote/checkpoint gates plus the five Docker tests that are exercised separately above; an exit-zero skip is not counted as remote capability passing.

## 4. CI configuration and evidence boundary

`.github/workflows/ci.yml` configures five jobs: `python-core`, `frontend`, `release-wheel`, `release-container`, and `legacy-unit`. It pins Python 3.13.14 and Node 24.18.0 where applicable, installs locked environments, and gives the Docker smoke both required opt-ins.

These are configured jobs only. The branch is unpushed, so there is no candidate-SHA GitHub run, URL, branch-protection observation, or evidence that any job is a required check.

The local container server was Docker 29.4.3 on Linux/aarch64 under Docker Desktop (`6.12.76-linuxkit`), with a Darwin/arm64 client. This proves a local Linux-container path, not native Linux host behavior, amd64/x86_64 behavior, cross-platform bit identity, `.53` deployment, or production readiness.

## 5. Deliberately unclaimed scope

C4 does not claim:

- GitHub synchronization, CI success, a PR, tag, published release, or `.53` deployment;
- `.53` Docker/GPU/checkpoint/service health;
- native Linux/amd64 testing or reproducibility across different operating systems/architectures;
- a complete Streamlit server smoke; only packaged presence and CLI path wiring were verified;
- a clean-wheel `praxis-vc ask` run;
- any real LLM call, private checkpoint, paid service, or newly downloaded scientific dataset;
- broader scientific capability than the frozen Phase 10 gate permits.

## 6. Gate decision and next phase

`C4_COMPLETE_LOCAL`

The four C4 plan items are satisfied locally: Python locks/deprecation handling, initial-bundle splitting and budgets, full wheel/CLI/API/same-origin package verification, and a real local Linux-container smoke. C5 must now classify and close the scientific/remote backlog without upgrading unsupported claims. Until C5 local classification is complete, the three-way status remains `KNOWN_DIVERGENCE`, not `READY_TO_SYNC`.
