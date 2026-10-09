# PRAXIS-2 下一步执行路线图（v0.16.0 → v1.0）

> 配合：
> - `2026-06-01-agent-framework-test.md`（智能体框架审计 + 9 项现状）
> - `2026-06-01-fe-be-test.md`（前后端测试 + 14d 观察期清单）
>
> 本文档：把上面发现的缺口落地成**可执行的步骤** + **里程碑** + **验证标准**。

---

## 0. 大局观

| 版本 | 主题 | 范围 | 完成判据 | 预估工时 |
|---|---|---|---|---|
| **v0.15.x** | 收尾 + dogfood | 已 ship，14d 观察期到 2026-06-12 | 监控无红牌 | — |
| **v0.16.0** | 消除幻觉缺口 | P0 全做完（5 工具包装 + M7 真执行）| 智能体 chat tool_use 率 > 60% | 1-2 周 |
| **v0.17.0** | 解锁外部生态 | MCP 客户端 + BashTool 上线 | 能装 Claude Code MCP 库 + 远端 shell 调通 | 2-3 周 |
| **v0.18.0** | 跨会话记忆 + skill 移植 | user_preferences 表 + 5 个 CC skill 试点 | 用户跨会话被 AI 记住 | 2 周 |
| **v0.19.0** | 硬约束 + 监控完备 | stop_hook 工具未调用否决 + 14d 监控自动化 | 幻觉指标 < 5% | 1 周 |
| **v1.0** | M13 准入 + 关 v1 链路 | M13 准入条件 #1-4 全满足 | 用户显式决策 | — |

**关键原则**：
1. **不动主链路**：staging 14d 观察期内不做激进重构。每个 release 都是 patch 加法不是减法。
2. **每个 release 都走 v0.15 ship SOP**：TDD red→green + rsync 两份 dist + playwright e2e + commit + push + tag。
3. **14d 观察期红牌优先**：先修，再做 feature。

---

## 1. v0.16.0：消除幻觉缺口（P0，1-2 周）

**问题**：当前 chat_registry 已修空 ToolRegistry，但仅 2/7 关键工具真注册。模型仍可纯文字绕过工具（"我会跑 BLAST" 实际不调）。

### 1.1 包装 5 个未注册工具进 ToolRegistry

| 工具 | 现状 | 工作 | 文件 | 验证 |
|---|---|---|---|---|
| BrainQueryTool | brains/retrieve.py 仅函数 | 包装 Tool 子类，input_schema 含 query+top_k | 新 `tools/brain_query.py` | TDD：mock retrieve_cases 返 3 case，验 Tool.run() 输出含 |
| RMCPWriteCaseTool | core/rmcp.py 定义未包装 | 包装 Tool，input: {brain, title, summary, evidence} | 新 `tools/rmcp_write.py` | TDD：调 → DB 写 case → 验持久化 |
| FileReadTool | 不存在 | 沙盒：仅读 user storage + brain skills | 新 `tools/file_read.py` | TDD：限制路径，验 escape 拒绝 |
| WebFetchTool | 不存在 | 限白名单 + 体积上限 | 新 `tools/web_fetch.py` | TDD：fetch 外部 URL，验 size limit |
| AgentTool 强化 | agents/agent_tool.py:41-80 已有但 carry | 增加 "spawn discipline agent" 路径 | 改 `agents/agent_tool.py` | 集成测：调 → spawn 子 agent → 真返结果 |

### 1.2 接通 M7 真执行链

**问题**：SkillExecTool.run() 多返"SOP 文本"。真 SSH 执行（skill_exec.py:253-318）只在显式 `force_ssh=True` 时走。

**步骤**：
1. SkillExecTool.run() 默认 → 检查 `host_inventory.json` → 有 conda env 即真 SSH exec
2. 缺依赖 → 触发 `install_deps_via_permission()` 提示 user
3. exec 完返 stdout/stderr/exit_code 结构化 dict
4. 失败路径：超时 / network error / OOM 各自分类

**验证**：
- TDD：mock SSH executor 返 stdout，验 Tool.run() 输出结构化
- e2e：playwright 让 AI 用 protein brain 跑 Boltz prediction skill → 真返预测结果（而非 SOP 文本）

### 1.3 v0.16.0 DoD

- [ ] 5 工具全 register + 14 个单测全绿
- [ ] SkillExecTool.run() 不再默认返 SOP（除非 SSH 不可达）
- [ ] e2e 1 个：让 AI 用 protein brain 跑 Boltz → 真返 PDB 文件
- [ ] e2e 2 个：让 AI 用 microbiome brain 跑 DADA2 → 真返 ASV 表
- [ ] 智能体 chat 中 `tool_use_count / message_count` ≥ 60%（手测 20 个对话）
- [ ] 14d 观察期监控无红牌
- [ ] commit + push + tag v0.16.0 + memory 更新

---

## 2. v0.17.0：解锁外部生态（P1，2-3 周）

### 2.1 MCP 客户端（一次性解锁 Claude Code 庞大 MCP 库）

**现状**：完全无 MCP client。`praxis2/mcp/` 目录不存在。

**实施步骤**：

**Phase 2.1.1：MCP client 基础（3-5 天）**
```
praxis2/mcp/
  __init__.py
  client.py          # StdioMCPClient + HttpMCPClient
  protocol.py        # JSON-RPC 2.0 frame 序列化/反序列化
  tool_adapter.py    # MCPTool(Tool):从 mcp manifest 转 input_schema
```
- TDD：fake mcp server stdin/stdout → 验 list_tools / call_tool
- 用 `mcp` Python 库（官方）做底层，仅做 Python 适配

**Phase 2.1.2：配置注入（1-2 天）**
- `config.py` 加 `PRAXIS_MCP_SERVERS_JSON='[{"name":"fs","cmd":"npx @modelcontextprotocol/server-filesystem ..."}]'`
- `chat_registry.py` 启动时遍历 config.mcp_servers，spawn subprocess + register MCPTool
- 失败路径：MCP server crash → 自动 retry 2 次 → 仍失败 → unregister + 写 audit log

**Phase 2.1.3：CC MCP 库适配（1-2 天）**
- 写一个 `mcp-from-claude-code.py` 脚本扫 `~/.claude/mcp.json` → 转 PRAXIS_MCP_SERVERS_JSON
- staging 试 5 个：filesystem / git / postgres / brave-search / sequential-thinking

### 2.2 BashTool / TerminalTool（解锁实时数据）

**现状**：无本地 BashTool。所有 exec 走 SSH 到 .53。

**实施步骤**：

**Phase 2.2.1：本地 BashTool（2-3 天）**
- 新 `tools/bash.py:BashTool(Tool)`
- input: `{command, cwd, env, timeout_s}`
- run() 用 `asyncio.create_subprocess_shell` + 限制 cwd 在 user storage 沙盒内
- output: `{stdout, stderr, exit_code, duration_ms}`
- 权限：默认 ASK（PhaseAwarePermission），白名单豁免（`ls`, `pwd`, `cat ~/storage/*`, `df`）

**Phase 2.2.2：远端 RemoteBashTool（1-2 天）**
- 复用 SkillExecTool 的 SSH 通道，但暴露为 user-facing tool
- 限定 .53 sandbox path（user 自己的 `~/data1/<user_id>/`）
- 失败：超时 / disconnect / quota 超

**Phase 2.2.3：沙盒强化（2 天）**
- cgroups（如果 docker host 支持） 或 systemd-run --scope 隔离
- 禁止 `rm -rf /` / `sudo` / 网络出向（可选）
- 资源限制：CPU 1 core, RAM 1GB, time 60s（用户可调）

### 2.3 v0.17.0 DoD

- [ ] MCP client + MCPTool 全单测绿
- [ ] 装 5 个 CC MCP server staging 都能调用
- [ ] BashTool local + remote 都跑通 + 权限 ASK e2e
- [ ] 安全测试：尝试 `rm -rf` / 越权访问别人 storage → 被拒
- [ ] e2e 真问题：让 AI "看下 .53 的 /tmp 有多少剩余空间" → 真返 df 输出
- [ ] commit + push + tag v0.17.0

---

## 3. v0.18.0：跨会话长时记忆 + CC skill 移植（P2，2 周）

### 3.1 跨会话长时记忆

**现状**：完全无。只有 user_profile 静态表 + 单会话 transcript。

**设计**：

```
PG schema 新增 user_memories 表：
  - id UUID PK
  - user_id UUID FK
  - key VARCHAR(128)        -- 如 'research_field', 'preferred_tools', 'recent_projects'
  - value TEXT              -- markdown 摘要
  - importance INT          -- 1-10
  - created_at TIMESTAMP
  - updated_at TIMESTAMP
  - last_recalled_at TIMESTAMP

UNIQUE (user_id, key)
INDEX (user_id, updated_at DESC)
```

**实施步骤**：

**Phase 3.1.1：memory store + repo（1 天）**
- `store/user_memory.py:UserMemoryRepo`
- CRUD：`get_top_k(user_id, k=10)`, `upsert(user_id, key, value, importance)`, `prune_old(days=90)`

**Phase 3.1.2：memory injection（1 天）**
- 在 `brains/system_prompt.py` 五步管道前加一步：拉 top-10 user_memories 注入 system
- 格式：`# 用户长期记忆（按重要性排序）\n- {key}: {value}\n...`

**Phase 3.1.3：MemoryWriteTool（1 天）**
- 新 `tools/memory_write.py:MemoryWriteTool(Tool)`
- AI 主动 `tool_use` 来写：`{key, value, importance}`
- 验证：用户问 "记住我搞 microbiome 16S" → AI 调 MemoryWriteTool → 下次新会话注入

**Phase 3.1.4：FE memory tab（0.5 天）**
- 在 👤 个人资料 modal 加一个 "我的记忆" tab
- 列出当前 user_memories（让用户能编辑/删除/调重要性）

### 3.2 Claude Code skills 移植试点

**现状**：CC skills 在 `~/.claude/plugins/cache/anthropic-skills/skill-creator/` 等。

**5 个试点目标**（先选无外部依赖、纯 markdown 引导型）：
1. `nature-writing` — 写作辅助
2. `nature-citation` — 文献引用  
3. `nature-figure` — 图表设计建议
4. `nature-polishing` — 论文润色
5. `nature-data` — Data Availability 段

**实施步骤**：

**Phase 3.2.1：移植脚本（1 天）**
- 写 `scripts/migrate_cc_skill.py`
- 输入：CC skill 目录路径
- 输出：转好的 PRAXIS brain skill（在 `brains/_common/skills/workflows/<name>/`）
- 转换：CC frontmatter → PRAXIS SKILL.md frontmatter（加 skill_id / scope / inputs/outputs）
- 不动 markdown 正文，让 brain_query / system_prompt 直接用

**Phase 3.2.2：5 个试点 + e2e（2 天）**
- 跑迁移脚本 5 次
- 让 AI 在 chat 中提"帮我写 abstract" → 应自动检索到 nature-writing skill 注入 system prompt
- e2e：playwright 切 yourself（自由模式）+ 问"帮我润色这段话" → AI 应 cite nature-polishing skill 内容

### 3.3 v0.18.0 DoD

- [ ] user_memories 表 + Repo + injection 全单测绿
- [ ] MemoryWriteTool e2e：跨会话记住"我是 microbiome 博后"
- [ ] FE memory tab 增删改查跑通
- [ ] 5 个 CC skill 移植成功 + 至少 1 个被 AI 在 chat 真引用
- [ ] commit + push + tag v0.18.0

---

## 4. v0.19.0：硬约束 + 监控完备（P3，1 周）

### 4.1 stop_hook 工具未调用就否决

**当前**：stop_hook 缝存在（`query.py:188-203`），但没有"必调工具"约束。

**实施**：
- 新 hook `tool_use_required_hook`：传入 state，若该轮 user message 提及 software/data analysis 且 tool_use_count == 0 → return veto + message "你必须用工具，不能纯文字回答"
- 触发条件：用关键词检测 + brain agent 的"该问题应该用 skill X"建议
- max_turns 兜底防死循环

### 4.2 监控完备

按 `fe-be-test.md §5.2` 8 个监控点全自动化：
- backend 存活 → 写 cronjob 每 5min curl /api/info
- litellm 存活 → 每 5min curl /v1/models
- postgres / redis 容量 → 每日 docker stats
- token 消耗 → 每日 SQL 跑 ledger 汇总
- user / 提案 backlog → 每日 admin/inbox 拉取
- 部署版本号 → 部署后 cron 立即拉

所有监控写到 `/tmp/praxis2-monitor.log` + 每周一汇总成 markdown 发到 admin inbox。

### 4.3 v0.19.0 DoD

- [ ] tool_use_required_hook 单测绿 + e2e 验证幻觉率下降
- [ ] 8 个监控点全自动化
- [ ] 智能体 chat 中 tool_use_count 0 占比 < 5%（手测 20 对话）
- [ ] commit + push + tag v0.19.0

---

## 5. v1.0 准入条件

满足以下**全部**才能 ship v1.0（关 v1 链路）：

1. **v0.16-v0.19 全部 ship** + 各自 14d 观察期无红牌
2. **核心 KPI**：
   - tool_use 率 > 80%（智能体真用工具，不幻觉）
   - 11/13 brain 至少 1 个 case e2e 自动跑通
   - 跨会话记忆用户验收通过（10 人 dogfood）
   - MCP server ≥ 10 个能稳定运行 ≥ 1 周
3. **战略对齐**：用户主导一轮"完整测试"（不限时间）
4. **v1 在线用户**：retention / 流量 / 投诉日志确认可承受切换
5. **用户显式决策**："开 v1.0 / 关 v1 链路"

---

## 6. 测试方法论

### 6.1 每个 release 必做（v0.16+）

```
1. TDD：red → green，每个新功能必有单测
2. 全量回归：.venv/bin/python -m pytest tests/ --ignore=tests/integration → 1800+ 绿
3. Deploy：rsync + restart + curl /api/info 验版本号
4. Playwright e2e：覆盖关键路径
5. Commit + push + tag + memory 更新
```

### 6.2 智能体质量评测（手动 + 自动化）

**手动 20 对话评测套件**（每 release 跑一遍）：
1. 5 个学科问题（每个 brain 1 个真实科研问题）
2. 5 个工具触发问题（"用 BLAST" / "跑 GROMACS" / "查 PubChem"）
3. 5 个跨会话问题（先告诉背景，下次问"我是干啥的"）
4. 5 个 corner case（恶意输入 / 超长 prompt / 多步任务）

**评分**：
- A: AI 真调工具 + 真返结果 + 引用 brain 案例
- B: AI 调工具但结果质量差
- C: AI 纯文字描述要调（**幻觉**）
- D: AI 编造结果 / 完全跑偏

通过线：A+B 占比 ≥ 80%，C 占比 ≤ 10%，D = 0%。

### 6.3 14d 观察期监控（自动）

按 §4.2 8 监控点。任何一个连续 3 天红牌 → 暂停下个 release，先修。

---

## 7. 风险点 + 应对

| 风险 | 概率 | 影响 | 应对 |
|---|---|---|---|
| MCP 客户端实装超工时 | 中 | 阻塞 v0.17 | 先做最小 stdio client，留 HTTP / TCP 到 v0.18 |
| BashTool 安全漏洞 | 低 | 严重 | 沙盒 + 白名单 + ASK 三层，安全测试单独审计 |
| 跨会话记忆冷启动 | 中 | 用户体验 | 第一次登录提示 "我可以记住你的偏好" + 引导用户填 |
| CC skill 移植格式不兼容 | 中 | 试点拖延 | 先选 5 个最简单的（纯 markdown），复杂的 v0.19 再做 |
| 幻觉率 KPI 达不到 | 高 | release 失败 | stop_hook 硬约束兜底；如仍不达，加 finetune signal |
| .53 staging 容量爆 | 中 | 全链路挂 | postgres 定期 vacuum + 旧 spawn task 7 天清 |
| paratera key 失效 | 低 | aws-gpt-5.4 不可用 | fallback 到 deepseek-v4-pro；监控加 key 失效检测 |

---

## 8. 时间线（粗略甘特）

```
Week 1-2 (2026-06-02 ~ 2026-06-16):
  v0.15.3 观察期 + v0.16 P0 工具包装实施
  里程碑: 6/12 14d 观察期复盘 → v0.16 ship

Week 3-4 (2026-06-16 ~ 2026-06-30):
  v0.17 MCP client + BashTool
  里程碑: v0.17 ship + 5 个 CC MCP server 接入

Week 5-6 (2026-07-01 ~ 2026-07-14):
  v0.18 跨会话记忆 + 5 CC skill 移植
  里程碑: v0.18 ship

Week 7 (2026-07-15 ~ 2026-07-21):
  v0.19 stop_hook 硬约束 + 监控自动化
  里程碑: v0.19 ship + KPI 验收

Week 8+ (2026-07-22 ~):
  v1.0 准入条件审查 + 用户主导完整测试
  里程碑: 用户决策 v1.0 ship 与否
```

预估总工时（不含 dogfood + 等待）：**6-8 周**。

---

## 9. 立即可做的下一步（本周）

不依赖任何决策，**今天就能做**：

| # | 工作 | 工时 | 输出 |
|---|---|---|---|
| 1 | 写 BrainQueryTool 单测（TDD red） | 30 min | 1 个 fail test |
| 2 | 包装 BrainQueryTool（TDD green） | 1h | 注册到 chat_registry |
| 3 | curl 测：让 AI 用 enzyme brain 答 "Stiffler 2015 case 是关于什么" → 应调 BrainQueryTool | 30 min | tool_use 出现 |
| 4 | 同样流程包装 RMCPWriteCaseTool + 测 | 2h | 2 个新工具 register |
| 5 | playwright e2e：上面 4 个工具的 happy path | 1h | 录制 4 个 e2e 场景 |

**Total: 半天**，能直接出 v0.16.0-alpha tag。

---

## 附录 A：里程碑速查

| 日期 | 事件 |
|---|---|
| 2026-06-12 22:00 | v0.15 14d 观察期复盘自动 trigger（scheduled task: praxis2-m12-staging-14d-review）|
| 2026-06-16 | v0.16 目标 ship |
| 2026-06-30 | v0.17 目标 ship |
| 2026-07-14 | v0.18 目标 ship |
| 2026-07-21 | v0.19 目标 ship |
| 2026-07-22+ | v1.0 用户决策窗口 |

## 附录 B：本会话已 ship release（参考）

```
21a8e27  docs(test-plans): 2 份审计文档
fd487d9  v0.15.3  feat: spawn polling 结果回填
c2ade5e  v0.15.2  paratera AWS-GPT-5.4 接入
18c7e80  v0.15.1  FE 智囊模式双图标 fix + paratera 占位
ae8e612  v0.15.0  feat: auto 模式 chat → 自动后台 spawn 全链路
403e9b1  v0.14.1  proposal display_status derive
5ba03b5           GET /api/me/proposals envelope key fix
e421154           ProposalsModal kind 契约 + FE 版本号
bc761ea           query 推理模型 max_tokens recovery + 393K cap
```
