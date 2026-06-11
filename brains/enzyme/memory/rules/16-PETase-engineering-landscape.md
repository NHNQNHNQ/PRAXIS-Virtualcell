---
rule_id: 16-PETase-engineering-landscape
schema_version: 1
rule_type: landscape
applies_to:
  cazy_families: [CE5]                  # CAZy CE5 cutinase / PET hydrolase
  property: thermostability_and_activity
  enzyme_classes: [hydrolase]
evidence_cases:
  - CE5-tournier-2020-nature             # LCC ICCG (Carbios)
  - CE5-yoshida-2016-science             # IsPETase 发现 (foundational scaffold)
  - CE5-lu-2022-nature                   # FAST-PETase (ML-aided 5-mut)
  - CE5-bell-2022-natcatal               # HotPETase (DE 21-mut)
confidence: medium                       # 4 evidence cases 跨 多 chassis + 多策略 (rational disulfide / ML / DE)
last_updated: 2026-04-28
---

## 规则

PET / 高熔点 polyester 解聚酶工程化按以下决策树:

1. **目标温度决定 chassis 选择**:
   - 工业 thermophilic (≥ 65 °C, PET-Tg 附近): **LCC** chassis (起始 Tm ~85 °C, 结构指导 + disulfide engineering 路线)
   - mesophilic-to-thermophilic 渐进: **IsPETase** chassis (起始 Tm ~50 °C, 接 ≥ 17 round DE 推到 ~80 °C)
2. **核心工程化目标是把 Tm 推到 PET-Tg (~70 °C) 之上**: 不达此条件即工业不可用
3. **Disulfide bridge 引入是 small-protein 解聚酶热稳定的 dominant 策略**: Cys pair 设计 (Cα-Cα 4.5-6.5 Å, χ3 ~ ±90°) + PyRosetta/Rosetta 几何筛 + 实验验证
4. **Pocket reshaping 改 substrate 接触模式**: PET binding cleft 浅, surface aromatic / 邻近残基替换可改 PET 接触效率
5. **多种引擎方法各有 niche**:
   - **Rational + 结构指导** (LCC ICCG, 4 mut): 短链路, 起始 chassis 已 thermostable
   - **ML-aided** (FAST-PETase, 5 mut MutCompute): 中等链路, 起始 chassis 中等 Tm
   - **Directed evolution** (HotPETase, 21 mut): 长链路, 起始 chassis Tm 低 mesophilic
6. **5-mutation 内 stacking 多 additive, > 5 必须实验验**: epistasis 上升

**强制排除区** (跨 chassis 一致):
- **catalytic Ser-His-Asp triad** (LCC: Ser165-His242-Asp210; IsPETase: Ser160-His237-Asp206)
- **Oxyanion hole** (主链 NH from Met / Tyr 邻近)
- **核心 disulfide bridge** (LCC 含 1, IsPETase 含 1; 已设计的 disulfide 锁定后不可拆)
- **substrate-binding aromatic patch** (Trp / Phe 关键 PET 接触面 — 仅 explicit 测试后才修改)

## 依据

| evidence_case | 关键观察 |
|---------------|---------|
| `CE5-tournier-2020-nature` | LCC ICCG (4 mut: F243I + D238C + S283C + Y127G) 提 Tm +10 °C 同时提 PET 解聚 turnover ~10×; rational + disulfide + pocket reshape 三轨并 |
| `CE5-yoshida-2016-science` | IsPETase 是 mesophilic 路线 starter; Tm ~50 °C, 必须工程化以达工业 condition |
| `CE5-lu-2022-nature` | MutCompute (3D-CNN ML) 选 5 mut 提 Tm +10 °C; ML 命中率 ~50%, 实验验证必需 |
| `CE5-bell-2022-natcatal` | HotPETase (21 mut, DE) 把 IsPETase 推到 ~80 °C, 显示 mesophilic chassis 也可达 thermophilic; round 数与 ML 比 性价比 trade-off |

## 边界

- 仅适用 CE5 cutinase / PET hydrolase 类; 其他 polyester (PEF / PBT / nylon) 部分共通但需 explicit 验证
- **AF model + PyRosetta 直接排序 mutation 不可信**(见反例 NEG-AFMUTATION-buel-2022 + NEG-FEP-cournia-2017)
- 高结晶度 PET (post-consumer 容器) 仍是 enzyme 工程化外的物理瓶颈; 必须配 amorphization 预处理
- **跨 chassis (LCC ↔ IsPETase) mutation 不可转移** (序列 identity ~50%, 工程化各有 niche)

## How to apply

- **Scoping Agent**: 用户提目标温度 + substrate 类型, 识别 mesophilic / thermophilic 路线
- **Design Agent**: 按 chassis 选 strategy (LCC: rational + disulfide; IsPETase: ML or DE; HotPETase: long DE)
- **Execution Agent**: disulfide 几何筛 (Cα-Cα 4.5-6.5 Å + χ3 ~ ±90°) + pocket reshape 候选; 不依赖 AF model 单独
- **Reviewer**: 检 catalytic triad + oxyanion hole + 已设计 disulfide 排除; 检 simulated PyRosetta 标 simulated; 检 process-realistic substrate (post-consumer PET) 验证

## 升级路径

升 `confidence: high` 需要再增 ≥2 evidence cases (建议: TfH / Thermobifida fusca cutinase, MHETase 工程化 e.g. Knott 2020 PNAS) + 至少 1 个明显反例 (公开报道的 PETase 工程化失败).
