---
rule_id: 18-cellulase-cross-family-landscape
schema_version: 1
rule_type: landscape
applies_to:
  cazy_families: [GH5, GH6, GH7, GH8, GH9, GH12, GH45]   # 跨纤维素酶常见家族
  cazy_class: GH
  property: thermostability_and_activity
  enzyme_classes: [hydrolase]
evidence_cases:
  - GH7-heinzelman-2009-pnas             # SCHEMA chimera
  - GH7-voutilainen-2010-prot-eng        # rational mutation transfer
  - GH7-goedegebuur-2017-jbc             # directed evolution + MD
  - GH8-anbar-2012-aem                   # consensus-guided
  - GH6-koivula-2003-biochem             # pH engineering (Cel6A)
  - GH45-davies-1995-biochem             # textile cellulase (Humicola Cel45A)
confidence: medium                       # 6 evidence cases 跨 4 家族 + 跨 fold
last_updated: 2026-04-28
---

## 规则

纤维素酶工程化按以下家族-fold 决策树:

1. **必先识别 fold + mechanism + mode**:
   - **GH7** ((β/α)8 + β-jelly roll): retaining cellobiohydrolase (CBHI), processive exo, 双 Glu 催化对; 工业 cocktail dominant
   - **GH6** ((β/α)8 with closed tunnel ββ' loop): inverting cellobiohydrolase (CBHII), processive exo, 单 Asp + 远端 base; 与 GH7 互补
   - **GH5** (TIM barrel): retaining endoglucanase, 双 Glu pair; 细菌主流
   - **GH8** ((α/α)6 toroid): inverting endoglucanase, 单 Asp + 单 Glu; cold-active
   - **GH9** (TIM barrel + Ig domain): inverting cellobiohydrolase, processive; 细菌 cellulosome
   - **GH12** (β-jelly roll, 小): retaining endoglucanase, 双 Glu, 紧凑
   - **GH45** (six-strand β-barrel, 小): inverting endoglucanase, 单 Asp + 远端 base; textile alkaline 来源
2. **目标决定家族选择**:
   - Industrial cellulose biorefinery (高 throughput, ~50 °C, pH 5): GH7 + GH6 + GH5 (Trichoderma cocktail)
   - Textile alkaline (pH 9, 60 °C): GH45 (Humicola insolens) > GH7 (无 alkaline 适应)
   - Cellulose nanocrystal (CNC) 制备: GH7 processive exo (产物均一)
   - Cold-active 应用 (低温 detergent): GH8 (cold-adapted)
3. **跨家族 mutation 转移率低 (<30%)**: GH 家族 fold + mechanism 差异显著, 同 family 内转移率较高 (50-70%)
4. **Inverting (GH6/8/9/45) vs retaining (GH5/7/12) 工程化策略不同**: retaining 双 catalytic glu pair 排除 mask, inverting 单 Asp + 远端 water-mediated base 排除 mask
5. **小蛋白 (~200 aa, GH45 / GH12) 工程化敏感于 mutation 累积**: ≥4 mutation stacking 必须实验 yield + Tm
6. **Tunnel topology 决定 processive vs endo mode**:
   - Closed tunnel (GH7 / GH6): processive exo
   - Open cleft (GH5 / GH9 / GH12 / GH45): endo

**强制排除区** (cross-family 共通):
- **catalytic acid/base (Asp 或 Glu)**: 严格保留, fold-specific
  - GH7 retaining: E212 + E217 类 双 Glu
  - GH6 inverting: D175 + D221 类 双 Asp
  - GH5 retaining: 双 Glu pair
  - GH8 inverting: D + E pair
  - GH45 inverting: 单 Asp + water-mediated base
- **Substrate-binding tunnel / cleft aromatic Trp/Tyr**: 保留, 决定 processivity + substrate orientation
- **Disulfide bridges** (常见于真菌 cellulase): 保留, 拆即 misfolding
- **N-glycosylation site** (真菌来源 cellulase): 真菌 host 表达必需, 转 prokaryotic host 失败

## 依据

| evidence_case | 关键观察 |
|---------------|---------|
| `GH7-heinzelman-2009-pnas` | SCHEMA 块重组 +10 °C; 同家族 ortholog 多 (≥3) 是前提 |
| `GH7-voutilainen-2010-prot-eng` | 跨 ortholog rational mutation 转移率 30-50%; 同家族即可 |
| `GH7-goedegebuur-2017-jbc` | 13 round DE 接 MD 验证, 提升 thermostability + 活性 |
| `GH8-anbar-2012-aem` | Cel8A consensus + Cα geometry filter; (α/α)6 toroid fold 不同 GH7/11 但 consensus 协议通用 |
| `GH6-koivula-2003-biochem` | TrCel6A pH 工程化, active site Asp pair pKa 调; 单点 ΔpH < 0.5 unit, 多 mutation 累积达 +2 unit |
| `GH45-davies-1995-biochem` | HiCel45A 是 alkaline 工业 cellulase 的天然 chassis; 6-strand β-barrel fold, mutation tolerance 受 small protein 限 |

## 边界

- 仅 GH 类水解纤维素酶; LPMO (AA9/10) 是 oxidative 类, 单独 landscape
- **跨 GH 家族 mutation 转移率 < 30%** (GH7 ↔ GH6 ↔ GH45 各有独立 fold)
- **小蛋白 (< 250 aa) 工程化 ≥ 4 mutation 必须验证 epistasis**(见反例 NEG-EPISTASIS)
- 真菌 cellulase 必须真菌 / Pichia / 类似 host 表达; E. coli 失败
- **Industrial PT (process tolerance) ≠ lab Tm**: 工业 application 必须直接测试 process condition (类 NEG-DRIFT-tokuriki-2009 反例)
- pH 工程化是 GH6 active site Asp pair 主线; GH7 双 Glu 工程化 pH 困难

## How to apply

- **Scoping Agent**: 识别用户目标 (substrate / 温度 / pH / 应用) → 选家族 chassis
- **Design Agent**: 应用 fold-specific mask + 选 strategy (SCHEMA / consensus / DE / pH engineering / disulfide); 跨家族转移 explicit 标 'cold_start cross-family'
- **Execution Agent**: 真菌来源 cellulase 必须 Pichia / fungal host 表达
- **Reviewer**: 检 fold-specific catalytic mask + 表达 host 适配 + (≥ 4 mutation) epistasis 验证 + process condition 测试

## 升级路径

升 `confidence: high` 需要再增 ≥2 evidence cases (建议补 GH5 + GH9 / GH12) + 至少 1 跨家族 mutation 转移失败案例.
