# P26E Host–Microbiome Contract 操作手册

> 状态：`COMPLETE — CONTRACT_ONLY / VALUE_FREE_ABSTENTION`
>
> Completion code SHA：`5bd3e502a7a1f1cb0fd1b79ecfd109eeeaf265c4`
>
> Science：`NOT_RUN`
>
> Policy：`NO_NEW_DECISION`
>
> P26R：`BLOCKED_EXTERNAL / NOT_RUN`

## 1. 适用范围

本手册只核验 P26E exact host/P25 identity、typed missing interface、time-unrolled DAG、negative
P22 audit 和 value-free compilation。它不授权外部资产、P26R、训练、模型执行、registry mutation、
operator promotion、P27B/P27C、发布或部署。

```text
praxis_virtualcell/host_microbiome.py
praxis_virtualcell/tests/test_host_microbiome.py
```

## 2. Freeze 顺序

1. Host 必须是 exact `VirtualCellRequestV2`，有 explicit cell type、tissue 和一个 requested output；
2. P25 输入必须是 exact `VirtualMicrobiomeContractV1`，role 为 `p25e_contract_only`；
3. Current `RegisteredCommunityPack`、member bytes、scope 和 contract fingerprints 必须重验；
4. Host Pack/release fingerprints 只能同时 absent 或同时 present；
5. Host context 从完整 request 确定性派生，但不能替代 full-request binding；
6. Interface、DAG、joint scope 和 outer contract fingerprints 必须重算闭合；
7. Community/matching release、interface mapping 和 output/input bindings 必须保持 `null`。

任一 nested `model_copy`、undeclared field、LLM verdict、stale hash 或 P25 byte drift 都必须 reject 或
abstain；不能重签后升级状态。

## 3. P22 host audit

`audit_host_release_candidate()` 只读取 caller 提供的 exact `CuratedVirtualCellRegistry` projection，
并重验 external checkpoint/lifecycle。它不写 registry，也不把 P22 context candidate 解释为 full request。

即使 catalog row 为 active、benchmark-passed、scientifically-validated、promotion-eligible 和
production-promoted，最高 audit status 仍是：

```text
p22_context_matched_request_binding_insufficient
```

此时 `exact_request_match_verified=false`，full-request science/policy 为 `null`。K562 或其他不同
cell context 必须得到 `release_mismatch`；不要更改 host request 迎合已有 release。

## 4. Interface 与 DAG

Interface 固定要求 metabolite/cytokine/receptor，以及 namespace/version/id、compartment、dose/unit、
time/unit identities。当前 mapping、source output、target input 均 unavailable；禁止 implicit conversion、
imputation 和 causal claim。

DAG 只能是：

```text
community_state_t0
→ mediator_state_t1
→ host_state_t2
→ community_state_t3
```

任何重排、回边、额外 node/edge、execution step 或 caller/LLM candidate 都必须拒绝。该拓扑只表达
future dependency order，不表示真实时间动力学或执行。

## 5. Compile 与 expected abstention

Compile 前再次运行 P25 planning 以检查 current community/member bytes。正常 contract-only fixture 的
mandatory ordered reasons 是：

```text
matching_host_release_unavailable
matching_community_release_unavailable
matching_release_unavailable
cross_domain_interface_unavailable
p26_real_execution_not_authorized
```

P25 scope/bytes 漂移时在首位增加 `unsupported_host_microbiome_scope`。所有输出都必须保持 empty steps、
non-executable、prediction/host/community/mediator `null`。禁止 fallback、partial numeric result、zero fill、
legacy predictor 或 LLM numerical output。

## 6. 定向核验

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_host_microbiome.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -ra \
  praxis_virtualcell/tests/test_host_microbiome.py \
  praxis_virtualcell/tests/test_virtual_microbiome_contract.py \
  praxis_virtualcell/tests/test_community_packs.py \
  praxis_virtualcell/tests/test_curated_registry.py \
  praxis_virtualcell/tests/test_virtual_experiment.py

python -m ruff check praxis_virtualcell/host_microbiome.py \
  praxis_virtualcell/tests/test_host_microbiome.py --no-cache
python -m ruff format --check praxis_virtualcell/host_microbiome.py \
  praxis_virtualcell/tests/test_host_microbiome.py
```

Frozen results are focused `8 passed`, adjacent `144 passed`, safe
`1,817 passed / 49 skipped / 387 deselected / 387.09s`, and legacy
`1,147 passed / 58 skipped / 105 deselected`. Synthetic P22/P25 fixtures are engineering conformance only。

## 7. 故障处置

| Symptom | Required action |
|---|---|
| P22 context matches but full request binding is absent | retain insufficient-binding audit; never promote |
| K562/different tissue appears as candidate | reject as mismatch; no host substitution |
| P25 member bytes drift | add unsupported-scope reason; no identity refresh |
| community or matching release hash is supplied to P26E schema | reject; use a future independently versioned release schema |
| mapping/unit/mediator binding is absent | retain interface reason and all values `null` |
| steps/prediction/authority field is injected | reject even if outer ID is recomputed |
| registry checkpoint is absent or stale | retain negative audit; no lifecycle assumption |
| `pip check` fails in shared environment | record failure; do not mutate dependencies without authorization |

## 8. P26R 独立授权窗口

P26R 至少需要 exact full host request binding、active host release、future multi-Pack community release、
matching release、typed mapping/output/input contracts，以及两侧 exact positive science 和 named-operator
production policies。还必须冻结 paired data、intervention/estimand、privacy/consent、donor/batch/experiment
split、baselines、metric/direction/CI、OOD/external policy、read-only assets、write-new output root、compute/
network boundary 和 rollback。

任一项缺失即 No-Go。P26E contract、P22 context match、P25E fixture、K562 或 synthetic registry row 都
不能授权 P26R。

## 9. P27A-E historical handoff 与后续状态

这是 P26E 完成时的 handoff：P27A-E 应从实际 P26E docs-closure HEAD 开始。它随后已从
`a12cf4f4b71efb653f8128afcb1f468211fdb837` 开始，在 code
`5875571bf9d8b518dc7a857feb935206f756de59` 完成 strict experiment-design contracts 与
rank-then-reveal synthetic harness。P27A-R historical replay 仍为
`REPLAY_NOT_RUN / ASSET_PENDING`；P27B/P27C 分别为
`AUTHORIZATION_REQUIRED / SHADOW_NOT_RUN` 与 `AUTHORIZATION_REQUIRED / PILOT_NOT_RUN`。
当前下一本地 work unit 是 P28E contract-only orchestrator/typed handoff/trace/abstention；真实
P28 acceptance 为 `0/3`。

Design rationale: [ADR-0022](../ADR-0022-host-microbiome-contract.md). Frozen evidence:
[P26E completion report](../../reports/phase26e/PHASE26E_COMPLETION.md).
