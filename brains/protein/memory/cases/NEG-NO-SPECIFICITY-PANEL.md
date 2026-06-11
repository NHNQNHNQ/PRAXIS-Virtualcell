---
case_id: NEG-NO-SPECIFICITY-PANEL
neg_pattern: binder_design_without_paralog_negative_design
design_task: de_novo_binder
target_pdb: 4Z18
target_uniprot: Q9NZQ7
fold_class: any
tools: [AlphaFold-Multimer]
key_paper_doi: 10.1038/s41586-022-04654-9
key_metrics:
  cross_bind_paralog_rate: "30-40% of strong-iPTM PDL1 binders cross-bind PDL2 (case-034 真验证)"
  affected_designs_in_PRAXIS_034: "design_0134 + design_0135 — iPTM drop only 9-10%"
status: failed
schema_version: 1
source: praxis_neg_pattern
extracted_at: 2026-05-04
tags: [NEG, anti-rule, specificity, negative-design, paralog, PDL1-PDL2, cross-binding]
---

# NEG: binder 设计不做 paralog negative panel

## ★ 失败模式
- Anti-PD-L1 binder 设计只 cite PDL1 metric，不测 PD-L2 (37% identity paralog)
- case-034 真数据: 5 个 PDL1-PASS 中 2 个 (0134, 0135) PDL2 iPTM 下降仅 9-10% → cross-bind
- 临床后果: 同时阻断 PDL2 → 免疫副作用 (autoimmune-like)
- 高 PDL1 iPTM 不等于 PDL1 specific

## ★ 排除/禁止
- 不允许 binder report 不含 specificity panel
- 不允许只 PDL1 iPTM ranking → ship in vitro
- 必须报告 paralog/family 至少 1 个 negative target 的 iPTM
- specificity_drop = PDL1_iPTM - paralog_iPTM 必须 > 0.4 才算 "GOOD"

## ★ 方法选择决策链（反向）
- 正确（case-034 验证）: PDL1 iPTM ≥ 0.6 + PDL2 iPTM drop ≥ 0.4
- 错误: 只看 PDL1 iPTM 排序 → top binder 可能 cross-bind

## Anti-pattern triggered
等价 anti-rule 10 (top-1 ship 无验证) + rule 09 violation (multi-modality validation 缺 specificity modality)

## Evidence cases
- protein-002 (Watson 2023, specificity 警告但未 enforce)
- protein-010 (Cao 2022 post-mortem, paralog cross-bind 是 dominant 失败模式)
- protein-025 (Mason 2021 antibody specificity, mammalian display + paralog panel mandatory)
- protein-034 (PRAXIS self-generated, 直接证据)
