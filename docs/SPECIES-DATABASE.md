# 物种参考组学与 MIC 映射库

当前数据建设使用物种级参考模式：药物实验 MIC 对应物种，每个物种的基因组、转录组、蛋白组各指定一个有来源的参考。无需实验菌株与参考菌株相同，也无需三种组学来自同一培养物。实际菌株样本模式继续使用原有严格配对规则。

“一一对应”指每物种每模态只有一个选定参考；药物与物种之间允许多条实验测量。同一分子、同一物种在不同实验菌株和条件下可以有不同 MIC，原记录分别保留，不用平均值替代，也不强行匹配参考株。

## 存储与身份

- 原始组学、ChEMBL 响应和实验标签各保留单份，已有数据通过原路径引用。组学 profile 只派生运行时所需特征；集合 manifest 只保存源 profile 指针。
- `praxis_species_reference.sqlite3` 使用外键连接 species、reference_modalities、compounds、experiments 和 label_files。每个物种—模态是唯一键；参考菌株和实验菌株分开存放。
- MIC 数值、不等号、单位、实验条件保留在 canonical `ExperimentRecord` JSONL 中。SQLite 通过文件、字节位置和记录 ID 定位答案，不再复制一份 MIC 值。
- native ChEMBL activity ID 跨导出版本去重；结构、物种、实验株、条件、assay/document 或测量冲突时拒绝静默去重。没有原生活动身份的 EC 历史简化表不能靠“数值一样”恢复唯一来源。
- `export-species-inputs` 只读候选结构、物种、参考 profile ID。输出不含 MIC、实验株、assay 描述、原始 activity ID、监督来源或审核答案；case ID 不携带实验终点信息。

## 参考集合

```json
{
  "schema_version": "praxis.species-reference.v1",
  "profile_id": "AB-SPECIES-REFERENCE",
  "species": {
    "scientific_name": "Acinetobacter baumannii",
    "taxonomy_id": "NCBITaxon:470"
  },
  "reference_profiles": {
    "genome": "source-genome-profile",
    "transcriptome": "source-RNA-profile",
    "proteome": "source-protein-profile"
  },
  "input_role": "species_reference",
  "relation": "species_level_reference",
  "prediction_scope": "species_reference",
  "selection_reasons": {
    "genome": "核验后的选择理由"
  }
}
```

`reference_profiles` 可以仅有一部分模态。每个指针须指向相同物种的 native v1/v2 profile；引用不能嵌套，也不能跨物种。组合视图不声明统一实验株、统一条件或样本配对，所选模态分别返回自己的来源身份、条件、单位、尺度和原生 source IDs。

基因组参考可以是已核验的组装注释或原生参考 CDS 注释；后者必须明确是注释存在性，不能声称具有该分离株的完整基因组变异。参考蛋白序列和功能注释不构成实测蛋白组。RNA/蛋白参考优先未给药基线，未知条件保留 null。

## 本地生成与使用

本次工作文件集中在 Git 忽略的 `local/species_reference_20261007/`。参考准备器输出 `assets/selected_references.json`；MIC 整理器输出 `mic/summary.json`，其中的 `label_files` 指向实际 canonical 实验文件，包括复用的原有 AB 标签。首次数据库放在 `database/v1/`；新版本使用新目录，避免覆盖旧评估引用。

```bash
# 先盘点和复用已存原生元数据，再补取各物种有限的官方 MIC 页
.venv/bin/praxis-vc acquire-species-mic \
  --archive-root '/Volumes/T7/PRAXIS-virtualcell-old/Ab-虚拟细胞世界模型' \
  --reuse-labels local/data_readiness_20261007/labels/experimental_labels.jsonl \
  --per-species-limit 300 \
  --output local/species_reference_20261007/mic

# labels 参数传入 mic/summary.json 中的实际 label_files 路径
.venv/bin/praxis-vc build-species-db \
  --references local/species_reference_20261007/assets/selected_references.json \
  --labels local/data_readiness_20261007/labels/experimental_labels.jsonl \
    local/species_reference_20261007/mic/taxon_562.experiments.jsonl \
    local/species_reference_20261007/mic/taxon_573.experiments.jsonl \
    local/species_reference_20261007/mic/taxon_287.experiments.jsonl \
  --output local/species_reference_20261007/database/v1

.venv/bin/praxis-vc species-db \
  --database local/species_reference_20261007/database/v1/praxis_species_reference.sqlite3

.venv/bin/praxis-vc export-species-inputs \
  --database local/species_reference_20261007/database/v1/praxis_species_reference.sqlite3 \
  --output local/species_reference_20261007/database/v1/inference_inputs.jsonl

.venv/bin/praxis-vc inspect --profile AB-SPECIES-REFERENCE
.venv/bin/praxis-vc inspect --profile EC-SPECIES-REFERENCE --modalities proteome
.venv/bin/praxis-vc inspect --profile AB-SPECIES-REFERENCE --modalities genome transcriptome
```

下载器保存官方响应、完整 URL、时间、页信息和内容校验收据，优先使用本机原生 ID 对应的元数据缓存。当前是每物种有限首批，不是全库覆盖。已有缓存可以离线重建；取新的在线版本应使用新的输出目录，保留旧版本的来源与评估引用。

继续扩容可指定 `--per-species-limit 5000 --page-size 1000 --reuse-cache local/species_reference_20261007/mic/nativecache`，并把旧 `summary.json` 中的全部标签路径传给 `--reuse-labels`。累计上限计原生活动，准入数由来源规则决定。旧缓存和 canonical 标签只读复用；新目录只保存新增响应和新增标签。分页必须保持物种过滤、连续 offset、来源版本和活动身份一致，不能把有限页数称为完整导出。

后续 `analyze --profile AB-SPECIES-REFERENCE`、Web 和 MCP 使用同一加载入口。只有实际可用的模态可选；缺少蛋白组时不会生成空的“完整组学”参考。

## 监督与评估含义

实验标签用于训练监督和独立评分，推理不查 MIC。LLM 返回物种参考背景下的活性估计、证据与机制假设；参考株的基因和丰度不能推广为该物种所有菌株的当前状态。

相同分子—物种的多个 MIC 是实验异质性，不能逐行随机分割到训练与测试。先按化学骨架和研究来源冻结评估，再为相同划分生成不同模态视图。比较“药物＋物种”与各参考模态及组合，并使用错误物种参考对照，能够检验额外信息的预测收益；固定参考不能证明同物种内菌株个体差异或组学因果机制。

MIC、生长抑制、MBC、蛋白结合和杀菌曲线仍是独立终点。MIC 标签不能直接提供作用靶点真值，老师 LLM 的解释也不能自动作为实验金标。

## 冻结物种参考评估与监督队列

物种参考数据库使用专用冻结入口。分组在全部物种上统一进行：`compound` 协议禁止同一归一化结构跨集合，`scaffold` 协议禁止同一骨架跨集合，换一个物种也不能绕过分组。`compound`、`scaffold`、`study` 分别回答新分子、新骨架、新研究的问题；`scaffold_study` 将共享骨架或研究传递连接，检查同时隔离这两者时的可用数据。前三种协议不能宣称同时隔离所有来源。空骨架统一视为一组，多个 MIC 测量分别保留。

```bash
.venv/bin/praxis-vc freeze-species-evaluation \
  --database local/species_reference_expansion_20261007/database/v2/praxis_species_reference.sqlite3 \
  --grouping scaffold \
  --output local/species_reference_expansion_20261007/evaluation/scaffold

.venv/bin/praxis-vc prepare-species-supervision \
  --manifest local/species_reference_expansion_20261007/evaluation/scaffold/manifest.json \
  --limit-per-species 8 \
  --output local/species_reference_expansion_20261007/supervision/scaffold_review_v1

# 预测结果保存后，评分才读取单份 canonical 标签
.venv/bin/praxis-vc score-species-evaluation \
  --manifest local/species_reference_expansion_20261007/evaluation/scaffold/manifest.json \
  --predictions local/predictions.jsonl --split test \
  --output local/species_reference_expansion_20261007/evaluation/scaffold/score.json
```

冻结目录包含无终点的 `inputs.jsonl`、私有位置索引 `answers.index.jsonl`、排除记录及 manifest。manifest 绑定数据库、原标签、原生参考 manifest/特征和集合指针的版本；后续修改任一来源会阻止该版本的监督准备与评分。比例按独立组分配，各物种的行数、分子数和组数分别报告；巨型连通组、缺席物种和不足三个分组的情况不会隐藏。

评分同时报告总体、各物种和宏平均。宏平均对有对应分母的物种等权，并列出实际参与物种数；错误率要与数值回答覆盖率一起阅读。相同分子—物种的多条实验记录只增加观测次数，不增加独立分子数。

每种协议对应自己的训练、验证和测试集合。一个实验在不同协议下可能得到不同 split，因此不能合并不同协议的训练队列，也不能把按一种协议训练的权重在另一种协议上的结果称为独立测试。主训练与组学消融必须始终绑定同一份冻结 manifest；其余协议先用于数据结构诊断，若正式评估则分别训练。

监督准备只选择被冻结为 `train` 的候选，按物种与结构去重后保留这些结构的全部训练记录位置。`observations.jsonl` 每个物种—模态组合只保存一次真实工具观察，`queue.jsonl` 引用这些视图和私有答案位置。它们是待审核模板，包含真实来源、单位、缺失值及身份不确定性，不是模型轨迹或人工金标。正式训练前需要审核并物化训练目标；不能把这批工具格式示例当作已完成的药效微调数据。
