# 菌株参考与微调训练集

2026-10-07。预测平台与训练索引采用同一个菌株参考契约。同一菌株每模态选择一个原生来源，允许来源条件不同；不同菌株分别建档。原始 MIC、组学和文献只保留一份，SQLite、集合 manifest 和来源索引引用原件。训练目标是必要的派生文件。

## 平台中的具体菌株

默认 CLI/Web 输入是 `AB5075-STRAIN-REFERENCE`。页面的新预测选择列出菌株集合及原生菌株档案，旧物种集合保留历史读取兼容。机制查询固定具体菌株；模型不能改换物种、菌株或候选结构。当前机制库缺 genotype/研究限定 namespace 字段时，显式基因型或研究内菌株的相关查询返回身份缺口，不借用其他背景。

| 菌株集合 | 实际可选模态 |
| --- | --- |
| AB5075-STRAIN-REFERENCE | genome、transcriptome、proteome |
| EC-MG1655-STRAIN-REFERENCE | genome、transcriptome、proteome |
| PA-PAO1-STRAIN-REFERENCE | genome、transcriptome、proteome |
| KP-HS11286-STRAIN-REFERENCE | genome |
| KP-K26-STRAIN-REFERENCE | transcriptome |
| KP-NCTC418-STRAIN-REFERENCE | proteome |
| 另外 18 个 E. coli 菌株集合 | genome |

三模态档案支持七种非空组合。缺失模态不补零或借用其他菌株。基因组存在性和参考翻译注释不代表蛋白丰度。K26 RNA 使用 HS11286 参考坐标，但来源株仍是 K26，不能因此与 HS11286 基因组合并。AB 蛋白对照身份推定、KP LFQ 未知尺度等原有限制继续保留。

```bash
.venv/bin/praxis-vc inspect
.venv/bin/praxis-vc inspect --profile EC-MG1655-STRAIN-REFERENCE --modalities genome proteome
.venv/bin/praxis-vc inspect --profile KP-K26-STRAIN-REFERENCE --modalities transcriptome
.venv/bin/praxis-vc serve --port 8787
```

## 实际数据覆盖

复用 7 个 canonical MIC 文件，共 24,792 条测量。11,973 条有明确株名，包含 917 个带命名空间的身份；研究内的相同编号不跨论文合并，未知株也不合并成一个虚构菌株。917 不是已完成生物学去重的独立菌株数。

当前只有 52 条 AB5075 MIC 可以链接到同菌株参考组学，划分为 train=48、validation=3、test=1。平台的 24 个可加载参考档案不等于 24 个已经具备 MIC 联合监督的菌株。其他明确菌株的 MIC 保留为无组学辅助任务，未知菌株记录不进入菌株 SFT。

沿用已有全局 scaffold 冻结：15,553 / 3,021 / 6,218 条。新索引不重新分配 split，不声称同时实现新菌株或新研究泛化；同一研究仍可能跨集合。推理输入白名单只含 SMILES、菌株身份、已知实验条件、所选参考与模态；DOI、原 assay 描述、MIC 和私有答案定位不进入输入。

## MIC 组件与联合文献组件

`supervision/v1/mic_sft.jsonl` 已生成 **7,227 个条件化 MIC 组件**，保留 **7,774 次训练测量**，其中 48 个组件有实际 AB5075 组学工具观察，7,179 个为无组学辅助任务。条件包括培养基、补充物、温度、暴露时间、方法和接种量；未知保持 null，不套用常见培养流程。相同结构、菌株和可见条件的多次实验形成一个观察分布目标，其中 380 个组件包含重复测量，最大组有 10 次测量。不取平均或中位值；`>`、`<`、`>=`、`<=` 和区间的边界保持原义。

该目标是来源已核验的实验监督，尚不是校准后的预测分布。它采用 `praxis.conditional-MIC-distribution.v1`，与运行时的 `Assessment` 单值/null MIC 契约不同；后续训练需使用匹配的任务头或输出契约，并单独完成角色/完整报告监督。当前不能把这 7,227 条称为完整智能体轨迹。

有组学组件使用实际 `overview/search_features/query_features` 消息和 native source IDs。当前观察视图读取少量原生特征以验证工具协议，不能称为完整细胞状态分析。只对 assistant 公开回答/工具调用计算生成损失，user/tool 消息不计算损失；训练框架仍需落实这一 mask。

文献从官方 Europe PMC/PMC 接口获取，按 DOI 去重，仅选择明确菌株的 train case。CLI 默认仅取书目和正文，`--include-supplements` 才尝试有界补充文件下载，实际是否取得分别记录。原文缓存保留版本、哈希、许可、JATS 段落/表格定位；补充文件在一个压缩包内引用，不重复展开原件。每个候选必须进一步绑定论文化合物编号、数据库分子身份、菌株和具体实验。仅同 DOI、同段出现关键词不够。

联合编译器要求显式 `praxis.literature-reviews.v1` 审核文件；再次核验原文哈希、实际 JATS passage、逐字引用区间、ChEMBL compound_record 映射、MIC 结构/document 和组件文件的预先登记哈希。机制区分实验、遗传、作者假说、通用背景和未知，另保存实验类型，例如 `phenotypic_rescue`；表型补充实验不变成直接靶点结合。原文与 MIC 只在训练答案/私有来源中使用，不注册为候选推理工具。

联合文件采用 `praxis.strain-joint-component.v1`，也是 MIC 与文献机制注释的组件任务，并非完整 `Assessment` 或实验验证。程序和 Codex 原文复核不等于人工金标。MIC 目标来自实验，逐字引句来自原文，机制说明为代理来源复核的转述，三者的生成来源分别标记；联合记录保留 `model_generated_target: true` 和 `human_reviewed: false`。同一 case 的联合组件是 MIC 组件的扩展，不能在训练混合时重复计作独立实验。论文和派生解释保持本地研究用途，数据来源许可不替代论文自身许可。

首批实际选择 25 篇 train 文献，均已核定 PMID，23 篇有 PMCID；取得 4 篇开放全文、1,210 个原文定位及 73 个待审核候选。7 篇仅取到书目，另 14 篇 Europe PMC 返回 502/503，单次 PMC OAI 补取返回 400；这些是访问失败，不能解释为文献不存在。正文和化合物映射通过来源回读，两次禁网重建逐字一致。补充文件本次明确跳过。

已生成 **3 个联合组件**，均为现有 AB5075 训练 case 的扩展：论文 [10.1021/acsmedchemlett.6b00296](https://doi.org/10.1021/acsmedchemlett.6b00296) 的化合物5提供亚油酸补充的表型机制线索，化合物1保留作者拟议通路背景，化合物4a保留机制未明确。39 条官方 `compound_record` 映射核对论文编号和数据库身份；三条均不声明已证实的具体结合靶点。当前 canonical 数据没有化合物5在 AB5075 的无补充基线记录，其余同结构 MIC 属于其他明确菌株，不能改绑以拼出配对实验。

## 本地结构与复现入口

```text
local/strain_training_20261007/
  database/v1/                    # SQLite、菌株身份、frozen case 和原件指针
  supervision/v1/                 # MIC 组件、实际观察视图、私有来源、联合审核队列
  literature/                     # 官方缓存、文章/段落索引、编号映射与审核文件
  joint/v1/                       # 已完成源复核的联合组件
  runtime_verification.json       # 实际 API/特征引用核验
```

来源为历史 `local/species_reference_expansion_20261007/database/v2/` 与 `evaluation/scaffold/`。已生成目录拒绝覆盖；更新来源或审核文件时写新版本。原件不搬动、不复制。

```bash
.venv/bin/praxis-vc build-strain-dataset \
  --database local/species_reference_expansion_20261007/database/v2/praxis_species_reference.sqlite3 \
  --frozen-manifest local/species_reference_expansion_20261007/evaluation/scaffold/manifest.json \
  --output /path/to/new/strain-dataset

.venv/bin/praxis-vc prepare-strain-supervision \
  --dataset /path/to/new/strain-dataset/summary.json --output /path/to/new/mic-supervision

.venv/bin/praxis-vc acquire-literature \
  --cases /path/to/new/strain-dataset/cases.jsonl --limit 25 --output /path/to/new/literature
# 同样的 cases/limit 可用 --offline 禁网重建已取得的文献索引。

.venv/bin/praxis-vc prepare-joint-supervision \
  --supervision /path/to/new/mic-supervision --literature /path/to/new/literature \
  --reviews /path/to/source-reviewed.json --output /path/to/new/joint-supervision
```

这些数据命令不读取 API key，不创建模型客户端。机制审核示例及实际聚合验证见 [strain_training_verification_20261007.json](../reports/llm_platform/strain_training_verification_20261007.json)。本轮只准备数据与平台，不启动微调，也没有证明 MIC 准确率或组学增益。
