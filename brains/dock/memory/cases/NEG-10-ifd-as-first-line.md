---
case_id: NEG-10-ifd-as-first-line
schema_version: 1
docking_type: induced_fit_protein_ligand
target_pdb: anti-pattern reference (kinase Type II)
target_class: kinase
ligand_type: small_mol
system_specifics:
  ligand_drug_likeness: drug_like
tools: [Schrodinger IFD-MD, Rosetta RosettaLigand]
flexibility_required: sidechain_flex
validation_benchmark: none
key_paper_doi: 10.1021/jm060522a
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-10-ifd-first-line
tags: [NEG, anti-pattern, IFD, first-line, no-rigid-baseline, flex-residues-too-many]
---

# NEG-10: IFD as first-line on 1k+ compound library (anti-rule-10)

## Background (anti-pattern)
团队对 1000 化合物 library 直接跑 Schrödinger IFD-MD (跳过 rigid baseline)。**IFD-MD ~5 min/化合物
×1000 = 83 hours computational cost** (rigid Vina ~5 sec/化合物, 1000 = 1.4 hours)。
**60x cost waste** — 因 ~70% 化合物 rigid Vina 已经够 (case dock-008 lesson)，
只有 RMSD > 3 Å 的剩 30% 才需要 IFD upgrade。

而且 team 在 IFD 输入指定 12 个 flex residues (binding-site + 5 Å 邻居)。**case dock-008 lesson 上限 6**。
计算时间再 ×4 (12-flex 比 6-flex)。最终 332 hours total — 比合理 strategy (rigid Vina 1.4h + IFD on top
30% = 14h) 慢 24x。

## ★ 排除/不做的事
- ❌ **IFD 当 first-line for library screening** (~70% case rigid 已足够)
- ❌ **IFD on > 100 compound library** (single-target lead opt 适合, hit-id 不适合)
- ❌ **flex_residues > 6** (case dock-008 lesson; 计算指数增长 with diminishing returns)
- ❌ **Backbone-level conformational change with IFD**: IFD 只 side chain; backbone change → ensemble docking
- ❌ **Single random seed for IFD**: stochastic; multi-seed (≥ 3) 验证 reproducibility
- ❌ **不查 ligand internal strain energy**: IFD pose 中 ligand 高 strain (>5 kcal/mol vs free) = red flag

## ★ 失败模式
- **Computational cost explosion**: flex_residues 从 6 → 8 → 10 → 12, runtime ~exp(N)
- **Multiple IFD outcomes**: 不同 initial pose → 不同 final, no convergence; top by score 不一定 right
- **Backbone change ignored**: IFD 不动 backbone; kinase activation loop flip / GPCR TM helix shift 漏掉
- **Side chain rotamer locked by H-bond network**: IFD 给的 packing 破坏 native H-bond → 假 stable
- **Pocket water 不动**: IFD 修 side chain 但 water rigid → physically inconsistent
- **Force field biased in flexible region**: side chain repacking accuracy 限于 FF
- **Hit-to-lead 适合, hit-id 不适合**: cost economics

## ★ 方法选择决策链 (correct alternative)
**Correct path** (case dock-008):
1. **Rigid Vina FIRST** for full library (~5 sec/cmpd × 1000 = ~1.5 hours)
2. **Filter by Vina score top N** (~30% of library)
3. **Sub-filter: top RMSD vs known holo > 3 Å OR score discrepancy** → IFD candidate (~30% of N = ~10% library)
4. **IFD on candidates only** (lead opt scope), `flex_residues ≤ 6`
5. **Multi-seed IFD** (3 random seeds): top pose consistency check
6. **Ligand strain energy check**: pose vs free state; > 5 kcal/mol = red flag
7. **Backbone-flexibility cases** → use ensemble docking (case dock-007), NOT IFD

**Why this beats the anti-pattern**:
- 60x speedup vs IFD-only strategy
- Side-chain only 假设清晰 (no backbone illusion)
- Multi-seed reproducibility
- Library scale: 1k compounds finishes in ~14 hours instead of ~330

## ★ Validation metric
- docking_type == induced_fit_protein_ligand + library_size > 100 → WARN (cost-prohibitive)
- flex_residues > 6 → BLOCK (case dock-008)
- IFD without rigid baseline performed first → WARN
- IFD pose ligand_internal_strain_energy > 5 kcal/mol → mark `physically_dubious=true`

## Lessons → anti-rule
- **anti-rule-10**: IFD as first-line on > 100 compound library → BLOCK; flex_residues > 6 → BLOCK
- Cross-case evidence: dock-008 (kinase Type II IFD)
- Confidence: medium-high
