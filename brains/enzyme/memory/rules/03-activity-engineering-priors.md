---
rule_id: 03-activity-engineering-priors
schema_version: 1
rule_type: case_distilled
applies_to:
  cazy_class: ALL
  enzyme_family: ALL
  property: [activity, kcat_improvement, catalytic_efficiency, thermostability_and_activity]
evidence_cases:
  - HHDH-fox-2007-natbiotechnol         # 4000× kcat via ProSAR (Codexis)
  - GH7-voutilainen-2010-prot-eng       # rational mutation transfer, T. emersonii Cel7A activity + Tm
  - GH7-goedegebuur-2017-jbc            # directed evolution + MD validation (TrCel7A; activity preserved across thermostability)
  - TRANSAMINASE-savile-2010-science    # ATA-117 industrial activity (productivity > 200 g/L)
  - KRED-ma-2010-greenchem              # KRED activity + cascade engineering
  - LIPASE-magnusson-2005-chembiochem   # CALB W104A: substrate scope expansion = activity gain on new substrate
confidence: high                          # 6 evidence cases 跨 5 enzyme families + 4 strategy types
last_updated: 2026-04-27
---

## 规则 — Activity / Catalytic Efficiency 工程化跨家族原则

(从 6 个 evidence cases 蒸馏: 1 GH 直接 activity 工程化案例 + 4 跨非 CAZy 工业级 productivity 工程化 + 1 lipase substrate-scope-driven activity gain)

### Activity 工程化的核心问题

不像 thermostability 或 substrate scope, "activity" 工程化 (kcat / kcat-Km) 较少作为孤立 target — 通常是:
- 产业 productivity 提升 (与 substrate scope / thermostability 同时演化)
- 突变库进化早期就被 selection 保护 (low-activity variants 直接淘汰)
- 后期 ProSAR 类统计方法揭示 distal mutations 的隐藏贡献

因此 rule 03 的内容主要是 "如何不失活" 与 "工业 productivity gating" 而不是 "如何主动提升 activity"。

### 决策树: activity 工程化策略选择

```
任务: enzyme 活性 / productivity 工程化
├── 当前活性是否极低 (kcat <0.01 s⁻¹)? 
│   ├── 是 + 已有 distantly related ortholog → metagenomic / ortholog screen 找 starting point (DERA / nitrilase 路径)
│   └── 是 + 无 ortholog → directed evolution + 高 throughput screen (Glieder BM3 / Williams OleD 路径)
├── 当前活性中等, 需要工业级 productivity (>g/L)?
│   ├── 有 enzyme family 已知工业 platform (Codexis 系列) → 学其策略 (CodeEvolver: structure-guided + ProSAR)
│   └── 是 — 进入大型 directed evolution: ~10-20+ rounds, 累加 20-35+ mutations (Codexis 范式)
├── 是否是 cofactor-dependent enzyme (NADPH / FAD / PLP)?
│   └── 必须 cofactor recycle 共同优化 (KRED + GDH 类 cascade engineering)
└── 是否要保持现有 specificity / ee?
    └── 双指标 selection (activity + ee 或 activity + specificity)
```

### 普适操作约束 (跨 6 cases 一致)

1. **Distal mutations 比预想多**: ProSAR (Fox 2007) 在 35-mutation HHDH 中显示 **~70% 的 beneficial mutations 在 active site 之外** (二级 sphere + surface). 工程化不能只看 active site.

2. **Activity 与 stability/specificity 是 entangled**: 单维 selection 必失败. 工业级工程化必须 dual/triple-screen:
   - kcat + Tm (Goedegebuur 2017)
   - kcat + ee (Savile 2010)
   - kcat + Tm + 表达 yield (Voutilainen 2010)

3. **工业级累加 mutations 的量级**:
   - Substrate scope-only 工程化: ~10 mutations 通常够 (Glieder 2002 BM3)
   - 工业级 activity + scope: 20-35 mutations 是 Codexis benchmark (Savile / Fox / KRED 一致)
   - "Few mutations" 路线 (Magnusson 2005 CALB W104A) 仅在 single key residue identifiable 时 viable

4. **Cofactor recycling 是 hidden gating**:
   - NADPH-dependent enzymes (KRED, IRED, MAO, P450) 工业反应 cofactor cost 关键
   - GDH / FDH (NADPH 再生) 是 cascade 必需元素
   - 改 enzyme 接受 NADH (替代 NADPH) 是 activity 工程化的另一支线 (cost 低 ~10×)

5. **High-throughput screen 决定 directed evolution 效率**:
   - 没有合适 readout, activity 工程化失败率指数上升
   - Surrogate substrate (e.g., p-NPx for hydrolases, UDP detection for GTs, H₂O₂ for oxidases) 是 enabler
   - 顶级 hits 必须用真实 substrate 验证 (避免 surrogate 偏置)

### Activity 工程化"反模式" (★ 必读)

- **改 catalytic 残基期望 kcat 提升**: 几乎必失活. catalytic residue 已经被自然进化优化, 改它会破坏 transition state 几何
- **仅在 active site ±5 Å 找 mutations**: ProSAR 显示 25/35 工业级 beneficial mutations 在 distal 残基; 错失大部分 actionable 空间
- **学术规模 (mg substrate) 评估工业 variants**: 工业反应 condition (g/L substrate, organic co-solvent, 拼接 cofactor recycle) 完全不同
- **单指标 directed evolution**: activity-only selection 必导致 stability / specificity 漂移

### 工业 vs 学术 activity 工程化对比

| 维度 | 学术规模 | 工业级 (Codexis 类) |
|------|---------|---------------------|
| 累加 mutations | 1-10 | 20-35+ |
| Rounds | 1-5 | 8-15 |
| Library size | 10²-10⁴ | 10⁴-10⁶ |
| Selection 维度 | 1-2 | 3-5 (activity + ee + Tm + organic + yield) |
| Enabler | hand-built screen | high-throughput LC-MS / chiral HPLC platform |
| Output | publishable variant | ton-scale process |

## 依据

| evidence_case | 关键观察 | 支持的 sub-rule |
|---------------|---------|----------------|
| `HHDH-fox-2007-natbiotechnol` | 35 mutations / 4000× kcat / 25 在 distal | distal mutations + ProSAR; 工业 platform 范式 |
| `GH7-voutilainen-2010-prot-eng` | Rational few-mutations 同时提 Tm + 活性 | Few-mutation rational 适用 well-characterized homolog |
| `GH7-goedegebuur-2017-jbc` | DE + MD validation, 累加 ~10-15 mutations, activity 保持 | DE + MD 是高质量工业级路线 |
| `TRANSAMINASE-savile-2010-science` | 27 mutations, 工业 productivity (sitagliptin) | 工业大 substrate 必走 ~25+ mutations |
| `KRED-ma-2010-greenchem` | Cascade engineering (KRED + HHDH + GDH) | 多 enzyme cascade 必同步 |
| `LIPASE-magnusson-2005-chembiochem` | W104A 单点突变扩 substrate 即提 new-substrate activity | Single-point 适用 pocket-controlled |

## 边界

- **不适用** sub-second turnover number 的极快 enzyme (如 carbonic anhydrase, catalase) — 这些已近 diffusion limit, 工程化 ceiling 低
- **不适用** ribozymes / ribosomes — 不是 protein
- 已知 caveat: ProSAR 等 statistical 方法需 ≥10⁴ variant data, 学术规模 directed evolution 通常 不到 — 需要 industrial platform 才能用

## How to apply

- **Design Agent**: 用决策树选策略
- **Reviewer (Gate 2)**: 对 activity-工程化任务, 检查 design_plan 是否:
  - 包含 dual-screen 设计
  - 累加 mutations 数量与目标 productivity 匹配 (大宗药级要求 >20)
  - 不仅在 active site ±5Å 找 mutations
  - 显式 cofactor recycle plan (if cofactor-dependent enzyme)
- **Reporting Agent**: 引用 cross-case 原则解释 activity 提升 mechanism (distal vs active site, 协同 cofactor 优化, etc.)

## 升级路径

升至 confidence: very_high 需要再增 ≥3 evidence cases 跨 3+ 个新 enzyme family activity-engineering specifically (不是 substrate scope incidentally)。当前 6 evidence 集中在 hydrolases + reductases, 缺 oxidoreductase / lyase / ligase 类 activity-target cases。
