"""validation_plan_writer:把主动学习队列渲染成 validation_plan.md(纯展示,确定性)。

铁律:只读 active_learning 队列 + report 现有字段,不重算科学决策、不改裁决;缺字段标 N/A。
这是 advisory「下一步该测什么」的人读版,与 active_learning_queue.json 同源。
"""
from __future__ import annotations

_NA = "N/A"


def _fmt(xs) -> str:
    ys = [str(x) for x in (xs or []) if str(x).strip()]
    return ", ".join(ys) if ys else "—"


def render_validation_plan(queue: dict, *, report: dict | None = None) -> str:
    """queue = active_learning 队列 dict({items, notes})。返回 md 文本。"""
    queue = queue or {}
    report = report or {}
    items = queue.get("items") or []
    lines: list[str] = []
    w = lines.append

    w("# 验证计划(Validation Plan · 主动学习建议)")
    w("")
    w(f"> drug: `{report.get('drug', _NA)}` · abstain: `{bool(report.get('abstained'))}` · "
      "advisory 建议下一步实验,**不改 prediction/verdict 裁决**。")
    w("")
    if not items:
        w(f"- 优先实验候选:`{_NA}`(无可执行候选)")
        w(f"- notes: {_fmt(queue.get('notes'))}")
        w("")
        return "\n".join(lines) + "\n"

    w("| 优先级 | 候选 | action | 类型 | expected_information_gain | 驱动信号 |")
    w("|---|---|---|---|---|---|")
    for i, it in enumerate(items, 1):
        w(f"| {i} | `{it.get('candidate', _NA)}` | {it.get('action', _NA)} | "
          f"{it.get('experiment_type', _NA)} | {it.get('expected_information_gain', _NA)} | "
          f"{_fmt(it.get('drivers'))} |")
    w("")
    w("**理由(rationale)**:")
    w("")
    for it in items:
        w(f"- `{it.get('candidate', _NA)}` — {it.get('rationale', '')}")
    notes = queue.get("notes") or []
    if notes:
        w("")
        w(f"- notes: {_fmt(notes)}")
    w("")
    w("_队列按 expected information gain 降序;打分复用确定性启发式(disagreement/OOD/证据等级/"
      "模块弱支持),非贝叶斯 EIG 严格计算。advisory 不碰终决。_")
    w("")
    return "\n".join(lines) + "\n"


def write_validation_plan(path: str, queue: dict, *, report: dict | None = None) -> str:
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_validation_plan(queue, report=report))
    return path
