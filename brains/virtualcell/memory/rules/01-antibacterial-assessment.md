---
rule_id: 01-antibacterial-assessment
schema_version: 2
rule_type: omics_conditioned_llm_prediction
scope: antibacterial_candidate_assessment
applies_to:
  agent: virtualcell
confidence: implementation_contract
---

# 菌株组学条件下的 LLM 预测

检索词：抗菌 候选 分子 药物 活性 耐药 机制 靶点 依据 预测 MIC 组学 转录组 AB5075 Acinetobacter baumannii SMILES DeepSeek。

LLM 是本入口唯一的药效预测引擎。工程工具提供实际组学数据、明确样本条件、基因注释和确定性分子结构处理。旧 MIC、AMR、QSAR、扰动和世界模型不参与推理，实测 MIC 记录不作为输入或查表答案。

## 运行

`praxis-vc profiles` 列出本地输入包，`praxis-vc inspect --profile ID` 核对身份、尺度与来源。`praxis-vc analyze --profile ID --smiles SMILES` 运行预测，`praxis-vc batch --profile ID --input candidates.csv` 批量输入。Web 由 `praxis-vc serve` 提供。

每次分析必须加载明确 profile 并查询实际基因行，保存执行记录。未知 profile、无效结构、查询失败或无证据时保留失败/未支持状态。旧 `praxis-mdr` 不用于本任务。

## 数据与证据

- 区分物种、实验菌株、参考 assembly 和样本。参考蛋白翻译不等于实测蛋白组。
- `AB5075-AZI000` 是历史未给药条件均值，保留来源尺度；未知基因型、时间、温度、生长期保持未知。
- 新候选工具输入只使用允许的未给药参考，treated/delta 与 MIC 标签不进入结果。
- 未见注释表示未知，不自动认定基因缺失。缺失模态显式标记。
- 事实引用对应实际工具返回字段、数值与来源。表达和注释可支持假说，不能单独证明结合、直接靶点或因果关系。

## 输出

分别输出活性预测、MIC 估计或未知、靶点与机制假说、支持证据、反证与缺口。MIC 数值标记为未校准的 LLM 估计，模型 confidence 不是实验校准概率。MIC 表示生长抑制；杀伤率、MBC、时间杀菌曲线缺少相应依据时保持未知。
保留模型、候选结构、输入样本和工具轨迹；私有思考正文不进入用户报告或证据。
