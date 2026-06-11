---
case_id: immuno-NNN-{shorthand}
schema_version: 1
task: mhc_class_i_epitope_prediction | mhc_class_ii_epitope_prediction | tumor_neoantigen_identification | tcr_repertoire_analysis | bcr_repertoire_lineage_analysis | mrna_vaccine_sequence_design | hla_typing_from_rnaseq | car_target_selection_safety | allergenicity_assessment | tcr_pmhc_complex_modeling
antigen_class: viral | bacterial | tumor_neoantigen | self | plant_protein | biologic | n/a
hla_class: HLA_I | HLA_II | allele_specific | population_coverage | n/a
hla_alleles: []                          # 4-digit format e.g. ["HLA-A*02:01"]; [] for non-HLA tasks
peptide_length_bin: 8 | 9 | 10 | 11 | 13-15 | 15-18 | 18-25 | n/a
disease_indication: infection_* | cancer_* | autoimmune_* | allergy_* | gmo_safety | n/a
target_protein_uniprot: []               # e.g. ["P0DTC2"]; [] when no specific protein
tools: [NetMHCpan-4.1, MHCflurry-2, ...]
tool_versions:                           # optional but recommended for QA layer 6
  NetMHCpan: "4.1"
  MHCflurry: "2.0"
key_paper_doi: 10.xxxx/xxxxx             # CrossRef-verified
status: validated | proposed | failed | partial | preregistered
source: praxis_seed | inhouse | literature
extracted_at: YYYY-MM-DD
tags: [...]
unverified_details: []                   # any frontmatter field not directly transcribed from paper
---

# {Title}

## Background
- 起点信息（病原体/疾病/抗原蛋白）:
- 目标:
- 应用场景:

## What I actually did
1. ...
2. ...

## ★ 排除/不做的事
（必填）哪些 epitope/clone/target 不该入选? 给生物学理由:
- self cross-reactive 肽:
- non-presented 肽（HLA LOH / B2M downregulation）:
- 不 immunogenic 但 high-binding 肽:
- subclonal mutation:
- non-expressed allele:
- (即使写"未报道"也要写)

## ★ 失败模式
（必填）哪些预测/设计失败了? 失败原因? 即使是"未报道"也要明确:
- HLA LOH / antigen escape:
- TCR repertoire constraint:
- pre-existing immunity / central tolerance:
- class II register ambiguity:
- mRNA innate immunity (TLR3/7/8) / m1Ψ unmodified:
- ...

## ★ 方法选择决策链
（必填）为什么选这条工具链?
- 为什么 NetMHCpan vs MHCflurry vs BigMHC consensus?
- OptiType vs arcasHLA vs HLA-LA?
- TCRdock vs AF-Multimer?
- 关键阈值（EL_rank / IC50 / CCF / VAF）?

## ★ Validation
（必填）in silico 通过 → in vitro / 临床实测的转化:
- IEDB known epitope recall:
- experimental binding (tetramer / SPR / BLI):
- functional T cell assay (IFN-γ ELISpot / ICS):
- 主要失败来源:

## Lessons → seeds for rules
1. ...

## 数据指针
- output: runs/{task_id}/outputs/...
- metrics: runs/{task_id}/intermediates/metrics.json
- raw_wetlab_data: ...
