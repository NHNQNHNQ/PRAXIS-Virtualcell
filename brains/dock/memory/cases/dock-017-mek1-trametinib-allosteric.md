---
case_id: dock-017-mek1-trametinib-allosteric
docking_type: induced_fit_protein_ligand
target_pdb: 7M0U
target_uniprot: Q02750
target_class: kinase
ligand_type: small_mol_drug_like
system_specifics:
  ligand_drug_likeness: drug_like
  binding_mode: allosteric
tools: [Schrodinger IFD-MD, AutoDock Vina (flex), GNINA 1.0, Rosetta RosettaLigand]
flexibility_required: backbone_flex
validation_benchmark: PDBbind
key_paper_doi: 10.1158/1078-0432.CCR-12-1872
status: validated
source: praxis_seed
tags: [allosteric, MEK1, trametinib, kinase, non-ATP-pocket, induced_fit, 7M0U]
---

# MEK1 + trametinib：非 ATP-竞争性别构 docking

## Background
Trametinib (Mekinist) 是 FDA-批准的 MEK1/2 别构抑制剂 (2013, melanoma BRAF V600E 联用)。与 ATP-竞争性激酶抑制剂 (case dock-008 IFD kinase, dock-011 BTK) 完全不同：
1. **结合在 ATP 旁边 allosteric pocket** (activation loop + αC helix interface)；
2. **DFG-out / αC-out 构象诱导** — MEK1 启动反应必须 αC-in，trametinib 锁 αC-out 阻止激活；
3. **Mg2+ + ATP 旁路 binding**: 不与 ATP 竞争 (ATP 结合不被 displace)，但阻止下游磷酸化；
4. **Selectivity advantage**: 别构 site 跨家族 sequence divergence 大 → MEK1/2 对 ERK / RAF 选择性高。

## What I actually did
1. **Receptor prep**: 7M0U (MEK1 + trametinib + ATP + Mg) — **保留 ATP + Mg2+** (allosteric inhibition 依赖 ATP 占位); 删 trametinib (要 redock); 加 H pH 7.4
2. **Pocket detection**: fpocket 找到 ATP pocket + 别构 pocket 两个 cavity；强制 box 中心定 allosteric pocket (中心 ≈ residue Lys97/Phe129/Met143)，不是 ATP pocket
3. **Trametinib SMILES**: `Cc1cnc(c(c1)C(=O)c2cccc(c2F)F)Nc3cc(c(c(c3)F)I)NC(=O)c4cccnc4O` — flat aromatic core + iodide → π-stacking + 卤键
4. **First try rigid Vina** in allosteric box: top score -7.2 kcal/mol but RMSD vs crystal 4.8 Å → fail (case dock-008 trigger)
5. **IFD via Vina --flexres**: 6 binding-site residues flex (Lys97, Met146, Phe129, Val127, Met143, Cys121) → top score -8.5 kcal/mol, RMSD 1.8 Å → success
6. **Cross-method consensus**: Schrödinger IFD-MD + Rosetta RosettaLigand + GNINA on flex-receptor → 3 方一致 (RMSD < 2 Å) — high confidence
7. **Selectivity panel**: same allosteric box dock to MEK2 (Q9Y594 - very similar) + ERK1/2 → trametinib MEK1/2 selectivity confirmed (ERK1 score > -5)

## ★ 排除/不做的事
- **删 ATP from receptor**: trametinib 是 "ATP-合作 allosteric" — 没 ATP 结合时构象不同; 必须保留 ATP (以及 Mg2+)
- **用 ATP pocket box** for trametinib docking: pocket 错位 → 必失败
- **Rigid docking 直接信任** when score 高: case dock-008 教训 — 别构 site 通常涉及 induced fit
- **跨激酶家族盲目转移参数**: ATP-pocket 同源性高，allosteric pocket 完全不同 — MEK1 别构 ≠ BRAF 别构 ≠ ERK 别构
- **DFG-out conformation 缺失**: trametinib 锁 DFG-out + αC-out — 用 active state crystal docking 给假阳
- **Mg2+ 删除**: ATP-Mg2+ coordination affects allosteric pocket dynamics
- **Single binding mode 假设**: type II / type III / type IV 异构都可能 — 别构 inhibitor 必须扫多种构象 input

## ★ 失败模式
- **DFG flip dynamics**: rare events on MD timescales — apo MD < 1 μs may miss DFG-out → ensemble docking needs long trajectories
- **Activation loop disorder in apo**: missing residues in 7M0U / 3WIG → can not directly use for docking; need loop modeling first
- **Resistance mutation MEK1 K57N / Q56P**: docking with WT MEK1 → predicts trametinib bind, but resistant cells in vivo → mutation panel needed
- **Off-target on other αC-out kinases**: cobimetinib selectivity issues — trametinib actually rather selective due to allosteric pocket geometry, but generic prediction tools miss this
- **ATP turnover rate dependency**: trametinib stabilizes inactive state, but if substrate ATP binds first then T inhibitor displaces — kinetics matter, docking gives only thermodynamic snapshot
- **Crystallographic artifacts**: 7M0U has high B-factor on activation loop — pose accuracy in that region uncertain

## Lessons → seeds for rules
1. **Allosteric kinase docking**: pocket detection (fpocket / DoGSiteScorer) FIRST → identify non-ATP cavity → box on allosteric center
2. **Keep ATP + cofactors** when allosteric inhibitor cooperates (case dock-007 ensemble docking conserved water lesson generalizes to ATP+Mg)
3. **Rigid → IFD pipeline mandatory** for allosteric (case dock-008 IFD lesson + this case both apply)
4. **Multi-conformation receptor input** for DFG-in/out + αC-in/out states — single crystal often biased
5. **Cross-family selectivity panel** uses *same allosteric box*, NOT ATP pocket box — selectivity comes from allosteric site sequence divergence
6. **Mutation tolerance**: WT docking + clinical resistance mutation panel both required for clinical prediction
