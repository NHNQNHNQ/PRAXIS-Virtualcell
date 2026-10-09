# Phase 23A Completion Report — Cell Interaction Evidence Contract

## Completion state

| Field | Exact value |
|---|---|
| Work unit | `P23A — Cell Interaction Evidence` |
| Starting SHA | `2b5c28ac152857dfa1109de41ed5d5ddc7ab06a4` |
| Completion code SHA | `2b894966cd00b2af2fafbf8f009566dd69f393a7` |
| Completion tree | `00bd98b0fd14091f4528115dcc66730264d5803a` |
| Source date epoch | `1786061504` |
| Branch | `codex/p23-cell-interaction` |
| Engineering | `COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE` |
| Science | `NOT_RUN` |
| Policy | `NO_NEW_DECISION` |
| P23B | `OPTIONAL / AUTHORIZATION_REQUIRED / NOT_RUN` |
| P24 | `AUTHORIZATION_REQUIRED / NOT_RUN` |

P23A 完成了一个 narrow、directed、evidence-only local contract：

```text
sender → receiver → interaction_evidence_score
```

它没有实现 receiver response prediction、effect estimation 或 causal inference。唯一 positive
projection 来自 supplied synthetic fixture；它只证明 P13-shaped contract/conformance 能精确拒绝
越界输入，不是 biological prediction 或 scientific evidence。

## 1. Frozen code scope

Completion code commit 只新增两个文件：

- `praxis_virtualcell/model_zoo/cell_interaction_evidence_contract.py`；
- `praxis_virtualcell/tests/test_cell_interaction_evidence_contract.py`。

| File | SHA-256 |
|---|---|
| module | `d1ba8d8054bf91c4a54a215c331fef65557df3954dba730998821ea9f70743cd` |
| test | `269c387423a41864031bb54fbbc692b84da0cbae5137db9fd6cbc077302d3081` |

没有修改 legacy communication/coculture code、P22 registry store、P18 multi-omics contract、P10
community v1 contracts、API/UI/JobStore/runtime routes 或 default adapter registry。

## 2. Contract delivered

### 2.1 Endpoint closure

每个 `InteractionEndpointV1` 精确重验一个 P22 `VirtualCellReleaseV1` 及其 release、context、
P19 registration 和 Pack fingerprints，并绑定 sender/receiver role。P23A 因而能发现 stale/forged
content closure，但不能推出 release 当前已在受信 P22 registry 中 cataloged、active 或 authorized。

`registry_state_verified` 被类型固定为 `false`。本轮没有打开 P22 store、读取 external checkpoint、
核验 registry authority 或执行 import/lifecycle mutation。测试中的 P22 releases 是 synthetic positive
contract fixtures，不是真实 curated releases。

### 2.2 Typed P18 reference

每个 endpoint 携带 `P18EndpointIdentityV1`，明确绑定 `vc.multiomics-model-input.v1`、Pack、view、
observation semantics、join、modality 和 observation fingerprints。Pack/organism/taxonomy/observation
会跨 endpoint 与 same-experiment record 重新核对。

这仍是 declared reference：`p18_contract_verified=false` 且
`observation_membership_verified=false`。没有读取真实 P18 Pack/model input、matrix 或 row membership。

### 2.3 Same-experiment and mapping identity

`SameExperimentInteractionEvidenceV1` 把一个 dataset/platform/evidence asset/record 与 experiment、
donor、sample、well、condition、dose/time、sender/receiver observation、ligand/receptor/evidence
namespaces 和 mapping asset 绑定到同一 strict object。合同没有第二 dataset 插槽，不允许跨无关数据集
配对。CURIE namespace、finite quantities 和所有 hashes 都被严格验证。

但 identity completeness 不等于 external verification：`evidence_asset_verified=false`、
`paired_linkage_verified=false`。本轮没有读取 paired/co-culture/spatial data 或 mapping bytes。

### 2.4 P20/P21 scorer declaration

`InteractionScorerFixtureV1` 记录 model release/artifact、benchmark bundle/protocol/run/result、P21B
execution 和 adapter identities，并冻结三项 baselines 与七项 OOD axes。所有 trust/execution flags
固定为 false；没有 candidate/model run、benchmark、baseline comparison、CI 或 real OOD evaluation。

### 2.5 P13-shaped output boundary

`CellInteractionEvidenceAdapter` 复用 P13 prepared input、output envelope、provenance 和 deterministic
conformance。Exact identities：

| Identity | Fingerprint |
|---|---|
| adapter | `6ca0a23373d6a0599c5b6055b4696a76dbd64d6317c656d11fab790b74be1467` |
| input contract | `83725f4a5753f4f9eec0ccea3405a35785fc9518ac1edbcb9cd4055dd6709f7d` |
| output contract | `2d27ac18d44d0fdab09c42107cc2ad45a3a9f920c706f37cebfe767270d4a12a` |

The adapter has no runtime scorer. It validates a supplied finite JSON-safe scalar in `[0, 1]`, labels it
`synthetic_conformance_not_evidence`, records uncertainty as unavailable, and exposes exactly:

```json
{"interaction_evidence_score":[0.625]}
```

No other projection key is legal. Metadata explicitly fixes real data/model execution, registry state,
asset/linkage, P20/P21 trust, baseline/CI, receiver response and causal claim to `false`. Abstentions are
value-free (`values=null`, `shape=null`, empty projection metadata) and cannot be projected.

## 3. Fail-closed and adversarial coverage

The `107` focused tests cover positive deterministic contract conformance and negative/adversarial cases:

- missing, malformed or stale release/context/registration/Pack/P18/interaction identities;
- swapped roles/direction, organism/taxonomy mismatch and observation drift;
- missing same-experiment identity fields, attempted second dataset and namespace/CURIE mismatch;
- negative/nonfinite/unsafe dose/time and bool/string/NaN/Inf/unsafe/out-of-range scores;
- baseline/OOD omissions, substitutions, reorderings and unexplained OOD;
- attempts to self-promote registry, P18, asset/linkage, P20/P21, science or policy flags;
- response/effect/causal/legacy fields at wrapper, prediction, projection and reason surfaces;
- Pydantic subclass and `model_copy` undeclared-field injection before nested normalization;
- generic `Mapping`/`UserDict` nesting and cyclic request metadata;
- stale interaction identity and forged envelope provenance;
- standalone output validation/projection, aggregation, legacy payload, I/O/runtime and default-registration
  bypass attempts.

The subclass/Mapping/cycle cases specifically ensure a permissive serialization boundary cannot silently discard
malicious extra fields and then produce a valid canonical fingerprint. Provenance tests ensure an otherwise
well-shaped envelope cannot be detached from its exact prepared input and request.

## 4. Verification matrix

| Gate | Frozen result |
|---|---|
| focused | `107 passed in 41.71s` |
| affected | `495 passed, 1 skipped in 116.55s` |
| safe | `1,787 passed, 49 skipped, 387 deselected in 367.11s` |
| legacy | `1,147 passed, 58 skipped, 105 deselected in 57.38s` |

Skip/deselect counts do not imply external assets, models, GPU, remote calls or scientific tests passed. The
matrix ran local repository tests and synthetic fixtures only.

## 5. Reproducible package evidence

| Property | Exact value |
|---|---|
| Wheel filename | `praxis_virtualcell-1.6.0-py3-none-any.whl` |
| Wheel size | `1,226,514` bytes |
| Wheel SHA-256 | `e78f40f0f4fe7354e3c660d6612a8ee60a1b2dd61af2fc606a67d01e67ac601e` |
| ZIP entries | `373` |
| React entries | `14` |
| Test entries | `0` |
| AppleDouble entries | `0` |
| Independent builds | byte-identical |
| Module source/wheel hash | `d1ba8d8054bf91c4a54a215c331fef65557df3954dba730998821ea9f70743cd` / exact match |
| Toolchain | Python `3.13.12`; build `1.5.0`; setuptools `70.2.0`; packaging `26.0`; Node `25.8.2`; npm `11.11.1`; Vite `8.1.2` |

Each build began from an independent archive of the completion SHA. Frontend dependency resolution used npm
offline; Python packaging used the currently installed toolchain with `--no-isolation` and
`--skip-dependency-check`. ZIP/content checks passed.

This evidence establishes exact-source reproducibility under that local toolchain. It is not a pinned dependency
closure, clean-environment install, wheel publication, signed release, staging or production proof.

## 6. Explicit non-events

P23A did not perform any of the following:

- read or import a real sender/receiver P22 release or mutate/query a live curated registry;
- verify P18 observation membership or read Pack/multi-omics values;
- read paired/co-culture/spatial evidence, ligand/receptor mapping or external model assets;
- train, tune, install or execute a model;
- run no-interaction, receiver-only or LR-coexpression baselines;
- calculate paired CI, scientific OOD metrics or an interaction score;
- output receiver response, response delta, effect size, treatment effect or causal language;
- create benchmark/scientific evidence, promotion eligibility or operator policy;
- register the adapter by default or wire API/UI/Data Center/Chat/JobStore/runtime;
- access network/GPU/remote compute, push, PR, tag, release, staging or deploy.

The exact project state is therefore:

```text
P23A engineering: COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE
P23A science: NOT_RUN
P23A policy: NO_NEW_DECISION
real data/assets/execution: NOT_RUN
receiver response: NOT_IMPLEMENTED
P23B: OPTIONAL / AUTHORIZATION_REQUIRED / NOT_RUN
P24: AUTHORIZATION_REQUIRED / NOT_RUN
```

## 7. Next-step decision

There is no remaining ungated local work unit that can honestly advance the scientific roadmap from this
completion. P23B is optional and requires an independent intervention/estimand window. If P23B is skipped, P24
is explicitly the First Real Community Adapter: it requires authorized exact real assets, a fixed P20/P21 model
identity and a write-new output root. A fake/no-asset P24 contract-only scaffold is not an eligible substitute.

### 后续唯一合并授权草案

以下是一个合并模板，不是当前授权。所有 `<...>` 必须由具名 operator 填写；只选择一个 route。

```text
授权以 P23A completion code SHA
2b894966cd00b2af2fafbf8f009566dd69f393a7 作为唯一起始基线，并选择且仅选择：

route=P23B：提供 exact receiver-response protocol fingerprint、exact P21B
candidate/evidence/execution identity、预声明 intervention/control/estimand/assumptions、
同实验 receiver measurement 和全部输入资产；

或 route=P24：明确跳过 P23B，创建 codex/p24-community-adapter，逐字节保持 P10
vc.community-*.v1 no-model serialization/fingerprint/abstain 语义，只为一个预声明双成员、
well-mixed、medium/abundance/time task 提供 exact member releases/Packs、mono/co-culture
time series、medium、growth/biomass、extracellular metabolomics、metabolite mapping、
fixed P20/P21 model/evidence/execution identity 和独立 v2/新命名 adapter/plan/result scope。

对所选 route 逐文件填写只读 absolute source path、size、SHA-256、license、source、usage；
填写当时不存在的 exact absolute write-new output root、offline/network policy、禁止覆盖策略、
资源限制、branch、exact file allowlist、现场 protected paths 和 local commit=yes/no。
真实执行前冻结 baseline、primary metric、paired CI、OOD/external gate、abstain 和 scientific
language policy。不得训练/调参，fixed model 必须来自 P20/P21；任一 gate 失败时不得产生
receiver response、causal claim、promotion-eligible evidence 或 production policy。不得实施未选
route、P25+、push、PR、main/tag、release、staging、deploy、.53、PRAXIS-2 或 old/**。
```

在 exact identities、paths、hashes、licenses 和 output root 未填写前，P23B/P24 都保持
`AUTHORIZATION_REQUIRED / NOT_RUN`。

## 8. Documentation map

- [ADR-0020](../../docs/ADR-0020-cell-interaction-evidence-contract.md)
- [P23A runbook](../../docs/runbooks/CELL-INTERACTION-EVIDENCE.md)
- [Current project and integration guide](../../docs/PRAXIS-VIRTUALCELL-CURRENT-PROJECT-AND-INTEGRATION-GUIDE.md)
- [Phase 12–30 execution plan](../../docs/PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md)
