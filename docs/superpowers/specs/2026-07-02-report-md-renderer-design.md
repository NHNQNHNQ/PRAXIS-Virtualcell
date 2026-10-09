# 确定性 report.md 渲染器 — 设计文档

> 日期 2026-07-02 · 归属 v0.6 产品化(计划 §3 报告输出标准) · 状态:已 brainstorm,待写实现计划。
> 上游计划:`~/Downloads/PRAXIS-VirtualCell-v0.6-next-plan.md`(v0.6–v0.8 工程计划)。本 spec 只覆盖其 Sprint 1 中「report.md 输出」这一自成一体的切片。

## 1. 背景与缺口

现状:一次 query 经确定性 runtime 产出 `structured_report`(abstain / reliability / prediction / models / provenance)+ 可选 `narrative`(LLM 散文)。`JobStore` 落盘 `report.json` / `trace.json` / `provenance.json`,LLM 有输出时才写 `narrative_report.md`。

**缺口**:`offline` 模式(零 LLM,论文主口径)跑完**只有 JSON,没有任何 Markdown 报告**。计划 §3 要求「每一次运行都生成一个标准 Markdown 报告,作为科学家可保存、可转发、可审稿、可追溯的主要结果文件」。

**目标**:新增一个**纯确定性**的 Markdown 渲染器,让每次 query(含 offline)都产出一份标准结构化 `report.md`,端到端可下载。

## 2. 铁律(继承项目地基)

1. **纯确定性、不调 LLM**:渲染器不 import / 不调用任何 LLM;只从已落盘的确定性 artifact 读数据。
2. **可复现**:同输入 → 同输出。渲染器内**不用 wall-clock**(`datetime.now()` 等);需要时间戳时取自 `trace` 里已有的 message timestamp。
3. **不编造**:只渲染 artifact 里已有的结论;字段缺失时诚实标注 `N/A` / `未记录`,绝不补数值或结论。
4. **不碰科学决策**:渲染器是纯展示层,不重新计算 verdict / reliability / prediction —— 全部读现有字段。
5. **与 LLM 散文正交**:确定性 `report.md` 与 LLM 的 `narrative_report.md` 并存互不覆盖。

## 3. 新增模块

`praxis_virtualcell/io/report_markdown.py`
- 纯函数 `render_report_md(job: dict) -> str`。
- 输入 = `JobStore.load()` 返回或 `run_query()` 结果可归一到的 job 结构:`report`(structured_report)/ `request` / `trace` / `provenance` / `llm_meta`。渲染器对缺失键做防御(缺则该段标注 N/A),不抛异常。
- 输出 = 一段 GitHub-flavored Markdown 字符串。

## 4. verdict 派生(确定性,复用现有字段,不新造判定)

现有 `report` 字段:`abstain`(bool)、`reliability`(high/medium/low)、`abstain_reasons`、`downgrade_reasons`(`ReportAgent` 已按 `downgrade:` 前缀拆分)、`caution_flags`(= `provenance.ortholog_cautions`)、`learned_reliability`。

派生单一 verdict(仅用于报告展示层聚合,不写回科学决策):

```
abstain == True                    → abstain
否则 downgrade_reasons 非空         → downgrade
否则 caution_flags 非空             → caution
否则                               → accept
```

## 5. 9 段模板 → 现有数据映射

标题沿用计划 §3.3(中英标题均可,实现取英文段标题 + 中文说明,与现有文档风格一致):

| 段 | 内容来源(全部来自确定性 artifact) |
|---|---|
| 1. Question | `request` 结构化任务(species / cell_type / perturbation_type / perturbation_targets / task_type)。原始自然语言:`llm_meta` 只存 hash 不存原文,offline CLI 亦无 → 标注「原始 NL 未记录(仅结构化任务权威)」 |
| 2. Cell Context | species / cell_type;available predictors = `models_used ∪ models_rejected`;applicability = §4 verdict |
| 3. Routing Decision | `models_used` / `models_rejected`(带 reason,若结构里有)/ `models_failed` / `model_disagreement` |
| 4. Result Summary | `prediction`:非 abstain 时列关键结构(shape / 关键量,不解读);abstain 时明确写「已弃权,不产出预测数值」 |
| 5. Governance Verdict | verdict / `reliability` / `abstain` / `learned_reliability`(reliability_score / abstain_decision / OOD flag / version / fallback) / reasons(abstain + downgrade) |
| 6. Evidence & Provenance | `provenance`:runtime_version / artifact_sha / input hash / artifact hash / fallback 标志 / rules_hit |
| 7. Biological Interpretation | 确定性最小事实复述(方向/是否 abstain),末尾固定标注「深入生物学解读需 LLM-assisted 模式;本段不越证据边界」 |
| 8. Limitations | `abstain_reasons` + `downgrade_reasons` + `caution_flags` + 结构性(mock predictor 命名含 `mock_` → 标注非真跑数值;跨物种 ortholog;proxy 指标)。honesty 核心 |
| 9. Reproducibility | request_id / mode / runtime_version / provenance hashes / 复现命令(`praxis-vc run --request <request.json> --mode offline`) |

顶部横幅固定标注:`mode` + 「LLM 未参与预测 / 治理决策;本报告由 structured artifact 确定性生成」。

## 6. 端到端接线

1. **JobStore**(`praxis_virtualcell/io/job_store.py`)
   - `save`:落盘 JSON 后,**始终**额外 `render_report_md` 并写 `report.md`(offline 也写);保留 `narrative_report.md` 逻辑不变。
   - `load`:若 `report.md` 存在则透出为 `report_md` 键。
2. **API**(`praxis_vc_api/`)
   - 新增 `GET /api/reports/{id}/markdown`,返回 `text/markdown`。历史 job 若无 `report.md`,现场 `render_report_md(load(id))` 重渲染(渲染器纯函数,幂等)。
   - service 层 `runtime_service.py` 加薄封装 `report_markdown(job_id) -> str`。
3. **React**(`praxis_vc_react/src/views/ResultView.tsx` + `api.ts`)
   - `api.ts` 加 `getReportMarkdown(id)`;ResultView 加「下载 report.md」按钮(触发浏览器下载)。
4. **CLI**:确认 `praxis-vc run` / `ask` 落盘路径经 `JobStore` → out 目录自动含 `report.md`(若 CLI 未走 JobStore,则在 CLI 落盘处补一次 `render_report_md` 写盘)。

## 7. 不做(YAGNI,留后续 slice)

- **LLM polishing**(计划 §3.4:`report.md → optional LLM polishing → polished_report.md` + consistency checker)。现有 `narrative` 已提供 LLM 散文;本 slice 只补确定性缺口。polishing 作为独立后续。
- CellContext / catalog 系统(计划 §2)、golden case 固化(§4)——各自独立 slice。

## 8. 测试(TDD)

新增 `praxis_virtualcell/tests/test_report_markdown.py`:
- **三类 verdict**:构造 accept / downgrade / abstain 三种 job dict,各渲染 → 断言 9 段标题齐全、verdict 行正确。
- **abstain 诚实性**:abstain job 的 Result Summary 不出现预测数值、Limitations 含 abstain 原因。
- **downgrade**:Limitations 含对应 downgrade_reasons。
- **缺失字段防御**:给最小 job(只有 report)也能渲染不抛异常,缺失段标 N/A。
- **无 LLM**:渲染器模块源码不 import LLM;渲染过程零 LLM 调用。
- **可复现**:同 job 连渲两次输出逐字节相同(证明无 wall-clock / 随机)。

`JobStore` 测试(扩现有):`save` 写出 `report.md`;`load` 返回 `report_md`。

API 测试(扩 `test_api.py`):`GET /api/reports/{id}/markdown` 对已有 job 返 200 + `text/markdown` 且含关键段标题;缺失 id 返 404。

## 9. 验收

- offline 跑一次 query → `runs/<job>/report.md` 存在且 9 段齐全。
- `GET /api/reports/{id}/markdown` 返 200 markdown;React 能下载。
- `PYTHONPATH=<repo> .venv/bin/python -m pytest praxis_virtualcell/tests` 全绿无回归。
- 渲染器纯确定性、可复现、不调 LLM。
