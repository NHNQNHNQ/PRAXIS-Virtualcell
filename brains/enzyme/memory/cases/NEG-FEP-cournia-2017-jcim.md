---
case_id: NEG-FEP-cournia-2017-jcim
schema_version: 1
parent_enzyme:
  uniprot: null
  enzyme_family: methodology_critique
  cazy_family: null
  ec: null
  organism: review_anchor
  pdb: null
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: ""
  class: review_anchor / FEP_critique
target_property: substrate_specificity
status: partial
provenance:
  source_type: literature
  doi: "10.1021/acs.jcim.7b00564"
  pmid: 29243483
  citation: "Cournia Z, Allen B, Sherman W (2017). Relative Binding Free Energy Calculations in Drug Discovery: Recent Advances and Practical Considerations. Journal of Chemical Information and Modeling 57(12):2911-2937."
  extracted_at: 2026-04-28
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1021/acs.jcim.7b00564 与 PMID 29243483 我推测; CrossRef 验证"
    - "本论文是 FEP+ (Schrodinger) / OpenMM / GROMACS-FEP 等 relative binding free energy 工具的实践综评"
    - "Cournia / Allen / Sherman 多在 Schrodinger 与学界合作组"
    - "标记反例 (NEG-) 因核心结论是 FEP/ABFE prediction 在 'easy' system 上准确 (RMSE < 1 kcal/mol), 但工业实际 system (柔性 active site / cofactor / 显著 ligand 变化) RMSE 仍 > 2 kcal/mol — 不足 actionable"
    - "对 PRAXIS-Enzyme 反规则: FEP 用于 substrate engineering 排序需要 explicit reservation, 不能直接当 'oracle'"
tags: [FEP, relative_free_energy, ABFE, drug_discovery, NEGATIVE_case, failure_mode_anchor, computational_predictor_critique, Cournia, Sherman, MD_based_prediction]
---

## 1. 背景与目标 — 反例性质
- 背景: Free energy perturbation (FEP) 与 absolute binding free energy (ABFE) 是 MD-based 预测 ligand-protein 亲和力 / 突变效应的现代工具
- 论文 systematic 综评 FEP+ (Schrodinger) / OpenMM / GROMACS-based FEP 的工业 deployment 经验, 包括 SAR ranking, 突变效应预测, scaffold hopping
- 反例核心: **FEP 在 'easy' system (类似 retrospective benchmark) 上 RMSE < 1 kcal/mol, 但 prospective drug discovery 与 enzyme engineering 中 RMSE > 2 kcal/mol** — 数量级误差让 ranking 不 actionable

## 2. 决策过程 (本论文是 review, 综合多个 application case)

### FEP / ABFE 适用 vs 失败的 system 分类
- **'Easy' (FEP 准确)**: 同 chemical series + active site 高度 conserved + 小 ligand 变化 (< 5 重原子) + 无 explicit conformational change
- **'Medium' (FEP 部分准确)**: 不同 chemical scaffold + active site 微调 + 大 explicit water 网络
- **'Hard' (FEP 不准)**: 大 conformational change + cofactor / metal 中心 + 显著 ligand size 变化 + 不同 binding mode

### 主要批评点
- Force field 误差 (< 0.5 kcal/mol RMSE 是 force field 系统极限, 累积到工业级失精度)
- 采样不充分 (long timescale dynamics 不可达, μs-ms 级 conformational sampling 缺失)
- water network 与 ion 处理简化
- Cofactor parameters 多无 high-quality FF, P450 heme / 金属酶常用 generic parameters

### 排除的位点 (★ 必填)
- 本案例为 review-anchor (methodology critique), 不针对单一 enzyme 残基级排除
- Implicit 排除: 任何 'FEP RMSE < 1 kcal/mol' 假定下做工业 enzyme engineering 排序的策略
- Cofactor-dependent enzyme 的 mutation 排序必须 explicit 排除单 FEP run 作为 ranking 信号 (anti-rule)
- Multiple ionization state / binding mode 不 explicit 处理时 FEP 输出排除作为可靠数据

## 3. 失败案例 (★ 必填) — 本案例的核心

- **同 chemical series ranking (FEP 强项) 也常 失败**: 当 ligand 变化引起 binding mode 切换 (新 conformer), FEP rank 顺序与实验完全相反
- **Scaffold hopping (跨化学系列) RMSE > 3 kcal/mol**: 不可用作 ranking
- **Cofactor-dependent enzyme (P450 / 金属酶) 突变效应预测**: heme 周围 mutation 的 FEP RMSE 普遍 > 2 kcal/mol — 对 P450 substrate engineering 不 actionable
- **Active site 显著 conformational change 时 FEP 完全失败**: 多 binding mode 间 sampling 不充分
- **Multiple ionization states 处理简陋**: 一些活性位点 His / Glu pKa 在 binding 状态变化, FEP 单 state simulation 失误
- **Explicit water network 重构慢**: 多 active site water 在 ligand 替换时 reorganize, FEP 短 timescale (~ns) 无法采样到位
- **跨工业 group benchmark 不一致**: 同 system 不同 group 的 FEP RMSE 可差 1-2 kcal/mol — 协议依赖

## 4. 学习收获 — 反规则 / anti-rule
- **成立的反规则 (anti-rule)**:
  - **FEP 'easy' vs 'hard' system 区分必须 a priori 评估**: 看 active site rigidity / cofactor / ligand size 变化范围
  - **Cofactor-dependent enzyme 的 FEP 突变预测 RMSE 高**: 不可单 FEP 排序工程化, 必须 + 实验
  - **FEP RMSE < 1 kcal/mol 仅在 retrospective benchmark 中达到**: prospective application 通常 RMSE 2-3 kcal/mol
  - **Multiple ionization / binding mode 必须 explicit treatment**: 单 state FEP 不可信
  - **Long timescale dynamics 缺失是 fundamental 限制**: 多 conformer sampling 在 ns FEP 不可达
- **被推翻的假设**:
  - "FEP 是 ligand engineering 的 oracle" — RMSE > 2 kcal/mol 在工业 case 不 actionable
  - "FEP 同 series ranking 总准" — binding mode 切换时反例
- **下次类似问题应优先尝试**:
  - FEP 用前先评估 system 'easy / medium / hard' 类
  - 'Hard' system 用 FEP 仅作 'top-N filter', 实验验证 top hits
  - Cofactor system 优先用专属 FF (e.g. P450 heme parameters from Vidossich 等)
- **应避免**:
  - 把 FEP RMSE benchmark 数字 (< 1 kcal/mol) 直接外推到工业 case
  - 单 FEP 排序 ship enzyme engineering 候选
  - Multiple ionization state / binding mode 不 explicit 用 FEP

### Anti-retrieval 信号 (★ 强标记)
本案例进入 indices/anti/: 任何 "FEP RMSE < 1 kcal/mol" 假定下做工业 enzyme engineering 排序被 vetoed; 任何 "P450 / 金属酶 FEP 突变预测不验实验" 被 vetoed; 任何 "FEP 单 state simulation + 不考虑 ionization / binding mode" 被 vetoed.

## 5. 计算 / 实验原始数据
论文综合多个 published FEP 实例 + 内部 Schrodinger benchmark 数据; FEP+ benchmark suite (Wang L 2015 JACS doi 10.1021/ja512751q) 是主要 retrospective 数据源.
