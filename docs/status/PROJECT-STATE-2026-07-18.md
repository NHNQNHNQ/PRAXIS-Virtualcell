# PRAXIS-VirtualCell Project State — 2026-07-18

> Captured: 2026-07-18 19:42 CST (+0800)
>
> Overall status: `PHASE_A_COMPLETE — PHASE_B_COMPLETE — C0_COMPLETE — C1_COMPLETE — C2_COMPLETE — C3_COMPLETE_LOCAL — C4_COMPLETE_LOCAL — Phase C5 next`
>
> Migration gate: `PHASE_A0_COMPLETE`

This file is the restart authority for the consolidation goal. It records observed facts, not desired end state. Re-run the listed read-only checks before relying on any value that may change.

## Canonical locations

| Role | Location | Rule |
|---|---|---|
| Active local development truth | `/Users/mzy/Projects/PRAXIS-virtualcell` | All Phase A–D work happens here |
| Read-only source archive | `/Volumes/T7/PRAXIS-virtualcell` | Do not stage, clean, reset, stash, gc, prune, or edit |
| Recovery material | `/Users/mzy/Projects/PRAXIS-virtualcell-recovery-20260718` | Preserve through final synchronization and release verification |
| Published truth | GitHub `NHNQNHNQ/PRAXIS-Virtualcell` | Phase A last-observed at `main=7fc4aa5`, tags through `v0.8.0` |
| Deployment/validation mirror | `.53` | Phase A last-observed detached at `b9abdbd`; details in `SYNC-STATE.md` |

The source volume is ExFAT and was 93% full. The active clone and recovery directory are on APFS with approximately 46 GiB available at migration time.

## Git state

| Item | Observed value |
|---|---|
| Audit anchor / current branch base | `24475f2eb14c27c7cfbb82b016b881e88e98b17c` |
| Active branch | `codex/project-consolidation`, created locally at `24475f2`; intentionally no upstream; C4 evidence HEAD `8ce42fe`, local candidate `1.6.0` |
| Preserved former working branch | `feat/v0.9-phase0-module-core=24475f2` |
| Local `main` | `176019ebd9c198f93a5a645f1ecefce9baaf0522` |
| Annotated tag `v1.5.0` | tag object `df04e74`; peeled commit `176019e` |
| Live-fetched `origin/main` tracking ref | `7fc4aa5b3bd03871358385f1d467a515be15aafe` |
| Live-fetched `origin/feat/v0.9-phase0-module-core` | `b9abdbdf733406853c4a338b29b705ca801d7ac7` |
| `refs/stash` | `77cb06d392a8a547e37c390d86769de23437cc83` |
| GitHub origin URL | `git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git` |
| Recovery remote URL | `/Users/mzy/Projects/PRAXIS-virtualcell-recovery-20260718/praxis-all.bundle` |

Observed graph relationships at local C4 evidence checkpoint `8ce42fe`; remote refs are the last values fetched in Phase A:

```text
HEAD...main                                     54 left / 0 right
HEAD...origin/feat/v0.9-phase0-module-core     135 left / 1 right
main...origin/main                              342 left / 0 right
HEAD...origin/main                              396 left / 0 right
```

The two `origin/*` values matched during Phase A's 2026-07-18 HTTPS `ls-remote` and HTTPS-backed `fetch --prune --tags`; they are now last-observed remote evidence and were not revalidated in C3 or C4. The persisted origin URL remains SSH. No pull, merge, rebase, push, PR, tag, or remote write has occurred.

The `.53` host was initially checked read-only during Phase A at 2026-07-18 13:12 CST and re-read at 13:33 immediately before the Phase A gate. That last observation showed detached `b9abdbd`, `main=7fc4aa5`, tags through `v0.8.0`, and one untracked 32,504-byte `vc_api.log`; it also showed `.53`-only branch `remote-gears-l4-95dc764=95dc764`. C3 and C4 did not revalidate those remote values. No process or environment check was performed. See `docs/status/SYNC-STATE.md`.

## Protected worktree state

The APFS clone preserves all original assets. C3 accepted the theme workstream; the remaining local-only assets are still protected:

| Asset | State | Protection |
|---|---|---|
| `praxis_vc_react/src/styles/base.css` | committed in accepted theme | tracked at `92ab4ee`; no worktree diff |
| `praxis_vc_react/src/styles/fonts.css` | committed in accepted theme | tracked at `92ab4ee`; no worktree diff |
| `praxis_vc_react/src/styles/themes.css` | committed in accepted theme | tracked at `92ab4ee`; no worktree diff |
| `praxis_vc_react/src/styles/tokens.css` | committed in accepted theme | tracked at `92ab4ee`; no worktree diff |
| `.claude/launch.json` | untracked | portable local configuration; preserve pending user decision |
| `.playwright-mcp/` (4 files) | ignored, present | archive-with-provenance; do not delete |
| `string.jpeg` | untracked | STRING screenshot; preserve pending provenance decision |
| `docs/superpowers/plans/2026-07-18-*.md` (2 files) | tracked | consolidation authority documents |

The original four-file CSS recovery patch remains preserved at SHA-256 `2c300a185c97f3821edc2e08d91a4d52f6ea1e00bcf52a55f1a1121173eaff7e`. C3 visually reviewed and refined that WIP before committing it; the final tracked theme must not be described as the patch being committed byte-for-byte.

`refs/stash^3` contains only `docs/PRAXIS-生物科学智能体-总介绍.md`. The stash commit has the same `77cb06d` OID in source, bundle, and clone. It was not popped or dropped. Its exported copy is in the recovery directory and has SHA-256 `6dacab11a753fda58b6c2b926a098648d4becf18dcef5b7cc148909431360d20`.

The ignored root `.env` existed in the source archive and was 252 bytes. Its contents were not read, displayed, or copied. No secret is included in the recovery manifest.

The recovery audit also found ignored reproducibility data and Phase 10 evidence that Git bundle could not carry. The following non-secret files were copied from T7 into the same ignored paths in the APFS clone and verified by source/target SHA-256: three `.h5ad` files (1,499,342,078 bytes total), `data/paul15/paul15.h5`, both LINCS L1000 up/down signature files, two JUnit XML files, and `reports/phase10/trace_bundle.json`. Exact hashes are in the recovery manifest. Rebuildable `.venv`, `node_modules`, caches, `dist`, `test-results`, `runs`, `egg-info`, and `__pycache__` were not copied.

Every protected CSS/untracked/stash item has an explicit disposition in `docs/status/WORKTREE-ASSETS.md`. Only the approved theme disposition was implemented, non-destructively, in `92ab4ee`; `.claude/`, ignored `.playwright-mcp/`, `string.jpeg`, stash, recovery material, and the T7 archive remain preserved.

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
- Completion commit: `bf644d268bd3029b233dc100d8f735ebfb09edc5`
- Result: all APFS, ref, WIP, asset, link, change-boundary, and three-way-ledger checks passed.
- External writes: none.

## Phase B baseline progress

The B0–C3 entries in this chronology are frozen phase snapshots. Present-tense wording inside them describes the state at that gate; the header and latest completed-phase entry are the current authority.

`B0_COMPLETE`

- Clean backend environment: Python `3.12.13`, pip `25.0.1`, pytest `9.1.1`, Ruff `0.15.22`; editable install `praxis-virtualcell==0.0.0` with `.[dev,api,mechanistic]` succeeded.
- Installed API stack: FastAPI `0.139.2`, Starlette `1.3.1`, httpx `0.28.1`; `pip check` exited `0` with no broken requirements.
- Clean frontend install: Node `v26.4.0`, npm `11.17.0`, React `19.2.7`, Vite `8.1.2`, Playwright `1.61.1`; `npm ci` and explicit `npm audit` exited `0`, with `0 vulnerabilities`.
- Ruff exited `1` with the expected 13 diagnostics: 2 in production code and 11 in tests; 4 `I001`, 7 `E501`, and 2 `F401`, of which 6 are marked automatically fixable. No fix was applied.
- Connectivity-only fsck exited `0`; there are no missing/corrupt objects and no AppleDouble diagnostics. Eight dangling blobs are non-corrupt staging leftovers and were not pruned.
- Environment creation changed no tracked manifest or source file. The four protected CSS files still produce the exact recovery patch SHA-256 `2c300a185c97f3821edc2e08d91a4d52f6ea1e00bcf52a55f1a1121173eaff7e`.

`B1_COMPLETE`

- Authoritative command `.venv/bin/pytest praxis_virtualcell/tests -m "not llm" -o addopts='' -q -ra` exited `0`: `912 passed / 40 skipped / 9 deselected / 0 failed`, with one Starlette/httpx deprecation warning, in `16.67s`.
- The 40 local skips are fully accounted for: 30 require Torch/GPU/remote donor capabilities and 10 require Linux/Docker. The 9 deselected tests are the `llm` scope.
- `env -u DEEPSEEK_API_KEY .venv/bin/python scripts/phase10/run_phase10_all.py` exited `0`. Its top-level status returns only the stable run's rc; that stable package-only run produced JUnit `tests=952, skipped=40, failures=0, errors=0`, hence `912 passed`; the root `tests/` tree was not included.
- The script's full package-only run had no API key and therefore safely skipped the 9 LLM tests: the separately observed `full rc=0` plus JUnit `tests=961, skipped=49, failures=0, errors=0` establish `912 passed`. It made no real LLM request.
- `reports/phase10/PHASE10_SUMMARY.md` is consistent for the stable scope: its `952 tests` includes 912 passed plus 40 skipped. Its historical full-scope `40 skipped` reflects an authenticated run where 9 LLM tests executed; this run has `49 skipped` because those 9 were deliberately not executed. This is an environment distinction, not a core regression.

`B2_COMPLETE`

- `npm run typecheck` and `npm run lint` each exited `0` with TypeScript `6.0.3` and Oxlint `1.72.0`.
- `npm run build` exited `0` with Vite `8.1.2`; 610 modules were transformed. The main JavaScript chunk is `631.61 kB` (`184.21 kB` gzip), and the main CSS chunk is `42.53 kB` (`13.08 kB` gzip).
- The build retains the known warning that at least one minified chunk exceeds `500 kB`; this is a C4 optimization item, not a Phase B failure.
- `CI=1 npm run e2e` exited `0`: all three Chromium specs passed in `3.9s` (happy path, six result tabs, and initial Ask screen).
- Playwright started a new Uvicorn server and its configuration assigned `PRAXIS_VC_RUNS` from `mktemp -d`. The repository `runs/` path was absent both before and after the run, port 8000 was released, and B2 only generated/updated ignored `dist/`, `test-results/`, and `node_modules/.tmp/*.tsbuildinfo`; the `node_modules/` directory itself already existed from B0.
- The three specs ran against the protected CSS worktree patch `2c300a...aff7e`. They cover navigation, structure, and happy-path API behavior, not pixel/CSS visual acceptance, deep abstain/failed values, or LLM mode.
- No tracked source/manifest changed. The protected CSS patch still hashes to `2c300a185c97f3821edc2e08d91a4d52f6ea1e00bcf52a55f1a1121173eaff7e`.

`B3_COMPLETE`

- `git archive` exported committed HEAD `4ae055c343c146fde133214e8bdcf96605e4fe15` to `/private/tmp`; the archive had no `.git` directory and therefore excluded all protected/untracked WIP.
- `.venv/bin/python -m pip wheel <archive> --no-deps` exited `0` and produced `praxis_virtualcell-0.0.0-py3-none-any.whl`: 712,807 bytes, 439 files, SHA-256 `a52031a770bbb97fcbe8b14d4f5cc008f25ba3f06e661ea04312b0d2eb8967c0`.
- The wheel contains `praxis_virtualcell/cli.py`, `praxis_vc_api/main.py`, VirtualCell brain YAML, cell catalog, model registry, governance JSON artifacts, and `praxis-vc = praxis_virtualcell.cli:main`.
- Wheel metadata and the editable install both report product version `0.0.0`; `.venv/bin/praxis-vc` exists. This agrees internally but conflicts with the local historical `v1.5.0` release tag and remains a C2 versioning task.
- A separate Python 3.12 virtual environment installed the wheel with `--no-deps`. From an empty working directory, the imported package resolved inside that environment's `site-packages`, and `praxis-vc --help` exited `0` with the four declared subcommands. This proves install/import/entry-point wiring only, not dependency resolution or subcommand execution.
- Version gap: wheel/editable metadata `0.0.0` conflicts with the local historical `v1.5.0` tag; this is a C2 version/documentation item.
- Packaging gap: the wheel does not contain `praxis_vc_web/app.py`, although the installed CLI exposes a `web` subcommand that invokes that path. The React `dist/` tree is checkout-built rather than wheel-contained. These are C4 packaging/reproducibility items; Phase B did not alter packaging.

`B4_COMPLETE`

- With real LLM and integration variables explicitly unset, `.venv/bin/pytest tests -m "not llm" -o addopts='' -q -ra` exited `1`: `1136 passed / 163 skipped / 1 failed` in `20.80s`. This is the separate inherited PRAXIS-2/legacy scope and is not counted as the VirtualCell core result.
- All 163 skips are accounted for: 104 integration cases require the explicit Docker/Postgres/Redis integration environment; 37 are missing/invalid inherited skill fixtures; 20 are explicitly quarantined inherited file/HPC cases; and 2 require optional `aiosmtpd` or `rdkit` dependencies.
- The only failure is `tests/test_m9_invariants.py::test_inv5_v1_backend_still_healthy`. TCP port `10.102.106.53:7788` accepted a connection, but `/api/info` returned HTTP 502 to urllib; follow-up curl with and without proxy bypass both reached `10.102.106.53` and received an empty reply (`curl` exit 52). This is `remote operational`, not a local product assertion failure.
- No real LLM request ran. Existing Phase 10 evidence remains authoritative for `.53`: real GEARS/scGPT and Norman mean-baseline remote tests passed on 2026-07-17, while donor `W4B_CKPT_DIR`, Docker smoke, and Gate A true-ML end-to-end validation remain explicitly pending.
- No `.53` repository, process, environment, checkpoint, Docker state, or deployment was changed during B4.

## Phase B completion

`PHASE_B_COMPLETE`

- Baseline report: `reports/quality/BASELINE-2026-07-18.md`
- Evidence parent: `5f359831faf0fba6d7a0c36532862adfe3454e18`
- Completion commit: `42ee96b0390bf1fcc7c8a7d004b3a51368d3672e`
- Independent review: two read-only audits passed after checking all commands, exits, numbers, scope boundaries, links, single C0–C5 ownership, and protected assets.
- Result: core `912/40/9/0`; frontend typecheck/lint/build and 3 E2E pass; Ruff has 13 mapped items; Legacy is `1136/163/1` with the sole failure owned by remote operations.
- External writes: none.

## Phase C improvement progress

`C0_COMPLETE`

- Completion commit: `905d8d6141b18c8e1dac5d72da93b12e95cc1b11`
- Ruff: the 13-item baseline was reproduced after the Phase B gate, then reduced to 0 without new excludes or `noqa` suppressions.
- Change boundary: eight explicit Python files; six safe import/unused-import fixes plus seven behavior-preserving line wraps. Independent AST/assertion review found no executable, scientific, fail-closed, or assertion change.
- Targeted regression: `85 passed / 0 failed`, with the already tracked Starlette/httpx warning.
- Authoritative core regression: `912 passed / 40 skipped / 9 deselected / 0 failed`, with the same single warning.
- Protected assets: four CSS files remained unstaged and retain patch SHA-256 `2c300a185c97f3821edc2e08d91a4d52f6ea1e00bcf52a55f1a1121173eaff7e`.

`C1_COMPLETE`

- Implementation commit: `57bc2581695e9eb48d0f51d3bb8e139f3f19d908`.
- Pytest policy: `integration`, `llm`, `remote`, and `operational` are statically registered and `strict_markers = true` is enabled. Repository-wide `--run-integration`, `--run-llm`, and `--run-remote` flags now make external suites explicit opt-ins; `PRAXIS_INTEGRATION=1` remains a compatibility path.
- Remote boundary: the fixed `10.102.106.53:7788` health invariant is marked `remote` plus `operational`; its socket, HTTP status, and service-name assertions were unchanged. The live LLM integration module is marked `integration`, `llm`, and `remote`, so a normal integration run cannot accidentally invoke it.
- CI policy: `.github/workflows/ci.yml` now has three blocking jobs: Python lint/VirtualCell core, frontend build/Playwright, and isolated legacy unit tests. Integration, LLM, GPU/checkpoint, and private-service execution remain explicit environment-specific gates rather than GitHub-hosted prerequisites.
- Python 3.12 local reproduction: `pip check` and Ruff passed; core remained `912 passed / 40 skipped / 9 deselected / 0 failed` with the existing Starlette/httpx warning; legacy isolation produced `1136 passed / 59 skipped / 105 deselected / 0 failed` and did not execute the `.53` operational probe.
- Fresh Python 3.13 reproduction: editable `.[dev,api,mechanistic]` install and `pip check` passed; Ruff passed; core again produced `912/40/9/0`, and legacy again produced `1136/59/105/0`.
- Node `24.18.0` / npm `11.17.0` reproduction: `npm ci` reported 0 vulnerabilities; typecheck, Oxlint, and Vite build passed; all three Chromium E2E specs passed. The known 631.61 kB main-chunk warning remains owned by C4.
- Configuration validation: strict all-suite collection passed, the fixed private-service test defaulted to one gated skip without a network call, and the live LLM integration module stayed skipped until all relevant opt-ins are present.
- Independent review: PASS for workflow execution paths, hook ordering, marker registration, remote isolation, and unchanged assertions. This is local reproduction evidence only; the branch has not been pushed and no GitHub Actions run is claimed.
- Protected assets: four CSS files remained unstaged and retain patch SHA-256 `2c300a185c97f3821edc2e08d91a4d52f6ea1e00bcf52a55f1a1121173eaff7e`.

`C2_COMPLETE`

- Implementation commit: `73f33246e22157d288829dc95e9ea2bd60ab10c3`; current-documentation commit: `8659c82f644744aeab24219e2f2cab6102afc24a`.
- Version contract: `pyproject.toml` is the sole manually edited product-version source. Installed metadata exposes the local, unreleased `1.5.1` candidate through `praxis_virtualcell.__version__`, the `praxis2` compatibility alias, CLI, FastAPI/OpenAPI, and health. The frontend package/lock is an npm-generated mirror; the UI consumes backend product/build identity.
- Protocol boundary: API `vc.api.v1`, runtime `vc.runtime.v1`, legacy health field `runtime_version="v0.3"`, message/schema/artifact/model versions, and injected build SHA remain separate from the product release.
- Editable verification: `pip check` passed; installed metadata and both package exports reported `1.5.1`; `praxis-vc --version` and `praxis-vc --help` exited `0`.
- Authoritative core regression: `917 passed / 40 skipped / 9 deselected / 0 failed` in `8.71s`, with the same single Starlette/httpx deprecation warning. The five additional passes are version/API contract tests; the frozen Phase 10 report remains `912/40/9`.
- Legacy isolation rerun: `1136 passed / 59 skipped / 105 deselected / 0 failed` in `15.88s`; the `.53` operational probe remained excluded and no real LLM request ran.
- Frontend on Node `26.4.0`: `npm ci` reported 0 vulnerabilities; typecheck, lint, and build passed; all four Chromium E2E specs passed. Main JavaScript remained `631.72 kB` (`184.27 kB` gzip) and CSS `42.53 kB` (`13.08 kB` gzip); the chunk warning stays owned by C4. C1's separate Node 24 evidence covered the earlier three-spec suite, not this four-spec C2 result.
- Clean distribution smoke: `git archive 73f3324` produced `praxis_virtualcell-1.5.1-py3-none-any.whl`, 714,871 bytes, SHA-256 `b571ee71a42d028774221b068a5d0b5a613bcebb456ba655c1a3b4e1d1690580`. A fresh Python 3.13 venv installed it with `--no-deps`; imports, metadata, `--version`, and `--help` passed from an empty working directory. Full dependency/run/API/web/dist/Docker reproduction remains C4.
- Independent reviews: version/API contract review PASS; documentation review PASS after correcting wheel, Streamlit, Docker, environment, and build-time configuration boundaries. All eight current-document links resolve and `git diff --check` passed.
- Publication boundary: no push, PR, merge, tag, deployment, `.53` mutation, or GitHub Actions run occurred. The historical local `v1.5.0` tag was not moved or recreated.
- Protected assets: four CSS files remain unstaged and retain patch SHA-256 `2c300a185c97f3821edc2e08d91a4d52f6ea1e00bcf52a55f1a1121173eaff7e`; `.claude/`, ignored `.playwright-mcp/`, `string.jpeg`, stash, recovery material, and the T7 archive remain preserved.

`C3_COMPLETE_LOCAL`

- Gate: `docs/status/PHASE-C3-GATE-2026-07-18.md`; evidence HEAD `410640360e6d98d399bd53867d8bbb25131dc144`.
- Change range: `afe9fc0..4106403` contains 19 local commits and 49 changed tracked files. The accepted theme is `92ab4ee`; request validation, workflow-race fixes, E2E hardening, the `1.6.0` version decision, and C4 §0 corrections are separately committed.
- Authoritative core rerun: `947 passed / 40 skipped / 9 deselected / 0 failed` in `9.53s`, with the existing Starlette/httpx warning.
- Legacy broad non-LLM rerun: `1136 passed / 158 skipped / 6 deselected / 0 failed` in `16.57s`; this remains a separate inherited scope.
- Frontend: typecheck, lint, build, and `npm audit` passed; audit reported 0 vulnerabilities. The current JS bundle is `635.51 kB` (`185.40 kB` gzip), CSS `40.70 kB` (`12.91 kB` gzip); the >500 kB warning remains C4.
- Playwright: 13 specs / 55 collected = `54 passed / 1 skipped / 0 unexpected / 0 flaky` in `30.34s`. S10 is the deliberately unexecuted real-LLM external gate, not a pass.
- Version surfaces: `pyproject.toml` remains the sole manual source; editable metadata, both Python exports, CLI, npm package and lock root report local candidate `1.6.0`. The C2 `1.5.1` clean wheel stays historical; a clean `1.6.0` wheel is C4.
- Protected assets: theme CSS has no worktree diff and the recovery patch remains archived. `.claude/`, ignored `.playwright-mcp/`, `string.jpeg`, stash, recovery material, and T7 remain unchanged.
- Publication boundary: branch has no upstream. No push, PR, merge, tag, deployment, `.53` mutation, or GitHub Actions run occurred; status remains `KNOWN_DIVERGENCE`.

`C4_COMPLETE_LOCAL`

- Gate: `docs/status/PHASE-C4-GATE-2026-07-18.md`; fixed implementation evidence HEAD `8ce42fe5d167bc4f41bbee596cdc9ab255591056`.
- Change range: `b573f01..8ce42fe` contains 11 local commits covering lazy Results loading and budgets, Python 3.13 hash locks, release data/static packaging, API error redaction, reproducible wheel/container construction, package-test exclusion, and the offline Docker smoke harness.
- Python 3.13.12 locked environment: `pip check` and Ruff passed. Authoritative core `957 passed / 35 skipped / 9 deselected / 0 failed`; legacy CI isolation `1136/59/105/0`; legacy broad non-LLM `1136/158/6/0`.
- Frontend on local Node 26.4.0 / npm 11.17.0: audit, typecheck, lint, build, and bundle budget passed. Initial JavaScript is 226,046 bytes / 70,320 gzip; Results is deferred as 410,889 bytes / 114,914 gzip. Playwright 14 specs / 57 collected = `56 passed / 1 real-LLM skip / 0 failed`.
- Full `1.6.0` release wheel: two clean archive builds were byte-identical at 922,334 bytes, SHA-256 `78e5287a5dd61478b041fd1a28783732cb75a250de02eec306d3803b3128fd4f`; locked clean install, `pip check`, installed console entry/offline outputs, API job, same-origin root/asset, and package-presence checks passed.
- Docker Desktop Linux/arm64: the committed release image built and all five non-root/health/CLI/static/API smoke checks passed with the container on `--network none`; owned resources were cleaned. This is not native Linux/amd64 or `.53` evidence.
- CI configuration now has five jobs (`python-core`, `frontend`, `release-wheel`, `release-container`, `legacy-unit`), but the candidate remains unpushed; no GitHub run or required-check status exists.
- Explicitly unclaimed: complete Streamlit server startup, clean-wheel `praxis-vc ask`, real LLM, `.53` GPU/checkpoints/services, publication, deployment, and any expansion of Phase 10 scientific claims.
- Protected assets and publication boundary remain unchanged: `.claude/`, ignored `.playwright-mcp/`, `string.jpeg`, stash, recovery material, T7 archive, local tags, GitHub, and `.53` were not modified.

## Next authorized work

Continue Phase C5 in this APFS clone:

1. Classify Gate A true-ML end-to-end evidence, W4B checkpoint availability, corpus/rate claims, independent conflict detection, and unsupported-claim detection as `met`, `narrowed`, `unsupported`, or `pending` without changing scientific conclusions.
2. Add local status/asset/runbook documentation and any prerequisite/provenance assertions that can be proven without private checkpoints or remote mutation.
3. Keep current-candidate W4B/GPU/checkpoint execution at its explicit remote gate. Historical paths conflict, so checkpoint presence requires a fresh authorized `.53` check.
4. Complete the C5 local classification gate before preparing Phase D's read-only three-end audit and synchronization proposal.

No external synchronization is authorized before the Phase D approval gate.
