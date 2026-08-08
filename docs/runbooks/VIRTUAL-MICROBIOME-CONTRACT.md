# P25E Virtual Microbiome Contract 操作手册

> 状态：`COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`
>
> Completion code SHA：`039393e6be897b3014bb0b657d0a439d879578b6`
>
> Science：`NOT_RUN`
>
> Policy：`NO_NEW_DECISION`

## 1. 适用范围

本手册只用于检查 P25E local contract、identity closure、P10 regression 和 value-free
abstention。它不授权读取新资产、运行 P24/P25R、训练、benchmark、registry mutation、operator
promotion、发布或部署。

模块与定向测试：

```text
praxis_virtualcell/community_packs/virtual_microbiome.py
praxis_virtualcell/tests/test_virtual_microbiome_contract.py
praxis_virtualcell/tests/test_community_packs.py
```

## 2. Freeze 核对顺序

1. 输入必须是 exact `RegisteredCommunityPack`；
2. community fingerprint 必须匹配 current manifest bytes；
3. 每个 member Pack reference/id/version/fingerprint 必须闭合；
4. 从每个 Pack root 重新注册并验证 current bytes；
5. 成员数必须为 2 或 3，member/Pack/strain identities 均 ordered、unique；
6. 每个成员必须具有 exact taxonomy、assembly 和一个显式 strain identity term；
7. abundance 必须为正并精确合计为一；
8. medium、compartment、time 和 well-mixed space 必须完整；
9. primary endpoint、adapter requirement 和 outer contract fingerprints 必须重算一致。

任一项失败都应返回 `VirtualMicrobiomeContractError`，不能删字段、补默认值、重排成员、推断
strain、补零或切换到 legacy predictor。

## 3. Exact request 与 planning

Request 必须逐项匹配：task、output、community、ordered member Pack fingerprints、medium、time、
scope、endpoint 和 adapter requirement fingerprint。Planning 会再次从 current Pack bytes 重建
完整 scope；只要任一 identity drift，就必须包含 `stale_community_identity` 或
`unsupported_virtual_microbiome_scope`。

即使所有 request identity 完全匹配，当前 gate reasons 仍必须完整保留：

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

Plan 永远是 empty steps、non-executable。Result 永远 abstains，primary/secondary prediction 都是
`null`，science/promotion/policy 状态都是 false。

## 4. Primary endpoint 与 baseline/OOD 解释

P25E 只声明 exact end-time ordered strain abundance fraction vector。Metric 是 mean absolute
error，lower is better，fixture threshold 是 `0.1`。该 threshold 是 future science gate 的
preregistration shape，不是已经通过的指标。

Required baselines 的顺序固定为：

```text
persistence, independent_monoculture, no_interaction
```

Required OOD axes 的顺序固定为：

```text
member, medium, initial_abundance, time, condition, batch
```

P25E 没有运行任何 baseline 或 OOD evaluation。删项、加项、重排或把某个 gate fingerprint 从
`null` 改成 caller-provided hash 都必须拒绝。

## 5. P10 regression

P10 `community_packs/contracts.py` 必须保持 SHA-256
`352892defdd1198263e9c57670da1d485da6d4740a31faafb7866e95b3c157dd`。其 canonical
CommunityPack/ledger/validation/plan/result fingerprints 与 plan ID 见
[completion report](../../reports/phase25e/PHASE25E_COMPLETION.md#5-p10-v1-byte-and-semantic-regression)。

如果任一 P10 golden 漂移，先停止 P25E/P26E 接线并审计原因。不得更新 golden 来掩盖非预期
serialization、fingerprint 或 abstention 变化。

## 6. 定向核验

```bash
pytest -q \
  praxis_virtualcell/tests/test_virtual_microbiome_contract.py \
  praxis_virtualcell/tests/test_community_packs.py
ruff check \
  praxis_virtualcell/community_packs/virtual_microbiome.py \
  praxis_virtualcell/community_packs/__init__.py \
  praxis_virtualcell/tests/test_virtual_microbiome_contract.py \
  praxis_virtualcell/tests/test_community_packs.py
```

Frozen P25E focused result is `21 passed`; P25E + P10 adjacent result is `60 passed`. Full local
evidence is recorded in the completion report.
All fixtures are checked-in, tiny and synthetic. They must not be written to a P21 evidence ledger or
represented as P25R science.

## 7. 故障处置

| Symptom | Required action |
|---|---|
| Pack bytes/fingerprint drift | reject freeze/plan; do not refresh identity silently |
| non-microbial or missing strain identity | reject scope; do not infer taxon/strain |
| wrong member order/abundance/medium/time | abstain as unsupported scope |
| missing adapter/model/environment/mapping | retain explicit gate reason and `prediction=null` |
| benchmark/evidence/policy hash supplied to P25E negative record | reject payload; use separately authorized P25R/P21C records |
| secondary output supplied | reject; secondary cannot rescue primary |
| P10 golden drift | stop integration and audit v1 bytes/semantics |
| `pip check` fails in shared environment | record failure; do not install or mutate environment without authorization |

## 8. P25R 独立授权窗口

真实 P25R 至少需要一个完整窗口冻结：exact 2–3 strain members、Pack roots and hashes、medium、
initial abundance、time、one primary endpoint、mapping asset、fixed P24/P20/P21 adapter/model/
environment/checkpoint/protocol identities、biological-group split、baselines、metric/direction/CI、
OOD/external policy、license/source/privacy、read-only inputs、write-new output root、compute/network
boundary and rollback.

缺少任何字段时不得读新资产或运行模型。Negative result is valid and must preserve abstention.
Positive promotion-eligible evidence still does not create product policy; that requires an independent
named-operator P21C decision.

## 9. P26E handoff

P26E may consume only immutable P25E contract identity as a typed missing prerequisite. It must not mark
the community executable, scientifically validated or production promoted. Real host–microbiome execution
requires exact promoted host and community releases plus an exact matching release; K562 is not a valid
substitute for a missing host context.

Design rationale: [ADR-0021](../ADR-0021-virtual-microbiome-contract.md).
