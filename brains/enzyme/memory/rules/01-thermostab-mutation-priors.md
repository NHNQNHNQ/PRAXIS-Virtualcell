---
rule_id: 01-thermostab-mutation-priors
schema_version: 1
rule_type: case_distilled
applies_to:
  cazy_families: [GH7, GH8, GH11]  # 已验证三个家族
  cazy_class: GH                    # class 级别也适用
  property: thermostability
evidence_cases:
  - GH7-heinzelman-2009-pnas        # SCHEMA chimera
  - GH7-voutilainen-2010-prot-eng   # rational mutation transfer (T. emersonii)
  - GH7-goedegebuur-2017-jbc        # directed evolution + MD validation
  - GH8-anbar-2012-aem              # consensus-guided mutagenesis (Cel8A, 不同 fold)
  - GH11-turunen-2002-jbiotechnol   # disulfide + surface Arg synergistic
  - GH11-fenel-2004-jbiotechnol     # N-terminal disulfide
  - GH11-hakulinen-2003-eurjbiochem # 12-xylanase comparative (provides selection criteria)
confidence: high                    # 7 evidence cases 跨 3 GH families + 含 4 种独立工程策略 (SCHEMA / consensus / directed evolution / disulfide), 跨 fold (β-jelly roll GH7/GH11 + (α/α)6 toroid GH8)
last_updated: 2026-04-27
---

## 规则

GH 家族酶热稳定性工程的位点筛选,优先级由高到低:

1. **块级重组 (SCHEMA / chimera)**: 当目标酶有 ≥3 同家族 ortholog 且至少 1 个 thermostable 时,优先尝试结构引导重组而非定点突变
2. **Disulfide engineering (β-fold 优)**: 在 alpha-helix 与相邻 loop 间引入 Cys 对 (Cα 距离 5-7 Å), GH11 / GH7 类 β-jelly roll/sandwich 普遍适用
3. **Surface Lys/Ser/Thr → Arg substitution**: 增加 surface salt-bridge 与 cation-π 网络;能稳态加分但单点增益小 (~+1°C/突变)
4. **Consensus mutation + PyRosetta 过滤**: 表面残基 RSA > 0.3 + PyRosetta ΔΔG < -1.5 kcal/mol;作为 baseline 起手
5. **Synergistic combinations**: 弱 stabilizing 突变与 disulfide 组合可超线性叠加 (Turunen 2001 J Biotech 关键发现)

**强制排除区** (跨案例一致):
- 活性位点催化残基 ±5 Å (GH7 E212/E217, GH11 E86/E177 类)
- 糖基化位点 ±3 残基 (case GH7-Voutilainen 与 starter case 共证)
- 信号肽区 (1-17 typical)
- Substrate-binding subsite 残基 (-7 ~ +2 along polysaccharide chain for cellulases)

## 依据

| evidence_case | 关键观察 |
|---------------|---------|
| `GH7-heinzelman-2009-pnas` | SCHEMA 块重组在 GH7 cellulase 上获得 +10°C 量级 Tm 提升;m_disruption 是表达成功率的强预测器 |
| `GH7-voutilainen-2010-prot-eng` | 跨 ortholog rational mutation transfer 命中率 30-50%;Tm 与活性可同时提升 |
| `GH11-turunen-2002-jbiotechnol` | Disulfide bridge + multiple surface Arg 在 GH11 xylanase 获得 +10-15°C synergistic 提升 |

## 边界

- **仅适用 GH 家族**;GT/PL/CE/AA 各有专属 landscape rule (见 `memory/rules/cazy-class-overviews/`)
- 4+ 突变组合需 MD 校验非加性 (从 Heinzelman SCHEMA 与 Turunen synergism 反向推论)
- 低表达突变体 (yield < 50% WT) 不可信 Tm 数据 — 跨 3 个 case 一致警告
- pH optimum shift 是 surface charge engineering 的常见副效应 (Turunen 案例显式记录) — 应用场景敏感时必须监测
- TIM barrel fold (e.g., GH13) 类不适用 disulfide engineering 规则 — fold 限制

## How to apply

- **Design Agent**: 在突变扫描后,按上述优先级与排除区给候选打"通过/排除"标
- 生成 `design_plan.json` 时,对排除位点必须填写 `excluded_positions[].reason` 字段,并引用具体 evidence_case
- 优先级 1-2 的策略 (SCHEMA / disulfide) 需要相应数据资源 (≥3 ortholog 序列 / 高分辨结构),Agent 在 scoping 阶段需评估
- **Reviewer (Gate 2)**: 检查 design_plan 是否遵守此规则;若违反,触发 required_repairs

## 升级路径

升至 `confidence: high` 需要再增 ≥3 evidence_cases 跨 ≥3 个 GH 家族,且包含至少 1 个明显反例(被推翻的子规则)。
