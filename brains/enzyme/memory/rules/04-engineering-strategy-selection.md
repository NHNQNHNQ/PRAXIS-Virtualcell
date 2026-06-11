---
rule_id: 04-engineering-strategy-selection
schema_version: 1
rule_type: case_distilled
applies_to:
  cazy_class: ALL
  enzyme_family: ALL
  property: [meta_strategy_selection]               # meta-rule, applies to ALL engineering tasks
evidence_cases:
  # SCHEMA recombination (≥3 orthologs)
  - GH7-heinzelman-2009-pnas
  # Rational mutation transfer (homolog literature)
  - GH7-voutilainen-2010-prot-eng
  # Directed evolution + MD validation
  - GH7-goedegebuur-2017-jbc
  # Industrial directed evolution + structure-guided + ProSAR
  - HHDH-fox-2007-natbiotechnol
  - TRANSAMINASE-savile-2010-science
  - CA-alvizo-2014-pnas
  - IRED-schober-2019-natcatal
  - KRED-ma-2010-greenchem
  # Stepwise rational (multi-spec gating)
  - HNL-glieder-2003-angewchem
  # Directed coevolution (dual-screen)
  - SUBTILISIN-strausberg-2005-biochemistry
  # Single-point rational (pocket-controlled enzyme)
  - LIPASE-magnusson-2005-chembiochem
  # Metagenomic ortholog screen
  - DERA-greenberg-2004-pnas
  - NITRILASE-desantis-2003-jacs
  # Tunnel engineering (buried active site)
  - DEHALOGENASE-pavlova-2009-natchembiol
  # Consensus mutation (MSA-based, no structure needed)
  - PHYTASE-lehmann-2000-protein-eng
  # Loop transplantation (specificity multi-determinant)
  - PROTEASE-hedstrom-1992-science
  # Site-saturation (single key residue)
  - ERED-padhi-2009-jacs
confidence: high                       # 17 evidence cases 跨 12 enzyme families + 8 distinct strategies
last_updated: 2026-04-27
---

## 规则 — Protein engineering strategy 选择 meta-rule

跨 17 evidence cases 总结的 strategy decision tree。本 rule 不替代 rule 01-03 的具体内容,而是路由到合适的 specific rule + landscape。

### 优先级 0: Pre-engineering checklist

任何工程化任务起手必做:

| Check | Tool / Source | Output |
|-------|---------------|--------|
| Identify catalytic residues | UniProt features + 文献 | `excluded_positions.catalytic` |
| Identify cofactor binding | UniProt active site features + structure | `excluded_positions.cofactor_pocket` |
| Identify oligomer interface | PDB biological assembly + literature | `excluded_positions.interface` |
| Identify glycosylation sites | UniProt features (real) + NetNGlyc预测 | `excluded_positions.glycosylation_halo` |
| Quantify ortholog diversity | MMseqs2 search vs UniRef + CAZy | `n_orthologs`, `max_thermophilic_Tm` |
| Check structure availability | PDB / AlphaFold | `has_structure: true/false` |
| Define target metric | DSF Tm / kcat / kcat-Km / ee / yield | `target_metric.spec` |
| Industrial vs academic scale | 期望 productivity g/L / publication mg | `scale: industrial/academic` |

### 决策树: 主选哪个策略?

```
任务 → 起始判断
│
├── 是否有 ≥3 well-characterized orthologs (含至少 1 个 thermophilic / 已 engineered)?
│   ├── 是 → SCHEMA recombination (Heinzelman 2009 模板, GH7-heinzelman-2009-pnas)
│   │       优势: 一次重组获得 +9-13°C 量级 Tm; block-level 比 site-level 高效
│   │       前提: 必须有 contact map analysis 工具 (RASPP, SCHEMA)
│   │
│   └── 否 → 走下一步判断
│
├── 是否有 well-characterized homolog 已发表的 mutation list?
│   ├── 是 → Rational mutation transfer (Voutilainen 2010 模板)
│   │       优势: 低成本 (5-10 候选), 学术规模可行
│   │       前提: 命中率 ~30-50%, 需要逐个验证
│   │
│   └── 否 → 走下一步判断
│
├── Active site 中是否有显著的 "lid" residue (Trp/Phe/Tyr 类大空间残基)?
│   ├── 是 + substrate-scope 工程 → Single-point rational (Magnusson 2005 CALB W104A 模板)
│   │       优势: 1-3 mutations 可大幅 reorient pocket
│   │       前提: 已知"lid" residue 通过结构分析 + 文献
│   │
│   ├── 是 + stereoselectivity → Site-saturation on lid (Padhi 2009 OYE1 W116 模板)
│   │       完整 NNK saturation + multi-substrate panel = stereocomplementary collection
│   │
│   └── 否 → 走下一步判断
│
├── 是否有 buried active site + substrate access bottleneck?
│   ├── 是 → Tunnel engineering (Pavlova 2009 DhaA 模板)
│   │       工具: CAVER tunnel analysis + multi-residue cooperative mutations
│   │       优势: 改 tunnel 比改 active site 安全 (catalytic 几何不破坏)
│   │
│   └── 否 → 走下一步判断
│
├── 是否有大型 ortholog 库 (metagenomic) 可访问?
│   ├── 是 → Metagenomic discovery (Greenberg DERA / DeSantis nitrilase 模板)
│   │       优势: 自然多样性涵盖大部分 substrate 需求
│   │       前提: high-throughput library expression + screening infrastructure
│   │
│   └── 否 → 走下一步判断
│
├── 是否有结构 + ≥10 ortholog MSA?
│   ├── 是 + 主目标 thermostability → Consensus mutation (Lehmann 2000 phytase 模板) + PyRosetta scan
│   │       优势: cheap, 不需要 directed evolution infrastructure
│   │
│   └── 否 → 默认路线
│
├── 默认: Directed evolution + structure-guided initial library
│   ├── 学术规模 (~5-10 mutations 目标): Glieder 2002 BM3 / Williams 2007 OleD 模板
│   │   关键 enabler: high-throughput screen (surrogate substrate 显色 / 质谱)
│   │   ~5 rounds, ~10 mutations
│   │
│   └── 工业规模 (>g/L productivity, 20+ mutations): Codexis CodeEvolver 范式 (Savile 2010, Fox 2007, Alvizo 2014, Schober 2019)
│       关键 enabler: high-throughput LC-MS / chiral HPLC platform
│       ~10-15 rounds, ~20-35 mutations
│       后期 ProSAR statistical analysis 揭示 distal beneficial mutations
│
└── 多 spec 同时优化 (Tm + activity + ee + 工业反应条件) → Stepwise (HNL Glieder 2003 模板) OR Directed coevolution (Strausberg 2005 模板)
    Stepwise: 一阶段优化一指标, 然后下阶段
    Directed coevolution: 双指标同 selection, 累加 mutations 同时改两 specs
    选择: spec 数 ≤2 → coevolution; spec ≥3 → stepwise
```

### 工业 vs 学术 scale 阈值 (重要)

| 维度 | 学术规模 | 工业规模 |
|------|---------|---------|
| 累加 mutations | 1-10 | 20-35+ |
| Rounds | 1-5 | 8-15 |
| Library size | 10²-10⁴ | 10⁴-10⁶ |
| Selection 维度 | 1-2 | 3-5 (activity + ee + Tm + organic + yield) |
| Enabler | hand-built screen | high-throughput LC-MS / chiral HPLC |
| Timeline | weeks-months | 6-18 months |
| 验证 | mg substrate | g/L 工业反应 condition simulation |

**任务 input 时要预先判断 scale, 因为决定整个工程化路线结构。**

### Cross-rule 路由

具体应用时, 此 meta-rule 路由到 specific rule:

| 主要目标 | 路由到 rule |
|---------|-------------|
| Thermostability | `01-thermostab-mutation-priors` |
| Substrate scope / specificity | `02-substrate-scope-engineering-priors` |
| Activity / kcat | `03-activity-engineering-priors` |
| Multi-property | rule 04 (本 rule) → coevolution / stepwise 选择 |

加上 enzyme family-specific landscape rule (e.g., `lipase-engineering-landscape`, `protease-engineering-landscape`) 提供专属 chassis 信息。

### Universal exclusion zones (跨所有 17 evidence cases)

不论选哪个策略, 这些是**绝对禁区**:

1. **Catalytic residues**: serine triad / cysteine dyad / metal-binding His / PLP-Lys / Schiff base Lys / Cu-coordinating His brace / Asp-Asp aspartic protease 等
2. **Cofactor binding pocket** 一级 sphere: NADPH Rossmann fold / FAD binding / heme pocket / PLP phosphate loop / TPP-Mg²⁺
3. **Oligomer interface**: TA dimer / CE7 hexamer / SDR tetramer / IRED dimer
4. **Disulfide bridges** (when present)
5. **Signal peptide / pre-pro region** (mature 蛋白生成必需)

### 策略选择反模式 (★ 必读)

- **改 catalytic residues** 期望 substrate scope / activity 提升 — 必失活, 跨所有 17 cases 一致
- **学术规模工程化期望工业级 productivity** — Codexis benchmark 显示工业级需 20+ mutations 累加
- **仅 active site ±5 Å 找 mutations** — Fox 2007 / Alvizo 2014 显示 distal mutations 是大部分贡献
- **单维 selection (only Tm 或 only activity 或 only ee)** — 必引发其他 spec 漂移
- **缺 high-throughput screen 启动 directed evolution** — 必失败 (无 readout)
- **从 active-site mutation 开始改 substrate specificity** — Hedstrom 1992 推翻 (loop 才是关键)

## 依据

| evidence_case | 关键决策点 | strategy 启发 |
|---------------|-----------|---------------|
| `GH7-heinzelman-2009-pnas` | 3 fungal Cel7A orthologs | SCHEMA branch |
| `GH7-voutilainen-2010-prot-eng` | T. emersonii 与 T. reesei 同源 | rational transfer branch |
| `GH7-goedegebuur-2017-jbc` | 单 enzyme + MD 解释 | DE + MD validation branch |
| `HHDH-fox-2007-natbiotechnol` | 工业 productivity | Codexis ProSAR branch |
| `TRANSAMINASE-savile-2010-science` | 大型 bulky pharma substrate | Codexis structure-guided branch |
| `CA-alvizo-2014-pnas` | extreme industrial conditions | Codexis + in-situ industrial selection |
| `KRED-ma-2010-greenchem` | cascade engineering | simultaneous multi-enzyme optimization |
| `IRED-schober-2019-natcatal` | bulky pharma imine | Codexis CodeEvolver branch |
| `HNL-glieder-2003-angewchem` | multi-spec gating (溶解+Tm+pH+biphasic) | Stepwise rational branch |
| `SUBTILISIN-strausberg-2005-biochemistry` | Tm + activity 双指标 | Directed coevolution branch |
| `LIPASE-magnusson-2005-chembiochem` | CALB W104 single key residue | Single-point rational branch |
| `DERA-greenberg-2004-pnas` | metagenomic discovery | Library mining branch |
| `NITRILASE-desantis-2003-jacs` | metagenomic + DE 串联 | Library + DE branch |
| `DEHALOGENASE-pavlova-2009-natchembiol` | buried active site + TCP access | Tunnel engineering branch |
| `PHYTASE-lehmann-2000-protein-eng` | 多 ortholog MSA, 无结构 | Consensus branch |
| `PROTEASE-hedstrom-1992-science` | substrate specificity 多决定因素 | Loop transplantation branch |
| `ERED-padhi-2009-jacs` | OYE1 W116 单 key residue saturation | Site-saturation branch |

## 边界

- 本 meta-rule **不取代** rule 01-03 specific guidance — 而是 routing layer
- 跨 family 决策可能不准确 if enzyme 是 truly novel (未涉及任何 17 evidence enzyme family)
- "Industrial vs academic" 二分有 gray zone — 中等规模 (academic-spinout, ~10-15 mutations) 介于两者

## How to apply

- **Scoping Agent**: 用 pre-engineering checklist 先填充 query 中的 enzyme features
- **Design Agent**: 走决策树, 同时引用 specific rule 01/02/03 + landscape rule
- **Reviewer (Gate 2)**: 检查 design_plan 是否:
  - 与决策树推荐 strategy 一致 (or 显式说明 deviation 理由)
  - excluded_positions 包含 universal exclusion zones
  - mutation 数量级与 scale (academic / industrial) 匹配
- **Reporting Agent**: 引用 strategy selection 解释为什么这条路径

## 升级路径

升至 confidence: very_high 需要再增 ≥3 evidence cases 跨 3 个新 strategy types (e.g., orthogonal cofactor swap, ancestral reconstruction, Rosetta-driven design 等)。当前 17 evidence 涵盖经典策略, 但 ML-driven engineering (AlphaFold + design models) 类新策略未充分代表。
