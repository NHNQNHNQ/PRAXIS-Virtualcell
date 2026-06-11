---
name: crispr_crispor_design
description: CRISPOR sgRNA 设计 + 脱靶预测。已装于 PRAXIS-CRISPR-crispor 隔离 env(crispor 依赖较重,与主 PRAXIS-CRISPR 分离)。
status: green
host_env: PRAXIS-CRISPR-crispor
maturity: stub
note: 自动生成的占位 SKILL.md(SOFTWARE-GAP-REPORT v2 §7);该 env 在 .53 staging 已装,
  待人工补充 SOP / 输入输出契约 / SOP / 失败模式。
---

# crispr_crispor_design

CRISPOR sgRNA 设计 + 脱靶预测。已装于 PRAXIS-CRISPR-crispor 隔离 env(crispor 依赖较重,与主 PRAXIS-CRISPR 分离)。

## 状态

**stub** — 仅声明该 staging env 的能力,让智能体能在 system prompt 中看到此 skill 候选。
具体 SOP / 输入输出契约 / run.py 实现待补。

## 建议下一步

1. 进 staging 该 env (`conda activate PRAXIS-CRISPR-crispor`) 看 `pip list` / `which`,确定真有的入口工具。
2. 写一个跑得起来的最小 demo(可参考同 brain 内其他成熟 skill 的结构)。
3. 把 stub 标记从 `maturity: stub` 升到 `maturity: draft` → `maturity: production`。

## 输出契约

```json
{
  "skill_id": "crispr_crispor_design",
  "n_guides": 0,
  "guides_csv": "",
  "best_guide": {
    "seq": "",
    "cfd_score": 0.0,
    "mit_score": 0.0
  },
  "diagnostics": {
    "brain": "crispr",
    "archetype": "crispr"
  }
}
```
