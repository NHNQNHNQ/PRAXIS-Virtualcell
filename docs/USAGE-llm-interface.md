# PRAXIS-VirtualCell 本地科学家界面 — 使用说明(v0.6 MVP)

> 离线优先、可审计、可回退。核心预测/可靠性治理/provenance 全由**确定性 runtime**完成;**LLM 只做**自然语言解析 / 路由建议 / critic 复核 / 报告润色,**绝不**碰 prediction / hard-rule / learned reliability 终决。默认 `offline`(零 LLM 调用)。

## 安装
```bash
pip install -e .            # 核心包 + CLI(praxis-vc)
pip install -e ".[api]"     # + FastAPI/uvicorn(本地服务)
pip install -e ".[web]"     # + Streamlit/requests(本地网页)
```

## 三种用法

### 1) CLI
```bash
# 结构化请求(离线确定性)
praxis-vc run --request examples/ahr_k562.json --mode offline --out runs/ahr

# 自然语言(offline 用确定性解析;llm-assisted 用 DeepSeek,需 .env 有 key)
praxis-vc ask --text "在人类 K562 里敲掉 AHR 会怎么样" --mode offline
praxis-vc ask --text "..." --mode llm-assisted --yes --out runs/ahr_llm   # --yes 确认执行
```

### 2) 本地网页(推荐科学家用,local-first,无需另起 API)
```bash
praxis-vc web                       # 或 streamlit run praxis_vc_web/app.py
```
流程:输入自然语言 → **解析**(可确认/编辑物种/细胞/扰动)→ **Confirm and Run** → Report(4 块)/ Trace / Provenance 三 tab。网页明确标注"LLM 未参与预测/治理决策"。

### 3) FastAPI(程序化 / 远端 / 未来 React 前端)
```bash
praxis-vc serve --host 127.0.0.1 --port 8000
```
| endpoint | 说明 |
|---|---|
| `GET /api/health` | mode / llm_enabled / runtime_version |
| `POST /api/parse` | 自然语言 → candidate_request + 校验(不执行) |
| `POST /api/jobs` | 已确认 request → 离线执行 → 落盘 job |
| `GET /api/reports/{id}` `/trace` `/provenance` | 结果 / trace / 溯源 |

## 模式与 LLM
- `offline`(默认):**不调用任何 LLM**;自然语言用确定性关键词解析。
- `llm_assisted`:需 `.env` 设 `DEEPSEEK_API_KEY` + `PRAXIS_VIRTUALCELL_MODE=llm_assisted`;LLM(deepseek-chat)解析/建议/critic/叙述;**失败自动 fallback 到确定性**。
- 决策边界铁律:`allow_llm_to_modify_core_decision/_prediction/_override_hard_rules` **永为 False**(`assert_llm_boundaries` 守卫);冲突时 deterministic wins,记 provenance。

## 输出(runs/<job_id>/)
`request.json` · `report.json` · `trace.json` · `provenance.json` · `narrative_report.md`(可选)· `llm_meta.json`(仅 hash,不存 key/原文)。

## 说明
- 本地(Mac)runtime 用 mock/可用 predictor 走完整治理流(route/reliability/abstain/critic/provenance);真 donor 数值预测在远端 A100(见 benchmarks/ + L4/G2 runbook)。
- 论文口径:所有 benchmark/prediction/reliability/abstention 结果在 offline 确定性模式生成、无 LLM 调用;LLM-assisted 是**界面层**,非科学决策层。
