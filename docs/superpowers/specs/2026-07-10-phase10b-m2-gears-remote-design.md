# P10.B(余下)M2 基因枢纽 GEARS 远端 .53 真实接入设计 spec

> P10.B 的 M2 单元(genetic_hub 真实预测器)。与 B1/B2/B3 的**本地确定性机制模型**(cobra FBA)不同,本单元接的是**非确定性神经网 GEARS**、**只能在 .53(GPU+torch)跑**。上游:roadmap `docs/superpowers/plans/2026-07-08-phase10-deep-validation-roadmap.md` §六.1(公开好模型优先接入),用户 4 项 brainstorm 决策(下 §一)。

## 一、用户拍板的 4 项设计决策(2026-07-10 brainstorm)

1. **方向 A:env 门控真实 CaseRunner**(扩 B1-B3 的 REAL_ENGINES + CaseRunner 分诊模式)。GEARS_CKPT 门控:.53 有 ckpt+torch → 真实 GEARS;Mac/无 ckpt → **fail-closed 回退现有 mock**(本地 OFFLINE 字节等价保留)。
2. **只接 GEARS**(第一批)。scGPT(gene→表征 baseline)留后续。
3. **本单元含实际 .53 SSH 验证**(控制器 SSH 到 .53 真跑 GEARS 过新 CaseRunner 路径,端到端证真)。
4. **Option B:GEARS 自算 delta(扰动 − 对照)**。GEARS 原生只产绝对表达(`gears_native_absolute_expression`,`not_comparable_to_donor_base`);M2 让 GEARS 同时预测对照态,`delta = 扰动态 − 对照态`(均 mean-over-cells)——是**真 delta**且类型与模块正常输出一致,但**属 GEARS-内部、非 donor 可比**,明标不冒充 donor delta。**绝不把绝对表达填进 delta 槽冒充 donor delta 预测。**

## 二、诚实边界与核心张力

**核心张力**:B1-B3 红线"OFFLINE 确定性字节等价"由**本地确定性机制模型**(cobra 同输入同输出)满足;GEARS 是**非确定性神经网**(registry 明标 `no_fixed_seed`,retrain noise 0.8392→0.8461)+ 需 GPU/torch(Mac 不可用)。故本单元**细化确定性红线**(下 §六):机制/mock 预测器仍字节等价;GEARS 神经网预测**显式标注 `non_deterministic` + 远端门控**,其字节等价**不作要求也不断言**;Mac 主链(mock)字节等价**不变**。

**诚实红线**:①GEARS delta 明标 `gears_internal_delta` + `not_comparable_to_donor_base`,不冒充 donor delta;②Mac 无 GEARS → fail-closed 回退 mock(不假装真跑、不静默编造);③基因不在 GEARS vocab(pert_list 9853)→ fail-closed abstain(不改测试凑绿);④`llm_used_for_prediction` 恒 False(GEARS 是模型不是 LLM,与"预测器是否真实"正交);⑤GEARS 点估计无标定不确定性 → `uncertainty.available=False`(不假造 CI)。

## 三、勘察坐实的现状(写 spec 前已核对)

- **M2/genetic_hub 现状**:engine=`donor_predictor`(route_table 名,非真模型),OFFLINE 下走 3 个自声明 mock(MockLinear/MockCPA/MockGEARS,常数 delta 0.0/0.5/0.4 → ensemble 均值 0.3)。`donor_predictor` **不在** `REAL_ENGINES`(`predictors/case_dispatch.py:13`),CaseRunner 从不被派发到 genetic_hub。
- **GearsWrapper 已存在**(`praxis_virtualcell/model_zoo/wrappers/gears_wrapper.py`):`run_prediction(model_input)` 用 `model_input["targets"]`,lazy import torch+gears(缺 → fail-closed),重建 PertData(`GEARS_DATA_ROOT`/`GEARS_DATA_NAME` 可 env 覆盖)、`load_pretrained(ckpt_stem)`、`predict([targets])`。**当前返回绝对表达**(`{"prediction":{"expression":...,"value_type":"gears_native_absolute_expression","not_comparable_to_donor_base":True},...}`),基因须 ∈ `g.pert_list` 否则 fail-closed。`declare_scope`=human/genetic_hub/perturbation_response/gene+gene_combination。**未被 build_runtime/case_dispatch 注册**。
- **registry.yaml `gears` 条目**:status=`planned`,wrapper=GearsWrapper,source=`remote:gears_ckpt`,requires=[torch,gpu],assets(model.pt sha 5fd17e.../config.pkl sha 7da56a...),remote_env host zkyd@10.102.106.53。
- **.53 就绪(本单元实测)**:SSH 免密通;repo `/home/zkyd/data1/mzy/PRAXIS-virtualcell`;conda base `/home/zkyd/miniconda3` env `virtualcell`(torch+gears 已装,`import torch,gears` 成功);GEARS ckpt `/home/zkyd/data1/mzy/gears_ckpt/norman_2019/{model.pt,config.pkl}` 在位;gears_data `/home/zkyd/data1/mzy/gears_data/norman_donor2` 在位。**非交互 shell 里 GEARS_CKPT 未设**——需运行时显式 `export GEARS_CKPT=/home/zkyd/data1/mzy/gears_ckpt/norman_2019`。
- **CaseRunner 契约**(`predictors/case_runner_agent.py`):`run_prediction` → `dispatch_runner(engine, raw)` → `runner(raw)` → CaseReport → `map_case_delta(engine, report)` → `prediction.delta`;`_result_status` disposition==abstain → rejected(经既有 reliability `if not used` 如实 abstain)。
- **ModelApplicability 分诊**(`agents/model_applicability.py:32-44`):`engine in REAL_ENGINES` → CaseRunner 单一候选;否则 mock 枚举(_CANDIDATES)。

## 四、架构:ckpt 门控的真实 GEARS 路径

### 4.1 分诊层(ckpt-aware,新增维度)
`donor_predictor` **不能无条件进 REAL_ENGINES**(否则 Mac 无 GEARS 会走 CaseRunner→fail-closed→abstain,破坏 Mac 现有 mock 行为)。故新增 **ckpt 门控**:
```python
# agents/model_applicability.py 分诊扩展(不改 REAL_ENGINES 本身)
if engine in REAL_ENGINES or (engine == "donor_predictor" and gears_available()):
    # → CaseRunner 单一候选
```
`gears_available()`(新增,`predictors/case_dispatch.py` 或独立 gating 模块):`os.environ.get("GEARS_CKPT")` 非空 **且** torch+gears 可 import(轻量探测,不真载 ckpt)。**Mac → False → 原 mock 枚举不变;.53(GEARS_CKPT 设)→ True → CaseRunner→GEARS。** 确定性、无副作用。

### 4.2 dispatch 层(新增 donor_predictor 分支)
`dispatch_runner("donor_predictor", raw)`(`case_dispatch.py` 加分支):
- 守卫:`species=="human"` + `perturbation_object∈{gene,gene_combination}` + `target_output=="expression"`(GearsWrapper.declare_scope 对齐);不满足 → `raise UnsupportedEngine`(→ 回退 mock 或诚实 abstain,与 B1-B3 一致)。
- 满足 → 返回 **GEARS runner**(封装 GearsWrapper),runner 产 CaseReport(delta + provenance)。
`map_case_delta("donor_predictor", report)` → GEARS-内部 delta。

### 4.3 GEARS-内部 delta(Option B,诚实核心)
GEARS runner(新增 `predictors/ml/gears_case.py` 或等价,复用 GearsWrapper):
1. `perturbed = GEARS.predict([targets])` 的 mean-over-cells 绝对表达(现有 wrapper 逻辑)。
2. `control = GEARS 对照态预测`(mean-over-cells)。**对照 API 待 .53 实现时坐实**:GEARS 惯例 `predict([['ctrl']])` 或 PertData 的 ctrl_adata 均值;两者取其一,以 .53 实跑确认的真实 API 为准(本单元含 .53 验证,当场核实)。
3. `delta = perturbed − control`(逐基因,`round()` 定点到与 mock delta 一致精度)。
4. CaseReport:`prediction.delta = <delta>`;`provenance` 标 `{"model":"gears","value_type":"gears_internal_delta","not_comparable_to_donor_base":True,"no_fixed_seed":True,"non_deterministic":True,"ckpt_sha":<registry sha>}`;`uncertainty.available=False`(点估计);基因不在 vocab → disposition=abstain(fail-closed)。

> **wrapper 改动最小化**:优先在 GEARS runner/case 层算 delta(调 GearsWrapper 两次或扩 wrapper 一个 `run_delta` 方法),**不破坏 GearsWrapper 现有 `run_prediction` 绝对表达契约**(它有既有测试/provenance)。具体是"runner 两调 wrapper" vs "wrapper 加 run_delta",留 plan 定;spec 只要求:delta = 扰动 − 对照,明标 gears_internal。

### 4.4 注册
`build_runtime`(`workflows/predict_delta_expression.py`)：CaseRunnerPredictorAgent 已注册(B1);GEARS runner 经 dispatch_runner 挂到 donor_predictor,**无需新 Agent**(复用 CaseRunner,与 B2/B3 一致)。registry.yaml `gears` status 由 `planned` → 保持 `planned`(broker 层不变,ckpt 仍 requires_manual_fetch;真实性由运行时 gears_available 门控体现,不动 broker fail-closed)——**registry status 不改**,避免碰 model_broker 五关。

## 五、数据流

human gene→expression 请求(如 norman vocab 内基因)→ ModelApplicability：
- **Mac(GEARS_CKPT 未设)**:`gears_available()=False` → 原 mock 枚举(MockLinear/CPA/GEARS)→ ensemble 0.3,**行为字节不变**。
- **.53(GEARS_CKPT 设)**:`gears_available()=True` → CaseRunner 单一候选 → dispatch_runner donor_predictor → GEARS runner → GEARS.predict 扰动+对照 → delta → CaseReport → `prediction.delta`=GEARS-内部 delta,provenance 标 gears_internal/non_deterministic;基因不在 vocab → 诚实 abstain。

## 六、确定性红线细化(本单元新增,写入 spec 权威)

- **不变**:Mac 主链(mock)+ 机制预测器(gem_fba/pathway_scoring)+ 所有 OFFLINE mock 请求 → **字节等价断言保留**。
- **新增例外(仅 GEARS 神经网)**:GEARS 预测 `non_deterministic=True`(no_fixed_seed),其数值**不作字节等价断言**;GEARS 路径**只在 .53(GEARS_CKPT 门控)激活**,Mac 恒不触发。GEARS 测试走 `pytest.mark.remote`(Mac skip),断言**结构 + 诚实标注 + delta 类型**(非数值字节等价)。
- `llm_used_for_prediction` 恒 False 不变。

## 七、.53 验证流程(本单元交付的一部分)

控制器 SSH 到 .53 亲验(用户决策 3):
```bash
ssh zkyd@10.102.106.53 'bash -lc "
  source /home/zkyd/miniconda3/etc/profile.d/conda.sh && conda activate virtualcell &&
  cd /home/zkyd/data1/mzy/PRAXIS-virtualcell && git pull &&
  export GEARS_CKPT=/home/zkyd/data1/mzy/gears_ckpt/norman_2019 &&
  export GEARS_DATA_ROOT=/home/zkyd/data1/mzy/gears_data GEARS_DATA_NAME=norman_donor2 &&
  PYTHONPATH=\$PWD python -m pytest praxis_virtualcell/tests -m remote -p no:cacheprovider -q
"'
```
验收:①新增的 GEARS remote 端到端测试(gene→expression 过 CaseRunner→GEARS→delta)在 .53 **passed**;②controller 用一次性脚本独立核实 delta = 扰动 − 对照(非绝对表达、非 mock 0.3)、provenance 标 gears_internal/non_deterministic;③既有 remote 测试(test_public_models_remote.py)仍 passed。**Mac 侧不 skip 的全量仍 758+/0 failed(mock 路径字节等价)。**

## 八、影响

- **Mac(开发/CI/审稿复现)**:genetic_hub 请求行为**字节不变**(mock 0.3);GEARS 测试 skip。全量回归数不减。
- **.53(真实能力)**:human gene→expression 命中 GEARS vocab → 真实 GEARS-内部 delta(明标非 donor 可比);vocab 外 → 诚实 abstain。
- **reliability/critic 裁决**:零改(CaseRunner 经既有 `_result_status` 透传 disposition;GEARS abstain 复用 B1 机制)。
- **8 模块真实覆盖**:M2 从 mock → **真实(.53 GEARS)**,真实覆盖 M2/M3/M4/M7(+微生物)。

## 九、红线

- 不碰 reliability/critic/route() 裁决;REAL_ENGINES 本身不改(donor_predictor 经 ckpt 门控独立判);registry status 不改(不碰 model_broker 五关)。
- GearsWrapper 现有 `run_prediction` 绝对表达契约 + provenance + 既有测试**不破坏**。
- **GEARS delta 明标 gears_internal_delta / not_comparable_to_donor_base,绝不冒充 donor delta**;绝对表达绝不填 delta 槽。
- Mac fail-closed 回 mock(不假真跑、不静默编造);vocab 外 fail-closed abstain。
- OFFLINE mock 路径字节等价不变;GEARS 非确定性显式标注 + 远端门控。`llm_used_for_prediction` 恒 False。
- 核心内核 + 根 tests/ 零触碰;不 push;trailer 恒 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。

## 十、完成标准

1. `gears_available()` ckpt 门控 + ModelApplicability ckpt-aware 分诊(Mac→mock、.53→CaseRunner)。
2. `dispatch_runner` donor_predictor 分支(human+gene+expression 守卫)+ GEARS runner 产 GEARS-内部 delta(扰动−对照)+ map_case_delta 分支。
3. **Mac 侧**:全量回归字节等价(mock 路径不变,758+/0 failed);GEARS 单元/契约测试(fail-closed 回 mock、vocab 守卫)以 mock/结构层覆盖,不需 torch。
4. **.53 侧**:GEARS remote 端到端测试 passed(真实 delta=扰动−对照、非 mock),控制器 SSH 亲验 + 独立核实 provenance 诚实标注;既有 remote 测试仍 passed。
5. ruff 全绿;台账 + 记忆勾账(M2 从 mock → .53 真实 GEARS-内部 delta 可运行);确定性红线细化写入台账。

## 十一、Self-review 覆盖

- 诚实核心:Option B delta 明标 gears_internal 非 donor 可比,不张冠李戴(不填绝对表达进 delta 槽)。
- 门控准:ckpt-aware 分诊使 Mac 字节等价保留、.53 真实,不无条件进 REAL_ENGINES。
- 最小侵入:复用 CaseRunner/case_dispatch(不新 Agent)、不改 GearsWrapper 绝对表达契约、不改 registry status/broker、不碰裁决。
- 确定性红线细化明确(机制/mock 字节等价;GEARS 非确定性+远端门控),写入 spec 权威。
- .53 验证流程具体可执行(SSH+conda+env+pytest -m remote),对照 API 待 .53 实测坐实(本单元含验证,当场核实)。
- 未越界:只接 GEARS(scGPT 留后续);不建自动化远程 RPC(用户否 C);registry/broker 不碰。
