---
case_id: NEG-07-flexpepdock-long-peptide
schema_version: 1
docking_type: peptide_protein
target_pdb: anti-pattern reference
target_class: chaperone
ligand_type: peptide
system_specifics:
  peptide_length_bin: ">20"
  peptide_structure: extended
tools: [Rosetta FlexPepDock]
flexibility_required: backbone_flex
validation_benchmark: none
key_paper_doi: 10.1093/nar/gkn216
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-07-flexpepdock-long-peptide
tags: [NEG, anti-pattern, peptide, FlexPepDock, length-gate]
---

# NEG-07: FlexPepDock on peptide > 20 aa (anti-rule-07)

## Background (anti-pattern)
团队对 25 aa peptide-MHC 结合做 FlexPepDock 100 trajectory。**违反 case dock-005 lesson**: 长度
> 20 aa medium-quality success rate < 20%。100 trajectory 不收敛 — top-1 RMSD 7-12 Å。
湿实验 SPR 显示 peptide 实际 binding，但 docking 给的 pose 完全错。

## ★ 排除/不做的事
- ❌ **FlexPepDock on peptide_length_bin == ">20"** (case dock-005)
- ❌ **HPEPDOCK 默认 cluster radius 对长肽** (>20 aa 不合适)
- ❌ **Peptide 不带 secondary structure prediction** (PSIPRED / NetSurfP)
- ❌ **Receptor 全 rigid (no side chain flex)** for peptide docking — peptide induces induced fit
- ❌ **Cyclic / disulfide / D-aa peptide on FlexPepDock** (force field 缺参数)
- ❌ **Peptide 当 small molecule** (Vina rotatable bonds > 10 失败)

## ★ 失败模式
- **Configurational degree-of-freedom 爆炸**: peptide 25 aa ≈ 50+ rotatable bonds, far beyond Vina/FlexPepDock 设计 envelope
- **Single trajectory 不收敛**: 100 trajectory 给 100 个不同 conformation, no clear cluster
- **Peptide 无 reference fold**: completely disordered IDR-like peptide 找不到 docking start
- **Multiple binding modes** (e.g., HSP70 promiscuous binding): top-1 may be secondary site
- **Cyclized peptide (Cys-Cys disulfide / head-to-tail amide)**: linear assumption breaks geometry
- **Non-natural aa (D-aa, Aib, hydroxyproline)**: standard force field 错

## ★ 方法选择决策链 (correct alternative)
**Correct path** (case dock-005 lesson):
1. **Length ≤ 15 aa** → FlexPepDock (medium-high success ~50%)
2. **Length 15-20 aa** → FlexPepDock (medium ~30-40%) + caution
3. **Length > 20 aa** → switch to:
   - **af3_complex_predict** (Boltz / AF-Multimer with peptide as second chain) — handles long peptide
   - **Plus post-MD short check** (50 ns water box) verify peptide doesn't unfold
4. **Cyclic peptide** → HADDOCK with custom topology
5. **Initial peptide secondary structure** (helix / extended / PPII) MUST be predicted (PSIPRED)
6. **Receptor side-chain flex mandatory** — peptide induces induced fit; rigid receptor underestimates

**Why this beats the anti-pattern**:
- AF-Multimer trained on 1000s of peptide-protein complexes, handles long peptides natively
- Length-aware confidence: 5-15 medium-high, 15-20 medium, >20 low (auto)

## ★ Validation metric
- docking_type == peptide_protein + chosen_methods 含 flexpepdock_peptide + peptide_length > 20 → BLOCK
- 缺 peptide_length_bin in system_specifics → BLOCK (cannot route)
- Cyclic peptide (terminal Cys-Cys + length ≥ 4) + chosen_methods == flexpepdock_peptide → WARN; suggest HADDOCK
- 缺 secondary_structure prediction in design → WARN

## Lessons → anti-rule
- **anti-rule-07**: peptide > 20 aa + FlexPepDock → BLOCK; route to af3_complex_predict; > 25 aa = low confidence regardless
- Cross-case evidence: dock-005 (FlexPepDock benchmark)
- Confidence: high
