---
case_id: NEG-14-diffdock-blind-shipped
schema_version: 1
docking_type: protein_ligand
target_pdb: anti-pattern reference (DiffDock blind)
target_class: mixed
ligand_type: small_mol_drug_like
system_specifics:
  ligand_drug_likeness: drug_like
tools: [DiffDock 1.1]
flexibility_required: rigid
validation_benchmark: PoseBusters
key_paper_doi: 10.1038/s42256-024-00895-7
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-02-single-method
tags: [NEG, anti-pattern, DiffDock, single-method, blind, PoseBusters-fail]
---

# NEG-14: DiffDock-only blind docking shipped (anti-rule-02)

## Background (anti-pattern)
团队对未知 binding site 的 receptor 用 **DiffDock blind 单方法** (no Vina/GNINA/AF3 cross-check)
ship top-1 pose 到湿实验。湿实验 SPR 显示 binding site 与 DiffDock pose 偏差 > 8 Å。
**DiffDock 在 PoseBusters benchmark 上 top-1 ≤ 2 Å rate ~38% (vs Vina box-guided ~50%, AF3 ~76%)
+ 其物理 sanity check (PoseBusters) fail rate 高 — Buttenschoen 2024 分析显示 DiffDock 容易给
"似是而非但物理不可" pose** (atom clash, 高 strain energy)。

## ★ 排除/不做的事
- ❌ **DiffDock 单方法 ship**: blind docking 给 DiffDock 是 first-line OK, 但 ship 必须 Vina + AF3 cross-check
- ❌ **不验 PoseBusters on DiffDock output**: case dock-009 mandate; DiffDock 物理 sanity 历来差
- ❌ **Blind docking 当 box-guided 替代**: 当 binding site 已知, **box-guided Vina 比 blind DiffDock 准**
- ❌ **n_seeds = 1 for DiffDock**: 必须 multi-sample + cluster

## ★ 失败模式
- **物理不可 pose**: DiffDock generate poses with atom clash + 异常键长 + 异常 chirality (Buttenschoen 2024 analysis)
- **Top-1 RMSD ~8 Å**: blind setting 找不到正确 pocket; box-guided 优势失去
- **Wrong binding site**: 全蛋白搜索 → 偶尔找 surface secondary site
- **湿实验 SPR site-mapping**: cross-link MS / HDX 显示 DiffDock 错位

## ★ 方法选择决策链 (correct alternative)
**Correct path**:
1. **Use DiffDock for blind only when binding site truly unknown**, AND always:
2. **Add PoseBusters mandatory** (case dock-009)
3. **Multi-method consensus**: DiffDock + AF3 (Boltz) + box-guided Vina (if any binding site hint)
4. **For unknown site**: combine DiffDock blind + fpocket binding site detection + box-guided Vina on top fpocket sites

## ★ Validation metric
- DiffDock as sole method (no consensus) → BLOCK (anti-rule-02)
- DiffDock output 缺 posebusters_check → BLOCK (anti-rule-11)
- PoseBusters pass rate < 50% on DiffDock output + no box-guided cross-check → confidence_label = low

## Lessons → anti-rule
- **anti-rule-02 (extension)**: DiffDock alone is single-method anti-pattern; pair with box-guided Vina + AF3 (multi-anchor with NEG-02)
- Cross-case evidence: NEG-02 + NEG-14 + dock-001 + dock-009
- Confidence: high
