---
case_id: NEG-SINGLE-MODALITY-VALIDATION
neg_pattern: fold_only_design_validated_with_single_modality
design_task: hallucination_de_novo
target_pdb: nan
target_uniprot: nan
fold_class: any
tools: [CD, SEC, NMR, X-ray, cryo-EM]
key_paper_doi: 10.1038/s41586-021-04184-w
key_metrics:
  cd_only_false_pass_rate: "~30% (CD pattern correct but SEC multi-peak)"
  sec_only_false_pass_rate: "~25% (SEC monomer but NMR shows molten globule)"
  multi_modality_validated_correct_rate: "70-85%"
status: failed
schema_version: 1
source: praxis_neg_pattern
extracted_at: 2026-05-04
tags: [NEG, anti-rule, multi-modality, validation, CD, SEC, NMR, X-ray]
---

# NEG: fold-only / hallucination / cyclic / symmetric / enzyme 设计单 modality 验证

## ★ 失败模式
- CD-only: secondary structure 看起来 OK 但 SEC 上多聚 / aggregate (~30% 假阳)
- SEC-only: monomer state 但 NMR 显示 molten globule (~25% 假阳)
- 没 NMR/X-ray confirmation 不能 claim "fold-correct"
- symmetric assembly 必须 cryo-EM (single SEC 假阳率 30-40%, case 031, 033)

## ★ 排除/禁止
- 不允许 hallucination/cyclic/symmetric/enzyme 任务报告中 < 3 modality
- 不允许 "fold confirmed" 单 SEC 或 单 CD claim
- 必须列 validation_modalities 字段 + 每个 modality 的 protocol

## ★ 方法选择决策链（反向）
- 正确（rule 09）: CD + SEC + NMR/X-ray + native MS（symmetric extra: cryo-EM）
- 错误: SEC-only "fold confirmed"

## Anti-pattern triggered
违反 rule 09 (multi-modality validation)

## Evidence cases
- protein-013 (Bhardwaj 2016 cyclic peptide; NMR ensemble 必)
- protein-014 (Hosseinzadeh 2017 macrocycle; NMR + X-ray subset)
- protein-015 (Anishchenko 2021 hallucination; CD + SEC + NMR/X-ray)
- protein-022 (Ingraham 2023 Chroma; CD + SEC + SAXS + NMR/X-ray)
- protein-031 (King 2014 cages; SEC + 负染 EM + cryo-EM)
- protein-033 (Hsia 2016 icosahedron; X-ray + cryo-EM + native MS)
