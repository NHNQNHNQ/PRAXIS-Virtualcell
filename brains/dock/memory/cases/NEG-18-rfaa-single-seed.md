---
case_id: NEG-18-rfaa-single-seed
schema_version: 1
docking_type: foundation_model_complex_prediction
target_pdb: anti-pattern reference (RFAA single seed)
target_class: mixed
ligand_type: small_mol
system_specifics: {}
tools: [RoseTTAFold-AA]
flexibility_required: backbone_flex
validation_benchmark: PoseBusters
key_paper_doi: 10.1126/science.adl2528
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-11-iptm-as-affinity
tags: [NEG, anti-pattern, RFAA, single-seed, no-consensus, no-PoseBusters]
---

# NEG-18: RFAA single-seed inference shipped (anti-rule-02 + anti-rule-11)

## Background (anti-pattern)
团队跑 RoseTTAFold-AA single-seed for novel scaffold inhibitor + receptor → 报告 single pose with
"top confidence". **没跑 PoseBusters; 没 cross-validate with AF3 / Boltz / Vina**.
RFAA single forward pass stochastic — 不同 seed 给不同 pose; **single seed 不能信任**.
后续 PoseBusters check 显示 atom clash + 异常 chirality (R→S flip)。
湿实验 SPR 显示 binding 但 pose RMSD vs cryo-EM 6.2 Å。

## ★ 排除/不做的事
- ❌ **RFAA single seed forward pass shipped**: stochastic; need multi-seed + cluster
- ❌ **RFAA-only without AF3 / Boltz cross-check**: 3-way consensus is rule (case dock-013)
- ❌ **PoseBusters 跳过 on RFAA output** (case dock-009 + dock-013 mandate)
- ❌ **Stereochemistry not verified**: input isomeric SMILES but output not checked for chirality preservation
- ❌ **OOD ligand chemtypes (PROTAC, macrocycle > 8-membered, metal-coordinated)**: RFAA degrades to random pose

## ★ 失败模式
- **Different seeds → different poses** (no convergence signal)
- **PoseBusters fail (~32% rate per case dock-013)** for RFAA outputs
- **Chirality flip**: foundation models偶尔翻转 R/S enantiomer
- **Membrane / lipid 缺失**: water-only RFAA on GPCR / membrane protein = unrealistic
- **Cofactor-dependent fold collapse**: missing NAD/heme/Mg2+ → active site geometry塌

## ★ 方法选择决策链 (correct alternative)
**Correct path** (case dock-009 + dock-013):
1. **n_seeds ≥ 5 mandatory** for foundation model inference
2. **3-way consensus**: AF3 + Boltz + RFAA (case dock-013 lesson) — when available, beats single-model
3. **PoseBusters check on EVERY pose** (overall_pass_rate threshold for confidence)
4. **Stereochemistry validation**: input isomeric SMILES; verify output chirality match
5. **Speed / accuracy trade-off**: RFAA ~2 min/cmpd (batch screen); AF3 ~10 min/cmpd (precision)
6. **iPTM ≠ KD** (anti-rule-11)

## ★ Validation metric
- foundation_model + n_seeds < 5 → WARN
- foundation_model + 缺 posebusters_check → BLOCK
- foundation_model + single-method (no 3-way consensus when feasible) → WARN

## Lessons → anti-rule
- **anti-rule-02 + anti-rule-11 (extension)**: RFAA / AF3 / Boltz single-seed shipped is double anti-pattern
- Cross-case evidence: NEG-02 + NEG-11 + NEG-18 + dock-009 + dock-013
- Confidence: high

## Training data leakage caveat (anti-rule-11 cross-reference)
Foundation models (AF3, Boltz, RFAA) trained on PDB pre-2021 / 2022. Any benchmark or
prospective claim requires **train/test PDB time-split** check: target PDB release year >= 2021
for fair evaluation. **Train data leakage** is a known anti-pattern (case dock-009 lesson) and
applies to all NEG- cases referencing foundation_model_complex_prediction.
