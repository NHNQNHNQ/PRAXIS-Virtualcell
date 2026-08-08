# Phase 26E Completion Report — Host–Microbiome Contract

## Completion state

| Field | Exact value |
|---|---|
| Work unit | `P26E — Host–Microbiome contract, time-unrolled DAG, matching requirements and abstention software` |
| Starting SHA / active baseline | `6bd02231449b6969e22aeb5bea6798fd334daef6` |
| Completion code SHA | `5bd3e502a7a1f1cb0fd1b79ecfd109eeeaf265c4` |
| Completion tree | `b3d7303cafb5b874c8b5a441b53e32ff77ef2c54` |
| Source date epoch | `1786176771` |
| Branch | `codex/p25e-virtual-microbiome` |
| Engineering | `COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION` |
| Umbrella state | `ENGINEERING_COMPLETE_SCIENCE_PENDING` |
| Fixture evidence | `SYNTHETIC_CONFORMANCE_ONLY` |
| Science | `NOT_RUN` |
| Product policy | `NO_NEW_DECISION` |
| P26R | `BLOCKED_EXTERNAL / NOT_RUN` |

Documentation closure is the commit containing this report and is intentionally not self-referential.

P26E freezes exact host/P25 community requirements, a typed missing cross-domain interface, a deterministic
forward DAG and negative release audit. It does not implement a host–microbiome model, co-simulation,
mediator inference or receiver response. Every compilation has empty steps and null values.

## 1. Frozen code scope

The completion code commit changes exactly two paths:

| Path | SHA-256 |
|---|---|
| `praxis_virtualcell/host_microbiome.py` | `94f421afabbc2932f574bd11d0d3b3a7e2a67d5b3c271528dafc52b2ee8b2c54` |
| `praxis_virtualcell/tests/test_host_microbiome.py` | `e788370b3ce3675ef936fc0aabf654d94a912213e45666f1fa4ed3daa4874a68` |

No P22/P25 schema, API, UI, JobStore, default registry, runtime route, model artifact, Pack or external asset
was changed. Protected workspaces, refs, services, `.53` and `old/**` were preserved.

## 2. Contract and schema identities

P26E adds five public strict records:

| Schema | Meaning |
|---|---|
| `vc.host-microbiome-interface-requirement.v1` | typed but unavailable cross-domain interface |
| `vc.host-microbiome-dag.v1` | deterministic topology-only DAG |
| `vc.host-microbiome-contract.v1` | exact host request × P25 contract × interface × DAG closure |
| `vc.host-release-audit-snapshot.v1` | negative P22 catalog/checkpoint audit |
| `vc.host-microbiome-compilation.v1` | immutable value-free abstention |

`vc.host-microbiome-joint-scope.v1` is a canonical fingerprint payload, not a sixth public model.
There is no P26E request, plan or candidate schema and no LLM/candidate authority input.

The checked-in synthetic conformance fixture produces:

| Identity | Fingerprint |
|---|---|
| host request | `0709e6fab6335b6d7e578fdb3d91ffc1d751553c3b5fbd39afe8ff3e11fab155` |
| host context | `c1f47346fd10f38ebbe50718a9983f104e1a77a1e9efbf91b8a906b68e66c070` |
| host benchmark scope | `9bf7423477efd8bf8f0fc3daf1333526b7580d3166b4a158b09b31eeb9353933` |
| P25 community contract | `f99d93bc4caf102ecf479a3c46fe3e9c0fc78e87b1aaeea5bc71a4b3ff86a806` |
| community | `dff238eebfb84175c867b012bc9d4158fec3a5bf2ec11cf1536f35fe76fcd99e` |
| community scope | `49bd4b00cb555dcc83d62839a97e17828aa86ec722f4abc8f61938a9282a0221` |
| bacteria member Pack | `8600261ad68302432186e7107f053a7a0fdf0e3dbc61dc9754a502b20a95b1fe` |
| yeast member Pack | `7f3bc08f6fd64209683603b1fc93b38a5e646b866eb05878160ec69a755b9ff1` |
| medium | `e20607dd366ce82c5b03b86f500e9362783b5e875d3ad22a16c8a7e2f06623a7` |
| time | `caac5f1039ca8a8d94cf6272a8495cabe7c7f4bb6c406374391ee7eca0c416b0` |
| interface requirement | `36606a03695d4ed226300f98c200673c820d02fd2d9b3564a35e76f228d3c495` |
| DAG | `f45c205f31b1675ee20d53b4a8f687f2259c5ac5e3586f45624468dd1a19a28a` |
| joint scope | `3e92ac0a0a2afdd3d190dd7a33ba88c50e62ad6a96ed091e56c74ac4cf71b2db` |
| P26 contract | `41117ebeb0deaf86b1d200061c16ea09ad1a390118bd71d09e4b4bb8281c5984` |
| unbound host audit | `3758ac523249cb3849050ced1bd0bba3bf6e2fb95ea676afaeb1908253ee6ab2` |
| compilation | `3c2a2e9dd8be5995a99ffba691f09183c7e5cbf1f1d3743686de91401ee9c285` |
| compilation ID | `hm_comp_9d8ecd6f0a81f1d5f42698cc` |

These values bind a synthetic engineering fixture only. The intestinal label and synthetic P22 positive-row
fixture are not real host data, a host release or host–microbiome evidence.

## 3. Explicit missing bindings

| Binding | Exact P26E value |
|---|---|
| required host Pack / release | `null / null` in the canonical unbound fixture |
| full host-request binding | `null` |
| community release schema / fingerprint | `null / null` |
| matching release fingerprint | `null` |
| interface mapping fingerprint | `null` |
| source-output / target-input contract | `null / null` |
| community science / production policy | `null / null` |
| full-request host science / production policy | `null / null` |

P22 v1 may audit a context candidate, but it cannot bind tissue, other complete request dimensions or a P25
community. Even a checkpointed, active and positive synthetic row therefore stops at
`p22_context_matched_request_binding_insufficient`; `exact_request_match_verified=false`. K562 mismatch
coverage proves fail-closed scope handling, not availability of an intestinal host capability.

## 4. DAG and honest abstention

The only permitted topology is:

```text
community_state_t0
→ mediator_state_t1
→ host_state_t2
→ community_state_t3
```

It is topology-only, not an executable, mechanistic, causal or converged time simulation. The normal ordered
abstention reasons are:

```text
matching_host_release_unavailable
matching_community_release_unavailable
matching_release_unavailable
cross_domain_interface_unavailable
p26_real_execution_not_authorized
```

Live P25 byte/scope drift prepends `unsupported_host_microbiome_scope`. Steps remain empty;
`prediction`, `host_result`, `community_result` and `mediator_trace` remain `null`.
Compilation fields fixed to false for science/promotion/policy are execution guards, not a failed benchmark or
operator decision. The scientific ledger remains `NOT_RUN`; product policy remains `NO_NEW_DECISION`.

## 5. Verification matrix

| Gate | Result |
|---|---|
| P26E focused | `8 passed` |
| P26E + P25E/P10 + P22/P17 affected | `144 passed` |
| safe local suite | `1,817 passed, 49 skipped, 387 deselected in 387.09s` |
| legacy suite | `1,147 passed, 58 skipped, 105 deselected` |
| Ruff | passed |
| Ruff targeted format | passed |
| Python compile/import | passed |
| `git diff --check` | passed |
| React typecheck / lint / build / bundle budget | passed |
| `pip check` | failed on pre-existing shared-environment dependency conflicts |

Adversarial coverage includes P22 same-context/full-request drift, K562 substitution, uncheckpointed and
revoked releases, P25 member-byte drift, nested-model/LLM authority injection, candidate API rejection and
re-signed step/prediction/community-release injection. No dependency was installed, removed or changed.

## 6. Local package evidence

Two independent exact completion-code archives produced byte-identical local wheels:

| Property | Exact value |
|---|---|
| product/distribution version | `1.6.0` — unchanged |
| filename | `praxis_virtualcell-1.6.0-py3-none-any.whl` |
| size | `1,242,422` bytes |
| SHA-256 | `69700bb63445864a457cb651037e69dddd93d5be4b184c55a34c3f9332de265a` |
| ZIP entries | `375` |
| React entries | `14` |
| test entries | `0` |
| AppleDouble entries | `0` |
| source/wheel P26E module SHA-256 | exact match: `94f421afabbc2932f574bd11d0d3b3a7e2a67d5b3c271528dafc52b2ee8b2c54` |
| toolchain | Python `3.13.12`; build `1.5.0`; setuptools `70.2.0`; packaging `26.0`; Node `25.8.2`; npm `11.11.1`; Vite `8.1.2` |
| SBOM / license inventory | `NOT_RUN` — formal P30A RC work, not a P26E science gate |

The build is exact local source/toolchain evidence with offline frontend inputs and no dependency mutation. It
is not clean-install or dependency-closure evidence, is not published or signed, and is not a release candidate.
No product/API/runtime version, tag or release identity changed.

## 7. Explicit non-events and next work

P26E did not read or download real host/community data, weights, checkpoints or mappings. It did not train,
tune, execute a model, run a baseline/CI/OOD/external evaluation, inspect human consent/privacy material,
perform P26R/P21B/P21C, create evidence or policy, mutate a registry, push, tag, release, deploy or touch `.53`,
PRAXIS-2, `old/**`, protected refs or services.

```text
P26E engineering: COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION
fixture evidence: SYNTHETIC_CONFORMANCE_ONLY
P26 science: NOT_RUN
P26 product policy: NO_NEW_DECISION
P26R: BLOCKED_EXTERNAL / NOT_RUN
prediction: null
next eligible local work unit:
P27A-E — strict experiment-design contracts + rank-then-reveal replay harness
fixture: SYNTHETIC_CONFORMANCE_ONLY
P27A-R historical replay: REPLAY_NOT_RUN / ASSET_PENDING
```

P27A-E is covered by standing local authorization and starts from the actual documentation-closure HEAD.
No canonical local historical replay pool exists. P27A-R requires an exact asset manifest, license
and outcome-separation identity; Git-external assets require a separate authorization window. P27B shadow
review and P27C prospective pilot remain separate externally authorized windows.

## 8. Documentation map

- [ADR-0022](../../docs/ADR-0022-host-microbiome-contract.md)
- [P26E runbook](../../docs/runbooks/HOST-MICROBIOME-CONTRACT.md)
- [Current integration guide](../../docs/PRAXIS-VIRTUALCELL-CURRENT-PROJECT-AND-INTEGRATION-GUIDE.md)
- [Phase 12–30 execution plan](../../docs/PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md)
- [Canonical completion ledger](../../docs/PHASE12-30-DETAILED-COMPLETION-CHECKLIST.md)
