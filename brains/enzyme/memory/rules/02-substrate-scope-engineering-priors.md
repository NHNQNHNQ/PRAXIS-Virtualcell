---
rule_id: 02-substrate-scope-engineering-priors
schema_version: 1
rule_type: case_distilled
applies_to:
  cazy_class: ALL                # 跨 CAZy 与 non-CAZy
  enzyme_family: ALL
  property: substrate_specificity
evidence_cases:
  - GT1-williams-2007-natchembiol      # OleD directed evolution
  - PL1-charnock-2002-pnas             # PL1 mechanism
  - CE7-vincent-2003-jmolbiol          # CE7 hexamer + dual substrate
  - AA9-frandsen-2016-natchembiol      # AA9 LPMO substrate binding mode
  - LIPASE-magnusson-2005-chembiochem  # CALB W104A rational
  - P450-glieder-2002-natbiotechnol    # BM3 alkane hydroxylase directed evolution
  - TRANSAMINASE-savile-2010-science   # ATA-117 sitagliptin directed evolution
  - KRED-ma-2010-greenchem             # KRED atorvastatin (Codexis cascade)
  - DERA-greenberg-2004-pnas           # DERA atorvastatin (metagenomic + DE)
  - PROTEASE-hedstrom-1992-science     # trypsin → chymotrypsin loop transplantation (specificity multi-determinant principle)
  - MAO-carr-2003-angewchem            # MAO-N evolved (S)-amine oxidative resolution
  - NITRILASE-desantis-2003-jacs       # Diversa metagenomic library + DE for chiral acid synthesis
confidence: high                       # 12 evidence cases 跨 5 CAZy classes + 7 non-CAZy enzyme families (lipase/P450/transaminase/KRED/DERA/protease/MAO/nitrilase) + 5 strategy types (rational / DE / structure-guided / metagenomic / loop_transplantation)
last_updated: 2026-04-27
---

## 规则 — Substrate Scope 工程化跨家族原则

(从 9 个 evidence cases 蒸馏, 跨 GT/PL/CE/AA/non-CAZy)

### 策略选择决策树

```
新 substrate scope 任务
├── 是否有目标 enzyme 的高质量结构 + 已识别 substrate-binding pocket "lid" 残基?
│   ├── 是 + lid 是 single Trp/Phe/Tyr → Single-point rational design 优先
│   │   (Magnusson 2005 CALB W104A 模板)
│   └── 否 → Directed evolution 路线
├── 是否有 ≥3 已表征的 ortholog?
│   ├── 是 → Structure-guided library + DE (Codexis 模板, Savile 2010)
│   └── 否 → Metagenomic ortholog screen + DE (Greenberg 2004 DERA 模板)
├── 是否是 pharmaceutical bulky substrate (大型, 远 from native scope)?
│   ├── 是 → 期望 20+ accumulated mutations, 工业 platform (Codexis 类) 必要
│   └── 否 → 5-10 mutations 通常够, 学术 directed evolution 可行
├── 是否需要 cofactor 协同?
│   └── 是 (KRED/P450/TA 类 NADPH/PLP/heme) → cofactor recycle enzyme 共同优化
└── 反应在 cascade 中?
    └── 是 → simultaneous engineering, 不能串行 (KRED 2010 模板)
```

### 普适操作约束 (跨所有 9 cases 一致)

1. **强制排除区** (绝对禁区, 改了必失活):
   - Catalytic 残基 (Ser-His-Asp triad / catalytic Glu/Asp / Cys axial / PLP-Lys / Schiff base Lys 等家族特征)
   - Cofactor binding pocket 一级 sphere (NADPH Rossmann fold / heme pocket / PLP phosphate loop / Cu His brace)
   - Oligomer interface (TA dimer / CE7 hexamer / SDR tetramer)
   - Signal peptide / leader sequence

2. **Dual-screen 是 mandatory** (单 screen 必失败):
   - Activity + selectivity (ee% / regio %) 同时
   - Pharmaceutical substrate: + organic solvent 兼容 + thermostability

3. **High-throughput screen 是 enabler 关键**:
   - 没有合适 readout, directed evolution 效率指数下降
   - Surrogate substrate (e.g., p-nitrophenoxyalkane for P450, UDP-detection for GT) 是常见 enabler
   - 但顶级 hits 必须用真实 substrate 验证

4. **结构引导 initial library** vs **random library**:
   - 有结构: 起手 saturation library on active site ±5-8 Å residues, 大幅压缩 rounds
   - 无结构: AlphaFold prediction 作起点 (近年已成 viable alternative)

5. **Industrial vs academic engineering 是不同 game**:
   - Academic: few mutations, mg-scale substrate, 优化 turnover number
   - Industrial: 20+ mutations, g/L 级 substrate, 优化 productivity (g product / g enzyme / hr)
   - 两者评估 metric 不通用; Sitagliptin/Atorvastatin 案例显示工业必须 g/L 级 final 验证

## 依据

| evidence_case | 关键观察 | 支持的 sub-rule |
|---------------|---------|----------------|
| GT1-williams-2007 | OleD acceptor scope 100-1000× 扩展 via DE + UDP screen | DE + HT screen 是 GT 主路 |
| LIPASE-magnusson-2005 | CALB W104 单点改 → large secondary alcohol 接受 | rational single-point in well-characterized lipase |
| P450-glieder-2002 | BM3 alkane hydroxylase needs ~10-15 累加 mutations | DE + surrogate screen, multi-mutation accumulation |
| TRANSAMINASE-savile-2010 | ATA-117 → sitagliptin 27 mutations, 工业 platform | structure-guided library + 工业 dual-screen |
| KRED-ma-2010 | Atorvastatin cascade: KRED + HHDH + GDH 同步 | cascade simultaneous engineering |
| DERA-greenberg-2004 | DERA double aldol 工程化 via metagenomic + DE | metagenomic ortholog + tolerance engineering |
| CE7-vincent-2003 | CE7 dual-substrate 由 open active site 几何决定 | 结构指导工程化必看 active site openness |
| AA9-frandsen-2016 | LPMO substrate scope 由 surface flat patch 决定 | 不是 pocket-binding 类 enzyme 工程化逻辑差异 |
| PL1-charnock-2002 | PL1/PL10 convergent mechanism, fold 不同同问题 | 跨 fold 经验有限, 选 chassis 时确认 fold |

## 边界

- 不适用 **酶完全失活** 类 destabilizing 改造 (active site geometry 全打散)
- 不适用 **cofactor swap** (e.g., NADPH → NADH preference 改, 见专门 rule)
- Membrane protein (跨膜 enzyme) 工程化 strategy 不同, 这里覆盖的是可溶 enzymes
- 已知反例: AA9 LPMO 的 substrate scope 不是 pocket-binding 类型 (是 flat surface), single-point 不太管用 — 与 lipase/P450 类 pocket enzyme 区别

## How to apply

- **Design Agent**: 用决策树选策略 (rational vs DE vs structure-guided)
- **Reviewer (Gate 2)**: 检查 design_plan 是否:
  - 显式排除 catalytic + cofactor + interface 区
  - 包含 dual-screen 设计
  - 选择了与 enzyme 类型匹配的 strategy (e.g., 对 P450 不要 expect single-point)
- **Reporting Agent**: 从此 rule 引用 cross-case 原则解释结果

## 升级路径

升至 confidence: very_high 需要再增 ≥3 evidence cases 跨 3+ 个新 enzyme family (e.g., monooxygenase 非 P450, hydratase, amidase 等), 且包含 ≥1 个明显反例 (推翻某子规则)。
