---
case_id: drug-007-protac-dbet1
project_phase: hit_id
target_uniprot: O60885 (BRD4)
target_pdb: 4OGI   # BRD4 BD1 with JQ1 (the dBET1 warhead target); 5JN1 is no longer in RCSB
target_class: bromodomain
indication: oncology_AML
modality: protac
hit_id_method: rational_design
representative_compounds:
  - name: dBET1
    chembl_id: null   # dBET1 has no clean ChEMBL entry; PROTAC literature
    smiles: O=C(CCCCCCCCC(=O)NC1CCC(=O)NC1=O)Nc1ccc2c(c1)C(=O)N(C)C(c1ccc(Cl)cc1)C2c1nnc(C)n1C
    inchikey: LKEHHHOYZWJXBT-UHFFFAOYSA-N   # RDKit-computed; the original KQXKGQTUZQXDIZ was wrong
    activity: BRD4 DC50 ~ 100nM
tools: [PyMOL, Vina (relaxed restraints), MD ROSETTA, Pocket2Mol, ProteinMPNN-DNA]
key_paper_doi: 10.1126/science.aab1433
status: validated
validated: true
source: praxis_seed
---

# dBET1：PROTAC 设计的物理建模特殊难点

## Background
PROTAC（Proteolysis-Targeting Chimera）= warhead (target ligand) + linker + E3 ligase ligand。dBET1（Winter 2015）是 PROTAC 早期里程碑：JQ1 (BRD4 binder) + thalidomide (CRBN binder) + linker → 诱导 BRD4 ubiquitination + degradation。**与传统抑制剂不同**：PROTAC 需形成 ternary complex（target-PROTAC-E3），design 难度上升一个 order。

## What I actually did（pipeline 复盘）
1. **Warhead 选择**：JQ1 (BRD4 binder, KD ~50 nM) + thalidomide (CRBN binder)——两个 ligand 都有 known PDB 共结晶
2. **Linker 长度估计**：用 PyMOL 量两个 protein-ligand 复合物 superimpose 后两 ligand exit vector 间距；典型 PROTAC linker 8-15 atoms (PEG / alkyl chain)
3. **Linker design**：PEG (ether-rich，柔性 + 溶解度) vs alkyl (rigid + lipophilic)；dBET1 用 alkyl linker
4. **Ternary complex modeling**：当前没有完美工具
   - PRosettaC, PROTAC-Model 等专用
   - 或自己 build：JQ1-BRD4 + thalidomide-CRBN superimpose；linker 通过 conformational sampling
5. **Cooperativity α**：α > 1 = positive cooperativity（PROTAC stabilize ternary）；α < 1 = negative；可用 BRET assay 实测；建模上看 ternary 复合物 strain energy
6. **DC50 vs IC50 不同**：DC50 是 degradation 50% 浓度，与 ternary 形成效率相关
7. **后筛 sanity**：linker 不能太长（hook effect → 低浓度好高浓度差）；linker 不能太短（ternary 几何不允许）

## ★ 排除/不做的事
- **当传统抑制剂 design**：忽略 ternary complex 几何，linker 长度乱拼
- **Linker 全 PEG 默认**：PEG 影响细胞穿透；alkyl 也是常用选择
- **不做 ternary docking**：PROTAC 关键是 ternary complex stability，纯 binary docking score 误导
- **Cooperativity 不评估**：α < 1 PROTAC 通常不 work（hook effect 强）
- **Hook effect 不预警**：bell-shaped dose response 是 PROTAC 标志，需评估
- **不评估 cell penetration**：MW 800+ 是常态，logP 可能高，BBB 穿透是 separate issue
- **Single E3 ligase**：CRBN 是默认但易耐药；VHL / cIAP / DCAF15 等多 E3 ligase 选择 expand scope

## ★ 失败模式
- **Hook effect 致命**：PROTAC 高浓度形成 binary 而非 ternary，degradation 反降；剂量窗口窄
- **Permeability 差**：MW 700-900 + 多 H-bond donor → PAMPA permeability 差；需化学优化
- **Selectivity vs paralog**：JQ1 同时结合 BRD2/3/4，dBET1 同样 pan-BET degrader（不一定坏，但是 specificity 限制）
- **E3 ligase 表达异质性**：CRBN 在不同 cancer cell line 表达水平差，dBET1 在低 CRBN 细胞失效
- **De novo resistance**：长期 PROTAC 处理诱导 CRBN/E3 突变 → 失效
- **In vitro vs in vivo gap**：cell-based DC50 与 in vivo PD（target degradation in animal）相关性差
- **Synthesis cost**：linker 设计 + 两个复杂 warhead，合成 8-12 步成本高

## Lessons → seeds for rules
1. **Ternary complex modeling 必须**（PRosettaC 或自己 build）
2. **Linker 多型号 sample**：PEG / alkyl / PEG-alkyl mix，test 5-10 长度
3. **Cooperativity α 评估**：模拟 ternary strain energy 或 wet lab BRET
4. **Hook effect 警告**：dose-response 必报 bell shape 风险
5. **Permeability 加权评估**：MW 700+ 的 ADMET 模型需 PROTAC-specific
6. **E3 ligase 多选**：CRBN / VHL / cIAP 至少 2 选，避免 single point failure
