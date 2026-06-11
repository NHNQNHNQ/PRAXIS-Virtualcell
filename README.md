# PRAXIS-virtualcell

PRAXIS-virtualcell is a PRAXIS-2-derived multi-agent framework for virtual-cell prediction.
It reuses the PRAXIS-2 agent runtime, long-term brain, validation rules and skill system, and
extends them with a virtual-cell brain, predictor registry, virtual-cell subagents and biological benchmarks.

> 基于 **PRAXIS-2**(commit `b124d66`)复制改造的多智能体虚拟细胞框架。继承 PRAXIS-2 的智能体运行时、长期大脑、
> 规则系统与工具执行能力,扩展虚拟细胞大脑、预测模型注册表、虚拟细胞 Subagent 与生物 benchmark。
> python 包名保持 `praxis2`;已移除 13 个通用学科大脑、改为单一 `virtualcell` 大脑;未纳入 frontend。
> 派生关系见 [PROVENANCE.md](PROVENANCE.md),大脑现状见 [brains/INDEX.md](brains/INDEX.md),基线见 [BASELINE.md](BASELINE.md)。

> ⚠️ 以下章节继承自 PRAXIS-2,部分内容(13 学科 / frontend / 部署拓扑)在 PRAXIS-virtualcell 中已调整,以 PROVENANCE / brains/INDEX 为准。

---

## 这是什么

- **内核**:纯 ASGI(不依赖 FastAPI)+ 自研工具闭环主循环 `query()` + 相位机(RMCP)+ 压缩(compact)+ 注入缝(seams),即一套 Claude-Code-style harness。
- **领域**:13 个学科专家(CRISPR / Protein / Dock / Enzyme / MD / Omics / Microbiome …),每个挂真实知识库(案例 / 规则 / 技能工作流),可 SSH 到远端跑 conda 环境的真实科学计算并返回真实结果。
- **反幻觉(项目地基)**:检索先行门 + stop_hook + 发版前门;引用强制真实 DOI;声称执行必须有真实工具调用佐证。诱导编造结果时,智能体会检索 → 识别科学陷阱 → 拒绝假数值 → 诚实说明,而非编造。

---

## 从哪里开始

| 文档 | 内容 |
|---|---|
| **[docs/项目说明.md](docs/项目说明.md)** | **系统现状 + 服务器部署位置 ← 先读这个** |
| [docs/TEST-AGENT-FRAMEWORK.md](docs/TEST-AGENT-FRAMEWORK.md) | 智能体框架测试计划(端到端真分析不幻觉) |
| [docs/TEST-WEB-BACKEND-FRONTEND.md](docs/TEST-WEB-BACKEND-FRONTEND.md) | Web 前后端测试计划 |
| [docs/superpowers/](docs/superpowers/) | 设计文档(spec)+ 实现计划(历史决策权威) |
| [docs/history/](docs/history/) | 历史版本状态 / 交接 / 计划(归档) |

---

## 架构

```
浏览器 → .40:8080 (反代 / 前端)  ──/api──→  .53:8001 (gunicorn ASGI)  →  litellm 127.0.0.1:4000 → DeepSeek / AWS
                                                  └─ PostgreSQL(会话 transcript / 用户 / 计费)
```

**后端 `praxis2/`(21 个代码模块)**:
`core`(执行内核:query 工具闭环 + 相位机 + compact)· `server`(ASGI 中枢,chat-stream SSE)· `brains`(13 学科知识库 + 共享规则)· `memory`(SessionStore 跨会话记忆)· `tools`(工具实现 + 反幻觉检索先行门)· `hooks`(stop_hook 反幻觉)· `agents` · `accounting`(计费)· `mcp`(外部工具)· `spawn`(后台长任务)· `store` / `runtime` / `auth` / `llm` …

**前端 `frontend/`**:React + TypeScript + Vite,对话状态机 + chat-stream 消费。

完整架构、能力清单、**服务器部署位置与 SOP** 见 [docs/项目说明.md](docs/项目说明.md)。

---

## 能力一览

- **智能体**:13 学科专家 + 3 智囊模式(通用助手 / 一统大脑路由 / 自由模式);3 种对话模式(ask / plan / auto)。
- **知识库**:14 个 brain(13 学科 + `_common`),167 个技能工作流,RMCP 治理(检索命中注入 / 为空显式降级)。
- **工具调用**:SkillExec(真执行链,SSH+conda)· BrainQuery · FileRead / WebFetch · AgentTool(三层隔离 fork)· MCP client(stdio)· BashTool(软沙盒 + 真隔离三件套)。
- **跨会话记忆**:SessionStore(transcript → PostgreSQL + resume),对话跨重启 / 换设备 / 重登持久恢复。
- **真隔离**:BashTool 文件系统(userns + tmpfs)+ 资源(cgroup)+ 网络(netns)隔离,opt-in 正交叠加。
- **计费**:Ledger(`balance_li`,1 元 = 100 li),按 token 计价。

---

## 开发

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
ruff check . && pytest                       # 175 测试文件 / ~2100 用例
cd frontend && npm install && npm run build
```

开发严格走 superpowers 流程(brainstorm → spec → 计划 → subagent-driven TDD + 两阶段 review),`main` 即生产线。

---

## 版本

三条 tag 线:`v0.x` 后端主线(当前 **v0.19.1**)· `v1.x-学科` brain milestone · `v2.0.x` agents 元数据。
`git tag -l | sort -V` 看全部。
