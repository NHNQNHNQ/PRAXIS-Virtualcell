---
case_id: {family}-{property}-{year}-{shorthand}
schema_version: 1
parent_enzyme:
  uniprot: P00000
  cazy_family: GH7              # GH/GT/PL/CE/AA + 数字
  ec: 3.2.1.176
  organism: Trichoderma reesei
  pdb: 1CEL                     # 可填 null
  sequence_md5: PLACEHOLDER     # 用于精确定位序列变更
substrate:
  primary_smiles: ""
  class: cellobiose
target_property: thermostability   # thermostability | substrate_specificity | activity | expression | ph_stability
status: validated                  # validated | failed | partial | preregistered | synthetic_starter
provenance:
  source_type: literature           # literature | inhouse | synthetic_starter
  doi: 10.xxxx/xxxxx
  extracted_at: YYYY-MM-DD
tags: [GH7, thermostability, ...]
---

## 1. 背景与目标
- parent 起始性质 (起始 Tm / kcat / Km / 选择性比 等):
- 目标提升:
- 应用场景 (为何需要):

## 2. 决策过程

### 候选位点策略
- 方法 (consensus / B-factor / PyRosetta scan / ML / docking):
- 候选数与覆盖度:

### 排除的位点 (★ 必填)
- 哪些位点考虑过被排除? 为什么?
- (即使写"未报道"也要写,强制思考)

### 计算工具与阈值
- 工具 + 阈值:
- 是否做 MD / QM-MM 验证:

## 3. 实验结果

### in silico 预测 vs 实测
| 突变 | 预测 | 实测 | 一致性 |
| --- | --- | --- | --- |
| WT  | -   | -   | -    |

### 失败案例 (★ 必填)
- 哪些预测正确但实验失败? 可能原因 (表达 / 可溶性 / 聚集 / 折叠) ?

## 4. 学习收获
- 成立的规则候选 (会被 distill 提升为 rule):
- 被推翻的假设:
- 下次类似问题应优先尝试:
- 应避免:

## 5. 计算原始数据指针
- pyrosetta_results:
- structures:
- md_trajectories:
- raw_wetlab_data:
