# PRAXIS-VirtualCell 使用指南

> 定位:可信虚拟细胞扰动预测。卖点不是"更准",而是**适用性判断 / 拒绝 / 弃权 / 降级 / 溯源 / 不过度承诺**。
> 铁律:所有预测/治理决策由**后端确定性 runtime**完成;LLM 只做自然语言解析、路由建议、critic 复核、报告润色,**绝不**碰 prediction / hard-rule / learned-reliability 终决 / provenance。默认 `offline`(零 LLM)。
> `1.7.0` 当前只是本地、未发布的 release-engineering source identity；P30A-E1 已完成。
> **E2a follow-on（2026-08-10）：** P30A-E2a clean-SHA offline preflight 为
> `COMPLETE_NEGATIVE`，未运行 install、build、OCI 或 full gate；下一 eligible local work unit 是
> P30A-E2b artifact-aware trusted finalizer。formal P30A 仍 `LOCAL_RC_INCOMPLETE`，science 为
> `NOT_RUN / SCIENCE_BADGE_INELIGIBLE`，policy 为 `NO_NEW_DECISION`。任何预测必须同时匹配 exact request × Pack × model × environment × adapter × evidence × policy；任一门缺失、失配、OOD 或超出 scope 都必须 `abstain`。

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
praxis-vc web   --api http://127.0.0.1:8000       # 旧 Streamlit,需 .[web]
```

`praxis-vc run`、`praxis-vc ask --yes` 与旧 Streamlit 都是正式入口：当前没有显式 Pack 时会生成
P12 V2 零步骤计划并 `abstain`，不会调用 mock 或 case runner。可治理 Pack 执行必须使用
`praxis-vc pack run --pack-id <id> --pack-version <version>`；不要按物种或 cell preset 推断 Pack。

当一个 exact release wheel 已成功构建时，它会包含 `praxis_vc_web/app.py`，`web`
子命令会使用打包后的绝对路径；运行仍需安装 `.[web]`。P30A-E1 的 wheel probes 已验证
该打包路径，但它们不是 clean-install-qualified formal RC artifact；P30A-E2a 的离线预检为
`COMPLETE_NEGATIVE`，下一为 P30A-E2b artifact-aware trusted finalizer。发行门尚未启动完整
Streamlit server，推荐使用下方 React 同源页面。

## 2. 本地网页流程

源码 checkout 先执行 `cd praxis_vc_react && npm ci && npm run build && cd ..`，再运行
`praxis-vc serve`。当且仅当 exact release wheel 或 P30 OCI artifact 成功构建时，它们才会
内含 React 静态资源、不需要外置源码 `dist/`；目前不能把该状态称为已完成。浏览器打开
`http://127.0.0.1:8000`。

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
| **accept** | exact 七门均通过且仍在声明 scope 内，可给预测 |
| **caution** | 仅用于不改变七门结果的 scope 内信息性告警；不得用它放行 OOD、跨物种推导或证据缺失 |
| **downgrade** | 历史显示状态，不能覆盖 exact gate；数据、模型或证据不足时仍必须 value-free `abstain` |
| **abstain** | 任一 exact gate 缺失或失败 → `prediction=null`，保留 reason/provenance |

## 5. 模式与边界

- `offline`(默认):不调任何 LLM;自然语言用确定性关键词解析。`offline` 不代表存在可执行模型，也不降低任何 evidence 或 policy 门。
- `llm_assisted`:需 `DEEPSEEK_API_KEY`;LLM 解析/建议/critic/叙述;失败自动回退确定性。
- 数值口径:本地 synthetic、tiny、dummy 或 test adapter 只能验证合同、溯源和 fail-closed 行为，不是科学 evidence，也不能作为缺失真实模型时的数值 fallback。只有 exact 七门全部通过的不可变 release 才可生成其声明 scope 内的预测，否则 `prediction=null` 并 `abstain`。
- UI footer 的产品版本和 build SHA 来自后端 `/api/health`；前端 package 版本不是发布真相。
