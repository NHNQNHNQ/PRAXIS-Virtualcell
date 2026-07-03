# PRAXIS-VirtualCell 使用指南

> 定位:可信虚拟细胞扰动预测。卖点不是"更准",而是**适用性判断 / 拒绝 / 弃权 / 降级 / 溯源 / 不过度承诺**。
> 铁律:所有预测/治理决策由**后端确定性 runtime**完成;LLM 只做自然语言解析、路由建议、critic 复核、报告润色,**绝不**碰 prediction / hard-rule / learned-reliability 终决 / provenance。默认 `offline`(零 LLM)。

## 1. 命令行(CLI)

```bash
# 结构化请求(离线确定性)
praxis-vc run  --request examples/ahr_k562.json --mode offline --out runs/ahr

# 自然语言 → 解析 →(--yes)执行
praxis-vc ask  --text "在 human 细胞里敲掉 AHR 会怎么样" --mode offline
praxis-vc ask  --text "..." --mode llm-assisted --yes --out runs/ahr_llm

# 本地服务 / 网页
praxis-vc serve --host 127.0.0.1 --port 8000     # FastAPI(需 .[api])
praxis-vc web   --api http://127.0.0.1:8000       # Streamlit(需 .[web])
```

## 2. 本地网页流程

`praxis-vc serve` 后浏览器开 `http://127.0.0.1:8000`:

1. **Ask**:自然语言描述扰动实验 + 选模式(offline / llm_assisted)→ Parse。
2. **Confirm**:确认/微调结构化请求——**species / perturbation_type 下拉**(来自后端权威枚举)+ **cell 预设选择器**(选物种/细胞预设自动填充,仍可手改);显示 parser / schema_valid / missing / errors。→ Confirm and Run。
3. **Result**:三 tab
   - **Report**:Summary / Prediction(是否 abstain)/ Reliability decision / Boundary;可导出 `report.md`(确定性 9 段)、`report.json`、`narrative.md`(可选 LLM 散文)。
   - **Trace**:agent 流程时间线。
   - **Provenance**:version / artifact_sha / rules / llm_meta(仅 hash)。

页面明确标注"LLM 未参与预测/治理决策"。

## 3. 输出(runs/<job_id>/)

| 文件 | 内容 |
|---|---|
| `report.md` | **确定性 Markdown 报告,9 段**(Question / Cell Context / Routing / Result / Governance Verdict / Evidence & Provenance / Biological Interpretation / Limitations / Reproducibility),offline 也有 |
| `report.json` | 结构化报告(abstain / reliability / prediction / models / provenance) |
| `trace.json` | agent 流程 |
| `provenance.json` | 溯源(rules / artifact hash) |
| `narrative_report.md` | 可选 LLM 散文(与 report.md 正交) |
| `llm_meta.json` | 仅 hash,不存 key/原文 |

## 4. 治理裁决(verdict)

| verdict | 含义 |
|---|---|
| **accept** | 适用且证据足,给预测 |
| **caution** | 带告警用(如跨物种 ortholog、药物签名噪声) |
| **downgrade** | 引擎在但数据/证据不足,降级解读不可全信 |
| **abstain** | 无适用引擎 → 系统正确弃权,不产出预测(治理有效) |

## 5. 模式与边界

- `offline`(默认):不调任何 LLM;自然语言用确定性关键词解析。
- `llm_assisted`:需 `DEEPSEEK_API_KEY`;LLM 解析/建议/critic/叙述;失败自动回退确定性。
- 数值口径:本地 offline 用 mock/可用 predictor 走完整治理流;真 donor 数值预测在远端 A100(见 benchmarks/)。论文口径:所有 benchmark/prediction/reliability 结果在 offline 确定性模式生成、无 LLM 调用。
