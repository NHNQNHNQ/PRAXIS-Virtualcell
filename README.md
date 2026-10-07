# PRAXIS-VirtualCell

加载具体菌株样本或物种参考组学，由 LLM 直接预测候选分子的抗菌活性、MIC，并提出有数据依据的靶点与机制假说。默认使用 DeepSeek；组学查询与结构处理工具不承担药效预测。

## 当前入口

- `praxis_virtualcell/data_packs/`：从原平台恢复的 AnnData/MuData 校验、只读矩阵读取与显式特征对齐。
- `praxis_virtualcell/omics/`：原生 v1/v2 组学与独立物种参考集合，支持单组学与组合选择，保留各来源株、条件、单位和引用身份。
- `praxis_virtualcell/llm_prediction/`：规划、组学工具分析、引用校验、科学审查、一次修订与复审、JSON/Markdown 报告和监督轨迹导出。
- `praxis_virtualcell/knowledge/`：按实际 taxon/strain 和候选精确结构检索独立机制证据，区分参考功能与蛋白实验。
- `praxis_virtualcell/datasets/`：真实实验监督整理、官方源数据补取、物种参考 SQLite 映射、标签隔离、分组冻结和事后评分。
- `praxis2/llm/`：复用原平台客户端，支持 DeepSeek 思考模式与连续工具调用。
- `praxis_virtualcell/web/`：选择菌株样本或物种参考、输入候选结构、查看组学概览与分析报告的本地页面。

旧 MIC、AMR、QSAR、扰动和世界模型不进入新预测入口。实测 MIC 记录不作为推理输入或查表答案。历史工具保留在 `praxis-mdr` 和独立组件中，已有结果保持原科学范围。

默认流程是「结构和身份验证 → 规划 → 读取所选组学 → 分析与引用校验 → 审查 → 必要时修订并复审 → 报告」。每个所选组学都要实际读取并引用。审查角色使用同一个配置好的 LLM，审查通过不代表实验验证。架构、数据契约和微调任务对应关系见 [AGENT-ARCHITECTURE](docs/AGENT-ARCHITECTURE.md)。

## 启动

安装见 [INSTALL](docs/INSTALL.md)。本地 `.env` 保存凭据并被 Git 忽略：

```text
DEEPSEEK_API_KEY=自己的本地凭据
PRAXIS_ANTHROPIC_BASE_URL=https://api.deepseek.com
PRAXIS_MODEL=deepseek-v4-pro
```

`PRAXIS_ANTHROPIC_BASE_URL` 是原框架兼容配置名，实际使用 OpenAI-compatible Chat Completions。凭据只在服务端读取。

```bash
.venv/bin/praxis-vc profiles
.venv/bin/praxis-vc inspect --profile AB5075-AZI000
.venv/bin/praxis-vc inspect --profile AB5075-AZI000 --modalities transcriptome
.venv/bin/praxis-vc inspect --profile AB-SPECIES-REFERENCE --modalities genome transcriptome
.venv/bin/praxis-vc serve --port 8787
```

打开 `http://127.0.0.1:8787`。页面显示实际输入包的身份与数据覆盖；分析后可查看报告、工具轨迹以及 JSON/Markdown；带报告编号的页面链接可重新打开，无需再次调用模型。

```bash
.venv/bin/praxis-vc batch --profile AB5075-AZI000 --input candidates/synthemol_20260923/repeat_1/molecules.csv --limit 1 --output reports/llm_live/first-candidate
```

批量导入只读取 SMILES 和候选编号，忽略 CSV 的历史 score/Q_value 与终点字段。去掉 `--limit` 可处理完整候选集；每个候选都会调用配置的 LLM。

页面始终提供基因组、转录组、蛋白组选择，仅启用当前档案实际可用的项。CLI 使用 `--modalities genome transcriptome proteome` 选择组合，缺失项会拒绝。本地报告可导出公开阶段与工具轨迹，默认进入待审核队列，不会把 LLM 预测 MIC 标成真实监督答案：

```bash
.venv/bin/praxis-vc export-sft --input reports/llm_live/assessment.json --output local/sft/assessment.jsonl
```

## 数据与结果语义

本机现有物种参考包含基因组注释、真实转录组和实测蛋白丰度，各模态保留独立来源与条件。参考注释不能代替新分离株的全基因组变异；固定参考丰度不能代表所有菌株的当前状态。未知时间、温度、基因型和生长期保持未知。处理后表达、实际 delta 和 MIC 标签不进入新候选工具结果。

MIC 是未经校准的 LLM 估计，可以为未知；它表示生长抑制，不等于杀伤率。靶点与机制保留假说身份。引用校验只证明观察值与工具返回一致，不证明药效正确或靶点因果关系。无实际组学查询或事实引用校验失败时返回 `unsupported`，不调用其他预测器补数值。

大型数据只存本地 `data/organisms/`，对应归档路径保留引用。数据准备与复现见 [OMICS](docs/OMICS.md)。本地 `.env` 与完整实时报告不进入 GitHub。

物种参考模式按“药物—实测 MIC—物种”建立监督，每物种每模态仅选一个来源，允许参考株与实验株不同。参考集合只存指针，SQLite 索引通过 canonical 标签位置关联答案，推理导出不包含终点。首版有 **12,450 条 MIC、6,199 个结构身份、4 个物种、12 个选定原生参考**，四物种均可选择三种单模态与七种组合。AB 蛋白对照身份有明确的推定限制。已复用本机数据并补取有限首批官方记录。配置与使用见 [SPECIES-DATABASE](docs/SPECIES-DATABASE.md)，实际覆盖和剩余缺口见 [DATA-READINESS](docs/DATA-READINESS.md)。

## 验证与后续

离线测试覆盖实际文件读取、样本/特征对应、未来数据隔离、多轮工具历史与事实引用。真实 API 运行验证工程链路，尚不构成独立药效准确率评估。当前使用基础 API 模型，尚未训练专用微调模型。

2026-10-07 完成智能体阶段架构、多组学选择、机制证据接线、监督/评估接口及物种参考映射。最新测试结果见 [TESTING](docs/TESTING.md)。T7 接入 19 个 genome-only 参考，53 接入两列真实 AB RNA（2 run、1 BioSample）。原有 AB 实验 MIC 准入 11650 条，其中 AB5075 单药 52 条；补库后总数为 12450，严格组学配对仍为 0。实际数据、冻结划分与下一步准入条件见 [DATA-READINESS](docs/DATA-READINESS.md)。

新架构已完成一次真实 DeepSeek 规划/检索/分析/审查运行并通过引用校验：输出为活性不确定、MIC 未知及机制假说。前两次运行的格式/引用问题均被拦截，原报告保留；工具现在提供已核验的引用路径示例，仍不自动修正模型答案。工程记录见 [verification](reports/llm_platform/engineering_verification_20261007.json)，不能据此声称独立药效准确率。

2026-10-06 已完成现有 24 个候选的实际批量处理：23 份通过引用校验，1 份被拒绝；474 条本地测试通过。详细结果与限制见 [TESTING](docs/TESTING.md)。完整实时报告保留在本地，不进入 GitHub。

作者药物生成器及外部资产仍需恢复。现有 24 个候选结构已接入同一接口；重复记录不计为 48 个不同分子。

历史整合与来源见 [CONSOLIDATION](docs/CONSOLIDATION.md)、[DATA-ASSETS](docs/DATA-ASSETS.md)、[DATA-LICENSES](docs/DATA-LICENSES.md)。代码许可 MIT；第三方数据遵循原来源许可。
