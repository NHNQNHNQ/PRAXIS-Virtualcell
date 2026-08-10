# P28E Multi-Agent Biology contract runbook

This runbook verifies the local contract-only P28E surface. It does not authorize or run real multi-agent
models, comparison/ablation, external tools, P27B/P27C, network access, training, deployment, or policy.

## Status ceiling

- Engineering: `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`
- Fixture: `SYNTHETIC_CONFORMANCE_ONLY`
- Real acceptance: `BLOCKED / 0_OF_3_QUALIFYING_MODULES`
- Science: `NOT_RUN`
- Product policy: `NO_NEW_DECISION`
- Comparison / ablation: `NOT_RUN`

The authoritative compilation always has zero roles, handoffs, trace events, execution steps, and qualifying
modules. Prediction/result/tool output are null. Advisory conformance records never count as model modules.
P17 compilation and P27 experiment are exact same-request records. The exact P27 replay-result fingerprint is
bound separately; `ReplayResultV1` has no request/experiment link, so do not describe it as request-matched.

## Public contracts

The six public schemas are:

```text
vc.multi-agent-role-policy.v1
vc.multi-agent-handoff.v1
vc.multi-agent-dag.v1
vc.multi-agent-trace-event.v1
vc.multi-agent-trace.v1
vc.multi-agent-biology-compilation.v1
```

`vc.multi-agent-value-free-handoff.v1` names the null I/O contract and
`vc.multi-agent-trace-root.v1` names the trace-root fingerprint payload; neither is a public record model.

## Directed verification

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_multi_agent_biology.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -rA \
  praxis_virtualcell/tests/test_multi_agent_biology.py \
  praxis_virtualcell/tests/test_virtual_experiment.py \
  praxis_virtualcell/tests/test_experiment_design_replay.py \
  praxis_virtualcell/tests/test_request_v2.py \
  praxis_virtualcell/tests/test_capability_runtime.py \
  praxis_virtualcell/tests/test_benchmark_system.py \
  praxis_virtualcell/tests/test_model_adapter_sdk.py \
  praxis_virtualcell/tests/test_active_learning_agent.py \
  praxis_virtualcell/tests/test_runtime_active_learning.py \
  praxis_virtualcell/tests/test_report_active_learning_request.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_packaging.py \
  praxis_virtualcell/tests/test_versioning.py

python -m ruff check . --extend-exclude old --no-cache
python -m ruff format --check \
  praxis_virtualcell/multi_agent_biology.py \
  praxis_virtualcell/tests/test_multi_agent_biology.py
python -m py_compile \
  praxis_virtualcell/multi_agent_biology.py \
  praxis_virtualcell/tests/test_multi_agent_biology.py
git diff --check
```

Expected exact completion-code results:

| Gate | Result |
|---|---|
| focused | `38 passed` |
| affected ten-test-file suite | `339 passed` |
| safe suite | `1,883 passed / 49 skipped / 387 deselected / 419.19s` |
| legacy suite | `1,147 passed / 58 skipped / 105 deselected / 51.29s` |
| packaging + versioning | `18 passed` |
| Ruff / format / compile / diff | PASS |
| React typecheck / lint / build / budget | PASS |
| `pip check` | shared-environment FAIL: missing `python-magic` + pre-existing `vcbench` pin conflicts; do not mutate the environment |

## Fail-closed audit

Verify all of the following remain rejected:

- external schema paired with the wrong P17/P27/replay fingerprint;
- internal handoff without an exact declared predecessor;
- undeclared/duplicate role, self-edge, cycle, or fifth outgoing handoff;
- payload, prediction, numerical result, evidence, policy, tool or external-action injection;
- re-signed trace that names a handoff absent from its bound DAG;
- nested subclass or `model_construct` type drift;
- P17 synthetic participants or advisory/rule records counted toward the real `3`-module gate;
- re-signed qualifying count, executable, science, promotion, conflict, partial-failure, comparison, or
  ablation claims;
- LLM/candidate/module/registry kwargs or request prose/secret/path echo.

## Local package evidence

Two fresh `git archive` trees of code commit `da4bfc042d96f830e2a7e8cdc62ba227c7ace949`
were built with `SOURCE_DATE_EPOCH=1786184568`, `npm ci --offline`, and Python
`--no-isolation --skip-dependency-check`. The wheels were byte-identical:

```text
praxis_virtualcell-1.6.0-py3-none-any.whl
size       1,259,255 bytes
sha256     0358bf4df9e929be7c520e93f7c95dccc351895e7926773b53de8febf7eaec9f
entries    377
React      14
tests      0
AppleDouble 0
```

The source/wheel module SHA-256 is
`aadb8fba6efb943799cfa8d9f296f2a7e03f27d45d52d22ce3e1b67b94b160ca`.
This is exact-local-source/toolchain evidence, not a clean dependency closure, RC, publication, release, or
science evidence. A preliminary build intentionally failed the required-static gate after npm 11 misapplied
`--prefix`; it produced no accepted artifact. Only the two subsequent clean archive builds are evidence.

## Interpretation and next gate

Do not describe P28E as multi-model execution, conflict recovery, scientific comparison, autonomous research,
or production orchestration. Real P28 requires three exact-request executable, scientifically validated, and
production-promoted model modules plus frozen comparison/ablation evidence.

At P28E closure, the next local work unit was P29E strict connected-subgraph contract plus authoritative
empty-graph/value-free abstention. P29E subsequently completed at
`471767e5f38f9866fbe396f39836369d943f6657` with `empty_not_connected`, zero nodes/edges and no
placeholder scale chain. A real connected biological subgraph remains unavailable. P30A-E1
release-contract hardening subsequently completed.

**E2a follow-on (2026-08-10):** P30A-E2a clean-SHA offline preflight completed
`COMPLETE_NEGATIVE`; it ran no install, build, OCI, or full gate. P30A-E2b artifact-aware trusted
finalizer was next at E2a closure, while formal P30A remained `LOCAL_RC_INCOMPLETE`, science remained
`NOT_RUN / SCIENCE_BADGE_INELIGIBLE`, and policy remained `NO_NEW_DECISION`.

**E2b follow-on (2026-08-10):** P30A-E2b archive-only runner completed
`COMPLETE_NEGATIVE`: source was stable, but both source archives safely failed on a tracked
unsupported link and wheelhouse coverage remains incomplete. Formal P30A remains
`LOCAL_RC_INCOMPLETE`; next is the P16R authorization-preflight identity bridge. Actual P16R
remains `AUTHORIZATION_REQUIRED / NOT_RUN`; science and policy remain unchanged.
