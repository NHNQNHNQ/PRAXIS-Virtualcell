---
name: thermompnn_stability
description: ThermoMPNN 基于 MPNN 表征的单点 ΔΔG 预测(零样本)。比物理-based(PyRosetta cartesian_ddg)快 1000x,适合 first-pass 筛选 → 用 PyRosetta 复核 top-N。
status: green
host_env: thermompnn
maturity: stub
note: 自动生成的占位 SKILL.md(SOFTWARE-GAP-REPORT v2 §7);该 env 在 .53 staging 已装,
  待人工补充 SOP / 输入输出契约 / SOP / 失败模式。
---

# thermompnn_stability

ThermoMPNN 基于 MPNN 表征的单点 ΔΔG 预测(零样本)。比物理-based(PyRosetta cartesian_ddg)快 1000x,适合 first-pass 筛选 → 用 PyRosetta 复核 top-N。

## 状态

**stub** — 仅声明该 staging env 的能力,让智能体能在 system prompt 中看到此 skill 候选。
具体 SOP / 输入输出契约 / run.py 实现待补。

## 建议下一步

1. 进 staging 该 env (`conda activate thermompnn`) 看 `pip list` / `which`,确定真有的入口工具。
2. 写一个跑得起来的最小 demo(可参考同 brain 内其他成熟 skill 的结构)。
3. 把 stub 标记从 `maturity: stub` 升到 `maturity: draft` → `maturity: production`。

## 输出契约

```json
{
  "skill_id": "thermompnn_stability",
  "wt_score": 0.0,
  "scan_csv": "",
  "top_mutations": [
    {
      "position": 1,
      "from_aa": "A",
      "to_aa": "V",
      "ddg": 0.0
    }
  ],
  "diagnostics": {
    "brain": "protein",
    "archetype": "mutation_scan"
  }
}
```
