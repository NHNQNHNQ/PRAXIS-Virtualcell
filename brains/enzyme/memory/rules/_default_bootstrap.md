---
rule_id: _default_bootstrap
schema_version: 1
type: cold_start_defaults
note: 案例库 < 5 时使用; 案例库扩充后逐步被具体规则替代
last_updated: 2026-04-27
---

# 冷启动默认规则

当 `memory/cases/` 中有效案例 < 5 个,无法做有效检索时, Agent 使用以下默认规则。这些是从领域常识总结的最低限度安全准则,**不应替代实际案例学习**。

## 通用 (适用所有 CAZyme 工程化任务)
- 必须先获取 parent 序列 + 至少一个结构 (PDB 或 AlphaFold 预测)
- 必须明确标注 target_property 与可量化 metric (Tm / kcat / Km / 选择性比 等)
- 任何突变设计必须保留 WT 对照
- 活性位点定位通过 CAZy / UniProt 注释 + 文献交叉验证

## 热稳定性 (target_property = thermostability)
- 默认起手: PyRosetta cartesian_ddg 全位点扫描, ΔΔG < -1.0 kcal/mol 入候选
- 表面残基优先 (RSA > 0.3)
- 排除催化残基及其 5 Å 内位点
- 排除糖基化位点 ±3 残基
- 单点验证 5-10 个再做组合
- 4+ 突变需 MD 校验非加性

## 底物专一性 (target_property = substrate_specificity)
- 默认起手: AutoDock Vina / GNINA 对接 WT 与候选突变体, 比较 binding pose 与 ΔG
- 关注活性位点 second shell 残基 (8-12 Å)
- 必须做 ON-target + OFF-target 对照 (双底物或多底物)
- 选择性提升 → ΔΔG_OFF - ΔΔG_ON 作为关键指标

## 活性 (target_property = activity, v0.5+)
- 留待 v0.5 实现; 当前不在范围

## 计算工具默认参数
- AlphaFold 预测: 适用 < 600 aa 序列; > 600 aa 优先用已有 PDB / 同源建模
- PyRosetta: 默认 BuildModel + Stability, RepairPDB 5 轮
- GROMACS: Amber99sb-ildn, TIP3P, 100 ns 默认时长, NPT 等温等压
- Vina: exhaustiveness=16, num_modes=20

## 升级触发
- 当 `cases/` 有 ≥ 5 个案例覆盖某 family/property 组合时, 该组合的默认规则失效
- 当 ≥ 3 个案例支持同一具体规则时, 提升为正式 rule (写到 `memory/rules/NN-...md`)
