---
case_id: drug-006-fbdd-vemurafenib
project_phase: hit_id_to_lead
target_uniprot: P15056 (B-Raf)
target_pdb: 3OG7 (B-Raf V600E with vemurafenib)
target_class: kinase
indication: melanoma_BRAF_V600E
modality: small_mol_inhibitor
hit_id_method: fragment_based_design
representative_compounds:
  - name: vemurafenib
    chembl_id: CHEMBL1229517   # corrected; original CHEMBL1336 was a different molecule (regorafenib-like)
    inchikey: GPXBXXGIAQBQNI-UHFFFAOYSA-N
    smiles: CCCS(=O)(=O)Nc1ccc(F)c(C(=O)c2c[nH]c3ncc(-c4ccc(Cl)cc4)cc23)c1F   # ChEMBL canonical (no F on chlorophenyl); IK GPXBXXGIAQBQNI-UHFFFAOYSA-N
  - name: 7-azaindole_fragment
    smiles: c1cc2[nH]ccc2cn1  # ~117 Da fragment hit
tools: [Schrödinger Glide (commercial), AutoDock Vina, RDKit, NMR (real wet lab)]
qa_notes:
  - "Original CHEMBL1336 was a completely different molecule. SMILES + computed InChIKey (GPXBXXGIAQBQNI-UHFFFAOYSA-N) is correct for vemurafenib; ChEMBL search by name confirmed CHEMBL1229517 as the authoritative ID."
key_paper_doi: 10.1038/nature05802
status: validated
validated: true
source: praxis_seed
---

# Vemurafenib FBDD：从 fragment hit 到 sub-nM 抑制剂的完整 pipeline

## Background
Plexxikon 用 fragment-based drug design (FBDD) 开发 vemurafenib：~20,000 fragment 库 → NMR/X-ray 筛 → 7-azaindole hit (KD ~150 μM) → fragment growing 5 步内 → vemurafenib (IC50 31 nM, B-Raf V600E)。是 FBDD 教科书 case，2002-2010 完成全程。

## What I actually did（in silico 复盘）
1. **Fragment library**：Astex/Plexxikon 类似公开 fragment 库 ~5000 化合物，Rule of 3（MW < 300, ≤ 3 HBA, ≤ 3 HBD, logP ≤ 3）
2. **Fragment screening in silico**：library 进 B-Raf ATP pocket（3OG7 prep）docking (Vina 高 exhaustiveness)，top 1% binders 识别
3. **Hot-spot 识别**：MD on apo B-Raf → 用 SiteMap / FTMap 识别 cryptic pocket / hot-spot
4. **7-azaindole** 在 hot-spot hinge region 形成 H-bond；下一步是 fragment growing 而非 fragment linking
5. **Growing strategy**：核心 scaffold 保留，逐次加 substituent → docking pose 检查 → ADMET evaluate
6. **关键决策**：B-Raf 与 C-Raf paralog selectivity 是 wet lab 拿到 X-ray 后才设计的（DFG-out vs DFG-in）
7. **Final**：vemurafenib 选 sulfonamide group 增 H-bond + halogen (F, Cl) 增 selectivity

## ★ 排除/不做的事
- **不做 fragment 阶段直接做 lead-like screening**：lead-like (MW 300-500) library 在弱 binder 淹没；fragment (MW < 300) 富集结合 hot-spot 的 ligand
- **Fragment 不验证物理结合**：纯 docking 无法证 fragment 真结合，必须 NMR/SPR/X-ray 实验确认
- **Growing 而非 linking 不分场景**：如果 2 个 fragment 在 pocket 不同位点 binding，linking 才合理；同一 hot-spot 应 grow
- **Selectivity 不在 fragment 阶段考虑**：fragment 太小本身无 selectivity；selectivity 在 lead optimization 阶段加
- **不用 X-ray confirmation**：纯 in silico growing 失败率极高；wet lab X-ray ground truth 是 FBDD 核心

## ★ 失败模式
- **Fragment hit rate 低**：典型 1-5%，500 fragment 库可能只有 5 个真 hit
- **Fragment 在 docking 假阳**：弱结合 (KD > 100 μM) 在 docking score 上区分度差，需 STD-NMR / WaterLOGSY 实验过滤
- **Cryptic pocket 错过**：apo 结构 pocket 不存在，holo 结构才显——fragment 库不会发现
- **Linker 设计陷阱**：两 fragment linking 时 linker 增 MW 但 strain energy 可能 + 5 kcal/mol，binding 反降
- **Selectivity vs paralog**：vemurafenib 早期版本 cross-react C-Raf；选 DFG-out 形态结合是关键
- **Resistance mutation**：V600E 反应好，但 V600K 不响应；FBDD 阶段不能预测

## Lessons → seeds for rules
1. **Fragment library Rule of 3** vs lead-like Rule of 5
2. **Fragment 物理验证强制**：纯 docking 不接受，需 SPR / NMR / X-ray
3. **Growing vs Linking 决策树**：同 hot-spot grow / 不同 hot-spot link
4. **Selectivity 在 lead-opt 阶段**，不在 fragment 阶段
5. **Cryptic pocket awareness**：apo 与 holo 结构都需要看
6. **Resistance mutation 在 design 时考虑**：mutation panel 在 lead-opt 阶段 docking
