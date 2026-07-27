# VirtualCellPack 能力矩阵（P0–P5）

P0 基线：`8e0d06348ebdf22e076037e6d661094ae877c5d1`；P5 唯一起始基线：`a229699deac1e791252739df71f4e4202cc72bac`。本表是能力与证据边界，不是性能排名；`pack_valid`、`model_compatible`、`scientifically_validated` 不得互换。

| 能力/组件 | 当前实现与真相源 | `pack_valid` | `model_compatible` | `scientifically_validated` | 结论与边界 |
|---|---|---:|---:|---:|---|
| 结构化 request | `core/request.py`、`core/request_v2.py`、`agents/request_adapter.py`、`species_schema.py` | N/A | 输入前置 | N/A | 必填字段缺失由 schema fail-closed；v2/domain/bundle nested JSON 验证后递归不可变；不猜测 targets/output |
| 确定性 runtime | `core/runtime.py`、`workflows/run_virtualcell_query.py`、MessageBus | 未加载 | 由 applicability/route/case gate 决定 | 不自动声称 | OFFLINE 零 LLM；trace、hash、governance 保持确定性 |
| SpeciesBrain | `agents/species_brain.py` + `brains/virtualcell/**` | N/A | 提供规则上下文，不裁决 | 不提供 | 只读 YAML、登记 rules_referenced；不产数值 |
| route table | `agents/route_table.py` | N/A | 声明式条件性 | 不提供 | engine/disposition/reason 是能力图，不是性能结论 |
| case dispatch | `predictors/case_dispatch.py`、`case_runner_agent.py` | N/A | `gem_fba`/state/embedding/pathway 条件性；GEARS 受 `.53` checkpoint+依赖窄门 | 仅可引用已有、口径匹配的 evidence | 不满足 runner/依赖/资产窄门即 reject/abstain；不新增 mock fallback |
| Model Zoo registry | `model_zoo/registry.yaml`、`registry.py` | registry 不是 pack | `ecoli_gem=available`；GEARS/scGPT/mean/yeast deletion=`planned` | training card/provenance 不是验证结果本身 | registry 记录状态、依赖与 hash；不携带权重、不添加模型 |
| Report | `agents/report.py`、`io/report_markdown.py` | N/A | 只呈现确定性结果 | 只呈现已有 evidence | 报告保留完整 request；9 段 Markdown 保持确定性 |
| ActiveLearning | `active_learning/active_learning_agent.py`、`acquisition.py` | N/A | 不负责兼容性 | 不负责验证 | 只生成 advisory queue；不改 prediction/verdict/abstain/provenance 真相 |
| Governance | `governance/*`、runtime gates | N/A | fail-closed 边界 | 只检查契约/evidence | provenance、module、cell type、narrative/hash gate 不能被 LLM 绕过 |
| LLM 外层 | `agents_llm/*`、`llm_orchestration/*` | N/A | 只能建议 | 不可裁决 | 只能解析/解释/critic/narrative；确定性 runtime wins |
| 测试口径 | `praxis_virtualcell/tests/baseline`、golden/negative、`docs/TESTING.md` | N/A | route/dispatch/registry contract | validation evidence 需独立 runbook | core、legacy、remote、LLM 分口径；P0 报告字节 hash 由测试固定；skip 不等于通过 |
| Pack manifest v0.1 | `data_packs/manifest.py`、`validator.py` | strict schema + root-bound manifest/path/size/hash 后可为 valid | 不提供 | 不提供 | P2/P3 fingerprint 与 read-only H5AD 合同保持兼容；YAML 错误保持 Pack 异常边界 |
| Pack semantic v0.2 | `data_packs/schema.py`、`anndata_adapter.py`、`registry.py`、ADR-0002 | manifest、asset 与 P4 全部语义门通过后可为 valid；registry 保存语义 loader 的已验证快照，不授予较弱状态 | 不提供 | 不提供 | NCBITaxon/assembly、role-bound cell semantics、正式 `CVCL_XXXX`、canonical feature、FK/control/unit/split/leakage 与完整 manifest canonical key 均 fail-closed；缺 omics 不降级 |
| Pack multiomics v0.3 | `data_packs/schema.py`、`manifest.py`、`mudata_adapter.py`、`registry.py`、ADR-0003 | manifest/path/size/hash、backed H5MU、modality 顺序/shape、paired/partially-paired membership、P4 科学语义全部通过后可为 valid | 不自动提供 | 不提供 | 全局 observation 是 modality observation 并集；选择时只保留真实行，不补零、不做跨 modality imputation；缺 MuData 不 fallback |
| Model feature contract | `data_packs/feature_alignment.py::ModelFeatureContract` | 不改变 Pack 状态 | taxonomy、assembly、modality、namespace/version、ID format、feature set/order 全部满足后才可为 compatible | 不提供 | 合同与可选 mapping asset 的 version/hash 进入 fingerprint；非 canonical ID、非有限 fill、未知字段和重复项 fail-closed |
| Explicit feature alignment | `align_features()`、`AlignmentReport`、P5 tiny RNA+protein fixture | 消费已验证 modality，不重新授予 Pack 状态 | strict default；仅显式 alias/aggregate/drop/fill/reorder 成功并产 provenance 时成立 | 不提供 | 不剥 version、不查 symbol、不自动 drop/fill/reorder/aggregate；无 ortholog 或 namespace fallback；成功对齐不等于模型运行 |
| Ontology 与跨物种边界 | manifest 中的标准 CURIE 或有定义 local CURIE | 仅离线语法/声明验证 | 不推导 | 不推导 | 无在线 ontology runtime 依赖；无 symbol、ortholog 或同源转换 fallback |

## 现有模型/引擎状态摘要

| registry/model 或 engine | 当前状态 | 可声称内容 | 不可声称内容 |
|---|---|---|---|
| `ecoli_gem` / `gem_fba` | available + Cobra 依赖 | 对声明的 bacteria GEM case 做机制 runner/治理测试 | 自动推广到 expression 或其他物种；不由 route 推导性能 |
| `gears` / `donor_predictor` | planned；`.53` 有受门控资产与环境记录 | 在批准的远端证据中单独报告其可复现实验 | 本地无 checkpoint 时的 mock 路径不是真 GEARS；不与不可比指标混表 |
| `scgpt` | planned；远端资产，不入 Git | 仅在批准的 checkpoint/evidence 上报告 | 不能从 registry 或 wrapper 存在推导 validation |
| `norman_mean_baseline` | planned；远端资产 | 可作为明确标注的 naive baseline evidence | 不得当成训练模型或默认预测器 |
| `yeast_deletion_fitness` | planned；无权重 | 仅登记未来数据缺口 | 不得生成 deletion-fitness 数值 |
| `pathway_scoring` / `embedding` / `state_scoring` | 按窄 case runner 条件性接入 | 仅对应数据集/对象/物种的现有 case | 不得把 marker/signature/状态刻画扩大成任意扰动预测 |
