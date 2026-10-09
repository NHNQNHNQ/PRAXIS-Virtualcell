# ADR-0023：Agentic experiment design contract 与 rank-then-reveal replay

- 状态：Accepted（P27A-E engineering `COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE_ONLY`）
- 日期：2026-08-08
- Starting SHA / active baseline：`a12cf4f4b71efb653f8128afcb1f468211fdb837`
- Completion code SHA：`5875571bf9d8b518dc7a857feb935206f756de59`
- Completion tree：`a7c65e7b30f51832660e66323b5946acbddcbf18`
- Source date epoch：`1786180822`
- 分支：`codex/p25e-virtual-microbiome`
- Engineering：`COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE_ONLY`
- Historical replay：`REPLAY_NOT_RUN / ASSET_PENDING`
- Science：`NOT_RUN`
- Policy：`NO_NEW_DECISION`
- P27B：`AUTHORIZATION_REQUIRED / SHADOW_NOT_RUN`
- P27C：`AUTHORIZATION_REQUIRED / PILOT_NOT_RUN`

## 背景

P27A 要求可审查的 Virtual Experiment、action/cost/control/batch/feasibility 合同，以及不会用
hidden outcome 选择实验的 offline replay。现场没有 canonical local historical replay pool：现有 M1
ledger 把 selection-time features 与 outcomes 放在同一记录，缺 P27 manifest、license、完整设计字段、
模型 identity 和 structural outcome separation；Golden Norman 真实资产仍是 remote；P9 和 tiny Packs
只能作为 contract/synthetic fixtures。

因此 P27A 拆为两个独立 work units：P27A-E 在 standing local authorization 下完成 strict software 与
synthetic conformance；P27A-R 只有 exact canonical asset manifest、license 和 outcome-separation identity
齐备后才运行。P27A-E 不能把 synthetic utility 写成 information gain、scientific evidence 或 product policy。

## 决策

### 1. Product design 固定为空 action space

`vc.virtual-experiment.v1` 的 compiler 接受 exact、递归重验的 `VirtualCellRequestV2`，但公开 record
只保留 `request_id`、full request fingerprint 和确定性派生的 cell/perturbation/constraint identities。
原始 request metadata、constraint values、asset paths 和 secrets 不进入 public bytes。

当前没有 exact-request executable + scientifically validated + production-promoted action domain，
因此 model、Pack、evidence、policy 和
action-catalog fingerprints 都为 `null`；control、replicate、cost 为 `null`，batch 与 selected actions 为空。
Design 固定 `abstain=true`、`executable=false`、`human_approval_status=required_not_granted`。Question 与
hypothesis 只是 prose；P27A-E 没有 LLM candidate/action-space API，prose 不能设置数值、scope、feasibility、
uncertainty、OOD、science、policy 或 verdict。

### 2. Synthetic action catalog 不能成为真实建议

`vc.experiment-action.v1` 覆盖 request/cell/model/Pack/compatibility/step/evidence/calibration/OOD identities，
以及 perturbation、control、replicate、batch、endpoint、cost、constraint 和 feasibility。其 status 被 Literal
锁定为 synthetic conformance、real domain unverified、science false、policy false、external execution false。
Endpoint 与 cost units 只锁定当前 synthetic fixture 的 exact literals，不建立通用 unit registry。

Selection view 要求 comparator actions 使用同一 cell/model/Pack/evidence/calibration/OOD/endpoint/unit domain。
Request/compatibility/step identities可以随 perturbation 变化；不允许把跨 domain rows 拼成 comparator pool。

### 3. Selection 与 outcome 在 schema 和 API 上分离

`vc.replay-selection-view.v1` 没有 outcome/label 字段，并明确标记 synthetic partitions 与 leakage audit
unavailable。`select_replay_actions(protocol, selection_view)` 的签名不接受 outcome ledger。Protocol 固定五个
有序策略：

```text
active_heuristic
random
uncertainty_only
diversity
expert_rule
```

所有策略共享 pool、count budget 与 canonical tie-break；random 通过 seed + action ID content hash 排序，
不读 global RNG。`active_heuristic` 只称 heuristic acquisition，不称严格 expected information gain；
`expert_rule` 是预登记静态 baseline，不是 P27B 具名专家 review。

### 4. 所有 receipts 冻结后才 reveal

Outcome-contract fingerprint 从 exact selection view、action→group binding、manifest/split/catalog identities 和
synthetic metric contract 确定性派生，不由 caller 自报。五份 `vc.replay-selection-receipt.v1` 全部固定
`outcome_accessed=false`。Evaluation 必须同时收到 exact protocol、selection view、五份 receipts 和 outcome
ledger；它重新执行全部 deterministic selectors 并逐 byte 比较 receipts。即使 attacker 重算 receipt ID，
改变 selected IDs/fingerprints/uncertainty 仍会被拒绝。

Outcome ledger 必须覆盖 exact catalog，每个 missing value 显式写 `unavailable`，每个失败写 `failed`；
action→group drift 被拒绝。Utility 只对 observed rows 求值，失败/不可用不补零、不静默删除，也不由其他
baseline 挽救 primary。

### 5. Replay result 有严格 maturity ceiling

`vc.replay-result.v1` 绑定 protocol、selection view、outcome ledger 和所有 receipts。它只报告 synthetic
realized utility、cost、failure 与 uncertainty summaries；`primary_passed=null`，comparison verdict 为
`not_scientific`。Historical replay、science、promotion、policy、shadow、prospective、autonomous 与 external
execution 状态都不能由重签 content hash 提升。

### 6. 不接入 legacy ActiveLearning/runtime/LLM candidate

现有 `ActiveLearningAgent` 输出宽松 string queue，缺 exact request/Pack/model/evidence/policy、control、batch、
cost 和 feasibility closure；`information_gain()` 也明确只是 heuristic。因此 P27A-E 没有修改或接入 legacy
queue/runtime，没有 default action registry，也没有 LLM candidate schema。Unknown `candidate` 参数直接拒绝；
question/hypothesis text 不改变 action space、selector、numeric fields 或 verdict。未来若接入，只能把 legacy/LLM
输出当 non-authoritative candidate，并由 exact frozen catalog 与 deterministic validation 裁决。

## 后果

P27A-E engineering 独立完成，P27 umbrella 为 `ENGINEERING_COMPLETE_SCIENCE_PENDING`。P27A-R 保持
`REPLAY_NOT_RUN / ASSET_PENDING`；它需要 exact path/size/SHA/source/license/privacy/consent、selection/outcome
分离、group split、完整 action/control/replicate/batch/endpoint/cost/model identities 和 frozen replay protocol。
如果资产在 Git 外，读取前必须另行授权。

P27B shadow expert review 与 P27C prospective pilot 仍是独立外部授权窗口。P27A-E 没有发送消息、控制设备、
采购、运行实验、训练模型或创建 scientific evidence/product policy。

下一 eligible local work unit 是 P28E contract-only multi-agent orchestrator、typed handoff、trace 与
value-free abstention。真实 P28 acceptance 仍至少需要三个 exact-request、exact-scope、executable、scientifically validated、
production-promoted 的模型模块；rule/advisory/synthetic 模块不计数。

操作边界见 [P27A-E runbook](runbooks/AGENTIC-EXPERIMENT-DESIGN.md)，frozen evidence 见
[P27A-E completion report](../reports/phase27ae/PHASE27AE_COMPLETION.md)。

## 2026-08-08 follow-on

P28E subsequently completed at code `da4bfc042d96f830e2a7e8cdc62ba227c7ace949` as an isolated,
value-free contract surface. It consumed only P27's actual synthetic maturity, kept authoritative roles and
handoffs empty, and left real P28 at `0/3`. The paragraph above is preserved as the historical P27 handoff;
the current next local unit is P29E strict connected-subgraph contract plus authoritative
empty-graph/value-free abstention. See
[ADR-0024](ADR-0024-multi-agent-biology-contract.md).
