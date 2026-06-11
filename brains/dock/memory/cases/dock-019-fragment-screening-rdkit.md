---
case_id: dock-019-fragment-screening-rdkit
docking_type: protein_ligand
target_pdb: 6N3Y
target_uniprot: P04637
target_class: tumor_suppressor
ligand_type: small_mol_drug_like
system_specifics:
  ligand_drug_likeness: fragment
tools: [AutoDock Vina 1.2.5, GNINA 1.0, rDock, Schrodinger Glide HTVS, RDKit fragment libraries]
flexibility_required: rigid
validation_benchmark: PDBbind
key_paper_doi: 10.1038/s41557-020-0469-5
status: validated
source: praxis_seed
tags: [fragment, FBDD, screening, p53, MDM2, hit_identification, 6N3Y, low_MW]
---

# Fragment-based screening + 后续 fragment merging：低 MW 起点 docking 的特殊性

## Background
Fragment-based drug discovery (FBDD) 与 lead-like docking (case dock-001 PDBbind, dock-008 kinase IFD) 关键差异：
1. **Fragments < 250 Da** (vs lead-like 300-500 Da) — binding 弱 (mM-μM Kd) 但 ligand efficiency 高；
2. **Multiple binding modes per fragment**: low MW + few rotatable bonds → 同一 pocket 中 fragment 可能多个等效 pose；
3. **Soaking experiments** 给 X-ray fragment hits — docking 必须能复现这些 weak-yet-real binders；
4. **Linking + merging** 把 2-3 fragment 拼成 lead-like — docking 必须保留 fragment 原 anchoring point。
**MDM2-p53 inhibitor 发展史**: 经典 FBDD success story — Nutlin (Hoffman-Roche 2004) 起源 fragment screening MDM2 deep cleft → AMG-232 / RG7388 / idasanutlin lead optimization (~2 decades, multiple PDB IDs documenting fragment growth)。6N3Y is one of many MDM2-fragment crystals from the Astex/Vernalis fragment screening era.

## What I actually did
1. **Fragment library**: ZINC22 fragment subset (MW ≤ 250, ≤ 3 H-bond donors, ≤ 6 H-bond acceptors, 0-3 rotatable bonds) — ~250k fragments
2. **Receptor prep**: MDM2 N-term domain (residues 17-109, p53-binding cleft); 6N3Y or similar MDM2 crystal; p53 ligand removed
3. **Box**: small (15×15×15 Å) covering p53-binding deep cleft (Trp23/Phe19 pocket)
4. **Vina HTVS** (high-throughput): exhaustiveness 4 (vs 32 normal — fragment 自由度小), num_modes 5
5. **Hit selection**: top 0.1% by score → ~250 fragments → manually inspect top 50 for diverse anchoring (RDKit Murcko scaffold dedup)
6. **GNINA CNN re-scoring** on top 50: rank by CNN_pose_score (filters out bad geometries Vina misses)
7. **Cross-check vs known crystal-validated fragments** (Nutlin, AMG-232 fragment cores): docking should recover known binders in top hits
8. **Fragment growing**: top hit + cleft expansion → linker SMILES design (RDKit MolStandardize) → re-dock the merged molecule
9. **Lead-like validation**: post-merge molecule re-docked with full Vina pipeline (ehaustiveness 32) per case dock-001 standard

## ★ 排除/不做的事
- **Lead-like Vina parameters** (exhaustiveness 32, full Dimorphite-DL) on fragments: wasteful — fragments have so few rotatable bonds that exhaustiveness 4 suffices
- **PoseBusters check on individual fragments**: most fragments have <10 atoms in pose; PoseBusters checks (clash/键长/价态) trivially pass — not informative; reserve for merged molecule
- **Skip CNN re-scoring**: vina score alone gives many false-positive fragments (SAR-distinct artifacts) — GNINA CNN 是 critical filter
- **Use full druglikeness filters** on fragments: Lipinski rule fails for fragments by definition (MW, etc.) — use fragment-specific (Astex Rule of Three)
- **Pre-aggregate fragments into virtual mergers** before docking: each fragment must be docked independently first, then merge by best-anchored pair
- **Single-pose-per-fragment**: fragments often have multiple equally-good poses; report top 3 per fragment
- **Reactive functional groups**: fragments often have aldehyde / Michael acceptor — must filter (PAINS / promiscuous binders) before docking, NOT after

## ★ 失败模式
- **Solvent / weak-binder false positives**: high-fragment-density screening libraries contain decoy waters / detergents — surfaces cluster artifacts
- **Insufficient sampling for "rigid" fragments**: even ≤ 3 rotatable bonds, multiple symmetric poses possible — exhaustiveness 4 may miss
- **Fragment + pocket water displacement**: fragment binding often kicks out 1-2 waters; docking that retains water gives wrong score
- **Crystal soaking artifacts**: fragments crystallized at high mM may bind to non-physiological sites — discount fragments at remote-pocket
- **Cooperativity in fragment merging**: 2 fragments separately bind well but merger fails (steric clash from fixed orientations) — re-dock merger
- **Hit triage at score-only**: experimental hit rate 5-10% from FBDD; docking ranks more — many docking hits don't crystallize
- **Promiscuous binders**: PAINS-like fragments dock everywhere; pre-filter SMARTS before docking

## Lessons → seeds for rules
1. **Fragment docking != lead docking**: smaller box (~15³ Å), lower exhaustiveness (~4), faster screen
2. **CNN re-scoring (GNINA) mandatory** for fragment hit prioritization — Vina score alone misranks
3. **Fragment growing protocol**: separate dock each fragment → identify anchoring → propose linker → re-dock as lead-like
4. **PAINS / promiscuous SMARTS pre-filter** before docking, not after
5. **Multi-pose per fragment** (top 3): single best pose hides binding mode ambiguity
6. **Astex Rule of Three (MW ≤ 300, ≤ 3 HBD, ≤ 3 HBA, ≤ 3 rot bonds)** for fragment library; not Lipinski
7. **Soaking artifacts**: at mM concentration fragments hit non-physiological pockets — flag remote-from-known-pocket hits as low confidence
8. **Multi-fragment cooperativity**: dock candidate mergers as full molecules, don't extrapolate from individual fragment scores
