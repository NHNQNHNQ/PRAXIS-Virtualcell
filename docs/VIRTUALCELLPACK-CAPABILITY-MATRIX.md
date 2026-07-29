# VirtualCellPack 能力矩阵（P0–P10）

P0 基线：`8e0d06348ebdf22e076037e6d661094ae877c5d1`；P8 Golden 起始基线：`09fb1bb3d02adfceed504cbccd7cf36c54a61b69`；P8 产品化收口起始基线：`b6cf226382cb841fb50e70875c82d1804ae5681e`；P9 起始基线：`480706fbf58343565532debeca70c4de093b045f`；P10 起始基线：`b0064fab936f06d09a88eea5292e934410302145`。本表是能力与证据边界，不是性能排名；`pack_valid`、`model_compatible`、`scientifically_validated` 不得互换。

| 能力/组件 | 当前实现与真相源 | `pack_valid` | `model_compatible` | `scientifically_validated` | 结论与边界 |
|---|---|---:|---:|---:|---|
| 结构化 request | `core/request.py`、`core/request_v2.py`、`agents/request_adapter.py`、`species_schema.py` | N/A | 输入前置 | N/A | 必填字段缺失由 schema fail-closed；v2/domain/bundle nested JSON 验证后递归不可变；不猜测 targets/output |
| 确定性 runtime | `core/runtime.py`、`workflows/predict_delta_expression.py`、MessageBus | Pack-aware 路径只接受 registry 签发的 `RegisteredPack` | 完整 Pack identity 时由 execution plan 决定；无 Pack 时走显式 legacy adapter | 不自动声称 | OFFLINE 零 LLM；trace、hash、governance 保持确定性；只给半个 Pack identity 在执行前拒绝 |
| SpeciesBrain | `agents/species_brain.py` + `brains/virtualcell/**` | N/A | 提供规则上下文，不裁决 | 不提供 | 只读 YAML、登记 rules_referenced；不产数值 |
| route table | `agents/route_table.py` | N/A | 仅为无 Pack legacy adapter 的声明式条件 | 不提供 | engine/disposition/reason 是兼容能力图，不是 Pack-aware 模型事实源或性能结论 |
| case dispatch | `predictors/case_dispatch.py`、`case_runner_agent.py` | N/A | 仅为无 Pack legacy adapter 保留；GEARS 仍受 `.53` checkpoint+依赖窄门 | 仅可引用已有、口径匹配的 evidence | Pack-aware plan 不调用 case dispatch，不满足计划条件也不 fallback 到 mock |
| Strict Model Zoo | `model_zoo/registry.yaml`、`registry.py`、`capability_registry.py::ModelCard` | registry 不是 Pack | `vc.model-card.v1` 完整声明才进入 P6 planner；旧条目仅 legacy 可查询 | training card/provenance 不是验证结果本身 | taxon/modality/assay/domain/perturbation/task/output/namespace/representation/assets/resources/uncertainty/OOD 全部 strict；导出副本不能改 registry truth；未增加模型或权重 |
| CapabilityRegistry | `model_zoo/capability_registry.py` | 只信 `RegisteredPack`，任意 manifest/path 均不能授予 valid | Request×Pack×Model 精确关系检查；缺任一维度即 false | 固定 false | full request/model/Pack/environment fingerprint；重复 requested outputs、跨 modality/namespace 交叉误配均拒绝 |
| ModelBroker + ExecutionPlan | `agents/model_broker_agent.py`、`vc.execution-plan.v1` | 未注册 Pack 产空 plan | 只实例化 `executable=true` steps；import/constructor 失败会修订 plan | 固定 false | 稳定按模型名排序；动态 wrapper 无需模型专用 build/route/case 分支 |
| Runtime environment/output gate | `EnvironmentSnapshot`、`ModelWrapper` | 不改变 Pack 状态 | 缺 dependency/resource/asset/wrapper/task/output adapter 或坏 plugin 输出均 fail-closed | 不提供 | 当前只执行 `predict_delta_expression → delta_expression`；delta 必须非空有限数值，uncertainty method 必须在 card 内 |
| P7 public data catalog | `catalogs/data_catalog.yaml`、`data_portal_service.py`、`vc.data-catalog.v1` | 不提供；catalog valid/file available 都不是 Pack 注册 | 不提供 | 固定不提升 | strict metadata、source/terms/path/size/hash；四物种五文件；无大数据入 Git |
| P7 allowlisted download | `/api/data-catalog/**/download` | 不提供；每次只证明当前外置文件匹配清单 | 不提供 | 不提供 | containment、普通文件、size、SHA-256 每次重验；缺失/篡改/hash 不可读/逃逸 fail-closed；Range 不绕过校验 |
| P7 quarantined upload | `/api/data-uploads`、`vc.upload-receipt.v1` | 不提供；receipt 不是 Pack | 不提供 | 不提供 | bearer 前置、body/文件/quota 限制、原字节/hash/原子 receipt；不解包、去重、归一化、补零、mapping、注册或预测 |
| P7 data UI | `DataLibrary.tsx` | 只显示后端资源状态 | 不判断 | 不裁决 | 精确物种筛选、可用下载、内存 token 和隔离上传；未就绪文件禁用；LLM 不参与 |
| P8 三物种微型 Pack | `example_packs/{human,mouse,bacteria}`、`vc.pack.v0.2` | 每个 manifest、约 44 KB H5AD、asset hash 和完整语义门通过后为 true | 不自动提供 | 固定 false | human/mouse 使用 `EnsemblGene`，E. coli 使用 `NCBIGene`；同一现有 registry 加载，不复制/转换 P7 数据，不改核心 runtime |
| P8 Pack product index/CLI | `pack_product.py`、`praxis-vc pack *`、`vc.pack-index.v1` | inspect 明确为 null；validate/register/list 每次重验 | compatibility/run 只消费现有 capability planner | 固定 false | register 使用本地锁和原子索引；冲突、篡改、缺依赖均 fail-closed；基础 `data_packs` 层不依赖 model zoo/runtime |
| P8 Pack read-only API | `/api/packs*`、`vc.pack-catalog.v1`、`vc.pack-compatibility-surface.v1` | 返回后端当前重验状态 | 只有绑定具体 request 的 compatibility 才能给出 | 固定 false | 无 HTTP register；不暴露 Pack root、model cache/asset path；只给半个 Pack identity 返回 422 |
| P8 Pack capability UI | `DataLibrary.tsx` | 只显示后端 `pack_valid`/validation status | 未绑定请求时明确显示“未按请求评估” | 只显示 false | 浏览器只 GET catalog，不调用 compatibility 预判，不复制 checks 或科学路由 |
| P8 历史 job execution identity | `JobStore`、`vc.job-execution-identity.v1` | 锁定运行时 Pack ID/version/fingerprint | 锁定 plan 中 model/card/compatibility fingerprints | 不提升 | 同名 job 拒绝覆盖；legacy job 显式记录无 Pack/model，不补造旧身份 |
| P8 fail-closed 产品验收 | `test_pack_product.py`、Playwright data-library spec | Pack bytes 被改即 invalid | 无模型、错误 modality/cell domain/taxon 均空 plan/弃权 | 固定 false | 有匹配测试模型时正式 plugin 执行；所有负例 prediction 为 null，且不得 fallback 到 Mock |
| P9 八轴 OOD manifest | `data/benchmarks/p9/ood-manifest.json`、`group-fixture.json`、ADR-0008 | 不改变 Pack 状态 | 不提供运行兼容性 | fixture 固定不提供 | 固定 IID、perturbation、combination、cell type、donor、dataset/platform、species、dose/time 的 train/validation/test biological groups；fixture 只证明 strict contract 和泄漏拒绝，不是假装八轴性能 |
| P9 grouped leakage audit | `benchmarks/ood_validation.py::audit_leakage` | 不改变 | 不改变 | 仅作为验证前置门 | biological-unit 与 replicate identity 任一跨 partition 即拒绝；feature/label 字段分离；无随机 split |
| P9 无适配外部验证 | `GSE67402 → GSE94117:glycerol_time_course`、`external-validation.json` | 不授予 Pack valid | 候选是离线 benchmark，不进入 model zoo | false | 4,484 exact-intersection IDs；external adaptation=0；排除同源风险 glucose cohort；不做 ID/ortholog 转换或补零 |
| P9 abstention / risk-coverage | validation-only 阈值、condition-level selective metrics | N/A | 不提升 | 不提升 | external coverage 0.625、wrong accept 0.75、unnecessary abstain 0.5；test/external label 不参与阈值选择 |
| P9 baseline promotion gate | candidate MSE 1.0603835779；no-change 1.0533347059；paired CI 跨 0 | N/A | `available=false` | `scientifically_validated=false` | 主指标未胜简单 baseline 且 CI 上界不小于 0；MAE 略好、Pearson 有限或 runtime 成功都不能覆盖失败 |
| P10 CommunityPack 前置接口 | `community_packs/contracts.py`、`vc.community-pack.v1`、`COMMUNITY-READINESS-CHECKLIST.md` | 每个成员仍须由既有 `PackRegistry` 当前字节重验；CommunityPack 不另授予成员 Pack 状态 | 无真实 adapter，community plan 固定 `executable=false` | 固定 false | 精确绑定成员 fingerprint、丰度、medium、compartment、time/well-mixed space、共享 metabolite namespace 与 evidence；不实现世界模型 |
| P10 tiny microbial members | `example_packs/{bacteria,yeast}` | E. coli 与 S. cerevisiae 均通过同一 v0.2 Pack 全门后成立 | 不自动提供 | false | 约 44 KB 合成 H5AD；yeast 不复制 P7 GEO 数据，也不加入 P8 三物种产品 catalog |
| P10 toy exchange / no-model gate | `vc.community-exchange-ledger.v1`、`vc.community-execution-plan.v1`、`vc.community-run-result.v1` | 不改变 | 无模型时不兼容、无 step | false | 精确有理数质量收支，无 tolerance/补零/单位换算；run 只能 `prediction=null` 且 `community_model_unavailable` abstain |
| P8 Golden Norman contract | `data/golden/norman_2019/contract.yaml`、ADR-0006 | 不直接授予；先锁 source/obs/var/X/counts/split/metric | 不直接授予 | 固定不提升 | K562 `CVCL_0004` 与原样保留 source `A549` 字段分开；无随机 split、归一化、补零、去重、symbol/ortholog 转换或结果后调参 |
| P8 Golden Pack | 外置 `pack/`、checked-in `pack.manifest.yaml`、`PackRegistry` | 完整 v0.2 schema/asset/semantic/leakage/hash 验证后为 true | 不自动提供 | false | `91,205×5,045`；派生只替换 obs，X/counts raw dataset hash 与 source 一致；大数据不入 Git |
| P8 simple baseline cards | 三个一卡 registry、`GoldenBaselineWrapper` | 消费已注册 Golden Pack | 对精确 request/Pack/card/environment/asset 关系为 true | false | no-change、condition-equal global mean、alpha=1 additive ridge；canonical Ensembl target only；缺失/篡改资产直接 abstain、无 mock fallback |
| P8 Golden evaluation | `vc.golden-evaluation.v1`、`evaluation.json` hash | 记录 true，不重新授予 | 记录每次正式 runtime true | 固定 false | 30 validation + 116 test condition 逐个走 broker/governance/report；full-feature condition-macro MSE 与 condition paired bootstrap；未运行 GEARS |
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
| Capability report provenance | `vc.compatibility-report.v1`、report `provenance.execution_plan/compatibility_reports` | 独立布尔并带 Pack fingerprint | 独立布尔并带逐项 checks/reasons | P6 恒为 false | 资产可用、plan 可执行、predictor success 均不能提升科学状态 |
| Ontology 与跨物种边界 | manifest 中的标准 CURIE 或有定义 local CURIE | 仅离线语法/声明验证 | 不推导 | 不推导 | 无在线 ontology runtime 依赖；无 symbol、ortholog 或同源转换 fallback |

## 现有模型/引擎状态摘要

| registry/model 或 engine | 当前状态 | 可声称内容 | 不可声称内容 |
|---|---|---|---|
| `ecoli_gem` / `gem_fba` | card available + Cobra 依赖；P6 plugin runtime 无 growth adapter | 对声明的 legacy bacteria GEM case 做机制 runner/治理测试；card 可审计 | 不得经 P6 delta coordinator 假装执行 growth；不由 route/card 推导性能 |
| `gears` / `donor_predictor` | planned；`.53` 有受门控资产与环境记录 | 在批准的远端证据中单独报告其可复现实验 | 本地无 checkpoint 时的 mock 路径不是真 GEARS；不与不可比指标混表 |
| `scgpt` | planned；远端资产，不入 Git | 仅在批准的 checkpoint/evidence 上报告 | 不能从 registry 或 wrapper 存在推导 validation |
| `norman_mean_baseline` | planned；远端资产 | 可作为明确标注的 naive baseline evidence | 不得当成训练模型或默认预测器 |
| `norman_no_change` / `norman_global_mean` / `norman_additive_linear` | P8 外置 hash-locked artifact + 各自 strict one-card registry；不加入默认 zoo | 只可复现冻结 Norman/K562 split 上的 baseline delta、MSE 和治理报告 | 不能泛化为其他 cell/data/split；不能因分数或 runtime success 声称 scientifically validated |
| `source-log-time-feature-trend-v1` | P9 离线、hash-only 参数；不加入 model zoo | 只可复现冻结 GSE67402→GSE94117 glycerol 无适配 benchmark | 主 MSE 未胜 no-change 且 CI 跨 0，因此 `available=false`、`scientifically_validated=false`；不得用于产品预测 |
| `yeast_deletion_fitness` | planned；无权重 | 仅登记未来数据缺口 | 不得生成 deletion-fitness 数值 |
| `pathway_scoring` / `embedding` / `state_scoring` | 按窄 case runner 条件性接入 | 仅对应数据集/对象/物种的现有 case | 不得把 marker/signature/状态刻画扩大成任意扰动预测 |
