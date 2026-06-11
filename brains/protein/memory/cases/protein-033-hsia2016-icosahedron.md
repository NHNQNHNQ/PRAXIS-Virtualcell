---
case_id: protein-033-hsia2016-icosahedron
design_task: symmetric_oligomer_de_novo
target_pdb: 5KP9
target_uniprot: nan
fold_class: icosahedral_60_subunit
length_range: 100-200
tools: [Rosetta, RPXdock, RosettaSymmetry, X-ray, cryo-EM, native_MS]
key_paper_doi: 10.1038/nature18010
key_metrics:
  designs_synthesized: "approx 7 icosahedral I3 designs"
  validated_60_subunit_assembly: "approx 5 verified by X-ray + native MS"
  Tm_top_design: ">100 degC (no measurable melting up to instrument limit)"
  diameter: "approx 25 nm icosahedral cage"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [nanocage, icosahedral, 60-subunit, hyperstable, Rosetta, X-ray, single-component]
unverified_details:
  - "Specific Tm > 100 degC is paper-claimed; 'no measurable melting' to limit"
  - "5/7 verified is approximate from supp"
---

# Hyperstable 60-subunit icosahedral protein nanocage（Hsia et al. Nature 2016）

## Background
- 起点：King 2014 (case 031) 展示 two-component co-assembly 形成 cages；single-component icosahedral (60 identical subunits) 是更难任务
- 目标：从单一 protein 设计 60-subunit icosahedral cage——这种自然界中天然 viral capsid 的对称组合，computational design 复刻
- 应用：与 King 2014 互补；single-component 简化 expression + scalability；Icosavax 等 vaccine cage platform；与 Bale 2016 同期 SOTA

## What I actually did（基于论文）
1. **Symmetry geometry**：I3 (icosahedral, 3-fold axis aligned) symmetry — 每 subunit 出现 60 次形成 icosahedron
2. **Scaffold pool**：trimer-forming Baker lab mini-protein scaffold 库
3. **RPXdock symmetric**：在 icosahedral symmetry 下扫描 trimer 之间的 inter-trimer interface
4. **Interface design**：RosettaDesign with symmetric mode（所有 60 subunit 同 sequence）
5. **Filter cascade**：
   - Rosetta interface ddG < -25 REU
   - shape complementarity > 0.65
   - buried unsatisfied H-bonds < 4
   - RPXdock score
6. **Selection**：~7 designs 选作 in vitro
7. **Validation**：
   - SEC-MALS (60-subunit MW)
   - 负染 EM 看 cage shape
   - X-ray 高分辨率 (~3Å) 部分 design
   - 高温 / chemical denaturation 测稳定性
8. **结果**：~5 designs 形成正确 icosahedral 60-subunit cage；diameter ~25 nm；hyperstable (无 measurable melting up to >100°C)

## ★ 排除的位点/区域
- **Trimer 内部 interface**：维持自身 trimer formation
- **Symmetry 操作下不同 copy 的 same residue**：自动 enforce identical sequence (single-component)
- **Disulfide bonds**：保留
- **Hydrophobic core**：trimer + cage interior 都 packed
- **Flexible loops > 15 aa**：cage geometry 严格，loop 太长会 misalign
- **Surface 电荷**：cage 内部 / 外部不同电荷 environment；balance design
- **N-terminal / C-terminal**：通常用于 fuse fluorophore 或 antigen，design 中保留 free

## ★ 失败模式
- **Off-target oligomer**：~2/7 形成 dimer-of-trimer 或 hexamer-of-trimer 而非 cage
- **Aggregation**：少数完全不可溶
- **Native MS 显示部分 cage**：少数 design ~30-mer (incomplete cage formation)
- **X-ray 无 diffraction**：~3 design crystallization fail；只能 cryo-EM
- **Incomplete cage in solution**：开放 vs closed cage equilibrium 偏向 open form
- **Cage 内部 disorder**：5 个验证 cages 中 2 个 inner surface disordered (cryo-EM 看不清)
- **Functional cargo 待加**：本论文 fold-only；vaccine antigen / drug 后续 fuse

## ★ 方法选择决策链
- **为什么 single-component icosahedron 而非 two-component**：simpler stoichiometry + expression；但要求 trimer scaffold 必须 stable + interface tractable
- **为什么 I3 (icosahedral) 而非 I (full icosahedral)**：I3 的 3-fold axis aligned 设计简化；纯 I (5-fold) 在 single-component 上几何困难
- **为什么 trimer-based scaffold**：60-subunit cage = 20 trimers (T = 20 在 I3 下)；trimer 是 building block
- **为什么 ddG cutoff -25 REU**：icosahedral interface 数量大（每 subunit 接触 4-6 邻居），单 interface 不需 picomolar
- **为什么 X-ray + cryo-EM 双 validation**：X-ray 高分辨率 atomic detail (3Å)；cryo-EM 大 cage 整体 (10-30Å); 互补
- **为什么 hyperstable 是设计目标**：vaccine / nanomaterial 应用要 robustness；自然 viral capsid hyperstable 是基线

## ★ In silico vs in vitro 差距
- **In silico filter pass → SEC monomer + 正确 oligomer state**：~7 → ~6 (~85%)
- **正确 oligomer → 60-subunit cage by 负染 EM**：~6 → ~5 (~83%)
- **Cage → high-resolution X-ray / cryo-EM**：~5 → ~3 (~60%)
- **总转化率 (in silico → atomic-detail-validated cage)**：~3/7 ≈ **43%**
- **vs case 031 (King 2014 two-component)**：similar ~50% rate；single-component 略低但更 scalable
- **vs case 019 (Wicky 2022 hallucination)**：similar ~43% fold-correct
- **Tm > 100°C**：超出 standard DSF instrument 范围；多数 cage 在 chemical denaturation (6 M GdmCl) 仍 fold
- **No standard pLDDT/iPTM**：classical Rosetta period；metric 是 X-ray RMSD + native MS + cryo-EM resolution

## Lessons → seeds for rules
1. **Single-component icosahedron** 在 expression + scalability 上有优势
2. **Trimer-based scaffold + I3 symmetry** 是 60-subunit cage 的实用 sweet spot
3. **Hyperstability (Tm > 80°C) 是 nanomaterial 标准**：industrial cage 需 robustness
4. **X-ray + cryo-EM + native MS 三步验证**：cage assembly 多 modality 必要
5. **43% atomic-detail validation rate** 是 single-component icosahedron 的 SOTA baseline
6. **后续 RFdiffusion symmetric (Watson 2023, case 009) 用 deep learning 重做 single-component icosahedron**：design space 扩展但 in vitro 转化率类似
7. **PRAXIS implication**：symmetric_design_pipeline 应支持 (a) single + two-component modes, (b) icosahedral T/O/I 几何 enforcement, (c) X-ray + cryo-EM + native MS 验证步骤要求, (d) hyperstability filter

## 数据指针
- 论文 + supp: https://doi.org/10.1038/nature18010
- I3-01 PDB: 5KP9 (representative validated cage)
- 后续 Bale 2016 + RFdiffusion symmetric work 在更高对称 + de novo space 扩展
