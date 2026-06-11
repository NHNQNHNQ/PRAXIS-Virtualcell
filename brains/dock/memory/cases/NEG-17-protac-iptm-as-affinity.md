---
case_id: NEG-17-protac-iptm-as-affinity
schema_version: 1
docking_type: foundation_model_complex_prediction
target_pdb: anti-pattern reference (PROTAC ternary AF3)
target_class: PROTAC_ternary
ligand_type: small_mol_or_protein
system_specifics:
  interface_type: induced_protac
tools: [AlphaFold3]
flexibility_required: backbone_flex
validation_benchmark: PoseBusters
key_paper_doi: 10.1038/s41586-024-07487-w
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-11-iptm-as-affinity
tags: [NEG, anti-pattern, PROTAC, ternary, AF3, iPTM, KD, induced-proximity]
---

# NEG-17: PROTAC ternary AF3 iPTM = 0.91 reported as "high affinity" (anti-rule-11)

## Background (anti-pattern)
团队跑 AF3 on E3 ligase (VHL) + linker + target protein (BRD4) PROTAC ternary complex →
**iPTM 0.91 + complex_pLDDT 84**. 报告写: "High iPTM confirms productive ternary complex with
predicted KD < 100 nM"。湿实验 cooperative binding assay (TR-FRET ternary) 显示 α factor
(cooperativity) 仅 0.3 (anti-cooperative; productive PROTAC needs α > 1)。
**iPTM 高 ≠ productive PROTAC** — pose geometry good but cooperativity (Δproximity-induced ΔG) negative。

## ★ 排除/不做的事
- ❌ **PROTAC iPTM 转 KD 或 α factor**: iPTM 是 pose quality; PROTAC degradation requires positive cooperativity
- ❌ **Single ternary pose** without considering linker rotamer ensemble
- ❌ **AF3 PROTAC pose 无 PoseBusters check**: iPTM 0.91 但 atom clash + linker high strain 常见
- ❌ **不验 cooperativity**: TR-FRET / SPR ternary cooperative binding 必须验
- ❌ **不区分 productive vs non-productive ternary**: geometric proximity alone 不足以 predict 泛素化

## ★ 失败模式
- **α factor < 1**: ternary complex forms but anti-cooperative — degradation 失败
- **Linker length / flexibility**: 短 linker 强迫 close geometry but high strain; 长 linker 弱 cooperativity
- **E3 binding mode rotation**: VHL + ligand 在 ternary 中可旋转 ~60°; AF3 single seed 选错 rotamer
- **K48-Ub vs K11/K63 specificity**: docking 不预测 ubiquitin chain type
- **Rebound / hook effect**: 高 PROTAC 浓度 → 自抑制 ternary; docking 看 single-stoichiometry
- **DC50 / Dmax 与 iPTM 无相关**: literature: r ~0.2 between AF3 ternary iPTM and degradation potency

## ★ 方法选择决策链 (correct alternative)
**Correct path** (case dock-016 + rule extension):
1. **PROTAC ternary docking 必跑** (case dock-016):
   - AF3 / Boltz multi-seed (n ≥ 5) — 看 pose convergence
   - PRosettaC (Rosetta) for cooperative geometry sampling
   - HADDOCK with linker as flexible custom topology
2. **iPTM as pose confidence ONLY**: NOT affinity, NOT cooperativity, NOT degradation potency
3. **Cooperativity assay required**: TR-FRET ternary, SPR ternary, BLI; α > 1 = positive cooperative
4. **Linker rotamer ensemble**: 10-50 linker conformations × 5 ternary poses
5. **PoseBusters mandatory** + linker strain energy < 5 kcal/mol
6. **DC50 / Dmax 由 cell-based degradation assay** (not docking)

## ★ Validation metric
- docking_type == foundation_model + system_specifics.interface_type == induced_protac + report claims "affinity" / "KD" / "DC50" from iPTM → BLOCK
- 缺 cooperativity assay plan → WARN (PROTAC-specific)
- 缺 linker rotamer sampling plan → WARN
- n_seeds < 5 → WARN

## Lessons → anti-rule
- **anti-rule-11 (extension)**: iPTM ≠ KD applies to ternary complexes (PROTAC, molecular glue, scaffold proteins) too
- Cross-case evidence: NEG-11 + NEG-17 + dock-009 + dock-016 (PROTAC ternary)
- Confidence: high (multi-modality: PL + ternary)

## Training data leakage caveat (anti-rule-11 cross-reference)
Foundation models (AF3, Boltz, RFAA) trained on PDB pre-2021 / 2022. Any benchmark or
prospective claim requires **train/test PDB time-split** check: target PDB release year >= 2021
for fair evaluation. **Train data leakage** is a known anti-pattern (case dock-009 lesson) and
applies to all NEG- cases referencing foundation_model_complex_prediction.
