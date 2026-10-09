# Phase 28E completion: contract-only Multi-Agent Biology

| Field | Exact value |
|---|---|
| Work unit | `P28E — exact P17/P27 input × advisory-only typed handoff/DAG/trace × authoritative 0/3 abstention` |
| Starting SHA | `971f812faae09fa833dc66741e86ec9ffe97947c` |
| Completion code SHA | `da4bfc042d96f830e2a7e8cdc62ba227c7ace949` |
| Completion tree | `e6f18371f5061c810b2cb87d9a278cfa6d6ac46b` |
| Source date epoch | `1786184568` |
| Branch | `codex/p25e-virtual-microbiome` |
| Outcome | `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION` |

## 1. Scope and result

P28E implements strict role policy, typed value-free handoff, deterministic advisory DAG, hash-chained no-run
trace, and an authoritative compilation. The authoritative output binds the P17 compilation and P27 experiment
to one request and separately binds the exact standalone P27 replay-result fingerprint, but exposes no
caller-supplied module, role, registry, candidate, tool, or LLM surface. `ReplayResultV1` has no request or
experiment binding, so P28E does not call that replay request-matched.

Current qualifying model modules are exactly `0/3`. Authoritative roles, handoffs, events, and execution steps
are empty; prediction, result, and tool output are null; execution, external action, science, promotion,
comparison, and ablation are false/not run. The result deterministically abstains.

Synthetic advisory role/handoff/trace fixtures validate the contract only and have
`counts_for_real_acceptance=false`. Legacy `AgentMessage`/`MessageBus` bytes and runtime wiring were not changed
or reused.

## 2. Schemas and trust boundaries

Six public strict records were added:

```text
vc.multi-agent-role-policy.v1
vc.multi-agent-handoff.v1
vc.multi-agent-dag.v1
vc.multi-agent-trace-event.v1
vc.multi-agent-trace.v1
vc.multi-agent-biology-compilation.v1
```

`vc.multi-agent-value-free-handoff.v1` is a null I/O contract version and
`vc.multi-agent-trace-root.v1` is a fingerprint payload version, not a seventh/eighth public model.

Exact protections include recursive type revalidation, canonical role/handoff ordering, permission and
resource literals, per-role handoff budget, acyclicity, external schema→upstream fingerprint binding, internal
predecessor binding, predecessor-hash trace closure, and an exact DAG↔trace handoff-set cross-check. Recomputing
a content hash cannot override semantic false/null literals.

## 3. Immutable fingerprints

| Artifact | Identity |
|---|---|
| module SHA-256 | `aadb8fba6efb943799cfa8d9f296f2a7e03f27d45d52d22ce3e1b67b94b160ca` |
| test SHA-256 | `23097c5a71324ffa5ce51bab925b58abce71b3e8d0a3848542d2174867ba50b7` |
| exact request fingerprint | `672f5072e2ae228c8ae66f3b198f3a08201c7605e90670384cc6b46e9e56e26f` |
| P17 compilation fingerprint | `1fa2b4f1030f9d4377c972c96210ca92fdc32b8556a8b7a38165ceb633efc970` |
| P27 experiment ID / fingerprint | `experiment_45a7d9838bc76c90dc929ca4` / `f30f9c73889544510ce784b2cbb75a461437024e8dbd0d0c949fe130d50231c7` |
| P27 replay result ID / fingerprint | `replay_result_9404a25fee5814291d2561ea` / `dda3876805303b0194647ec2a8d3b628ffde87b4ed614c3a1370d466c43d5161` |
| authoritative empty DAG fingerprint | `fa0f40f57af4364870e9884eac658f0361208c02b133e5bbf2fd35833c17f1a9` |
| authoritative empty trace ID / fingerprint | `trace_6f080fbc821bb3aeb55916d9` / `06dd36af11f94458aea816d987bec09ac01530a2467aba9a07ed1dd3a3c72cb5` |
| compilation ID / fingerprint | `ma_comp_d33129a47f1942d913b7fe49` / `c68bee6068ce176bd5c3b610a46fcf92757abcc8a827502fb1df806b795ecc02` |

Synthetic advisory conformance identities:

| Record | Identity |
|---|---|
| cell role fingerprint | `8ce0297c8323f083b67703ba99bf56e73b163eb0a73151aed5126d12db6a9417` |
| literature role fingerprint | `08e66d2a0d6382a198b301e0c59df7a53cffe0c541c2d922ee9de2c9608351a9` |
| handoff ID / fingerprint | `handoff_8bcb6ce026d70ea1529c2de9` / `e007337e5ec48d0158e2c5dfe9135bc0868fbbbfd6ef086c443cfc40997e5813` |
| advisory DAG fingerprint | `987ccbd88d56d4bd36973ee49e565b6f0a7a4998455b39fe153054a901f5a38f` |
| trace ID / fingerprint | `trace_5a95c5f250c0623216fd6913` / `14f38c712ab10f62c9844630421ea992000b012eca6f749b99102319dea35c35` |
| trace event ID / fingerprint | `event_0ae6c68287ff3817bbaa274a` / `4d474acb64dc9cd17a1c335580b55979587d1aa98f1a70fa1a0f68bb9aa1a06b` |

These fixture identities are `SYNTHETIC_CONFORMANCE_ONLY`, not evidence, execution, or policy.

## 4. Verification matrix

| Gate | Result |
|---|---|
| P28E focused | `38 passed` |
| P28E + P17/P27/request/capability/benchmark/adapter/ActiveLearning affected | `339 passed` |
| safe local suite | `1,883 passed, 49 skipped, 387 deselected in 419.19s` |
| legacy suite | `1,147 passed, 58 skipped, 105 deselected in 51.29s` |
| packaging + versioning | `18 passed` |
| full Ruff / targeted format / compile / diff | passed |
| React typecheck / lint / build / bundle budget | passed |
| `pip check` | failed: shared environment lacks `python-magic` and has pre-existing `vcbench` pin conflicts; no environment mutation |

Adversarial coverage includes wrong external input fingerprints, missing internal predecessors, undeclared or
duplicate roles, cycles, handoff-budget overflow, payload/value/evidence/policy injection, foreign re-signed
trace events, nested subclass/`model_construct` drift, synthetic participant laundering, status elevation,
secret/path echo, and closed LLM/module/registry inputs.

## 5. Local package evidence

Two fresh exact-code `git archive` trees used offline npm and the installed Python toolchain with no isolation
or dependency resolution. The wheels are byte-identical:

| Property | Exact value |
|---|---|
| product/distribution version | `1.6.0` — unchanged |
| filename | `praxis_virtualcell-1.6.0-py3-none-any.whl` |
| size | `1,259,255` bytes |
| SHA-256 | `0358bf4df9e929be7c520e93f7c95dccc351895e7926773b53de8febf7eaec9f` |
| ZIP entries | `377` |
| React entries | `14` |
| test / AppleDouble entries | `0 / 0` |
| source/wheel module SHA-256 | exact match |
| toolchain | Python `3.13.12`; build `1.5.0`; setuptools `70.2.0`; packaging `26.0`; Node `25.8.2`; npm `11.11.1`; Vite `8.1.2` |
| SBOM / license inventory | `NOT_RUN` — formal P30A work |

This is exact-source local reproducibility, not a pinned dependency closure, clean install, signed artifact,
release candidate, publication, staging, production, or science evidence. The initial npm `--prefix` attempt
failed and the required-static build gate rejected the missing frontend. That rejected attempt is not package
evidence; only the two subsequent clean archive builds count.

## 6. Engineering, science, and policy ledger

| Plane | Status |
|---|---|
| Engineering | `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION` |
| Fixture evidence | `SYNTHETIC_CONFORMANCE_ONLY` |
| Real P28 acceptance | `BLOCKED / 0_OF_3_QUALIFYING_MODULES` |
| Scientific status | `NOT_RUN` |
| Product policy | `NO_NEW_DECISION` |
| comparison / ablation | `NOT_RUN` |

No real model, asset, benchmark, comparison, ablation, conflict resolution, failure recovery, external action,
scientific evidence, policy, promotion, push, release, deployment, `.53`, PRAXIS-2, `old/**`, or protected ref
was touched.

## 7. Known limitations and next work

P28E does not demonstrate multi-model execution, better science, lower cost, higher coverage, fault recovery,
conflict resolution, or autonomous research. Its P27 replay input is identity-bound but not request-bound;
P27A-R/B/C remain at their prior gates. Real P28 requires three
exact-request executable, scientifically validated, production-promoted model modules and separately frozen
comparison/ablation evidence.

The next eligible local work unit is P29E strict state/action/observation/time and connected-subgraph contracts
plus authoritative empty-graph/value-free abstention; no empty graph is represented as connected. Current
qualified biological nodes are zero, so a real connected subgraph remains blocked and no molecule→organism
placeholder chain may be fabricated.
