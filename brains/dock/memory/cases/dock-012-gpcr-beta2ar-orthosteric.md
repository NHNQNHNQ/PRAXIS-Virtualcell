---
case_id: dock-012-gpcr-beta2ar-orthosteric
docking_type: protein_ligand
target_pdb: 2RH1
target_uniprot: P07550
target_class: GPCR
ligand_type: small_mol_drug_like
system_specifics:
  ligand_drug_likeness: drug_like
tools: [AutoDock Vina 1.2.5, GOLD, Glide SP, GNINA 1.0]
flexibility_required: sidechain_flex
validation_benchmark: PDBbind
key_paper_doi: 10.1126/science.1150577
status: validated
source: praxis_seed
tags: [PL, GPCR, beta2AR, carazolol, orthosteric, 2RH1, transmembrane]
---

# β2-AR + carazolol：GPCR orthosteric docking 的特殊性

## Background
G-protein-coupled receptors (GPCR) 占人类基因组 ~3% + 占 30%+ FDA 批准药靶；docking 特殊性：
(1) **Transmembrane bundle 7 helices** — 与水溶性 kinase/protease pocket 几何完全不同；
(2) **Active vs inactive state**: agonist vs antagonist 触发不同 conformations，不能用 wrong-state structure；
(3) **Sodium binding site** (D2.50 pocket) — allosteric water-coordinated Na+ 影响 inverse agonist binding；
(4) **Lipid bilayer 缺失** — water-only docking under-counts membrane partitioning。
β2-AR (P07550) + carazolol (inverse agonist) 在 2RH1 (Cherezov 2007 Science) 是 GPCR docking 的金标准 case。

## What I actually did
1. **Receptor prep**: 2RH1 — T4 lysozyme fusion 移除 (T4L 代替 ICL3)；保留 4 个 conserved water (D2.50 sodium-pocket water + Asp113 water-bridge); Reduce 加 H pH 7.4
2. **Side-chain flex**: 7 个关键残基 (Asp113, Tyr308, Trp286, Phe289, Phe290, Asn312, Tyr316) — Vina `--flexres` 模式（IFD 的轻量替代）
3. **Ligand prep**: carazolol enum tautomer (β-blocker secondary amine; 不同 protonation @ pH 7.4 影响 Asp113 H-bond)
4. **Box**: 18×18×18 Å (orthosteric pocket smaller than ATP pocket; 22³ 太大易飘到细胞外 vestibule)
5. **Multi-method consensus**: Vina + GOLD + Glide SP — 3 个 docker top-1 pose RMSD < 2 Å vs 2RH1 crystal (consensus high)
6. **Reverse docking validation**: 把 carazolol 也 dock 到 5HT2A / D2R 等 同源 GPCR — selectivity ranking 与文献一致

## ★ 排除/不做的事
- **用 active-state β2-AR (3SN6 with G-protein)** docking antagonist: 强 conformational coupling — antagonist 通常 docking 到 inactive state (2RH1)，agonist 才 dock active
- **删 D2.50 Na+ binding site water**: ~50% allosteric inverse agonist 性质来自此水网络
- **Box 太大涵盖 extracellular vestibule**: GPCR 有 secondary binding site 在 EC loop → blind 大 box 会找到非 orthosteric pose
- **用 homology model GPCR (no crystal)**: GPCR homology model TM6/TM5 几何变化大；除非 sequence identity > 50% 否则信任度低
- **不显式建模 cholesterol binding sites**: β2-AR 有 CCM (cholesterol consensus motif) 在 TM4，影响 thermostability；docking 单蛋白 mode 不含
- **跨态推断**: inactive crystal docking → 不能直接预测 in-cell signaling efficacy (G-protein coupling)

## ★ 失败模式
- **Lipid 缺失 → 偏亲水分子假高 score**: 真实 in-membrane partitioning 影响 affinity，docking 单独算 aqueous binding
- **TM6 outward movement (active state)**: 与 inactive crystal docking 偏差 ~14 Å (TM6 cytoplasmic end)
- **Ligand-induced TM6 rotation**: agonist binding 触发 TM6 旋转 ~6° + outward 14 Å — rigid IFD 预测不到
- **Conformational selection**: GPCR 在生理状态下 visit inactive/intermediate/active states; 单 crystal docking 偏向 trapped state
- **Allosteric modulators**: BPTU (DCB-3503) 等结合 TM 外侧 lipid-facing site — orthosteric box 漏掉
- **G-protein binding-site water**: active state cytoplasmic Gα binding pocket water 网络不能 reuse from inactive

## Lessons → seeds for rules
1. **GPCR docking 必须 state-match**: antagonist→inactive crystal; agonist→active crystal; 不可混用
2. **Conserved water 强制保留**: D2.50 Na+ pocket water + Asp113 hinge water (β2-AR specific) — 文献证据驱动 (case dock-007 ensemble docking 通用启发)
3. **Box 18×18×18 GPCR-specific** (case dock-001 默认 22³ 不适用)
4. **Lipid 缺失 caveat 必报**: confidence -1 grade for membrane proteins
5. **Ensemble docking + apo MD ≥ 200 ns** for GPCR conformational sampling (case dock-007 lesson + GPCR specific upgrade)
6. **TM helix bundle outward movement → ensemble; back-pocket water → IFD; both → MD-driven cluster**: hierarchy of correction levels
