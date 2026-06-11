---
case_id: NEG-19-rna-aptamer-pp-docker
schema_version: 1
docking_type: protein_nucleic_acid
target_pdb: anti-pattern reference (RNA aptamer + protein)
target_class: receptor
ligand_type: nucleic_acid
system_specifics:
  na_strandedness: ss
  sequence_specificity: random
tools: [HADDOCK 2.4, ZDOCK]
flexibility_required: rigid
validation_benchmark: none
key_paper_doi: 10.1093/nar/gkx1037
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-12-na-pp-docker
tags: [NEG, anti-pattern, RNA-aptamer, ssRNA, PP-docker, no-secondary-structure]
---

# NEG-19: RNA aptamer + protein with HADDOCK PP docker (no NA mode + no 2D structure) (anti-rule-12)

## Background (anti-pattern)
团队对 RNA aptamer (~40 nt, ssRNA hairpin + internal loop secondary structure) docking 到目标蛋白
用 HADDOCK 2.4 default PP weights (no NA mode)。**RNA 用 helix-only assumption + rigid B-form-like
geometry**, 没正确 fold RNA secondary structure。Top-1 cluster 把 RNA 摆到蛋白 surface 而不是
known binding cleft (literature SHAPE probing data 矛盾)。

## ★ 排除/不做的事
- ❌ **HADDOCK / ClusPro on RNA-protein** (PP scoring biased)
- ❌ **ssRNA rigid docking**: ssRNA 极柔，rigid 假设破坏
- ❌ **RNA helix-only assumption**: 复杂 RNA 含 hairpin / internal loop / pseudoknot — 用 SimRNA / RNAComposer
- ❌ **不验 RNA secondary structure**: SHAPE / CMC chemical probing data 必比对
- ❌ **RNA aptamer with G-quadruplex motif (TBA, AS1411)** without specialized G4 force field

## ★ 失败模式
- **RNA secondary structure errors propagate**: input 3D RNA model 错 → 整个 protein-RNA 几何错
- **ssRNA flexibility 不建模**: rigid assumption 给假 contacts
- **R-loop / triplex / G-quadruplex unsupported**: standard NA docker 不识别
- **PP scoring biased to electrostatic / hydrophobic**: NA backbone-base specific contact under-weighted
- **湿实验 SHAPE / DMS-MaPseq 不匹配**: aptamer pose with wrong base accessibility pattern

## ★ 方法选择决策链 (correct alternative)
**Correct path** (case dock-010 + extension):
1. **NA-specific docker**: HDOCK / NPDock / **AF3 (NA mode) / Boltz / RoseTTAFold-2NA**
2. **AF3-NA / Boltz first-line for aptamer-protein** (joint fold both ssRNA structure + complex)
3. **RNA secondary structure prep**: SimRNA (de novo) or RNAComposer (from SHAPE-Seq); validate against literature
4. **For G-quadruplex aptamers** (TBA, AS1411): explicit G4 force field (CHARMM-G4 or AMBER-OL15)
5. **SHAPE / CMC probing data validation**: high-reactivity nt should be solvent-exposed in pose

## ★ Validation metric
- docking_type == protein_nucleic_acid + ligand_type == ssRNA / aptamer + chosen_methods 含 HADDOCK without NA mode → BLOCK
- 缺 RNA secondary structure prediction (SHAPE / CMC / SimRNA) → BLOCK
- G4 motif detected (consecutive G-tracts) + standard force field → WARN

## Lessons → anti-rule
- **anti-rule-12 (extension)**: protein-NA covers TF-DNA, CRISPR-RNP, aptamer; multi-anchor with NEG-12 + NEG-19
- Cross-case evidence: NEG-12 + NEG-19 + dock-010 (TF-DNA) + dock-015 (Cas9-gRNA)
- Confidence: high (multi-NA-modality)
