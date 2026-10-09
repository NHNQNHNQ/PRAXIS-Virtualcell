# ADR-0004：VirtualCellPack P6 能力驱动 runtime

- 状态：Accepted（P6 本地候选）
- 日期：2026-07-27
- 唯一起始基线：`e97cfa153281fb6c9ad33e39c916e2fed1225df9`
- 前置：ADR-0001、ADR-0002、ADR-0003

## 背景

P0–P5 已分别冻结 request/runtime 科学边界、Pack identity、只读 H5AD/H5MU
语义和显式 feature alignment，但主 workflow 的模型选择仍以
`ModelApplicability` 候选、`REAL_ENGINES` 和 `case_dispatch` 为主。Model Zoo
虽能登记状态、依赖和资产 hash，却没有成为 Pack-aware 执行的事实源。

P6 需要让一个请求能以可审计方式回答：

```text
Request × Registered Pack × Model Card × Environment
→ CompatibilityReport
→ deterministic ExecutionPlan
```

同时必须保留无 Pack 调用的冻结 legacy 行为，不能把迁移误写成一次不兼容替换。

## 决策

### 1. 四个输入都必须有明确身份

- Request 使用完整 canonical `vc.request.v2` SHA-256，不只使用 `request_id`。
- Pack 必须是 `PackRegistry` 完整验证后签发的 `RegisteredPack`；任意 manifest
  对象或路径不能自行宣称 `pack_valid`。
- Model 必须来自严格 `vc.model-card.v1`；未知字段、重复项、类型强制转换、
  非 canonical 名称、坏 CURIE/hash/path 均拒绝。
- Environment 使用 `vc.environment.v1`，显式列出可 import 的 Python 依赖、
  资源和当前 runtime 真正实现的 task/output adapter。

四者 fingerprint 都进入 report/plan identity。相同 `request_id` 但 targets、
metadata 或其他 request 内容不同，必须产生不同的 plan identity。

### 2. 模型卡是 Pack-aware 模型能力的唯一声明

`vc.model-card.v1` 固定：

- taxon、modality、assay、cell/tissue domain；
- perturbation、task、output；
- feature namespace/version/ID format、representation；
- assets/path/SHA-256/media type；
- Python dependency、runtime resource；
- uncertainty method 和完整 canonical OOD dimensions；
- wrapper class、model version、status、training/provenance。

旧 registry 条目仍可供 legacy `model_request` 查询，但没有
`vc.model-card.v1` 就不会进入 P6 `CapabilityRegistry`。

### 3. 三层状态不可合并

`CompatibilityReport` 分开记录：

- `pack_valid`：Pack 是否由本进程 registry 完整验证并注册；
- `model_compatible`：Request、Pack 和 Model 的 taxon/modality/assay/domain/
  perturbation/task/output/namespace/representation 是否全部满足；
- `scientifically_validated`：P6 固定为 `false`。

资产、依赖、资源、wrapper 和 runtime adapter 属于
`environment_compatible`/`executable`，不能反向提升前两层，也不能把成功执行
写成科学验证。

### 4. 兼容性是关系约束，不是各维度独立有交集

除 Model 与 Pack 各自覆盖某个 modality/namespace 外，还必须证明请求所指的
modality 和显式 namespace 确实存在于该 Pack。这样可阻止“Model 同时支持 RNA
和 protein、Pack 只有 RNA、Request 要 protein”被多个独立交集错误放行。

没有 symbol lookup、version stripping、ortholog conversion、补零、去重、
随机划分或 mock fallback。重复 requested outputs 直接产生明确拒因，不会先
去重再判断。

### 5. Broker 负责计划和实例化，runtime 只执行计划步骤

`ModelBrokerAgent`：

1. 接受 strict v2 request 与完整 Pack identity；
2. 让 `CapabilityRegistry` 对所有严格模型卡产生稳定排序的 reports；
3. 只为 `executable=true` 的 report 生成 step；
4. 实例化前再次核对资产 SHA-256，再动态 import `ModelWrapper` 子类并通过
   `from_capability` 绑定模型卡、report 和已验 hash 的资产路径；
5. constructor/import 失败时修订 report/plan 并移除 step。

主 runtime 只注册 Broker 返回的 prepared wrappers。新增测试 dummy plugin
只增加临时模型卡和 wrapper 类，没有修改 `build_runtime`、`route_table` 或
`case_dispatch` 的模型专用分支。

当前执行协调器只实现 `predict_delta_expression → delta_expression`。该事实由
Environment contract 明示；其他 task/output 即使模型本身兼容，也会以
`environment.runtime_task:*`/`environment.runtime_output:*` fail-closed。
插件返回值还必须提供非空、有限数值的 `prediction.delta` 和模型卡允许的
uncertainty method；整个返回对象必须是递归合法 JSON 值。

### 6. legacy 是显式适配器

- 同时提供 `pack_id` 和 `pack_version`：走 P6 Broker 路径；
- 两者都不提供：走 `LegacyModelApplicabilityAdapter`；
- 只提供一个：在任何模型运行前拒绝。

因此 `_LEGACY_CANDIDATES`、`REAL_ENGINES` 和 `case_dispatch` 只保留为无 Pack
兼容路径，不再是 Pack-aware 执行的事实源。P0 代表性 offline report 字节保持
不变。

### 7. LLM 不参与兼容性或裁决

Model card parsing、Pack identity、environment detection、compatibility checks、
plan、prediction 和 governance 全部为确定性代码。LLM 可继续做现有解析、建议、
critic 和 narrative，但不能创建/修改 report checks、plan steps、数值预测、
`scientifically_validated` 或最终 verdict。

## Fail-closed 结果

| 情形 | 结果 |
|---|---|
| Pack 未注册 | `pack_valid=false`、无 step |
| request 越 model/Pack scope | `model_compatible=false`、无 step |
| asset 缺失或 SHA-256 不符 | `assets_ready=false`、无 step |
| dependency/resource/runtime adapter 缺失 | `environment_compatible=false`、无 step |
| wrapper import/constructor 失败 | plan 被修订并移除该 step |
| plugin 输出类型、delta 或 uncertainty 契约错误 | predictor rejected/failed，runtime abstain |
| 没有 executable model | 空结果进入既有 Reliability，得到硬 abstain；不调用 mock |

## 后果与限制

- Model Zoo、PackRegistry 和 Broker 成为 Pack-aware 主链事实源；旧分流仍可明确
  审计和回滚。
- P6 没有增加模型、下载资产、提交权重、修改 UI、push 或运行远端验证。
- 当前主 workflow 的 Pack-aware 入口仍从 legacy `VirtualCellRequest` 显式投影到
  v2；直接以不可投影的 v2 taxon/domain 运行留给后续阶段。
- Pack schema 尚无独立 assay 字段；P6 只能对现有 modality ontology 做精确
  声明检查，不做 ontology 推理。区分 modality/assay 的新 Pack schema 需单独 ADR。
- `PackRegistry` 是进程内已验证快照，不是签名、跨进程事务或持续文件监控。
- 模型卡兼容、资产可用和一次执行成功都不构成 benchmark 或
  `scientifically_validated=true`。
