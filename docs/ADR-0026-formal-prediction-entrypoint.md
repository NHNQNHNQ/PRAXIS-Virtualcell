# ADR-0026: Formal prediction entrypoints require Pack-aware planning

**Status:** accepted
**Date:** 2026-08-10
**Work unit:** `P12 product-entrypoint alignment / no-Pack fail-closed execution`

## Context

The P12 execution gate already requires an exact request × Pack × release × artifact × environment × adapter ×
evidence × policy closure. Historical `run_query`, `run_request`, and the legacy runtime still exist for frozen
P0/P10 compatibility tests and can enumerate mock or case-runner predictors. A formal UI/API/CLI/Streamlit
request without Pack identity must not inherit that compatibility behavior.

## Decision

Formal UI/API/CLI/Streamlit callers use `run_formal_query`. With no exact `pack_id + pack_version`, the runtime
still sends the normalized request to `ModelBrokerAgent`, but supplies no `RegisteredPack`. P12 therefore emits a
`vc.execution-plan.v2` with zero steps and `pack.unregistered` compatibility reasons. The public result is a
value-free abstention with `prediction=null`, no models used, no learned-reliability score, an explicit
`pack_unregistered` reason, and a V2 job execution identity whose `legacy_adapter=false`.

Formal runtime construction does not register `MockLinear`, `MockCPA`, `MockGEARS`, `CaseRunner`, or the legacy
applicability adapter. It also does not infer a Pack from species, cell preset, Data Center display, or free text.
An empty plan has no executable module route.

`run_query`, `run_request`, and `build_runtime()` remain explicitly named compatibility/test harnesses for frozen
legacy regression only. They are not formal product execution authority and cannot be cited as P12/P14–P16
scientific evidence, compatibility, promotion, or a prediction capability.

## Consequences and non-goals

- Current Chat has no Pack selector, so it intentionally abstains until a future product surface collects an
  explicit Pack identity and connects it to deterministic Pack-aware execution. It must not auto-bind a builtin
  Pack.
- The direct `vc.request.v2` surface remains the existing P17 contract-only compiler; this change does not turn
  it into a model runner.
- No model, adapter, Pack, evidence, policy, scientific validation, promotion, release, external asset, network,
  or deployment action is created by this decision.
- The first real perturbation claim still requires its independent run window—currently most usefully P16R's
  frozen K562 benchmark—followed by an operator policy decision.

## Verification

The directed tests cover no-Pack formal abstention, a V2 zero-step plan, explicit Pack reason, V2 non-legacy job
identity, no mock/case trace recipients, Pack-bound runtime regression, and API/module-plan behavior. They do not
create scientific evidence.
