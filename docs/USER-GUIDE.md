# PRAXIS-VirtualCell 使用指南

> 定位:可信虚拟细胞扰动预测。卖点不是"更准",而是**适用性判断 / 拒绝 / 弃权 / 降级 / 溯源 / 不过度承诺**。
> 铁律:所有预测/治理决策由**后端确定性 runtime**完成;LLM 只做自然语言解析、路由建议、critic 复核、报告润色,**绝不**碰 prediction / hard-rule / learned-reliability 终决 / provenance。默认 `offline`(零 LLM)。

## 1. 命令行(CLI)

```bash
praxis-vc --version

# 结构化请求(离线确定性)
praxis-vc run  --request examples/ahr_k562.json --mode offline --out runs/ahr

# 自然语言 → 解析 →(--yes)执行
praxis-vc ask  --text "在 human 细胞里敲掉 AHR 会怎么样" --mode offline
praxis-vc ask  --text "..." --mode llm-assisted --yes --out runs/ahr_llm

# 本地服务 / 网页
praxis-vc serve --host 127.0.0.1 --port 8000     # FastAPI(需 .[api])
praxis-vc web   --api http://127.0.0.1:8000       # 旧 Streamlit,源码 checkout + .[web]
```

当前 wheel 不包含 `praxis_vc_web`，所以 `web` 子命令尚不是已验证的 wheel 能力；即使在源码 checkout 中也需安装 `.[web]` 并从仓库根目录运行。打包修复归 C4。推荐使用下方 React 同源页面。

## 2. 本地网页流程

先执行 `cd praxis_vc_react && npm ci && npm run build && cd ..`，再运行 `praxis-vc serve`，浏览器打开 `http://127.0.0.1:8000`。没有预先构建的 `dist/` 时只提供 API。

1. **提问（Ask）**：描述扰动实验并选择模式，调用 Parse。
2. **核对（Review）**：查看解析摘要，确认或修改 species、cell、perturbation、task 等字段。
3. **路由（Route）**：查看静态的模块/物种适配预期；这里不是实际运行结果。
4. **运行（Run）**：最终确认参数并执行确定性 workflow。
5. **结果（Results）**：查看六个 tab。
   - **报告**：结构化报告、可靠性裁决、边界与 Markdown 导出。
   - **预测**：只读数值/图形展示，与报告同源。
   - **模块路由**：运行后后端返回的实际 module plan。
   - **证据**：本次运行的 evidence 与审计线索。
   - **运行轨迹**：agent/runtime 时间线。
   - **溯源**：规则、artifact hash、版本标识和 LLM metadata hash。

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
- UI footer 的产品版本和 build SHA 来自后端 `/api/health`；前端 package 版本不是发布真相。
