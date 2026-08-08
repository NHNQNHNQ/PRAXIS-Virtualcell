# ADR-0020：Cell Interaction Evidence contract

- 状态：Accepted（P23A engineering `COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE`）
- 日期：2026-08-07
- 唯一起始 / P22 documentation closure：`2b5c28ac152857dfa1109de41ed5d5ddc7ab06a4`
- Completion code SHA：`2b894966cd00b2af2fafbf8f009566dd69f393a7`
- Completion tree：`00bd98b0fd14091f4528115dcc66730264d5803a`
- Source date epoch：`1786061504`
- 分支：`codex/p23-cell-interaction`
- 前置：ADR-0019
- 工程状态：`COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE`
- Science：`NOT_RUN`
- Policy：`NO_NEW_DECISION`
- P23B：`OPTIONAL / AUTHORIZATION_REQUIRED / NOT_RUN`
- P24：`AUTHORIZATION_REQUIRED / NOT_RUN`

## 背景

P23A 的唯一允许输出是一个有方向的 sender→receiver association evidence score。它不能把
ligand/receptor 共表达、synthetic fixture 或两个内容自洽的 release hashes 改写成 receiver
response、effect size、干预效应或因果结论。

P22 已提供 `vc.virtual-cell-release.v1` 的 immutable content closure，但默认 curated registry
仍 absent/empty，本轮也没有读取 registry、验证 lifecycle/authentication 或导入 release。P18
提供 multi-omics typed model-input contract，但本轮没有读取真实 P18 Pack/model input 或验证
observation membership。P20/P21 identities 也只有 caller-supplied fixture references；没有可信
P21B execution、模型 artifact 或 benchmark result。

因此，P23A 必须把「结构可验证」和「外部事实已验证」严格分开，并在没有授权的情况下只提供
local synthetic conformance。

## 决策

### 1. 输入绑定两个 exact release closure，但不声称 registry truth

`InteractionEndpointV1` 分别固定 `sender` 和 `receiver` role，并重新验证 exact P22
`VirtualCellReleaseV1`、release fingerprint、Virtual Cell context fingerprint、P19 factory
registration fingerprint 和 Pack fingerprint 的闭包关系。两个 endpoint 还必须具有相同 organism
和 P18 taxonomy。

这只验证对象内部的 immutable content closure。两个 endpoint 的
`registry_state_verified` 被类型固定为 `false`；P23A 不读取 P22 store/checkpoint，不检查
cataloged/revoked/superseded state，也不认证 registry authority。Release 中携带的 P19/P12/P21
依赖不能由 P23A 重新推导为可信 evidence、policy 或 execution。

### 2. P18 identity 是 typed、content-bound、unverified reference

`P18EndpointIdentityV1` 明确引用 `vc.multiomics-model-input.v1`，绑定 model-input、Pack、view、
observation semantics、join、modality 和 observation identities。它与 endpoint Pack fingerprint、
organism 和 same-experiment sender/receiver observation 做交叉核对。

`identity_role` 固定为 `declared_p18_contract_fixture_reference`；
`p18_contract_verified=false`、`observation_membership_verified=false`。P23A 不接受一个裸 hash
来声称 P18 contract 已验证，也不读取矩阵、Pack rows 或 mapping。

### 3. Same-experiment 采用一个不可拆分身份

`SameExperimentInteractionEvidenceV1` 在同一个 strict frozen object 中绑定：

- dataset、platform、evidence asset 和 evidence record fingerprints；
- experiment、donor、sample、well、condition、dose 和 time；
- sender/receiver roles 与各自 observation ID；
- ligand、receptor、evidence namespace/version/fingerprint；
- ligand/receptor mapping asset fingerprint。

合同没有第二个 receiver dataset 字段，因此不能表达或静默接受跨无关数据集伪配对。CURIE prefix
必须与声明 namespace 一致，数值必须 finite、非负且 JSON-safe。尽管 identity 完整，
`evidence_asset_verified=false` 和 `paired_linkage_verified=false` 仍被类型固定；真实 asset bytes 和
same-experiment linkage 本轮都没有验证。

### 4. Scorer 只保存不可信 P20/P21 references

`InteractionScorerFixtureV1` 固定 model release/artifact、benchmark bundle/protocol/run/result、
P21B execution 和 adapter fingerprints。Canonical baselines 的顺序和值只能是：

```text
no_interaction
receiver_only
lr_coexpression
```

Canonical OOD axes 的顺序和值只能是：

```text
sender, receiver, ligand, donor, dataset, platform, dose_time
```

这些字段只是 declared identities。`p20_p21_bindings_verified`、`trusted_p21b_execution`、
`model_artifact_verified`、`real_model_execution_authorized` 和
`real_model_execution_performed` 全部被类型固定为 `false`。P23A 不训练、不调参、不执行模型，
也不根据这些 hashes 计算 evidence score。

### 5. 复用 P13 Adapter SDK，但没有 runtime

`CellInteractionEvidenceAdapter` 复用 P13 `VirtualCellModelAdapter`、strict input/output contracts、
`PreparedAdapterInput`、output envelope、execution provenance 和 deterministic conformance。Adapter
identity、input contract 和 output contract fingerprints 分别为：

- `6ca0a23373d6a0599c5b6055b4696a76dbd64d6317c656d11fab790b74be1467`；
- `83725f4a5753f4f9eec0ccea3405a35785fc9518ac1edbcb9cd4055dd6709f7d`；
- `2d27ac18d44d0fdab09c42107cc2ad45a3a9f920c706f37cebfe767270d4a12a`。

Prepared input 绑定 exact request 和 complete interaction-input fingerprint，但 `pack_fingerprint`、
values、shape、feature contract 和 alignment 均为空。Request 不允许 receiver intervention，且必须
精确声明有方向 pair、paired evidence modality、canonical baselines 和 unit-interval score。

模块没有 loader、filesystem/network I/O、legacy communication import、model execution、registry
mutation、aggregation policy、HTTP/API/UI wiring 或默认 adapter registration。Standalone envelope
validation/projection 被禁用；所有 output 必须与 exact prepared input 和 provenance 重新绑定。

### 6. 唯一 projection 是 supplied synthetic fixture score

唯一 non-abstaining status 为 `synthetic_conformance`。Wrapper 可携带一个由测试调用方提供的 finite、
JSON-safe、`[0, 1]` scalar；它不是 P23A 计算结果，也不是模型输出。Envelope 固定：

- shape `(1,)`，unit `dimensionless`；
- uncertainty 不可用且未校准；
- `record_role=synthetic_conformance_not_evidence`；
- score semantics 为 `association_evidence_only`；
- score source 为 `supplied_contract_fixture_not_model_output`；
- real data/model execution、asset/linkage、P20/P21 binding、registry state、baseline comparison、
  paired CI、receiver response 和 causal claim metadata 全部为 `false`。

对外 projection 的 exact key set 是：

```json
{"interaction_evidence_score":[0.625]}
```

`receiver_response`、`receiver_response_delta`、`effect_size`、`treatment_effect`、causal text 和
legacy co-culture fields 在 wrapper、nested prediction 与 projection 任一层都 fail closed。

### 7. Gate failure 是 value-free abstention

允许的 failure status/reason 固定为：

| Status | Exact reason | 额外要求 |
|---|---|---|
| `missing_paired_evidence` | `missing_paired_evidence` | 无 score |
| `baseline_gate_failed` | `baseline_gate_not_met` | 无 score |
| `unsupported_scope` | `unsupported_interaction_scope` | 必须带 canonical OOD dimensions |
| `execution_not_authorized` | `p23a_real_execution_not_authorized` | 无 score |
| `registry_state_unverified` | `curated_release_state_unverified` | 无 score |

Abstention 的 values/shape 为 `null`，projection metadata 为空，且禁止 projection。Unknown、重复、
重排或无解释 OOD dimensions 均被拒绝。

### 8. Canonicalization 防御包含 subclass、Mapping 和 cycle

所有 P23 objects 都是 strict、frozen、extra-forbid，并使用 canonical JSON SHA-256 identity。
跨 P22/P18/P13 边界前会检查 undeclared model fields；Pydantic subclass、`model_copy` 注入字段、
generic `Mapping`/`UserDict` 嵌套、循环 mapping/list 和 stale nested fingerprints 不能在 dump/
normalization 中被静默丢弃。Envelope provenance 必须精确绑定 prepared input、request、adapter、
contracts 和 compatibility fingerprint；伪造或漂移会 fail closed。

## 验证与完成身份

| Evidence | Frozen value |
|---|---|
| completion code SHA / tree / epoch | `2b894966cd00b2af2fafbf8f009566dd69f393a7` / `00bd98b0fd14091f4528115dcc66730264d5803a` / `1786061504` |
| focused | `107 passed in 41.71s` |
| affected | `495 passed, 1 skipped in 116.55s` |
| safe | `1,787 passed, 49 skipped, 387 deselected in 367.11s` |
| legacy | `1,147 passed, 58 skipped, 105 deselected in 57.38s` |
| reproducible wheel | `praxis_virtualcell-1.6.0-py3-none-any.whl`；`1,226,514` bytes；SHA-256 `e78f40f0f4fe7354e3c660d6612a8ee60a1b2dd61af2fc606a67d01e67ac601e`；`373` entries / React `14` / tests `0` / AppleDouble `0` |
| module source / wheel | SHA-256 `d1ba8d8054bf91c4a54a215c331fef65557df3954dba730998821ea9f70743cd`；exact match |
| test source | SHA-256 `269c387423a41864031bb54fbbc692b84da0cbae5137db9fd6cbc077302d3081` |
| two independent builds | byte-identical；npm offline；Python `--no-isolation --skip-dependency-check` |

Packaging 使用当前已安装 toolchain，从 completion SHA 的独立 source archives 构建。这只证明 exact
local source/toolchain 的 byte reproducibility 和 wheel content integrity；它不是 pinned dependency
closure、clean-install、publication 或 release evidence。

## 后果与下一 gate

P23A engineering 完成不新增真实 cell-interaction capability。没有读取 sender/receiver release、Pack、
paired/co-culture/spatial data、mapping 或 model artifact；没有 model run、baseline comparison、paired CI、
OOD science、scientific validation、promotion、registry mutation、release 或 deploy。Science 为
`NOT_RUN`，policy 为 `NO_NEW_DECISION`。

P23B 是可选且独立的 receiver-response 授权窗口，需要 exact intervention data、estimand、assumptions、
frozen protocol 和 P21B candidate/evidence identity。若跳过 P23B，P24 也不能用一个 synthetic
contract-only scaffold 自动推进：它是 First Real Community Adapter，必须先获得 exact real
mono/co-culture assets、mapping、fixed P20/P21 model 和 write-new output window 的授权。当前两者均为
`AUTHORIZATION_REQUIRED / NOT_RUN`。

2026-08-08 follow-on：后续持续本地授权把 P25 拆为 E/R/policy 窗口，并允许独立 P25E
contract-only engineering。P25E 已完成 value-free abstention，但没有冒充或完成 P24，也没有
授权 P25R；P24/P25R 仍为 `AUTHORIZATION_REQUIRED / NOT_RUN`。当前下一 eligible local unit 是
同样只能 fail closed 的 P26E contract/DAG/matching/abstain software。

操作边界见 [P23A runbook](runbooks/CELL-INTERACTION-EVIDENCE.md)，完整证据见
[P23A completion report](../reports/phase23a/PHASE23A_COMPLETION.md)。
