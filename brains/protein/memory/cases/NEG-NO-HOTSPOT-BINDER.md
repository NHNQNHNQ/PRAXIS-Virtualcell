---
case_id: NEG-NO-HOTSPOT-BINDER
neg_pattern: rfdiffusion_binder_without_hotspot_residues
design_task: de_novo_binder
target_pdb: 4Z18
target_uniprot: Q9NZQ7
fold_class: any
tools: [RFdiffusion, ProteinMPNN]
key_paper_doi: 10.1038/s41586-022-04654-9
key_metrics:
  in_vitro_success_rate: "near zero — binder drifts from epitope"
  motif_RMSD_to_target_hotspot: "uncontrolled (>10 Å typical)"
status: failed
schema_version: 1
source: praxis_neg_pattern
extracted_at: 2026-05-04
tags: [NEG, anti-rule, RFdiffusion, hotspot, binder, no-target-aware]
---

# NEG: RFdiffusion binder 不指定 hotspot residues

## ★ 失败模式
- RFdiffusion 在 ppi mode 中 `ppi.hotspot_res=[]` 或 not set → backbone 不知道 PD-L1/target 上哪里要 bind
- 输出 binder 远离 epitope；in vitro 几乎 0% binding
- 即使 AF2-Multimer 跑通也是 random target surface, 不在设计 hotspot 上
- Rule 02 强制 (mandatory hotspot + paired_msa)

## ★ 排除/禁止
- `ppi.hotspot_res` 为空时直接 abort, raise error
- 不允许"先生成 backbone 再看哪里 bind"
- 不允许从 case 002 / 011 / 018 的 hotspot-aware pipeline 退化

## ★ 方法选择决策链（反向）
- 正确: 先文献 / structural 分析定 hotspot (PD-L1: A56,A115,A125; case 002)
- 错误: 不定 hotspot, 让 RFdiff "自己找"

## Anti-pattern triggered
违反 rule 02 (hotspot mandatory)
等价 anti-rule 1 (de novo design without proper iteration) — 缺 target-awareness

## Evidence cases
- protein-002 (Watson 2023, hotspot mandatory)
- protein-010 (Cao 2022 post-mortem, hotspot-not-occupied = common failure)
- protein-011 (Cao 2020 LCB, hotspot definition was step 1)
