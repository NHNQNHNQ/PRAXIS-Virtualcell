---
case_id: TRANSKETOLASE-hibbert-2007-jbiotechnol
schema_version: 1
parent_enzyme:
  uniprot: P27302               # E. coli transketolase A (TktA)
  cazy_family: null
  enzyme_family: transketolase / TPP_dependent_aldol
  ec: 2.2.1.1
  organism: Escherichia coli
  pdb: 1QGD                     # E. coli TktA 经典结构
substrate:
  primary_smiles: "CCCCC=O"      # propanal / pentanal (示意; 论文用 various aldehyde acceptors)
  class: aliphatic_aldehyde / non_natural_substrate
target_property: substrate_specificity   # 扩 TktA 对 non-α-hydroxylated aldehyde 接受
status: validated
provenance:
  source_type: literature
  doi: "10.1016/j.jbiotec.2007.07.949"
  pmid: null
  citation: "Hibbert EG, Senussi T, Costelloe SJ, Lei W, Smith ME, Ward JM, Hailes HC, Dalby PA (2007). Directed evolution of transketolase activity on non-phosphorylated substrates. J Biotechnol 131(4):425-432."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 第一次推 j.jbiotec.2006.11.017 错 (实际是别的 J Biotechnol PHBV paper), CrossRef 文本搜后改为 10.1016/j.jbiotec.2007.07.949"
    - "E. coli TktA UniProt P27302 高把握"
    - "PDB 1QGD 是 E. coli TktA 经典; 后续 Hailes/Dalby 实验室解析其 evolved 突变体结构"
    - "Hailes lab (UCL) + Dalby lab (UCL Biochem Eng) 经典 transketolase 工程化系列"
    - "TPP (thiamine pyrophosphate) cofactor 必需; 工程化避免破坏 cofactor 结合"
    - "本工作针对 non-phosphorylated aldehyde acceptors (天然 substrate 是 phosphorylated sugar) — substrate scope 大幅扩展"
tags: [transketolase, TPP_dependent, substrate_specificity, directed_evolution, asymmetric_aldol, non_phosphorylated_substrate, Hailes-lab, Dalby-lab, non-CAZy]
---

## 1. 背景与目标
- parent: E. coli TktA (UniProt P27302), TPP-dependent transketolase, EC 2.2.1.1
- 自然反应: 把 ketose (e.g., xylulose-5-P) 上的 ketol unit (HOCH₂-CO-) 转移到 aldehyde acceptor (e.g., ribose-5-P) — pentose phosphate pathway 关键步骤
- 自然 substrate: phosphorylated sugars (xylulose-5-P, ribose-5-P, fructose-6-P)
- 目标: 扩 substrate scope 至 **non-phosphorylated aliphatic aldehydes** (propanal, butanal, pentanal 类), 给非天然 hydroxyketones (chiral 二醇前体)
- 应用: chiral synthon 合成 (asymmetric aldol via TPP-mediated mechanism), 替代化学不对称 aldol

## 2. 决策过程

### 候选位点策略
- **Directed evolution** + structure-guided initial library:
  1. 起始 WT TktA, 用 1QGD 结构识别 substrate-binding cleft 的 phosphate-binding residues (Arg + Asp cluster)
  2. Saturation mutagenesis on phosphate binding pocket (希望去掉 phosphate 偏好)
  3. Multi-round screening with non-phosphorylated aldehyde substrates
  4. 累加 ~3-5 mutations
- 选择压力: 让 enzyme 接受 propanal 等小型 aliphatic aldehyde

### 排除的位点 (★ 必填)
- TPP 结合 残基 (His + Glu cluster, conserved across ThDP-dependent enzymes) 严格保留 — cofactor 必需
- Catalytic Glu (proton donor for ylide formation) 保留
- Mg²⁺ 结合 (与 TPP 共同) 保留
- Dimer interface — TktA 是 obligate dimer

### 计算工具与阈值
- Structure 1QGD 指导 library design
- Activity assay: NADH coupled assay (后续 dehydrogenase) 或 LC-MS 直接 product detection
- 实验校验: 重组表达 in E. coli → 多 aldehyde acceptor panel 测 → chiral HPLC ee%

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| WT TktA 活性 (propanal) | 极低 (<1% vs xylulose-5-P) |
| Evolved variants 活性 (propanal, pentanal) | 50-100× WT |
| ee 的 (R)-或 (S)- 选择性 | >90% (取决于 substrate) |
| 累加 mutations | 3-5 |
| 关键 mutations | 集中在 phosphate-binding loop (e.g., H100, H473 周围) |

### 失败案例 (★ 必填)
- 早期 saturation library: 完全去掉 phosphate-binding 残基的 variants 失活 — 必须保留部分 hydrogen bond capacity
- 部分 evolved variants 接受 non-phosphorylated 但失去 phosphorylated substrate 活性 — specificity tradeoff
- TPP cofactor loading 部分变体 ~50%, 工业级反应需要 holo-form 制备 (incubate with Mg²⁺ + TPP)

## 4. 学习收获
- **成立的规则候选**:
  - **TPP-dependent enzyme 工程化的核心**: 不动 TPP 结合 + ylide formation residue, 改 substrate-binding loop
  - **Phosphate-binding pocket 是 TktA 类 substrate scope 工程化的 key target** — 改这里能去除 phosphate 偏好
  - **3-5 mutations 通常够** (vs 工业 substrate 工程化的 20+) — 因为 specificity 由几个关键 residue 控制
- **被推翻的假设**:
  - "TPP-dependent 类 enzyme 因 cofactor 复杂难以工程化" — Hibbert 2007 显示 directed evolution 可大幅扩 substrate scope
- **下次类似问题应优先尝试**:
  - TPP-dependent 类工程化 (transketolase / decarboxylase / pyruvate-related): 起手 saturation on substrate-binding pocket
  - 非天然 substrate 接受能力工程化: 选择压力直接用 target substrate
- **应避免**:
  - 改 TPP 结合 residue — 必失活
  - 假设单 enzyme 可同时接受 phosphorylated + non-phosphorylated — specificity tradeoff 通常不可避免

## 5. 计算 / 实验原始数据
原始 evolved variants kinetics + chiral HPLC 数据见 J Biotechnol 131(4) 2007 supplementary; 后续 Smith / Cazares-Korner 续篇含 mechanism 解析.
