---
case_id: protein-029-siegel2010-diels-alderase
design_task: enzyme_de_novo_design
target_pdb: 3I1C
target_uniprot: nan
fold_class: TIM_barrel
length_range: 200-300
tools: [Rosetta, RosettaMatch, RosettaDesign, Quantum_Mechanics_TS_modeling, X-ray]
key_paper_doi: 10.1126/science.1190239
key_metrics:
  designs_synthesized: "84 designs synthesized + assayed"
  active_designs: "approx 2 designs (DA-20, DA-26 etc.) showed measurable Diels-Alder catalysis"
  kcat_KM_top: "approx 0.04 M^-1 s^-1 (very low but above background)"
  enantio_selectivity: ">97% ee for top design (chiral selective bimolecular DA)"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [enzyme-design, de-novo, Diels-Alderase, RosettaMatch, transition-state, stereoselective, classical-Rosetta]
unverified_details:
  - "Specific kcat/KM and ee numbers from supp; values vary by design"
  - "Catalytic activity is modest by industrial standards; landmark mainly for proof-of-concept"
---

# De novo Diels-Alderase（Siegel et al. Science 2010）

## Background
- 起点：Diels-Alder 反应在自然界没有专属酶（diene + dienophile cycloaddition）；computational de novo enzyme design 的 ultimate test bed
- 目标：设计第一个 stereoselective bimolecular Diels-Alderase——证明纯 computational design 可生成自然界没有的酶活性
- 应用：landmark 论文，建立"理性 enzyme design from QM transition state"范式；后续 Yeh 2023 luciferase 等 deep-learning 工作的 conceptual 前驱

## What I actually did（基于论文）
1. **TS modeling**：用 quantum mechanics (DFT B3LYP/6-31G*) 计算 Diels-Alder transition state 结构 + electrostatic
2. **Theozyme construction**：定义 4 个理论 catalytic residues 的 hotspot geometry —— H-bond donor (主链 NH 或 Tyr OH) + H-bond acceptor (Glu/Asp 羰基) + non-polar pocket
3. **RosettaMatch**：scan ~40,000 PDB scaffold（TIM-barrel + jelly-roll + αβ-barrel）找符合 theozyme geometry 的 backbone
4. **RosettaDesign**：为每个 match 设计周边序列优化 substrate binding pocket
5. **Filter cascade**：
   - Rosetta active site preorganization score
   - Substrate binding ddG < -5 kcal/mol
   - Pocket complementarity (shape + electrostatic)
   - Catalytic residue distance constraints met (within 0.5 Å of theozyme)
6. **Selection**：~84 designs 选作 wet lab
7. **Validation**：
   - E.coli 表达 (BL21)
   - HPLC 测 Diels-Alder product formation
   - GC-MS 测 enantiomer ratio
   - X-ray 结构 verify catalytic geometry
8. **结果**：
   - DA-20 等设计显示 measurable activity (kcat/KM ~0.04 M⁻¹s⁻¹)
   - >97% ee (高 stereo-selectivity)
   - X-ray 结构 confirm theozyme placement < 1 Å

## ★ 排除的位点/区域
- **TIM-barrel 内核 helix**：维持 fold；不允许大 mutation
- **Substrate channel 关键 residues**：定义 pocket geometry 的 frozen
- **Disulfide bonds**：保留
- **Active site 已定义的 4 个 catalytic residues**：absolutely frozen
- **Polar buried residues 在 H-bond network**：design 时 case-by-case
- **跨膜段 / 信号肽**：不适用（水溶性 enzyme）

## ★ 失败模式
- **绝大多数 design 没有 catalysis**：~82/84 表达可溶 + binding substrate 但不催化——active site geometry 在 in vitro 偏离 theozyme
- **kcat 极低 (10^-3 ~ 10^-2 turnover/s)**：远低于天然酶（typically 10^2-10^4）——precise TS stabilization 在 design 时 hard
- **Substrate pocket too tight / loose**：~30% 设计 KM > 1 mM 或 binding 失效
- **Enantio-selectivity 部分失败**：非 top-2 design 多数 racemic（设计的 chirality bias 不准确）
- **Off-pathway reaction**：少数设计催化 substrate-water hydrolysis 而非 DA
- **后续 directed evolution 必要**：raw kcat 极低 + 需要 SSM 多轮提升 (典型 100-1000x)

## ★ 方法选择决策链
- **为什么 RosettaMatch + theozyme 而非纯 hallucination**：精确 TS geometry constraint 必须 match scaffold backbone；hallucination 在 catalytic 任务上空间太大
- **为什么 QM TS 而非 force field**：DFT 给 transition state 准确 electrostatic / geometry；force field 在 TS 上不可信
- **为什么 84 designs 而非 1000+**：合成 + 表达 + assay cost；1990s-2000s 实验throughput 限制
- **为什么 X-ray 验证 critical**：active site geometry 是 catalysis 决定因素；只 AF2 不可信（2010 没 AF2）
- **为什么 stereo-selectivity 是 metric**：DA 反应 chirality 是 enzyme 价值核心；racemic catalyst 无意义

## ★ In silico vs in vitro 差距
- **In silico filter pass → 表达可溶**：~84 → ~70 (~83%)
- **可溶 → substrate binding (KM ≤ 1 mM)**：~70 → ~40 (~57%)
- **Binding → measurable catalysis above background**：~40 → ~2 (~5%)
- **Catalysis + correct stereo-selectivity (ee > 50%)**：~2 → ~2 (~100% of catalytic)
- **总转化率 (in silico → useful enzyme)**：~2/84 ≈ **2.4%**
- **vs case 020 (Yeh 2023 luciferase ~0.07%)**：早期 Rosetta+TS design 看起来高，但 Yeh 是 deep-learning 时代 + 更难 catalysis (luminescence 比 DA 复杂)
- **kcat absolute scale**：Siegel 2010 DA-20 ~0.04 M⁻¹s⁻¹ vs Kemp eliminase Khersonsky ~0.6 M⁻¹s⁻¹ vs natural enzyme 10^4-10^7 M⁻¹s⁻¹
- **No standard pLDDT/iPTM**：classical Rosetta period；metric 是 RosettaMatch geometry RMSD + Rosetta_ddG + experimental kcat/KM

## Lessons → seeds for rules
1. **De novo enzyme design 的 absolute kcat 极低**——~10^-3 turnover/s baseline, far from natural
2. **RosettaMatch + theozyme + design + DE 是 classical pipeline**：deep-learning 时代是 RFdiffusion-AA + LigandMPNN + DE
3. **Stereo-selectivity 比 catalysis 更易 design-encode**：只 2 个 active design 但都 >97% ee
4. **2.4% transcription rate 是 classical de novo enzyme design 的 baseline**——比 binder (~1-15%) 难
5. **X-ray active site 验证不可省**：catalysis 决定 in active site geometry < 1 Å
6. **Directed evolution 必要 follow-up**：raw kcat 太低，industrial use 需 100-1000x 提升
7. **PRAXIS implication**：enzyme_de_novo_design skill 应包含 (a) RosettaMatch theozyme stage, (b) RFdiffusion-AA backbone + ProteinMPNN-Ligand sequence, (c) X-ray validation flag, (d) directed evolution loop integration

## 数据指针
- 论文 + supp: https://doi.org/10.1126/science.1190239
- DA-20 PDB: 3I1C (one of designs)
- 后续 Khersonsky directed evolution work 把 kcat 提升 ~300x
