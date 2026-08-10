# ADR-0024: P28E Multi-Agent Biology contract-only orchestration

- Status: Accepted
- Date: 2026-08-08
- Starting SHA: `971f812faae09fa833dc66741e86ec9ffe97947c`
- Completion code SHA: `da4bfc042d96f830e2a7e8cdc62ba227c7ace949`

## Context

P28 real acceptance requires at least three distinct, exact-request model modules that are executable,
scientifically validated, and production promoted. The current repository has zero such modules. P17
synthetic participants, P27 synthetic replay records, legacy rules, and advisory roles cannot satisfy that
gate. P27A-R is still `REPLAY_NOT_RUN / ASSET_PENDING`; P27B and P27C have not run.

The legacy `AgentMessage` and `MessageBus` are mutable, accept free-form payloads, and do not provide the
strict immutable identity closure required here. Reusing them would turn a conformance surface into an
authority surface.

## Decision

P28E adds an isolated strict module with six public records:

1. `vc.multi-agent-role-policy.v1`;
2. `vc.multi-agent-handoff.v1`;
3. `vc.multi-agent-dag.v1`;
4. `vc.multi-agent-trace-event.v1`;
5. `vc.multi-agent-trace.v1`;
6. `vc.multi-agent-biology-compilation.v1`.

`vc.multi-agent-value-free-handoff.v1` is a declared null I/O contract and
`vc.multi-agent-trace-root.v1` is a canonical fingerprint payload. Neither is an additional public model.

Role policies freeze schema allowlists, permissions, handoff budget, timeout, retry, concurrency,
cancellation, and a local contract-only resource class. Network, filesystem writes, subprocesses, devices,
dynamic tools, external actions, and numerical output are always forbidden. Advisory roles are explicitly
`counts_for_real_acceptance=false`.

Typed handoffs carry one exact input fingerprint and no payload, prediction, numerical result, evidence, or
policy. A DAG binds the exact P17 compilation, P27 experiment, and P27 replay fingerprints. External handoff
schema identities must equal the corresponding DAG identity; an internal handoff must reference an exact
declared predecessor. Roles and handoffs are canonical, budgeted, and acyclic.

The no-run trace is predecessor-hashed and must contain exactly one event for each DAG handoff. A separate
DAG/trace cross-check prevents a self-consistent re-signed trace from claiming a handoff absent from the DAG.
Content hashes provide identity, not signer authentication.

The authoritative compiler has no caller-supplied role, module, candidate, registry, tool, or LLM surface.
It accepts an exact same-request P17 compilation and P27 experiment plus an exact standalone P27 replay-result
identity, then emits an empty authoritative DAG and trace. `ReplayResultV1` carries no request/experiment
binding, so the replay identity is not described as request-matched:

- qualifying modules `0/3`;
- roles, handoffs, events, and execution steps empty;
- prediction, result, and tool output null;
- executable, execution, external action, science, promotion, comparison, and ablation false/not run;
- conflict and partial failure `not_evaluated_no_execution`;
- deterministic abstention.

Synthetic advisory role/handoff/trace records test only the contract. They are excluded from the
authoritative compilation and from real P28 acceptance.

## Consequences

- Engineering is `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`.
- Synthetic fixture evidence is `SYNTHETIC_CONFORMANCE_ONLY`.
- Science is `NOT_RUN`; product policy is `NO_NEW_DECISION`.
- Real P28 remains `BLOCKED / 0_OF_3_QUALIFYING_MODULES`.
- Single-agent/monolithic/multi-agent comparison, ablation, conflict resolution, failure recovery, and real
  execution were not run and cannot be inferred from the schemas.
- No legacy bus, default runtime, API, registry-positive path, LLM, network, asset, or device integration was
  added.

At P28E closure, P29E was the next local unit and could define only a strict connected-subgraph contract plus
authoritative empty-graph/value-free abstention. P29E subsequently completed at
`471767e5f38f9866fbe396f39836369d943f6657` with `empty_not_connected`, zero nodes/edges and no
placeholder scale chain. Real P29 remains separately gated. P30A-E1 release-contract hardening
subsequently completed.

**E2a follow-on (2026-08-10):** P30A-E2a clean-SHA offline preflight completed
`COMPLETE_NEGATIVE`; it ran no install, build, OCI, or full gate. P30A-E2b artifact-aware
finalizer was next at E2a closure, while formal P30A remained `LOCAL_RC_INCOMPLETE`, science remained
`NOT_RUN / SCIENCE_BADGE_INELIGIBLE`, and policy remained `NO_NEW_DECISION`.

**E2b follow-on (2026-08-10):** P30A-E2b archive-only runner also completed
`COMPLETE_NEGATIVE`: source was stable, but both source archives safely failed on a tracked
unsupported link and wheelhouse coverage remains incomplete. Formal P30A remains
`LOCAL_RC_INCOMPLETE`; at E2b closure, the next local unit was the P16R authorization-preflight identity bridge.
Actual P16R remains `AUTHORIZATION_REQUIRED / NOT_RUN`; science and policy remain unchanged.

**P16R-PREFLIGHT follow-on (2026-08-10):** the local authorization-preflight identity bridge
subsequently completed `COMPLETE — IDENTITY_PREFLIGHT_ONLY` at
`4f77255f84e33180d7d73b421fc9737ca3a1121d`. It binds declarations only and fixed value-free
abstention; it does not read assets, run a model/benchmark, create evidence or policy, or alter
runtime/registry exposure. Actual P16R remains `AUTHORIZATION_REQUIRED / NOT_RUN`, science remains
`NOT_RUN`, policy remains `NO_NEW_DECISION`, and the local queue is `BLOCKED_EXTERNAL`.
