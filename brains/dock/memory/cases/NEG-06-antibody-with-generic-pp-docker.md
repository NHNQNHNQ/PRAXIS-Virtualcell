---
case_id: NEG-06-antibody-with-generic-pp-docker
schema_version: 1
docking_type: antibody_antigen
target_pdb: anti-pattern reference (Fab vs antigen)
target_class: antibody
ligand_type: protein_antibody
system_specifics:
  CDR_H3_length: 14
  interface_type: transient
tools: [ClusPro 2.0, HADDOCK 2.4]
flexibility_required: rigid
validation_benchmark: CAPRI
key_paper_doi: 10.1371/journal.pcbi.1000644
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-06-antibody-generic-docker
tags: [NEG, anti-pattern, antibody, framework-binding, no-paratope-restriction]
---

# NEG-06: Antibody-antigen with generic PP docker (no antibody mode) (anti-rule-06)

## Background (anti-pattern)
团队拿 Fab + antigen 跑 ClusPro 默认 balanced weight (无 antibody mode) + HADDOCK 不限定 paratope。
**Top-1 cluster 显示 antibody framework β-sheet (Trp36, Tyr49 framework residues) 朝向 antigen** —
生物学上不可能 (paratope 是 CDR1/2/3, 不是 framework)。湿实验 SPR / BLI 显示 designed
antibody 完全无 binding。

CDR H3 长度 22 aa (anti-pattern flag — case dock-004 lesson > 18 aa = low conf)，
但 team 没用 SnugDock CDR-flex mode 也没用 IgFold structure prep — homology model framework 错。

## ★ 排除/不做的事
- ❌ **ClusPro default balanced weight on antibody** without `--antibody-mode` (case dock-003 lesson)
- ❌ **HADDOCK on Fab without paratope restriction** (CDR-only AIR active)
- ❌ **Antibody framework structure from traditional homology** (Modeller/SwissModel) — must IgFold/ImmuneBuilder
- ❌ **CDR H3 > 18 aa + ignore confidence flag**
- ❌ **Nanobody (VHH) + IgFold (Fv tool)** — VHH 没 light chain, 用 NanoNet (case dock-014 lesson)
- ❌ **Bispecific Ab / IgG full molecule single dock** — 必须拆 Fab 并联

## ★ 失败模式
- **Framework face binds antigen** (ClusPro default puts highest-electrostatic-complementarity face): 生物学不可能但 PIPER score 好
- **Long H3 (>18 aa)** + rigid CDR: 所有 antibody-specific docker 失败; 即使 SnugDock CDR-flex 也 < 20% medium quality
- **Glycan-shielded epitope** (spike, gp120): 模型不含糖 → false binding to glycan-mask 区域
- **Conformational epitope vs linear**: 序列上不连续 epitope，rigid docking 难
- **湿实验 SPR / BLI 完全无 binding 信号**: antibody 错 face binding antigen
- **Allosteric Ab** (作用通过远端 conformational change): docking 概念失效

## ★ 方法选择决策链 (correct alternative)
**Correct path** (case dock-004 SnugDock + dock-014 nanobody):
1. **Antibody prep**: IgFold (Fv) for Fab/scFv; NanoNet for VHH/nanobody — NOT homology
2. **CDR H3 length gate**: > 18 aa → confidence_label=low automatic; warn user
3. **Use SnugDock with CDR-flex** (Rosetta) OR `cluspro_blind_pp` with `--antibody-mode`
4. **Epitope hint mandatory** (case dock-004): blind epitope 即使 SnugDock 也降到 < 20% success
5. **n_trajectories ≥ 1000** (Fab); ≥ 1500 (VHH 因 H3 自由度更大, case dock-014)
6. **AF-Multimer / Boltz cross-check**: 3-way consensus = high conf

**Why this beats the anti-pattern**:
- Antibody-mode restricts paratope to CDR (framework face cannot bind)
- IgFold framework geometry > homology by ~3 Å avg RMSD
- Epitope hint constrains to biologically meaningful region

## ★ Validation metric
- docking_type == antibody_antigen + chosen_methods 含 cluspro_blind_pp 但 antibody_mode != true → BLOCK
- chosen_methods 含 cluspro_blind_pp / haddock_pp_with_air 但缺 epitope_hint / paratope_restriction → BLOCK
- antibody framework method ∉ {IgFold, ImmuneBuilder, NanoNet, AlphaFold-Multimer} → WARN
- CDR_H3_length > 18 → confidence_label must be low/cold_start (auto)

## Lessons → anti-rule
- **anti-rule-06**: antibody_antigen 用 generic PP docker without antibody-mode → BLOCK; framework method must be IgFold/ImmuneBuilder/NanoNet
- Cross-case evidence: dock-003 (ClusPro antibody mode), dock-004 (SnugDock + IgFold), dock-014 (NanoNet for VHH)
- Confidence: high
