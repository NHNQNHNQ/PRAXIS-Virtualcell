# Phase 12 — Virtual Cell Model Zoo v2 completion

Work unit: `P12 — Virtual Cell Model Zoo v2 / governed exact request×Pack×release gate`

Outcome: `ENGINEERING_COMPLETE`

Starting SHA: `b19c896202bea56f894d0ad540501331af42a40c`

Completion code SHA: `1a5464fb0d2d9e105058f6797d92efd69783e5b2`

Completion tree: `a1823bfa6a1f0d694c0558fbf4bd0f93ef2d83f0`

Branch at completion: `codex/p12-model-registry-v2`

## Scope and protected state

P12 added immutable artifact, environment, adapter, evidence, operator-policy, release and
lifecycle identities; conservative v1 migration; exact Pack-aware compatibility/execution gates;
path-redacted read projections; and v2 job identity. It did not download or run weights, train a
model, access remote services, create scientific evidence, or make an operator promotion decision.

The observed implementation diff is the exact 27-path diff from the starting SHA to the completion
code SHA: `README.md`; `docs/ADR-0009-virtualcell-model-zoo-v2.md`;
`docs/HANDOFF-P10-TO-NEXT-CONVERSATION.md`; `docs/INDEX.md`;
`docs/PHASE0-10-SUMMARY-AND-REMAINING-WORK.md`; `docs/PHASE11A-DATA-CENTRIC-UI-DESIGN.md`;
`docs/PHASE12-30-DETAILED-COMPLETION-CHECKLIST.md`;
`docs/PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md`; `docs/PHASE12-30-MASTER-PROMPT.md`;
`docs/PHASE12-30-SEQUENTIAL-MASTER-PROMPT.md`;
`docs/PRAXIS-VIRTUALCELL-CURRENT-PROJECT-AND-INTEGRATION-GUIDE.md`; `docs/TESTING.md`;
`docs/VERSIONING.md`; `docs/VIRTUALCELLPACK-CAPABILITY-MATRIX.md`;
`docs/runbooks/VIRTUALCELL-MODEL-ZOO-V2.md`; `praxis_virtualcell/agents/model_broker_agent.py`;
`praxis_virtualcell/io/job_store.py`; `praxis_virtualcell/model_zoo/cache.py`;
`praxis_virtualcell/model_zoo/capability_registry.py`; `praxis_virtualcell/model_zoo/registry.py`;
`praxis_virtualcell/model_zoo/registry_v2.py`; `praxis_virtualcell/pack_product.py`;
`praxis_virtualcell/tests/fixtures/model_registry_v2/legacy_migration.json`;
`praxis_virtualcell/tests/test_capability_runtime.py`;
`praxis_virtualcell/tests/test_model_registry_v2.py`; `praxis_virtualcell/tests/test_pack_product.py`;
and `praxis_virtualcell/tests/test_packaging.py`.

No staged, modified, deleted, or untracked paths existed before the completion audit. `old/**`, the
three protected repository copies, remote refs, GitHub, `.53`, services, ports, external assets and
existing deployment state were not modified.

## Contracts and immutable identities

The completed engineering contracts are:

- `vc.model-artifact.v1`, `vc.model-environment.v1`, `vc.model-adapter.v1`;
- `vc.model-validation-evidence.v1`, `vc.model-operator-policy.v1`;
- `vc.model-release.v1`, `vc.model-registry-event.v1`, `vc.model-registry-state.v1`;
- `vc.model-registry.v2`, `vc.model-registry-catalog.v2`;
- `vc.environment.v2`, `vc.compatibility-report.v2`, `vc.execution-step.v2`,
  `vc.execution-plan.v2`, and `vc.job-execution-identity.v2`.

The legacy migration fixture SHA-256 is
`bfb8ac5c730d1ea5a42e5155b98ffcc12bc884b05ef20aeccdef9a34cb06f4e3`. Its inputs remain:

- v1 model registry: `435651dcb74b22e5a6091ddfc93ba8aa151fbf3926035e3aeb9cb6a49af463fc`;
- P8 manifest: `724b701beda574ad344b764de09dafb86648e49c9a327df717212aaf25cc71ac`;
- P9 negative result: `abd1145c434fd4e48ac9d72e94e8e19d14a5b4011f03d05db4823dd91760da6e`.

Migration admits no evidence or policy, preserves P9 `available=false`, and leaves all migrated
Pack-aware releases non-executable.

## Validation bound to completion bytes

All commands ran locally without network, external assets, weights, training, LLM, GPU or remote
services. The post-commit audit observed a clean worktree before and after validation.

- Model Registry v2 contract file: `60 passed`.
- Five-file P12 directed gate: `184 passed`.
- VirtualCell core, excluding the explicit LLM gate: `1388 passed`, `35 skipped`, `9 deselected`.
- Legacy unit gate, excluding integration/LLM/remote: `1146 passed`, `59 skipped`, `105 deselected`.
- Packaging regression: `13 passed`.
- P12 Ruff scope: passed.
- Frontend `typecheck`, `lint`, `build`, and bundle budget: passed; no frontend bytes changed in P12,
  so no service-backed E2E was used as P12 completion evidence.
- `pip check`: passed in the isolated Python 3.13.12 P12 environment. The shared Miniforge base is
  intentionally not evidence because it contains unrelated `vcbench` pins and invalid metadata.
- `git diff --check`: passed.
- Two independently built release wheels are byte-identical: 1,064,637 bytes, SHA-256
  `d6e431dd5f1f175eaec9b605e25df4e47864194932f86ca9dfa5c8cc4be63543`.
- Clean-wheel verification passed for installed CLI offline execution, API health/job, packaged
  React root/assets, and version `1.6.0`.

The isolated lock fingerprints were build
`098f255a59bbddbae9166a6bc1b676d6cbce5bd47efcafb620ce901d2bf6becc`, dev
`49d5d18e6a9c85f0d2e8e01912b7e0ad02b255302b43661bf72879477d87bea3`, and runtime
`9f3cfde07a9a0398792daa4822267058e239651c59ddd5fc6affb90b9f82baaf`.

## Engineering, science and policy status

Engineering: `contract_defined=true`, `implementation_complete=true`, `tests_passed=true`,
`artifact_ready=true` for the local software candidate.

Scientific evidence: `NOT_RUN`. P12 created no `benchmark_passed`, `scientifically_validated`, or
`promotion_eligible` result for any real capability. Synthetic positive records are contract tests
only.

Product policy: `NO_NEW_DECISION`; no real capability became `production_promoted`.

Negative result retained: the P9 external-validation result remains negative and unbound; runtime
continues to abstain. Missing evidence, policy, environment, adapter, artifact readiness, exact
scope, or active lifecycle state also produces an empty plan and abstention.

Known limitations: `data_only` remains a registry safe-load declaration rather than a type-level
loader proof; migrated v1 cards remain incomplete; no real model or new species/task capability was
validated; remote CI, release, deployment and operator decisions were not performed.

Next eligible local work unit: `P13 — Model Adapter SDK / versioned task-output conformance`.
