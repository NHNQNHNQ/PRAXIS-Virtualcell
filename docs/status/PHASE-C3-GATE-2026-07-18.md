# PRAXIS-VirtualCell Phase C3 Completion Gate — 2026-07-18

> Status: `C3_COMPLETE_LOCAL`
>
> Evidence head: `410640360e6d98d399bd53867d8bbb25131dc144`
>
> Product candidate: `1.6.0_LOCAL_CANDIDATE_UNPUBLISHED`
>
> Synchronization: `KNOWN_DIVERGENCE`

This gate closes the local theme and full-E2E improvement unit. It does not publish, deploy, or synchronize the candidate. GitHub and `.53` remain at their separately recorded last-observed states in `SYNC-STATE.md`.

## Change boundary

- Base: C2 gate commit `afe9fc0`.
- Evidence range: `afe9fc0..4106403` = 19 local commits, 49 changed tracked files.
- Theme: accessible light/dark themes accepted in `92ab4ee`; Newsreader was removed from the generated npm manifest/lock mirror.
- UI: stage scroll, Results toolbar, export/copy behavior, presets, history switching, responsive reachability, and actual `data-theme` behavior were exercised and corrected.
- Workflow safety: Ask/Review/Run/Results late-response and navigation races are guarded; invalid editable fields require actual correction; historical result requests cannot overwrite the current job.
- Request boundary: explicit `结构化描述:` input is strict, LLM candidates remain tolerant, `/api/parse` responses are JSON/UTF-8/structure safe, and API `run_job` executes/saves only the validator-normalized top-level request.
- Version: the accepted user-visible scope promoted the never-published `1.5.1` patch candidate to local minor candidate `1.6.0` in `b5dfc80`. API/runtime/message/governance/model namespaces did not change.

No scientific claim, reliability decision rule, governance artifact, local milestone tag, `main`, stash, T7 archive, GitHub ref, or `.53` state was changed by C3.

## Final local verification

| Layer | Command / method | Result |
|---|---|---|
| Python dependency | `.venv/bin/python -m pip check` | PASS; no broken requirements |
| Python lint | `.venv/bin/ruff check .` | PASS; 0 diagnostics |
| Core | `.venv/bin/python -m pytest praxis_virtualcell/tests -m "not llm" -o addopts='' -q -ra` | `947 passed / 40 skipped / 9 deselected / 0 failed`; one existing Starlette/httpx warning; `9.53s` |
| Legacy broad non-LLM | `.venv/bin/python -m pytest tests -m "not llm" -o addopts='' -q -ra` | `1136 passed / 158 skipped / 6 deselected / 0 failed`; `16.57s`; separate scope, not added to core |
| Version/API | version contract plus health targeted run | `6 passed / 0 failed`; metadata, both Python exports, CLI and npm mirror all reported `1.6.0` |
| Frontend static | `npm run typecheck` and `npm run lint` | PASS |
| Frontend build | `npm run build` | PASS; JS `635.51 kB` (`185.40 kB` gzip), CSS `40.70 kB` (`12.91 kB` gzip) |
| Dependency audit | `npm audit` | PASS; 0 vulnerabilities |
| Playwright | 13 specs / 55 collected, JSON reporter | `54 expected / 1 skipped / 0 unexpected / 0 flaky`; `30.34s` |
| Patch hygiene | `git diff --check` | PASS |

The Vite chunk warning over 500 kB remains a measured C4 item. The clean `1.5.1` wheel recorded in C2 is historical evidence; a clean `1.6.0` wheel has not yet been built and belongs to C4.

## E2E and visual acceptance

- Local suites implement S1–S9 and S11–S13 across abstain states, hostile input, perturbation matrices, advanced fields, result artifacts, theme/history, presets, repeatability, responsive stage flow, and stability.
- S10 is an honest, always-explicit skip until a real LLM credential, opt-in, and authorization are present. It was not executed and must not be reported as passed.
- Light/dark visual review accepted the C3 theme; tests also verify the actual root `data-theme` value and complete workflow reachability in both theme contexts.
- The Results toolbar regression intentionally uses a narrow 1280×720 `.card-actions` plus `getBoundingClientRect()` geometry assertion because it protects a reproduced overlap bug. S12 mobile/tablet checks use viewport changes to prove semantic reachability, not pixel equivalence.
- Playwright collectors await report, trace, provenance, and module-plan requests and monitor console, page, and service failures. They do not convert expected external gates into passes.

## Mutation and adversarial evidence

Representative red-to-green or mutation checks covered:

- stale parse success/failure after the Ask draft or mode changes;
- pending Run rail navigation and late completion;
- object targets becoming `"[object Object]"`;
- editable Review errors and options-service fallback;
- deep/surrogate/NaN/oversized parse candidates;
- explicit unsupported outputs and mixed target types;
- expected boolean inversions and step-count changes in E2E collectors.

Independent read-only reviews found no remaining C3 P1/P2 blocker. Supplemental review audits exercised 139 directed backend checks, 125 schema/runtime/module checks, 1,092 API fuzz cases, and 2,000 validator fuzz cases with zero observed failure. The fuzz figures are review-time sampling evidence, not a checked-in deterministic CI gate.

## Honest residuals and next owner

- Real LLM E2E S10 remains pending explicit opt-in and authorization.
- Starting a new query or opening history during a pending Run can leave a backend-completed job whose sidebar is not refreshed immediately; the displayed task remains race-safe.
- If `/api/options` fails, local correction of species/type is permissive and final legality depends on `/api/jobs` validation.
- `/api/jobs` still exposes `detail=str(e)` for some failures; information-leak hardening remains C4.
- API `run_job` is normalized-only; direct `run_query` and `praxis-vc run` are outside that claim.
- Bundle splitting, Python constraints, clean `1.6.0` wheel/API/web/dist/Docker reproduction, Linux Docker smoke, and FastAPI/Starlette/TestClient deprecation work remain C4.
- Checkpoint/GPU/scientific remote items remain C5 and are not made true by local E2E.

## Gate decision

`C3_COMPLETE_LOCAL`

C3 may hand off to C4. The branch has no upstream and remains intentionally local-only. No push, PR, merge, tag, deployment, `.53` mutation, or GitHub Actions result is claimed. Phase D still requires a fresh three-end read, an exact synchronization plan, and explicit user authorization before any external write.
