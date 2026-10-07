# 当前数据接入与监督准备

2026-10-07。当前阶段完成智能体接口、真实观测接入和独立评估准备；正式药效微调还需要严格配对的数据与审核后的监督答案。

## 真实组学

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

机制库目前只有 **7 条 AB5075 原生基因功能参考注释，0 条 pathway，0 条已核验分子–蛋白实验交互**。ChEMBL 整菌 assay 和未核验摘要关系不作为蛋白结合证据。智能体工具固定查询已选 profile 的 taxon/strain；候选交互查询只能用提交分子的精确结构。空结果代表证据缺口。机制引用不能代替逐模态读取与引用。

## 冻结评估与审核队列

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

先完成真实智能体调用与来源核验，再审核流程监督。补充实验配对时，需要同一分子测试形式、菌株/isolate、原生样本身份与处理前条件依据；蛋白组需要实测丰度及原生 protein ID 桥接。药物处理后的 RNA/蛋白响应不能混入处理前预测输入。

审核后的工具/观察数据可以先训练架构遵循能力。要声称“组学改善药效预测”，则必须补齐独立配对队列，用相同分组比较无组学、各单模态及真正配对的组合，并在相同冻结测试集上比较基础 LLM 与微调模型。现有 52 条 AB5075 历史 MIC 不足以支持这个结论。

53 已核验 8×A100-SXM4-40GB。硬件充足不改变数据准入要求；本轮没有启动正式 LoRA，也没有用老师模型生成的 MIC 补实验标签。
