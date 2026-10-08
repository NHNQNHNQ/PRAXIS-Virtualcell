# PRAXIS-VirtualCell

加载具体菌株的参考组学，由 LLM 直接预测候选分子的抗菌活性、MIC，并提出有数据依据的靶点与机制假说。默认使用 DeepSeek；组学查询与结构处理工具不承担药效预测。

## 当前入口

- `praxis_virtualcell/data_packs/`：从原平台恢复的 AnnData/MuData 校验、只读矩阵读取与显式特征对齐。
- `praxis_virtualcell/omics/`：原生 v1/v2 组学与菌株参考集合，支持单组学与组合选择，保留各来源条件、单位和引用身份。
- `praxis_virtualcell/llm_prediction/`：规划、组学工具分析、引用校验、科学审查、一次修订与复审、JSON/Markdown 报告和监督轨迹导出。
- `praxis_virtualcell/knowledge/`：按实际 taxon/strain 和候选精确结构检索独立机制证据，区分参考功能与蛋白实验。
- `praxis_virtualcell/cell_structure/`：查询有来源的区室、邻接关系及蛋白定位，严格区分物种背景和菌株证据。
- `praxis_virtualcell/datasets/`：真实实验监督、菌株 SQLite 索引、条件化 MIC 目标、官方文献定位与审核、标签隔离、分组冻结和事后评分。
- `praxis2/llm/`：复用原平台客户端，支持 DeepSeek 思考模式与连续工具调用。
- `praxis_virtualcell/web/`：选择具体菌株与组学模态、输入候选结构、查看概览与分析报告的本地页面。

旧 MIC、AMR、QSAR、扰动和世界模型不进入新预测入口。实测 MIC 记录不作为推理输入或查表答案。历史工具保留在 `praxis-mdr` 和独立组件中，已有结果保持原科学范围。

默认流程是「SMILES 和菌株身份验证 → 加载细胞结构背景 → 规划 → 读取所选组学与结构 → 分析与引用校验 → 审查 → 必要时修订并复审 → 报告」。每个所选组学都要实际读取并引用。可单独配置 Qwen 负责分析与修订，规划/审阅继续使用基础服务；审查通过不代表实验验证。候选分子的模型输入只有经校验的 SMILES，名字和编号仅作私有溯源。六项 MIC 实验条件从 Web/CLI 传入，未知保留为空，与组学采样条件分开。架构和数据契约见 [AGENT-ARCHITECTURE](docs/AGENT-ARCHITECTURE.md)，Qwen 接入与训练见 [QWEN-MIC-SFT](docs/QWEN-MIC-SFT.md)。

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
.venv/bin/praxis-vc inspect --profile AB5075-STRAIN-REFERENCE
.venv/bin/praxis-vc inspect --profile AB5075-STRAIN-REFERENCE --modalities transcriptome
.venv/bin/praxis-vc inspect --profile EC-MG1655-STRAIN-REFERENCE --modalities genome transcriptome
.venv/bin/praxis-vc serve --port 8787
```

打开 `http://127.0.0.1:8787`。页面显示实际输入包的身份与数据覆盖；分析后可查看报告、工具轨迹以及 JSON/Markdown；带报告编号的页面链接可重新打开，无需再次调用模型。

```bash
.venv/bin/praxis-vc batch --profile AB5075-STRAIN-REFERENCE --input candidates/synthemol_20260923/repeat_1/molecules.csv --limit 1 --output reports/llm_live/first-candidate
```

批量导入只读取 SMILES 和候选编号，忽略 CSV 的历史 score/Q_value 与终点字段。去掉 `--limit` 可处理完整候选集；每个候选都会调用配置的 LLM。

页面始终提供基因组、转录组、蛋白组选择，仅启用当前档案实际可用的项。CLI 使用 `--modalities genome transcriptome proteome` 选择组合，缺失项会拒绝。本地报告可导出公开阶段与工具轨迹，默认进入待审核队列，不会把 LLM 预测 MIC 标成真实监督答案：

```bash
.venv/bin/praxis-vc export-sft --input reports/llm_live/assessment.json --output local/sft/assessment.jsonl
```

## 数据与结果语义

本机现有菌株参考包含基因组注释、真实转录组和实测蛋白丰度。同一集合只引用同菌株、同声明基因型的来源，允许不同模态来自不同培养条件。AB5075、MG1655、PAO1 各可使用三模态；K. pneumoniae 的 HS11286、K26、NCTC418 分别只有基因组、RNA、蛋白组，分开选择。其余 18 个 E. coli 档案为 genome-only。参考注释不能代替新分离株的全基因组变异；未知时间、温度、基因型和生长期保持未知。处理后表达、实际 delta 和 MIC 标签不进入新候选工具结果。

MIC 是未经校准的 LLM 估计，可以为未知；它表示生长抑制，不等于杀伤率。靶点与机制保留假说身份。引用校验只证明观察值与工具返回一致，不证明药效正确或靶点因果关系。无实际组学查询或事实引用校验失败时返回 `unsupported`，不调用其他预测器补数值。

大型数据只存本地 `data/organisms/`，对应归档路径保留引用。数据准备与复现见 [OMICS](docs/OMICS.md)。本地 `.env` 与完整实时报告不进入 GitHub。

当前监督采用“SMILES—菌株—参考组学—实验条件—MIC—文献机制解析”。底层复用 **24,792 条 MIC、10,813 个结构身份、4 个物种**的 canonical 文件。11,973 条有明确菌株名称，917 个带命名空间的身份不等于 917 个已核验的独立生物菌株；研究内编号不跨文献合并。最新 v3 有 **7,193 个组件、7,372 次训练测量、1,950 个有组学报告、104 个机制联合报告**；分子公开输入只用 SMILES，答案统一为完整 Assessment，原始数据不重复存放。报告是来源核验后构建的弱监督，人工机制金标仍为 0。覆盖、真实试训和评估入口见 [QWEN-MIC-SFT](docs/QWEN-MIC-SFT.md)。历史物种索引保留作只读来源，旧物种参考入口不再作为默认档案。

2026-10-08 已接入细胞结构查询、结构报告及证据范围检查。36 条结构事实均为四物种的背景知识，菌株实测结构与蛋白定位记录为 0。独立 `qwen_joint_sft_v4_compact` 为 1,950 条组学报告增加区室查询并共享 v3 原始索引；7,193 条全量预检通过，最长 31,740 token，无截断。53 上八卡 Qwen3-32B 已完成 12 步 LoRA 工程测试，包括最长样本反向、checkpoint1→6→12 恢复、适配器导出及扰动后重载；主机最低可用内存的观测值为 292.07 GiB，无 OOM 或 swap，结束后 GPU 已释放。试训适配器位于 53 的 `outputs/qwen3_32b_joint_lora_v4_guarded_20261008/adapter`，仅供工程验证；独立 MIC 预测评估尚未执行，正式全量训练暂停。详情见 [试训验证报告](reports/llm_platform/qwen_v4_compact_trial_verification_20261008.json) 和 [CELL-STRUCTURE](docs/CELL-STRUCTURE.md)。

训练通过独立 supervisor 保护：真实 cgroup 硬上限 300 GiB、high 260 GiB、swap 0、`memory.oom.group=1`；主机可用内存低于 160 GiB 时停止整个本次训练组，训练入口在加载权重前要求有效硬限制。guard 的 observed peak 来自 1 秒采样，NCCL heartbeat 为 120 秒、DDP timeout 为 600 秒，cold 烟测最长 900 秒。安全运行入口见 [QWEN-MIC-SFT](docs/QWEN-MIC-SFT.md)。

## 验证与后续

离线测试覆盖实际文件读取、样本/特征对应、未来数据隔离、多轮工具历史与事实引用。真实 API 运行验证工程链路，尚不构成独立药效准确率评估。平台当前使用基础 API 模型；现有 12 步 trial adapter 仅供工程验证，正式全量微调与独立 MIC 预测评估尚未开展。 四物种主评估按全局化学骨架冻结：训练/验证/测试为 15,553/3,021/6,218 条，各集合均包含四物种；实验答案独立保管。

2026-10-07 完成智能体阶段架构、多组学选择、机制证据接线、监督/评估接口及物种参考映射。最新测试结果见 [TESTING](docs/TESTING.md)。T7 接入 19 个 genome-only 参考，53 接入两列真实 AB RNA（2 run、1 BioSample）。原有 AB 实验 MIC 准入 11650 条，其中 AB5075 单药 52 条；补库后总数为 24792，严格组学配对仍为 0。实际数据、冻结划分与下一步准入条件见 [DATA-READINESS](docs/DATA-READINESS.md)。

新架构已完成一次真实 DeepSeek 规划/检索/分析/审查运行并通过引用校验：输出为活性不确定、MIC 未知及机制假说。前两次运行的格式/引用问题均被拦截，原报告保留；工具现在提供已核验的引用路径示例，仍不自动修正模型答案。工程记录见 [verification](reports/llm_platform/engineering_verification_20261007.json)，不能据此声称独立药效准确率。

2026-10-06 已完成现有 24 个候选的实际批量处理：23 份通过引用校验，1 份被拒绝；474 条本地测试通过。详细结果与限制见 [TESTING](docs/TESTING.md)。完整实时报告保留在本地，不进入 GitHub。

作者药物生成器及外部资产仍需恢复。现有 24 个候选结构已接入同一接口；重复记录不计为 48 个不同分子。

历史整合与来源见 [CONSOLIDATION](docs/CONSOLIDATION.md)、[DATA-ASSETS](docs/DATA-ASSETS.md)、[DATA-LICENSES](docs/DATA-LICENSES.md)。代码许可 MIT；第三方数据遵循原来源许可。
