# P10.C1 跨模块一致性治理(诚实窄门版)设计 spec

## 1. 目标与背景

P10.C 治理补齐单元的第一子单元。目标:把**跨模块结果治理**从"完全不存在"推进到"module_plan 内部一致性检测接入主链 + 严重不一致真触发 abstain",作为 Phase 10 论文主张("代码治理的多智能体操作层")的治理能力之一。

**关键:本单元是"诚实窄门版",不是 roadmap 原设的"通用 5 类跨模块冲突检测"。** 两次只读勘察(C1 现实基础 + 补数据流可行性)已证实原设方向不成立,用户据此拍板改窄门版。

## 2. 勘察确立的现实约束(设计的事实地基)

- **"多模块独立结果"在现状不存在**:一次 query 经 route_table(if/elif **单出口**,`target_output` 互斥枚举)只映射到**单个** engine;`module_plan` 的多个 entry 是**纯路由标注(零 delta、零独立预测)**;predictor fan-out 的 `disagreement` 是 **predictor 级不是 module 级**。要多引擎结果需新建跨请求编排层 + 动 ensemble/reliability 边界,工程量与收益严重不对等。
- **真实可比重叠场景仅 1 个**:human + IFN-β 别名靶标,`target_output∈{flux,state}` → `metabolic_tendency`(M3/M4) vs `cell_state`(M7),同数据源(Kang 2018)、同单位(Cohen's d),只支撑"证据强度"1 类,触发窗口极窄;且需跨请求编排(同一 query 跑两 target_output)才能同时拿到两结果。
- **roadmap 5 类冲突数据可判定性**:只有"证据强度"有真实数据;"细胞背景/机制层级"顶多做"不可比→拒绝"门禁;"方向/时间尺度"**无 per-module 数据支撑**(强建=张冠李戴,B1-M2 血泪)。
- **B4 并不真触发 abstain**:B4 只改 `module_plan` 在 provenance 里显示的 verdict,`reliability` 完全不读 module_plan。C1 要真触发 abstain 是 B4 从未做过的新动作。
- **裁决流事实**:最终 abstain 由 `reliability_decision.abstain` 决定,report 据此组装(prediction=None if abstain);reliability 读 ensemble payload,**不读 module_plan**。runtime 裁决流 = ensemble→reliability→critic→provenance→report,**report 组装后 runtime 有后处理阶段**(module_plan + report 信号全齐,现挂 evidence_level/learning_queue)。

## 3. 范围(诚实窄门)

**做**:
- 把现有死码 `governance/module_consistency.py::check_module_plan`(检测 module_plan 内部一致性的 4 条 fail-closed 规则)**接进主链**。
- 检测到违规 → 记录 provenance(advisory);**严重违规 → governance gate 真触发 abstain**(不改 reliability/critic 裁决逻辑与数值)。

**明确 limitation(不做,诚实标注,不伪造)**:
- **方向冲突**:现状无 per-module delta(module entry 零预测),强建=张冠李戴 → limitation。
- **时间尺度冲突**:schema 无 timepoint 字段,agents/core 零 temporal → limitation。
- **细胞背景冲突**:只有单请求 cell_type,无 per-module 细胞背景结果 → limitation(现有 reliability cell_type 降级已覆盖单请求维度)。
- **证据强度对(human+IFN-β 的 metabolic_tendency vs cell_state)**:需跨请求编排(同一 query 跑 flux+state 两次),触及"多引擎结果"复杂度,成本与收益不对等 → 本单元 limitation,留后续(若 D 阶段端到端需要再议)。

## 4. 架构设计

### 4.1 现有 check_module_plan(不改其 4 条规则逻辑,只接线)
`governance/module_consistency.py::check_module_plan(plan: dict) -> list[str]`,纯确定性函数,返回违规字符串列表(空=一致):
1. `verdict` 不得比 `route_disposition` 更乐观;
2. `mismatch` 非 None → `verdict` 不得 accept;
3. `engine` 须 ∈ `MODULES[mid].engines` 白名单(非 reject);
4. `overall_verdict` 不得比最保守 entry 更乐观。

### 4.2 接线位置:runtime 后处理阶段(report 组装后)
在 `core/runtime.py` 现有"读已组装 report 追加信息"的后处理段(现挂 module_plan/llm_cross_module_notes/evidence_level 处),**module_plan 存在时**调 `check_module_plan(module_plan)` 得 `violations`。此位置 module_plan + report 信号全齐,且**不碰 reliability/critic agent 代码**。

### 4.3 违规响应(分级)
- **violations 为空**(一致,正常流程绝大多数):无任何动作,**report 字节等价完全不变**(见 §6 红线)。
- **violations 非空**(module_plan 自相矛盾,异常信号):
  - **记录 provenance**:`report.provenance["cross_module_consistency"] = {"violations": [...], "gate_abstained": bool}`(advisory,始终记录)。
  - **governance gate 真触发 abstain**:gate 只写 **report 对外字段**——`report.abstain` 置 True(最终对外弃权)、`report.prediction` 置 None(与既有 abstain 语义一致)、`report.abstain_reasons` 追加 `cross_module_inconsistency`(不覆盖既有 reasons)。**report 顶层的 reliability 产物字段(`reliability`/`model_disagreement`/`failed_checks` 等)原样保留不改**;reliability 的原 `abstain` 判定在 override **前**捕获,记入 `provenance.cross_module_consistency.reliability_original_abstain` 供审计(注:report 顶层无完整 `reliability_decision` 子结构,是从 reliability_decision **提取**的字段——`abstain`/`reliability`/`model_disagreement`/`failed_checks`;gate 只 override 对外 `abstain`+`prediction`+`abstain_reasons`,其余提取字段不动)。语义:report 对外 `abstain = reliability 原 abstain OR gate_abstained`。符合 roadmap line 127"触发 abstain 不改写确定性裁决数值"——reliability/critic agent 代码零改、裁决数值零改,只在 governance 后处理层加一道对外 abstain gate。

### 4.4 为什么这样不违红线
- reliability/critic **agent 代码零改**,它们照常裁决、其 reliability_decision/critic 数值原样保留在 report 里可审计。
- C1 是**独立 governance gate**(类比 C2 provenance 硬门思路),在裁决之后、对外之前,依据跨模块一致性 override 最终 abstain。roadmap line 127 明确授权"跨模块冲突检测只做 advisory + 触发 abstain,不改写确定性裁决数值"。
- gate 逻辑确定性(纯函数 check_module_plan + 确定性 override),**无 LLM**,`llm_used_for_prediction` 恒 false。

## 5. 关键风险与前置验证(Task 0)

**最大风险**:若现有正常流程产的 module_plan 本就有 check_module_plan 违规,接线 + abstain 会让正常请求被误 abstain,破坏字节等价 + 大量回归失败。

**Task 0 前置验证(实现第一步,先于任何接线)**:枚举现有全量测试涵盖的代表性请求(含 B4 advisory 场景 M1/M5/M8、gem_fba、GEARS 门控、abstain 边界),对每个产出的 module_plan 跑 check_module_plan,**确认现状全部无违规**(基线一致)。B4 的 downgrade 是"更保守"方向,不触发规则 1/4(它们查"更乐观"),预期兼容——但必须实测坐实,而非假设。若发现现有 module_plan 有违规,**停止 BLOCKED 报告控制器**(说明接线前提不成立,需先修 module_plan 产出或调整 check_module_plan)。

## 6. 红线(全程不可破)

- **reliability/critic 裁决逻辑与数值零改**:C1 只在 governance 后处理层 override 最终 abstain 布尔 + 清 prediction,reliability_decision 既有字段原样保留。
- **check_module_plan 4 条规则逻辑不改**:只接线调用,不改其判定(若需扩展规则,另议,本单元不改)。
- **OFFLINE 确定性字节等价**:一致 module_plan(无违规)→ 零动作 → 现有全量请求 report/trace 字节完全不变(接线是"仅在违规时才生效"的旁路 gate)。
- **确定性、无 LLM**:gate 全程确定性纯函数,`llm_used_for_prediction` 恒 false。
- **核心内核 + 仓库根 tests/ 零触碰**;REAL_ENGINES 本体/route_table.route()/registry 不改。
- **诚实不伪造**:不为"能检测冲突"编造 per-module 结果;方向/时间尺度/细胞背景/证据强度对如实标 limitation。
- 不 push;commit trailer 恒 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。

## 7. 测试(T10.5 一致性子集,落 praxis_virtualcell/tests/phase10)

- **Task 0 基线**:现有代表性请求的 module_plan 全部 check_module_plan 无违规(接线前提坐实)。
- **接线单元(一致场景零动作)**:runtime 后处理调 check_module_plan,一致 plan(无违规)→ **零动作**:不 abstain、**不往 provenance 加 `cross_module_consistency` 键**、report 与未接 gate 时字节完全一致(保 §6 字节等价红线——加任何 provenance 键都会破坏字节等价,故一致场景无痕迹,可审计性让位于确定性红线)。
- **触发 abstain**:构造(monkeypatch/注入)一个含违规的 module_plan(如 verdict 比 route 更乐观)→ gate override abstain=True + prediction None + abstain_reasons 含 `cross_module_inconsistency` + provenance `gate_abstained=True`。
- **裁决数值不变**:同上违规场景,断言 reliability_decision 的既有数值字段(reliability_score/disagreement/disposition 等)与未接 gate 时一致(gate 只改 abstain 布尔 + prediction)。
- **字节等价回归**:现有全量 OFFLINE 请求(一致 plan)3 跑 structured_report + trace 字节等价不变;全量回归数(基线 774)净增 C1 测试、0 failed。
- **确定性**:llm_used_for_prediction 恒 false。

## 8. Self-Review(占位符/一致性/范围/歧义)

- 无 TBD/TODO;limitation 明确列出(方向/时间尺度/细胞背景/证据强度对),非占位。
- 一致性:abstain 触发机制(§4.3 governance gate)与红线(§6 reliability 零改)自洽——gate 在裁决后 override 最终 abstain 布尔,不改裁决数值。
- 范围:聚焦单一实现单元(module_consistency 接线 + gate),规模适中(runtime 后处理接线 + provenance + gate override + 测试),无需再拆。
- 歧义消除:"真触发 abstain"= governance gate override 最终对外 abstain 布尔 + 清 prediction,**不等于**改 reliability 裁决逻辑或数值;"严重违规"= check_module_plan 任一违规(现有 4 规则皆 fail-closed 方向,统一触发 abstain,保守),不再细分严重度(YAGNI)。
