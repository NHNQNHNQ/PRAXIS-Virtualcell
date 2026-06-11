---
case_id: NEG-SYMMETRY-NO-TIED-MPNN
neg_pattern: symmetric_design_proteinmpnn_without_tied_positions
design_task: symmetric_oligomer_de_novo
target_pdb: nan
target_uniprot: nan
fold_class: any
tools: [ProteinMPNN, RFdiffusion]
key_paper_doi: 10.1038/s41586-023-06415-8
key_metrics:
  sequence_breaks_symmetry_when_untied: "100% — chain A and B get different sequences"
  in_vitro_oligomer_state_match_untied: "<10%"
  in_vitro_match_with_tied_mpnn: "60-70% (cases 009, 019, 031, 033)"
status: failed
schema_version: 1
source: praxis_neg_pattern
extracted_at: 2026-05-04
tags: [NEG, anti-rule, symmetric, ProteinMPNN, tied-positions, oligomer]
---

# NEG: symmetric design 用 ProteinMPNN 但不指定 tied_positions_jsonl

## ★ 失败模式
- 对称 backbone (C3, C4, D2, I3) 经过 ProteinMPNN without `tied_positions_jsonl` → 同 backbone 上不同 chain 给不同 sequence
- 结果不再是 homo-oligomer, 而是 hetero (不可能在 vitro 重组)
- SEC 表现混乱, native MS 不一致

## ★ 排除/禁止
- 不允许 symmetric 任务的 MPNN 调用没有 `--tied_positions_jsonl`
- skill `symmetric_design_pipeline` 必须 enforce tied positions
- 报告必须证明 sequence 在所有 symmetry-related copy 上 identical

## ★ 方法选择决策链（反向）
- 正确（rule 08）: RFdiff symmetric mode + MPNN tied_positions + AF-Multimer 多 chain 验证 + cryo-EM oligomer state
- 错误: RFdiff symmetric backbone + MPNN 普通模式 = sequence 破对称

## Anti-pattern triggered
违反 rule 08 (symmetry enforced throughout pipeline)

## Evidence cases
- protein-009 (Watson 2023 RFdiff symmetric; tied MPNN required)
- protein-019 (Wicky 2022 hallucination symmetric; MCMC enforce throughout)
- protein-031 (King 2014 two-component cages; symmetric design pipelines)
- protein-033 (Hsia 2016 icosahedron; tied MPNN for 60-subunit)
