---
case_id: {design_task}-{target_shorthand}-{year}
schema_version: 1
design_task: structure_prediction | structure_prediction_complex | complex_prediction | de_novo_binder | stabilization | mutation_effect_prediction | antibody_cdr_modeling | antibody_design | structure_search_homology | high_throughput_structure_prediction | symmetric_oligomer_de_novo | redesign | binder_validation_post_mortem
target_pdb: 1ABC                       # nullable for de novo cases
target_uniprot: P00000                 # nullable for de novo cases
fold_class: immunoglobulin | helical_bundle | beta_sheet | TIM_barrel | rossmann | ob_fold | mini_protein | helical_bundle_C3 | any | ...
length_range: 60-120                   # optional
tools: [RFdiffusion, ProteinMPNN, AlphaFold2]
tool_versions:                         # optional but recommended for QA layer 6
  RFdiffusion: "git:abcd1234"
  AlphaFold: "2.3.2"
key_paper_doi: 10.xxxx/xxxxx           # CrossRef-verified
key_metrics:
  pLDDT_mean: 0
  iPTM: 0
  pAE_interface: 0
  Rosetta_ddG: 0
  in_silico_success_rate: ""
status: validated | proposed | failed | partial | preregistered
source: praxis_seed | inhouse | literature
extracted_at: YYYY-MM-DD
tags: [...]
unverified_details: []                 # any frontmatter field not directly transcribed from paper
---

# {Title}

## Background
- 起点信息（基因/家族/结构基础）:
- 目标:
- 应用场景:

## What I actually did
1. ...
2. ...

## ★ 排除的位点/区域
（必填）哪些残基/区域不能动? 给生物学理由:
- 保守催化残基:
- 二硫键:
- 跨膜段:
- 糖基化位点:
- 表位关键残基:
- (即使写"未报道"也要写)

## ★ 失败模式
（必填）哪些预测/设计失败了? 失败原因? 即使是"未报道"也要明确:
- 低 pLDDT 区段:
- iPTM<0.6 复合物:
- 表达失败 / aggregation:
- in vitro fold 失败:
- specificity 漂移:
- ...

## ★ 方法选择决策链
（必填）为什么选这条工具链?
- 为什么 RFdiffusion 而非 Chroma:
- ProteinMPNN 温度选择:
- AF-Multimer vs AF3 vs Boltz-1:
- 关键阈值(pLDDT/iPTM/ddG):

## ★ In silico vs in vitro 差距
（必填）in silico 通过 → in vitro 实测的转化率:
- 表达成功率: 
- fold 正确率:
- 结合功能率:
- 高亲和(KD<100nM)率:
- 主要失败来源:

## Lessons → seeds for rules
1. ...

## 数据指针
- 结构: runs/{task_id}/structures/...
- metrics: runs/{task_id}/intermediates/metrics.json
- raw_wetlab_data: ...
