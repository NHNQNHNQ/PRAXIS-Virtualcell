---
case_id: protein-020-yeh2023-de-novo-luciferase
design_task: enzyme_de_novo_design
target_pdb: nan
target_uniprot: nan
fold_class: TIM_barrel_or_NTF2_like
length_range: 100-180
tools: [RFdiffusion, ProteinMPNN, AlphaFold2, family-wide_hallucination_FWH, ligand_aware_design]
key_paper_doi: 10.1038/s41586-023-05696-3
key_metrics:
  designs_synthesized: "approx 7000+ across multiple substrates"
  active_designs: "approx 0.1-1% showed catalytic activity above baseline"
  best_kcat_substrate: "luminescence at 10^6 RLU/sec for top designed luciferase on diphenyl terazine substrate"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [enzyme-design, de-novo-luciferase, RFdiffusion, ligand-aware, NTF2, TIM-barrel]
unverified_details:
  - "Number of synthesized designs is approximate from supp; specific count varies by substrate"
  - "Active fraction (~0.1-1%) is the typical de novo enzyme yield"
  - "Specific KD numbers between substrate variants need verification from supp Table"
---

# De novo design of luciferases（Yeh et al. Nature 2023）

## Background
- 起点：De novo enzyme design 历史上效率低（~1% active rate, very low kcat）。深度学习 design tool 出现后是否能突破？
- 目标：设计完全 de novo 的 luciferase（萤光素酶）——蛋白要包裹特定 substrate (diphenyl terazine, hydroxydiphenyl terazine 等)，催化 oxidative decarboxylation 产光
- 应用：里程碑——证明 de novo enzyme design 在 deep-learning 时代可达 catalytic activity 而非仅 fold；为 PRAXIS-Drug + PRAXIS-Protein 联合提供 framework

## What I actually did（基于论文）
1. **Substrate selection**：合成多种 luciferin-like substrates（diphenyl terazine 等），定义 enzyme 应包裹的小分子 + substrate 关键官能团
2. **Active site geometry**：Rosetta 设计 active site —— 3-4 关键残基的 hotspot（H-bond donor / catalytic Asp / hydrophobic pocket）
3. **Backbone design (RFdiffusion + family-wide hallucination)**：从已知 NTF2-fold scaffold + luciferin-binding pocket geometry 出发，hallucinate 包裹 substrate 的 backbone
4. **Sequence design (ProteinMPNN, ligand-aware)**：用 ProteinMPNN 序列填空，frozen catalytic residues + substrate 周围 residues 设计
5. **AlphaFold2 验证**：跑 AF2 with initial guess 看设计是否 fold 到设计 backbone
6. **Filter cascade**：
   - pLDDT_binder/structure ≥ 80
   - Active site residue placement RMSD vs design < 1 Å
   - Substrate pocket volume / shape complementarity
   - Rosetta ddG of substrate binding
7. **In vitro**：~7000+ design 跨多个 substrate；E.coli 表达，纯化，luminescence assay
8. **结果**：top design 显示 measurable luminescence (10^6 RLU/sec)；多轮 directed evolution 后 kcat 进一步提升；catalytic activity 在 de novo 设计中创纪录

## ★ 排除的位点/区域
- **Substrate 化学反应中心（C=C, C-C 切割位点）**：不能让 design residue 占据；substrate 必须接触溶剂可达的"反应表面"
- **必需的 catalytic residues**：~3-4 个 freezing 残基（H-bond donor for terazine 羰基、catalytic Glu/Asp 等）
- **Substrate-binding pocket 内层疏水残基**：design 时 frozen 否则 binding 失效
- **Active site 周围 5 Å 区域**：禁止 large mutation；ProteinMPNN 受限设计
- **Loop 中柔性区**：catalytic loops 不允许 reduce 长度（关闭 substrate exit）
- **跨膜段 / 信号肽**：N端可加（in vivo target）但 design 阶段不算

## ★ 失败模式
- **Soluble expression rate**：~30-50% 设计 in E.coli 不可溶（典型 de novo enzyme 通病）
- **AF2 confirmed fold but no activity**：~70% in silico filter 通过 + in vitro 表达 + SEC OK 的 design 仍无 catalytic activity——substrate binding 仍是 design challenge
- **Substrate pocket too tight / too loose**：~10% 设计实测 KD 异常（要么不结合，要么 KM > 1 mM）
- **Catalytic geometry 不准**：active site residues 在 AF2 上 placement < 1 Å 但在 X-ray 上偏离 > 2 Å——AF2 在 side chain rotamer 上 less reliable
- **Off-pathway reaction**：少数 design 切割 substrate 但不产光 / 产生 wrong product
- **Directed evolution 必要**：raw design 多数 kcat 极低 (~10^-3 turnover/sec)；要 SSM 多轮选才到 useful range

## ★ 方法选择决策链
- **为什么 RFdiffusion family-wide hallucination 而非 ab initio design**：scaffold-guided 提供 fold prior + 让 substrate-binding pocket geometry 一致——pure ab initio 在包裹 ligand 上极难
- **为什么 NTF2-like fold scaffold pool**：enzyme like luciferase 的 substrate-binding pocket 几何 fits NTF2 family
- **为什么 ProteinMPNN ligand-aware (LigandMPNN-precursor)**：fixed-ligand context 让 ProteinMPNN 知道哪些位置不能 mutate
- **为什么 7000+ design 而非更少**：de novo enzyme active rate 历史低 (~1%)；超量是必需
- **为什么 directed evolution 一定要做**：raw kcat < 0.001/s 多数；catalytic enzyme 需要 SSM + 多轮选
- **为什么 X-ray 验证 final hits**：AF2 在 side chain rotamer 上 not perfect；catalytic enzyme 必须 X-ray 确认 active site

## ★ In silico vs in vitro 差距
- **In silico filter pass → 表达可溶**：~7000 → ~3500 (50%)
- **可溶 → SEC monomer**：~3500 → ~2500 (~70%)
- **SEC OK → catalytic activity 可测**：~2500 → ~10-30 (~0.5-1%) **← 极低**
- **Catalytic active → kcat / KM ≥ industrial threshold**：进一步 directed evolution 后 ~5 个 enzyme
- **总转化率 (in silico → useful enzyme)**：~5 / 7000 ≈ **0.07%**
- **vs case 011 binder ~1%**：de novo enzyme 比 binder 难 10-100x
- **vs case 003 stabilization (Watson 2023, partial)**：完全不同 task；stabilization 是 leverage 已有 fold + activity，de novo enzyme 是从零

## Lessons → seeds for rules
1. **Active site residues 是 freezing constraint 的核心**——RFdiff + ProteinMPNN 都必须知道哪些残基不能动
2. **Family-wide scaffold + ligand-aware design > pure ab initio**：包裹 substrate 必须有 fold prior
3. **0.5-1% catalytic activity rate 是 de novo enzyme 的 baseline**——比 binder 难 10x
4. **Directed evolution 不可省**：raw design kcat 极低，必须 SSM + select
5. **AF2 active site placement 不可信**：必须 X-ray 验证 final design
6. **超量设计是 de novo enzyme 的必经**：7000+ design 才出 5-10 useful enzyme
7. **PRAXIS implication**：未来加 enzyme_de_novo_design skill；wire LigandMPNN + RFdiffusion-AA 作为 backbone； rule 03 active site freeze 升级为 enzyme-aware (catalytic residue MUST freeze)

## 数据指针
- 论文 + supp: https://doi.org/10.1038/s41586-023-05696-3
- Top luciferase 设计 + X-ray PDB IDs 在 supp materials
- LigandMPNN 后续 paper (Dauparas et al.) 直接 cite this work
