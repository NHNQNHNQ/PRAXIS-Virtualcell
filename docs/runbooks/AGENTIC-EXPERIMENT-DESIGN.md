# P27A-E Agentic Experiment Design 操作手册

> 状态：`COMPLETE — CONTRACT_ONLY / SYNTHETIC_CONFORMANCE_ONLY`
>
> Completion code SHA：`5875571bf9d8b518dc7a857feb935206f756de59`
>
> Historical replay：`REPLAY_NOT_RUN / ASSET_PENDING`
>
> Science：`NOT_RUN`
>
> Policy：`NO_NEW_DECISION`

## 1. 适用范围

本手册只核验 P27A-E strict Virtual Experiment/action/replay contracts、deterministic rank-then-reveal
harness、synthetic fixture 和 human-approval/status ceilings。它不授权 P27A-R historical asset read、P27B
shadow expert review、P27C prospective pilot、外部消息、设备、采购、实验、训练、promotion、发布或部署。

```text
praxis_virtualcell/experiment_design.py
praxis_virtualcell/tests/test_experiment_design_replay.py
```

## 2. Product design freeze

调用 `compile_contract_only_experiment()` 时：

1. request 必须是 exact `VirtualCellRequestV2`；nested subclass、undeclared field 或 `model_copy` type drift 拒绝；
2. task 必须只有一个 requested endpoint；
3. public record 只保存 request ID/fingerprint 和派生 scope fingerprints，不保存 raw metadata/constraints；
4. question/hypothesis 只能是 prose，不能提供 candidate action、numeric protocol 或 verdict；
5. model/Pack/evidence/policy/action catalog 必须保持 `null`；
6. control/replicate/cost 为 `null`，batch/selected actions 为空；
7. human approval 为 required/not granted，execution/science/policy 全部 false。

任何调用者若需要真实 action suggestion，应先建立 exact-request executable + scientifically validated +
production-promoted model domain；不得用 synthetic
catalog、legacy ActiveLearning string queue、K562 邻域或 LLM 文本填补。

## 3. Synthetic selection view

Synthetic action 必须包含 exact identity、control/replicate/batch/endpoint/cost/feasibility 字段，但 status 固定：

```text
record_role = synthetic_conformance_action
real_model_domain_verified = false
scientifically_validated = false
production_promoted = false
external_execution_allowed = false
```

Selection view 不得出现 realized utility、label、outcome status 或 outcome path。Comparator rows 必须共享
cell/model/Pack/evidence/calibration/OOD/endpoint/unit domain。Synthetic partition names 和
`leakage_audit_status=unavailable_synthetic_conformance` 不能改写为 historical 或 leakage-passed。

## 4. Protocol 与五个 selectors

`freeze_replay_protocol()` 从 exact selection view 派生 manifest/split/catalog/view/outcome-contract identities，
固定 count budget、seed、canonical action-ID tie-break 和五个有序策略。Budget 大于 pool 时 fail closed。

`select_replay_actions()` 只接受 protocol 与 selection view。它不能接收 outcome ledger，也不能 import oracle。
所有 receipts 必须先冻结，且 `outcome_accessed=false`。相同 input/seed 产生 bit-identical receipts；仅改变
outcome values 不得改变任何 receipt。

## 5. Reveal 与 evaluate

`evaluate_replay()` 的顺序是：

1. exact revalidate protocol、view、receipts 和 ledger；
2. 要求五份 receipts 按 canonical strategy order 全部存在；
3. 重新运行 deterministic selectors 并逐 byte 比较 receipts；
4. 重算 outcome-contract fingerprint；
5. 要求 ledger action set 等于 catalog action set；
6. 要求每个 action→group binding 与 view 一致；
7. 对每个 selected action 保留 `observed`、`failed` 或 `unavailable`；
8. 只对 observed values 计算 synthetic mean；绝不补零、impute、删行或输出科学 pass。

Receipt ID、result ID 和 fingerprints 是 content identities，不是签名。可信结果必须由该 deterministic API
对 exact inputs 重算；不能仅因 caller 构造了一个 schema-valid object 就视为历史或科学 evidence。

## 6. 定向核验

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q \
  praxis_virtualcell/tests/test_experiment_design_replay.py

PYTHONDONTWRITEBYTECODE=1 python -m pytest -o addopts='' -q -rA \
  praxis_virtualcell/tests/test_experiment_design_replay.py \
  praxis_virtualcell/tests/test_virtual_experiment.py \
  praxis_virtualcell/tests/test_request_v2.py \
  praxis_virtualcell/tests/test_capability_runtime.py \
  praxis_virtualcell/tests/test_benchmark_system.py \
  praxis_virtualcell/tests/test_model_adapter_sdk.py \
  praxis_virtualcell/tests/test_active_learning_agent.py \
  praxis_virtualcell/tests/test_runtime_active_learning.py \
  praxis_virtualcell/tests/test_report_active_learning_request.py

python -m ruff check . --extend-exclude old --no-cache
python -m ruff format --check \
  praxis_virtualcell/experiment_design.py \
  praxis_virtualcell/tests/test_experiment_design_replay.py
```

Frozen results are focused `28 passed`, affected `301 passed`, safe
`1,845 passed / 49 skipped / 387 deselected / 453.03s`, and legacy
`1,147 passed / 58 skipped / 105 deselected / 61.21s`.

## 7. 故障处置

| Symptom | Required action |
|---|---|
| raw request contains secret/path | retain only request ID/fingerprints; never serialize raw metadata/constraint values |
| action pool mixes model/Pack/evidence/OOD/endpoint/unit domain | reject view; no comparator normalization |
| selection row contains outcome/label | reject as undeclared field |
| receipt selected IDs/fingerprints change after freeze | recompute canonical receipts and reject, even if receipt ID was recomputed |
| ledger omits an action | require explicit `unavailable`; no silent row drop |
| outcome group differs from selection binding | reject cross-bound ledger |
| selected outcome has failed/unavailable status | preserve absent utility and status; never zero fill |
| result claims historical/scientific/promoted/shadow/prospective/autonomous | reject Literal/status ceiling drift |
| `pip check` fails in shared environment | record failure; do not mutate dependencies without authorization |

## 8. P27A-R 独立资产窗口

P27A-R 至少需要一个 immutable manifest，绑定 exact read-only path、size、SHA-256、source、license、usage、
privacy/consent；selection-time bytes 与 hidden outcome bytes 必须结构分离；还要固定 group split、action、control、
replicate、batch、endpoint/unit、cost、feasibility、model/evidence/calibration/OOD identities、五个 strategies、budget、
seed、tie-break、metric/direction 和 failure policy。

当前 M1 ledger、P9 fixtures、Golden summaries 和 tiny Packs 都不满足这些条件。不得为它们补造 license、
design fields 或 outcome separation。Git 外资产读取需要新的 exact authorization window。

## 9. P27B / P27C 与 P28 handoff

P27B 必须使用具名专家、盲评 rubric、conflict disclosure 和 write-new shadow output；P27C 还需要 ethics、
biosafety、operator、人员、预注册 protocol 和 exact external actions。P27A-E 不能替代任何一门。

下一 eligible local work unit 是 P28E contract-only orchestrator、typed handoff、trace 与 value-free abstention。
只有至少三个 exact-request、exact-scope、executable、scientifically validated、production-promoted 模型模块才能通过真实 P28
acceptance；synthetic、rule 或 advisory 模块不计数。

Design rationale: [ADR-0023](../ADR-0023-agentic-experiment-design-contract.md). Frozen evidence:
[P27A-E completion report](../../reports/phase27ae/PHASE27AE_COMPLETION.md).

## 10. 2026-08-08 follow-on

P28E subsequently completed as contract-only/value-free engineering at
`da4bfc042d96f830e2a7e8cdc62ba227c7ace949`; real P28 remains blocked at `0/3` qualifying modules.
Section 9 is the historical P27 handoff, not a current assertion that P28 is still unstarted. The next local
unit is P29E strict connected-subgraph contract plus authoritative empty-graph/value-free abstention; no
biological placeholder nodes are allowed.
See the [P28E runbook](MULTI-AGENT-BIOLOGY-CONTRACT.md).
