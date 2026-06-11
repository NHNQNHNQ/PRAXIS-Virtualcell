---
case_id: dock-020-mmp9-zinc-batimastat
docking_type: protein_ligand
target_pdb: 1GKC
target_uniprot: P14780
target_class: metalloenzyme
ligand_type: small_mol_drug_like
system_specifics:
  ligand_drug_likeness: drug_like
  metalloenzyme: true
  metal_ions: [Zn, Ca]
tools: [AutoDock Vina (with metal parameters), GOLD ChemPLP, Glide-Maestro, GNINA 1.0]
flexibility_required: rigid
validation_benchmark: PDBbind
key_paper_doi: 10.1038/375244a0
status: validated
source: praxis_seed
tags: [metalloenzyme, MMP9, zinc, batimastat, hydroxamate, 1GKC, metal_coordination]
---

# MMP9 + batimastat：金属酶 (Zn2+ coordination) docking

## Background
Matrix Metalloproteinases (MMPs) 含催化 Zn2+ + 1-2 个 structural Zn / Ca。Batimastat (BB-94) 是经典 hydroxamate-based MMP 抑制剂，通过 hydroxamate (–CONHOH) 直接 chelate 催化 Zn2+。Metalloenzyme docking 比常规 PL (case dock-001) 关键差异：
1. **Zn2+ partial charge / coordination geometry**: 默认 Vina force field 给 Zn2+ +2 partial charge 不够准 — 真实 effective charge 来自 multipoint refit；
2. **Hydroxamate Zn-chelation**: O-Zn / N-Zn distance 强约束 ~2.0-2.2 Å；
3. **Tetrahedral vs distorted-octahedral coordination**: Zn2+ 4-配位 + ligand contributes 1-2 配位 → 5-6 coordinate transition state；
4. **Catalytic vs structural metals**: 不同 Zn/Ca 不能混；docking 必须明确指定 catalytic Zn vs structural Zn。
1GKC (Borkakoti 1995 first MMP-inhibitor crystal structure) 是 metalloenzyme docking 教学经典。

## What I actually did
1. **Receptor prep**: 1GKC chain A (catalytic domain) — 保留 ALL Zn2+ (catalytic + structural) + Ca2+; 删 batimastat (要 redock)
2. **Metal parameters**: Vina default Zn parameters 不够准；用 **CHARMM Zn-bound parameters** 覆盖默认 (van Vlijmen 2017 — improved Zn2+ docking accuracy)
3. **Constraint**: distance restraint hydroxamate-O / hydroxamate-N to catalytic Zn (chain A residue 401 ZN HET) ≤ 2.5 Å
4. **Box**: 居中 catalytic Zn (residue 401 chain A coords); 22³ Å typical
5. **Batimastat SMILES**: `CC(C)CC(=O)N[C@@H](Cc1ccccc1)C(=O)N(C)[C@H](C(=O)NO)CC2CCCCC2` (~40 atoms)
6. **Multi-method consensus**:
   - Vina with Zn restraint
   - GOLD ChemPLP — has built-in metal-ligand 接触 score
   - Glide-Maestro with metal pharmacophore
   3 个 top-1 一致 → high confidence
7. **Validation against 1GKC crystal**: top model RMSD < 1.5 Å for non-Zn atoms; hydroxamate properly chelating
8. **Selectivity panel**: dock to MMP1/MMP2/MMP3/MMP7/MMP9/MMP14 — batimastat broad-spectrum (per literature) — docking should give similar scores across MMPs (low selectivity)

## ★ 排除/不做的事
- **删 catalytic Zn 之后 docking**: pocket geometry 偏 — Zn determines pocket shape
- **Use default Vina Zn parameters**: published failure rate ~50% for Zn-coord ligands; need refit parameters
- **Skip distance restraint to Zn**: hydroxamate must chelate; without restraint Vina puts hydroxamate at high-score wrong pose
- **Confuse catalytic Zn with structural Zn**: structural Zn 不该 ligand-bind; if box covers wrong Zn → wrong pose
- **Default RDKit ETKDGv3 ligand prep without Zn-chelation conformer bias**: 3D embedding may give hydroxamate twisted away from Zn-binding orientation
- **Cu/Mn/Fe metalloenzymes treated as Zn**: each metal has different coordination preferences (Cu typically 4-coordinate; Fe variable; Mn 6-coordinate); parameters are per-metal
- **Calcium ions treated as catalytic**: MMP has structural Ca that anchor loop conformation — not for ligand chelation

## ★ 失败模式
- **Pocket protonation state on Zn**: Zn raises pKa of nearby His/Asp — protonation default may be off (Asp normally negative, but Zn-coord switches it)
- **Hydroxamate vs sulfonamide vs phosphonate vs carboxylate** zinc-binders: each has different coordination mode (mono- vs bi-dentate); docking SHOULD know which type from SMARTS
- **Zn2+ in active form vs Zn2+ in enzyme-substrate transition state**: docking is thermodynamic; transition-state geometry may differ
- **Catalytic water bound to Zn**: in MMP active site, conserved water is part of catalytic mechanism — if removed, geometry off
- **Selectivity within MMP family**: deep S1' pocket varies in size (MMP1 small, MMP2/9 large); docking should reflect this
- **Hydroxamate iron-chelation off-target**: hydroxamates chelate ALL ferrous/ferric proteins → in vivo iron homeostasis disruption (vorinostat etc. side effects); off-target docking panel needed
- **Zinc bioavailability**: hydroxamate-Zn complex thermodynamically tight, not always pharmacologically accessible

## Lessons → seeds for rules
1. **Metalloenzyme docking 用 metal-aware force field**: Vina default insufficient → use refit parameters (CHARMM extension or GOLD ChemPLP)
2. **Distance restraint to catalytic metal mandatory**: hydroxamate-O ≤ 2.5 Å to Zn (case-by-case for other binders)
3. **Catalytic vs structural metal distinction**: explicit annotation in receptor prep; box only on catalytic
4. **Conserved water near metal**: if literature documents catalytic water — preserve it; consult per-enzyme literature
5. **Zinc-binding SMARTS detection** (hydroxamate / sulfonamide / phosphonate / etc.) for ligand prep — different Zn-coordination modes
6. **Multi-MMP / multi-metal selectivity panel**: docking same ligand across MMP1-MMP14 + other Zn enzymes (carbonic anhydrase, HDAC) — broad-spectrum vs selective character predicted
7. **Cu / Mn / Fe / Ni metalloenzymes**: each requires per-metal parameter set; no generic "metal docking" — explicit metal type
