---
case_id: cryo-008-af-cryoem-hybrid
schema_version: 1
sample_type: any
target_pdb: 8GFV
target_emdb: EMD-40000
molecular_weight_kda: 300
symmetry_group: C1
resolution_target: "3-4"
resolution_achieved_a: 3.5
detector_type: K3
detergent_or_lipid: none
method_choice: [alphafold3, esmfold, phenix_dock_in_map, chimerax_flexfit, isolde, colabfold]
tools: [AlphaFold3, ESMFold, ColabFold, Phenix 1.21, ChimeraX 1.7, ISOLDE]
status: validated
provenance:
  source_type: literature
  doi: "10.1038/s41592-023-02087-4"
  citation: "Terwilliger TC, et al. AlphaFold predictions are valuable hypotheses and accelerate but do not replace experimental structure determination. Nat Methods 21, 110-116 (2024)"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: ["AF3 + cryoEM hybrid is methodology pattern; PDB ID exemplar (8GFV is a separate B2AR-Gs cryoEM structure used as illustration)"]
tags: [AF_hybrid, alphafold3, esmfold, dock_in_map, flexfit, ISOLDE, model_building_acceleration, hybrid_confidence]
---

# AF + cryoEM hybrid：用 AF prediction 加速 model building

## Background
2022-2024 后 standard：(1) 拿到 cryoEM map → (2) AF 预测 receptor + partner 结构 → (3) flexfit AF model 进 map → (4) refine。**比 ab initio model building 快 10×**，特别在 medium res (3-4 Å) 时。AF model + map combined 给 best result。

## What I actually did
1. **Map collect** to ~3.5 Å
2. **AF prediction**：所有 chains AF3 / ColabFold prediction with high pLDDT
3. **Initial dock**：Phenix dock_in_map 把 AF model 放入 map best fit
4. **Flexfit**：ChimeraX `fitmap` + ISOLDE molecular dynamics flexible fit
5. **Compare**：AF prediction 与 cryoEM map 一致区 keep；不一致区（map 显示不同 conformation）需 manual remodel
6. **Refine**：Phenix real_space_refine + Coot fix
7. **Validate**：MolProbity + Q-score + EMRinger
8. **Output**：cryoEM-restrained AF model + per-residue confidence comparison

## ★ 排除/不做的事
- **Pure AF model 当 final**：AF 不知 cryoEM-specific conformation；需 fit 进 map
- **Pure ab initio build**：浪费 AF 提供的 secondary structure 信息
- **AF low-pLDDT region 强 fit**：map 看不清 + AF 不准 → 双重不可信，标 disordered
- **不比对 AF vs map difference**：差异是有意义的 biology 不是噪声
- **AF model 偏离 map > 5 Å region 不 remodel**：保留 AF prediction 但说"map shows different state"
- **不报 hybrid confidence**：用户需知哪部分 from AF, 哪部分 from map

## ★ 失败模式
- **AF prediction 错（rare but happens）**：cofactor-dependent fold / new fold 不在 AF 训练
- **Map 与 AF 都显示 wrong conformation**：apo AF + apo map → 实际 holo state 缺失
- **Multi-conformer map averaged**：map 本身是 ensemble average，single AF model 难 fit
- **Chain assignment ambiguity**：multimer cryoEM map 中哪条链是哪个 sequence 不清
- **Modified residue / glycan / ligand 在 AF model 里没有**：map 显示 density 但 AF model 缺
- **AF version drift**：AF2 vs AF3 prediction 不同，model build 不稳定

## Lessons → seeds for rules
1. **AF + cryoEM hybrid 是 default**：不是替代任一
2. **Per-residue AF pLDDT 与 map confidence 双源标注**
3. **AF vs map difference 是生物学**（如 conformational state difference）不是 error
4. **Cofactor / glycan / ligand 单独处理**：AF 不含
5. **多 AF prediction (AF3 + ESMFold) cross-check**
6. **ISOLDE flexfit > rigid fit** for medium res maps
