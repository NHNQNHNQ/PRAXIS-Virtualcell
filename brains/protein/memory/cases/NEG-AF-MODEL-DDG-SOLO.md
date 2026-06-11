---
case_id: NEG-AF-MODEL-DDG-SOLO
neg_pattern: alphafold_predicted_structure_plus_pyrosetta_ddg_alone
design_task: stabilization
target_pdb: nan
target_uniprot: nan
fold_class: any
tools: [AlphaFold2, PyRosetta]
key_paper_doi: 10.1016/j.molcel.2016.06.012
key_metrics:
  af_low_plddt_active_site_unflagged_rate: "frequent — AF default doesn't refuse low-conf regions"
  pyrosetta_ddg_alone_precision_top10: "30-50%"
  combined_with_msa_evolutionary_precision: "70-85%"
status: failed
schema_version: 1
source: praxis_neg_pattern
extracted_at: 2026-05-04
tags: [NEG, anti-rule, AF-model, PyRosetta, single-method, stabilization, evolutionary-missing]
---

# NEG: AF predicted structure + PyRosetta ΔΔG 单一信号给 mutation 排序

## ★ 失败模式
- AlphaFold predicted structure 在 active site 或 loop 区域 pLDDT < 70 时 sidechain rotamer 不稳
- PyRosetta cartesian_ddg 直接读 AF model → 在低 pLDDT 区给 noise + bias
- 缺 evolutionary track (MSA consensus) → 单方误判 stabilizing → 实测 destabilizing 30-50%
- "AF + PyRosetta top-10 → ship" = 高假阳率

## ★ 排除/禁止
- 不允许 single (AF model + 单一方法 ddG (例如 PyRosetta cartesian_ddg)) 作为 stability 推荐
- AF model 必须先 pLDDT check（active site / functional loop ≥ 70）
- PyRosetta 必须配 ≥ 2 method (Rosetta cartesian_ddg, EVmutation, EVE) (rule 06)

## ★ 方法选择决策链（反向）
- 正确: AF model pLDDT-aware → PyRosetta ∩ Rosetta_ddg ∩ MSA-consensus (PROSS / FireProt 双轨, case 023, 024)
- 错误: AF + PyRosetta top-N → ship lab

## Anti-pattern triggered
违反 rule 06 (multi-method ddG); 等价 anti-rule 4 (AF + ddG single-channel ship)

## Evidence cases
- protein-023 (PROSS Goldenzweig; MSA evolutionary + Rosetta 双轨, PyRosetta-only 不够)
- protein-024 (FireProt Bednar; PyRosetta + Rosetta 双共识)
- protein-027 (EVmutation; evolutionary 必须 加入)
