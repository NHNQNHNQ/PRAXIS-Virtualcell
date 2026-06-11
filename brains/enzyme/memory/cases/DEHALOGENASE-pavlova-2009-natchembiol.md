---
case_id: DEHALOGENASE-pavlova-2009-natchembiol
schema_version: 1
parent_enzyme:
  uniprot: P59336               # DhaA (haloalkane dehalogenase) from Rhodococcus rhodochrous NCIMB 13064
  cazy_family: null
  enzyme_family: haloalkane_dehalogenase / α/β_hydrolase_fold
  ec: 3.8.1.5
  organism: "Rhodococcus sp. (literature uses Rhodococcus rhodochrous NCIMB 13064)"
  pdb: 1BN6                     # DhaA 经典结构 (Newman 1999)
substrate:
  primary_smiles: "ClC(Cl)Cl"    # 1,2,3-trichloropropane (TCP) — 难降解的 anthropogenic groundwater pollutant
  class: anthropogenic_polychlorinated / environmental_remediation
target_property: substrate_specificity   # WT 几乎不识别 TCP, 工程化让其接受
status: validated
provenance:
  source_type: literature
  doi: "10.1038/nchembio.205"
  pmid: null
  citation: "Pavlova M, Klvaňa M, Prokop Z, Chaloupkova R, Banas P, Otyepka M, Wade RC, Tsuda M, Nagata Y, Damborsky J (2009). Redesigning dehalogenase access tunnels as a strategy for degrading an anthropogenic substrate. Nat Chem Biol 5(10):727-733."
  extracted_at: 2026-04-27
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1038/nchembio.205 高把握 (well-cited Damborsky lab paper)"
    - "DhaA UniProt P59336 高把握"
    - "PDB 1BN6 是 DhaA 经典结构 (Newman 1999); Damborsky 2009 evolved variants 后续可能 deposit"
    - "Damborsky 实验室 (Loschmidt Labs, 捷克) 是 enzyme tunnel engineering 创始团队"
    - "TCP (1,2,3-trichloropropane) 是 EPA 关键 groundwater contaminant, biodegradation 长期目标"
tags: [haloalkane_dehalogenase, DhaA, alpha_beta_hydrolase_fold, substrate_specificity, access_tunnel_engineering, anthropogenic_substrate, environmental_remediation, TCP, Damborsky-lab, non-CAZy]
---

## 1. 背景与目标
- parent: DhaA (haloalkane dehalogenase, UniProt P59336, α/β hydrolase fold), EC 3.8.1.5
- 自然 substrate: 1-haloalkanes (chloro-/bromo-alkanes), via Asp-His-Asp catalytic triad with covalent intermediate
- 目标: 让 DhaA 高效降解 1,2,3-trichloropropane (TCP) — anthropogenic 污染物 (groundwater contaminant), WT 几乎无活性
- 应用: 环境 remediation — TCP-contaminated groundwater 生物降解; bioremediation 概念验证

## 2. 决策过程 — Tunnel engineering (Damborsky lab 招牌)

### 候选位点策略
- **Access tunnel redesign** (而不是 active site 直接突变):
  1. 用 CAVER 计算工具识别 DhaA 的 substrate access tunnels (从 surface 到 catalytic Asp)
  2. 找 tunnel "bottleneck" 残基 (限制 large/branched substrate 进入)
  3. 多个 tunnel residues (不在 active site 一级 sphere, 但控 substrate access) 系统突变
- 累加 5 mutations: I135F + C176Y + V245F + L246I + Y273F (具体 mutation list 见原文)

### 排除的位点 (★ 必填)
- α/β hydrolase 催化 Asp106-His272-Asp260 triad 严格保留 — 突变即失活
- Halide-binding Trp-pair (W107, W141) 保留 — 反应必需
- Oxyanion hole 主链 NH 保留
- 不动 active site 一级 sphere — 重要的洞察: 改 access tunnel 比改 active site 更安全 (catalytic geometry 不破坏)

### 计算工具与阈值
- **CAVER tunnel analysis** (Damborsky lab 工具): 识别 substrate access pathways
- MD simulations: 确认 evolved variant tunnels 实际更宽 / 更柔
- 实验校验: 重组表达 in E. coli → TCP / chloroalkane substrate panel 测 kcat/Km → MD trajectory dynamics

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| WT DhaA 活性 (TCP) | 极低 (kcat/Km < 10⁻³ M⁻¹s⁻¹) |
| 5-mutation evolved variant (DhaA31) 活性 (TCP) | 32× WT (kcat/Km ~10⁻¹) |
| 活性 (small substrate, 1-iodobutane) | 维持 (specificity 不被破坏) |
| Tunnel "bottleneck" 直径 (MD avg) | ~3 Å → ~5 Å |
| TCP biodegradation in microcosm | 显著加速 |

### 失败案例 (★ 必填)
- 早期单点 mutations 几乎全部 negligible 改进 — tunnel 是 multi-residue cooperative 系统, 单点不够
- 部分组合 mutations destabilize fold — 5-mutation variant 只是 tunnel + stability 兼顾的局部最优
- 即使 evolved variant TCP 活性仍低于 small natural substrate — anthropogenic substrate 工程化有 inherent ceiling

## 4. 学习收获
- **成立的规则候选**:
  - **Access tunnel engineering** (而不是 active site mutation) 是 substrate access-limited enzymes 的核心策略
  - **CAVER 类工具** 是 tunnel-bottleneck identification 的 enabler — 没有 tunnel analysis 难找 mutation 目标
  - **Anthropogenic substrate** 工程化常需 tunnel + stability coevolution; 5+ mutations 通常 minimum
  - **不要碰 active site 一级 sphere** when tunnel mutation 即够 — 风险/收益更好
- **被推翻的假设**:
  - "Substrate scope 工程化必改 active site" — Pavlova 2009 显式推翻 (5 mutations 全在 tunnel, 不在 active site)
- **下次类似问题应优先尝试**:
  - 任何 enzyme substrate scope 工程化, 先做 CAVER tunnel analysis 看是否有 access bottleneck
  - α/β hydrolase fold + buried active site enzyme 普遍受益于 tunnel engineering (与 surface-active enzyme 不同)
- **应避免**:
  - 直接改 active site catalytic 残基期望 substrate scope — risky
  - 单 round single-point — tunnel mutations 是 cooperative

## 5. 计算 / 实验原始数据
原始 CAVER analysis + MD trajectories + 5-mutation variant kinetics 见 Nat Chem Biol 5(10) 2009 supplementary; CAVER tool 公开可用 (Damborsky lab).
