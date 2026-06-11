---
case_id: NEG-NO-ACTIVE-SITE-FREEZE
neg_pattern: proteinmpnn_redesign_without_active_site_freeze
design_task: redesign
target_pdb: 1RX1
target_uniprot: P00374
fold_class: any
tools: [ProteinMPNN]
key_paper_doi: 10.1126/science.add2187
key_metrics:
  activity_loss_rate_when_unfrozen: ">50% loss of catalytic activity"
  binding_loss_when_unfrozen: ">70% loss of substrate binding"
status: failed
schema_version: 1
source: praxis_neg_pattern
extracted_at: 2026-05-04
tags: [NEG, anti-rule, ProteinMPNN, active-site, freeze, redesign, catalytic-residue]
---

# NEG: ProteinMPNN redesign 不 freeze 活性位点 / 催化残基 / 辅因子位

## ★ 失败模式
- ProteinMPNN 不指定 `--fixed_positions_jsonl` → 催化残基被 mutate 成 random aa
- DHFR 案例: 50%+ 活性损失 (case 003)
- enzyme de novo 案例: catalytic geometry 偏离 1-2 Å, kcat 暴跌 100x (case 020, 029, 030)

## ★ 排除/禁止
- 不允许 ProteinMPNN redesign 缺 fixed_positions_jsonl
- catalytic residues 必须显式列在 excluded_positions
- 5 Å radius around active site 都算 frozen
- 辅因子配位 / disulfide / 二聚化界面也必 freeze
- skill `proteinmpnn_redesign` 已 hard-enforce: empty freeze_residues → ERROR (rule 03)

## ★ 方法选择决策链（反向）
- 正确（rule 03）: 分析催化残基 → 写 fixed_positions_jsonl → MPNN 设计周边
- 错误: MPNN 全自由设计 + 期望 active site 自然保留 (50%+ 损失)

## Anti-pattern triggered
违反 rule 03 (active site freeze)

## Evidence cases
- protein-003 (Watson 2023 ProteinMPNN-DHFR; freeze critical)
- protein-020 (Yeh 2023 luciferase; catalytic residues 显式 frozen)
- protein-023 (PROSS Goldenzweig; active site 5Å exclusion)
- protein-029 (Siegel 2010 DA; theozyme catalytic geometry frozen)
- protein-030 (Jiang 2008 retro-aldol; Lys Schiff base 必 frozen)
