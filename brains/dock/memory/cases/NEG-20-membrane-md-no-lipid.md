---
case_id: NEG-20-membrane-md-no-lipid
schema_version: 1
docking_type: ensemble_protein_ligand
target_pdb: anti-pattern reference (GPCR / GLUT / membrane protein)
target_class: GPCR
ligand_type: small_mol_drug_like
system_specifics:
  ligand_drug_likeness: drug_like
tools: [GROMACS, AutoDock Vina 1.2.5]
flexibility_required: ensemble
validation_benchmark: none
key_paper_doi: 10.1126/science.1150577
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-09-ensemble-md-too-short
tags: [NEG, anti-pattern, membrane, ensemble, water-only-MD, lipid-missing, GPCR]
---

# NEG-20: Ensemble docking with water-only MD (no lipid bilayer) on membrane protein (anti-rule-09 + anti-rule-03)

## Background (anti-pattern)
团队对 GPCR (β2-AR / GLUT1 / 类似) 跑 200 ns MD ensemble docking — **但 in water-only solvation
(没 lipid bilayer)**。GPCR TM helix 在水溶环境 sampling 不真实: TM6 outward movement +
lipid-mediated cholesterol binding modes 缺失。**Ensemble representatives 全部 distorted —
ensemble docking 在 distorted ensemble 上不如 single inactive crystal docking**。

## ★ 排除/不做的事
- ❌ **Membrane protein water-only MD**: 必 lipid bilayer (POPC / DOPC / mixed)
- ❌ **GPCR cholesterol binding sites 缺失**: CCM motif (case dock-012) 影响 thermostability + agonist
- ❌ **Cofactor / ion 缺失**: GLUT1 substrate-bound state 含 conserved water + glucose contact
- ❌ **Membrane protein用 implicit solvent (GBSA / PBSA)**: 不能替代 explicit lipid
- ❌ **Lipid composition 简单 POPC for cholesterol-rich GPCR**: 必加 30% cholesterol for plasma membrane GPCR

## ★ 失败模式
- **TM helix distortion** in water-only: 跨膜螺旋在水中 unfold 趋势 (~100 ns 后明显)
- **Cholesterol-mediated binding modes missed**: BPTU (β2-AR PAM) 等 lipid-facing site
- **Allosteric modulator failure**: PAM / NAM 通过 lipid-protein-ligand 三方接触
- **Ensemble representatives distorted**: cluster representatives 都失真 → docking 物理不可
- **湿实验 cell-based assay vs reconstituted bicelle assay**: 差异提示 lipid 重要

## ★ 方法选择决策链 (correct alternative)
**Correct path** (case dock-007 + dock-012 + dock-018):
1. **Membrane protein MD MUST be in explicit lipid bilayer**:
   - PACKMOL-Memgen / CHARMM-GUI Membrane Builder
   - POPC / DOPC / mixed (with cholesterol for GPCR)
   - System size: protein + lipid + water + ions ≥ 80,000 atoms typical
2. **MD length adjusted**: lipid equilibration ~50 ns + production ≥ 200 ns
3. **Force field**: CHARMM36m + CHARMM lipid; or Amber14SB + Lipid17/Lipid21
4. **Cluster representatives** check: TM helix RMSD vs initial < 3 Å (sanity)
5. **For docking on ensemble**: dock to multiple lipid-equilibrated frames; lipid-facing sites enumerated separately
6. **GLUT1-class transporters**: substrate-bound vs apo MD give different ensembles (case dock-018)

## ★ Validation metric
- target_class ∈ {GPCR, membrane_transporter, ion_channel, transmembrane} + MD setup 缺 lipid bilayer → BLOCK
- 缺 lipid composition declaration in design_plan → BLOCK
- MD trajectory < 50 ns lipid equilibration → WARN
- GPCR + 缺 cholesterol % declaration → WARN per case dock-012

## Lessons → anti-rule
- **anti-rule-09 + anti-rule-03 (extension)**: ensemble + membrane requires lipid bilayer; water-only MD on TM proteins is structural anti-pattern
- Cross-case evidence: NEG-09 + NEG-15 + NEG-20 + dock-007 + dock-012 + dock-018
- Confidence: high (cross-anti-rule consensus)
