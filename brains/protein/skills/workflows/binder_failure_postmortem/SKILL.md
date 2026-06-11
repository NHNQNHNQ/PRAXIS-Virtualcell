---
name: binder_failure_postmortem
description: Tag in vitro failures into 4-axis taxonomy (misfold/aggregation/non-binder/weak-binder)
status: green
host_env: praxis-protein
---

## 一句话原则
真实分析驱动 — 不是"训了个模型"; 把湿实验结果按 protein-010 4-axis taxonomy 分类，feed back 到 cases；揭露 in silico metric 与 in vitro success 的 < 0.5 correlation gap。

## 适用场景
- design_task == binder_validation_post_mortem
- 已有 design_pipeline 输出 + in vitro 结果 (LIMS envelope)

## 不适用
- ❌ 还没有 in vitro 数据时 — 先跑湿实验
- ❌ Non-binder design (e.g. enzyme variant) — 用 PRAXIS-Enzyme 的对应工具

## 环境检查
仅 Python 标准库 + project schema。无外部依赖。

## 输入契约
```json
{
  "design_results_json": "runs/<task>/de_novo_binder/.../result.json",
  "wet_lab_envelope_jsonl": "runs/<task>/wetlab_data/_validated/*.json",
  "out_dir": "..."
}
```

## 输出契约
```json
{
  "n_designs": 47,
  "n_in_vitro_tested": 24,
  "failure_tags": {
    "expression_failure": 9,    // ~40%
    "misfold": 5,                // ~20%
    "non_binder": 7,             // ~30%
    "weak_affinity": 2,          // ~10%
    "success_high_affinity": 1
  },
  "metric_correlation_to_success": {
    "pLDDT_binder": 0.31,
    "iPTM": 0.42,
    "Rosetta_ddG": 0.28,
    "SAP_score": -0.51,
    "ESM2_PLL": 0.48
  },
  "case_writeback_proposal": {
    "should_write": true,
    "draft_case_id": "binder-<target>-<batch>-postmortem",
    "lessons": ["...", "..."]
  },
  "provenance": {"simulated": false}
}
```

## QC gate
- 至少 5 in vitro samples 才有 statistical sense；< 5 emit warn
- All 4 failure axes counted (even if 0)
- Write-back to memory/cases/_proposed/ as draft

## 实现状态
- ✅ SKILL.md
- ✅ runner.py — **fully real (pure Python + pandas-style aggregation)**
- ✅ All work complete; no GPU required
