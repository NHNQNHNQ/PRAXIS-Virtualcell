---
rule_id: _default_bootstrap
schema_version: 1
scope: bootstrap
applies_to:
  perturbation_type: ALL
  species: ALL
  task: ALL
evidence_cases: [vcell-001]
confidence: medium
rule_type: cross_task_priors
provenance:
  source_type: synthesis
  source_path: synthesis/virtualcell-bootstrap.md
  extracted_at: 2026-06-11
---

# virtualcell — 冷启动通用先验

任何 virtual-cell 任务在没有任务专属 rule 命中时,遵守以下先验(Week 3/5 起由真实 cases 扩充)。

## 1. 公开 benchmark 必同表对比

**How to apply**:任何 predictor / Coordinator 的论文级 claim,至少在 1 个公开 benchmark(Norman / Replogle / Sciplex / E.coli / yeast)上跑通,且与 ≥3 baseline 同表对比。

## 2. 跨物种迁移先查负迁移经验

**How to apply**:把某物种训练/验证的模型用到另一物种前,先查 negative-transfer 经验;缺经验则默认保守,倾向 abstain 而非强行外推。

## 3. simulated 产物自标

**How to apply**:预测 / 仿真产物必须标 `simulated`,不与实验数据混表、混库。

## 4. 强基线下诚实报告 abstain 收益

**How to apply**:abstain 卖点以 accepted-set 增益 + (mean − std) > 0 为准;增益小就如实写"强基线下空间收窄",不夸大。

---

每条 recommendation 末尾给 `confidence: {cold_start | low | medium | high}`,并说明来源(命中几条 case/rule、是否有 benchmark anchor)。
