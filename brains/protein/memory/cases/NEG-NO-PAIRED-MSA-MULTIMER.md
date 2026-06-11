---
case_id: NEG-NO-PAIRED-MSA-MULTIMER
neg_pattern: af_multimer_without_paired_msa
design_task: complex_prediction
target_pdb: 6M0J
target_uniprot: P0DTC2
fold_class: any
tools: [AlphaFold-Multimer]
key_paper_doi: 10.1038/s41586-024-07487-w
key_metrics:
  iPTM_artifact_inflation: "+0.1-0.3 false-high"
  interface_RMSD_drift_vs_crystal: ">5 Å"
status: failed
schema_version: 1
source: praxis_neg_pattern
extracted_at: 2026-05-04
tags: [NEG, anti-rule, AF-Multimer, paired-MSA, multimer, interface-error]
---

# NEG: AF-Multimer 跑 multimer 不带 paired MSA

## ★ 失败模式
- `--use_paired_msa=false` 或 一条 chain 来自不同 organism 的 unpaired MSA → interface 几何错位
- iPTM 可能 inflate 到 0.85+ 但 interface RMSD vs 真复合 > 5 Å (false high confidence)
- 所有 dimer/multimer 任务都需要从 UniProt OX 共组装的 paired MSA

## ★ 排除/禁止
- 不允许 AF-Multimer with `use_paired_msa=False`
- 不允许 unpaired MSA 推到 reporting agent
- 报告中必须显示 `paired_msa: true` + `paired_msa_size`

## ★ 方法选择决策链（反向）
- 正确: AF-Multimer 含 uniprot.fasta paired MSA pipeline (case 001, 007)
- 错误: 单 chain MSA + concat = "fake multimer"

## Anti-pattern triggered
违反 rule 02; 等价 anti-rule 4 (single-channel signal misuse)

## Evidence cases
- protein-001 (AF3 RBD-ACE2; paired MSA mandatory)
- protein-007 (AF-Multimer heterodimer; paired MSA = critical signal)
- protein-018 (Bennett 2023 DL filter, paired MSA + initial guess required)
