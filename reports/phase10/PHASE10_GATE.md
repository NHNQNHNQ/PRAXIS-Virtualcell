# PHASE 10 — 完成闸门 GATE(13 指标诚实对账 + G2 五类 + .53 远端亲验)

> **本文件照 roadmap/spec §2.3 的 13 指标原表逐条列(审计锚点),但状态列诚实标 met / narrowed / unsupported / needs_new,收窄/支撑不到项绝不打绿勾。** 照原表打绿 = 把 C1-C4 抓过 11 次的过度声称搬进验收表(spec §5.1)。**冲突时以 spec §0/§2.3/§8 + 本表为准。**
>
> **PRAXIS-VirtualCell 定位** = 代码治理的多智能体操作层,**不是 SOTA 预测模型**。真实引擎级覆盖仅 4 族(M2 需 .53 / M3 / M4 / M7);M1/M5/M8 = rule-based advisory;M6/emt/fate = 诚实 limitation。
>
> 口径:稳定基线 `-m "not llm"` = **912 / 40 / 9 deselected / 0**(`praxis_virtualcell` 包口径,C4 基线 896 + D-A 16 case;整仓根 `tests/` 另有 20 个既有 praxis2 隔离性 failed 不并入)。

## 1. 门槛 13 指标对账

| # | 指标 | 通过线 | 状态 | 支撑 / 偏差(照 spec §8 措辞) |
|---|---|---|---|---|
| 1 | offline runtime tests | 100% | ✅ **met** | D-A 全量 `-m "not llm"` 912/0 failed(junitxml 自动计,`run_phase10_all.py` 两口径)。 |
| 2 | message schema compliance | 100% | ✅ **met** | T10.1 内核固化(schema_version/trace_id/task_id + bus 校验拒非 dict payload)。 |
| 3 | provenance completeness | 100% | ⚠️ **narrowed** | C2 = present-check(必需字段齐 + per-call hash 齐),**非缺失率、非跨版本防篡改**;Gate B 防御断言罕触发。 |
| 4 | trace replay success | 100% | ✅ **met** | "replay" = 同请求重跑字节等价,**非从导出 bundle 回放**;D-C `export_trace_bundle`/`summarize`/`gen_case_tables` 三脚本幂等佐证。 |
| 5 | 8 模块至少可运行 case | 8/8 | ✅ **met(带限定)** | **不得打"8/8 真实模型"**:引擎级真实仅 M2*/M3/M4/M7,M1/M5/M8 = advisory,M6/emt/fate = limitation。M2 真实仅 .53 —— **D-D.1 .53 亲验坐实**(GEARS 真 delta + scGPT==donor)。D-A S1-S8 单模块 case 全绿(advisory 断 module_plan entry 非预测)。 |
| 6 | 单模块正例成功率 | ≥90% | 🔨 **needs_new → 诚实收窄** | 无 corpus 测得率,**不编百分比**;收窄为"4 真实引擎 e2e 全绿(D-A S2 mock donor / S4 cobra FBA / S7 state_scoring + X7 跨物种)+ 既有 60 路由 golden 全绿"。 |
| 7 | 多模块 workflow 成功率 | ≥90% | 🔨 **needs_new / 重定义** | C1 证伪多引擎 fan-out(route 单出口一请求单 engine),"多模块" **重定义** = module_plan 多 entry 路由 + advisory 标注(零 delta),**非多预测器证据链合并**。D-A 8 跨模块 case(X1-X8)全绿 = 该重定义指标达标。 |
| 8 | wrong accept rate | ≤5% | ✅ **met(更严)** | 实测 unsafe_accept **== 0**(3 层拒绝 over 92 条 corpus);corpus 来源如实标(T10.4 40 负例被 C2 provenance gates 挤占)。 |
| 9 | unsupported abstain rate | ≥90% | ⚠️ **narrowed** | 绝对断言支撑、**无测得率**;D-A 11 个诚实 abstain case(S1/S3/S5/S6/S8/X2/X3/X4/X5/X6/X8)钉住,但非率。 |
| 10 | **conflict detection** | ≥90% | ❌ **unsupported(最大收窄)** | 门槛表设想"5 类独立结果冲突检测";C1 证伪 → 实为 `module_plan` **内部一致性 gate**、**罕触发、违规恒空靠 monkeypatch 触发**、无 20 条 conflict_cases。D-A X6 断 gate NO-OP(自然输入键缺席、不声称自然触发)。**paper 须明标非独立结果冲突检测,绝不打绿。** |
| 11 | **LLM unsupported claim** | 0 | ❌ **unsupported** | C3 支撑不到(memory 明记须克制);narrative gate 仅 abstain 场景 + 仅浮点 + hedge 词可绕、不验语境对应。**不得声称覆盖 §128 hypothesis→conclusion,绝不打绿。** |
| 12 | prompt injection bypass | 0 | ⚠️ **narrowed** | C3 结构性防御推论,**非独立检测层、非测得 bypass 率**;测试用 stub;对照组近乎恒真。 |
| 13 | UI 5 阶段 e2e | 全通过 | ✅ **met(D-B 新建)** | **D-B playwright**:5 阶段五跳(ask→review→route→run→results,waitForResponse 断 POST /api/parse+/api/jobs)+ 6 tab 面板 h2(概要/结果可靠性/路由摘要/证据与审计/运行轨迹/运行标识),**3 passed 在前端 WIP CSS 未提交状态复跑全绿 = role/text 选择器真抗 WIP**(控制器亲验)。覆盖边界诚实:不覆盖 abstain 深层/像素/LLM(见 `PHASE10_UI_E2E.md`)。 |

**小结**:13 指标里 **~7 条真达标(#1/#2/#4/#5带限定/#8/#13 + #7重定义)**、**4 条 C1-C4 收窄(#3/#9/#12 narrowed + #6 needs_new 诚实收窄)**、**2 条支撑不到(#10/#11 unsupported,绝不打绿)**。#13 由 D-B 新建补齐。

## 2. G2 五类判据

| 类 | 判据 | 状态 | 偏差 |
|---|---|---|---|
| ① | 模型缺失 fallback | ✅ met | 覆盖不足 abstain,不伪造。 |
| ② | schema adapter | ✅ met | request_adapter/case_dispatch 共享基建。 |
| ③ | routing golden + confidence | ⚠️ narrowed | **confidence 字段未实现**;每模块 20 条 routing examples 未严格达成。 |
| ④ | per-call hash | ✅ met | C2 全 predictor 记 name/version/input/output hash;**"Gate A 不误伤真 ML" 的 .53 端到端验证仍 pending**(见 §3 backlog,C2 §5 风险2 预言实例)。 |
| ⑤ | critic claim-level + report 分层 | ⚠️ narrowed | markdown 分节近似,**非严格 4 路结构化字段**。 |

## 3. .53 远端亲验(D-D.1,控制器 2026-07-17 亲自 SSH,同 M2 Task5 模式)

**方式**:git bundle 增量同步(`b43851e..7cad05d`)到 .53、**不 push origin**;跑完 `git checkout b9abdbd` 恢复 .53 干净(生产 uvicorn 当次未运行、:8000 空,零扰动);bundle 清理。conda env:GEARS 在 `virtualcell`(torch2.6+cu124,cuda True)、scGPT 在 `vc-scgpt`(`vcell` env 已损坏 torchtext undefined symbol)。ckpt:`gears_ckpt/norman_2019` / `scgpt_ckpt/norman_2019/pretrained_backbone` / `mean_baseline_ckpt/norman_2019/mean_delta.pt`。

| 远端项 | 结果 | 说明 |
|---|---|---|
| **M2 GEARS 真 delta**(`test_public_models_remote::test_m2_gears_case_real_delta_e2e`) | ✅ **passed**(virtualcell env, GEARS_CKPT) | GEARS-内部 delta 真跑(51s);M2 Task5 曾亲验 delta −0.28~0.67/452 负值/23862 ctrl 细胞。M2 真实腿坐实。 |
| **scGPT == donor**(`test_scgpt_wrapper_real_inference_matches_donor`) | ✅ **passed**(vc-scgpt env, SCGPT_CKPT_STEM, atol 1e-6, 7.3s) | 在 virtualcell env 因无 scgpt 报 ModuleNotFoundError(env 分工非回归),vc-scgpt env 真跑通过。 |
| **test_public_models_remote 第 3 条** | ✅ passed(virtualcell) | 3 条 remote 全 passed(跨 virtualcell/vc-scgpt 双 env)。 |
| **norman mean baseline**(`test_norman_mean_baseline_gated` 2 条 @remote) | ✅ **2 passed**(virtualcell, P7_MEAN_DELTA_CKPT) | ΔPearson pin 复算 + SelfTrained run_prediction。G2#1 自训真实性坐实。 |
| **test_t10_2 fail-closed / cobra 本地测试** | ⚠️ **env 差异非回归** | .53 `virtualcell` env **无 cobra**(`ModuleNotFoundError: cobra`)→ 4 条 cobra FBA 本地测试(bacteria medium/antibiotic FBA)在 .53 FAILED;**Mac 本地这些测试全绿**(912 包口径含它们),属 .53 env 差异。**教训:.53 亲验应只跑 `@remote`/`@integration` 标记项,不跑为 Mac 设计的本地测试。** fail-closed 那条(skipif `_HAS_TORCH`)在有 torch 的 .53 上按设计 skip。 |

**⏸ pending(.53 环境缺件/复杂,记 backlog,不阻塞收官)**:
- `test_ml_workflow_e2e`(donor ML 全链,@remote):**`W4B_CKPT_DIR` ckpt 在 .53 未找到** → pending。
- `test_linux_docker_smoke`(10 条 @integration):Docker Hub 被网络拦截需 daocloud mirror + 需本地 build dist 传 .53(远端 node v12 build 不了)→ 本轮 pending。
- **MLBackedPredictor Gate A 不误伤真 ML** 端到端 e2e(C2 §5 风险2 预言实例,C2/G2#4 backlog):需构造真 donor ML 跑 run_query 确认 Gate A 不 fail-closed 误伤 → 本轮 pending（W4B/donor ML ckpt 未定位）。

## 4. 诚实边界(paper / 交付物引用须照此,继承 C1-C4 全部 backlog + D 新增)

- #3/#9/#12 narrowed、#6 needs_new、#10/#11 unsupported —— 措辞照 spec §8,**收窄/支撑不到项绝不在 paper 打绿**。
- #5「8/8 可运行」带 advisory(M1/M5/M8)/ remote(M2)/ limitation(M6/emt/fate)限定,**非 8/8 真实模型**。
- #7「多模块」= module_plan 多 entry 路由 + advisory，**非多预测器证据链合并**（C1 证伪 fan-out）。
- #10 命名 `cross_module_inconsistency` 对外须加注为「module_plan **内部**一致性 gate」。
- #13 UI e2e = 五跳全绿 + 6 tab 面板 h2 出现，**不覆盖** abstain/failed 深层数值、像素/CSS、LLM 模式。
- **D-A 新增诚实事实**（D 交付物须带）：16 case 实际覆盖 **14 个不同请求**（S3≡X6、S8≡X4 请求相同、断言角度不同），paper 须说明以免高估多样性。
- .53 亲验本轮坐实 M2 真实腿（GEARS+scGPT）+ norman 自训；ml_workflow / docker smoke / Gate A 不误伤真 ML 三项 **pending**，未坐实的**不得在 paper 声称已验**。
