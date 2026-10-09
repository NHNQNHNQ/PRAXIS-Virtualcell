# ADR-0001：VirtualCellPack 基座与科学边界（P0）

- 状态：Accepted（仅 P0）
- 日期：2026-07-27
- 实施基线：`8e0d06348ebdf22e076037e6d661094ae877c5d1`
- 范围：冻结现有 request/runtime/治理边界，修复 Report → ActiveLearning 的 request 传递 seam。
- 明确不做：Pack loader、新模型、权重入 Git、UI 变更、`.53` 同步或远端写入。

## 背景审计

现有确定性链路为：

`VirtualCellRequest.from_dict` → `InputInterpreter` → `BioObjectNormalizer` → `SpeciesBrain` → `ModelApplicability` → `route_table` → predictor/case dispatch → `EnsembleCoordinator` → `Reliability` → `Critic` → `ProvenanceAgent` → `Report` → `EvidenceLevel` / `ActiveLearning`。

- request 真相来自 `core/request.py`；`agents/request_adapter.py` 只把 A 面字段映射为模块路由输入，不猜测缺失科学字段。
- `SpeciesBrain` 只读取 species/generic YAML，并输出规则引用；它不生成预测数值，也不是模型兼容性或科学验证的裁决者。
- `route_table.route()` 是声明式 presence/absence 能力图，输出 engine、disposition、reason 和 data gate；它不代表性能。
- `case_dispatch.dispatch_runner()` 是 engine 到具体 case runner 的确定性边界。缺 runner、依赖、checkpoint 或不满足窄门时抛出 `UnsupportedEngine`，由现有 runtime 走 reject/abstain 语义。
- `model_zoo/registry.yaml` 只登记模型类型、物种、模块、任务、状态、依赖、资产 hash 和 provenance。当前 `ecoli_gem` 为 `available`；GEARS、scGPT、mean baseline、yeast deletion fitness 仍是 `planned`。权重不在仓库内。
- `ReportAgent` 是结构化报告组装器，不得丢掉确定性 request 上下文。P0 修复为报告保留完整 `request`，使下游 ActiveLearning 能得到真实 species/targets。
- `ActiveLearningAgent` 只读 report/evidence，输出 advisory learning queue；它不改变 prediction、verdict、abstain 或 provenance 真相。

## 决策

### 1. 三层状态分离

三层状态统一使用 `valid | invalid | unknown`；`unknown` 不能被静默解释成 `valid`，也不能触发 mock 或补零。状态由确定性 runtime/manifest/evidence 产生，LLM 只能解析、解释或提出建议。

| 状态 | 定义 | 成为 `valid` 的证据 | fail-closed 边界 |
|---|---|---|---|
| `pack_valid` | 一个 VirtualCellPack 的结构、manifest、文件列表、hash、版本/协议、license 和 provenance 均符合契约 | 未来 loader 对 manifest 与声明资产逐项校验通过 | P0 没有 Pack loader；当前只能记录“未加载/unknown”，不得把 registry 条目当 pack 已验证 |
| `model_compatible` | 已声明模型与归一 request 的 species、module、task、输入/输出、engine、wrapper、依赖和已声明资产相容 | route + registry + dependency/asset gate 全部通过 | `planned`、缺依赖、缺资产、wrapper 不匹配或未解析时为 `unknown/invalid`，不得 fallback 到 mock 作为模型真相 |
| `scientifically_validated` | 模型输出具有可审计的固定数据集、split、baseline、metric、泄漏检查、随机性/重复策略、artifact hash 和适用范围证据 | 对应 validation runbook/evidence 全部存在且结果可复现、口径可比 | `model_compatible` 不蕴含科学有效；没有证据时保持 `unknown`，不得由报告文案或 LLM 升级 |

只有三层都为 `valid`，才允许对外使用“该 pack 中该模型已科学验证”的表述。`model_compatible=valid` 仍可能只产生 `caution`/`downgrade`；任何层为 `invalid` 或未满足必要窄门时，现有治理必须拒绝、降级或弃权。

### 2. 真相与建议分工

- 数值、route、hard rule、reliability、abstain/downgrade/accept、provenance 和三层状态均由确定性代码、manifest、hash 或 validation evidence 决定。
- LLM 不写入三层状态，不选择最终模型，不产生数值预测，不覆盖 hard rule，不裁决科学有效性。
- 没有同源转换、静默归一、补零、去重、随机划分或 mock fallback。现有 Mock predictor 仅是离线兼容/测试路径；不得被报告为科学验证结果，P0 不扩展该路径。

### 3. P0 兼容修复

`ReportAgent` 在结构化报告中保留 `p["request"]`。这是唯一实现改动；ActiveLearning 的打分、排序、候选格式和治理旁路均不改。回归测试覆盖：

1. Report 输出包含完整 request；
2. Report → ActiveLearning 产生 `genetic_hub@human:AHR`，不再产生 `genetic_hub@:unspecified`；
3. runtime 离线代表请求的候选也保留真实上下文。

## 后续阶段闸门

后续实现 Pack loader 前，必须先由用户指定上一阶段完成 SHA，并补齐 manifest schema、资产 hash 校验、pack/model compatibility test、scientific validation runbook 和小型 fixture。P0 不预埋 loader 接口，也不添加模型或权重。
