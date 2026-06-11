# v0.17.0 现状(MCP client + 本地 BashTool · GA)

> **锁定**: 2026-06-03 · **base**: v0.17.0-beta(`7911520`)→ **HEAD** `50f0422`(代码+报告)· tag `v0.17.0` 指向本回填 commit
> **关联文档**:
> - `docs/superpowers/specs/2026-06-02-mcp-client-stdio-design.md` + `docs/superpowers/specs/2026-06-03-bash-tool-local-design.md`(spec)
> - `docs/superpowers/plans/2026-06-03-v017-ga-finalize.md`(GA 收尾 plan)
> - `docs/test-plans/2026-06-03-v017-eval.md`(KPI 复测报告)
> **GitHub**: `main` + tag `v0.17.0` 已 push

---

## 1. 一句话定位

v0.17.0 = 智能体获得**外部 MCP server 工具调用**(stdio)+ **本地 shell 执行**(软沙盒,opt-in)两大能力,GA 收尾补齐端到端集成测试、KPI 复测、文档化软沙盒限制。

## 2. 重要功能 / 改动

- **MCP client(alpha,`f08cf36`)**:stdio transport,常驻连接池,工具名 `mcp__<server>__<tool>`,32 单测。
- **本地 BashTool(beta,`7911520`)**:软沙盒(黑/白/灰裁决 + env 裁剪 + rlimit + cwd 校验),`PRAXIS_BASH_TOOL_ENABLED` 默认关。灰区经 `BridgePermissionAdapter` ASK 弹前端。
- **GA 收尾(本轮)**:
  - 补 ASK→bridge→resolve→run 端到端集成测试(final review I-2)
  - eval 加 safety 判定 + MCP/Bash 4 个 KPI case
  - bash.py timeout_s 非数字 → recovery_hint;清 app.py dead import
  - 版本号 → v0.17.0

## 3. ⚠️ 软沙盒安全限制(prod 启用前必读)

**MVP 是"软沙盒",不是真隔离。** 命令以 server uid 运行。已知边界:跨用户文件读取(同 uid)、shell `cd` 出沙盒、孙子进程逃逸、绝对路径读敏感文件(已黑名单缓解)。

**缓解层**:黑名单挡破坏性命令 + 灰区 ASK 逐条确认 + rlimit 限资源 + 默认关 opt-in。

**多用户 prod 启用 BashTool 的前置 = v0.18 真隔离**(`systemd-run --scope -p MemoryMax= -p CPUQuota=` 或 container/namespace)。当前仅 staging 单机 opt-in 启用。

## 4. 数字对照

| 项 | beta | GA |
|---|---|---|
| 全量测试 | 1887 | 1895 pass(+集成 2 + bash 1 + eval 单测 5 = +8;junit 1981 / 0 fail / 86 skip)|
| 新工具 | MCP + Bash | + 集成测试 2 + eval 单测 5 |
| 版本号 | 0.17.0-beta | 0.17.0 |

## 5. 回滚

`PRAXIS_BASH_TOOL_ENABLED=false`(或不配)+ 不配 `PRAXIS_MCP_SERVERS_JSON` → 行为 == v0.17.0-alpha 之前主链。
