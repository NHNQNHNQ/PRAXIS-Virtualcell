# PLAN v0.6 Phase 4 — React 正式网站(接现有 FastAPI)

> 目标:在已完成的 P1(核心+服务层)/P2(FastAPI `praxis_vc_api`)/P3(Streamlit)之上,做**React/Vite 正式前端**,通过现有 REST endpoints 完成一次完整 query,并支持多 job 管理 / 报告导出 / trace 可视化。loop 按顺序取第一个未勾选 `- [ ]` 完成。
> **上下文交接**:整体现状见 `docs/ANALYSIS-SUMMARY.md`;界面架构与铁律见 `docs/PLAN-v0.6-llm-interface.md` + `docs/USAGE-llm-interface.md`。FastAPI 已就绪(health/parse/jobs/reports/trace/provenance),React 只是前端。

## 铁律(每步必守)
- 核心科学决策全在后端确定性 runtime;**前端只展示,绝不**在前端做预测/治理判断。UI **必须明确标注**"LLM 未参与预测/治理决策";narrative 旁标"generated from structured report"。
- 默认 offline;模式切换只传给后端。前端不存/不显示 API key。
- 后端不改核心逻辑(只可加 CORS);不碰 v0.2/v0.3 正文、不碰 praxis_virtualcell governance/predictors。
- 每步本地单独 commit(末尾 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`);commit 前 `find docs praxis_virtualcell praxis_vc_api praxis_vc_react -name '._*' -delete`。
- React 放**新目录 `praxis_vc_react/`**(仓库已有的 `frontend/` 是别的项目,勿动);gitignore `praxis_vc_react/node_modules/` 和 `dist/`。
- 前端 py 测试无关;后端若动 FastAPI 要跑 `.venv/bin/python -m pytest praxis_virtualcell/tests` 无回归(带 `PYTHONPATH=<repo>`)。

## 环境前置(loop 第一步必查)
- [ ] R4.0 — 查 `node -v` / `npm -v`。**无 node/npm → 硬门停下**,让用户装(Node ≥18)。有则继续。

## 步骤

### - [ ] R4.1 — FastAPI 加 CORS + 冒烟
- `praxis_vc_api/main.py` 加 `CORSMiddleware`(允许 `http://localhost:5173`、`127.0.0.1:5173` — Vite dev)。
- 启动 `praxis-vc serve`(或 `uvicorn praxis_vc_api.main:app`),`curl /api/health` 返 200;`POST /api/parse` offline 通。
- 验收:CORS 生效;`pytest praxis_virtualcell/tests` 无回归(test_api 仍绿)。

### - [ ] R4.2 — Vite + React + TS scaffold + API client
- `npm create vite@latest praxis_vc_react -- --template react-ts`;`npm i`。`.env`/config 里 API base 默认 `http://127.0.0.1:8000`(可 `VITE_API_BASE` 覆盖)。
- `src/api.ts`:`health()/parse(text,mode)/createJob(request,mode,enable_llm_report)/getReport(id)/getTrace(id)/getProvenance(id)`。
- 验收:`npm run build` 通过;`npm run dev` 起;首页能拉到 `/api/health`(后端开着时)。

### - [ ] R4.3 — 页面:Ask → Confirm → Report/Trace/Provenance
- **Ask**:textarea + 模式选择(offline/llm_assisted)+ Parse 按钮 → 调 `/api/parse`。
- **Confirm**:显示 candidate(species/cell_type/perturbation_type/targets 可编辑)+ parser/llm_used/schema_valid/assumptions;missing/errors 高亮;**Confirm and Run** → `/api/jobs`。
- **Result**:tab Report(4 块:Summary / Prediction(是否 abstain)/ Reliability decision / Boundary)+ narrative(标注 LLM 未改预测)· Trace(agent 表格/流程)· Provenance(version/artifact_sha/fallback/llm_meta hash)。
- 顶部横幅:`mode` + "LLM 未参与预测/治理决策"。
- 验收:后端开着时,输入自然语言 → 确认 → 得到报告/trace/provenance,全链走通(offline)。

### - [ ] R4.4 — Jobs 列表 + 报告导出 + trace 可视化
- Jobs 页:列 `runs/` 下 job(需后端加 `GET /api/jobs`(list)—— 若无则本步先给后端加该 endpoint,复用 `JobStore.list_jobs`)。点击载入历史 job。
- 报告导出:前端下载 structured_report.json / narrative.md。
- Trace 可视化:按 sender→receiver 顺序渲染 agent 流程(简单时间线/列表即可,不必上重库)。
- 验收:能列出并重看历史 job;能导出报告。

### - [ ] R4.5 — 构建产物 + CLI 集成 + 文档
- `npm run build` → `praxis_vc_react/dist/`;可选:FastAPI 挂载静态(`app.mount("/", StaticFiles(dist))`)让 `praxis-vc serve` 直接托管前端。
- CLI:`praxis-vc web` 保留 Streamlit;新增说明 React 用法(dev:两个进程;prod:serve 托管 dist)。
- 更新 `docs/USAGE-llm-interface.md` 加 React 段;pyproject 无需加(前端独立)。
- 验收:一条命令能看到 React 网站 + 后端;文档齐。

## 停止条件(硬门,停下汇报)
1. `node/npm` 缺失或版本过低(R4.0)——停,让用户装;
2. `git push`(只本地 commit);
3. 需改 v0.2/v0.3 正文 或 praxis_virtualcell governance/predictors 核心;
4. `pytest` 后端回归、或 `npm run build` 失败且无法自解;
5. 需要新增付费/外部服务(除已有 DeepSeek);
6. R4.0-R4.5 全完成 → 停,简短汇报,提示可跑 `praxis-vc serve` + React dev。

## /loop 提示词(复制到下一个对话)

```
/loop 读 docs/PLAN-v0.6-phase4-react.md,自主推进 Phase 4 React 正式网站:反复取第一个未勾选(- [ ])步骤,按其"验收/铁律"做到底,直到 R4.0-R4.5 全完成或撞硬门。先做 R4.0 查 node/npm(无则停下让我装)。React 放新目录 praxis_vc_react/(勿动已有 frontend/),前端只展示、绝不在前端做预测/治理判断、UI 明确标注"LLM 未参与预测/治理决策"、默认 offline、不显示 API key。后端只可加 CORS/list-jobs endpoint,不碰 governance/predictors 核心、不碰 v0.2/v0.3 正文;动后端要跑 PYTHONPATH=<repo> .venv/bin/python -m pytest praxis_virtualcell/tests 无回归。每步:npm run build 通过 / 全链能对本地 FastAPI 走一次 offline query,commit 前 find ... -name '._*' -delete,本地单独 commit(末尾 Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>),把该步骤改 [x],简短汇报后继续下一步。只在这些硬门停:①node/npm 缺失或过低;②git push;③需改 v0.2/v0.3 正文或 governance/predictors 核心;④pytest 回归或 npm build 失败无法自解;⑤需新增付费/外部服务;⑥R4.0-R4.5 全完成。整体现状背景见 docs/ANALYSIS-SUMMARY.md 与 docs/PLAN-v0.6-llm-interface.md。全部完成后简短汇报即可,别问我下一步。
```
