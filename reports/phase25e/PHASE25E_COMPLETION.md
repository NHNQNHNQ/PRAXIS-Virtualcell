# Phase 25E Completion Report — Virtual Microbiome Contract

## Completion state

| Field | Exact value |
|---|---|
| Work unit | `P25E — fixed 2–3-member virtual microbiome contract and fail-closed software` |
| Starting SHA / active baseline | `ae5e93571783cb3cf49a6e0fab531a89e963f7ec` |
| P23A prerequisite code SHA | `2b894966cd00b2af2fafbf8f009566dd69f393a7` |
| Completion code SHA | `039393e6be897b3014bb0b657d0a439d879578b6` |
| Completion tree | `b53e542940bf39fd44965fe55416798211ab580b` |
| Source date epoch | `1786171049` |
| Branch | `codex/p25e-virtual-microbiome` |
| Engineering | `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION` |
| Fixture evidence | `SYNTHETIC_CONFORMANCE_ONLY` |
| Science | `NOT_RUN` |
| Product policy | `NO_NEW_DECISION` |
| P24 real adapter | `AUTHORIZATION_REQUIRED / NOT_RUN` |
| P25R real assets/model/benchmark | `AUTHORIZATION_REQUIRED / NOT_RUN` |

P25E freezes one narrow engineering shape:

```text
ordered 2–3 strain-resolved members
+ exact initial abundance + well-mixed medium/compartment + time
→ strain-level abundance fractions at the exact end time
```

It does not implement a P24 adapter, model, solver, mapping, benchmark protocol, evidence or policy.
Every plan is non-executable and every result is a value-free abstention. The repository-local
E. coli/yeast fixture proves deterministic contract conformance only; it is not a scientific
community model or evidence that those organisms interact as represented by the fixture.

## 1. Frozen code scope

The completion code commit changes exactly four paths:

| Path | SHA-256 |
|---|---|
| `praxis_virtualcell/community_packs/virtual_microbiome.py` | `747808c002ff36e5ac00076da50c5a07cb8d4716596e18a1fd8665e8c7a26d61` |
| `praxis_virtualcell/community_packs/__init__.py` | `9fa0e7e4f1645a26463bdafc108363d9386a74a539eda6e518a89ff8e4283640` |
| `praxis_virtualcell/tests/test_virtual_microbiome_contract.py` | `f37b8ad46f4f9edeedfd14214c3f6a8ae0f5cef632ad298c08095bc96180d40e` |
| `praxis_virtualcell/tests/test_community_packs.py` | `0675448ef3b5be47b7ebd18d19307c83f851d42eabd58d3a9f9b1382ff7176a6` |

P10 `community_packs/contracts.py` is byte-unchanged with SHA-256
`352892defdd1198263e9c57670da1d485da6d4740a31faafb7866e95b3c157dd`. No concrete
`CommunityModelAdapter` subclass or default registration was added. No API, UI, JobStore,
legacy predictor, registry store or runtime route was changed.

## 2. Contract delivered

P25E adds independent, strict and fingerprinted schemas:

- `vc.virtual-microbiome-scope.v1`;
- `vc.virtual-microbiome-primary-endpoint.v1`;
- `vc.virtual-microbiome-adapter-requirement.v1`;
- `vc.virtual-microbiome-contract.v1`;
- `vc.virtual-microbiome-request.v1`;
- `vc.virtual-microbiome-plan.v1`;
- `vc.virtual-microbiome-result.v1`.

The biological scope binds ordered member IDs, current Pack bytes/fingerprints, NCBI taxonomy,
scientific name, assembly, one explicit unique strain identity term, exact initial abundance,
medium, compartment, start/end time and `well_mixed` space. Abundances must be positive and sum
exactly to one. Time must move forward. The schema requires two or three members, but the current
contract-only allowlist contains exactly the checked-in E. coli and yeast Pack fingerprints, so the
only positive freeze fixture has exactly two members. An arbitrary human/mouse Pack cannot be
relabeled as a strain-resolved microbiome member.

The sole primary endpoint is `strain_level_abundance_at_end_time`, an ordered fraction vector.
Its preregistered metric is mean absolute error, lower is better, and its exact engineering fixture
threshold is `0.1`. `secondary_may_override_primary=false`, and P25E result schemas require
`secondary_predictions=null`.

The adapter requirement freezes these ordered baseline names:

```text
persistence, independent_monoculture, no_interaction
```

and these ordered OOD axes:

```text
member, medium, initial_abundance, time, condition, batch
```

The record deliberately binds P24 adapter, model, environment, metabolite mapping, benchmark
protocol, evidence and policy fingerprints to `null`. It records immutable missing bindings rather
than pretending a mutable authorization/science state is part of biological scope identity.

## 3. Deterministic synthetic conformance identity

The canonical checked-in fixture produces the following engineering-only identities:

| Identity | Fingerprint |
|---|---|
| community | `dff238eebfb84175c867b012bc9d4158fec3a5bf2ec11cf1536f35fe76fcd99e` |
| bacteria member Pack | `8600261ad68302432186e7107f053a7a0fdf0e3dbc61dc9754a502b20a95b1fe` |
| yeast member Pack | `7f3bc08f6fd64209683603b1fc93b38a5e646b866eb05878160ec69a755b9ff1` |
| medium | `e20607dd366ce82c5b03b86f500e9362783b5e875d3ad22a16c8a7e2f06623a7` |
| time | `caac5f1039ca8a8d94cf6272a8495cabe7c7f4bb6c406374391ee7eca0c416b0` |
| scope | `49bd4b00cb555dcc83d62839a97e17828aa86ec722f4abc8f61938a9282a0221` |
| primary endpoint | `9fd0320daf7fe55d20bc3a7ef693edc8c1132d31438510678df40a97f3868c04` |
| adapter requirement | `5f913d59d8631a1ad79e99ad4fb70b52f9b60a1863120ef795417548908c3b90` |
| contract | `f99d93bc4caf102ecf479a3c46fe3e9c0fc78e87b1aaeea5bc71a4b3ff86a806` |
| request | `28d8d380bb20d638f2f55ca8ef9cf03ce574a763fd0d9f1c28338ef5cf87f19d` |
| plan | `aa3fe0db7099720f400e21cf92e312450b53e618e4976fa814e70747d18d7be0` |
| result | `b1b5ba16796dbc755f1dab6ba2ef78ea6001dc98f457ca9718f4f62cefd4a32c` |

The deterministic plan ID is `vm_plan_f6566a9ee2793d9ed07b58d8`. Its steps are empty and
`executable=false`.

## 4. Honest abstention

An exact request still returns `prediction=null` and `secondary_predictions=null` with these
ordered reasons:

```text
p24_adapter_unavailable
model_identity_unavailable
environment_identity_unavailable
metabolite_mapping_identity_unavailable
benchmark_protocol_unavailable
real_execution_binding_unavailable
scientific_evidence_unavailable
production_policy_unavailable
```

Member-byte drift, a re-signed but different community scope, or request identity drift prepends
the corresponding revalidation/scope reason. It never falls back to P10 toy balance, a legacy
predictor, zero filling, an LLM, a default value or a synthetic prediction.

## 5. P10 v1 byte and semantic regression

P25E preserves the P10 `vc.community-*.v1` no-model contract. Canonical regression identities are:

| P10 object | Frozen identity |
|---|---|
| CommunityPack | `03babc6f574097eaeaa511ed7eae201938e991e22ba41314897ddf9c9af96ec0` |
| exchange ledger | `dc5fc14a23ed501b3725aae86f247ee50664741004c8087562da9e610bbea654` |
| exchange validation | `829dcd877b7e535003435e80316f8eaf396b0e79344857232d0ec35ec07d48fc` |
| execution plan | `e4cada5ad70cb94e0e816c7d83b3eee3fe61c492a31e69ec1963d2b890372b60` |
| run result | `208406cf43548d0b6b2f20388328e142df6320a17f99746ff0337306925a47c4` |
| plan ID | `community_plan_813cc094d6d2f90d552f1a45` |

These P10 objects remain toy/no-model serialization and abstention evidence only.

## 6. Verification matrix

| Gate | Result |
|---|---|
| P25E focused | `21 passed` |
| P25E + P10 adjacent | `60 passed` |
| safe local suite | `1,809 passed, 49 skipped, 387 deselected in 449.43s` |
| legacy suite | `1,147 passed, 58 skipped, 105 deselected in 57.14s` |
| Ruff | `All checks passed` |
| Ruff format check | passed for all four changed code/test paths |
| Python compile | passed |
| `git diff --check` | passed |
| React typecheck / lint / build | passed; bundle budget passed |
| `pip check` | failed on pre-existing host-environment dependency conflicts |

`pip check` reported the already-polluted shared environment, including missing `python-magic` and
incompatible `vcbench` pins. No dependency was installed, removed or changed, and this failure is
not represented as a passing dependency-closure gate. The successful pytest/Ruff/frontend results
remain local source checks, not clean-environment or scientific validation.

## 7. Reproducible package evidence

Two independent `git archive` trees of the completion code SHA were built with npm strictly offline
and Python build isolation disabled. The wheels are byte-identical:

| Property | Exact value |
|---|---|
| filename | `praxis_virtualcell-1.6.0-py3-none-any.whl` |
| size | `1,234,438` bytes |
| SHA-256 | `c8529477974c6379f75bee05e4b0b589e3a03ed70302617ab46461954915d77e` |
| ZIP entries | `374` |
| React entries | `14` |
| test entries | `0` |
| AppleDouble entries | `0` |
| source/wheel P25E module SHA-256 | exact match: `747808c002ff36e5ac00076da50c5a07cb8d4716596e18a1fd8665e8c7a26d61` |
| toolchain | Python `3.13.12`; build `1.5.0`; setuptools `70.2.0`; packaging `26.0`; Node `26.4.0`; npm `11.17.0`; Vite `8.1.2` |

The first attempted archive command used npm 11's `--prefix` form and failed before packaging; it
produced no wheel. Re-running from each archive's frontend working directory succeeded offline.
Only the two successful, byte-identical wheels above are package evidence. They are not published,
signed, installed into a clean environment, or a release candidate.

## 8. Explicit non-events and next work

P25E did not read or download external data, weights, checkpoints, mappings or model artifacts. It
did not train, tune, run P24/P25R/P21B, evaluate a baseline, compute a confidence interval, access
test/external data, create evidence, make an operator decision, mutate a registry, push, tag,
release, deploy or touch `.53`, PRAXIS-2, `old/**`, protected refs or services.

The exact state is:

```text
P25E engineering: COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION
fixture evidence: SYNTHETIC_CONFORMANCE_ONLY
P25 science: NOT_RUN
P25 production policy: NO_NEW_DECISION
P24 real adapter: AUTHORIZATION_REQUIRED / NOT_RUN
P25R: AUTHORIZATION_REQUIRED / NOT_RUN
prediction: null
next eligible local work unit: P26E host–microbiome contract/DAG/matching/abstain software
```

P26E is eligible only as fail-closed engineering under the standing local authorization. Without
exact-scope scientifically validated and production-promoted host and community releases plus a
matching release, P26E must remain non-executable. K562 cannot substitute for a required host.

## 9. Documentation map

- [ADR-0021](../../docs/ADR-0021-virtual-microbiome-contract.md)
- [P25E runbook](../../docs/runbooks/VIRTUAL-MICROBIOME-CONTRACT.md)
- [Current integration guide](../../docs/PRAXIS-VIRTUALCELL-CURRENT-PROJECT-AND-INTEGRATION-GUIDE.md)
- [Phase 12–30 execution plan](../../docs/PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md)
- [Canonical completion ledger](../../docs/PHASE12-30-DETAILED-COMPLETION-CHECKLIST.md)
