---
rule_id: 19-GT-donor-acceptor-switch-landscape
schema_version: 1
rule_type: landscape
applies_to:
  cazy_families: [GT1, GT2, GT4, GT7, GT8]   # 跨 GT-A / GT-B fold
  cazy_class: GT
  property: substrate_specificity
  enzyme_classes: [transferase]
evidence_cases:
  - GT1-williams-2007-natchembiol        # OleD directed evolution + UDP detection assay
  - GT2-morgan-2013-nature               # BcsA-BcsB cellulose synthase 机制 + translocation
  - GT4-schmolzer-2016-biotechadv        # SuSy biocatalytic glycosylation cascade
  - GT7-ramakrishnan-2002-jbc            # B4GalT1 Y289L donor specificity switch
confidence: medium                       # 4 evidence cases 跨 GT-A + GT-B 两 fold + 跨 donor / acceptor 工程化
last_updated: 2026-04-28
---

## 规则

糖基转移酶 (GT) 工程化按以下决策树:

1. **首先识别 fold (GT-A vs GT-B)**:
   - **GT-A fold**: Rossmann + 短 helix + DXD motif (Mn²⁺/Mg²⁺ 配位); 紧凑 active site, single-residue 'gatekeeper' 控 donor specificity
   - **GT-B fold**: 双 Rossmann domain (N-端 + C-端) + 大 inter-domain cleft; 开放 active site, acceptor scope 易扩
   - 例: GT1 (B), GT2 (A), GT4 (B), GT7 (A), GT8 (A)
2. **GT-A 工程化主战场是 donor specificity (DXD pocket 后端 'gatekeeper')**: 单 mutation 即可 90× switch (B4GalT1 Y289L 范例); 但是 'switch' 不是 'add' (lose native + gain new)
3. **GT-B 工程化主战场是 acceptor scope (大 cleft 容多 acceptor 类型)**: 多 round DE / saturation 在 acceptor pocket 表面 aromatic 残基扩 promiscuity (OleD 范例)
4. **High-throughput UDP detection assay 是 GT 工程化 enabler**: UDP / NDP 释放为通用 readout (UDP + NDP 检测 kit); 缺 readout 时 GT 工程化效率极低
5. **Sucrose synthase (GT4) 是 UDP-Glc 再生 module 的 platform**: 任何 UDP-sugar 依赖 GT 工程化项目, SuSy 是 cofactor regeneration 标配
6. **跨 fold (GT-A ↔ GT-B) mutation 不可转移**: gatekeeper 概念 (GT-A) 与 cleft engineering 概念 (GT-B) 不同
7. **Cofactor / metal 必需在工程化全程考虑**: GT-A 严格依赖 Mn²⁺ / Mg²⁺, mutation 不破 DXD motif

**强制排除区** (cross-family 共通):
- **GT-A**: DXD motif (D-X-D Mn²⁺ binding) + catalytic Asp/Glu (general base for inverting) + UDP nucleotide binding domain (Rossmann fold) + acceptor-binding subsite
- **GT-B**: 双 Rossmann fold core (N-端 + C-端) + UDP/NDP 结合 motif (N-端 Rossmann) + catalytic His/Asp pair
- **GT2 (BcsA, membrane-integral)**: 跨膜 helix bundle + finger helix (cyclic-di-GMP allosteric) + product translocation channel + DDD catalytic triad
- **GT4 (SuSy)**: catalytic Glu (acid/base) + UDP/NDP binding domain + tetramerization interface + N-端调控片段 (plant SuSy)

## 依据

| evidence_case | 关键观察 |
|---------------|---------|
| `GT1-williams-2007-natchembiol` | OleD directed evolution + UDP detection assay 扩 acceptor scope 100-1000×; GT-B fold acceptor pocket loop 是 hot spot |
| `GT2-morgan-2013-nature` | BcsA-BcsB 共晶 + UDP-Glc + 增长 cellooligo: GT2 catalytic + translocation 耦合, finger helix allosteric 控 on/off |
| `GT4-schmolzer-2016-biotechadv` | SuSy 是 UDP-Glc 现场再生 module, 与 downstream GT 级联是制糖工程 master pattern; Acidithiobacillus 来源优于 plant |
| `GT7-ramakrishnan-2002-jbc` | B4GalT1 Y289L (single 'gatekeeper' mutation) UDP-Gal → UDP-GalNAc 90× switch; 但 native 活性下降 ~10× (specificity tradeoff) |

## 边界

- 仅 GT1 / GT2 / GT4 / GT7 等代表 GT 家族; GT3 (glycogen synthase), GT35 (phosphorylase) 等单独 landscape
- **跨 GT-A / GT-B fold mutation 不可转移**
- **'switch' vs 'add' 工程化目标必须 explicit**: single mutation 多 'switch' (lose native, gain new), 'add' 需多 mutation
- **Membrane-integral GT (GT2 BcsA / 类似)** 工程化必须 + transmembrane stability assay
- **Donor regeneration (UDP / GDP / TDP-sugar) 是 system-level 变量**: 不是单 GT 优化可解决 — SuSy / kinase 类 cofactor module 必须配套

## How to apply

- **Scoping Agent**: 识别用户目标 (donor switch / acceptor scope / cofactor regeneration / 等) → 选 GT 家族 chassis
- **Design Agent**: 按 fold (GT-A: gatekeeper single; GT-B: acceptor pocket saturation; SuSy: cofactor module) 选 strategy
- **Execution Agent**: 配 UDP / NDP detection assay (高通量 readout); 跨 fold 转移 mutation explicit 'cross-fold cold_start' 标
- **Reviewer**: 检 DXD motif + catalytic 残基 + (GT-A) gatekeeper / (GT-B) cleft engineering; 检 cofactor regeneration 是否考虑

## 升级路径

升 `confidence: high` 需要再增 ≥2 evidence cases (建议补 GT8 / GT35) + 至少 1 个 GT 工程化失败案例 (e.g. cross-fold 直接转移).
