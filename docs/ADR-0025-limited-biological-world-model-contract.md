# ADR-0025: Limited Biological World Model Contract

**Status:** accepted — P29E contract-only closure
**Date:** 2026-08-08
**Work unit:** `P29E — limited biological world model / exact empty graph`
**Code commit:** `471767e5f38f9866fbe396f39836369d943f6657`
**Tree:** `d1dec19f06ec88f563406b45f2b544effabad915`

## Decision

P29E defines only strict, deterministic records for the prerequisites of a limited biological world model. It
does not create a biological world model candidate, run a model, load an asset, or manufacture a connected
graph. The authoritative P29E result is an empty graph whose connectivity status is exactly
`empty_not_connected`.

The public contracts are:

1. `vc.state-action-observation-time-requirement.v1` — exact P28 compilation identity, with scope, state,
   action, observation, time, longitudinal-data, and intervention-data identities all `null`;
2. `vc.connected-typed-subgraph.v1` — nodes, edges, and scales empty; qualifying biological-node count and
   adjacent-scale-edge count `0`; `connected=false`, `real_biological_subgraph=false`, and
   `executable=false`;
3. `vc.limited-world-model-compilation.v1` — binds the first two records and the exact P28 compilation
   fingerprint, with data/weight/model/environment/adapter/compute/benchmark/evidence/policy/result
   fingerprints and every value-bearing output `null`.

The sole compiler input is an exact, recursively revalidated `MultiAgentBiologyCompilationV1`. It admits no
node, edge, asset path, registry, candidate, tool, or LLM parameter. P28 itself remains value-free at `0/3`
qualifying modules; synthetic or advisory records cannot be converted into biological nodes.

## Consequences and non-goals

- An empty graph is not treated as connected, even vacuously. No molecule, protein, cell, community, or
  organism placeholder node or edge is emitted.
- The P27 replay reference inherited through P28 remains a standalone identity; it is explicitly not
  request-bound and cannot become evidence, a result, or a promotion input.
- The compilation deterministically abstains with canonical reasons for missing P28 qualifying modules,
  missing state/action/observation/time identities, missing real adjacent-scale subgraph, and no authorized
  P29 data/model/benchmark run.
- Engineering is `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`; science is `NOT_RUN`; product policy
  is `NO_NEW_DECISION`. The real P29 candidate remains `BLOCKED / 0_QUALIFYING_BIOLOGICAL_NODES`.
- P29E is not a benchmark, longitudinal/intervention analysis, causal claim, rollout, calibration, OOD
  evaluation, conservation result, general life model, or arbitrary-cell predictor.

## Identity boundary

Content hashes identify exact bytes; they are not a signature, registry attestation, or proof that an arbitrary
claimed upstream fingerprint exists. Compiler-time input is recursively validated as an exact P28 object.
Serialized P29 records retain content-hash provenance only and must not be described as authenticated
attestation without a separately governed registry/signature mechanism.

## Evidence and handoff

The implementation is `praxis_virtualcell/limited_world_model.py`
(`b730220099b36df99f7ba706be7dea6174b1c41329b62526dc45bda475c155ae`) and its conformance suite is
`praxis_virtualcell/tests/test_limited_world_model.py`
(`43dee397437bf779fdab79726090b2f84538ad331a6bb1bd0abd2b37b844391f`). See
[the P29E completion report](../reports/phase29e/PHASE29E_COMPLETION.md).

At P29E closure, P30A local RC closure was the next eligible local work unit. P30A-E1
release-contract hardening subsequently completed.

**E2a follow-on (2026-08-10):** P30A-E2a clean-SHA offline preflight completed
`COMPLETE_NEGATIVE`; it ran no install, build, OCI, or full gate. At E2a closure, the next eligible local
work unit was P30A-E2b artifact-aware finalizer, while formal P30A remained
`LOCAL_RC_INCOMPLETE`, science remained `NOT_RUN / SCIENCE_BADGE_INELIGIBLE`, and policy remained
`NO_NEW_DECISION`. P30 may classify P29 as unsupported/experimental; it cannot infer a
science-qualified capability badge from this contract-only result.

**E2b follow-on (2026-08-10):** P30A-E2b archive-only runner completed
`COMPLETE_NEGATIVE`: source was stable, but both source archives safely failed on a tracked
unsupported link and wheelhouse coverage remains incomplete. Formal P30A remains
`LOCAL_RC_INCOMPLETE`; at E2b closure, the next local unit was the P16R authorization-preflight identity
bridge. Actual P16R remains `AUTHORIZATION_REQUIRED / NOT_RUN`; P29 remains contract-only and
cannot imply a science-qualified capability badge.

**P16R-PREFLIGHT follow-on (2026-08-10):** the local authorization-preflight identity bridge
subsequently completed `COMPLETE — IDENTITY_PREFLIGHT_ONLY` at
`4f77255f84e33180d7d73b421fc9737ca3a1121d`. It preserves P29's non-claim boundary: declarations
and fixed abstention only, with no asset I/O, candidate/comparator execution, benchmark evidence,
policy, registry/runtime route, release, or promotion. Actual P16R remains
`AUTHORIZATION_REQUIRED / NOT_RUN`; science remains `NOT_RUN`, policy remains `NO_NEW_DECISION`,
and the local queue is `BLOCKED_EXTERNAL`.
