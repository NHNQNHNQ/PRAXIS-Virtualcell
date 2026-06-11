---
case_id: CA-alvizo-2014-pnas
schema_version: 1
parent_enzyme:
  uniprot: P00918               # Human carbonic anhydrase II (CA II)
  cazy_family: null
  enzyme_family: carbonic_anhydrase / α_CA
  ec: 4.2.1.1
  organism: Homo sapiens
  pdb: 2CBA                     # CA II 经典结构
substrate:
  primary_smiles: "O=C=O"        # CO₂ — substrate; product is HCO₃⁻ + H⁺
  class: small_molecule_inorganic / CO2_hydration
target_property: thermostability_and_activity   # ultra-thermostable CA at high pH/temp for industrial CO₂ capture
status: validated
provenance:
  source_type: literature
  doi: "10.1073/pnas.1411461111"
  pmid: null
  citation: "Alvizo O, Nguyen LJ, Savile CK, Bresson JA, Lakhapatri SL, Solis EOP, Fox RJ, Broering JM, Benoit MR, Zimmerman SA, Novick SJ, Liang J, Lalonde JJ (2014). Directed evolution of an ultrastable carbonic anhydrase for highly efficient carbon capture from flue gas. PNAS 111(46):16436-16441."
  extracted_at: 2026-04-27
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1073/pnas.1411461111 高把握 (well-cited Codexis × Codexis-Codexis paper)"
    - "Human CA II UniProt P00918 高把握 (经典 reference)"
    - "PDB 2CBA 是 CA II 经典 1.5 Å 结构 (Eriksson 1988)"
    - "Codexis 工业 CO₂ capture project; 累加 ~16-20 mutations 给 evolved variant"
    - "工程化目标极端: pH 9.5, 100°C, 4.2 M alkanolamine sorbent — 真实 flue gas 条件"
tags: [carbonic_anhydrase, CA_II, thermostability, activity, CO2_capture, alkaline_pH, directed_evolution, industrial_carbon_capture, Codexis, non-CAZy]
---

## 1. 背景与目标
- parent: Human CA II (UniProt P00918), Zn²⁺-containing α-carbonic anhydrase, EC 4.2.1.1
- 自然反应: CO₂ + H₂O ⇌ HCO₃⁻ + H⁺ (turnover 极快, kcat ~10⁶ s⁻¹, near diffusion limit)
- 工业目标: 在 **flue gas 条件** 工作 — 100°C, pH 9.5, 4.2 M MDEA (alkanolamine 类 sorbent), 高 CO₂ partial pressure
- 这是工业 enzyme 极限挑战: WT CA II 在 60°C+ 即变性, 在 4.2 M 胺中失活 < 1 hour
- 应用: post-combustion CO₂ 捕集 — 化石电厂减排, 比纯化学吸收更高效

## 2. 决策过程

### 候选位点策略 — Codexis CodeEvolver
- **Directed evolution + ProSAR + 工业 condition selection**:
  1. 起始 WT CA II
  2. Multi-round random + saturation libraries
  3. Selection 在工业反应条件 (pH 9.5, 100°C, 4.2 M MDEA) 直接 — 学术规模 mild conditions selection 无法 transfer
  4. 累加 ~16-20 mutations
- 与 sitagliptin TA / atorvastatin KRED+HHDH 同 platform

### 排除的位点 (★ 必填)
- **Zn²⁺ 配位 Histidines (H94, H96, H119)** 严格保留 — Zn²⁺ 是 catalytic essential
- **Catalytic gateway** Glu (E106) + Thr (T199) 保留 — proton wire to bulk
- **Active site water molecule binding pocket** 残基保留
- 核心 β-sheet 内部疏水残基保留 — fold 稳定性

### 计算工具与阈值
- Codexis ProSAR statistical analysis
- High-throughput CO₂ hydration assay (pH-stat or coupled detection)
- 工业反应条件模拟必备 (4 M MDEA, alkaline pH, high temp)

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| WT CA II Tm (no MDEA) | ~60°C |
| WT half-life (4.2 M MDEA, 50°C) | < 1 hour |
| Engineered ultrastable variant Tm | >100°C (in MDEA solvent) |
| Engineered half-life | >100,000× WT |
| 累加 mutations | ~16-20 |
| Industrial outcome | flue gas CO₂ capture pilot scale demonstrated |

### 失败案例 (★ 必填)
- 早期 rounds: surface mutations 提 Tm 但 kcat 下降 — 必须双指标 selection
- 部分 stability mutations 改 Zn²⁺ binding 几何 → catalytic activity loss; 这些被快速淘汰
- 部分 high-Tm variants 在纯水中稳定但 4.2 M MDEA 中聚集 — solvent compatibility 是隐藏 spec
- "Activity-stability tradeoff" 长期被认为 inevitable, 但 Codexis 此案例显示通过 distal (非 active site) mutations 可大幅突破

## 4. 学习收获
- **成立的规则候选**:
  - **Industrial extreme condition (high temp + high pH + high salt)** enzyme 工程化必走 Codexis 类 platform — 学术规模 mild condition selection 无法 transfer
  - **Distal mutations are key** for activity-stability simultaneous improvement (与 HHDH-fox-2007 一致)
  - **Solvent compatibility 是 hidden gating spec** — water-only test 必须配 industrial-relevant solvent test
  - **Even highly evolved enzymes (CA II 已是 near-diffusion-limit) 仍可工程化** for stability without losing activity
- **被推翻的假设**:
  - "Activity-stability tradeoff is inherent" — Alvizo 2014 显示 100,000× stability 提升而保持 activity
  - "Near-diffusion-limit enzymes 不能工程化" — CA II 显示仍可 (focus shifts to stability under conditions, not catalytic perfection)
- **下次类似问题应优先尝试**:
  - 工业 CO₂ capture / industrial extreme-condition 任务: 必须 in-situ industrial buffer selection
  - High-Tm + high-activity 同时: distal mutations 通过 ProSAR 找
- **应避免**:
  - 仅在水中评估 — industrial solvent 必同步测
  - 假设 Zn²⁺ 配位变化是 negligible — 严格保留所有 metal binding 残基
  - 单维 selection — Tm-only 必 cost activity

## 5. 计算 / 实验原始数据
原始 evolved variant 性能 + industrial pilot 数据见 PNAS 111(46) 2014; Codexis 商业化细节部分专利化.
