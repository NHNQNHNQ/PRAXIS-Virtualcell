# P23A Cell Interaction Evidence 操作手册

> 状态：`COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE`
>
> Completion code SHA：`2b894966cd00b2af2fafbf8f009566dd69f393a7`
>
> Science：`NOT_RUN`
>
> Policy：`NO_NEW_DECISION`

## 1. 本手册适用范围

本手册只说明如何检查 P23A local contract 和 synthetic conformance。它不授权读取外部
sender/receiver assets、运行模型、访问 P22 registry、登记 release、执行 P21B、研究 receiver
response 或生成因果结论。

当前模块：

```text
praxis_virtualcell/model_zoo/cell_interaction_evidence_contract.py
```

当前测试：

```text
praxis_virtualcell/tests/test_cell_interaction_evidence_contract.py
```

## 2. 安全解释规则

P23A 的唯一投影形状为：

```json
{"interaction_evidence_score":[0.625]}
```

该数值只能在 `prediction_status=synthetic_conformance` 时作为调用方提供的 contract fixture
通过验证。它的范围是 `[0, 1]`，shape 是 `(1,)`，unit 是 `dimensionless`，语义是
`association_evidence_only`。它不是模型计算结果、scientific evidence、receiver response、effect
size 或 causal claim。

任何 UI、API、report 或集成层都不得把 synthetic projection 标为预测。P23A 没有 HTTP/UI/runtime
wiring，也没有进入 `DEFAULT_ADAPTER_REGISTRY`；除测试或明确的 local contract inspection 外，不应
把它接入请求执行路径。

## 3. 输入核对顺序

按以下顺序 fail closed；不要根据后续字段补足前一层未验证状态。

1. 重新解析 exact sender 与 receiver `VirtualCellReleaseV1`；
2. 对每个 endpoint 核对 release/context/P19 registration/Pack fingerprints；
3. 核对 typed P18 model-input/view/observation/modality identities；
4. 将 P18 Pack、organism/taxonomy 和 observation 与 endpoint/same-experiment identity 交叉绑定；
5. 核对一个不可拆分的 dataset/platform/experiment/donor/sample/well/condition/dose/time identity；
6. 核对 ligand/receptor/evidence namespaces 和 mapping asset fingerprint；
7. 核对 scorer 声明的 adapter、model、benchmark 和 P21B references；
8. 核对 canonical baselines 和 OOD axes；
9. 核对 exact `vc.request.v2` task/output/direction/modalities/baselines/constraints；
10. 生成并保存 prepared-input fingerprint，后续 envelope/projection 必须回绑该 identity。

结构通过后仍必须保留以下事实：

```text
sender.registry_state_verified = false
receiver.registry_state_verified = false
p18_contract_verified = false
observation_membership_verified = false
evidence_asset_verified = false
paired_linkage_verified = false
p20_p21_bindings_verified = false
trusted_p21b_execution = false
model_artifact_verified = false
real_data_authorized = false
real_model_execution_authorized = false
real_model_execution_performed = false
scientifically_validated = false
promotion_eligible = false
production_promoted = false
```

如果调用方需要把任一值改为 `true`，当前 P23A schema 会拒绝。不要绕过 schema；应停止并进入对应的
真实数据/执行/benchmark/operator 授权窗口。

## 4. Canonical baselines 与 OOD

Baselines 只能按以下顺序出现：

```text
no_interaction, receiver_only, lr_coexpression
```

这只是预注册形状；P23A 没有实际运行这些 baseline。不得把 legacy Kang/LR coexpression 或
co-culture proxy 当作已完成 comparison。

OOD axes 只能按以下 canonical 顺序取其有序子集：

```text
sender, receiver, ligand, donor, dataset, platform, dose_time
```

只有 `unsupported_scope` 可带 OOD，且必须使用 reason
`unsupported_interaction_scope`。Unknown axis、重排、空 dimensions 配 detected=true、或
detected=false 仍携带 dimensions/reason 都会拒绝。

## 5. Output 与 abstention

### 5.1 Synthetic conformance

Non-abstaining wrapper 必须逐字段精确满足：

- status 是 `synthetic_conformance`；
- record role 是 `synthetic_conformance_not_evidence`；
- prediction 只含 score、`unit_interval` scale 和 `association_evidence_only` semantics；
- score 是 finite、JSON-safe、非 bool 且位于 `[0, 1]`；
- uncertainty 是 exact unavailable/un-calibrated record；
- OOD 是 not detected；
- interaction fingerprint 与 prepared input 完全一致。

输出 metadata 会明确保存所有未运行/未验证 gate 为 `false`，并将 score source 标为
`supplied_contract_fixture_not_model_output`。Projection 会删除 metadata，只留下唯一 score key；
因此消费方必须同时保留 envelope/provenance，不能脱离上下文把 projection 作为 evidence。

### 5.2 Value-free abstention

| Wrapper status | Exact abstain reason | Projection |
|---|---|---|
| `missing_paired_evidence` | `missing_paired_evidence` | 禁止 |
| `baseline_gate_failed` | `baseline_gate_not_met` | 禁止 |
| `unsupported_scope` | `unsupported_interaction_scope` | 禁止 |
| `execution_not_authorized` | `p23a_real_execution_not_authorized` | 禁止 |
| `registry_state_unverified` | `curated_release_state_unverified` | 禁止 |

这些 envelope 的 values/shape 必须为 `null`，projection metadata 必须为空。调用方应原样呈现 abstain，
不能调用 LLM、legacy predictor 或默认值填入替代 score。

## 6. 禁止字段与 legacy 隔离

以下类别在 wrapper、prediction、projection、free-text reason 或 nested contract 中一律拒绝：

- receiver response / delta；
- effect/treatment effect；
- causal claim、activation 或 chain completion；
- legacy `ctrl`、`stim`、`fold_change`；
- legacy `step1_communication`、`step2_receiver_response`、`chain_complete`。

不要 import 或调用 `LRCommDB`、`CellStateDB`、`run_communication_case`、
`run_coculture_case`。P23A source 有静态测试确保没有这些 runner、AnnData/Scanpy、network、Path 或
`open()` 调用。

## 7. 定向核验

在 completion code SHA 上可运行：

```bash
pytest -q praxis_virtualcell/tests/test_cell_interaction_evidence_contract.py
```

Frozen focused 结果是 `107 passed in 41.71s`。完整 recorded matrix：

| Gate | Result |
|---|---|
| focused | `107 passed in 41.71s` |
| affected | `495 passed, 1 skipped in 116.55s` |
| safe | `1,787 passed, 49 skipped, 387 deselected in 367.11s` |
| legacy | `1,147 passed, 58 skipped, 105 deselected in 57.38s` |

测试全部使用 synthetic identities、Python objects 和现有 repository fixtures；没有真实 asset/model
I/O、network、training、GPU、registry mutation、science 或 policy action。

重点 negative/adversarial coverage：

- stale release/context/P19 registration/Pack/P18/interaction fingerprints；
- sender/receiver role、organism、taxonomy、observation 或 direction drift；
- 缺失 same-experiment field、第二 dataset、bad hash/CURIE/quantity；
- canonical baseline/OOD 顺序和值漂移；
- bool/string/NaN/Inf/unsafe integer/out-of-range score；
- response/effect/causal/legacy fields 在每一层注入；
- Pydantic subclass 与 `model_copy` undeclared fields；
- generic `Mapping`/`UserDict` 和 cyclic nested mappings；
- forged prepared-input/envelope provenance；
- standalone projection/validation、aggregation、legacy runner 和 default registration bypass。

## 8. Packaging 证据如何解释

Completion wheel：

```text
filename: praxis_virtualcell-1.6.0-py3-none-any.whl
size: 1,226,514 bytes
sha256: e78f40f0f4fe7354e3c660d6612a8ee60a1b2dd61af2fc606a67d01e67ac601e
entries: 373
React entries: 14
test entries: 0
AppleDouble entries: 0
```

两个独立 source archives 使用 npm offline 和当前已安装 Python toolchain 的
`--no-isolation --skip-dependency-check` 构建，wheel byte-identical，ZIP 检查通过。Source/wheel 中
`cell_interaction_evidence_contract.py` SHA-256 都是
`d1ba8d8054bf91c4a54a215c331fef65557df3954dba730998821ea9f70743cd`。

这不是 pinned dependency closure、clean install、发布、release 或 deploy 证据。

## 9. 故障处置

| 症状 | 正确处置 |
|---|---|
| registry 未验证 | 返回 `registry_state_unverified` abstention；不要读取或修改 registry |
| paired evidence 缺失 | 返回 `missing_paired_evidence` abstention；不要跨 dataset 配对 |
| baseline 未过门 | 返回 `baseline_gate_failed` abstention；不要保留 score |
| scope/OOD 不支持 | 返回 `unsupported_scope` 和 canonical dimensions |
| execution 未授权 | 返回 `execution_not_authorized`；不要运行 artifact |
| provenance 漂移 | 拒绝整个 envelope；不要重算/修补 fingerprint |
| 出现 response/causal 字段 | 拒绝 payload；不要降级到 legacy runner |

## 10. 后续授权边界

P23B 与 P24 都不是本手册自动允许的下一步。P23B 是可选 receiver-response science 窗口；P24 是
First Real Community Adapter，不存在可先做的无资产 fake contract-only scaffold。当前两者均为
`AUTHORIZATION_REQUIRED / NOT_RUN`。唯一合并授权草案见
[P23A completion report](../../reports/phase23a/PHASE23A_COMPLETION.md#后续唯一合并授权草案)。

2026-08-08 follow-on：后续持续本地授权已允许并完成独立 P25E contract-only/value-free
abstention work unit。它不改变本手册的 P24 real-only 边界，也不授权 P25R。当前 P24/P25R
仍未运行；P26E 只可继续 contract/DAG/matching/abstain software，不能执行 host–microbiome
模型或生成 prediction。

设计理由见 [ADR-0020](../ADR-0020-cell-interaction-evidence-contract.md)。
