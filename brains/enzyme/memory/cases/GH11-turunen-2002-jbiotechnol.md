---
case_id: GH11-turunen-2002-jbiotechnol
schema_version: 1
parent_enzyme:
  uniprot: P36217              # T. reesei XYNII (endo-1,4-beta-xylanase 2)
  cazy_family: GH11
  ec: 3.2.1.8
  organism: Trichoderma reesei (Hypocrea jecorina)
  pdb: 1XYN                    # T. reesei XYNII 结构
substrate:
  primary_smiles: "OC[C@@H]1O[C@@H](O[C@@H]2[C@@H](O)[C@@H](O)[C@H](O)O[C@@H]2CO)[C@H](O)[C@@H](O)[C@@H]1O"   # xylobiose 的近似 SMILES (β-1,4-xylobiose); 注意 xylose 是戊糖, 此处为示意 — 用户最终请用 RDKit 规范化
  class: xylobiose / xylan
target_property: thermostability
status: validated
provenance:
  source_type: literature
  doi: "10.1016/S0168-1656(01)00253-X"
  pmid: "11488221"
  citation: "Turunen O, Vuorio M, Fenel F, Leisola M (2001/2002). Engineering of multiple arginines into the Ser/Thr surface of Trichoderma reesei endo-1,4-β-xylanase II increases the thermotolerance and shifts the pH optimum towards alkaline pH. Protein Engineering 14(11):861-869."
  related_paper: "Turunen O, Etuaho K, Fenel F, Vehmaanperä J, Wu X, Rouvinen J, Leisola M (2001). A combination of weakly stabilizing mutations with a disulfide bridge in the alpha-helix region of Trichoderma reesei endo-1,4-beta-xylanase II increases the thermal stability through synergism. J Biotechnol 88(1):37-46."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "Turunen 团队在 2001-2002 年间发了多篇 TrXyn II 工程论文 (alpha-helix arginine substitution / disulfide bridge / N-terminal extension); 我引的两篇是其中较代表性的, DOI/PMID 用户用前请复核"
    - "具体 disulfide 桥连接的两个 Cys 位置 (S110C/N154C 或类似) 与精确 ΔTm 数值"
    - "xylobiose SMILES 是示意, 应该重新生成规范"
tags: [GH11, thermostability, xylanase, disulfide_bridge, surface_arginine, alpha_helix, Turunen-lab]
---

## 1. 背景与目标
- parent: T. reesei XYNII / Xyn2 (UniProt P36217), 工业用 GH11 endo-xylanase
- 起始 Tm: ~57°C (XYNII 是 mesophilic xylanase 代表)
- 目标: 提升 Tm 至 60-70°C 范围, 用于纸浆漂白与饲料加工 (高温/碱性条件)
- 应用: 纸浆 ECF 漂白 (60-70°C, pH 8-9), 动物饲料预消化

## 2. 决策过程 (合并 Turunen 团队 2001-2003 多篇工作的核心思路)

### 候选位点策略
- **多线并进**:
  1. **Surface Arg substitution**: 把 alpha-helix 区表面的 Ser/Thr → Arg, 增加 surface salt-bridge 与 cation-π 网络 (Turunen 2001 Protein Eng)
  2. **Disulfide bridge engineering**: 在 alpha-helix 与相邻 loop 引入 Cys 对 (距离 ~5.5 Å), 形成桥 (Turunen et al. 2002 J Biotechnol)
  3. **N-terminal extension** (后续 Fenel 2004 等): 把 thermophilic GH11 的 N-端片段移植过来
- 候选基于 PyMOL/Cα 距离测量 + Bonsai-style stability prediction

### 排除的位点 (★ 必填)
- **活性位点 cleft (catalytic E86, E177)** 完全保留, 包括周围 substrate-binding sheet
- thumb loop (residues 100-115 范围) — 控制 substrate access, 不动
- N-glycosylation site (XYNII 有 1 个 known site) 保留

### 计算工具与阈值
- 主要靠 sequence-structure 直觉 + Cα distance measurement (没用 PyRosetta, PyRosetta 当时不普及)
- 实验校验: heterologous expression (Trichoderma reesei 自身 host or E. coli) → CD melting curve → 活性测定 (xylan 或 RBB-xylan)

## 3. 实验结果

### 总体趋势 (★ 数值范围, 具体见原文)
| 策略 | ΔTm 量级 (vs WT XYNII ~57°C) |
| --- | --- |
| Multiple surface Arg substitution | +3 ~ +6°C |
| 单 disulfide bridge (alpha-helix + loop) | +5 ~ +10°C |
| Disulfide + Arg substitution (synergistic combo) | +10 ~ +15°C (Turunen 2001 J Biotech 报道的 synergism 关键发现) |
| N-terminal extension (后续工作) | +10 ~ +20°C 量级 |

### 失败案例 (★ 必填)
- 不是所有 Cys-Cys 距离合适的位点都成功形成 disulfide (Cys 暴露后氧化或与游离 Cys 错配)
- 部分 Arg substitution 中性或轻度负面 — Lys → Arg 之类细节差异敏感
- pH optimum 偏移: surface charge 改变同时偏移 pH optimum (Turunen 2001 主标题就是 "shifts pH optimum towards alkaline") — 既是副效应也是设计目标

## 4. 学习收获

- **成立的规则候选**:
  - **GH11 (β-jelly roll fold) 的 alpha-helix 区是 disulfide engineering 的理想位置**, Cα 距离 ~5.5-7 Å 的 Ser/Thr/Asn 对优先尝试
  - **synergistic combination**: 弱 stabilizing 突变与 disulfide 组合可超线性叠加 (Turunen 2001 J Biotech 核心发现)
  - **surface Ser/Thr → Arg substitution** 在 GH11 是稳定的"安全"突变, 多个一起做能稳态加分 (~+1°C/突变)
  - **pH optimum 偏移**是 surface charge engineering 的副效应; 想保留 pH optimum 应用 Lys 而非 Arg
- **被推翻的假设**:
  - "disulfide bridge 总是稳定的" — Cys 配对不准时反而引入折叠错误 / 暴露 Cys 触发聚集
- **下次类似问题应优先尝试**:
  - 对 GH11 类 xylanase, **disulfide engineering ∪ surface Arg substitution** 是文献验证的双重路径
  - N-terminal swap (来自 thermophilic 同家族) 是更激进的 +20°C 选项
- **应避免**:
  - 单独依赖一个 disulfide; 总要做 multiple-Arg 作为补充
  - 忽视 pH optimum shift — 应用场景若需中性 pH 必须监测

## 5. 计算 / 实验原始数据
原始 melting curve 与活性数据见 Protein Engineering 14(11) 与 J Biotechnol 88(1).
