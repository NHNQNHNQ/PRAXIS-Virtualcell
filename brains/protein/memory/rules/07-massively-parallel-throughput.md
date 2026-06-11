---
rule_id: 07-massively-parallel-throughput
schema_version: 1
applies_to:
  design_tasks: ["de_novo_binder", "enzyme_de_novo_design", "antibody_design", "hallucination_de_novo"]
  fold_classes: ["ALL"]
evidence_cases:
  - "protein-002-rfdiffusion-pdl1-binder"
  - "protein-011-cao2020-lcb-spike-binder"
  - "protein-012-chevalier2017-flu-ha-mini-binder"
  - "protein-018-bennett2023-deep-learning-binder-filter"
  - "protein-020-yeh2023-de-novo-luciferase"
confidence: high
last_updated: 2026-05-01
---

## 规则
**De novo binder + enzyme + antibody 设计任务必须超量设计 (oversampling)**——in vitro 转化率 typically 0.07-15%；不超量则得不到 hit。最低规模：

| 任务 | Min in silico designs | Typical in vitro tested | 备注 |
|---|---|---|---|
| Mini-binder (post-DL filter) | ~1000 | ~50-100 (per target) | Bennett 2023 era SOTA |
| Mini-binder (classical) | ~10000 | ~150-200 | Cao 2020 LCB |
| Massively parallel binder | ~10^4 | ~10^4 (yeast display) | Chevalier 2017 |
| De novo enzyme | ~5000-10000 | ~50-100 | Yeh 2023 luciferase |
| De novo antibody affinity | ~1000 | ~30-100 | Mason 2021 / Hie 2024 |

**单设计 lab 测**永远不应该是 v0 strategy。Reviewer gate 阻塞 single-design recommendations for binder/enzyme.

## 依据
- **protein-002 (Watson 2023 RFdiff PD-L1 binder)**：1000 RFdiff backbone → 5-metric filter 剩 ~50 → visual + in vitro 剩 ~10；in vitro 5-15% 成功；单 design 概率 <1%
- **protein-011 (Cao 2020 LCB spike)**：~10^6 RIF dockings → ~10^5 sequences → ~150 实测 → 2 picomolar；超量 1000x 才达 pM
- **protein-012 (Chevalier 2017 flu HA)**：22,000 designs by oligo chip + yeast display → ~3% FACS positive → ~30 nM-level binder；总 throughput 10^4 needed for diversity
- **protein-018 (Bennett 2023 DL filter)**：每 target 1000-10000 设计 + AF2 initial guess filter；提升 in vitro 转化率到 6-23%（vs 1-2% pre-DL）
- **protein-020 (Yeh 2023 luciferase)**：~7000+ design 跨 substrate；active 率 0.5-1% → 总 useful enzyme ~5

**通用 power-law**：useful design count ≈ in_silico_count × in_vitro_conv_rate；mini-binder typical conv = 5-15% (DL era) → 100 in vitro pass → ~10 useful → 10x oversampling at design stage

## 边界 (★ 必填)
- **Computational budget** 限制时 (e.g., student project)：scale down 但**显式标 reduced-scale**, confidence label 降到 low
- **Repeat / SAR 分析任务**：不需要超量；focused mutagenesis (≤ 50 designs) 适用
- **Targeted modification of existing binder**：affinity maturation via single-point (Hie 2024 PLM)；< 50 designs
- **Test of method / proof-of-concept**：可降到 10-20 designs，but conclusion 不该 generalize
- **Symmetric assembly fold-only**：~10-30 designs 已足够 (case 031 King ~12, case 033 Hsia ~7)；fold 比 binder 容易
- **Cyclic peptide fold-only**：100% rate (case 013)，单 design 可行

## How to apply
- **Scoping**：strategy 输出必须含 `n_designs >= 100` for binder; `>= 50` for enzyme; `>= 30` for antibody
- **Design**：design_plan 必须有 oversampling factor 字段；< 10x in vitro budget → block
- **Execution**：de_novo_binder_pipeline / enzyme skill 强制 default `--n-designs 100` minimum；< 50 raise warning
- **Reporting**：报告必须 explicit "oversampling: in silico N → top-K filter → in vitro M → useful U"；conversion rate 必表
- **Reviewer**：design_plan 中 n_designs < 100 (binder/enzyme) → block，除非用户 explicit `--small-scale` flag + override reasoning
