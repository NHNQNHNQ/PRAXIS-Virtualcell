# PHASE 10 — UI E2E(前端 playwright)

> D-B 前端 e2e:5 阶段 happy path 五跳 + 6 tab 面板可达。选择器全 role/text/label(抗前端 WIP CSS,零像素/CSS 断言)。webServer 先 build 再 uvicorn 同源托管,固定 1280×720。

## 覆盖(诚实边界)
- ✅ 5 阶段推进:ask→review→route→run→results,waitForResponse 断 POST /api/parse + /api/jobs 硬证据。
- ✅ 6 tab 可达 + 面板 h2:概要 / 结果可靠性 / 路由摘要 / 证据与审计 / 运行轨迹 / 运行标识(默认 query「在 human 细胞敲 AHR」产出非 abstain + module_plan + evidence + provenance 完整结果)。
- ❌ **不覆盖** abstain/failed 深层数值(那是内核 pytest 的活);不覆盖像素/CSS/视觉;不覆盖 LLM 模式。
- 门槛 #13「UI 5 阶段 e2e 全通过」= 五跳全绿 + 6 tab 面板 h2 出现。

## 实跑结果(实测,标口径)
- 命令:`cd praxis_vc_react && npm run e2e`(3 spec:smoke / happy-path / result-tabs)
- 结果:**3 passed**(smoke 1 + happy-path 1 + result-tabs 1;耗时 4.9s)
- **抗 WIP 验证**:在前端 4 个 WIP CSS(src/styles/{base,fonts,themes,tokens}.css)未提交状态下复跑全绿 → role/text 选择器不受 CSS 改动影响(spec §5.3)。
- 截图:`PHASE10_UI_E2E_results.png`(Results 页 6 tab,报告 tab「概要」+ 预测「已给出预测」delta,非 abstain)。
