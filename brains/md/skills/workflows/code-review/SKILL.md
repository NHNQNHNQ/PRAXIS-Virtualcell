---
name: workflow-code-review
description: 面向科研脚本与分析流程的代码审查工作流。适用：检查分析脚本、统计脚本、图表生成脚本的正确性与可复现性。
---

# 代码审查 Skill

## 审查重点

- 输入文件路径是否真实存在
- 统计口径是否一致
- 是否混入不同任务集或不同批次数据
- 图和表是否来自同一数据源
- 是否存在硬编码、手工补值和不可追溯修改

## 输出格式

1. 发现的问题（按严重性排序）
2. 对结果的影响
3. 建议修复方式
4. 是否需要补充验证

## 科研场景常见问题

- benchmark 与历史 case 混算
- 图 B 和图 C 口径不同
- case 名映射错误
- 轨迹分析前未做 PBC 校正
- 误把派生分数当作原始主分

## 输出契约

```json
{
  "ok": true,
  "skill_id": "code-review",
  "result": {},
  "diagnostics": {
    "brain": "Naruto-main",
    "archetype": "generic"
  }
}
```
