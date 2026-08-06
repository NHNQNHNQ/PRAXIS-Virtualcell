# Phase 13 — Model Adapter SDK completion

Work unit: `P13 — Model Adapter SDK / versioned task×output adapter conformance`

Outcome: `ENGINEERING_COMPLETE`

Starting SHA: `f83c13db386cb552b3ce7a5643e5ffbead0ff573`

Completion code SHA: `744d0a28d2cfc13d1b10e85b133b6c13b9426174`

Completion tree: `198e623120688d3704b9312990ddaa93c9a7b0e6`

Branch at completion: `codex/p13-model-adapter-sdk`

## Scope and protected state

P13 added strict, versioned adapter input and output contracts; immutable prepared-input, output-envelope
and execution-provenance records; exact task×output registry resolution; deterministic conformance
checking; and a governed generic adapter-output path through ensemble, reliability, provenance and
reporting. It retained the existing delta-expression path and reused the existing model-feature and
alignment contracts. It did not download or run real model weights, train a model, access remote
services, create scientific evidence, or make an operator promotion decision.

The observed implementation diff is the exact 16-path source/test diff from the starting SHA to the
completion code SHA: `praxis_virtualcell/agents/critic.py`;
`praxis_virtualcell/agents/ensemble.py`; `praxis_virtualcell/agents/model_broker_agent.py`;
`praxis_virtualcell/agents/provenance_agent.py`; `praxis_virtualcell/agents/reliability.py`;
`praxis_virtualcell/agents/report.py`; `praxis_virtualcell/core/runtime.py`;
`praxis_virtualcell/governance/gate_util.py`; `praxis_virtualcell/model_zoo/adapter_sdk.py`;
`praxis_virtualcell/model_zoo/capability_registry.py`;
`praxis_virtualcell/model_zoo/wrappers/base.py`; `praxis_virtualcell/predictors/base.py`;
`praxis_virtualcell/tests/test_capability_runtime.py`;
`praxis_virtualcell/tests/test_model_adapter_output_flow.py`;
`praxis_virtualcell/tests/test_model_adapter_sdk.py`; and
`praxis_virtualcell/workflows/predict_delta_expression.py`.

No staged, modified, deleted, or untracked paths existed before this completion report was created.
`old/**`, the protected repository copies, remote refs, GitHub, `.53`, services, ports, external
assets and existing deployment state were not modified.

## Contracts and immutable identities

The completed engineering contracts are:

- `vc.adapter-input-contract.v1` and `vc.adapter-output-contract.v1`;
- `vc.prepared-adapter-input.v1`, `vc.adapter-output-envelope.v1`, and
  `vc.adapter-execution-provenance.v1`;
- `vc.adapter-conformance-report.v1`;
- exact task×output adapter registration and resolution, reusing `vc.model-adapter.v1` identity; and
- feature/alignment binding that reuses `vc.model-feature-contract.v1` and
  `vc.alignment-report.v1`.

The adapter-global canonical delta-expression reference fingerprints are:

- adapter: `17afc27e56dba13567001ff1982cbf1660e2948fadf2147301a1d0dcf61aeb3d`;
- input contract: `d10cf437291dc1ebb1689c3f4c5eea4d82af3842491c224172215faddca93078`;
- output contract: `d863783786504ebf768cfd7e2fbad66cfd03a029deb1dee3543a9872712e363d`.

The completion conformance fixture uses request `p13-reference` (K562, TP53), no Pack or
compatibility binding, and raw delta values `[0.25, -0.5]`. Its execution-specific fingerprints are:

- prepared input: `31d1859a226c50375b7f4d65b6307a9680d9e71e978f4f16e5eb053d90c5de3e`;
- output envelope: `a6745427e8f0e9d516789ec9418a42fdb024e245d452b1ca4825c24398996ba2`;
- conformance report: `b40374d81f9ec3362d9950bffcfa97f123e46abc80f8b4b135fd5afa02bded18`.

Those three fixture fingerprints change when the request, Pack/compatibility binding or raw output
changes; they are reproducibility evidence for this fixture, not adapter-global identities.

The default registry contains only the governed `predict_delta_expression` × `delta_expression`
reference adapter. Growth and fitness adapters remain test-only dummies.

## Validation bound to completion bytes

All commands ran locally without network, external assets, real weights, training, LLM, GPU or
remote services.

- Model Adapter SDK contract file: `48 passed`.
- Adapter output-flow file: `22 passed`.
- Capability/runtime file: `75 passed`.
- P13 directed gate: `265 passed`.
- VirtualCell core, excluding the explicit LLM gate: `1462 passed`, `35 skipped`, `9 deselected`,
  with two known MuData warnings.
- Legacy unit gate, excluding integration/LLM/remote: `1146 passed`, `59 skipped`, `105 deselected`.
- Packaging regression: `13 passed`.
- P13 Ruff scope: passed.
- Frontend `typecheck`, `lint`, `build`, and bundle budget: passed.
- `pip check`: passed in the isolated validation environment.
- Two independent wheels built from the exact completion code commit are byte-identical: 1,076,180
  bytes, SHA-256 `3658b6247a909d0351d760295e0bcbb8082eac930d96fdfe39e4377b591b4f23`.
- Clean-wheel verification passed for the installed SDK and default-registry import.

## Engineering, science and policy status

Engineering: `contract_defined=true`, `implementation_complete=true`, `tests_passed=true`; the
exact-commit local software wheel passed reproducibility and clean-install checks. This does not set
any Model Registry release or model artifact to `artifact_ready=true`.

Scientific evidence: `NOT_RUN / NOT_APPLICABLE`. P13 is a contract and integration work unit; its
reference and dummy records are engineering fixtures, not real-model benchmark, OOD, calibration or
scientific-validation evidence.

Product policy: `NO_NEW_DECISION`; no real capability became `production_promoted`.

Release state: no product-version bump, Git tag, release, push or deployment was performed for P13.

Negative result retained: the P9 external-validation result remains
`abd1145c434fd4e48ac9d72e94e8e19d14a5b4011f03d05db4823dd91760da6e`; its negative status and
runtime abstention are unchanged.

Known limitations: the default registry has only the delta-expression reference adapter; growth and
fitness dummies are test-only; no real model, weight, dataset or new capability was validated; and no
Phase 14 science or policy work was performed.

Next eligible local work unit: `P14E — E. coli K-12 knockout→growth contract`. `P14R` and `P14B`
were not authorized and were not run.
