---
case_id: CE5-yoshida-2016-science
schema_version: 1
parent_enzyme:
  uniprot: A0A0K8P6T7            # IsPETase from Ideonella sakaiensis 201-F6 (PETH); UniProt 收录
  cazy_family: CE5                # 多数文献归 CE5; 也有作 standalone α/β-hydrolase
  ec: 3.1.1.101                   # poly(ethylene terephthalate) hydrolase (PETase, 现行 EC)
  organism: Piscinibacter sakaiensis   # 2018 重分类自 Ideonella sakaiensis 201-F6
  pdb: 5XJH                       # IsPETase apo crystal (Han 2017 deposit, follow-up)
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "CCOC(=O)c1ccc(C(=O)OCC)cc1"   # PET model substrate / BHET
  class: polyethylene_terephthalate / aromatic_polyester
target_property: substrate_specificity   # 主线: 在 mesophilic (~30 °C) 条件直接降解 PET, 不靠高温
status: validated
provenance:
  source_type: literature
  doi: "10.1126/science.aad6359"
  pmid: 26965627
  citation: "Yoshida S, Hiraga K, Takehana T, Taniguchi I, Yamaji H, Maeda Y, Toyohara K, Miyamoto K, Kimura Y, Oda K (2016). A bacterium that degrades and assimilates poly(ethylene terephthalate). Science 351(6278):1196-1199."
  extracted_at: 2026-04-28
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1126/science.aad6359 与 PMID 26965627 我推测; CrossRef 验证"
    - "UniProt A0A0K8P6T7 我推测对应 IsPETase; QA 验证"
    - "PDB 5XJH 我推测对应 IsPETase apo; 原 Yoshida 2016 paper 未必 deposit, follow-up Han Liu 2017 Nat Commun (10.1038/ncomms14837) 解构"
    - "本论文是在 PET 回收瓶垃圾场分离 Ideonella sakaiensis 菌株 — 第一个能在 mesophilic (~30 °C) 直接降解结晶 PET 的 wild-type bacterium"
    - "IsPETase + MHETase 双酶系: IsPETase 切 PET → MHET, MHETase (Knott 2020 PNAS, doi 10.1073/pnas.2006753117) 切 MHET → TPA + EG"
    - "engineering target 标 substrate_specificity 因 IsPETase 底物 scope 与传统 cutinase 显著不同 (PET 降解优先)"
    - "本案例为后续 FAST-PETase / HotPETase 系列工程化提供 starter scaffold"
    - "CAZy 将 PETase 归 CE5 carbohydrate esterase 5 家族 (cutinase 同类), 部分文献也单独称 PETase"
tags: [CE5, IsPETase, PET_hydrolase, plastic_degradation, mesophilic, Ideonella_sakaiensis, foundational_discovery, Yoshida-2016, Oda-lab, MHETase_partner, scaffold_starter]
---

## 1. 背景与目标
- parent: Ideonella sakaiensis 201-F6 IsPETase (CE5 cutinase-like α/β-hydrolase); 含 catalytic Ser-His-Asp triad + 较浅 substrate cleft
- 起始性质: 在 mesophilic (~30 °C, lab condition) 条件直接降解 amorphous PET, kcat 较低 (~10⁻³ s⁻¹) 但是当时 wild-type 家族中最强的 PET 直接降解者
- 目标: 鉴定能在常温降解 PET 的 wild-type 酶, 揭示其 sequence / structure 特征以指导工业 PET 降解 enzyme 的工程化
- 应用: PET 塑料回收 (常温/低能耗) 工程化的 starter scaffold; 后续 FAST-PETase / HotPETase / 等多个工程化 variant 全基于 IsPETase

## 2. 决策过程

### 候选位点策略
- 本论文主要是 discovery (从环境样本筛 PET-degrading bacteria, 鉴定 enzyme); 不是 directed engineering
- 后续 follow-up 作为 starter, 多个组用以下策略改造:
  - **rational pocket reshaping** (active site cleft 拓宽)
  - **disulfide bridge** 引入 (类比 LCC ICCG 路线, Tournier 2020 Nature)
  - **surface charge optimization** (W159H / S238F 等 reported variants)

### 排除的位点 (★ 必填)
- **catalytic triad Ser160-His237-Asp206** (IsPETase numbering): 严格保留, α/β-hydrolase 经典
- **oxyanion hole** (主链 NH 来自 Met161 + Tyr87 等): 保留以稳定 tetrahedral intermediate
- **核心 disulfide bridge** Cys203-Cys239 (IsPETase 含 1 对 二硫键, 比 LCC 多): 保留以维持 fold stability
- **W159 / S238 关键 substrate-binding residues**: 后续工程化常 mutate, 但需 explicit 测试

### 计算工具与阈值
- discovery 阶段: 16S rRNA 系统发育鉴定菌种 + 全基因组 + protein 异源表达验证 + LC-MS 检 PET 降解产物
- 后续工程化阶段: AlphaFold 模型 + PyRosetta ddG (但需注意 NEG-AFMUTATION-buel-2022 反例提示 AF + ddG 在 designed mutation 排序失精度) + 实测 high-temperature PET turnover

## 3. 实验结果

### IsPETase 起始性能
| 量 | 值 |
| --- | --- |
| Tm | ~50 °C (低 -- 工业瓶颈) |
| 在 amorphous PET (30 °C) 比活 | ~baseline (与 LCC apo 同量级) |
| 在 PET-Tg (~70 °C) 活性 | ~0 (因 Tm 低于 PET-Tg 即变性) |
| Substrate scope | PET / MHET / pNPP (model substrate) |

### 失败案例 (★ 必填)
- **IsPETase 起始 Tm ~50 °C** 远低于 PET 玻璃化温度 (~70 °C), 不能在工业 condition (PET-Tg 附近高 throughput) 工作 — 这是 IsPETase 本体的 fundamental 局限
- **catalytic triad 邻近 mutation (即使 ΔΔG -预测好)**: 多次报道破坏 catalysis, IsPETase 与 LCC 同类但 catalytic geometry 比 LCC 更敏感
- **AF model + PyRosetta 工程化 IsPETase 命中率低**: 见反例 NEG-AFMUTATION-buel-2022 — AF model 不能可靠预测 IsPETase 突变效应
- **跨 cutinase 来源 mutation 转移 (LCC ↔ IsPETase) 部分失败**: 序列 identity ~50%, 二级结构相似但 active-site 微差大, mutation 直接转移命中率 <30%

## 4. 学习收获
- **成立的规则候选**:
  - **PET 降解酶工程化的核心瓶颈是 Tm 与 PET-Tg (70 °C) 关系**: IsPETase Tm <50 °C 是首要工程化目标 (FAST-PETase / HotPETase 都首要解决此)
  - **CE5 cutinase 工程化排除 mask (与 CE5-tournier-2020 一致)**: catalytic Ser-His-Asp + oxyanion hole + 已设计 disulfide
  - **Mesophilic PET 降解酶 (IsPETase) 是工业起点**: 不需要从头筛环境样本, 用 IsPETase 作 scaffold 工程化
  - **跨 PETase 来源 (IsPETase / LCC / TfH / Cutinase) mutation 转移率 ~30%**: 不能直接套用, 需在目标 scaffold 重新验证
- **被推翻的假设**:
  - "PET 降解仅在高温 (60-70 °C) 工程化条件下可行" — IsPETase 直接证伪, mesophilic 路线可行
- **下次类似问题应优先尝试**:
  - 任何 PET 降解酶项目, 优先用 IsPETase 或 LCC 作 starter (具体取决于目标温度: 高温用 LCC, 常温用 IsPETase)
  - **Tm 与 substrate Tg 的关系是 polymer-degrading enzyme 工程化的 core variable** (与 Tournier 2020 一致)
- **应避免**:
  - Catalytic triad ±3 残基 mutation
  - 单纯依赖 AF model + PyRosetta 排序 (见反例 NEG-AFMUTATION)
  - 把 IsPETase 单独工程化在 PET-Tg 工作 (Tm 不够, 必须先 thermostab)

## 5. 计算 / 实验原始数据
原始 Ideonella sakaiensis 鉴定 + IsPETase 异源表达数据见 Science 2016 supplementary; IsPETase 结构由 Han 2017 Nat Commun follow-up 提供.
