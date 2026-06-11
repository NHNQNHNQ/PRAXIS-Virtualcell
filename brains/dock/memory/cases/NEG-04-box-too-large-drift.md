---
case_id: NEG-04-box-too-large-drift
schema_version: 1
docking_type: protein_ligand
target_pdb: anti-pattern reference
target_class: mixed
ligand_type: small_mol_drug_like
system_specifics:
  ligand_drug_likeness: drug_like
tools: [AutoDock Vina 1.2.5]
flexibility_required: rigid
validation_benchmark: none
key_paper_doi: 10.1021/acs.jcim.8b00545
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-04-box-too-large
tags: [NEG, anti-pattern, box-size, vina-drift, allosteric]
---

# NEG-04: Vina box too large (>30 Å³) drifts to allosteric / surface (anti-rule-04)

## Background (anti-pattern)
团队 "为了不漏掉" 把 Vina box 设到 40 Å³ 包整个 receptor surface。**Vina exhaustive 搜索时
top score pose 飘到 GPCR EC vestibule / kinase 远端 surface pocket / allosteric site**，不是 orthosteric。
湿实验 top-1 化合物 IC50 > 100 µM (没活性) — 但 docking score -10.5 kcal/mol (假阳)。

## ★ 排除/不做的事
- ❌ **Box > 30 Å³ for typical drug-like PL** (case dock-001 lesson)
- ❌ **"Cover entire protein" 思路**: blind docking 用 DiffDock 而不是大 box Vina
- ❌ **Box 不居中 crystal ligand / known binding site**: 把 binding site offset > 5 Å 必败
- ❌ **GPCR 用 22³ Å default**: orthosteric pocket 较小; case dock-012 lesson 推荐 18³

## ★ 失败模式
- **Vina sampling 受 box 体积非线性影响**: box 体积 ↑ 2x → effective sampling 密度 ↓ 8x (3D)
- **Top-1 score drift to surface pocket**: 物理上更宽松的 pose 竞争 → false positive
- **GPCR EC vestibule false binding**: 7TM 蛋白胞外 loop 区域是 secondary binding site
- **Allosteric site 假阳**: BCR-ABL allosteric vs orthosteric inhibitors 结合方式不同; rigid Vina 大 box 把两者搞混
- **Computational waste**: 4x box → 8-10x runtime + 不一定 top-1 更好

## ★ 方法选择决策链 (correct alternative)
**Correct path** (case dock-001 + dock-012):
1. **Default box size = 22 Å³** for typical drug-like PL (case dock-001)
2. **GPCR-specific = 18 Å³** (case dock-012; orthosteric pocket smaller)
3. **Box center**: crystal ligand centroid (if available) OR catalytic / known binding site CA centroid
4. **For blind docking** (no binding site hint): use **DiffDock** (designed for blind) NOT large-box Vina
5. **For full-protein scan**: explicit allosteric site enumeration via fpocket / Sitemap → multi-site docking

**Why this beats the anti-pattern**:
- Vina autobox 在 specific known site 比"全 surface" 错误率低 5-10x (case dock-001 ablation)
- Specific box size 强制 sampling density 集中 → top-1 真信号
- DiffDock blind design 显式处理 "no box" 假设

## ★ Validation metric
- design_plan.docking_box.size 任一维 > 30 → WARN
- size > 40 → BLOCK (drift risk too high; suggest DiffDock for blind)
- box_center == [0,0,0] (default placeholder) without explicit override → BLOCK
- For GPCR target_class: size > 22 → WARN per case dock-012

## Lessons → anti-rule
- **anti-rule-04**: PL Vina box > 30 Å³ → WARN; > 40 Å³ → BLOCK + suggest DiffDock for blind; GPCR-specific 18³
- Cross-case evidence: dock-001 (default 22³), dock-012 (GPCR 18³)
- Confidence: medium-high (well-documented cross-case)
