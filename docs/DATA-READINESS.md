# 当前数据接入与监督准备

2026-10-07。当前阶段完成智能体接口、真实观测接入和独立评估准备。数据建设现采用物种参考模式：实测 MIC 对应物种，每物种每模态选一个参考，严格实验配对不再是这个模式的统一门槛。实际样本模式继续保留严格配对；正式微调还需审核监督并生成训练目标。映射库与运行入口见 [SPECIES-DATABASE](SPECIES-DATABASE.md)。

## 当前 v2 覆盖

复用首版全部标签与 12 个组学参考，EC/KP/PA 的 ChEMBL 原生活动各扩至累计 5000 条；15000 条活动中，13142 条准入、1858 条排除。准入中旧 800 条只引用，新增 12342 条单独存放。连同 AB 历史数据，总计 **24792 条 MIC、10813 个结构身份**。

| 物种 | MIC 记录 | 结构身份 | 研究数 |
| --- | ---: | ---: | ---: |
| A. baumannii | 11650 | 5774 | 466 |
| E. coli | 4219 | 2378 | 169 |
| K. pneumoniae | 4369 | 3286 | 296 |
| P. aeruginosa | 4554 | 2630 | 217 |

结构可能跨物种出现，表中结构数不能相加作为全库独立结构数。当前是有序、有限页数的覆盖，不是完整 ChEMBL 导出或随机代表性样本。新增记录的 49368 个原生活动/assay/document/结构定位与原始测量、删失关系逐条核验；两次禁网重建逐字一致。817 条单位未核定、318 条组合/增效/聚合等上下文、217 条物种描述冲突等记录保留排除原因，没有为了增量降低准入要求。数据库来源链接核验不等于逐篇全文复核或重复实验。

工作目录为 `local/species_reference_expansion_20261007/`：`mic/` 保存新增标签、官方新增响应及收据，`database/v2/` 保存派生索引；旧标签和原始组学只读引用。新下载 93 个响应共约 46.8 MB。实测 MIC 只供监督和事后评分，推理输入依然只含结构、物种、参考档案和预测范围。

## 当前四物种冻结与审核队列

四套协议均冻结全部 24792 条实验，含 14068 个不同的结构—物种输入；全部训练/验证/测试集合均包含四物种。分组在物种之间统一，比例按组而非实验行数分配。

| 协议 | 独立组 | 最大组占记录比例 | 训练 / 验证 / 测试记录 |
| --- | ---: | ---: | --- |
| compound | 10715 | 2.68% | 17553 / 2337 / 4902 |
| scaffold（主协议） | 3415 | 4.80% | 15553 / 3021 / 6218 |
| study | 895 | 2.02% | 16652 / 3052 / 5088 |
| scaffold_study | 169 | 89.57% | 24119 / 402 / 271 |

各协议要求隔离的身份跨集合重叠均为零。scaffold 仍有 622 个研究跨集合，因此评估的是新骨架，不能同时声称新研究泛化；study 有 228 个归一化结构跨集合。联合协议消除两类重叠，但 22207 条记录连成一组，测试集太小，仅作为补充诊断。主协议测试集 AB/EC/KP/PA 分别有 2336/1306/1262/1314 条记录。不同协议必须分别使用自己的训练集，不可合并训练后再宣称各测试集独立。

主 scaffold 下已生成 **32 个待审核候选（每菌 8 个）、28 种真实工具观察视图和 48 个私有训练答案定位**。跨菌合计 30 种不同结构。172 次工具调用重放、48 次原生特征查询和 2364 条精确来源引用通过核验，验证/测试记录混入为零。观察视图只存一次，候选引用对应视图；不是 224 个独立生物样本。全部保留 `needs_review`、`trainable=false`、`prediction_is_gold=false`，未物化 MIC 训练答案、未调用 LLM、未启动微调。

另一个实际发现是标签异质性：3480 个结构—物种输入有多次 MIC 记录；其中 2713 个有多条精确测量，1272 个的精确值跨度超过 2 倍、894 个超过 4 倍。这反映实验株和条件差异等来源异质性，不能归结为模型误差。固定物种参考不能区分这些记录的实验状态；正式构造 MIC 监督目标时须保留差异及不确定性，不能任取一条作为普适真值。当前原测量分别保留，没有平均化或删去不同值。

上述产物在 `evaluation/{compound,scaffold,study,scaffold_study}/` 与 `supervision/scaffold_review_v1/`。版本绑定、输入白名单、组间隔离与队列核验的公开聚合记录见 [species_expansion_verification_20261007.json](../reports/llm_platform/species_expansion_verification_20261007.json)。这些检查尚未证明 LLM 药效准确率或组学收益。

## 首版建设记录与组学来源限制

本机数据整理后，复用 AB 历史 canonical 标签 11650 条，不复制原件；官方 ChEMBL 每个补充物种先取 300 条活动，经原始活动、assay、文献、结构四级关联后准入 800 条。总计 **12450 条 MIC、6199 个结构身份**。这是有限首批覆盖，不能称为完整数据库或已经完成药效微调。

| 物种 | MIC 记录 | 结构身份 | 已选参考 |
| --- | ---: | ---: | --- |
| A. baumannii | 11650 | 5774 | 基因组注释、历史未给药 RNA、实测蛋白组（对照身份推定） |
| E. coli | 232 | 176 | 基因组注释、未给药 RNA、实测蛋白组 |
| K. pneumoniae | 276 | 262 | 染色体基因组注释、未给药 RNA、实测蛋白组 |
| P. aeruginosa | 292 | 229 | 基因组注释、未给药 RNA、实测蛋白组 |

新活动的 100 条排除原因包括组合/增效或聚合 MIC（91）、assay 描述与物种字段矛盾（7）、缺原生关系符（1）、未核定质量单位（1）。旧 EC 90099 条简化表缺 activity/assay/document ID，保留原件并整源隔离，不用结构或数值相似性猜回实验来源。800 条新标签共 3200 个四级来源定位已逐条核验，原生缓存可禁网重建。

已选 **12 个原生参考、4 个物种集合**，四物种均可选择三种单模态及七种组合。来源条件与样本分别记录，不声明跨模态样本配对。蛋白组 AB/EC/PA/KP 分别有 1955/2019/1591/1813 个作者原生观察，其中有效数值为 1136/2019/1590/1442。

参考数据的原生 ID、单位和尺度保留：EC RNA 为作者 QC 对数表达，KP RNA 为作者原始 read count，不能直接跨样本定量比较；KP 蛋白列保留作者 LFQ 原值，尺度未直接明确的部分保持未知。AB MaxQuant 未定量零值转为 null；PA/KP 缺失丰度也为 null，不作缺失补零。参考基因注释存在性不等于已测全基因组变异或阴性基因调用；KP 当前参考仅包含染色体，不能假定包含全部质粒。

AB 蛋白来自 [作者 PXD028502 研究](https://journals.plos.org/plospathogens/article?id=10.1371/journal.ppat.1010308) 的 `LFQ intensity A1`。A1 与原始质谱文件的映射已核验；其未给药对照身份由四组设计、作者命名和差异表的数值一致性推定，缺少逐文件处理身份字典。精确采样培养基、总培养时间与生长期保持未知。该限制写入 source receipt、原生 manifest 的 value_semantics/citation 并暴露给模型和报告；没有将作者局部蛋白 ID 猜接为 ABUW 基因。只取约 1.04 MB ZIP 范围片段，核验成员 CRC/长度，未下载或声称校验完整 530 MB 压缩包。

数据库和覆盖位于 `local/species_reference_20261007/database/v1/`，源核验与参考选择分别在同级 `mic/`、`assets/`。实际参考株、样本、条件、来源及功能桥接计数见 `assets/selected_references.json` 和 `reference_validation.json`。原始数据保持单份，集合 manifest 只引用已有 native profile。

## 补库前的真实组学盘点

| 数据 | 已接入状态 | 能说明什么 |
| --- | --- | --- |
| AB5075-AZI000 | T7 原有历史 RNA 均值 profile | 历史未暴露表达背景，不能拆成多个独立测量 |
| AB5075-Abaum_0017、AB5075-Abaum_0023 | 53 上两列原始 QC RNA profile，每列 3895 个原生特征 | 2 个 run、1 个 BioSample，独立生物重复未证实 |
| 19 个 E. coli FASTA/GFF | T7 已生成 genome-only 参考 profile | 100758 条基因/伪基因注释；培养条件、RNA、实测蛋白与 MIC 配对未知 |
| PA 5572×411 本地矩阵 | 未准入 | 数字行索引需要原始基因桥接与元数据核验 |
| 实测蛋白组 | 已核验可加载 profile 为 0 | 参考蛋白序列/翻译 ID 不能代替蛋白丰度 |

53 工作目录：`/home/zkyd/data1/mzy/PRAXIS-virtualcell-agent-runtime-20261007`。原始 AB 作者矩阵仍在原有 `Ab-Worldmodel/abaumannii-world-model/data/raw/abaumprecise/repository/data`，没有重新下载或复制；新 profile 是必要的逐列观测表与来源收据。服务器已有项目未被替换。

该目录的 `.venv` 复用已有 A100 conda 环境的公共包，在隔离环境中补 RDKit 与配置依赖，不修改共享环境。实际 RNA 工具观测与离线模型协议 fixture 已通过规划/分析/审查；本轮没有在服务器部署外部 API 凭据或模型权重。从该目录运行 `.venv/bin/python -m praxis_virtualcell.cli --data-root data/organisms profiles` 可查看接入数据。

基因组参考使用 `condition.role=sequenced_reference`，只允许 genome-only；未知培养/暴露条件保持 null。不能把这种参考称为未暴露实测基线。

## 实验监督与机制证据

旧 AB MIC 表的 12349 条来源测量重新关联原始 assay/document 后，11650 条准入为历史实验监督；699 条隔离，其中 512 条涉及增效、组合或聚合上下文，187 条 assay-document 关联待核。

AB5075 单药历史 MIC 为 **52 条：32 条精确值、20 条右删失值**，来自 8 个 assay、4 个研究。原先找出的 250 条带 AB5075 标签的记录有许多是另一种抗生素在增效剂条件下的 MIC，不能作为候选自身 MIC。

同 isolate、同 condition 的组学与 MIC 严格配对数为 **0**。`same_strain_reference` 仅表示菌株参考关系，不能升级为实验配对。EC 原始 90099 条化合物记录缺实验/菌株身份，NCBI 两表只有 SIR 且数值测量为空，未转成 MIC。

`ExperimentRecord` 保留终点种类、单位、不等式、区间、原始测量、来源和配对证据；`analysis_input()` 用白名单隔离标签。推理不读 MIC、assay 描述或监督答案。

机制库目前只有 **7 条 AB5075 原生基因功能参考注释，0 条 pathway，0 条已核验分子–蛋白实验交互**。ChEMBL 整菌 assay 和未核验摘要关系不作为蛋白结合证据。实际样本模式的机制工具固定查询已选 profile 的 taxon/strain；物种参考模式按固定 taxon 查询，记录仍保留自己的来源株与条件。候选交互查询只能用提交分子的精确结构。空结果代表证据缺口。机制引用不能代替逐模态读取与引用。

## 早期 AB 单物种冻结与审核队列

本地输出位于 Git 忽略的 `local/data_readiness_20261007/`。`labels/experimental_labels.jsonl` 是单份 canonical 标签；冻结集的 `answers.index.jsonl` 只引用记录 ID，不复制测量答案。`inputs.jsonl` 没有终点，候选 ID 为不携带实验信息的 case 编号。五种分组分别评估不同泛化问题，不能混成一个准确率。

| 分组 | 准入记录 | 分组数 | 训练/验证/测试记录 |
| --- | ---: | ---: | --- |
| compound | 11650 | 5746 | 8787 / 821 / 2042 |
| scaffold | 11650 | 1982 | 7738 / 1381 / 2531 |
| study | 11650 | 466 | 7299 / 1516 / 2835 |
| strain | 9521 | 817 | 7410 / 604 / 1507 |
| joint | 9521 | 74 | 9033 / 149 / 339 |

compound 分组只在划分时去 counterion/归一化电荷，测量中的 tested form 保持原样；scaffold 把无环分子放在同组；strain 使用物种与株名命名空间，不把不同研究里同名的“1”当同一株。joint 对共享分子、菌株、研究作传递聚类，最大组为 8030 条，因此划分严重不均衡。菌株名称分组不等于基因组谱系聚类。

`evaluation/paired-omics` 明确为 `insufficient_groups`、0 条记录。历史 MIC 的冻结不能证明组学提高了准确率。

评分程序在推理结束后单独读取答案。精确 MIC 使用 log2 误差与一个二倍稀释步长命中率；删失值使用原始开闭区间一致性，不将 `>64` 当作 `64`。必须同时报告数值回答覆盖率，避免只统计肯回答的容易案例。

`seeds/` 是真实工具数据生成的公开观察审核队列：标记 `source_grounded_template`、`needs_review`、`trainable=false`、`prediction_is_gold=false`。它用于审核后训练工具使用、单位/来源保留和不确定性表达，不能作为药效真值或独立生物样本计数。模型真实轨迹通过现有 `export-sft` 单独导出，也默认待审核。

实际生成了 T7 20 条、53 上 2 条工具监督候选，没有为达到 80 条而复制样例。另外，完整 DeepSeek 实际运行通过后导出 3 条公开角色轨迹；这些轨迹仍待审核，不因为 LLM 审查接受而自动变成人工金标。

## 复现入口

```bash
# 盘点本地资产；不下载数据
.venv/bin/python -m praxis_virtualcell.datasets.inventory \
  --repo-root . --output-dir local/data_readiness_new/inventory

# 历史实验标签与隔离队列
.venv/bin/praxis-vc curate-labels --output local/data_readiness_new/labels

# 先冻结，再生成训练监督；同一实验不能跨模态落入不同 split
.venv/bin/praxis-vc freeze-evaluation \
  --labels local/data_readiness_new/labels/experimental_labels.jsonl \
  --grouping compound --output local/data_readiness_new/evaluation/compound

# 根据实际 profile 生成待审核工具观察；不会生成 MIC 答案
.venv/bin/praxis-vc prepare-seeds --output local/data_readiness_new/seeds

# 预测完成后才读取私有答案。predictions.jsonl 使用 case_id 或 candidate.id
.venv/bin/praxis-vc score-evaluation \
  --manifest local/data_readiness_new/evaluation/compound/manifest.json \
  --predictions local/predictions.jsonl --output local/evaluation_score.json
```

冻结输出目录不可覆盖；修改 canonical 标签后，旧冻结集评分会拒绝，需要建立新的版本。

## 接着做什么

先审核当前 32 个候选和 28 种观察模板，确定多次 MIC 测量的监督目标及不确定性表达，再从主 scaffold 训练集扩展正式监督。验证/测试集保持冻结，避免根据测试结果筛选训练样例。补充实验配对时，需要同一分子测试形式、菌株/isolate、原生样本身份与处理前条件依据；蛋白组需要实测丰度及原生 protein ID 桥接。药物处理后的 RNA/蛋白响应不能混入处理前预测输入。

审核后的工具/观察数据可以先训练架构遵循能力。物种参考模式允许用历史药物—物种 MIC 监督，在相同冻结测试集上比较物种名称与加入各参考模态后的收益；不由此声称能够解释同物种内的菌株状态差异。实际样本模式要评价个体组学贡献，仍需独立配对队列。两个任务不能混成同一个准确率。

53 已核验 8×A100-SXM4-40GB。硬件充足不改变数据准入要求；本轮没有启动正式 LoRA，也没有用老师模型生成的 MIC 补实验标签。
