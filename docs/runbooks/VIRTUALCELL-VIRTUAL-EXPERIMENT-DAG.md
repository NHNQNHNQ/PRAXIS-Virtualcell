# Virtual Cell Brain / Virtual Experiment DAG 本地只读运行手册

本 runbook 只审计 P17 deterministic contract、direct-v2 integration、JobStore binding 与
离线工程验证。它不访问网络或外置资产，不实例化 wrapper，不运行模型/LLM/GPU/科学任务，
也不执行 promotion、release、publish、deploy、服务启动或 `.53` 操作。

## 1. 固定代码身份与状态

从仓库根执行只读检查：

~~~bash
git rev-parse --show-toplevel
git rev-parse --git-dir
git branch --show-current
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
git status --short
~~~

P17 completion code identity：

~~~text
starting SHA          ff525a0611901df422161a7143ebfe9d1e051008
completion code SHA   16636f1b2c36e0a0fabb782a662b5b3b934891e0
completion tree       321a59eed44c45bf2bb8798714352b3303b92e58
branch                codex/p17-virtual-cell-brain
status                P17_CONTRACT_COMPLETE_REAL_MULTI_MODEL_ACCEPTANCE_PENDING
~~~

后续 docs closure 或 P18 commit 会改变 HEAD/tree；不要回退工作树来匹配旧 SHA。P17
fingerprints、测试与 packaging evidence 绑定上面的 completion code SHA。

允许的解释只有：engineering contract complete、real multi-model acceptance pending、
science NOT_RUN、product policy NO_NEW_DECISION。不得写成模型执行成功、scientifically
validated、promotion eligible、published、released 或 deployed。

## 2. 入口隔离审计

P17 direct path 只接受 exact `vc.request.v2` 加 exact `pack_id` / `pack_version`：

~~~text
runtime_service.run_job
  -> VirtualCellRequestV2.from_dict
  -> virtual_experiment_payload
  -> exact PackRegistry record
  -> ModelBrokerAgent.plan
  -> CapabilityRegistry.plan
  -> compile_virtual_experiment
  -> structured abstention
  -> JobStore execution identity v3
~~~

检查源码引用，不启动 API 或服务：

~~~bash
rg -n "vc.request.v2|virtual_experiment_payload|def plan" \
  praxis_vc_api/services/runtime_service.py \
  praxis_virtualcell/pack_product.py \
  praxis_virtualcell/agents/model_broker_agent.py
~~~

必须满足：

- direct path 只有 plan compilation，没有 `instantiate` 或 wrapper preparation；
- output 的 `prediction=None`、`models_used=[]`、`trace=[]`、`abstain=true`；
- `llm_used_for_prediction=false`、`llm_enabled=false`；
- legacy `run_pack_query` 遇到 v2 marker 立即拒绝；
- structured report 与 top-level provenance 携带同一个 execution plan 与 compilation。

不要通过启动服务、构造真实模型 cache 或运行 legacy message bus 来“验证”本合同。

## 3. Schema 与 deterministic binding 审计

只读列出 P17 schemas：

~~~bash
rg -n '^class (VirtualExperiment|VirtualCellBrain|CandidateDAG)' \
  praxis_virtualcell/virtual_experiment.py
~~~

权威链：

~~~text
request + CellContext + exact Pack + environment
  -> CapabilityRegistry ExecutionPlanV2
  -> canonical plan fingerprint / plan_id
  -> VirtualExperimentDAGV1
  -> VirtualCellBrainContextV1
  -> VirtualExperimentDecisionV1
  -> authoritative compilation fingerprint
~~~

审计时必须核对：

- strict/frozen contracts 拒绝 unknown fields、隐式 coercion、subclass 与构造绕过；
- node 逐项绑定 step/model/release/capability/environment 及 aligned adapter contracts；
- node/edge canonical order，且拒绝 duplicate、self-edge、dangling edge、contract mismatch、cycle；
- Brain 精确绑定 request、cell、Pack、plan、DAG、reports 与 registry identity closure；
- decision participant/step fingerprints 与 DAG/Brain 一致；
- 少于两个不同 promoted capabilities 时 nodes 为空且 final verdict 为 abstain；
- P17 无论 participant count 都固定 `executable=false`、`execution_performed=false`。

Completion code inventory 是 5 releases / 0 native / 0 promoted；因此 current result 的
participant count 为 0，reason 是 `insufficient_production_promoted_capabilities`。不要修改
registry 来制造正例。

## 4. Candidate DAG 隔离审计

Candidate 仅允许 strict `vc.candidate-virtual-experiment-dag.v1`；review 只能是：

| status | reason |
|---|---|
| `not_provided` | `candidate_not_provided` |
| `matched` | `candidate_matched_authoritative_dag` |
| `rejected` | `candidate_rejected_by_deterministic_validation` |
| `unavailable` | `candidate_generation_unavailable` |

每个 review 必须匹配独立 `candidate_review_fingerprint`，但 review 与该 checksum 都不进入
`authoritative_dict()`。相同 request/plan/registry 下，candidate absent、matched、invalid 或
unavailable 都不能改变 DAG、Brain、decision、authoritative compilation fingerprint 或 job
execution identity。这里不需要也不允许真正调用 LLM。

## 5. JobStore replay 与 tamper 审计

只读检查 v3 bindings：

~~~bash
rg -n "vc.job-execution-identity.v3|brain_fingerprint|dag_fingerprint" \
  praxis_virtualcell/io/job_store.py
~~~

Exact-v2 job 应保存 `request.json`、`report.json`、`trace.json`、`provenance.json` 与带 content fingerprint 的
`execution_identity.json`。加载时须重新验证 compilation 和 companion cross-binding。以下 tamper
必须返回 unavailable 或抛 contract error，而不是降级继续：

- 替换 request、plan、Pack、Brain、DAG 或 decision fingerprint；
- 让 DAG step/capability/node 与 execution plan 不一致；
- 让 structured report 与 top-level provenance 的 compilation 不一致；
- 改 candidate review status/reason 却保留旧 candidate checksum；
- 把已有 companions 的 identity v3 改成 v2；
- 删除一部分 companion files。

没有 companions 的真正 historical self-contained v1/v2 record 可继续只读；这不是 current
v3 job 的降级通道。

## 6. 测试与静态 gate

安全 focused gate：

~~~bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q \
  praxis_virtualcell/tests/test_virtual_experiment.py

python -m ruff check . --extend-exclude old --no-cache

python -m py_compile \
  praxis_virtualcell/virtual_experiment.py \
  praxis_virtualcell/agents/model_broker_agent.py \
  praxis_virtualcell/pack_product.py \
  praxis_vc_api/services/runtime_service.py \
  praxis_virtualcell/io/job_store.py

git diff --check
~~~

Completion validation：

- P17 suite：41 passed；
- adjacent suites：377 passed，1 skipped；
- safe gate（排除 `mudata` 与 Golden/GEM/Norman science）：1,487 passed，48 skipped，
  387 deselected；
- full Ruff：passed；changed-path `py_compile` / diff / format checks：passed。

`test_mudata_alignment` collection 因 optional `mudata` 未安装而 unavailable；不要在线安装
依赖来改变本地证据。Global `pip check` 也不能作为 gate，因为 base environment 已被既有
无关 distributions/conflicts 污染。

## 7. Test-only fifth taxon replay anchor

Danio rerio / `NCBITaxon:7955` 仅在临时测试 fixture 中存在；不得把它写入 production
registry。Canonical fixture identities：

| Identity | Fingerprint |
|---|---|
| Pack | `2d18a4ff702797774ec2faba9546f538e936a25a5bb9d27c40d796ecd949ad50` |
| plan | `d24c3202d63616d65b59cdb144995a7dcb0806a30ce1e034e0949317e548a207` |
| DAG | `19b1883cf48380c010d919d539b0eecfbe442713d1de1eb5a5a150501a80cdc6` |
| Brain | `1e4e4a7d591423d83e3bd9302281200e27ecfbf148c0f6f1966868b2e7538a5c` |
| authoritative compilation | `06eb1f07e15db983155c0d8b0be8207e1118610fc6508599b08bb136a54a48e3` |
| candidate review | `c37def4523924536e2a290b5ba4999ba9a376ef1c609635f8d89777f193ab749` |
| job identity | `5db65d8c268d91a17511bef54142d5d1b6b4af56b4bff28fa17251b4eea9e706` |

这些 fingerprints 证明 deterministic engineering replay，不证明 Danio model、data、Pack
或生产 capability 存在。

## 8. Packaging 复核与限制

Exact code commit packaging boundary：

~~~text
SOURCE_DATE_EPOCH  1786018775
wheel size         1118410 bytes
wheel SHA-256      bd3752b90a6d8e4d7a825b2f4925d00eb7e5204021fef3404b67e88f7a0e23bd
entries            366
React static       14
tests              0
AppleDouble        0
Brain module       present
~~~

两个独立 clean `git archive`、offline builds 对 code commit 产生 byte-identical complete
wheel。工具链为 Node 24.14.0 / npm 11.11.1、Python 3.12.13、setuptools 83、wheel 0.47、
packaging 26.2。该证据只支持 exact local engineering artifact reproducibility。

Official strict script 在 network-denied 环境中因 locked `packaging==26.2` 不在脚本隔离 cache
而 fail closed。Clean no-deps smoke 因 runtime `PyYAML` 缺失失败；继承 polluted system-site
的 no-deps smoke 通过 import/static/CLI，但不是 authoritative dependency proof。不要据此
发布 wheel 或宣称 clean install closure。

## 9. 停止条件

出现以下任一情况立即停止并记录为 contract violation：

- real wrapper/model/LLM/GPU/science 被执行；
- v2 request 进入 legacy runner，或缺 exact Pack 仍被接受；
- candidate 改变 authoritative identity；
- fewer-than-two promoted capabilities 得到 executable/non-abstain verdict；
- asset path 泄漏到 public provenance；
- Danio fixture 被注册到 production；
- v3 identity 可用 schema downgrade 绕过；
- 发起 network、promotion、push、release、deploy、`.53` 或服务操作。

P17 engineering artifact ready 不等于 published/released。在 P17 completion 当时，下一
eligible work unit 是 P18 contract-only multi-omics；真实 multi-model acceptance 继续
pending。P18 后续完成状态及当前 next gate 以 [P18 completion report](../../reports/phase18/PHASE18_COMPLETION.md)
和 [document index](../INDEX.md) 为准。
