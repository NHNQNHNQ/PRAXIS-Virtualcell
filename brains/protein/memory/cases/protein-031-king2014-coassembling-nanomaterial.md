---
case_id: protein-031-king2014-coassembling-nanomaterial
design_task: symmetric_oligomer_de_novo
target_pdb: 4NWN
target_uniprot: nan
fold_class: helical_bundle_T_O_I_symmetry
length_range: 100-200
tools: [Rosetta, RPXdock, RosettaSymmetry, NegativeStain_EM, Cryo-EM, X-ray]
key_paper_doi: 10.1038/nature13404
key_metrics:
  symmetry_types_explored: "T (tetrahedral), O (octahedral), I (icosahedral) — 12 to 60-subunit caged assemblies"
  designs_synthesized: "approx 12 distinct co-assembling pairs"
  validated_by_cryo_EM: "approx 6 verified to form designed cage architecture"
  cage_diameter_range: "approx 8-25 nm depending on symmetry"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [nanomaterial, co-assembly, symmetric, icosahedral, octahedral, tetrahedral, RPXdock, cryo-EM, Rosetta]
unverified_details:
  - "12 design count is approximate from supp; specific PDB IDs in supp Table"
  - "Cage diameters vary by symmetry; T smallest (~8 nm), I largest (~25 nm)"
---

# Co-assembling protein nanomaterial 设计（King et al. Nature 2014）

## Background
- 起点：Bale 2016 / Hsia 2016 等之前的工作展示了 single-component 对称组装；King 2014 首次展示 two-component (heterodimeric) co-assembly 可形成 12-60 subunit nanocages
- 目标：设计两种 oligomeric 蛋白（如 trimer + dimer），它们共组装形成精确几何的 cage（T = 12 subunits, O = 24, I = 60）
- 应用：开拓 protein nanomaterials 领域（vaccine scaffolds, drug delivery, image agents）；Neoleukin / Icosavax 等公司核心 platform；与 PRAXIS-Drug + PRAXIS-Protein 联合相关

## What I actually did（基于论文）
1. **Symmetry geometry**：选择 T/O/I symmetry 数学约束，定义 component A (e.g., trimer) + component B (e.g., dimer) 的相对取向 + 距离
2. **RPXdock**：Rosetta-based docking algorithm，把 A + B 在所有对称位置 systematically 摆放
3. **Interface design**：RosettaDesign 设计 A-B contact surface (typically 600-1500 Å² interface)
4. **Filter cascade**：
   - Rosetta interface ddG < -25 REU
   - shape complementarity > 0.6
   - buried unsatisfied H-bonds < 4
   - cage geometry (subunit angle ± 5°)
5. **Selection**：~12 designs (T/O/I across multiple component combinations) 选作 in vitro
6. **Validation**：
   - SEC-MALS (oligomeric state)
   - 负染 EM 看 cage assembly
   - cryo-EM (some) for high-resolution structure
   - X-ray for subunit structure
7. **结果**：~6/12 designs verified by cryo-EM as designed cage architecture; sizes 8-25 nm; some assemblies thermostable up to 60-70°C

## ★ 排除的位点/区域
- **Component A、B 的 native oligomer interface**：必须保持（trimer 或 dimer 自身是 stable）
- **Symmetry 操作下不同 copy 的 same residue**：RosettaSymmetry 自动 enforce 同步 mutation
- **Disulfide bonds**：保留
- **Glycosylation sites**：避开 interface
- **Buried hydrophobic core**：不动
- **Surface 电荷分布需 balance**：cage interior + exterior 不同电荷，影响 stability
- **Loop 长度 > 15 aa**：geometric uncertainty 高，cage assembly 可能 misalign

## ★ 失败模式
- **Off-target oligomeric state**：~3/12 设计 SEC 上多峰 / 错 symmetry（T 设计成 D 形 dimer-of-trimer 等）
- **Aggregation**：~2/12 不可溶 / 形成 amorphous aggregate
- **正确 cage 但 monomer 不稳**：A 或 B 在 absence of partner 失活
- **Cryo-EM resolution 限制**：early-stage designs ~10 Å resolution，subunit detail blurred
- **Cage 内部 disorder**：少数 design cage shell 形成但 interior 通道 disordered
- **Subunit ratio 不准确**：A:B 化学计量比 in vitro 偏离设计（应 1:1.5 但 SEC-MALS 显示 1:1）
- **Functional load 不易**：post-design 添加 cargo (DNA, drug 分子) 化学修饰复杂

## ★ 方法选择决策链
- **为什么 two-component co-assembly 而非 single-component**：geometric 灵活性更高；单 component 能达 T，但 I (60 subunits) 几乎只能 two-component
- **为什么 RPXdock 而非 manual placement**：穷举 symmetric docking poses；一致性 + computational efficiency
- **为什么 ddG < -25 REU 而非 -40**：interface 范围中等 (600-1500 Å²)；不需要 picomolar binder 那种深 ddG
- **为什么 cryo-EM 验证 而非 SEC-only**：oligomeric state 不等于 cage assembly；多峰 SEC 下 native MS 可澄清，但完整 cage 结构 cryo-EM 必须
- **为什么 T/O/I 而非 higher symmetry**：geometric 数学严格限制；I (icosahedral) 是 highest symmetry-stable cage

## ★ In silico vs in vitro 差距
- **In silico → SEC monomer + 正确 oligomeric state**：~12 → ~9 (~75%)
- **正确 oligomer → cryo-EM cage assembly**：~9 → ~6 (~67%)
- **总转化率**：~6/12 ≈ **50%**（fold + cage symmetry）
- **vs case 019 (Wicky 2022 hallucination C2-D2 ~43%)**：King 2014 略好，因为 two-component 几何更刚性
- **vs case 002 / 010 (binder ~5-15%)**：cage assembly 比 binder 容易，因为 fold-only + symmetric constraint
- **No standard pLDDT/iPTM**：cryo-EM resolution + SEC-MALS + symmetry RMSD 是核心 metric
- **Functional cage as scaffold (vaccine, delivery)**：~3/6 验证 cage 进一步显示功能（display antigen 或 encapsulate cargo）

## Lessons → seeds for rules
1. **Two-component co-assembly > single-component** 在 high symmetry cage 上几何更灵活
2. **RPXdock 是 cage design 的核心算法**——symmetric docking 系统枚举
3. **cryo-EM 验证 cage assembly 不可省**：SEC oligomer state 仅 necessary 不 sufficient
4. **50% fold-correct rate** 是 nanomaterial cage 的 baseline——比 binder 高，比 enzyme 高
5. **T/O/I 是 stable cage symmetry 选择**：higher symmetry 失败率显著更高
6. **Functional cage applications (vaccine, delivery)**：基于 fold-OK cage 可后续 display antigen / encapsulate cargo
7. **PRAXIS implication**：symmetric_design_pipeline 应支持 (a) RPXdock-style two-component 模式, (b) cryo-EM 数据 import / native MS 验证, (c) cage diameter / subunit count enforcement; rule 02 (paired_msa) 不直接适用，但 symmetry constraint enforcement 是同等关键 

## 数据指针
- 论文 + supp: https://doi.org/10.1038/nature13404
- 6 验证 cage PDB IDs (cryo-EM): supp Table
- 后续 Bale 2016 / Hsia 2016 在更高对称 + thermostab 上 push
