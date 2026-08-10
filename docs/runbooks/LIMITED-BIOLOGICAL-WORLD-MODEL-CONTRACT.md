# P29E Limited Biological World Model Contract Runbook

## Scope and status

This runbook verifies `P29E — limited biological world model / exact empty graph` at code commit
`471767e5f38f9866fbe396f39836369d943f6657` (tree
`d1dec19f06ec88f563406b45f2b544effabad915`, source-date epoch `1786187523`).

- Engineering: `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`
- Science: `NOT_RUN`
- Product policy: `NO_NEW_DECISION`
- Real P29: `BLOCKED / 0_QUALIFYING_BIOLOGICAL_NODES`
- At P29E closure, next eligible local work unit: P30A local RC closure; P30A-E1 subsequently
  completed.
- **E2a follow-on (2026-08-10):** P30A-E2a clean-SHA offline preflight completed
  `COMPLETE_NEGATIVE`; it ran no install, build, OCI, or full gate. P30A-E2b artifact-aware
  trusted finalizer was next at E2a closure; formal P30A remained `LOCAL_RC_INCOMPLETE`, science remained
  `NOT_RUN / SCIENCE_BADGE_INELIGIBLE`, and policy remained `NO_NEW_DECISION`.
- **E2b follow-on (2026-08-10):** P30A-E2b archive-only runner completed
  `COMPLETE_NEGATIVE`: source was stable, but both source archives safely failed on a tracked
  unsupported link and wheelhouse coverage remains incomplete. Formal P30A remains
  `LOCAL_RC_INCOMPLETE`; next is the P16R authorization-preflight identity bridge. Actual P16R
  remains `AUTHORIZATION_REQUIRED / NOT_RUN`.

No real P29 asset, data, model, weight, benchmark, external action, promotion decision, release, push, or
deployment was performed.

## Contract checks

1. Compile only an exact `MultiAgentBiologyCompilationV1`; reject subclasses, undeclared fields,
   `model_copy`/`model_construct` drift, stale nested identities, and non-canonical types.
2. Confirm P28 remains value-free with `qualifying_module_count=0`; advisory and synthetic participants do
   not become P29 biological nodes.
3. Confirm the state/action/observation/time requirement has all scope, state, action, observation, time,
   longitudinal-data, and intervention-data identities `null`.
4. Confirm the graph has empty nodes, edges, and scales; node and edge counts `0`; `connected=false` and
   `connectivity_status=empty_not_connected`; it is neither real nor executable.
5. Confirm all data/model/environment/adapter/compute/benchmark/evidence/policy/result identities, prediction,
   result, tool output, rollout, calibration, OOD, conservation, and counterfactual-consistency fields are
   `null`; execution, science, promotion, and external-action fields are false.
6. Confirm `standalone_replay_result_request_bound=false`. A standalone P27 replay must never be described as
   request-matched or used to create scientific evidence.
7. Confirm the compiler signature has only `p28_compilation`; it must reject caller-supplied nodes, asset paths,
   registries, candidates, LLMs, tools, or arbitrary keyword arguments.

## Local verification

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_limited_world_model.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_multi_agent_biology.py \
  praxis_virtualcell/tests/test_limited_world_model.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -rA \
  praxis_virtualcell/tests/test_limited_world_model.py \
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

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -rA \
  praxis_virtualcell/tests \
  --ignore=praxis_virtualcell/tests/test_mudata_alignment.py \
  -k 'not golden and not gem and not norman'

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -rA \
  tests -m 'not (integration or llm or remote)'

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_packaging.py \
  praxis_virtualcell/tests/test_versioning.py

ruff check praxis_virtualcell/limited_world_model.py \
  praxis_virtualcell/tests/test_limited_world_model.py
ruff format --check praxis_virtualcell/limited_world_model.py \
  praxis_virtualcell/tests/test_limited_world_model.py
python -m py_compile praxis_virtualcell/limited_world_model.py \
  praxis_virtualcell/tests/test_limited_world_model.py

npm --prefix praxis_vc_react run typecheck
npm --prefix praxis_vc_react run lint
npm --prefix praxis_vc_react run build

python -m pip check
git diff --check
```

Recorded counts are focused `51`, P28+P29 `89`, post-commit `117`, affected `390`, safe suite
`1,934 passed / 49 skipped / 387 deselected`, legacy `1,147 passed / 58 skipped / 105 deselected`, and
packaging/versioning `18`.

`pip check` remains an honest failure because the shared environment lacks `python-magic` and retains the
pre-existing `vcbench` pin conflicts; no dependency or environment state was changed. A broad collection
attempt without the explicit `test_mudata_alignment.py` exclusion failed because optional `mudata` is absent
and is not counted as a passing gate.

## Identity caveat

Hashes are content identities, not attestations. A P29 serialized record cannot prove an otherwise unverified
upstream fingerprint exists; the compiler's exact P28 object validation is the executable local boundary.
Do not represent a hash as a signature, registry admission, scientific result, or operator decision.

## Real-P29 gate

A separately authorized real P29 window must first freeze an exact limited biological scope, real connected
adjacent-scale typed subgraph, model/data/weight/environment/compute identities, longitudinal and intervention
data, split/OOD protocol, baselines, primary metric/CI, rollout/calibration/conservation criteria, and external
policy. Until then, all P29 requests abstain. P30A may ship only the honest software surface with P29 disabled
or experimental; it does not change this gate.
