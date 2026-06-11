---
case_id: cryo-005-modelangelo-buildmodel
schema_version: 1
sample_type: any
target_pdb: 8OHB
target_emdb: EMD-16888
molecular_weight_kda: 500
symmetry_group: C1
resolution_target: "2-3"
resolution_achieved_a: 2.8
detector_type: K3
detergent_or_lipid: none
method_choice: [modelangelo, phenix_realspace, coot, isolde, buccaneer]
tools: [ModelAngelo 1.0, Phenix 1.21, Coot 0.9, ChimeraX 1.7, ISOLDE]
status: validated
provenance:
  source_type: literature
  doi: "10.1038/s41586-024-07215-4"
  citation: "Jamali K, et al. Automated model building and protein identification in cryo-EM maps. Nature 2024"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
tags: [model_building, modelangelo, phenix, validation, MolProbity, Q_score, EMRinger, Ramachandran, automated]
---

# ModelAngelo：cryoEM map 自动建模的 game-changer

## Background
2024 年 ModelAngelo 把 cryoEM model building 从 days-weeks（手工 + Phenix）提速到 hours。trained on PDB-EMDB pairs，输入 sharpened map + sequence → 输出 atomic model with confidence per residue。**不取代专业 model builder，但加速 80% workflow**。

## What I actually did
1. **Map prep**：DeepEMhancer / Phenix auto-sharpen post-processed map (final density)
2. **ModelAngelo 输入**：map (.mrc) + protein sequences (FASTA, multi-chain)
3. **Output**：mmCIF model + per-residue confidence + sequence assignment
4. **Confidence interpretation**：
   - High (> 0.8): trust as-is
   - Medium (0.5-0.8): manual review
   - Low (< 0.5): rebuild with Coot
5. **Phenix real_space_refine** + Coot manual fix on low-confidence region
6. **ISOLDE in ChimeraX** for problematic backbone tracing
7. **Validation**：MolProbity score / Ramachandran outlier / Q-score (Phenix) / EMRinger
8. **典型时间节省**：手工 build 100 残基 ~1-2 day → ModelAngelo + manual fix < 4h

## ★ 排除/不做的事
- **Sequence 不输 + 单跑 ModelAngelo**：unassigned poly-Ala model，下游用处有限
- **不做 manual review on low-confidence region**：blind trust ModelAngelo 出错
- **跳过 Phenix refinement**：ModelAngelo 输出 still need real-space refine
- **MolProbity 不查**：clash / Ramachandran outlier 必有，不查不知道
- **低 res region 强 build all-atom**：< 4 Å 区域 rebuild 用 polyalanine 或 backbone-only
- **不指定 chain 数**：multimer 时漏指定让模型 mix chain

## ★ 失败模式
- **Sequence assignment 错位**：相邻 chain 序列错配，需 manual fix
- **Low local resolution 区段乱 build**：ModelAngelo 给 model 但 confidence 低，建 vs 不建是 judgement
- **RNA/DNA 不支持（早期版本）**：纯 protein-trained，nucleic acid 区缺失；用 RNAComposer / DRRAFTER
- **Ligand 不识别**：non-standard residue / cofactor 不 build
- **Glycosylation 缺失**：N-glycan 在 map 中可见但 ModelAngelo skip
- **Side chain 在 backbone-OK region 仍 wrong rotamer**：需 Coot manual fix

## Lessons → seeds for rules
1. **ModelAngelo 是 first pass**，不是 final
2. **Sequence input 必给**：assignment + confidence 才有意义
3. **Per-residue confidence label** 决定 manual review 范围
4. **Phenix real_space_refine 后必跑**
5. **MolProbity / EMRinger / Q-score 必查**
6. **RNA/DNA / ligand / glycan 走专用工具**
7. **Low local res (< 4 Å) → polyalanine** or skip
