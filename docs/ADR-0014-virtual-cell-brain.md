# ADR-0014：Deterministic Virtual Cell Brain 与 Virtual Experiment DAG

- 状态：Accepted（P17 engineering contract complete；real multi-model acceptance pending）
- 日期：2026-08-06
- 唯一起始基线：`ff525a0611901df422161a7143ebfe9d1e051008`
- Completion code SHA：`16636f1b2c36e0a0fabb782a662b5b3b934891e0`
- Completion tree：`321a59eed44c45bf2bb8798714352b3303b92e58`
- 分支：`codex/p17-virtual-cell-brain`
- 前置：ADR-0006、ADR-0008、ADR-0009、ADR-0010、ADR-0011、ADR-0012、ADR-0013
- 状态码：`P17_CONTRACT_COMPLETE_REAL_MULTI_MODEL_ACCEPTANCE_PENDING`

## 背景

P12–P16E 已把 model、artifact、environment、adapter、evidence、operator policy 与三个
窄任务工程合同拆成可寻址 identity。P17 需要在这些 identity 之上定义一个可审计、可
重放的 Virtual Cell Brain：它必须从 exact request、CellContext、Pack、registry 与
CapabilityRegistry 的确定性结果生成 Virtual Experiment DAG，且不能把 LLM proposal、
wrapper 初始化或真实模型执行混入权威身份。

代码完成时 registry 恰有 5 个 release、0 个 native release、0 个 production-promoted
capability。所有 release 都是 legacy incomplete。因此当前没有满足真实 multi-model
acceptance 的参与者；P17 只能完成合同与 fail-closed integration，不能声称进行了预测、
科学验证或生产编排。

## 决策

### 1. `vc.request.v2` 只走 exact Pack-bound direct path

Runtime 对 exact `vc.request.v2` 要求调用方同时提供非空、无首尾空格的 `pack_id` 与
`pack_version`，重新 strict-validate request 后进入 `virtual_experiment_payload`。该入口：

1. 用 exact Pack registry 解析 Pack；
2. 构建 model registry、cache identity 与 environment snapshot；
3. 仅调用 `ModelBrokerAgent.plan()`；
4. 编译 DAG、Brain context、decision 与 candidate audit；
5. 返回结构化 abstention 并写入 JobStore。

Legacy `run_pack_query` 明确拒绝携带 `vc.request.v2` marker 的 hybrid request。旧请求仍走
原有 legacy path，不能通过附加旧字段或 v2 marker 跨越入口边界。

### 2. Broker 的 P17 权威输入是 plan，不是 wrapper

`ModelBrokerAgent.plan()` 只调用既有 `CapabilityRegistry.plan()`。P17 direct path 不调用
`instantiate`，不准备 wrapper，不导入或加载模型资产，不产生预测，也不启动 LLM。既有
message-bus/legacy execution handler 保留，但不是 P17 direct-v2 的实现依据。

Execution plan fingerprint 从 canonical、path-free 的公开 identity 计算。Request、Pack、
environment、compatibility report、model、release、capability、adapter、input/output contract、
evidence 与 policy 都必须重新绑定 registry record；未知字段、subclass、`model_construct`
绕过、指纹错配或不完整 Pack identity 一律 fail closed。

### 3. DAG 是唯一权威实验图

P17 冻结以下 strict、frozen schemas：

| Schema | 作用 |
|---|---|
| `vc.virtual-experiment-node.v1` | 绑定一个 execution step 与 exact model/release/capability/environment/adapter contracts |
| `vc.virtual-experiment-edge.v1` | 绑定 source/target step 与 output→input contract identity |
| `vc.virtual-experiment-dag.v1` | 绑定 request、CellContext、Pack、environment、plan、validated steps、participants、nodes 与 edges |
| `vc.virtual-cell-brain-context.v1` | 汇总权威决策所依赖的全部 immutable identities |
| `vc.virtual-experiment-decision.v1` | 固定 executable、conflict、partial failure、abstain 与 final verdict |
| `vc.virtual-experiment-compilation.v1` | 交叉绑定 DAG、Brain、decision 与独立 candidate audit |

Node 与 edge 使用 canonical fingerprint order；重复 step、重复 edge、self-edge、dangling
edge、contract 不兼容或 cycle 均被拒绝。`plan_id` 必须等于
`plan_ + plan_fingerprint[:24]`。DAG/Brain/decision 的 request、Pack、plan、participant 与
step identities 必须逐层一致。

至少两个不同的 production-promoted capability 才能形成 multi-model-eligible participant
set。少于两个时权威 DAG 不承载执行 nodes。无论数量多少，P17 decision 都固定：

~~~text
executable=false
execution_performed=false
conflict_detected=false
partial_failure_detected=false
abstain=true
final_verdict=abstain
~~~

当前 0 promoted 的 reason 是
`insufficient_production_promoted_capabilities`。即使未来合同编译看见至少两个 promoted
participants，P17 仍以 `contract_only_execution_not_authorized` abstain；执行授权必须由后续
明确 phase/version 作出，不能静默改变 v1 语义。

### 4. Brain context 绑定全部决策证据，不保留可变引用

Brain context 固定 request、CellContext、Pack、environment snapshot、plan、DAG、execution
steps、participating capabilities，以及 registry 中 compatibility、model、release、capability、
environment、adapter、input/output contract、evidence 与 policy fingerprints。公开 identity
不包含本地资产路径或 model-version convenience string。

任何 registry 或 plan record 重算 fingerprint 后，即使局部对象自身 fingerprint 合法，只要与相邻
record、DAG node、Brain 或 decision 不一致，compilation 仍必须拒绝。重放依赖完整 identity
闭包，不依赖 model name、文件名或目录扫描。

### 5. LLM candidate 永远是非权威审计输入

可选 proposal 只接受 `vc.candidate-virtual-experiment-dag.v1` strict schema。确定性 validator
把它标记为 `not_provided`、`matched`、`rejected` 或 `unavailable`；candidate 不得改变权威
DAG、Brain、decision 或 authoritative compilation fingerprint。

Candidate review 自身另有 `candidate_review_fingerprint`，因此 audit status/reason 的 tamper
可以被发现。该 review 与 checksum 都从 `authoritative_dict()` 排除：审计记录可寻址，但
不能让 LLM availability 或 proposal 内容改变实验权威身份。

### 6. JobStore 使用 execution identity v3 并拒绝降级旁路

Exact-v2 P17 job 使用 `vc.job-execution-identity.v3`，在既有 request/report/provenance/plan
绑定之外保存 Brain 与 DAG fingerprints。保存与加载都会重新解析 compilation，并核对：

- structured report 与 top-level provenance 的 plan/compilation 完全相同；
- request、plan、DAG、Brain、decision、step、capability 与 node registry identities 一致；
- companion request/report/trace/provenance 文件与 execution identity 相互绑定；
- 已有 companions 的 v3 job 不能把 identity schema 改写为 v2 来绕过 Brain/DAG checks。

真正 self-contained、没有 companion files 的历史 v1/v2 identity 保留只读兼容；部分缺失
companions 或伪造 downgrade 均视为 unavailable。Candidate audit 不进入 authoritative report
identity，保持 proposal 是否存在对 job identity 无影响。

### 7. 第五 taxon 只存在于临时测试 fixture

Danio rerio / `NCBITaxon:7955` 只在测试临时目录内构造 Pack/request，用于证明 species-neutral
identity compilation。它从未写入 production Pack registry、model registry、默认 adapter、
species branch 或 checked-in data。测试结束后没有第五 taxon 的产品注册状态。

## 后果与边界

P17 engineering 状态为：

~~~text
contract_defined=true
implementation_complete=true
tests_passed=true
artifact_ready=true
science=NOT_RUN
product_policy=NO_NEW_DECISION
production_promoted=false
published_or_released_artifact=false
~~~

这里的 `artifact_ready=true` 只表示 exact code commit 可重复构建的本地工程 wheel 已就绪；
没有 artifact publication、tag、release、push 或 deployment。

P17 未访问网络或外置 scientific assets，未训练、调参、运行 GPU/LLM/wrapper/model，未执行
Golden/GEM/Norman science，未创建 evidence 或 operator decision，未修改 `.53`、服务、端口、
生产 registry 或默认 adapter。P14R/P15R/P16R 与相应 B 阶段仍未运行。

真实 multi-model acceptance 仍待至少两个被明确 policy promotion 的 capability，以及后续
执行、冲突、partial failure 与科学验收授权。下一 eligible local work unit 是 P18
contract-only multi-omics cell-state；它不能继承 P17 尚不存在的真实执行或科学证据。
