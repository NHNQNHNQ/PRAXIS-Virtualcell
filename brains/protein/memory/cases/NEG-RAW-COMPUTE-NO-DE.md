---
case_id: NEG-RAW-COMPUTE-NO-DE
neg_pattern: pure_de_novo_design_shipped_without_directed_evolution
design_task: enzyme_de_novo_design
target_pdb: nan
target_uniprot: nan
fold_class: any
tools: [Rosetta, ProteinMPNN, RFdiffusion]
key_paper_doi: 10.1126/science.1190239
key_metrics:
  raw_kcat_de_novo_enzyme: "10^-3 - 10^-2 turnover/sec (industrial threshold ~10^2)"
  raw_KD_de_novo_binder: "μM-mM (picomolar = 10^4 worse)"
  improvement_after_DE: "100-10000x typical"
status: failed
schema_version: 1
source: praxis_neg_pattern
extracted_at: 2026-05-04
tags: [NEG, anti-rule, directed-evolution, de-novo, enzyme, binder, mandatory-iteration]
---

# NEG: 纯计算 de novo 设计直接 ship 不接 directed evolution

## ★ 失败模式
- de novo enzyme raw kcat 10⁻³/s (case 020/029/030) — industrial 需 10² 才有用
- de novo binder raw KD μM (case 011 LCB raw 中位 micromolar; LCB1 picomolar 是 outlier 经过 selection)
- "computational only top-1 → ship lab" = 99% 失败
- 缺乏 SSM (site-saturation) + selection 多轮提升

## ★ 排除/禁止
- 不允许 de novo enzyme/binder report 缺 directed_evolution_plan 字段
- 不允许 "industrial-grade" claim 但 raw 是 computational-only
- raw kcat < 10/s 的 enzyme 必须标 "DE follow-up required" 才能进 reporting

## ★ 方法选择决策链（反向）
- 正确（rule 10）: computational design + ≥ 1 round SSM + selection (yeast / phage display)
- 错误: 完全 in silico → 直接 ship → 99% 失败

## Anti-pattern triggered
等价 anti-rule 1 (de novo design 不接 ≥10 round directed evolution); rule 10 violation

## Evidence cases
- protein-011 (Cao 2020 LCB; selection 必经)
- protein-012 (Chevalier 2017; yeast display 内嵌 selection)
- protein-020 (Yeh 2023 luciferase; raw kcat 10⁻³ → DE 100x)
- protein-029 (Siegel 2010 DA; Khersonsky DE 提升 300x)
- protein-030 (Jiang 2008 retro-aldol; Althoff/Giger DE 10000x)
