# PRAXIS-VirtualCell P10 历史接手说明

> 状态：`SUPERSEDED P10 HISTORICAL HANDOFF — DO NOT EXECUTE`
>
> 原 P10 接手提示词已被当前 Phase 12–30 顺序状态机取代。旧文本仍保存在 Git
> 历史中；不得从旧阶段编号、旧路径、旧 SHA、旧远程观测或旧授权模板恢复当前动作。

## 当前接手入口

规范工作树：

```text
/Volumes/T7/PRAXIS-virtualcell
```

外置 Git metadata：

```text
/Users/mzy/Projects/.PRAXIS-virtualcell-gitdir
```

当前历史锚点：

```text
P11B product code  bf44aac25b993e49d0146ccd52dddad5c2fa14de
DOCS-CLOSURE parent b02d21985bcde50cf0758d339b05b13bb3e200a2
next numbered phase P12 Virtual Cell Model Zoo v2
```

DOCS-CLOSURE completion SHA 不写入会被该 SHA 自身改变的文档。接手时必须用现场
`git rev-parse HEAD`、parent、exact allowlisted diff、post-commit status 和完成报告
共同验证。P12 尚未实施；只有该 closure identity 成立且用户另发精确 P12 授权时
才能开始。

准确产品承诺是：

> 任意符合显式合同的数据可以制作成 VirtualCellPack 接入；只有存在匹配、可执行且
> 经过验证并获 product policy 批准的模型时才产生预测，否则明确 abstain。

## 当前权威文档

1. [当前项目与集成指南](PRAXIS-VIRTUALCELL-CURRENT-PROJECT-AND-INTEGRATION-GUIDE.md)
2. [Phase 12–30 顺序总提示词](PHASE12-30-SEQUENTIAL-MASTER-PROMPT.md)
3. [Phase 12–30 执行路线](PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md)
4. [Phase 12–30 详细完成清单](PHASE12-30-DETAILED-COMPLETION-CHECKLIST.md)
5. [Phase 12–30 协调提示词](PHASE12-30-MASTER-PROMPT.md)

若摘要、文档和现场 Git 冲突，以 exact local bytes、Git identity 和不可变 artifact
为先；报告差异并停止写操作。

## 永久保护边界

- `/Volumes/T7/PRAXIS-virtualcell/old/**`
- `/Users/mzy/Projects/PRAXIS-virtualcell-p9`
- `/Users/mzy/Projects/PRAXIS-virtualcell`
- `/Users/mzy/Projects/PRAXIS-virtualcell-recovery-20260718`
- `/home/zkyd/data1/mzy/PRAXIS-2` 和现有 gunicorn
- 未获相应独立授权的 GitHub main/tag、历史 refs、`.53`、服务、端口、数据、
  权重、checkpoint、对象存储和外部系统

每轮必须从 `git status --short` 动态生成 staged/modified/deleted/untracked
保护清单。除当前授权 exact allowlist 外，所有用户文件都不得 stage、commit、覆盖
或格式化；远程状态未在当前窗口现场只读刷新时只能称历史记录。
