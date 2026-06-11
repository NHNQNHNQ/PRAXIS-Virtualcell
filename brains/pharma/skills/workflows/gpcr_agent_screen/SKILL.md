---
name: gpcr_agent_screen
description: GPCR-targeted small-molecule 智能体环境(可能包含 docking + structure-aware filtering)。具体能力 TBD,见 staging env 包列表。
status: green
host_env: gpcr-agents
maturity: stub
note: 自动生成的占位 SKILL.md(SOFTWARE-GAP-REPORT v2 §7);该 env 在 .53 staging 已装,
  待人工补充 SOP / 输入输出契约 / SOP / 失败模式。
---

# gpcr_agent_screen

GPCR-targeted small-molecule 智能体环境(可能包含 docking + structure-aware filtering)。具体能力 TBD,见 staging env 包列表。

## 状态

**stub** — 仅声明该 staging env 的能力,让智能体能在 system prompt 中看到此 skill 候选。
具体 SOP / 输入输出契约 / run.py 实现待补。

## 建议下一步

1. 进 staging 该 env (`conda activate gpcr-agents`) 看 `pip list` / `which`,确定真有的入口工具。
2. 写一个跑得起来的最小 demo(可参考同 brain 内其他成熟 skill 的结构)。
3. 把 stub 标记从 `maturity: stub` 升到 `maturity: draft` → `maturity: production`。

## 输出契约

```json
{
  "skill_id": "gpcr_agent_screen",
  "n_compounds": 0,
  "admet_csv": "",
  "diagnostics": {
    "brain": "pharma",
    "archetype": "pharma"
  }
}
```
