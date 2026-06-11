---
case_id: NEG-SINGLE-DDG-PREDICTOR
neg_pattern: stability_or_mutation_prediction_with_single_predictor
design_task: stabilization
target_pdb: 1RX1
target_uniprot: P00374
fold_class: any
tools: [ThermoMPNN, Rosetta_cartesian_ddg, PyRosetta, EVmutation, EVE]
key_paper_doi: 10.1101/2023.07.27.550881
key_metrics:
  single_predictor_spearman: "0.4-0.65 (low precision)"
  precision_top10_single: "30-50%"
  precision_top10_2_method_intersection: "70-80%"
status: failed
schema_version: 1
source: praxis_neg_pattern
extracted_at: 2026-05-04
tags: [NEG, anti-rule, ddG, stability, mutation-effect, single-method, multi-method-mandatory]
---

# NEG: 用单一 ΔΔG / fitness predictor 给 lab 推荐

## ★ 失败模式
- ThermoMPNN 单跑 Spearman ~0.65 — 不可信单点排序
- Rosetta cartesian_ddg 单跑 假阳率 30-50%
- PyRosetta cartesian_ddg 单跑 RMSE ~1.5 kcal/mol (与实验同 scale 噪声)
- 单 method top-10 → ~50% lab 实测无效

## ★ 排除/禁止
- 不允许 mutation_effect_scan / stabilization 任务用单 predictor
- ≥ 2 method 共识 + 物理 + evolutionary 双轨 (rule 06)
- 报告中必须显示每 method 的 score + intersection 标注

## ★ 方法选择决策链（反向）
- 正确（rule 06）: ThermoMPNN ∩ Rosetta + EVmutation/EVE evolutionary; ≥ 2 method 共识 precision 80%+
- 错误: ThermoMPNN top-10 → ship lab

## Anti-pattern triggered
违反 rule 06 (multi-method ddG voting); 等价 anti-rule 4

## Evidence cases
- protein-003 (ProteinMPNN-DHFR; 三方投票)
- protein-004 (ThermoMPNN saturation, single-method precision low)
- protein-023 (PROSS Goldenzweig; MSA + Rosetta 双轨)
- protein-024 (FireProt Bednar; PyRosetta + Rosetta 双共识)
- protein-027 (EVmutation; DCA-only 0.5-0.6)
- protein-028 (EVE; deep VAE evolutionary)
