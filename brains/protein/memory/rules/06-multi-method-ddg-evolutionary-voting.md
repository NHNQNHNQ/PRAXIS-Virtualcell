---
rule_id: 06-multi-method-ddg-evolutionary-voting
schema_version: 1
applies_to:
  design_tasks: ["stabilization", "mutation_effect_prediction"]
  fold_classes: ["ALL"]
evidence_cases:
  - "protein-003-proteinmpnn-thermostab"
  - "protein-004-thermompnn-saturation"
  - "protein-023-goldenzweig2016-pross-stability"
  - "protein-024-bednar2015-fireprot"
  - "protein-027-riesselman2018-evmutation"
  - "protein-028-frazer2021-eve"
confidence: high
last_updated: 2026-05-01
---

## 规则
**ΔΔG 或 mutation effect prediction 必须 ≥ 2 个 method 共识**：物理-based (Rosetta cartesian_ddg / PyRosetta) 和 evolutionary-based (EVmutation / EVE / ESM-1v / ProteinMPNN log-likelihood) 是互补 signals。Single-method 推荐 视为 anti-pattern；Reviewer gate 阻塞 lab 推荐 if 单 predictor used。

更细：
- **稳定化 (stabilization)**：Rosetta_ddG ∩ PyRosetta ∩ MSA-consensus（PROSS/FireProt 经验）；最少 2 vote
- **Mutation effect prediction**：物理 ddG ∪ evolutionary likelihood (EVmutation/EVE) ∪ DL ddG (ThermoMPNN) — 最少 2 vote，理想 3 vote
- **Top-K intersection > top-K union**：精度 80%+ vs 30%-precision 单方 (per protein-004 benchmark)

## 依据
- **protein-003 (Watson 2023 ProteinMPNN-DHFR)**：单 ProteinMPNN 不预测 ΔΔG；联合 Rosetta + ThermoMPNN 三方投票 (3/3 = 高 confidence, 2/3 = 中)；活性突变在 single-method 上经常 false positive
- **protein-004 (ThermoMPNN saturation, SNase 600 mut)**：单 ThermoMPNN Spearman ~0.65；ThermoMPNN ∩ Rosetta intersection 把 precision 拉到 80%+，single-method precision 30%
- **protein-023 (PROSS Goldenzweig 2016)**：明确"双轨过滤"——MSA evolutionary consensus (≥10x freq) + Rosetta cartesian_ddg < -1 kcal/mol；PROSS server 是这条 rule 的产品化
- **protein-024 (FireProt Bednar 2015)**：PyRosetta cartesian_ddg + Rosetta cartesian_ddg 必须双 method 共识；single 假阳率 30-50%；双共识降到 ~10%
- **protein-027 (EVmutation Riesselman 2018)**：DCA + Rosetta cartesian_ddg ensemble 把 Spearman 从 0.5-0.6 拉到 ~0.7
- **protein-028 (EVE Frazer 2021)**：deep VAE evolutionary 在 ClinVar pathogenicity 上 AUC 0.91；与 ddG predictor 互补可达 ~0.93

## 边界（★ 必填）
- **Cold-start (n_cases < 3)**：本规则可降为 advisory；用户需 explicit 确认
- **MSA 浅 (< 50 effective sequences)**：evolutionary track degrade；单 ddG predictor 可接受但报告 low_confidence
- **Indel 突变**：EVmutation/EVE 不支持；只 Rosetta 或 ProteinMPNN log-likelihood
- **Surface vs buried**：surface mutation 上多 method 都不准 (Spearman <0.5)；分层报告
- **Catalysis-modulating mutations**：ddG 不抓 catalytic effect；需要 enzyme-specific assay
- **Multi-point > 2 mutations**：epistasis 破坏 additivity；single-mutant ddG sum 不可信

## How to apply
- **Scoping**：design strategy 必须列 ≥ 2 predictor (e.g., "ThermoMPNN + Rosetta cartesian + EVmutation")
- **Design**：mutation_library 每条 mutation 必须有 ≥ 2 method ΔΔG / fitness scores
- **Execution**：mutation_effect_scan skill default `--predictors ThermoMPNN,Rosetta,EVmutation`；single-predictor 拒绝
- **Reporting**：top-N 推荐表必须显示每 method 的 score；intersection vs union 标注
- **Reviewer**：检测 design_pipeline 中只有 1 ΔΔG/fitness predictor → block；高 confidence 推荐 (lab 实测) 必须 ≥ 2 method 同时 favor
