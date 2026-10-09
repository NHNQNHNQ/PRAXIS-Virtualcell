# Phase 10 深度测试路线图:Paper-grade Deep Validation

> 顶层分解文档(decomposition roadmap)。Phase 10 = v1.4 后用户发起的"论文级深度测试与证据封存阶段"。
> 每个子相位(P10.A–P10.D)走各自的 spec → plan → execute 循环;本文件只锚定分解、决策、G2 策略、门槛。
> 权威计划来源:用户 2026-07-08 给出的 Phase 10 十四节计划(brainstorm 对齐后落地)。

## 一、Phase 10 核心目标(要回答的 6 个问题)

1. **确定性内核是否稳定?** offline 下 message bus / AgentMessage / trace / provenance / critic / abstain 全链路可复现。
2. **8 个细胞模块是否都能真实接入?** 每个模块都有可执行预测路径(真实模型 / 规则引擎 / 显式 fallback)。
3. **智能体是否真的在控制预测模型?** 不是 LLM 直接回答,而是 agent 路由到 registry 中的真实模型 / 规则 / 数据 / fallback。
4. **系统是否知道自己不能做什么?** unsupported / 缺模型 / 越界 / 证据不足 / 冲突 → abstain,不硬编答案。
5. **跨模块问题能否拆解与合并?** 多模块证据链 + 冲突检测。
6. **前端和 LLM 外层是否安全?** 解析 / 路由建议 / 润色 / 复核可增强体验,但不得篡改确定性预测。

## 二、定位与论文主张边界(第十四节)

Phase 10 之后论文主张锚定为:
> PRAXIS-VirtualCell 不是"新的 SOTA 虚拟细胞预测模型",而是一个**代码治理的多智能体操作层**——把生物学问题路由到模块专属预测器、强制 schema 化 handoff、记录 provenance、支持确定性重放、在模型覆盖或证据不足时 abstain。

含义:M1/M5/M8 缺公开真实预测模型 → rule-based fallback + 诚实 limitation,不削弱论文主张(主张是"治理层"而非"最强预测器")。

## 三、决策记录(2026-07-08 brainstorm 拍板)

| # | 决策 | 选择 | 影响 |
|---|---|---|---|
| D1 | Phase 10 野心边界 | **完整建设版(8/8 真实接入 + 全治理能力)** | 含大量功能建设,非纯测试;工期数倍 |
| D2 | T10.7 前端 e2e 测试栈 | **正式引入 `@playwright/test`** | 推翻 Phase 9"前端不引入测试栈";前端首次测试栈,e2e spec 入仓可 CI 复跑 |
| D3 | 测试路径 | **`praxis_virtualcell/tests/phase10/`** | 用户计划写的根 `tests/phase10/` 是继承 PRAXIS-2 的 214 文件框架测试区(红线不碰),必须改到项目测试口径下 |

## 四、子相位分解(依赖链 A → B → C → D)

### P10.A — 内核固化 + 测试脚手架(地基)
- **目标**:先用测试把确定性内核焊死,后续功能建设有护栏。
- **工作**:`tests/phase10/` + `benchmarks/phase10/` + `scripts/phase10/` + `reports/phase10/` 目录基建;**T10.1** 全套——trace 重跑 hash 一致、message/AgentMessage schema 严格校验(非法拒绝)、offline 全管线两跑字节等价。
- **对应**:T10.1、十一节目录结构、部分 scripts。
- **依赖**:无(起点)。

### P10.B — 八模块真实接入(最大功能块 = G2)
- **目标**:8/8 模块都有可执行预测路径。
- **工作**:① 14 个 `run_*_case` 接入 Agent Bus + 统一 **case 分发层**(module→runner);② **M1/M5/M8 新建 rule-based fallback 预测器**(标注 `rule_based`/`evidence_limited`,**不伪装 full model**);③ M2 远端 .53 case 通道固化;④ M6 数据扩展;⑤ model_zoo registry 补全 8 模块;⑥ **T10.2** 每模块 3 正例 + 2 负例。
- **对应**:T10.2、G2、G2 五类不过处理(见六节)。
- **依赖**:P10.A。**规模最大,内部可能再分 2–3 批(按模块分组)。⚠️ M2 真实正例带 .53 依赖。**

### P10.C — 治理能力补齐 + 负例/冲突/LLM 安全
- **目标**:补齐论文核心卖点的两项治理能力 + 深测拒绝/冲突/LLM 边界。
- **工作**:① **跨模块结果冲突检测**(方向/证据强度/时间尺度/细胞背景/机制层级 5 类)从零建 + 接入 reliability→abstain;② **provenance 完整性硬门**(缺字段 fail、缺则不进 final report)+ per-call hash(name/version/input/output/param/evidence);③ 越界 cell type abstain 语义;④ LLM 守卫全入口覆盖 + 抗注入 + narrative 一致性校验;⑤ **T10.4**(40 负例)⑥ **T10.5**(20 冲突)⑦ **T10.6**(40 LLM 对照)。
- **对应**:T10.4 / T10.5 / T10.6。
- **依赖**:P10.B(需多模块结果才能测冲突)。**⚠️ T10.6 带 .53 依赖。**

### P10.D — 端到端 + 前端 e2e + 交付物 + 完成闸门
- **目标**:全链路 e2e + 前端 e2e 栈 + 论文级交付物。
- **工作**:① **T10.3** 16 个 e2e(8 单模块 + 8 跨模块);② **T10.7** 引入 `@playwright/test` + 8 e2e 场景;③ 交付物 `reports/phase10/` 六材料 + `summarize`/`export_trace_bundle` 脚本;④ **G2 门槛核验 + Phase 10 完成闸门**(七节门槛表)。
- **对应**:T10.3 / T10.7 / 十二节交付物 / 十三节门槛。
- **依赖**:P10.A/B/C 全就位。

## 五、勘察确认的现状基准(2026-07-08,三 Explore agent)

- **测试基建成熟**:`praxis_virtualcell/tests/` 115 文件;golden 18+60 case、negative 14、abstain/critic/offline-determinism 有基础(T10.1/T10.4 大量可复用扩展)。
- **8 模块真实预测可达 3–5/8**:M3/M4/M7 本地真实可跑(cobra FBA + 真数据 Cohen's d);M2 真实只在 .53 远端(本地 mock);M6 真实但单一数据源;**M1/M5/M8 零预测器,仅 YAML 基因集名字**。14 个 `run_*_case` 未接 Agent Bus,offline 主链只跑 3 个 mock。
- **两项治理能力缺失**:跨模块结果冲突检测**完全不存在**;provenance 完整性硬门**未实现**(只 flag 不阻断)。
- **前端零测试栈**:`praxis_vc_react/package.json` 无 vitest/jest/playwright。

## 六、G2 五类不过处理策略(用户第十节)

G2 = 8 模块真实模型/规则/数据接入门槛。不过 → 定位失败类型修到通过,不接受失败。

1. **模型缺失** → 查公开模型;无则建 deterministic fallback,标 `rule_based`/`evidence_limited`,**不伪装 full predictive model**。
2. **输入 schema 不统一** → module-specific adapter,gene/perturbation/cell_type/species/assay/timepoint 标准化,统一接受 `VirtualCellRequest`。
3. **路由错误** → routing golden set,每模块补 20 条 routing examples,hard rule 优先于 LLM suggestion,router 输出含 confidence + reason。
4. **结果不可审计** → 每个 model call 强制写 model name/version + input/output/param hash + evidence source,缺一 fail。
5. **生物学解释过度** → critic 加 claim-level check;final report 拆 supported findings / model-limited findings / hypotheses / unsupported requests。

## 七、Phase 10 完成门槛(第十三节)

| 指标 | 通过线 |
|---|---|
| offline runtime tests | 100% |
| message schema compliance | 100% |
| provenance completeness | 100% |
| trace replay success | 100% |
| 8 模块至少可运行 case | 8/8 |
| 单模块正例成功率 | ≥ 90% |
| 多模块 workflow 成功率 | ≥ 90% |
| wrong accept rate | ≤ 5% |
| unsupported abstain rate | ≥ 90% |
| conflict detection | ≥ 90% |
| LLM unsupported claim | 0 |
| prompt injection bypass | 0 |
| UI 5 阶段 e2e | 全通过 |

## 八、目录结构(修正:测试落项目口径,非根 tests/)

```
praxis_virtualcell/tests/phase10/           # ← 用户计划的 tests/phase10/ 修正到此(红线:根 tests/ 不碰)
  test_t10_1_runtime_determinism.py
  test_t10_2_module_contracts.py
  test_t10_3_end_to_end_cases.py
  test_t10_4_abstain_negative_cases.py
  test_t10_5_cross_module_conflicts.py
  test_t10_6_llm_outer_layer.py
  test_t10_7_frontend_e2e.py                # 或前端 e2e 落 praxis_vc_react/ 下(P10.D 定)
benchmarks/phase10/
  module_cases.yaml / end_to_end_cases.yaml / negative_cases.yaml
  conflict_cases.yaml / llm_assisted_cases.yaml
scripts/phase10/
  run_phase10_all.py / summarize_phase10.py / export_trace_bundle.py
reports/phase10/
  PHASE10_SUMMARY.md / PHASE10_FAILURES.md / PHASE10_TRACE_AUDIT.md / PHASE10_UI_E2E.md
```

## 九、最终交付物(第十二节,论文/答辩用)

1. `reports/phase10/PHASE10_SUMMARY.md` — 总报告(测试数/通过率/各模块表现/abstain/critic/LLM 对照/UI/失败与修复)
2. 8 模块覆盖表(模块 / 正例 / 负例 / 模型接入 / provenance / critic / 状态)
3. 16 个 end-to-end case 表
4. 负例与 abstain 表
5. trace/provenance audit bundle
6. UI 流程截图或录屏

## 十、红线(继承 Phase 0–9 + Phase 10 专属)

**继承**:后端确定性内核不被 LLM/前端改坏;根 `tests/` 永不碰(测试口径 `praxis_virtualcell/tests`);OFFLINE 全程 `llm_used_for_prediction` 如实 false;commit trailer 恒 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`;里程碑 tag 本地不 push(分支可 push GitHub→.53)。

**Phase 10 专属**:
- M1/M5/M8 fallback 必须标注 `rule_based`/`evidence_limited`,**绝不伪装成 full predictive model**。
- 跨模块冲突检测**只做 advisory + 触发 abstain**,不改写确定性裁决数值。
- LLM 外层(解析/路由建议/润色/复核)**不得**改写 prediction、跳过 registry、改数值、删低置信/abstain、把 hypothesis 写成 conclusion。
- provenance 硬门:缺必需字段 → fail;缺 provenance 的结果不进 final report。
- **D2 例外**:P10.D 起前端引入 `@playwright/test`(推翻 Phase 9"前端不引入测试栈",已用户拍板)。

## 十一、执行节奏

逐子相位 spec → plan → execute,每子相位收尾控制器阶段末验证;沿用 Phase 0–9 的两审(spec 合规审 + 代码质量审)+ build-verified(前端)/ 标准 TDD(后端)纪律;派 subagent 加防注入警示,收结果先查 tool_uses>0 且格式合规。台账 `UPGRADE-PROGRESS.md` 逐 task 勾账 + 事件日志。**下一步:P10.A 详细设计(brainstorm → spec)。**
