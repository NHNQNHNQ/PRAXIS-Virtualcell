# 验证

## 2026-10-07 菌株参考与文献监督组件

最新本地 CI 同选择集 **1019 passed**，全仓 Ruff 和 `git diff --check` 通过。新增测试覆盖同株跨条件参考、跨株/基因型拒绝、单模态与七组合、研究内命名空间、默认菌株档案与旧物种预测拒绝、冻结源文件和中间组件哈希、train-only MIC 分布及删失保留、官方文献缓存/失败状态、JATS/OAI 段落表格定位、原文逐字引用和化合物编号/结构/document 校验。数据 CLI 不读取凭据或创建模型客户端。

真实核验了 **24 个菌株集合、42 个模态视图、73 次 API 请求、30 个原生特征查询和 554 个字段引用**。训练 MIC 组件为 7227 个，保留 7774 次测量；有组学组件48个，读取1个AB5075视图、10次真实工具调用和159个字段引用。字段引用不是独立生物实验。验证/测试 MIC 没有物化为训练目标，原件保持单份。

实际文献 pilot 选择25篇，取得4篇开放正文，1210个原文定位、73个引句候选和39个论文化合物编号映射均通过回读；两次禁网重建7个输出逐字相同。14篇正文访问失败及单次官方补取结果如实保留，没有冒充成功。编译3个来源复核的联合组件，分别为表型机制线索、作者假说和机制未知，均不声明直接靶点结合。这些转述来自代理，不是人工金标。

公开聚合记录见 [strain_training_verification_20261007.json](../reports/llm_platform/strain_training_verification_20261007.json)，文件结构与使用见 [STRAIN-TRAINING](STRAIN-TRAINING.md)。没有调用付费 LLM API、启动训练或测得药效准确率/组学增益。

## 2026-10-07 扩容、全局冻结与监督队列

最新本地 CI 同选择集 **934 passed**，全仓 Ruff 通过。新增检查覆盖分页 offset/过滤条件/源版本与重复活动、缓存只读复用和禁网重建、全物种结构/骨架/研究分组、巨型连通组与分组不足、冻结来源变更拦截、按物种及宏平均评分、train-only 队列和真实 v1/v2 工具观察引用。数据 CLI 测试明确拦截任何 LLM 配置或客户端创建。

实际扩容从官方源累计取 EC/KP/PA 各 5000 条活动，新增准入 12342 条。49368 个四级来源定位、原始测量及删失关系通过核验；7 个 canonical 标签文件两次禁网重建逐字一致，旧文件未变。v2 索引含 24792 条记录、10813 个结构身份。原始数据、旧缓存和旧标签没有复制。主 scaffold 评估冻结为 train/validation/test 15553/3021/6218 条，跨物种统一分组。

实际四协议各自要求的结构/骨架/研究身份跨集合重叠为零；所有推理行均通过字段白名单核验。主监督队列含 28 个视图、32 个候选、48 个 train 私有定位，验证/测试定位为零；172 次真实工具重放、48 次原生特征查询、2364 个精确引用与 352 个 null 观察通过校验。公开聚合记录见 [species_expansion_verification_20261007.json](../reports/llm_platform/species_expansion_verification_20261007.json)。

这些是数据与工程验证；本轮没有生成 LLM 药效预测或启动训练。冻结标签不会提供给推理，待审核观察模板也不等于药效真值。实际分组覆盖、来源限制和监督审核状态见 [DATA-READINESS](DATA-READINESS.md)。

## 2026-10-07 首版物种参考映射库

首版本地 CI 同选择集 **881 passed**，Ruff 与 `git diff --check` 通过。新增测试覆盖独立来源集合、七种模态视图、跨物种与嵌套引用拒绝、原生引用保留、推定对照与未知尺度固定显示、MIC 四级原生来源关联、重复活动与冲突、单份答案索引及无标签推理白名单。

实际本机数据验证包括：SQLite 完整性和外键零错误；12,450 条推理输入逐条白名单检查；四物种各七组合共 28 个 overview 请求，以及 12 个真实特征查询共 **40 个 Web API 请求**；12 个特征的引用路径和值均通过校验。当前 35 个可加载 profile 包含 4 个引用集合，原生模态数量为 genome=23、transcriptome=4、proteome=4，集合不重复计为实测样本。MIC 补取的原生缓存已禁网重建，800 条新实验标签的 3,200 个活动/assay/document/结构定位逐条核验。

AB 蛋白对照身份仍是可审计推定，固定物种参考不构成实际样本配对。当前首批补库也不构成完整 ChEMBL 导出；尚未冻结这批新数据的评估、调用 LLM 评价药效、训练或证明组学收益。代码测试及上述真实读取是工程验证。原始数据保持单份，公开验证记录见 [species_database_verification_20261007.json](../reports/llm_platform/species_database_verification_20261007.json)，覆盖与来源限制见 [DATA-READINESS](DATA-READINESS.md)。

## 2026-10-07 补库前的智能体架构与多组学

当前 CLI/Web 默认执行规划、组学分析、精确引用校验、科学审查和最多一次修订/复审。多组学 v2 支持 genome/transcriptome/proteome 七种组合，v1 真实 AB5075 RNA 输入保持兼容。公开阶段可以导出为默认待审核的 SFT 记录，监督答案与推理输入分开。

本地与 CI 相同的选择集 **778 passed**，Ruff、`git diff --check` 和 CLI 入口通过：

```bash
.venv/bin/python -m pytest -q tests/agent_runtime tests/omics tests/llm_prediction tests/datasets tests/knowledge \
  tests/test_llm_platform.py tests/test_llm_platform_agents.py tests/test_llm_platform_ui.py \
  tests/mdr_gnb/unit/test_abstain.py tests/mdr_gnb/unit/test_features.py \
  tests/mdr_gnb/unit/test_ensembler.py tests/mdr_gnb/unit/test_critic.py \
  tests/mdr_gnb/unit/test_rule_baseline.py tests/mdr_gnb/unit/test_species_registry.py \
  tests/mdr_gnb/unit/test_report_builder.py tests/mdr_gnb/api/test_schemas.py
.venv/bin/python -m ruff check praxis2 praxis_virtualcell tests
```

测试验证所选模态实际被读取并引用、不同菌株/条件拒绝融合、实测蛋白组与参考翻译区分、缺失值不补零、未选数据隔离、修订后的第二次审查、失败不发布数值以及人工金标也满足模态覆盖。页面测试用 Node 实际执行静态 JavaScript；没有 Node 时明确跳过该项。真实本地 AB5075 工具读取接入新角色流程的测试通过，但该测试的模型回复为离线模拟。GitHub 缺少不可再分发的本地 profile 时，实际文件用例明确跳过。

新增测试覆盖真实标签与增效上下文隔离、删失区间、盐/母体分组、研究限定菌株命名空间、联合传递分组、无标签推理输入、冻结不可覆盖、事后覆盖率评分、实际来源监督队列、机制作用域与引用，以及机制不能替代模态观测。数据 CLI 不读取凭据或构造模型客户端。

本次实际接入 19 个本地 genome-only 参考、53 上 2 列原始 RNA，未增加严格组学与药效配对、实测蛋白组或专用微调模型。工程链路验证不代表药效准确率评估。架构和导出边界见 [AGENT-ARCHITECTURE](AGENT-ARCHITECTURE.md)，实际数据准入见 [DATA-READINESS](DATA-READINESS.md)。

真实 DeepSeek 验证使用原平台凭据、同一个现有生成候选与 AB RNA 背景，推理不提供实测 MIC。前两次分别因前言/数字 MIC 漏引用、嵌套 provenance 路径引用错误被拒绝，报告保存且 MIC 未发布。补明确输出契约、机制查询独立 source_id 与已核验路径示例后，第三次完成规划→检索分析→科学审查，`completed`、引用通过、审查接受；活性 uncertain、MIC null、confidence 未校准。有效公开轨迹导出为 3 条 needs_review 记录。

完整报告保留在本地 `reports/llm_live/agent_smoke_grounded_20261007/001.json`，工程元数据见 [engineering_verification_20261007.json](../reports/llm_platform/engineering_verification_20261007.json)。53 隔离环境的验证使用真实 RNA 与明确标为离线 fixture 的模型回复，没有远程外部 LLM 调用；不能混作真实模型验证。现有第三方组学缺失时 CI 会跳过对应真实文件用例，其余契约测试仍运行。

## 2.1 纯 LLM 与组学入口

当前 CI 安装 `.[dev,api,chemistry,omics]`，运行智能体框架、组学加载、LLM 证据校验、页面 API 和保留的基础兼容测试。2026-10-06 本地同一选择集 **474 passed**；Ruff 和 `git diff --check` 通过。其中 41 条组学测试包含小型真实 H5AD 文件、损坏哈希/形状边界、来源和未给药数组隔离，89 条 LLM 分析测试验证引用拒绝、一次格式纠正与多轮思考历史。

```bash
.venv/bin/python -m pytest -q tests/agent_runtime tests/omics tests/llm_prediction tests/test_llm_platform.py \
  tests/mdr_gnb/unit/test_abstain.py tests/mdr_gnb/unit/test_features.py \
  tests/mdr_gnb/unit/test_ensembler.py tests/mdr_gnb/unit/test_critic.py \
  tests/mdr_gnb/unit/test_rule_baseline.py tests/mdr_gnb/unit/test_species_registry.py \
  tests/mdr_gnb/unit/test_report_builder.py tests/mdr_gnb/api/test_schemas.py
.venv/bin/python -m ruff check praxis2 praxis_virtualcell tests
```

GitHub 不携带本地组学源文件，真实 AB5075 文件的用例会明确跳过；合成输入包和 H5AD 文件的边界验证仍运行。已在 APFS 暂存源代码构建 2.1.0 wheel，并在仓库外从 wheel 读取实际组学包、提供静态页面，确认页面资源已打包，凭据、大型数据和实时报告未打包。

真实 API 验证与离线测试分别记录。2026-10-06 使用原平台本地凭据及 `deepseek-v4-pro`，处理现有 24 个候选：23 个 `completed` 且引用校验通过，1 个 `unsupported`。候选编号、原始 SMILES、菌株/模型身份及输入顺序已核对。12 个有数值 MIC 估计，其余为未知；全部信心为低、未经校准。

初次批量运行的 10,000 tokens 预算导致 8 份截断和 1 份工具轮次耗尽，原记录保留。扩大到 65,536 tokens、限制最后一轮提交答案后，复用 6 份通过报告，补跑其余 18 个。最终被拒绝的 `candidate-020` 在第八轮首次提交答案，其中一条局限说明有有效引用，但未填写要求的结构化观察；没有剩余轮次进行纠正，其 MIC 保持未知。

复核同时发现正文显示精度的误判：`9.52`、`4.21`、`9.53` 是实际表达值的两位小数舍入，结构化观察与引用仍保留完整精度。校验现已允许按正文所显示的小数位正确舍入，机器字段的数值、来源与路径仍必须精确一致。原报告及其原始失败原因保留；该候选仍未满足结构化观察合同，不能据此转为有效预测。

不含凭据或完整药效输出的工程记录见 [engineering_verification_20261006.json](../reports/llm_platform/engineering_verification_20261006.json)。完整报告及按输入顺序排列的 `summary.json` 仅保存在本地 `reports/llm_live/batch_20261006/`；首份报告可在页面按编号重开，复查无需再次调用模型。真实调用成功只说明工具链与引用格式可运行，不是独立 MIC、杀伤能力或靶点准确率评估。

## 历史组件与整合验证

```bash
.venv/bin/python -m pytest tests/agent_runtime -q
.venv/bin/python -m pytest tests/mdr_gnb -m 'not (integration or llm or remote)' -q
.venv/bin/python -m ruff check praxis2 praxis_virtualcell tests
```

`integration` 等标记用于选择测试；Redis/PostgreSQL 集成测试还检查显式连接环境变量。标记 `local_artifacts` 的 MDR 测试需要本地数据/模型及相应科学依赖，可用 `-m 'not local_artifacts'` 排除。基础 CI 使用明确的离线选择集。

AB 组件另有依赖及测试入口，见组件 README。整合验证包含从本地旧版本权重运行直接 MIC，并保持与 09-23 的较新服务器比较结果区别。

历史整合 CI 运行不依赖大型本地工件的智能体、数值工具/API 合同测试和安装检查；旧论文实验、Docker/A100 和多阶段 release 合同退出 CI。

独立组件的验证记录见 `reports/antibacterial/direct_mic/import_verification_20261006.json` 与 `reports/antibacterial/synthemol/migration_verification_20261006.json`：12 个原版本权重各复现一条留出预测，4 项 direct MIC 与 5 项生成器验证单测通过。新主包 wheel 在仓库外安装后确认版本 2.0.0、物种规则、CLI、API `/health` 与 `/species` 可用；该安装检查未装大型工件，物种可用数为零符合预期。

2026-10-06 的本地检查：CI 中完全相同的测试选择集 **335 passed**。现有 MDR 本地环境为 Python 3.11、NumPy 2.4.6、scikit-learn 1.9.0、RDKit 2026.3.3，满足当前安装约束。MDR 回归已确认 **618 条用例通过、3 条跳过**；一次整套运行记录 616 passed / 3 skipped，随后修复 species-agent 测试的迁移路径并定向确认该文件 3 passed。跳过项是未配置 Redis/PostgreSQL 和未安装 AMRFinder。未重新运行完整套件或重训模型。

历史科学 campaign 和报告快照测试保存在同级归档目录 `PRAXIS-virtualcell-old/records/2026-10-06/migrated-legacy-tests/mdr_gnb/`，不纳入当前回归。它们包含旧战役与当前单药请求校验、T6 报告 schema 不兼容的问题；VERDICT 逐字快照也受本次报告目录重排影响。原始报告和科学结果未改写或重算。当前报告目录为 `reports/antibacterial/mdr_gnb/`。
