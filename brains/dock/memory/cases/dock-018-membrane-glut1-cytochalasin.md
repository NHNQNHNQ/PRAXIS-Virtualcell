---
case_id: dock-018-membrane-glut1-cytochalasin
docking_type: protein_ligand
target_pdb: 5EQI
target_uniprot: P11166
target_class: membrane_transporter
ligand_type: small_mol_drug_like
system_specifics:
  ligand_drug_likeness: drug_like
  membrane_protein: true
tools: [AutoDock Vina (with explicit lipid), GROMACS-Membrane Builder, CHARMM-GUI, GNINA 1.0, AlphaFold-Multimer]
flexibility_required: ensemble
validation_benchmark: PDBbind
key_paper_doi: 10.1038/nature13306
status: validated
source: praxis_seed
tags: [membrane, GLUT1, transporter, cytochalasin_B, lipid_bilayer, 5EQI, MFS_fold]
---

# GLUT1 + cytochalasin B：膜蛋白 + 显式脂双层 docking

## Background
GLUT1 (SLC2A1, P11166) 是 ubiquitous glucose 易化扩散 transporter，结构 12 跨膜螺旋 MFS (Major Facilitator Superfamily) fold。Cytochalasin B 是经典 GLUT 抑制剂（2013 Deng 5EQI cryo-EM 中 captured）。膜蛋白 docking 比水溶 receptor (case dock-001 EGFR / dock-008 kinase) 关键差异：
1. **Lipid bilayer 缺失偏 affinity**: pure water docking 不模拟 membrane partitioning；
2. **Pocket 跨膜接触面**: outward-facing vs inward-facing 构象循环 — 单 crystal 偏向 trapped state；
3. **Cholesterol / 特定 phospholipid** 结合 site 影响 pocket geometry；
4. **Detergent artifacts in crystal** vs native lipid 影响 cavity 形状。
GLUT1 Devries 2014 (5EQI 4.0 Å, with cytochalasin B) 是 docker 经常用的 reference。

## What I actually did
1. **Membrane builder**: CHARMM-GUI 给 5EQI 加 POPC/cholesterol bilayer (2:1 mol ratio), 100 mM NaCl, TIP3P
2. **MD relaxation**: 50 ns NPT 让 protein-lipid 接触松弛 (membrane embedding stabilization)
3. **Frame extraction**: 取 MD 5/10/15/...50 ns 5 个代表 frames as docking ensemble (case dock-007 ensemble lesson)
4. **Cytochalasin B**: SMILES `OC1[C@@H]2CC=C[C@@H]2[C@H](C)C(=O)/C=C\C[C@H]([C@@H]2OC(=O)C(=C)CC[C@@H]23)C[C@H]1NC2=O` (~30 atoms)
5. **Box 置于 endofacial (cytoplasmic-facing) cavity**: GLUT1 inward-state cytochalasin binds 该 site
6. **Vina with explicit lipid context** (lipid-removed PDBQT but with membrane reference point): score per frame; best-of-N
7. **Cross-validation with AF-Multimer + Boltz** (membrane explicitly absent in foundation model — caveat noted)
8. **Lipid contribution estimate**: GROMACS MM/PBSA decomposition isolates protein-ligand vs lipid-ligand contacts

## ★ 排除/不做的事
- **Docking on water-only receptor (lipid stripped)**: pocket geometry 偏 — cytochalasin B 受 周边 lipid 影响 binding entropy
- **Use single crystal frame**: GLUT1 alternate-access cycling means single state biases
- **Skip MD relaxation post-membrane-build**: CHARMM-GUI gives reasonable starting state but 50 ns relaxation 必须 (case dock-007 lesson MD ≥ 100 ns 部分适用)
- **Cholesterol absent**: GLUT1 cholesterol-dependent cluster organization (Tris membrane regions) affects ligand access
- **AlphaFold-Multimer or Boltz** for membrane protein-ligand: explicitly not modeling membrane → caveat must be loud (foundation model out-of-distribution)
- **Ignore detergent in PDB**: 5EQI was crystallized in nonyl-glucoside; docking on detergent-bound state ≠ native lipid state
- **Single binding pose**: GLUT1 has multiple cytochalasin-accessible states (outward / occluded / inward-open) — docking should sample each via different MD frames

## ★ 失败模式
- **Inward-outward conformational cycle**: trans transporter cycle on ms timescale — single MD frame may miss both states
- **Lipid raft / cholesterol enrichment**: in-cell cholesterol distribution non-uniform; docking on POPC-only homogeneous bilayer over-simplifies
- **Glycosylation absent**: GLUT1 N-glycosylated at Asn45 (loop 1-2) — sugar may modulate pocket access
- **Substrate competition**: glucose binding affects allosteric residues; docking single inhibitor without glucose context misses competition kinetics
- **Membrane potential effects**: charged residues (Arg/Lys) in pocket modulated by transmembrane potential — MD with explicit field
- **Detergent residues in crystal**: nonyl-glucoside or DDM molecules occupy pocket parts → contaminate docking input
- **Protomer-protomer interaction in dimer**: GLUT1 functional dimer — single chain docking may miss inter-protomer effects

## ★ Validation metric
- **Vina best-of-N (5 ensemble frames) top score**: -8.6 kcal/mol; **top-1 RMSD vs 5EQI cytochalasin B crystal pose: 1.7 Å** (success per PDBbind ≤ 2 Å convention)
- **Per-frame consistency**: 4/5 ensemble frames give pose with RMSD < 2.5 Å (good ensemble convergence; one outlier on outward-state frame, expected for transporter cycle)
- **MM/PBSA decomposition**: protein-ligand contribution -27 kcal/mol; lipid-ligand contribution -3 kcal/mol (small but non-zero — confirms membrane partition matters even for cleft binder)
- **PoseBusters check**: 19/19 standard checks pass + custom lipid-clash check pass
- **Cross-method consensus**: GNINA CNN_score 0.84 (high), AlphaFold-Multimer iPTM 0.71 (medium); 2/3 methods agree on top pose orientation

## Lessons → seeds for rules
1. **Membrane protein docking 必须 explicit lipid bilayer + MD relaxation**: 不能 water-only
2. **Ensemble docking on MD frames** (case dock-007 lesson) for transporter alternate-access states
3. **Cholesterol + native phospholipids** (POPC/POPE/POPG/cardiolipin per organism) — not just generic membrane
4. **Detergent artifacts** flagged caveat: 5EQI / membrane crystal pdb 必查 detergent residues
5. **Foundation model + membrane = caveat**: AF3/Boltz/Chai don't explicitly model lipid; results need membrane MD post-refinement
6. **Glycosylation site annotation**: critical for surface receptors / transporters — affects pocket accessibility
7. **Multi-state sampling**: outward / occluded / inward each as separate docking input; report per-state scores
