# Phase 6:公开模型接入(GEARS/scGPT 收编进 ModelBroker + provenance + fail-closed)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 **.53 上真跑的 GEARS/scGPT 能力**(torch+GPU 真装、有真锚点 ΔPearson)产品化成 **ModelBroker 插件** —— 不是从零训模型,而是把"远端脚本 + 硬编码 `/home/zkyd/...` 路径 + 200MB ckpt"收编进 Phase 2 已落地的治理框架:①新增 `GearsWrapper`/`ScgptWrapper`(扩 `ModelWrapper`→`PredictorAgent`,补 `declare_scope()`/`estimate_uncertainty()`/`declare_provenance()`,**缺 torch/ckpt → fail-closed 优雅降级**);②registry.yaml 补 `scgpt` 条目、给 `gears`/`scgpt` 加 `assets`(ckpt 声明 + sha256 版本锁位)与 `provenance`(锚点数字 + 远端坐标),ckpt/数据挪出硬编码路径 → 由 registry **声明**;③broker 对新公开模型解析:装了 torch+ckpt sha 对 → available→wrapper;缺 torch/gpu/ckpt → fail-closed **不静默 accept**(registry 里仍可见,标 `planned`/`requires_manual_fetch`/`unavailable`);④真 GEARS/scGPT 推理跑通设计成 **gated 契约测试**(`@pytest.mark.remote`,本地 Mac 无 torch 自动 skip,只在 .53 真跑);⑤provenance/可分发性校验 + Phase 6 完成闸门。Phase 6 属 **v1.3 里程碑(public release)** 的第一块(与 Phase 7 并行,共同依赖 Phase 2 broker,v1.3 tag 留 Phase 8)。

**Architecture:** 全部**净新增 + 复用,不推倒**。`GearsWrapper`/`ScgptWrapper` 与 `GemWrapper`(`model_zoo/wrappers/gem_wrapper.py`)**同构**:extends `ModelWrapper`(拿 fail-closed + retrieve-before-predict 门),`__init__` **lazy** 载 torch/ckpt(缺则抛 → 上层 fail-closed),`run_prediction` 内部包现有 `predictors/ml/` 的 `MLPredictorAgent`/`build_predictor_from_ckpt`(scGPT)或 GEARS `predict([['gene']])`(GEARS)——**不重写 ML 内核**。registry.yaml 只**追加/扩字段**(新增 `scgpt` 条目 + 给 `gears`/`scgpt` 加 `assets`/`provenance`);`ModelZooRegistry._validate` 扩一条 `public_model` 带 `assets` 时的 schema 校验(net-new 分支,不改现有 self_trained 校验)。`ModelBrokerAgent` 复用现有 `_resolve`(status/requires/source 三关已 fail-closed),Phase 6 只**加 assets sha256 版本锁关**(缺 ckpt/ sha 不匹配 → available=False),**不改现有三关逻辑**。Phase 6 只交付 wrapper + registry 声明 + broker assets 关 + gated 契约测试,**不接 runtime 管线**(接管线是 Phase 8 网站发行时的事,与 Phase 2 GemWrapper 未接管线同理)。

**Tech Stack:** Python 3.13 / pytest 参数化 + `@pytest.mark.remote`(conftest:无 torch 自动 skip)/ PyYAML / hashlib(sha256,标准库)。**本地 `.venv/bin/python` 有 cobra、无 torch**(实测 `importlib.util.find_spec('torch') is None`)——故 GEARS/scGPT 的**缺依赖 fail-closed 路径本地可测且计入 passed**;**真推理(load ckpt + forward)只能 .53 跑,本地 `@pytest.mark.remote` skip**(诚实:这批 skip 会让 skip 基线从 25 升到 27,见铁律)。

---

## 铁律(每个 task 验收都要守)

- **纯新增 + 复用,不改现有逻辑**:只新增 `model_zoo/wrappers/gears_wrapper.py`、`model_zoo/wrappers/scgpt_wrapper.py`、新测试;`model_zoo/registry.yaml`(追加 scgpt 条目 + 给 gears/scgpt 扩 assets/provenance,**不改** ecoli_gem/yeast_deletion_fitness 条目)、`model_zoo/registry.py`(`_validate` **追加** assets schema 分支,不改现有 self_trained/白名单校验)、`agents/model_broker_agent.py`(`_resolve` **追加** assets sha256 关,不改现有 status/requires/source 三关)是**受控最小扩现有**。**不改** `core/` `predictors/`(现有 ml 桥不动)`route_table` 任何逻辑;若发现现有行为与预期不符 → **真实 bug,停下报告,不改代码/测试迁就**(红线 5)。
- **红线 6(本 Phase 头号红线):模型缺失/无 provenance/缺依赖/ckpt sha 不匹配 → fail-closed,绝不静默 accept、绝不假装可用**。每个 wrapper task **都有专门的缺依赖(缺 torch)fail-closed 测试**;每个 broker task 都断"planned/缺 torch/缺 ckpt → available=False + reason 点名缺什么"。**绝不为了让测试绿而 mock 掉真模型语义、或把 fail-closed 改成静默可用**(违者 = 破坏 Phase 6 卖点)。
- **红线 1:OFFLINE 默认零 LLM 不变**。Phase 6 不碰 LLM(wrapper/registry/broker 全零 LLM);wrapper 不 import `agents_llm`/`llm_orchestration`。`assert_llm_boundaries` 三 flag 恒 False(不碰 config)。
- **红线 3:只在 `praxis_virtualcell/tests` 工作**,永不碰根 `tests/` 的 ~1398 继承测试。
- **红线 5:不迁就**:GEARS/scGPT 真推理测试与真实行为不符 → 特征化 pin 真值(锚点 ΔPearson 用 `pytest.approx` 宽容度对齐 finding 的诚实标注)或真 bug BLOCKED,绝不改语义凑绿。
- **增量复用不推倒**:GearsWrapper/ScgptWrapper 包现有 `predictors/ml/`(`MLPredictorAgent`/`build_predictor_from_ckpt`/`donor_bridge`)+ GEARS 原生 `predict`,不重写 ML 内核(路线图红线 5)。
- **测试口径** = `praxis_virtualcell/tests`(**绝不碰根 `tests/`**)。Phase 6 起点基线(当前分支 `feat/v0.9-phase0-module-core`,HEAD `f07e0dc`,含 Phase 0–5)**实跑核实 = 556 passed / 25 skipped / collected 581**(2026-07-05 `pytest --junit-xml` 实测:`tests=581 failures=0 errors=0 skipped=25`;注:台账/commit message 里的 "556 passed" = collected 581 − skipped 25,一致)。`-q` 不打印精确 passed;精确数用 `--junit-xml` 属性换算:**passed = tests(collected) − skipped − failures − errors**。验收只认:**failures=0 errors=0** + 每 task 新增测试条数正确(离线可跑的计入 passed,`@pytest.mark.remote` 的计入 skipped)。
- **⚠ skip 基线诚实声明(重要,与前几 Phase 不同)**:Phase 6 的**真推理 gated 契约测试**(Task 6.5)用 `@pytest.mark.remote`,本地无 torch 自动 skip → **skip 基线从 25 升到 27**(新增 2 个 remote-marked skip:一个 GEARS 真推理、一个 scGPT 真推理)。这是**诚实的、设计使然的** skip(与 Phase 2 的 cobra/torch gated 同款惯例,conftest `pytest.mark.remote` 无 torch 自动 skip),**不是** flaky/隐藏失败。验收口径相应改为:**failures=0 errors=0 skipped=27**(25 旧 + 2 新 remote)。其余所有 task(6.1–6.4/6.6)的缺依赖 fail-closed / registry 声明 / broker assets 关 / provenance 校验测试**全部离线确定性可跑、计入 passed、不新增 skip**。
- **每 task 全量回归绿**后再 commit:`PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`;commit 前 `find . -name '._*' -delete`(外置盘 AppleDouble);**只 `git add` 本 task 明列的文件**(工作树里 `docs/superpowers/plans/UPGRADE-PROGRESS.md` 有控制器的未提交改动,**绝不带进 commit**);commit message 末尾加 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`;当前分支 `feat/v0.9-phase0-module-core`,**不 push**。
- **不打 tag**:Phase 6 **不是里程碑**(v1.3 要等 Phase 6+7+8 全完成,Phase 8 才打 v1.3.0)。Phase 6 全 task 绿 = 完成闸门,**不打 tag**。

---

## 数据契约(已实跑核实 2026-07-05,计划代码与之对齐)

以下是 Phase 6 依赖的**真实接口/字段/路径/锚点**(实读源码 + finding 核实,非路线图旧描述):

- **`model_zoo/wrappers/base.py:ModelWrapper`**(实读)extends `PredictorAgent`:`declare_scope() -> dict`(**abstractmethod**,子类必实现,返回 `{species: list, module: str, task: list, perturbation?: list}`);`estimate_uncertainty(model_input, prediction) -> dict`(默认从 `run_prediction` 取 uncertainty,None → `{"available": False, "reason": "model_reports_no_uncertainty"}`,失败 → `{"available": False, "reason": "uncertainty_estimation_failed: ..."}`)。`name` 类属性。**无 `declare_provenance()` 方法**(Phase 6 Task 6.1 net-new 加,不改 base 现有两方法)。
- **`predictors/base.py:PredictorAgent`**(实读):`assess_applicability(request, brain_context)->(score, reason)`、`prepare_input(request, brain_context)->dict`(默认 `{"targets": request.get("perturbation_targets", [])}`)、`run_prediction(model_input)->dict`(**abstract**,返回 `{prediction, uncertainty}`)、`handle(message, bus)`(**fail-closed 三态**:`assess_applicability` reject → `status="rejected" prediction=None`;`run_prediction` 抛异常 → `status="failed" prediction=None provenance={"error": str(e)}`;成功 → `status="success"`;retrieve-before-predict 门:bus 无 `brain_retrieved` → raise `RetrieveBeforePredictError`)。emit `predictor_result`,receiver=`EnsembleCoordinator`。**GearsWrapper/ScgptWrapper 的缺 torch/ckpt fail-closed 就是走"`run_prediction` 抛 → handle 归 failed"这条既有路径**(不新造 fail-closed 机制)。
- **`model_zoo/wrappers/gem_wrapper.py:GemWrapper`**(实读,**同构样板**):extends ModelWrapper;`__init__(sbml_path=None)` **lazy** `from ...ecoli_gem import EcoliGEM`(缺 cobra → import/构造抛);`declare_scope()` 返回 dict;`run_prediction(model_input)` 取 `model_input.get("targets", [])` 真跑 `knockout_many`;`estimate_uncertainty` 覆写为 `{"available": True, "method": "deterministic_fba", "note": ...}`。**GEARS/scGPT wrapper 与它逐行同构,只是 lazy import 换成 torch + ckpt。**
- **`predictors/ml/donor_bridge.py`**(实读,scGPT 复用):`build_predictor_from_ckpt(ckpt_stem: str) -> (model, cfg)`(读 `ckpt_stem + ".json"` 的 `class_name`/`kwargs` 重建 + `torch.load(ckpt_stem + ".pt", weights_only=False)` load state_dict;**import torch + donor `/home/zkyd/data1/mzy/Virtual cell`**);`load_norman(split, ...)`。**文件顶层 `import torch` → 本地无 torch import 即抛 ModuleNotFoundError**(这是 fail-closed 触发点)。
- **`predictors/ml/ml_predictor_agent.py:MLPredictorAgent`**(实读,scGPT 复用):`__init__(donor_model)`;`predict_tensor(control, pert_emb, *, kind, targets) -> torch.Tensor`(调 donor `model.predict(ctx, pert).mean`);`as_donor_predictor()`。顶层 `import torch`。
- **`predictors/ml/agent_adapter.py:MLBackedPredictorAgent`**(实读):extends `PredictorAgent`;`__init__(donor_model, *, control, pert_table, pert_dim, name)`;`prepare_input`(schema→tensor,`_pert_emb_for`)、`run_prediction`(调 `MLPredictorAgent(...).predict_tensor`,返回 `{"prediction": {"delta": [...], "n_genes": N}, "uncertainty": {"std": float}}`);`make_ml_agent(donor_model, *, norman_ds, name)`。**scGPT wrapper 的真推理路径就是复用它**(不重写)。
- **`predictors/mock_gears.py:MockGEARSAgent`**(实读):`name="MockGEARS"`;`assess_applicability` 加"gene 不在 graph vocabulary → rejected";`run_prediction(model_input)` 返回 `{"prediction": {"delta": [0.4 for _ in targets] or [0.4]}, "uncertainty": {"sigma": 0.25}}`(每基因常数 0.4)。**这是本地无 torch 时 GearsWrapper 的"降级占位/mock 语义参照",但 Phase 6 GearsWrapper 不静默用 mock 冒充真 GEARS —— 真推理缺 torch 就 fail-closed,不返回 0.4 假装可用。**
- **`model_zoo/registry.py:ModelZooRegistry`**(实读):`__init__(registry_path=None)`(默认 `model_zoo/registry.yaml`);`_load` → `_validate(name, entry)`(fail-closed:`_REQUIRED_FIELDS=(name,type,species,module,task,source,license,status,wrapper,version)` 缺任一 → ValueError;`type∈LEGAL_TYPES=(public_model,self_trained)`;`status∈LEGAL_STATUS=(available,planned,missing)`;`module∈M.MODULE_ORDER`;`species` 非空 list;`requires` 是 list;`self_trained` 必带 `training_card`(training_data/split/baseline/metrics/provenance));`names()`/`get(name)`(未知→KeyError)/`status(name)`/`is_available(name)`/`by_module(module_id)`(未知模块→KeyError)/`by_species(species)`。**Task 6.3 给 `_validate` 加 `assets` schema 分支(有 assets 时每条须含 filename/sha256/bytes 或 sha256=null 占位),不改现有分支。**
- **`model_zoo/cache.py:ModelCache`**(实读):`__init__(root=None)`(默认 `~/.cache/praxis_virtualcell/model_zoo/`);`asset_path(model_name, asset) -> Path`(命名空间 `<root>/<model_name>/<asset>`);`check(model_name, asset, *, sha256=None) -> AssetStatus(available, path, reason)`(缺文件 → `available=False reason="asset_not_found: ..."`;sha 不匹配 → `available=False reason="sha256_mismatch: ..."`;命中 → `available=True`)。**Task 6.4 broker 的 assets 关直接调 `ModelCache.check`,不改 cache。**
- **`model_zoo/downloader.py:resolve_source(entry) -> dict`**(实读):`cobra_bundled*` → resolved/available;`local:<rel>` → 存在则 resolved,缺则 requires_manual_fetch;`remote:*`/`self_trained:*` → `{"status": "requires_manual_fetch", "available": False, ...}`;缺 source → ValueError。**gears/scgpt 的 source=`remote:*` → 现有 downloader 已判 available=False**(broker source 关已 fail-closed,Phase 6 不改)。
- **`agents/model_broker_agent.py:ModelBrokerAgent`**(实读):`__init__(registry=None)`;`handle` emit `model_broker_result`(receiver=`EnsembleCoordinator`,payload=`{model_name, available, status, wrapper, reason}`);`_resolve(model_name)` 顺序:①未知→KeyError→`available=False reason="unknown model..."`;②`status != available`→`available=False reason="model status=..., not available"`;③`missing_deps=[d for d in requires if not _dep_available(d)]` 非空→`available=False reason="missing required dependencies: [...]"`;④`resolve_source` not available→`available=False reason="source not resolvable: ..."`;⑤全过→`available=True reason="ok"`。`_dep_available(dep)`:`_PY_DEPS={"torch","cobra"}` 内用 `importlib.util.find_spec`;**gpu 等非 python 依赖返 False**(fail-closed)。**Task 6.4 在 ④ 之后加 ⑤assets sha256 关(有 assets 时每条过 `ModelCache.check`,任一缺/sha 不匹配 → available=False),原 ⑤"全过 available" 后移为 ⑥**。
- **本地依赖实况(实测)**:`.venv/bin/python` → `cobra 0.31.1` 有、`importlib.util.find_spec('torch') is None`(**无 torch**)。故:gears(requires `[torch,gpu]`)→ broker 现在就 `available=False reason="missing required dependencies: ['torch', 'gpu']"`(torch find_spec=None + gpu 恒 False);scgpt(requires `[torch,gpu]`)同理。**这是 Phase 6 缺依赖 fail-closed 的本地真实触发点,不需 monkeypatch 即天然 fail-closed。**
- **`tests/conftest.py`**(实读,gating):`@pytest.mark.remote` → 无 torch(`import torch` 失败)自动 `skip(reason="无 torch(Mac 本地),跳过 remote 标记测试")`;`@pytest.mark.llm` → 无 `DEEPSEEK_API_KEY` 自动 skip。**当前 25 skip 由这些 marker 构成。Task 6.5 的真推理测试 `pytestmark = pytest.mark.remote` → 本地新增 2 skip(25→27)。**
- **`predictors/ml/test_ml_donor_bridge.py` / `test_ml_agent_bus.py`**(实读,**remote gated 测试样板**):`pytestmark = pytest.mark.remote`;真推理测试从 `os.environ["W4A_LINEAR_CKPT"]`/`os.environ["W4B_CKPT_DIR"]` 取 ckpt(远端 env 给),`build_predictor_from_ckpt` 重建 + 真跑;bus 测试造 `brain_retrieved` + `_payload`。**Task 6.5 逐样复刻这套 remote gated 惯例。**

### 真锚点数字(来自 finding,写进 registry.yaml provenance;诚实标注)

- **GEARS**(`docs/findings/finding_w4c_gears.md`):GEARS 原生 norman pipeline 全通,GNN train 5 epoch;`pearson 0.9834, pearson_de 0.8392, mse 0.0068`(GEARS `compute_metrics`,**simulation split,含 baseline 的 absolute-expression pearson**);⚠**与 donor base 的 per-cell ΔPearson(0.6–0.7)不可比**(指标不同 + split 不同,ADR-W4c-1)。GEARS 无固定 seed(重训 0.8392→0.8461)。**同表可比 ΔPearson 入表 A 是 backlog**(见 `docs/L4-gears-remote-runbook.md`,需 .53 上包 `GearsDonorAdapter` 经 `EvalAgent.evaluate` 在 donor test split 上评)。→ provenance 写 `pearson_de: 0.8392`(GEARS native simulation split)+ `comparable_delta_pearson: null`(未做,标 backlog)+ `not_comparable_to_donor_base: true`。
- **scGPT**(`docs/findings/finding_w4c_scgpt.md`):frozen scGPT encoder(53.8M)+ 轻 head(2.47M),复用 donor `train_predictor` on donor norman;`SCGPT_NORMAN_DELTA_PEARSON = 0.4407, cosine 0.9808, n=7290`(**per-cell ΔPearson,与表 A 同口径可比**);**明显低于 base**(cpa 0.6716 等);根因 frozen backbone + 轻 head 在 norman 饱和(train_loss 0.045→0.044 不降)。集成 pipeline 全通:`MLPredictorAgent(scgpt).predict_tensor == donor predict` 逐元素(atol 1e-6)。ckpt:`/home/zkyd/data1/mzy/scgpt_ckpt/norman_2019/pretrained_backbone.{pt,json}`(json kwargs 含 `backbone_name=scgpt`;pt ≈196MB)。→ provenance 写 `delta_pearson: 0.4407`(donor norman test split,同表 A 口径)+ `cosine: 0.9808` + `n: 7290` + `note: "frozen backbone 偏低,SOTA 需 fine-tune(backlog)"`。
- **远端坐标**(挪出硬编码 → registry 声明):GEARS env `virtualcell`(torch 2.6+cu124);scGPT env `vc-scgpt`(torch 2.3+cu121),ckpt `scgpt_ckpt/norman_2019/pretrained_backbone.{pt,json}`;donor 源码 `/home/zkyd/data1/mzy/Virtual cell`。这些进 registry.yaml 的 `assets`(相对声明 + `source_note` 指认远端获取路径)与 `provenance.remote_env`,**不再散落在脚本硬编码**。

**与路线图/规格旧描述的真实代码校正清单(按真代码写,不照抄旧描述):**
1. **registry.yaml 里 `gears` 条目已存在**(Phase 2 种子:planned/requires `[torch,gpu]`/wrapper `gears_wrapper.GearsWrapper`),`scgpt` **不存在**。→ Phase 6 **不新建 gears 条目**(改为给它扩 `assets`/`provenance` 字段),**新建 scgpt 条目**。
2. **`gears_wrapper.py` 文件不存在**(registry.yaml 指向它但 Phase 2 未实现,这是"planned wrapper 类路径")。→ Task 6.1 net-new 创建;创建后 registry 指向不变,但**status 仍 planned/broker 仍 fail-closed**(因缺 torch/ckpt),不因文件存在就 available。
3. **`ModelWrapper` 无 `declare_provenance()`**(base 只有 declare_scope + estimate_uncertainty)。→ Task 6.1 给 base **net-new 加** `declare_provenance()` 默认实现(返回 `{}`),GearsWrapper/ScgptWrapper 覆写返回锚点;**不改** declare_scope/estimate_uncertainty 现有两方法。
4. **GEARS 接口 `predict([['gene']])` 与 donor predictor 不同构**(finding_w4c_gears §集成:"communicative predictor-agent 适配留 backlog")→ GearsWrapper 的真推理 `run_prediction` **不能复用 `MLPredictorAgent`/donor_bridge**(那是 pert_emb 接口),须走 GEARS 原生 `predict`;本地无 torch/无 GEARS 包 → lazy import GEARS 抛 → fail-closed。**Task 6.1 GearsWrapper 的真推理体标 gated(.53),本地只测 lazy import 缺 torch → fail-closed。**
5. **scGPT 接口已同构 donor**(`MLPredictorAgent(scgpt).predict_tensor == donor predict`,finding_w4c_scgpt §集成全通)→ ScgptWrapper 的真推理 `run_prediction` **复用 `build_predictor_from_ckpt` + `MLPredictorAgent`**(现成),不重写。**Task 6.2 ScgptWrapper 真推理体标 gated(.53),本地测 lazy import 缺 torch → fail-closed。**
6. **本地无 torch → gears/scgpt 天然 fail-closed**(broker `_dep_available('torch')=find_spec=None=False`),**不需 monkeypatch 造缺依赖**(与 Phase 2 broker 测试 monkeypatch 造缺 cobra 不同——那是因 cobra 本地有,须模拟缺;torch 本地本就没有,直接真实 fail-closed)。
7. **provenance 不是 `PredictorResultMessage.provenance`**(那是运行时逐次预测的 provenance dict)。Phase 6 的"模型级 provenance"(训练锚点/远端坐标/可分发性)是 **registry.yaml 声明 + wrapper `declare_provenance()`**,是**静态模型卡**,与运行时 provenance 正交。计划里"provenance"专指前者。

---

## v1.3 里程碑待确认项(科学决策;已落最小确定性集保证可测 + fail-closed,不阻塞执行)

规划 subagent 已就下列需用户拍板的科学核心点**落最小确定性集**(保证 Phase 6 可测 + fail-closed),标为"v1.3 待确认",到 v1.3 pause 时连同 .53 真推理结果一起交用户定:

1. **GEARS/scGPT 的 scope 边界声明**:本 Phase 落 `GearsWrapper.declare_scope() = {species:[human], module:genetic_hub, task:[perturbation_response], perturbation:[gene, gene_combination]}`、`ScgptWrapper.declare_scope() = {species:[human], module:genetic_hub, task:[predict_delta_expression], perturbation:[gene]}`(对齐 registry.yaml module=genetic_hub + finding 的 norman 训练域）。**待确认**:是否扩到 mouse(ortholog 投射)/更多 task —— 当前保守只声明 human/norman 域,超域输入靠继承的 `assess_applicability` 走 rejected(fail-closed 不越域预测)。
2. **estimate_uncertainty 口径**:GEARS 无原生 uncertainty → `ScgptWrapper`/`GearsWrapper` 覆写 `estimate_uncertainty` 返回 `{"available": False, "reason": "model_reports_no_calibrated_uncertainty", "method": "point_estimate"}`(诚实:点估计,无标定不确定性),**不假造 CI**。**待确认**:未来是否用 ensemble disagreement / MC-dropout 补真 uncertainty(backlog)。
3. **真锚点数字是否写进 provenance**:本 Phase **写**(GEARS pearson_de 0.8392 native + comparable=null;scGPT ΔPearson 0.4407 同表口径),并**诚实标注不可比性/frozen 偏低/backlog**。**待确认**:GEARS 同表可比 ΔPearson(需 .53 跑 `GearsDonorAdapter`,见 L4 runbook)何时补入 —— 当前 `comparable_delta_pearson: null` + `status_note: backlog`,不虚构。
4. **requires_manual_fetch 的取数流程**:本 Phase registry.yaml 的 `assets` 用 `source_note` 声明"远端 .53 路径 + 如何获取"(人可读),`sha256: null`(占位,真 sha 待 .53 上算过填);broker assets 关遇 `sha256: null` → 判 `requires_manual_fetch`(不静默 available)。**待确认**:是否建 gated HTTP/OSS 分发源(当前只声明远端手动获取路径,零网络请求)。

---

# Phase 6:公开模型接入 · 任务

## Task 6.1:ModelWrapper 加 `declare_provenance()` + GearsWrapper(缺 torch fail-closed)

**决策说明:** 先给 `ModelWrapper` base **net-new 加** `declare_provenance() -> dict` 默认实现(返回 `{}`,不改 declare_scope/estimate_uncertainty)。再建 `GearsWrapper`(与 `GemWrapper` 同构):`declare_scope`(human/genetic_hub/perturbation_response)、`declare_provenance`(GEARS 锚点)、`estimate_uncertainty`(点估计,无标定 → available=False,不假造)、`run_prediction`(真推理体 **lazy import GEARS + torch**;本地无 torch → import 抛 → 继承 `handle` 归 `failed`,fail-closed)。**红线 6 专门测试**:本地无 torch 时 `run_prediction` 抛(不静默返回 mock 0.4 冒充可用)。

**Files:**
- Modify: `praxis_virtualcell/model_zoo/wrappers/base.py`(末尾加 `declare_provenance` 默认方法,不改现有两方法)
- Create: `praxis_virtualcell/model_zoo/wrappers/gears_wrapper.py`
- Test: `praxis_virtualcell/tests/test_gears_wrapper.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_gears_wrapper.py`:

```python
"""Phase 6:GearsWrapper —— 把 .53 上真跑的 GEARS 收编为 ModelWrapper 插件。
本地(无 torch)可测:declare_scope/declare_provenance 契约、estimate_uncertainty 诚实点估计、
缺 torch → run_prediction fail-closed(不静默返回 mock 0.4 冒充真 GEARS)。
真推理(load ckpt + GEARS predict)是 .53 的事 → Task 6.5 gated。"""
import importlib.util

import pytest

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper
from praxis_virtualcell.model_zoo.wrappers.gears_wrapper import GearsWrapper

_HAS_TORCH = importlib.util.find_spec("torch") is not None


def test_is_model_wrapper_subclass():
    assert issubclass(GearsWrapper, ModelWrapper)


def test_declare_scope_human_genetic_hub():
    scope = GearsWrapper().declare_scope()
    assert scope["module"] == "genetic_hub"          # 对齐 registry.yaml gears.module
    assert "human" in scope["species"]
    assert "perturbation_response" in scope["task"]
    assert "gene" in scope["perturbation"]


def test_declare_provenance_has_gears_anchor_and_honest_flags():
    prov = GearsWrapper().declare_provenance()
    assert prov["model"] == "gears"
    # 锚点:GEARS native pearson_de 0.8392(finding_w4c_gears)
    assert prov["metrics"]["pearson_de"] == pytest.approx(0.8392, abs=1e-4)
    # 诚实:与 donor base 不可比 + 同表 ΔPearson 未做(backlog)
    assert prov["not_comparable_to_donor_base"] is True
    assert prov["metrics"]["comparable_delta_pearson"] is None
    assert "remote_env" in prov                      # 远端坐标进 provenance(挪出硬编码)


def test_estimate_uncertainty_is_honest_point_estimate():
    """GEARS 无标定不确定性 → available=False + method=point_estimate(不假造 CI)。"""
    unc = GearsWrapper().estimate_uncertainty({}, None)
    assert unc["available"] is False
    assert unc["method"] == "point_estimate"


@pytest.mark.skipif(_HAS_TORCH, reason="本地无 torch 才测 fail-closed;有 torch 时真推理走 Task 6.5 gated")
def test_run_prediction_fail_closed_without_torch():
    """红线 6:缺 torch → run_prediction 抛(不静默返回 mock 0.4 冒充可用)。"""
    with pytest.raises(Exception) as ei:
        GearsWrapper().run_prediction({"targets": ["AHR"]})
    msg = str(ei.value).lower()
    assert "torch" in msg or "gears" in msg or "no module" in msg


@pytest.mark.skipif(_HAS_TORCH, reason="本地无 torch 才测 handle fail-closed 归 failed")
def test_handle_degrades_to_failed_without_torch():
    """缺 torch 时经 bus handle → status=failed（继承 PredictorAgent fail-closed），prediction=None。"""
    from praxis_virtualcell.core.bus import MessageBus
    from praxis_virtualcell.core.message import AgentMessage

    bus = MessageBus()
    bus.send(AgentMessage("b0", "SpeciesBrain", "X", "brain_retrieved", {}, "t0"))
    w = GearsWrapper()
    req = {"species": "human", "input_modality": "scRNA",
           "task_type": "perturbation_response", "perturbation_type": "gene",
           "perturbation_targets": ["AHR"]}
    bc = {"species": "human",
          "model_applicability": {"GearsWrapper": {"supported_species": ["human"],
              "supported_modalities": ["scRNA"], "supported_tasks": ["perturbation_response"]}},
          "rules_referenced": ["r1"]}
    w.handle(AgentMessage("m1", "X", "GearsWrapper", "predict",
                          {"request": req, "brain_context": bc}, "t1"), bus)
    res = bus.latest("predictor_result").payload
    assert res["status"] == "failed"                 # 不是 success、不是静默 accept
    assert res["prediction"] is None


def test_no_llm_import_in_module():
    import praxis_virtualcell.model_zoo.wrappers.gears_wrapper as m
    src = open(m.__file__, encoding="utf-8").read()
    assert "agents_llm" not in src and "llm_orchestration" not in src
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_gears_wrapper.py -q`
Expected: FAIL(ModuleNotFoundError: ...gears_wrapper;且 base 无 declare_provenance)。

- [ ] **Step 3: 给 base 加 `declare_provenance`**

在 `praxis_virtualcell/model_zoo/wrappers/base.py` 的 `estimate_uncertainty` 方法**之后**追加(不改现有两方法):

```python
    def declare_provenance(self) -> dict:
        """返回模型级 provenance(静态模型卡:训练数据/指标锚点/远端坐标/可分发性)。
        默认空(机制模型如 GEM 无训练锚点);ML wrapper(GEARS/scGPT)覆写返回真锚点。
        与运行时 PredictorResultMessage.provenance 正交(那是逐次预测的证据链)。"""
        return {}
```

- [ ] **Step 4: 写 `gears_wrapper.py`**

写 `praxis_virtualcell/model_zoo/wrappers/gears_wrapper.py`:

```python
"""GearsWrapper:把 .53 上真跑的 GEARS(GNN,norman)收编为 ModelWrapper 插件。

与 GemWrapper 同构:extends ModelWrapper(拿 fail-closed + retrieve-before-predict 门)。
GEARS 接口 `predict([['gene']])` 与 donor predictor 不同构(finding_w4c_gears),故真推理
**不复用 MLPredictorAgent/donor_bridge**,走 GEARS 原生 API,lazy import(缺 torch/GEARS → 抛 →
继承 handle 归 failed,fail-closed)。本地无 torch → run_prediction 缺依赖 fail-closed;
真推理(load ckpt + GEARS predict)是 .53 的事(Task 6.5 gated)。

锚点(finding_w4c_gears):GEARS native pearson_de 0.8392(simulation split,含 baseline 的
absolute-expression pearson),⚠与 donor base 的 per-cell ΔPearson 不可比;同表 ΔPearson 是 backlog。
"""
from __future__ import annotations

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper


class GearsWrapper(ModelWrapper):
    name = "GearsWrapper"

    def __init__(self, ckpt_stem: str | None = None) -> None:
        # 不在构造时载 torch/GEARS(允许无 torch 环境实例化以查 scope/provenance/契约);
        # 真推理时 lazy import,缺依赖 → 抛 → fail-closed。
        self._ckpt_stem = ckpt_stem

    def declare_scope(self) -> dict:
        return {
            "species": ["human"],                    # norman 训练域(finding);扩 mouse 留 v1.3 待确认
            "module": "genetic_hub",                 # 对齐 registry.yaml gears.module
            "task": ["perturbation_response"],
            "perturbation": ["gene", "gene_combination"],
        }

    def declare_provenance(self) -> dict:
        return {
            "model": "gears",
            "type": "public_model",
            "training_data": "norman_2019 (Perturb-seq, K562)",
            "architecture": "GEARS GNN (hidden=64), 5 epoch",
            "metrics": {
                # GEARS 原生 compute_metrics(simulation split,absolute-expression pearson)
                "pearson": 0.9834,
                "pearson_de": 0.8392,
                "mse": 0.0068,
                # 同表 A 可比的 per-cell ΔPearson 未做(需 .53 GearsDonorAdapter,见 L4 runbook)
                "comparable_delta_pearson": None,
                "metric_note": "GEARS native pearson on absolute expression; NOT donor delta_pearson",
            },
            "not_comparable_to_donor_base": True,     # ADR-W4c-1:指标+split 不同,不可同表对比
            "no_fixed_seed_note": "GEARS retrain noise 0.8392->0.8461",
            "remote_env": {                            # 挪出硬编码 → 声明式
                "host": "zkyd@10.102.106.53",
                "conda_env": "virtualcell (torch 2.6+cu124)",
                "donor_src": "/home/zkyd/data1/mzy/Virtual cell",
            },
            "distributable": False,                    # 需 torch+GPU+GEARS 包;缺则 fail-closed
            "status_note": "capability real on .53; comparable-table ΔPearson is backlog",
        }

    def estimate_uncertainty(self, model_input: dict, prediction: dict | None) -> dict:
        # GEARS 输出点估计,无标定不确定性 → 诚实 available=False(不假造 CI)
        return {"available": False, "reason": "model_reports_no_calibrated_uncertainty",
                "method": "point_estimate"}

    def run_prediction(self, model_input: dict) -> dict:
        """真推理:lazy import torch + GEARS,load ckpt,GEARS predict([[gene]])。
        缺 torch/GEARS/ckpt → 抛 → 继承 handle 归 failed(fail-closed,不静默返回 mock)。
        本地无 torch → 此处即抛;.53 上真跑(Task 6.5 gated)。"""
        import torch  # noqa: F401 — 缺 torch 即抛 ModuleNotFoundError(fail-closed 触发点)
        from gears import GEARS  # noqa: F401 — 缺 GEARS 包即抛

        if not self._ckpt_stem:
            raise RuntimeError("gears ckpt 未声明(registry assets requires_manual_fetch);fail-closed")
        # 真推理体(.53)：load GEARS ckpt → predict targets → 返回 {prediction, uncertainty}。
        # 具体 load/predict 以 .53 GEARS save/load API 为准(Task 6.5 远端填实并 gated 验证)。
        raise NotImplementedError(
            "GEARS real inference runs on .53 (gated); local has no torch/GEARS -> fail-closed")
```

> **诚实说明**:`run_prediction` 真推理体在本地环境**必抛**(无 torch → `import torch` 先抛;即使有 torch 也因 `NotImplementedError` 抛),这是**设计的 fail-closed**——GEARS 真 predict 的 load/save API 须在 .53 上核实后填(Task 6.5 gated 验证)。**这不是占位符偷懒**:本地无 GEARS 包 + 无 ckpt,任何"能跑的本地实现"都只能是 mock 0.4 假装可用,那正是红线 6 禁止的。fail-closed 抛异常是唯一诚实选择。

- [ ] **Step 5: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_gears_wrapper.py -q`
Expected: 8 passed(本地无 torch,两个 `skipif(_HAS_TORCH)` 的 fail-closed 测试**执行并通过**——因 `_HAS_TORCH=False` → 不 skip)。

- [ ] **Step 6: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 564 passed / 25 skipped / 0 failed(556 + 8 新;不新增 skip——本 task 无 remote-marked 测试)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/model_zoo/wrappers/base.py praxis_virtualcell/model_zoo/wrappers/gears_wrapper.py praxis_virtualcell/tests/test_gears_wrapper.py
git commit -m "feat(phase6): ModelWrapper.declare_provenance + GearsWrapper(scope/锚点 provenance/点估计 uncertainty/缺 torch fail-closed 不静默 mock)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 6.2:ScgptWrapper(缺 torch/ckpt fail-closed + 真推理复用 MLPredictorAgent)

**决策说明:** 建 `ScgptWrapper`(与 GearsWrapper 同构):`declare_scope`(human/genetic_hub/predict_delta_expression)、`declare_provenance`(scGPT 锚点 ΔPearson 0.4407 + frozen 偏低诚实标注 + ckpt 坐标)、`estimate_uncertainty`(点估计)、`run_prediction`(真推理体 **复用 `build_predictor_from_ckpt` + `MLPredictorAgent`**——scGPT 接口已同构 donor,finding_w4c_scgpt;本地无 torch → `donor_bridge` 顶层 `import torch` 抛 → fail-closed)。**红线 6 专门测试**:缺 torch → fail-closed;registry 声明的 ckpt 缺失/ sha 待填 → 不静默 available(broker 关在 Task 6.4 测)。

**Files:**
- Create: `praxis_virtualcell/model_zoo/wrappers/scgpt_wrapper.py`
- Test: `praxis_virtualcell/tests/test_scgpt_wrapper.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_scgpt_wrapper.py`:

```python
"""Phase 6:ScgptWrapper —— 把 .53 上真跑的 scGPT(frozen backbone + head)收编为 ModelWrapper。
本地(无 torch)可测:scope/provenance 契约、诚实点估计 uncertainty、缺 torch → run_prediction
fail-closed(不静默返回假 delta)。真推理(load 196MB ckpt + MLPredictorAgent)是 .53 → Task 6.5 gated。
scGPT 接口已同构 donor(finding_w4c_scgpt:predict_tensor==donor predict),故真推理复用
build_predictor_from_ckpt + MLPredictorAgent,不重写 ML 内核。"""
import importlib.util

import pytest

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper
from praxis_virtualcell.model_zoo.wrappers.scgpt_wrapper import ScgptWrapper

_HAS_TORCH = importlib.util.find_spec("torch") is not None


def test_is_model_wrapper_subclass():
    assert issubclass(ScgptWrapper, ModelWrapper)


def test_declare_scope_human_genetic_hub():
    scope = ScgptWrapper().declare_scope()
    assert scope["module"] == "genetic_hub"
    assert "human" in scope["species"]
    assert "predict_delta_expression" in scope["task"]


def test_declare_provenance_has_scgpt_anchor_and_honest_flags():
    prov = ScgptWrapper().declare_provenance()
    assert prov["model"] == "scgpt"
    # 锚点:scGPT ΔPearson 0.4407(donor norman test split,同表 A 口径可比)
    assert prov["metrics"]["delta_pearson"] == pytest.approx(0.4407, abs=1e-4)
    assert prov["metrics"]["cosine"] == pytest.approx(0.9808, abs=1e-4)
    assert prov["metrics"]["n"] == 7290
    # 诚实:frozen backbone 偏低,SOTA 需 fine-tune(backlog)
    assert prov["frozen_backbone_underperforms"] is True
    # ckpt 坐标进 provenance(挪出硬编码)
    assert "pretrained_backbone" in prov["remote_env"]["ckpt"]


def test_declare_provenance_comparable_to_donor_base():
    """scGPT ΔPearson 与 donor base 同口径可比(与 GEARS 不同)。"""
    prov = ScgptWrapper().declare_provenance()
    assert prov.get("not_comparable_to_donor_base", False) is False


def test_estimate_uncertainty_is_honest_point_estimate():
    unc = ScgptWrapper().estimate_uncertainty({}, None)
    assert unc["available"] is False
    assert unc["method"] == "point_estimate"


@pytest.mark.skipif(_HAS_TORCH, reason="本地无 torch 才测 fail-closed;有 torch 时真推理走 Task 6.5 gated")
def test_run_prediction_fail_closed_without_torch():
    """红线 6:缺 torch → run_prediction 抛(不静默返回假 delta 冒充可用)。"""
    with pytest.raises(Exception) as ei:
        ScgptWrapper().run_prediction({"targets": ["AHR"]})
    msg = str(ei.value).lower()
    assert "torch" in msg or "scgpt" in msg or "no module" in msg or "ckpt" in msg


@pytest.mark.skipif(_HAS_TORCH, reason="本地无 torch 才测 handle fail-closed 归 failed")
def test_handle_degrades_to_failed_without_torch():
    from praxis_virtualcell.core.bus import MessageBus
    from praxis_virtualcell.core.message import AgentMessage

    bus = MessageBus()
    bus.send(AgentMessage("b0", "SpeciesBrain", "X", "brain_retrieved", {}, "t0"))
    w = ScgptWrapper()
    req = {"species": "human", "input_modality": "scRNA",
           "task_type": "predict_delta_expression", "perturbation_type": "gene",
           "perturbation_targets": ["AHR"]}
    bc = {"species": "human",
          "model_applicability": {"ScgptWrapper": {"supported_species": ["human"],
              "supported_modalities": ["scRNA"], "supported_tasks": ["predict_delta_expression"]}},
          "rules_referenced": ["r1"]}
    w.handle(AgentMessage("m1", "X", "ScgptWrapper", "predict",
                          {"request": req, "brain_context": bc}, "t1"), bus)
    res = bus.latest("predictor_result").payload
    assert res["status"] == "failed"
    assert res["prediction"] is None


def test_no_llm_import_in_module():
    import praxis_virtualcell.model_zoo.wrappers.scgpt_wrapper as m
    src = open(m.__file__, encoding="utf-8").read()
    assert "agents_llm" not in src and "llm_orchestration" not in src
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_scgpt_wrapper.py -q`
Expected: FAIL(ModuleNotFoundError: ...scgpt_wrapper)。

- [ ] **Step 3: 写 `scgpt_wrapper.py`**

写 `praxis_virtualcell/model_zoo/wrappers/scgpt_wrapper.py`:

```python
"""ScgptWrapper:把 .53 上真跑的 scGPT(frozen backbone 53.8M + 轻 head 2.47M)收编为 ModelWrapper。

与 GemWrapper/GearsWrapper 同构。scGPT 接口已同构 donor(finding_w4c_scgpt:
MLPredictorAgent(scgpt).predict_tensor == donor predict,atol 1e-6),故真推理**复用**
predictors/ml 的 build_predictor_from_ckpt + MLPredictorAgent,不重写 ML 内核。
lazy import(donor_bridge 顶层 import torch → 缺 torch 即抛 → 继承 handle 归 failed,fail-closed)。
本地无 torch → run_prediction 缺依赖 fail-closed;真推理(load 196MB ckpt)是 .53(Task 6.5 gated)。

锚点(finding_w4c_scgpt):ΔPearson 0.4407 / cosine 0.9808 / n 7290(donor norman test split,
同表 A 口径,与 donor base 可比);frozen backbone + 轻 head 在 norman 饱和 → 明显低于 base(诚实)。
ckpt:/home/zkyd/data1/mzy/scgpt_ckpt/norman_2019/pretrained_backbone.{pt,json}(pt≈196MB)。
"""
from __future__ import annotations

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper


class ScgptWrapper(ModelWrapper):
    name = "ScgptWrapper"

    def __init__(self, ckpt_stem: str | None = None) -> None:
        # 不在构造时载 torch/ckpt(允许无 torch 环境查 scope/provenance);真推理时 lazy import。
        self._ckpt_stem = ckpt_stem

    def declare_scope(self) -> dict:
        return {
            "species": ["human"],                    # norman 域;扩 mouse 留 v1.3 待确认
            "module": "genetic_hub",
            "task": ["predict_delta_expression"],
            "perturbation": ["gene"],
        }

    def declare_provenance(self) -> dict:
        return {
            "model": "scgpt",
            "type": "public_model",
            "training_data": "donor norman_2019 (frozen scGPT encoder + light head)",
            "architecture": "frozen scGPT backbone 53.8M + head 2.47M (train_loss 0.045->0.044 saturated)",
            "metrics": {
                # 同表 A 口径的 per-cell ΔPearson(与 donor base 可比)
                "delta_pearson": 0.4407,
                "cosine": 0.9808,
                "n": 7290,
                "metric_note": "per-cell delta_pearson on donor norman test split (comparable to base)",
            },
            "not_comparable_to_donor_base": False,    # 同口径可比(与 GEARS 不同)
            "frozen_backbone_underperforms": True,     # 诚实:0.4407 明显低于 base(cpa 0.6716 等)
            "underperform_reason": "frozen foundation encoder + light head saturates on norman; "
                                   "SOTA needs fine-tune (unfreeze 53.8M + flash_attn) — backlog",
            "remote_env": {
                "host": "zkyd@10.102.106.53",
                "conda_env": "vc-scgpt (torch 2.3+cu121)",
                "donor_src": "/home/zkyd/data1/mzy/Virtual cell",
                "ckpt": "/home/zkyd/data1/mzy/scgpt_ckpt/norman_2019/pretrained_backbone.{pt,json}",
            },
            "distributable": False,                    # 196MB ckpt + torch;缺则 fail-closed
            "status_note": "integration pipeline fully verified on .53; frozen baseline honest-low",
        }

    def estimate_uncertainty(self, model_input: dict, prediction: dict | None) -> dict:
        return {"available": False, "reason": "model_reports_no_calibrated_uncertainty",
                "method": "point_estimate"}

    def run_prediction(self, model_input: dict) -> dict:
        """真推理:lazy import donor_bridge(顶层 import torch → 缺则抛)→ build_predictor_from_ckpt
        重建 scgpt backbone + load head → MLPredictorAgent 真跑。缺 torch/ckpt → 抛 → handle 归 failed
        (fail-closed,不静默返回假 delta)。本地无 torch → 此处即抛;.53 真跑(Task 6.5 gated)。"""
        if not self._ckpt_stem:
            raise RuntimeError("scgpt ckpt 未声明(registry assets requires_manual_fetch);fail-closed")
        # donor_bridge 顶层 import torch;本地无 torch → ModuleNotFoundError(fail-closed 触发点)
        from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt

        model, _cfg = build_predictor_from_ckpt(self._ckpt_stem)  # 重建 scgpt backbone + load head
        # 真推理复用 MLPredictorAgent(scGPT 接口已同构 donor,finding_w4c_scgpt)。
        # control/pert_emb 的 schema→tensor 适配由 .53 上的 norman ds 提供(Task 6.5 远端填实并 gated 验证)。
        raise NotImplementedError(
            "scGPT real inference (load 196MB ckpt + MLPredictorAgent on norman) runs on .53 (gated); "
            "local has no torch/ckpt -> fail-closed")
```

> **诚实说明**:同 Task 6.1——`run_prediction` 本地必抛(无 torch → `donor_bridge` import torch 抛;有 torch 也因 ckpt 缺失/NotImplementedError 抛)。真推理体的 control/pert_emb 适配须在 .53 上用真 norman ds 填实(Task 6.5 gated 验证 `predict_tensor == donor predict`)。fail-closed 是唯一诚实选择,**绝不本地伪造 delta 冒充可用**。

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_scgpt_wrapper.py -q`
Expected: 9 passed(本地无 torch → `skipif(_HAS_TORCH)` 的两个 fail-closed 测试执行并通过)。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 573 passed / 25 skipped / 0 failed(564 + 9 新;不新增 skip)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/model_zoo/wrappers/scgpt_wrapper.py praxis_virtualcell/tests/test_scgpt_wrapper.py
git commit -m "feat(phase6): ScgptWrapper(scope/锚点 provenance ΔPearson 0.4407 可比+诚实低/点估计/缺 torch 复用 donor_bridge fail-closed 不伪造 delta)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 6.3:registry.yaml 补 scgpt 条目 + gears/scgpt 扩 assets/provenance + `_validate` assets schema

**决策说明:** ckpt/数据挪出硬编码 → 由 registry **声明**。给 registry.yaml:①**新增** `scgpt` 条目(public_model/human/genetic_hub/planned/wrapper=ScgptWrapper/requires `[torch,gpu]`);②给现有 `gears` 与新 `scgpt` 加 `assets`(声明 ckpt 文件名 + `sha256: null` 占位 + `source_note` 远端获取路径)与 `provenance`(锚点摘要,与 wrapper `declare_provenance` 呼应)。`_validate` **追加** assets schema 分支(有 assets 时每条须含 `filename` + `sha256` 键——`sha256` 可为 null 占位,但键必须在;fail-closed:结构坏 → ValueError),**不改** 现有必填字段/白名单/self_trained 校验。

**Files:**
- Modify: `praxis_virtualcell/model_zoo/registry.yaml`(新增 scgpt 条目 + gears/scgpt 加 assets/provenance;不改 ecoli_gem/yeast_deletion_fitness)
- Modify: `praxis_virtualcell/model_zoo/registry.py`(`_validate` 末尾追加 assets schema 分支)
- Test: `praxis_virtualcell/tests/test_registry_public_models.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_registry_public_models.py`:

```python
"""Phase 6:registry 公开模型声明(gears/scgpt)+ assets schema 校验。
铁律:ckpt 挪出硬编码 → registry assets 声明(filename + sha256 占位 + source_note);
assets 结构坏 → ValueError(fail-closed)。gears/scgpt 仍 planned(缺 torch/ckpt → broker fail-closed)。"""
import pytest

from praxis_virtualcell.model_zoo.registry import ModelZooRegistry


@pytest.fixture(scope="module")
def reg():
    return ModelZooRegistry()


def test_scgpt_entry_present_and_planned(reg):
    e = reg.get("scgpt")
    assert e["type"] == "public_model"
    assert e["module"] == "genetic_hub"
    assert "human" in e["species"]
    assert e["status"] == "planned"                  # 缺 torch/ckpt → 仍 planned,不静默 available
    assert e["wrapper"].endswith("scgpt_wrapper.ScgptWrapper")


def test_gears_and_scgpt_have_assets_declared(reg):
    for name in ("gears", "scgpt"):
        e = reg.get(name)
        assert e.get("assets"), f"{name} 缺 assets 声明(ckpt 须挪出硬编码进 registry)"
        for a in e["assets"]:
            assert "filename" in a and "sha256" in a  # sha256 可为 null 占位,但键必须在
            assert "source_note" in a                 # 远端获取路径(requires_manual_fetch 取数流程)


def test_gears_and_scgpt_have_provenance(reg):
    assert reg.get("gears")["provenance"]["metrics"]["pearson_de"] == pytest.approx(0.8392, abs=1e-4)
    sp = reg.get("scgpt")["provenance"]["metrics"]
    assert sp["delta_pearson"] == pytest.approx(0.4407, abs=1e-4)


def test_query_by_module_genetic_hub_includes_public_models(reg):
    names = {e["name"] for e in reg.by_module("genetic_hub")}
    assert {"gears", "scgpt"} <= names


def test_illegal_assets_shape_is_rejected(tmp_path):
    """assets 条目缺 filename/sha256 键 → ValueError(fail-closed)。"""
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "models:\n"
        "  m:\n"
        "    name: m\n"
        "    type: public_model\n"
        "    species: [human]\n"
        "    module: genetic_hub\n"
        "    task: t\n"
        "    source: 'remote:x'\n"
        "    license: MIT\n"
        "    status: planned\n"
        "    wrapper: x.Y\n"
        "    version: v1\n"
        "    requires: [torch]\n"
        "    reliability_policy: ml_disagreement\n"
        "    assets:\n"
        "      - filename: w.pt\n"                    # 缺 sha256 键
        "        source_note: remote\n",
        encoding="utf-8")
    with pytest.raises(ValueError) as ei:
        ModelZooRegistry(registry_path=str(bad))
    assert "assets" in str(ei.value) or "sha256" in str(ei.value)
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_registry_public_models.py -q`
Expected: FAIL(`scgpt` 未注册 → KeyError;gears 无 assets/provenance;`_validate` 未校验 assets)。

- [ ] **Step 3: 扩 registry.yaml(gears 加 assets/provenance + 新增 scgpt)**

在 `praxis_virtualcell/model_zoo/registry.yaml` 中,把现有 `gears` 条目**在 `reliability_policy: ml_disagreement` 之后追加**(不改 gears 已有字段):

```yaml
    assets:
      - filename: gears_model.pt          # GEARS 原生 save/load 产物(.53)
        sha256: null                       # 占位:真 sha 待 .53 上算过填(requires_manual_fetch)
        source_note: "fetch from zkyd@10.102.106.53 conda env virtualcell; GEARS native save_model"
    provenance:
      training_data: norman_2019
      architecture: GEARS GNN hidden=64 5epoch
      metrics: {pearson: 0.9834, pearson_de: 0.8392, mse: 0.0068, comparable_delta_pearson: null}
      not_comparable_to_donor_base: true   # ADR-W4c-1:与 donor base 指标/split 不同,不可同表
      remote_env: {host: "zkyd@10.102.106.53", conda_env: "virtualcell (torch 2.6)"}
      distributable: false
```

在文件**末尾**(yeast_deletion_fitness 之后)新增 `scgpt` 条目:

```yaml

  scgpt:
    name: scgpt
    type: public_model
    species: [human]
    module: genetic_hub
    task: predict_delta_expression
    source: "remote:scgpt_ckpt"           # 远端 196MB ckpt,requires_manual_fetch
    license: MIT
    status: planned                        # 缺 torch/ckpt → 仍 planned,broker fail-closed
    wrapper: praxis_virtualcell.model_zoo.wrappers.scgpt_wrapper.ScgptWrapper
    version: norman_2019-pretrained_backbone
    requires: [torch, gpu]
    reliability_policy: ml_disagreement
    assets:
      - filename: pretrained_backbone.pt   # ≈196MB scGPT backbone + head
        sha256: null                        # 占位:真 sha 待 .53 上算过填
        source_note: "fetch from /home/zkyd/data1/mzy/scgpt_ckpt/norman_2019/ (host .53, env vc-scgpt)"
      - filename: pretrained_backbone.json # 重建 kwargs(backbone_name=scgpt)
        sha256: null
        source_note: "same dir; class_name + kwargs for build_predictor_from_ckpt"
    provenance:
      training_data: donor norman_2019 (frozen scGPT + light head)
      architecture: frozen backbone 53.8M + head 2.47M (saturated)
      metrics: {delta_pearson: 0.4407, cosine: 0.9808, n: 7290}
      not_comparable_to_donor_base: false  # per-cell ΔPearson 同表 A 口径可比
      frozen_backbone_underperforms: true  # 诚实:低于 base,SOTA 需 fine-tune(backlog)
      remote_env: {host: "zkyd@10.102.106.53", conda_env: "vc-scgpt (torch 2.3)", ckpt: "scgpt_ckpt/norman_2019/pretrained_backbone.{pt,json}"}
      distributable: false
```

- [ ] **Step 4: 扩 `_validate`(加 assets schema 分支)**

在 `praxis_virtualcell/model_zoo/registry.py` 的 `_validate` 方法**末尾**(self_trained training_card 校验**之后**)追加:

```python
        # assets 声明(可选;有则每条须含 filename + sha256 键 —— sha256 可 null 占位,但键必须在,
        # 保证 ckpt 挪出硬编码后可被版本锁/取数流程指认。结构坏 → ValueError,fail-closed)
        assets = entry.get("assets")
        if assets is not None:
            if not isinstance(assets, list):
                raise ValueError(f"{name} assets 必须是 list")
            for a in assets:
                if not isinstance(a, dict) or "filename" not in a or "sha256" not in a:
                    raise ValueError(f"{name} assets 条目须含 filename + sha256 键: {a}")
```

- [ ] **Step 5: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_registry_public_models.py -q`
Expected: 5 passed。

- [ ] **Step 6: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 578 passed / 25 skipped / 0 failed(573 + 5 新;不新增 skip)。注意核对现有 `test_model_zoo_registry.py` 仍全绿(assets 分支是可选的 net-new,不破坏 3 种子条目)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/model_zoo/registry.yaml praxis_virtualcell/model_zoo/registry.py praxis_virtualcell/tests/test_registry_public_models.py
git commit -m "feat(phase6): registry 补 scgpt 条目 + gears/scgpt 声明 assets(ckpt 挪出硬编码,sha256 占位)/provenance(真锚点)+ _validate assets schema fail-closed

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 6.4:broker 对公开模型的 assets sha256 版本锁关(缺 ckpt/sha 不匹配 → fail-closed 不静默 accept)

**决策说明:** `ModelBrokerAgent._resolve` **追加** assets 版本锁关(在现有 source 关之后、"全过 available" 之前):有 `assets` 的条目,每条经 `ModelCache.check(model_name, filename, sha256=sha256)`;任一缺文件/ sha 不匹配 → `available=False reason="asset unavailable: ..."`;`sha256: null`(占位未填)→ 判 `requires_manual_fetch`(不静默 available)。**不改**现有 status/requires/source 三关(gears/scgpt 因 requires 缺 torch 已在第③关 fail-closed,本关是"即便有 torch 也须 ckpt 到位且 sha 对"的**第二道锁**,证明 fail-closed 纵深)。broker 加可选 `cache` 注入(默认 `ModelCache()`),测试用 tmp_path。

**Files:**
- Modify: `praxis_virtualcell/agents/model_broker_agent.py`（`__init__` 加 cache 注入;`_resolve` 追加 assets 关）
- Test: `praxis_virtualcell/tests/test_broker_public_models.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_broker_public_models.py`:

```python
"""Phase 6:broker 对公开模型(gears/scgpt)fail-closed 纵深。
铁律(红线 6):planned/缺 torch/缺 ckpt/sha 占位 → available=False + reason 点名缺什么,绝不静默 accept。
本地无 torch → gears/scgpt 在 requires 关就 fail-closed(reason 点名 torch/gpu)。
assets 关:即便依赖齐,ckpt 缺失/sha 占位/sha 不匹配 → 仍 available=False(第二道锁)。"""
import hashlib
import importlib.util

from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.model_zoo.cache import ModelCache

_HAS_TORCH = importlib.util.find_spec("torch") is not None


def _ask(name):
    return AgentMessage("q1", "Client", "ModelBrokerAgent", "model_request",
                        {"model_name": name}, "t1")


def _resolve(name, cache=None):
    bus = MessageBus()
    ModelBrokerAgent(cache=cache).handle(_ask(name), bus)
    return bus.latest("model_broker_result").payload


def test_gears_fail_closed_missing_torch_locally():
    """本地无 torch → gears requires[torch,gpu] 关 fail-closed,reason 点名依赖。不静默 accept。"""
    if _HAS_TORCH:
        import pytest
        pytest.skip("本地有 torch 时此断言不成立;缺 torch 断言见此路径")
    p = _resolve("gears")
    assert p["available"] is False
    assert p["status"] == "planned"
    assert "torch" in p["reason"] or "gpu" in p["reason"] or "planned" in p["reason"]


def test_scgpt_fail_closed_locally():
    p = _resolve("scgpt")
    assert p["available"] is False               # planned + 缺 torch/ckpt → 不静默 available
    assert p["reason"]


def test_wrapper_class_path_still_visible_when_unavailable():
    """fail-closed 不等于隐藏:registry 里 wrapper 类路径仍可见(可分发性声明),只是不可用。"""
    p = _resolve("scgpt")
    assert p["wrapper"].endswith("scgpt_wrapper.ScgptWrapper")
    assert p["available"] is False


def test_assets_sha_placeholder_gates_requires_manual_fetch(tmp_path, monkeypatch):
    """assets sha256=null(占位未填)→ 即便依赖齐也判 requires_manual_fetch(不静默 available)。
    模拟依赖齐(_dep_available 全 True),隔离出 assets 关的行为。"""
    import praxis_virtualcell.agents.model_broker_agent as mba
    monkeypatch.setattr(mba, "_dep_available", lambda dep: True)  # 假装 torch/gpu 都在
    cache = ModelCache(root=str(tmp_path))
    p = _resolve("scgpt", cache=cache)           # scgpt assets sha256=null + ckpt 不在 tmp
    assert p["available"] is False
    assert "asset" in p["reason"] or "manual_fetch" in p["reason"] or "sha256" in p["reason"]


def test_assets_present_and_sha_match_passes_asset_gate(tmp_path, monkeypatch):
    """assets 齐 + sha 对 → assets 关放行(证明关不是恒 False 空转)。用临时 registry + 真文件 sha。"""
    import praxis_virtualcell.agents.model_broker_agent as mba
    from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
    monkeypatch.setattr(mba, "_dep_available", lambda dep: True)

    payload = b"fake-weights"
    sha = hashlib.sha256(payload).hexdigest()
    reg_yaml = tmp_path / "reg.yaml"
    reg_yaml.write_text(
        "models:\n"
        "  tm:\n"
        "    name: tm\n"
        "    type: public_model\n"
        "    species: [human]\n"
        "    module: genetic_hub\n"
        "    task: t\n"
        "    source: cobra_bundled_textbook\n"   # source 关放行(resolved)
        "    license: MIT\n"
        "    status: available\n"                 # available 才走到 assets 关
        "    wrapper: x.Y\n"
        "    version: v1\n"
        "    requires: []\n"
        "    reliability_policy: p\n"
        "    assets:\n"
        "      - filename: w.pt\n"
        f"        sha256: '{sha}'\n"
        "        source_note: local\n",
        encoding="utf-8")
    cache = ModelCache(root=str(tmp_path))
    ap = cache.asset_path("tm", "w.pt")
    ap.parent.mkdir(parents=True, exist_ok=True)
    ap.write_bytes(payload)                       # 落真文件,sha 对

    bus = MessageBus()
    mba.ModelBrokerAgent(registry=ModelZooRegistry(registry_path=str(reg_yaml)),
                         cache=cache).handle(_ask("tm"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is True                 # 依赖齐 + source resolved + assets sha 对 → available


def test_assets_sha_mismatch_fail_closed(tmp_path, monkeypatch):
    """assets sha 不匹配(篡改/版本错)→ available=False(fail-closed,红线 6)。"""
    import praxis_virtualcell.agents.model_broker_agent as mba
    from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
    monkeypatch.setattr(mba, "_dep_available", lambda dep: True)

    wrong_sha = hashlib.sha256(b"expected").hexdigest()
    reg_yaml = tmp_path / "reg.yaml"
    reg_yaml.write_text(
        "models:\n"
        "  tm:\n"
        "    name: tm\n    type: public_model\n    species: [human]\n"
        "    module: genetic_hub\n    task: t\n    source: cobra_bundled_textbook\n"
        "    license: MIT\n    status: available\n    wrapper: x.Y\n    version: v1\n"
        "    requires: []\n    reliability_policy: p\n"
        "    assets:\n"
        "      - filename: w.pt\n"
        f"        sha256: '{wrong_sha}'\n"
        "        source_note: local\n",
        encoding="utf-8")
    cache = ModelCache(root=str(tmp_path))
    ap = cache.asset_path("tm", "w.pt")
    ap.parent.mkdir(parents=True, exist_ok=True)
    ap.write_bytes(b"actual-different-bytes")     # sha 不匹配

    bus = MessageBus()
    mba.ModelBrokerAgent(registry=ModelZooRegistry(registry_path=str(reg_yaml)),
                         cache=cache).handle(_ask("tm"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False
    assert "sha256" in p["reason"] or "asset" in p["reason"]
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_broker_public_models.py -q`
Expected: FAIL(`ModelBrokerAgent.__init__` 无 `cache` 参数 → TypeError;assets 关未实现 → sha 对的 available 用例失败)。

- [ ] **Step 3: 扩 `model_broker_agent.py`**

在 `praxis_virtualcell/agents/model_broker_agent.py` 顶部 import 区**追加**:

```python
from praxis_virtualcell.model_zoo.cache import ModelCache
```

把 `__init__` 改为(加 cache 注入,不改 registry 注入):

找到:

```python
    def __init__(self, registry: ModelZooRegistry | None = None) -> None:
        self._reg = registry or ModelZooRegistry()
```

替换为:

```python
    def __init__(self, registry: ModelZooRegistry | None = None,
                 cache: ModelCache | None = None) -> None:
        self._reg = registry or ModelZooRegistry()
        self._cache = cache or ModelCache()
```

在 `_resolve` 方法里,找到现有 source 关之后、"全部通过 → available" 之前的这段:

```python
        # 4) source 解析(远端 gated → requires_manual_fetch → 不可用)
        src = resolve_source(entry)
        if not src["available"]:
            base["reason"] = f"source not resolvable: {src['reason']}"
            return base

        # 全部通过 → available
        base["available"] = True
        base["reason"] = "ok"
        return base
```

替换为(在 source 关与 available 之间插 assets 关):

```python
        # 4) source 解析(远端 gated → requires_manual_fetch → 不可用)
        src = resolve_source(entry)
        if not src["available"]:
            base["reason"] = f"source not resolvable: {src['reason']}"
            return base

        # 5) assets 版本锁关(有 assets 时每条须落地 + sha 对;sha=null 占位 → requires_manual_fetch)。
        #    这是 fail-closed 第二道锁:即便依赖/source 齐,ckpt 未取到/sha 不匹配 → 不静默 accept(红线 6)。
        for a in entry.get("assets", []) or []:
            declared_sha = a.get("sha256")
            if declared_sha is None:
                base["reason"] = (f"asset requires_manual_fetch: {a.get('filename')} sha256 未登记"
                                  f"(占位)—— 需按 source_note 手动获取并登记 sha 后方可用")
                return base
            st = self._cache.check(model_name, a["filename"], sha256=declared_sha)
            if not st.available:
                base["reason"] = f"asset unavailable: {st.reason}"
                return base

        # 全部通过 → available
        base["available"] = True
        base["reason"] = "ok"
        return base
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_broker_public_models.py -q`
Expected: 6 passed(本地无 torch → `test_gears_fail_closed_missing_torch_locally` 走缺 torch 断言路径)。

- [ ] **Step 5: 红线核验 —— Phase 2 broker 回归仍绿**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_model_broker_agent.py -q`
Expected: 5 passed(现有 broker 测试不受 assets 关影响——ecoli_gem 无 assets,for 循环空转不改行为;gears 在 requires 关已 return,到不了 assets 关)。若红,说明改动破坏了现有三关 → 真 bug,停下报告(红线 5),不改测试迁就。

- [ ] **Step 6: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 584 passed / 25 skipped / 0 failed(578 + 6 新;不新增 skip)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/agents/model_broker_agent.py praxis_virtualcell/tests/test_broker_public_models.py
git commit -m "feat(phase6): broker assets sha256 版本锁第二道关(缺 ckpt/sha 占位/sha 不匹配→fail-closed 不静默,依赖齐+sha 对才放行;wrapper 类路径 unavailable 时仍可见)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 6.5:真 GEARS/scGPT 推理 gated 契约测试(.53 跑通,本地 remote skip,诚实标注)

**决策说明:** 建 `@pytest.mark.remote` 的**真推理契约测试**(逐样复刻 `test_ml_agent_bus.py` 的 remote gated 惯例):在 .53 上(有 torch + ckpt)`ScgptWrapper(ckpt_stem).run_prediction` 真跑并断言 `predict_tensor == donor predict`(atol 1e-6,finding_w4c_scgpt 锚点);GEARS 同理真跑 `predict([['gene']])` 并断言产出结构。**本地 Mac 无 torch → conftest 自动 skip**(诚实:skip 基线 25→27)。这是"真推理跑通是 .53 的事"的落地——**本地绝不跑真模型,绝不 mock 真语义凑绿**。ckpt 路径从 env 取(`SCGPT_CKPT_STEM`/`GEARS_CKPT`,.53 上给),不硬编码。

**Files:**
- Create: `praxis_virtualcell/tests/test_public_models_remote.py`

- [ ] **Step 1: 写 gated 测试(本地即 skip)**

写 `praxis_virtualcell/tests/test_public_models_remote.py`:

```python
"""Phase 6:GEARS/scGPT 真推理 gated 契约测试(仅 .53:torch + GPU + ckpt;Mac 无 torch → conftest 自动 skip)。

诚实:这 2 条是 @pytest.mark.remote,本地 skip(skip 基线 25→27,与 Phase 2 torch/cobra gated 同款惯例)。
真推理跑通是 .53 的事 —— 本地绝不跑真模型、绝不 mock 真语义凑绿(红线 5/6)。
ckpt 路径从 env 取(.53 上给),不硬编码 /home/zkyd。"""
import os

import pytest

pytestmark = pytest.mark.remote


def test_scgpt_wrapper_real_inference_matches_donor():
    """.53:ScgptWrapper 真跑 == donor predict(atol 1e-6,finding_w4c_scgpt 集成锚点)。
    ΔPearson 0.4407 是 eval 全集指标(此处只验单点等价性,分数入 provenance 已声明)。"""
    from praxis_virtualcell.model_zoo.wrappers.scgpt_wrapper import ScgptWrapper

    ckpt_stem = os.environ["SCGPT_CKPT_STEM"]        # .53:.../scgpt_ckpt/norman_2019/pretrained_backbone
    w = ScgptWrapper(ckpt_stem=ckpt_stem)
    out = w.run_prediction({"targets": ["AHR"]})
    assert "prediction" in out and "delta" in out["prediction"]
    assert out["prediction"]["n_genes"] > 0
    # 等价性锚点:与 donor predict 逐元素(atol 1e-6)——.53 上按 finding 的 pipeline 断言。
    # (donor 对照值由 .53 上的 build_predictor_from_ckpt + donor predict 现算,不硬编码。)


def test_gears_wrapper_real_inference_structure():
    """.53:GearsWrapper 真跑 GEARS predict([['gene']]) → 产出结构(condition-level delta)。
    pearson_de 0.8392 入 provenance 已声明;此处验产出契约(不与 donor 同表——GEARS 不可比)。"""
    from praxis_virtualcell.model_zoo.wrappers.gears_wrapper import GearsWrapper

    ckpt_stem = os.environ["GEARS_CKPT"]             # .53:GEARS 原生 save 目录/stem
    w = GearsWrapper(ckpt_stem=ckpt_stem)
    out = w.run_prediction({"targets": ["AHR"]})
    assert "prediction" in out
```

> **诚实说明**:此文件 2 条测试**在本地必 skip**(`pytestmark = pytest.mark.remote` + conftest 无 torch 自动 skip)。它们**不写占位断言凑绿**——真推理断言(等价性 atol 1e-6 / 产出结构)是 .53 上执行者按 finding pipeline 填实并验证的**真契约**;本地无法验证故 skip,这是设计使然(与 `test_ml_agent_bus.py` 等 10 个现有 remote 文件同款)。**执行者若在 .53 跑,须补全 donor 对照值/GEARS load API 并让 2 条真绿;本地只验证它们被正确 skip。**

- [ ] **Step 2: 跑确认本地 skip(不是 fail)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_public_models_remote.py -q`
Expected: 2 skipped(conftest:无 torch → remote 自动 skip)。**关键:是 skipped 不是 failed/errors。**

- [ ] **Step 3: 确认 skip 基线升到 27(诚实核验)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q --junit-xml=/tmp/junit_phase6_t65.xml`
然后取精确数:
Run: `python3 -c "import xml.etree.ElementTree as ET; r=ET.parse('/tmp/junit_phase6_t65.xml').getroot(); s=r if r.tag=='testsuite' else r[0]; print('tests=%s failures=%s errors=%s skipped=%s'%(s.get('tests'),s.get('failures'),s.get('errors'),s.get('skipped')))"`
Expected: `tests=586 failures=0 errors=0 skipped=27`(584 passed 前值 collected 609?——核算:上一 task 末 collected = 584 passed + 25 skipped = 609;本 task +2 collected 全进 skipped → tests=611? )。

> **⚠ 计数自查(执行者务必用 junit 实数,不照抄）**:上一 task(6.4)末:passed=584, skipped=25 → collected=609。本 task 新增 2 条 remote 测试,本地全 skip → passed 仍 584,skipped 25→27,collected 609→611。故本 task 后 junit 应为 `tests=611 failures=0 errors=0 skipped=27`,passed=611−27=584(passed 不增,skip +2)。**验收认 failures=0 errors=0 skipped=27,passed=584 不变。** 上面 Step 3 的 "tests=586" 是起草估算,**以实跑 junit 为准**;若不符,按实数记录,别凑。

- [ ] **Step 4: 提交**

```bash
find . -name '._*' -delete
git add praxis_virtualcell/tests/test_public_models_remote.py
git commit -m "test(phase6): GEARS/scGPT 真推理 gated 契约测试(@pytest.mark.remote,.53 跑通本地 skip;skip 基线诚实 25→27,不 mock 真语义凑绿)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 6.6:provenance/可分发性交叉校验 + Phase 6 完成闸门

**决策说明:** 落一层**跨源一致性校验**(纯测试,不改源码):registry.yaml 的 `provenance`/`scope` 声明与 wrapper 的 `declare_provenance()`/`declare_scope()` 必须一致(module/锚点数字对齐),防"registry 说一套、wrapper 说另一套";可分发性声明齐全(每个公开模型有 assets + source_note + distributable 标注)。最后跑全量回归 + 红线核验(fail-closed 纵深 + LLM 边界 + golden/negative KPI)+ 台账**不动**(控制器更新)。**不打 tag**(Phase 6 非里程碑)。

**Files:**
- Test: `praxis_virtualcell/tests/test_phase6_provenance_gate.py`

- [ ] **Step 1: 写校验测试**

写 `praxis_virtualcell/tests/test_phase6_provenance_gate.py`:

```python
"""Phase 6 完成闸门:registry 声明 ↔ wrapper 声明 跨源一致 + 可分发性齐全 + fail-closed 纵深。
铁律:registry.provenance/scope 与 wrapper.declare_* 一致(防双真相源);每个公开模型
assets+source_note+provenance 齐(ckpt 挪出硬编码可指认);缺依赖/缺 ckpt → broker fail-closed。"""
import importlib

import pytest

from praxis_virtualcell.model_zoo.registry import ModelZooRegistry


def _wrapper_instance(class_path: str):
    mod, cls = class_path.rsplit(".", 1)
    return getattr(importlib.import_module(mod), cls)()


@pytest.fixture(scope="module")
def reg():
    return ModelZooRegistry()


@pytest.mark.parametrize("name", ["gears", "scgpt"])
def test_registry_module_matches_wrapper_scope(reg, name):
    """registry.module == wrapper.declare_scope()['module'](防双真相源)。"""
    e = reg.get(name)
    w = _wrapper_instance(e["wrapper"])
    assert w.declare_scope()["module"] == e["module"]
    assert set(e["species"]) <= set(w.declare_scope()["species"]) or \
           set(w.declare_scope()["species"]) <= set(e["species"])


@pytest.mark.parametrize("name", ["gears", "scgpt"])
def test_registry_anchor_matches_wrapper_provenance(reg, name):
    """registry.provenance 锚点 == wrapper.declare_provenance() 锚点(数字一致)。"""
    e = reg.get(name)
    w = _wrapper_instance(e["wrapper"])
    wp = w.declare_provenance()
    if name == "gears":
        assert wp["metrics"]["pearson_de"] == pytest.approx(
            e["provenance"]["metrics"]["pearson_de"], abs=1e-4)
        assert wp["not_comparable_to_donor_base"] is True
    else:
        assert wp["metrics"]["delta_pearson"] == pytest.approx(
            e["provenance"]["metrics"]["delta_pearson"], abs=1e-4)
        assert wp["not_comparable_to_donor_base"] is False


@pytest.mark.parametrize("name", ["gears", "scgpt"])
def test_distributability_declared(reg, name):
    """可分发性齐全:assets(含 source_note)+ provenance.distributable 标注,ckpt 可指认。"""
    e = reg.get(name)
    assert e["assets"] and all("source_note" in a for a in e["assets"])
    assert e["provenance"]["distributable"] is False   # 需 torch+GPU+ckpt,缺则 fail-closed


def test_public_models_wrapper_importable(reg):
    """wrapper 类路径可 import(可分发性:装了 wheel 的人能拿到类,即便模型 unavailable)。"""
    for name in ("gears", "scgpt"):
        w = _wrapper_instance(reg.get(name)["wrapper"])
        assert w.declare_scope()["module"] == "genetic_hub"


def test_broker_fail_closed_depth_for_public_models():
    """红线 6 纵深:本地 broker 对 gears/scgpt 全 available=False(缺 torch/ckpt),reason 非空。"""
    from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
    from praxis_virtualcell.core.bus import MessageBus
    from praxis_virtualcell.core.message import AgentMessage

    for name in ("gears", "scgpt"):
        bus = MessageBus()
        ModelBrokerAgent().handle(AgentMessage(
            "q", "C", "ModelBrokerAgent", "model_request", {"model_name": name}, "t"), bus)
        p = bus.latest("model_broker_result").payload
        assert p["available"] is False and p["reason"]
        assert p["wrapper"]                              # 不隐藏:类路径仍可见
```

- [ ] **Step 2: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_phase6_provenance_gate.py -q`
Expected: 8 passed(2 参数 × 3 参数化 test = 6 + 2 单测;本地无 torch 不影响这批——只查声明/契约/broker fail-closed,不真推理)。

> 计数说明:`test_registry_module_matches_wrapper_scope`(×2)+ `test_registry_anchor_matches_wrapper_provenance`(×2)+ `test_distributability_declared`(×2)+ `test_public_models_wrapper_importable`(×1)+ `test_broker_fail_closed_depth_for_public_models`(×1)= 8 条。

- [ ] **Step 3: 红线核验(fail-closed 纵深 + LLM 边界 + golden/negative KPI)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_gears_wrapper.py praxis_virtualcell/tests/test_scgpt_wrapper.py praxis_virtualcell/tests/test_broker_public_models.py praxis_virtualcell/tests/test_model_broker_agent.py praxis_virtualcell/tests/test_llm_boundary_flags.py praxis_virtualcell/tests/test_golden_cases.py praxis_virtualcell/tests/test_negative_cases.py -q`
Expected: 全绿(Phase 6 未碰管线/治理/LLM 边界:assert_llm_boundaries 三 flag 恒 False、golden unsafe-accept=0、negative 无静默 accept;公开模型缺依赖/缺 ckpt fail-closed 纵深齐)。若某文件名不存在(如 golden/negative/llm_boundary 的确切文件名),先 `ls praxis_virtualcell/tests/ | grep -E "golden|negative|boundary"` 核实真名再跑,不臆造。

- [ ] **Step 4: 全量回归(精确数)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q --junit-xml=/tmp/junit_phase6_final.xml`
然后取精确数:
Run: `python3 -c "import xml.etree.ElementTree as ET; r=ET.parse('/tmp/junit_phase6_final.xml').getroot(); s=r if r.tag=='testsuite' else r[0]; print('tests=%s failures=%s errors=%s skipped=%s'%(s.get('tests'),s.get('failures'),s.get('errors'),s.get('skipped')))"`
Expected: `tests=619 failures=0 errors=0 skipped=27`(6.5 末 collected 611 + 本 task 8 新 = 619;passed = 619 − 27 = **592**)。**关键:failures=0 errors=0 skipped=27**(27 = 25 旧 + 2 Task 6.5 remote)。若不符,以实数为准,别凑。

- [ ] **Step 5: 核对新增数据进 wheel(registry.yaml 声明可分发)**

Run: `grep -n "recursive-include praxis_virtualcell" MANIFEST.in`
Expected: 有 `recursive-include praxis_virtualcell *.yaml *.json`(已实测存在 → registry.yaml 的 scgpt/assets 声明自动纳入 wheel,装 wheel 的人能在 registry 里看到 gears/scgpt + provenance)。若无 `*.yaml` 通配则追加。

- [ ] **Step 6: 提交(不 tag、不 push、不碰台账)**

```bash
find . -name '._*' -delete
git add praxis_virtualcell/tests/test_phase6_provenance_gate.py
git commit -m "test(phase6): provenance/可分发性跨源一致闸门(registry↔wrapper 锚点/module 对齐防双真相源 + fail-closed 纵深)+ Phase 6 完成(592 passed/27 skipped,不打 tag)

Phase 6 收编 GEARS/scGPT 进 ModelBroker:wrapper(缺 torch/ckpt fail-closed 不伪造)+ registry
声明 assets(ckpt 挪出硬编码/sha256 占位)/provenance(真锚点 pearson_de 0.8392 不可比 / ΔPearson
0.4407 可比诚实低)+ broker assets 版本锁第二道关 + 真推理 .53 gated 本地 skip。红线 6 fail-closed
纵深守住,管线/治理/LLM 边界零改动。Phase 6 非里程碑,不打 tag,v1.3 等 Phase 7+8。

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

**Phase 6 验收:**
- ✅ GearsWrapper / ScgptWrapper(扩 ModelWrapper,与 GemWrapper 同构):declare_scope + declare_provenance(真锚点)+ estimate_uncertainty(诚实点估计)+ 缺 torch → run_prediction fail-closed(不静默返回 mock/假 delta 冒充可用)。
- ✅ registry.yaml:新增 scgpt 条目 + gears/scgpt 声明 assets(ckpt 挪出硬编码 → filename + sha256 占位 + source_note 取数流程)+ provenance(锚点 + 诚实标注);`_validate` assets schema fail-closed。
- ✅ broker assets sha256 版本锁**第二道关**:缺 ckpt / sha 占位 / sha 不匹配 → available=False 不静默;依赖齐 + source resolved + sha 对才放行(关非空转)。wrapper 类路径 unavailable 时仍可见(可分发性)。
- ✅ 真 GEARS/scGPT 推理 gated 契约测试(.53 跑通,本地 remote skip,**诚实标注 skip 基线 25→27**,不 mock 真语义凑绿)。
- ✅ provenance/可分发性跨源一致闸门(registry ↔ wrapper 锚点/module 对齐,防双真相源)+ fail-closed 纵深。
- ✅ 556 基线零回归(纯新增 + 受控最小扩现有 registry/broker,未碰管线/治理/LLM 边界/predictors)→ **592 passed / 27 skipped / 0 failed**;不打 tag(v1.3 等 Phase 7+8)。

---

## Self-Review(写完对照骨架 + 真实代码)

- **骨架覆盖**:骨架建议的 6 块全部展开——①GEARS wrapper(Task 6.1,含 base declare_provenance + 缺 torch fail-closed)②scGPT wrapper(Task 6.2,复用 MLPredictorAgent/donor_bridge + 缺 torch fail-closed)③registry.yaml 加 GEARS/scGPT 条目(Task 6.3,assets/source/scope/provenance,optional extra requires[torch,gpu])④broker 对新公开模型的解析(Task 6.4,available→wrapper、缺 torch/ckpt→fail-closed 不静默,assets 第二道锁)⑤真推理 gated 契约测试(Task 6.5,.53 跑通本地 skip 诚实标注)⑥provenance/可分发性校验 + 完成闸门(Task 6.6)。6 个 task(骨架说"参考前几 Phase 7–8 个",取 6 个每个足够小)。

- **写作中发现并修正的旧描述偏差(真实代码校正清单已在头部展开)**:①gears 条目 Phase 2 已存在(不新建,改扩 assets)、scgpt 不存在(新建);②gears_wrapper.py 文件不存在(net-new);③ModelWrapper 无 declare_provenance(net-new 加);④GEARS 接口与 donor 不同构(真推理不复用 MLPredictorAgent,走原生 predict);⑤scGPT 接口已同构 donor(复用 build_predictor_from_ckpt);⑥本地无 torch → 天然 fail-closed(不需 monkeypatch 造缺 torch,与 Phase 2 造缺 cobra 不同);⑦模型级 provenance ≠ 运行时 PredictorResultMessage.provenance。

- **诚实的计数与 skip 声明**:起点基线实跑核实 = **556 passed / 25 skipped / collected 581**(junit `tests=581 skipped=25`,与台账/commit "556 passed" 一致——556 = 581 − 25)。Task 6.5 的 2 条 remote 测试本地 skip → **skip 基线诚实升到 27**(不像前几 Phase 保 25,已在铁律 + Task 6.5 明确标注为设计使然、非隐藏失败)。各 task 期望 passed:6.1 +8→564 / 6.2 +9→573 / 6.3 +5→578 / 6.4 +6→584 / 6.5 +0(+2 skip)→584 / 6.6 +8→**592**。验收统一认 **failures=0 errors=0 + 新增条数正确 + skipped=27**(用 junit 实数,不照抄估算)。

- **无占位符**:每个 GREEN 步骤给可运行最小真实代码。**例外的"诚实抛异常"不是占位符**:GearsWrapper/ScgptWrapper 的 `run_prediction` 本地必抛(缺 torch/ckpt),这是**红线 6 要求的 fail-closed**——本地任何"能跑的实现"都只能伪造 delta 冒充可用,那正是禁止的。真推理体的填实 + 验证在 Task 6.5 的 .53 gated 测试里(执行者远端补全 donor 对照/GEARS load API)。已在两处"诚实说明"明确这不是偷懒。

- **类型一致性**:`declare_scope()->dict{species,module,task,perturbation}`、`declare_provenance()->dict{model,metrics,...}`、`estimate_uncertainty(model_input,prediction)->dict{available,method,...}` 在 base/GearsWrapper/ScgptWrapper/测试四处签名统一;registry `assets` 条目 schema(filename+sha256+source_note)在 registry.yaml/`_validate`/broker assets 关/测试四处一致;broker `_resolve` 返回 `{model_name,available,status,wrapper,reason}` 不变(assets 关只加 return 分支,不改结构);`ModelBrokerAgent.__init__(registry, cache)` 新增 cache 注入在 broker/测试两处一致。

- **红线逐条守**:红线 6(缺依赖/无 provenance/sha 不匹配 fail-closed)每个 wrapper task 有专门缺 torch 测试、每个 broker task 有 fail-closed 纵深断言;红线 1(OFFLINE 零 LLM)wrapper 有 no-LLM-import 测试、不碰 config;红线 3(只在 praxis_virtualcell/tests);红线 5(不迁就,真 bug BLOCKED,红线核验 Step 若破停下报告);增量复用(ScgptWrapper 复用 build_predictor_from_ckpt/MLPredictorAgent,GearsWrapper 复用现有 handle fail-closed,不重写 ML 内核)。

- **v1.3 待确认项**:scope 边界(保守 human/norman)、estimate_uncertainty 口径(点估计不假造)、真锚点写 provenance(写 + 诚实标注不可比/frozen 低/backlog)、requires_manual_fetch 取数流程(source_note 声明 + sha256 null 占位 gate)——4 项已落最小确定性集保证可测 + fail-closed,标头部待确认,不阻塞执行。

---

## 下一步(Phase 7 展开时机)

Phase 6 全 task 绿(592 passed / 27 skipped)后,Phase 6 与 Phase 7(自训模型第一批,净新增训练)并行——Phase 7 复用本 Phase 落地的 `assets`/`provenance` registry schema + broker assets 版本锁 + SelfTrainedWrapper(registry.yaml 已声明 yeast_deletion_fitness self_trained 种子)。Phase 8(网站 + Linux release)时再把公开/自训模型接进 runtime 管线(本 Phase 与 Phase 2 GemWrapper 同,只交付库 + broker,未接管线),到 Phase 8 全完成才打 **v1.3.0** tag。
