# PRAXIS-2 智能体框架测试计划

> 范围：基于 claude-code 内核思想的 query 主循环 + tool registry + brain skills + MCP 接入 + 跨会话记忆
> 当前版本：v0.15.3（2026-06-01）
> 文档生成方式：4 路 Explore agent 并行审计代码库,每条结论带 file:line 证据

---

## 1. 总目标

智能体的关键是「用户提出问题 → 智能体提出方案 → 真找到分析软件环境 → 做真分析」。
之前版本最大的问题：**幻觉太大，不调用工具**。

本文档要测的是：**当前的 PRAXIS-2 在多大程度上真的做到了不幻觉、真调工具、真跑软件**。

---

## 2. 9 项审计与现状结论

| # | 审计点 | 现状 | 关键缺口 |
|---|---|---|---|
| Q1 | 智能体真调工具 vs 幻觉 | ⚠️ 框架已修复，工具暴露给 API，但仅 2/7 工具真注册 | 5 个关键工具未包装 |
| Q2 | 工具 run() / MCP API / 大脑例子软件协议 | ⚠️ 框架成熟，11/13 brain 真能用，**0 个 MCP** | 完全无 MCP client |
| Q3 | 跨会话长时记忆 | ❌ 完全无 | 只有静态 profile + 单会话 transcript |
| Q4 | TerminalTool / 实时数据 | ❌ 无本地 BashTool | 计算全走 SSH → `.53` |
| Q5 | 5h 上下文限制（Claude Code 同款） | ⚠️ 反应式 compact，无定时滚动 | precompact_gate + PTL 异常驱动，非时间窗 |
| Q6 | 第三方 MCP 安装机制 | ❌ 完全未实现 | 需引入 mcp 库 + MCPBridge |
| Q7 | 未安装软件处理 | ✅ 完整 | probe_dependencies + sbatch + SOP 降级 |
| Q8 | query.py 与 Claude Code 内核差异 | ✅ State 更显式，stop_hook 独创，工程严格性优于推测的原版 | M0 串行 ToolRunner，M1+ 预留并发 |
| Q9 | Claude Code skills/MCP 移植 | ⚠️ 格式天然兼容，路径清晰，未实施 | 3 个递进方案（拷贝/MCP 适配/元工具） |

---

## 3. 测试场景（按 9 个审计点逐一覆盖）

### 3.1 工具真调用（防幻觉）

**当前注册的工具**（`praxis2/server/chat_registry.py:30-38`）：
```
AgentTool      ✅ 类完整（agents/agent_tool.py:41-80）
SkillExecTool  ⚠️ 类存在但 run() 多返回 SOP，未真执行
```

**未包装的关键工具**：
- `BrainQueryTool`（brains/retrieve.py 仅函数,无 Tool 子类）
- `RMCPWriteCaseTool`（core/rmcp.py 定义但未包装）
- `BashTool` / `TerminalTool`（不存在）
- `FileReadTool` / `WebFetchTool`（无）

**测试场景**：

| ID | 场景 | 期望行为 | 通过标准 |
|---|---|---|---|
| T1.1 | 用户问"用 BLAST 比对这段序列 ATG..." | LLM 应 `tool_use` AgentTool 或 SkillExecTool | SSE 流含 `tool_start` / `tool_end` 事件 |
| T1.2 | 用户问"用 BLAST 比对这段序列..." | LLM **不应**只用文字描述"我会跑 BLAST" | 若 `tool_use` 事件计数 = 0 → 该轮判失败 |
| T1.3 | 在 chat_registry 临时**不注册任何工具** | LLM 输出应仅是文字 + 不含 tool_use | 用作 negative control，证明注册机制起作用 |
| T1.4 | system_prompt 含"必须用 SkillExecTool 验证你的方案"指令 | LLM 应主动调 SkillExecTool | 验证 system_prompt 注入有效 |
| T1.5 | 检查 `query.py:98` `tools=registry.openai_tools()` 真传给 API | 抓 outgoing API 请求 body | `tools` 字段含 ≥2 个 function 定义 |
| T1.6 | stop_hook 检验"工具未调用就否决" | 配置 stop_hook 在终答时检查 tool_use_count == 0 → veto | 模型被强制再走一轮（max_turns 兜底）|

**关键诊断指标**（按 user 一次对话计算）：
- `tool_call_count / message_count` 比值
- `text_only_with_software_mention_count`（口头说要用某软件但实际无 tool_use 的数量）→ 应趋近 0

### 3.2 MCP 接入测试

**现状**：**完全无 MCP client 实现**。`praxis2/` 目录搜 `mcp_client / McpClient / stdio / http_mcp` 全零命中。代码里大量 `RMCP` 是内部相位管理（retrieve→execute→finalize），**不是** Model Context Protocol。

**测试场景**：
- T2.1 配置一个 stdio MCP server（如官方 `@modelcontextprotocol/server-filesystem`）→ 当前应失败 → 证明缺口
- T2.2 实施"方案 B"（MCP 客户端 stdio + JSON-RPC + MCPTool 子类）后重测

**通过标准**：能让 PRAXIS backend `.mcp.json` 配置外部 MCP server，并在 chat-stream 中通过 `mcp_*_*` tool 名暴露给 LLM 调用。

### 3.3 TerminalTool / 实时数据

**现状**：无本地 BashTool。所有"执行"走 `SubprocessSkillExecutor`（executor.py:68-125），SSH 到 `.53` conda activate 后跑。worker.py 只跑 LLM（不 exec）。

**测试场景**：
- T3.1 用户问"现在 cwd 是什么 / 列一下 /tmp" → 当前必失败（无 Bash tool）
- T3.2 当前 spawn worker 跑 SPEC：实测是 LLM 再跑一遍 prompt，不是 sandbox exec python
- T3.3 加 BashTool（spec: 权限 ASK + sandbox + 限制目录）后，重复 T3.1

**通过标准**：用户可以问任何"在 .53 上跑 X"，AI 真返 stdout/stderr 而不是编造结果。

### 3.4 跨会话长时记忆

**现状**：❌ **完全无**。
- `user_profile`（auth/repository.py:84-85）只是静态注册元数据
- `session.py:209 resume()` 只在同会话内重建
- `brains/<slug>/memory/cases/*` 是**模型层**的案例库（学科 know-how），不是**用户层**的"我的记忆"

**期望机制**（参照 Claude Code memory）：
- `~/.claude/projects/<project>/memory/MEMORY.md` 跨会话持续
- 每会话开始时把 memory 注入 system prompt
- 模型可以 `memory_write_tool` 主动追加

**测试场景**：
- T4.1 用户对话 1：说"我是搞 16S 微生物组的博后" → 关闭浏览器 → 重新登录 → 对话 2 问"我是干啥的"→ 当前必失败
- T4.2 实施跨会话记忆后：重测 T4.1，AI 应主动引用先前对话

### 3.5 上下文窗口管理（5h 限制）

**现状**：⚠️ 不是 Claude Code 那种定时滚动，是反应式 + 主动混合。

- 反应式（`query.py:114-122`）：API 返 `PROMPT_TOO_LONG` 异常 → compact → 重试
- 主动（`query.py:62-68`）：`precompact_gate(state)` 由调用方注入（一般用 `usage.should_auto_compact(used >= window - buffer)`）→ 压缩
- 无 5h 时间窗 reset

**测试场景**：
- T5.1 长对话累积 messages → 接近 1M 上下文窗口时 → 验证 precompact 触发，注入 `【前段摘要】...`
- T5.2 故意构造 PROMPT_TOO_LONG → 验证 reactive_compact_done 标记防无限 compact
- T5.3 24h 内多次对话 → 验证无定时滚动（与 Claude Code 行为差异）

**通过标准**：context 不会爆，但 PRAXIS 的"压缩时机"是反应式而非时间窗。文档化这个差异。

### 3.6 第三方 MCP 安装

同 §3.2 — 当前零支持。如要让用户在 PRAXIS 上也能装 Claude Code 庞大 MCP 库，最低成本路径：

```
1. praxis2/mcp/client.py 实装 StdioMCPClient + JSON-RPC 2.0
2. MCPTool(Tool) 子类把 MCP manifest 转 input_schema()
3. config.py 加 mcp_servers 字段读 .mcp.json
4. chat_registry.py 启动时遍历 config.mcp_servers, 注册到 ToolRegistry
```

### 3.7 未装软件处理 ✅

**现状**：完整。

- `probe_dependencies()`（deps.py:43-87）按 available set 逐包检查
- 缺依赖返回 `is_error=True` + missing 列表 + 建议 `conda install` 命令
- env 歧义显式列举候选，**绝不静默挑**
- `install_deps_via_permission()` 先 ASK，-y 自动确认
- HPC sbatch：完整实现（hpc_submit.py + md/sbatch.py）

**测试场景**：
- T7.1 故意请求 `cryosparc` 但 `.53` 未装 → AI 应正确报告"missing cryosparc, 建议安装 X"
- T7.2 请求时 host_inventory.json 显示已有 conda env "boltz1" → AI 应优先用该 env 跑 Boltz
- T7.3 ASK 权限通过 → install_deps 自动跑 → workflow 真接续

### 3.8 query.py 与 Claude Code 内核差异

参考完整对比表见末尾附录 A。

**关键对比**：

| 维度 | Claude Code | PRAXIS-2 | 评估 |
|---|---|---|---|
| State 显式 | 隐式（局部变量散落） | 显式 dataclass + transition 标记 | PRAXIS 更严格 |
| ToolRunner | 推测并发 | 串行（SerialToolRunner，M0） | PRAXIS 待 M1+ 并发 |
| Compact 时机 | 定时滚动（推测） | 反应式 + 主动混合 | 差异，文档化 |
| stop_hook | 无 | 独创，每终答都跑 | PRAXIS 优于推测原版 |
| AbortSignal | 推测有 | 显式 + 占位 tool_result 补齐 | PRAXIS 更清晰 |

### 3.9 Claude Code skills/MCP 移植到 PRAXIS

**3 个递进方案**（来自 audit agent 4）：

| 方案 | 工时 | 路径 |
|---|---|---|
| A. 直接拷贝 + 薄适配 | 2-3h / skill | 拷 `~/.claude/skills/*` → `brains/_common/skills/workflows/*`，改 frontmatter |
| B. 实装 MCP 客户端 | 3-5d | `praxis2/mcp/client.py` + `MCPTool(Tool)` + config.mcp_servers |
| C. Claude Code 元工具自分析 | 1-2w | 写一个 CC skill 自动评估每个 skill 的可移植性 + 优先级队列 |

**推荐**：先 B（一次到位的 MCP 适配），后 C（让 CC 自动选哪些装）；A 是临时验证手段。

---

## 4. 测试通过标准（Definition of Done）

### 4.1 必过

- [ ] 一次"用 BLAST 比对序列"的 chat 中 `tool_use` 事件计数 > 0（T1.1/T1.2）
- [ ] 11/13 brain 在自动测试覆盖至少 1 个 case 的"真跑流程"（T7 系列）
- [ ] 长对话触发 compact 时不掉消息（T5.1/T5.2）
- [ ] 未装软件场景报错带建议而非编造结果（T7.1）

### 4.2 计划

- [ ] MCP client 实装（方案 B 完成）→ 可调外部 MCP server 工具
- [ ] BashTool / TerminalTool 加入（带权限 + sandbox）
- [ ] 跨会话长时记忆机制（user_preferences 表 + memory injection）
- [ ] Claude Code skills 批量移植试点 5 个（先 nature-citation / nature-figure / nature-polishing / nature-data / nature-response）

### 4.3 期望差异（文档化即可，不阻塞）

- [ ] PRAXIS compact 是反应式，Claude Code 是定时滚动 → 写明差异
- [ ] PRAXIS M0 串行 ToolRunner，M1+ 才并发 → 写明 roadmap

---

## 5. 优先级建议（按 ROI）

| 优先级 | 工作 | 工时 | 收益 |
|---|---|---|---|
| P0 | 包装 BrainQueryTool / RMCPWriteCaseTool 进 ToolRegistry | 1-2h | 直接消除"工具能看见但不能调"缺口 |
| P0 | 接通 M7 真执行链（SkillExecTool.run() 不再返 SOP） | 0.5-1d | 真"做分析"链路打通 |
| P1 | 实装 MCP 客户端（方案 B） | 3-5d | 一次性解锁 Claude Code MCP 庞大库 |
| P1 | BashTool（权限 ASK + sandbox） | 1-2d | 解锁实时数据 + 远端 shell |
| P2 | 跨会话长时记忆 user_preferences 表 + injection | 2-3d | 用户体验跨越式提升 |
| P2 | Claude Code skill 批量移植试点 5 个（方案 A） | 1-2d | 快速覆盖 nature 系列写作场景 |
| P3 | 给 stop_hook 加"工具未调用就否决"硬约束 | 0.5d | 防幻觉强约束 |

---

## 附录 A：query.py 关键 spec 编号速查

| § | 文件:line | 功能 |
|---|---|---|
| §7.1 | query.py:35-51 | query() 签名 + seams |
| §7.1.1 | query.py:57-59 | max_turns 熔断 |
| §7.1.2 | state.py:28-53 | 显式 State dataclass |
| §7.1.3 | query.py:104-119 | tool_use_blocks 顺序保真 |
| §7.1.4① | query.py:114-122 | reactive_compact_done |
| §7.1.4② | query.py:175-186 | max_output_recovery + boost 倍增 |
| §7.1.5 | query.py:125-145 | AbortSignal + 占位 tool_result |
| §7.1.6 | query.py:159-161 | ESCALATED（recovery 预算耗尽） |
| §7.1.8 | query.py:160-173 | SerialToolRunner.run_turn |
| §7.4.3 | memory/session.py | UUID idempotency + append-only |
| §7.4.5 | compact.py:18-42 | adjust_index 防 orphaned tool_result |
| §7.6.1 | query.py:188-203 | stop_hook 每终答都跑 + pending_stop_reasons |
| §12.3 | query.py:62-68 | precompact_gate 主动压缩 |

## 附录 B：审计原始事实来源

证据汇总自 2026-06-01 4 个 Explore agent：
- Agent 1：tools/registry + MCP + TerminalTool + 未装软件（4 项）
- Agent 2：13 brain 的 skills/cases/rules/软件协议覆盖度
- Agent 3：长时记忆 + 5h 限制 + query 对比
- Agent 4：智能体幻觉 vs 真调工具 + skills/MCP 移植

每条结论附 file:line 证据，原始报告留存在会话 transcript。
