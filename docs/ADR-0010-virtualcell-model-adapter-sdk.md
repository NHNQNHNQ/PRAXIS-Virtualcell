# ADR-0010：Virtual Cell Model Adapter SDK 与严格 task/output 执行合同

- 状态：Accepted（Phase 13 engineering complete）
- 日期：2026-08-06
- 唯一起始基线：`f83c13db386cb552b3ce7a5643e5ffbead0ff573`
- Completion code SHA：`744d0a28d2cfc13d1b10e85b133b6c13b9426174`
- Completion tree：`198e623120688d3704b9312990ddaa93c9a7b0e6`
- 分支：`codex/p13-model-adapter-sdk`
- 前置：ADR-0003、ADR-0004、ADR-0009
- 范围：Phase 13；不实施 P14 real model/science/policy，不作 promotion 决定

## 背景

P12 已用 `vc.model-adapter.v1` 把 adapter 名称、版本、implementation、task、output
及输入/输出合同 fingerprint 纳入 release identity，但该记录只描述身份，不提供可执行
SDK。运行时仍主要围绕既有 `predict_delta_expression` 路径传递 wrapper 字典，无法用同一
机制严格证明输入准备、输出归一化、feature alignment、OOD、abstain 和 provenance。

P13 只补齐这一工程层：为明确注册的 task/output adapter 提供不可变合同、确定性
conformance 和 fail-closed runtime 接线。它不下载资产、不载入或训练新模型、不访问
网络或外置数据、不运行科学实验，也不生成 evidence、operator policy 或 promotion。
P9 的真实负结果继续保持原 bytes 和原结论，不因 adapter 可执行而改变。

## 决策

### 1. 冻结严格、版本化的 Adapter SDK 合同

SDK 新增以下 canonical JSON 合同。合同均冻结、严格拒绝未知字段和隐式类型转换，
fingerprint 由确定性 JSON bytes 的小写 SHA-256 得出：

| 合同 | schema | 唯一职责 |
|---|---|---|
| `AdapterInputContract` | `vc.adapter-input-contract.v1` | 声明 exact task/output、数值类型、shape、unit、Pack data 和 alignment 要求 |
| `PreparedAdapterInput` | `vc.prepared-adapter-input.v1` | 绑定 exact adapter/input contract/request，并按需绑定 Pack、compatibility、feature contract 和 alignment |
| `AdapterOutputContract` | `vc.adapter-output-contract.v1` | 声明 exact task/output、数值类型、shape、unit、uncertainty、OOD 和 abstain 要求 |
| `AdapterOutputEnvelope` | `vc.adapter-output-envelope.v1` | 保存已验证 values 或 abstain、uncertainty、OOD、projection metadata 和 execution provenance |
| `AdapterExecutionProvenance` | `vc.adapter-execution-provenance.v1` | 绑定 exact adapter、输入、request、Pack、compatibility 和输入/输出合同 fingerprints |
| `AdapterConformanceReport` | `vc.adapter-conformance-report.v1` | 保存同一输入和 raw output 的确定性 conformance 结果 |

`AdapterUncertainty` 和 `AdapterOOD` 是 envelope 内的严格嵌套对象，不是独立的
versioned schema identity。新增或改变上述合同语义必须使用新的 schema version；不能
在 v1 下静默放宽 shape、unit、uncertainty、OOD、abstain 或 provenance。

数值张量必须非空、矩形、shape 相符且只含 JSON-safe finite numbers。`bool`、NaN、
Infinity、超出安全 JSON integer 范围的整数、ragged tensor 和 unit 漂移全部拒绝。

### 2. Adapter 身份由实现和两端合同共同确定

`VirtualCellModelAdapter.identity()` 复用 P12 `AdapterIdentity`，并把 implementation
locator、task/output 和 exact input/output contract fingerprints 纳入同一 identity。
Phase 13 reference adapter 的冻结身份为：

| 项 | 值 |
|---|---|
| adapter id / version | `delta-expression-reference` / `1.0.0` |
| task / output | `predict_delta_expression` / `delta_expression` |
| adapter fingerprint | `17afc27e56dba13567001ff1982cbf1660e2948fadf2147301a1d0dcf61aeb3d` |
| input contract fingerprint | `d10cf437291dc1ebb1689c3f4c5eea4d82af3842491c224172215faddca93078` |
| output contract fingerprint | `d863783786504ebf768cfd7e2fbad66cfd03a029deb1dee3543a9872712e363d` |

其 input contract 为 float、shape `(None, None)`、unit `None`，且
`pack_data_required=false`、`alignment_required=false`；output contract 为 float、
shape `(None,)`、unit `None`，并要求 uncertainty、OOD，允许 abstain。该 reference
adapter 只规范既有 delta-expression wrapper 合同，不代表新增科学能力。

### 3. Registry 是显式 in-process allowlist

`AdapterRegistry` 只通过显式 `register()` 建立 task/output 和 identity fingerprint
索引，并提供 `resolve()`、`resolve_requested()`、`resolve_fingerprint()` 和
`resolve_identity()`。它不扫描 entry point、不按类名或 model name 猜 adapter，也不
从网络、配置目录或第三方 package 自动发现实现。

生产默认 `DEFAULT_ADAPTER_REGISTRY` 只注册 `DeltaExpressionReferenceAdapter`。
growth 和 fitness dummy adapters 只用于测试多 task/output contract 与 conformance；
它们不得进入默认 registry，不得作为模型能力、科学 evidence 或 promotion 依据。

P12 `AdapterIdentity` 必须与 runtime registry 中的完整 identity bytes 精确相等。缺失、
未注册、fingerprint 漂移或 task/output 不唯一时一律 fail closed。v1 对任何 multi-output
request 都 fail closed；未来若支持 composite adapter，必须另行定义 schema 与 registry
语义，不能从当前单 output lookup 推断。

### 4. 输入准备复用既有 feature/alignment 合同

`PreparedAdapterInput` 绑定 exact request fingerprint，并可绑定 Pack、compatibility、
values、unit、P5 `ModelFeatureContract` 和 `AlignmentReport`。SDK 不另建 feature mapping
体系，也不自动猜 Pack row、control、split、matrix、gene identifier、unit 或 transform。

若 adapter 声明 `pack_data_required=true`，prepared input 必须同时包含 values 和 Pack
fingerprint；若声明 `alignment_required=true`，还必须同时提供 feature contract 与
alignment report，并精确检查：

- feature contract fingerprint；
- target feature order；
- values 与 alignment target shape；
- mapping asset identity 和 hash。

任一绑定缺失或漂移都拒绝。只验证 request target compatibility 不能证明模型所需矩阵
已经绑定；Broker 对 data-required adapter 缺 values/matrix 的情况返回空计划，不制造
输入或 mock fallback。

### 5. 输出 envelope 必须保守且 science/policy neutral

Adapter 把 wrapper raw output 归一化为 exact output contract envelope，并验证 finite
values、shape、unit、uncertainty、OOD、abstain 和 execution provenance。检测到 OOD 时
必须 abstain；abstain 时禁止 values/shape 且必须给出 reason；非 abstain 时必须具有与
合同相符的 values/shape。

Adapter projection 只可携带 JSON-safe 的任务输出 metadata。`evidence`、
`scientifically_validated`、`promotion_eligible`、`operator_policy`、
`production_promoted` 等 science/policy keys 被保留并拒绝。Wrapper raw output 中即使
出现 evidence/policy 字段，也不复制、解释或修改为 envelope claim。Adapter 不能签发
科学结论或 operator decision。

### 6. Runtime 接线保持严格路径与 legacy 路径隔离

Pack-aware `CapabilityRegistry` 使用显式 adapter registry，并按 P12
`AdapterIdentity` exact resolution；缺 adapter 时返回空 execution plan。Broker 负责
准备 adapter input，wrapper 只消费该 prepared input，再由同一 adapter 归一化输出并
核对 model-card 声明的 uncertainty method。

严格 adapter abstain 在 wrapper/runtime 中形成 rejected result，同时保留 adapter
provenance。Critic、provenance、report 和 governance gates 只在存在合法 envelope 时
携带 adapter output；governance abstain 会清除公开 adapter output，但保留审计所需
provenance。现有 route table 和 case dispatch 不增加 model/species 特判。

Ensemble 只聚合已注册、同 fingerprint、同 task/output contract 的严格 envelopes；
strict/legacy 混用、adapter fingerprint 不同或 envelope 不兼容时拒绝。Delta reference
adapter 的聚合是确定性均值，但明确声明 ensemble uncertainty unavailable，不能从均值
推断 calibrated uncertainty。Learned reliability 只适用于既有 delta task/output；其他
输出保持 unsupported/fallback，不伪造 reliability。

无 Pack legacy 路径继续作为独立兼容边界，不得被描述为 P12/P13 fully governed，也不
允许 legacy 字典绕过严格 envelope gate。

### 7. Conformance 必须可重复

`run_adapter_conformance()` 先验证 prepared input，再对同一 raw output 独立执行两次
adapt/validate，并比较完整 envelope bytes、fingerprint 和非 abstain projection。只有
全部 byte-identical 才产生 `vc.adapter-conformance-report.v1`。Conformance 证明合同
实现确定性，不证明模型质量、科学有效性、evidence 充分或 production promotion。

## 被拒绝的方案

- 用 Python entry points 或 package 扫描自动注册 adapter：无法维持显式 allowlist 和
  exact runtime identity。
- 只修改 `ModelCard.outputs` 或继续传递自由字典：不能约束 input preparation、OOD、
  abstain、provenance 和 projection。
- 为 P13 再造 feature mapping/alignment schema：会与 P5 合同形成两套真相源。
- 自动推断 row、control、split、matrix、identifier、shape 或 unit：会把缺失绑定伪装成
  可执行输入。
- 把 growth/fitness dummy 注册到生产默认 registry：测试合同会被误读为真实能力。
- 允许 adapter 复制或生成 science/policy 字段：会越过 P12 evidence 与 operator-policy
  分层。
- 对缺模型、缺数据或不兼容路径返回 mock prediction：违反 fail-closed 和 no-fake-output
  边界。
- 在 P13 顺带实现 P14 model、asset、科学运行或 promotion：超出当前授权。

## 后果与限制

P13 工程状态为 COMPLETE：严格 adapter contract、registry、conformance 和 runtime
接线已完成，但没有新增模型、权重、资产、训练、科学结果、evidence、policy、release、
deploy 或 promotion。默认生产 registry 仍只有 delta reference adapter；growth/fitness
只存在于测试。

P13 也没有证明任何 Pack 已具备某一未来 adapter 所需的 matrix binding。新的真实
task/output 必须先完成独立工程阶段并提供 exact model/environment/adapter bindings；
之后才可在独立授权窗口运行科学验证和作 operator policy 决定。

下一步是 P14E。P14R（真实科学运行）和 P14B（operator policy/promotion）都需要单独
授权。P9 negative result 保持 `available=false`、
`scientifically_validated=false`，其 result SHA
`abd1145c434fd4e48ac9d72e94e8e19d14a5b4011f03d05db4823dd91760da6e` 不变。

## U1 本地 direct-v2 发布可验证性补充（未发布）

这是 P13 历史完成记录之外的通用本地候选，不改变既有 Adapter SDK schema 或任何历史
fingerprint。`vc.direct-v2-execution.v1` 只能由显式注入的 `DirectV2RuntimeFactory` 构造，
Python、CLI、HTTP 共享 `submit_direct_v2_job_from_factory()`。未注入 factory 的 HTTP 请求返回
`503 direct_v2_factory_unconfigured`，并且不写 JobStore；已安装 wheel verifier 将此作为负向合同。

direct-v2 的 U1 V2 计划仍只支持一个已准备 step；U2 新增的 V3 仅在 exact registered
`vc.output-reducer-policy.v1` 存在时允许多个 generic step，并把 reducer binding/receipt 写入
新的 V3/V5 identity。无 policy 或 policy/order/source/output drift 先以
`output_reducer_required` 空计划 fail-closed；任一步失败则 hard-abstain，不回退到 adapter aggregate、
默认 reducer 或部分模型结果。direct-v2 wrapper 还必须显式声明
`artifact_snapshot_supported = True`：Broker 以 no-follow descriptor 封存 exact artifact bytes，wrapper 只接收
private snapshot 而不接收 path；未适配既有 wrapper 在构造期收敛为空计划，不能由 core 退回 path。Runtime 仅接受
同一完整 snapshot handoff。direct-v2 还要求 write-new `vc.environment.v3` + `EnvironmentIdentityV2` 的
`vc.artifact-snapshot-budget-policy.v1`：它只限制 sealed artifact snapshot 的声明 bytes/entries，并声明/绑定
`execution_only` retention scope，不是 RSS/cgroup/隔离保证。Golden research-only release 已精确绑定其三件 artifact 的
`4,374,098 bytes / 3 entries`；该数值不包含 2.28GB Pack，也不决定 production 容量、并发或部署隔离。
本节仍是未发布本地证据，不证明科学验证、release 或 promotion。
