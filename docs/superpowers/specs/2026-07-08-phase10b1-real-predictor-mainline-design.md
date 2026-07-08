# P10.B1 设计规格:真实预测器接入 offline 主链(adapter 基建 + gem_fba 首接)

> Phase 10 / P10.B 第一子批。上游:roadmap `docs/superpowers/plans/2026-07-08-phase10-deep-validation-roadmap.md`;P10.B 分批见其中。
> 决策来源:2026-07-08 brainstorm —— 架构走**接入 offline 主链**(agent 真控制预测);B1 范围**先接 gem_fba 验证机制 + 建完整 adapter 框架**,其余 5 engine 增量。

## 一、目标

1. 建 adapter 基建,把真实 `run_*_case`(产 CaseReport)接进 offline 主链(`build_runtime`/`run_workflow`),让 agent 真正路由到 module-specific 真实预测器(论文主张核心)。
2. 首接 **gem_fba** engine(M3/M4 GEM):真实请求(bacteria/yeast gene KO growth)在主链跑真实 cobra FBA。
3. **保 mock 请求(donor_predictor,如 AHR)字节等价不变**(P10.A 焊死的基线);真实请求也字节等价(probe 已证 cobra FBA 两跑 CaseReport 字节相等)。

## 二、范围

**In scope(B1)**
- `CaseRunnerPredictorAgent`(adapter,PredictorAgent 子类)。
- `case_dispatch`(engine→runner 分发,B1 只实现 gem_fba 的 gene→growth:bacteria→ecoli、yeast→yeast)。
- CaseReport→`{prediction:{delta},uncertainty,evidence,provenance}` 映射(gem_fba)。
- `ModelApplicability` 候选改造:按 route engine 选候选(gem_fba→adapter;其余 engine 保持现状 mock 枚举)。
- `build_runtime` 注册 adapter。
- 测试:gem_fba 端到端真实预测 + 两跑字节等价 + mock 请求(AHR)零变 + 受影响测试更新。

**Out of scope(后续)**
- 其余 5 engine(state_scoring/pathway_scoring/spatial_niche/embedding/communication)接入 → B1 内**增量 task**(每 engine 一个:分发 + delta 映射 + 测试)。
- gem_fba 的 medium_shift/antibiotic 子路径(先只 gene→growth)。
- M1/M5/M8 rule-based fallback → **B2**。
- `RouteDecision.confidence` + registry 补全 8 模块 + 每模块 routing examples → **B3**。
- M2 远端 .53 通道 + M6 数据 + T10.2 全量 case + G2 门槛 → **B4**。

## 三、现状与勘察(2026-07-08)

- 14 个 `run_*_case`(如 `predictors/mechanistic/gem_model.py:55` `run_growth_case`)统一签名 `(raw_req: dict, gem/db=None, ...) → (CaseReport, RouteDecision)`,只被 tests 调用,**未接主链**。
- `CaseReport`(`agents/case_report.py:23`)7 段:case_id / structured_input / object_normalization / models_tools_selected / raw_output / baseline_comparison / reliability_decision / provenance_boundary。gem_fba 的 `raw_output` = `{wt_growth, knockouts:[{gene,in_model,growth,ratio,essential}]}`(round 5/4 位)。
- `PredictorAgent`(`predictors/base.py:14`)子类实现抽象 `run_prediction(prepared) → {prediction,uncertainty,evidence,provenance}`,基类 `handle` 走 retrieve-before-predict 门 + `assess_applicability` + `_emit` PredictorResultMessage。mock 样板 `predictors/mock_linear.py:10`。
- fan-out(`core/runtime.py:85-91`):遍历 `applicable + rejected_candidates`,逐个 `mk_message(receiver=pname,"predict",{request,brain_context})` → 收 `predictor_result` → `results` → EnsembleCoordinator。
- `ModelApplicability`(`agents/model_applicability.py:14,39`)硬编码枚举 `_CANDIDATES=("MockLinear","MockCPA","MockGEARS")`,据 brain_context 规则分 applicable/rejected。
- `EnsembleCoordinator`(`agents/ensemble.py:40-56`)**已支持单 predictor**(k<2→`single_model`,score=None);要求 `r["prediction"]["delta"]` 是向量。
- A→B raw 键映射已存在:`runtime.py:175` `_request_to_module_input`(perturbation_type→perturbation_object、output_modality→target_output)。
- **probe 确证**:Mac 本地 cobra 0.31.1 可用;`run_ecoli_growth_case({bacteria,gene,growth,[b0720]})` 两跑 `CaseReport.to_dict()` **字节相等**;b0720(gltA)KO→growth 0.0/ratio 0.0/essential(FBA 判 essential,生物学正确)、disposition accept。

## 四、设计

### 4.1 CaseRunnerPredictorAgent(adapter,`predictors/case_runner_agent.py` 新建)

PredictorAgent 子类,一个参数化 agent(内部按 engine→runner 分发,非每 engine 一个类)。`run_prediction(prepared)` 流程:
1. 从 prepared 取 request;`raw_req = request_to_module_input(request)`(复用 runtime 的 A→B 键映射,见 4.4 抽出为共享 util)。
2. `dec = route(normalize_request(raw_req))`;`engine = dec.engine`(`normalize_request` 见 `agents/species_schema.py`、`route` 见 `agents/route_table.py`;runner 内部会再 normalize+route 校验 engine,重复但确定性无害)。
3. `runner = dispatch_runner(engine, raw_req)`(4.2);若 engine 无真实 runner → 抛 `UnsupportedEngine`(基类 handle 捕获 → status="failed",不伪造)。
4. `report, _ = runner(raw_req)`(真实 case runner)。
5. `delta = map_case_delta(engine, report)`(4.3)。
6. 返回:
   ```python
   {
     "prediction": {"delta": delta},
     "uncertainty": {"disposition": report.reliability_decision["disposition"],
                     "caution_flags": report.reliability_decision["caution_flags"]},
     "evidence": report.provenance_boundary.get("rules_hit", []),
     "provenance": {**report.provenance_boundary, "case_id": report.case_id,
                    "engine": engine, "raw_output": report.raw_output},
   }
   ```
`assess_applicability`:engine 有真实 runner 且 route≠reject → applicable(score 由 disposition 映射,如 accept→1.0/caution→0.6/downgrade→0.3);否则 reject(rejection_reason=engine 或 route reason)。

### 4.2 engine→runner 分发(`predictors/case_dispatch.py` 新建)

```python
def dispatch_runner(engine: str, raw_req: dict):
    """engine + 请求上下文 → 具体 run_*_case。B1 只实现 gem_fba 的 gene→growth。"""
    species = raw_req.get("species")
    obj = raw_req.get("perturbation_object")
    if engine == "gem_fba" and obj == "gene":
        if species == "bacteria":
            from praxis_virtualcell.predictors.mechanistic.ecoli_gem import run_ecoli_growth_case
            return run_ecoli_growth_case
        if species == "yeast":
            from praxis_virtualcell.predictors.mechanistic.yeast_gem import run_yeast_growth_case
            return run_yeast_growth_case
    raise UnsupportedEngine(f"B1 未接入 engine={engine} object={obj} species={species}")
```
(其余 engine / gem_fba 的 medium·drug 子路径在后续增量 task 往这里加分支。`UnsupportedEngine` 新异常,继承 PraxisVCError。)

### 4.3 CaseReport→delta 映射(`case_dispatch.py` 内 `map_case_delta`)

按 engine 一个规则。B1 gem_fba:
```python
def map_case_delta(engine: str, report) -> list[float]:
    if engine == "gem_fba":
        # 每个 KO 基因 growth 相对 WT 的变化:ratio-1(essential→ratio 0→-1.0;无效应→0)。
        # ratio 已 round 4 位(gem_model.py:95),确定性。基因不在 GEM→ratio None→跳过(不虚构)。
        return [round(k["ratio"] - 1.0, 4) for k in report.raw_output["knockouts"]
                if k["ratio"] is not None]
    raise UnsupportedEngine(engine)
```
契约:delta 是确定性数值向量(继承 raw_output 的 round);空 delta(全基因不在 GEM)时 reliability 已 abstain(disposition),ensemble 收 vecs 为空 → 与现状 abstain 语义一致。

### 4.4 ModelApplicability 候选改造(`agents/model_applicability.py`)

**最小侵入**:保持现有 mock 枚举逻辑,前置 engine 分诊。
```python
def handle(self, message, bus):
    req = message.payload["request"]; bc = message.payload["brain_context"]
    raw = request_to_module_input(req)          # 复用共享 util(A→B 键)
    engine = route(normalize_request(raw)).engine
    if engine in _REAL_ENGINES:                  # B1: {"gem_fba"};后续增量往里加
        # 真实 engine → 候选 = 单个 adapter agent name;跳过 mock 枚举
        applicable, rejected = ["CaseRunner"], []
        bc2 = {**bc, "routing": {..., "real_engine": engine}}
        # emit applicability_decided(applicable=["CaseRunner"])
        return
    # 否则:现状 mock 枚举逻辑完全不变(donor_predictor/AHR + 未接 engine 走这里)
    ...
```
说明:
- `request_to_module_input` 从 `runtime.py:175` 抽为共享函数(如 `agents/request_adapter.py` 或 `core/`),runtime 与 ModelApplicability 共用,避免重复。
- `_REAL_ENGINES` = 已接入的真实 engine 集合(B1={"gem_fba"});其余真实 engine(state_scoring 等)暂不在集合内 → 走现状 mock 枚举(多半 reject→abstain),与接入前一致,直到各自增量 task 加入集合。
- `donor_predictor`/AHR 恒走 else 分支(mock 枚举)→ **字节等价不变**。

### 4.5 build_runtime 注册(`workflows/predict_delta_expression.py`)

`register_agent(CaseRunnerPredictorAgent(name="CaseRunner"))`,与现有 3 mock 并列注册。fan-out 遇 `applicable=["CaseRunner"]` → dispatch 到 adapter。

### 4.6 数据流(两条路径)

- **mock 请求**(human AHR gene→expression):route=donor_predictor → ModelApplicability else 分支 → 3 mock 枚举 → ensemble → **与 P10.A 完全一致,字节等价**。
- **真实请求**(bacteria b0720 gene→growth):route=gem_fba → applicable=["CaseRunner"] → adapter 调 run_ecoli_growth_case → 真实 FBA → delta=[-1.0] → ensemble(single_model) → Reliability accept → Report。**新真实预测路径,字节等价(cobra 确定)**。

## 五、影响与迁移(重要)

接入 gem_fba 后,**bacteria/yeast gene KO growth 请求从现状 abstain(mock 全 reject)变成真实 FBA 预测(accept)**。这是**预期的语义提升,非回归**。受影响测试(执行时定位后更新,如 `test_offline_workflow.py:16` "bacteria 无适用模型→abstain"):核对确认变化确由"接入真实 GEM"引起后,更新断言为真实预测结果。**若发现 mock 请求(donor_predictor/expression)行为改变 = 真实回归,停下排查。**
- **P10.A 的 `test_offline_rerun_byte_equal[abstain]` 用 b0720 gene→expression**(delta_expression),route 走微生物 expression 铁律 **reject**(非 gem_fba growth),**不受 B1 影响**,仍 abstain。
- baseline 快照(`test_baseline_*`)只覆盖 AHR(donor_predictor)与 4 物种 routing engine/disposition,不跑 bacteria growth 主链预测 → 预计不破(执行时确认)。

## 六、测试(`tests/phase10/test_t10_2_module_contracts.py` 新建 + 复用/更新既有)

1. **gem_fba 端到端真实预测**:offline `run_query({bacteria,gene,growth,[b0720]})` → 不 abstain、reliability accept、prediction.delta=[-1.0]、provenance 含 tool=cobrapy/case_id/engine=gem_fba。
2. **真实请求两跑字节等价**:同请求 3 跑 structured_report+trace 的 canonical sha256 全等(复用 P10.A `_canon_hash` 思路)。
3. **mock 请求零变**:AHR(human gene expression)offline 仍走 3 mock、reliability 与接入前一致(锁 P10.A 基线)。
4. **adapter 映射单元测试**:map_case_delta(gem_fba, 构造 CaseReport) → 预期 delta;UnsupportedEngine 对未接 engine 抛错。
5. **受影响测试更新** + 全量回归复绿(≥670 + 新增,0 failed)。

## 七、B1 完成标准(gate)

1. adapter + case_dispatch + map_case_delta + ModelApplicability 改造 + build_runtime 注册落地。
2. gem_fba 真实请求在主链跑真实 FBA(bacteria/yeast gene KO growth),reliability accept + 真实 delta。
3. mock 请求(AHR)字节等价不变(P10.A 基线锁定)。
4. 真实请求两跑字节等价。
5. 受影响测试(bacteria/yeast growth abstain→predict)已更新、全量回归 0 failed。
6. ruff 全绿;`agents/` 治理裁决·reliability·critic·LLM 边界逻辑未改(只改 ModelApplicability 候选选择);根 tests/ 零触碰;trailer 恒 `Co-Authored-By: Claude Opus 4.8`。

## 八、红线

- 不碰 reliability/critic/provenance/LLM 边界的裁决逻辑;ModelApplicability 只改"选哪些候选",不改 ortholog/negative-transfer 判定。
- 真实预测确定性:只用确定性 runner(cobra FBA 已证字节稳);不引入 wall-clock/随机。
- adapter 诚实:CaseReport 的 disposition/boundary 如实透传,不伪造;基因不在 GEM → 如实(ratio None 跳过 + disposition abstain/caution)。
- 不 push;里程碑 tag 本地。

## 九、后续增量(B1 内 + 后批)

- B1 内增量 task:逐 engine 接入(state_scoring→cell_state/emt/fate、pathway_scoring→metabolic_tendency、spatial_niche、embedding、communication),每个 = dispatch 分支 + map_case_delta 规则 + 端到端测试 + `_REAL_ENGINES` 加入。
- gem_fba 的 medium_shift/antibiotic 子路径。
- 之后 B2(M1/M5/M8 fallback)/B3(registry+confidence)/B4(M2 远端+T10.2+G2)。
