---
case_id: NEG-16-mpro-covalent-no-warhead
schema_version: 1
docking_type: covalent_protein_ligand
target_pdb: 6LU7
target_uniprot: P0DTC1
target_class: protease
ligand_type: covalent_warhead_small_mol
system_specifics:
  warhead_type: aldehyde
  reactive_residue: Cys145
tools: [AutoDock Vina 1.2.5]
flexibility_required: rigid
validation_benchmark: none
key_paper_doi: 10.1126/science.abb4489
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-08-covalent-no-restraint
tags: [NEG, anti-pattern, covalent, SARS-CoV-2-Mpro, aldehyde, Cys145]
---

# NEG-16: SARS-CoV-2 Mpro inhibitor (aldehyde / nirmatrelvir-like) without warhead detection (anti-rule-08)

## Background (anti-pattern)
团队对 SARS-CoV-2 Mpro (3CL protease) 跑 plain Vina with peptidomimetic 含醛 warhead
(类似 nirmatrelvir/Paxlovid 但 team's analog) — **Vina 没识别 aldehyde 是 reversible covalent warhead
to Cys145**。Top-1 pose 把醛朝外 (距 Cys145 SG 5.6 Å)，物理上不可形成 thiohemiketal 共价。
湿实验 LC-MS 显示 0% 共价标记 — pose 完全错。

## ★ 排除/不做的事
- ❌ **Aldehyde / nitrile / α,β-unsaturated ketone warhead 用 plain Vina** without `--covalent-residue Cys145`
- ❌ **Reversible covalent (aldehyde, nitrile) 与 irreversible (acrylamide) 混用同 path**: kinetics 不同
- ❌ **Cys145 / His41 catalytic dyad 都不区分**: Mpro Cys145 是 nucleophile, His41 是 general base; covalent attack 在 Cys145
- ❌ **Mpro homology to chymotrypsin pocket assumed**: structural similarity not enough; explicit Cys145 SMARTS detection
- ❌ **Flexibility ignored**: Mpro His41-Cys145 catalytic dyad orientation depends on substrate state

## ★ 失败模式
- **Reversible covalent kinetics**: aldehyde forms thiohemiketal at equilibrium; kon/koff matter, not just docking score
- **Hydration state**: Mpro active site has crystallographic water network; covalent docking pose H-bond pattern depends
- **GSH detoxification**: aldehyde warheads can be reduced by aldoketo reductases or react with GSH; in-vivo failure cycle
- **P1 / P2 / P3 / P4 substrate-mimetic side chain**: covalent docking should preserve substrate-mimetic geometry across S1-S4 subsites
- **湿实验 LC-MS / SARS-CoV-2 cell-based assay**: 0% covalent labeling, no antiviral activity

## ★ 方法选择决策链 (correct alternative)
**Correct path** (rule_01 + case dock-006 + dock-011 + NEG-16):
1. **Warhead SMARTS detection extended for aldehyde**: pattern `[CX3H1](=O)[#6]` for aldehyde C
2. **Cys145 explicit `reactive_residue: Cys145`** in system_specifics (Mpro nucleophile)
3. **Reversible vs irreversible flag**: aldehyde, nitrile = reversible; acrylamide, chloroacetamide = irreversible
4. **Distance constraint ≤ 2.0 Å** between warhead C and Cys145 SG
5. **Use Meeko `--tether_smarts "[CX3H1](=O)" --rec_residue "A:CYS:145"`**
6. **Substrate-mimetic geometry validation**: P1 = Gln-like, P2 = Leu-mimic — verify subsite occupancy

## ★ Validation metric
- docking_type == covalent_protein_ligand + target == Mpro + reactive_residue ≠ Cys145 → BLOCK
- Aldehyde warhead detected + reversible flag missing → WARN
- 缺 P1-P4 subsite check on Mpro pose → WARN

## Lessons → anti-rule
- **anti-rule-08 (extension)**: covalent rule applies to all warhead chemistries (acrylamide / aldehyde / nitrile / boronate) + all nucleophiles (Cys / Ser / Lys)
- Cross-case evidence: NEG-08 + NEG-16 + dock-006 (KRAS Cys, acrylamide) + dock-011 (BTK Cys, acrylamide) → now also Mpro Cys + aldehyde
- Confidence: high (multi-target, multi-warhead-chemistry consensus)
