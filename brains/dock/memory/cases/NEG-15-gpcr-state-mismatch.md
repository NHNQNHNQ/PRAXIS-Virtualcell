---
case_id: NEG-15-gpcr-state-mismatch
schema_version: 1
docking_type: protein_ligand
target_pdb: anti-pattern reference (GPCR β2-AR active vs inactive)
target_class: GPCR
ligand_type: small_mol_drug_like
system_specifics:
  ligand_drug_likeness: drug_like
tools: [AutoDock Vina 1.2.5, GLIDE]
flexibility_required: rigid
validation_benchmark: none
key_paper_doi: 10.1126/science.1150577
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-03-rigid-when-conformational-change
tags: [NEG, anti-pattern, GPCR, state-mismatch, agonist, inactive-crystal]
---

# NEG-15: GPCR agonist docked into inactive-state crystal (anti-rule-03)

## Background (anti-pattern)
团队对 β2-AR active-state agonist (BI-167107 derivative) 用 inactive crystal (2RH1, antagonist-bound)
做 rigid Vina 排序。**Top-1 score 高但全部 binding mode 与已知 agonist binding (3SN6 active state) 偏差 ~14 Å**
(因 active state TM6 outward + ICL3 重排; rigid inactive 假设破坏 binding pocket 几何)。
湿实验 cAMP 累积测定显示 designed agonist 实际是 partial agonist or inverse agonist。

## ★ 排除/不做的事
- ❌ **Antagonist 用 active crystal / agonist 用 inactive crystal**: GPCR docking 必 state-match (case dock-012 lesson)
- ❌ **All-state docking 平均**: agonist + antagonist 不能混排同一 crystal
- ❌ **没核对 receptor state metadata**: PDB header / 与已知 ligand category 一致
- ❌ **Homology model 跨 state**: e.g., 同源 active state model on inactive scaffold = 几何错
- ❌ **Membrane bilayer 缺失**: 水溶 docking 上 lipid-mediated binding modes 漏

## ★ 失败模式
- **TM6 outward movement ~14 Å** (β2-AR; case dock-012 lesson): inactive crystal cytoplasmic side relative to active
- **ICL3 reorganization**: active state has ICL3 ordered, inactive has flexible/missing ICL3
- **Sodium-binding pocket water network**: active state Na+ sites drained; inactive retains
- **Cholesterol consensus motif (CCM)**: thermostability + agonist binding-site water differ
- **Functional outcome misclassified**: docking can place ligand correctly geometrically but functional class (agonist vs antagonist vs PAM) needs functional assays

## ★ 方法选择决策链 (correct alternative)
**Correct path** (case dock-012 lesson):
1. **State match**: agonist → active state crystal (e.g., β2-AR 3SN6 with G-protein); antagonist → inactive (2RH1)
2. **PAM (allosteric modulator)** → may need both states + lipid-facing site sampling
3. **Box 18 Å³ for orthosteric** (case dock-012); 22 Å³ default 太大
4. **Conserved water 强制保留**: D2.50 Na+ pocket + Asp113 hinge water
5. **Membrane-aware**: PACKMOL-Memgen + MD ≥ 200 ns + ensemble docking
6. **Functional assay confirm**: cAMP / GTPγS / β-arrestin recruitment

## ★ Validation metric
- target_class == GPCR + flexibility_required == rigid → WARN
- 缺 receptor state hypothesis (active/inactive/PAM) in scoping_plan → BLOCK
- 缺 conserved water list when PDB has documented water → WARN
- 缺 membrane / lipid plan in design when target is 7TM → WARN

## Lessons → anti-rule
- **anti-rule-03 (extension)**: GPCR state mismatch is structural-but-functional anti-pattern; sister to kinase DFG
- Cross-case evidence: NEG-03 + NEG-15 + dock-012
- Confidence: high
