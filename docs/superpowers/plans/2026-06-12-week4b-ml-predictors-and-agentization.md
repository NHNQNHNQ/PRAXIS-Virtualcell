# Week 4b — donor predictor 全迁移 + Coordinator 复现 + predictor agent 化 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans(远端执行,inline 最稳)。Steps 用 checkbox。延续 Week 4a 的 donor_bridge 模式与远端 `virtualcell` 环境(torch 2.6.0+cu124,GPU)。

**Goal:** M1 迁 donor latent/gnn/decoder/cpa/scGPT 5 个 predictor + 集成 donor Coordinator 复现 Norman ~0.70;M2 把真 predictor 接入 Week 2 communicative 骨架(PredictorAgent + message bus + retrieve-before-predict + reliability/abstain + provenance);外部 GEARS audit-first 风险隔离。

**Spec:** [docs/superpowers/specs/2026-06-12-week4b-ml-predictors-and-agentization-design.md](../specs/2026-06-12-week4b-ml-predictors-and-agentization-design.md)

**Context(recon 实测):** 5 predictor 接口与 linear 完全相同 → donor_bridge 直接泛化。各 base anchor:latent 0.6922 / gnn 0.6918 / scGPT 0.6750 / decoder 0.6636 / cpa 0.5673。Coordinator ~0.70 = latent+gnn 组合。Coordinator API:`SubAgent(SubAgentSpec(name,bench_id,predictor_name), predictor)` + `Coordinator(subs)`。scGPT=donor `pretrained_backbone`(已有 ckpt)。GEARS 无 norman ckpt(vcell 有 `cell-gears` 包)。

**远端约定(同 Week 4a):** donor 根 `/home/zkyd/data1/mzy/Virtual cell`(含空格引号);远端仓 `/home/zkyd/data1/mzy/PRAXIS-virtualcell`;`source /home/zkyd/software/miniconda3/etc/profile.d/conda.sh && conda activate virtualcell`;Mac commit+push → 远端 git pull;ml 测试标 `remote`(Mac skip);commit 前清 `._*`;ckpt stem 用 `runs/full_bench_20260521_060815/checkpoints/norman_2019/<name>`;W4A_ANCHOR 锚定值见 finding。

---

## M1 — donor predictor 全迁移 + Coordinator 复现 0.70

### Task 1:donor_bridge 泛化 + 多 predictor 锚定

**Files:** 改 `predictors/ml/donor_bridge.py`(`_cls` 注册 5 类);新 `benchmarks/_anchor_donor_multi.py`;新 `tests/test_ml_multi_bridge.py`

- [ ] **Step 1: 写远端测试** `test_ml_multi_bridge.py`(标 `remote`):参数化 5 predictor(stem 由 env `W4B_CKPT_DIR` 给),各 `build_predictor_from_ckpt` → 校验 `cfg["class_name"]` 与 `model.pert_dim/n_genes`。
- [ ] **Step 2: 泛化 `_cls`**:在 `donor_bridge._cls` 注册 `LatentAdditivePredictor / GNNPertPredictor / DecoderOnlyPredictor / CPAStylePredictor / PretrainedBackbonePredictor`(各 `from predictors.<mod> import ...`)。`build_predictor_from_ckpt`/`load_norman` 已通用,不改。
- [ ] **Step 3: 锚定脚本** `_anchor_donor_multi.py`:对 5 predictor(+linear 共 6)循环 `build_predictor_from_ckpt` + `EvalAgent.evaluate(model, load_norman())`,打印各 `S0_recorded`(json meta) vs `S_eval`,对照。
- [ ] **Step 4: commit+push;远端跑**(`export W4B_CKPT_DIR=.../norman_2019`;锚定脚本 + pytest)。**Gate**:5 predictor 各自 `S_eval` 复现各 anchor(<1e-3;deterministic 应逐位,非 deterministic 容差);测试 pass。数字写 `docs/findings/finding_w4b_multi_anchor.md`(committed)。

### Task 2:通用 MLPredictorAgent + 多 predictor 等价性

**Files:** 泛化 `predictors/ml/linear_additive_agent.py` → 新 `predictors/ml/ml_predictor_agent.py`(通用 `MLPredictorAgent`,linear agent 保留为薄 alias);`tests/test_ml_multi_agent.py`

- [ ] **Step 1: 写测试**:对 5 predictor,`MLPredictorAgent(model).predict_tensor(control, pert_emb, kind, targets)` == `model.predict(ctx, pert).mean` 逐元素(atol 1e-6)。复用 Week 4a 的 non-control 样本选择逻辑(`item.kind in model.perturbation_kinds`)。
- [ ] **Step 2: 实现** `MLPredictorAgent`:与 Week 4a `LinearAdditivePredictorAgent` 同结构(接口对所有 base 相同),`name` 由 `donor_model.name` 取。
- [ ] **Step 3: commit+push;远端测试**。**Gate**:5 predictor 等价性 pass。

### Task 3:Coordinator 集成 + 复现 ~0.70

**Files:** 新 `predictors/ml/coordinator_bridge.py`;新 `benchmarks/coordinator_eval.py`;`tests/test_ml_coordinator.py`

- [ ] **Step 1: 远端先锚定 donor Coordinator 真值**:SSH 用 donor 代码构建 `Coordinator([SubAgent(SubAgentSpec(...), model) for latent,gnn])` + `EvalAgent.evaluate(coord, load_norman())`,记 `S_coord_donor`(预期 ~0.70)。写 finding。
- [ ] **Step 2: 写测试** `test_ml_coordinator.py`(remote):`coordinator_eval.score_coordinator(ckpt_dir, predictors=["latent_additive","gnn_pert"])` 的 dp == `S_coord_donor`(<1e-3)。
- [ ] **Step 3: 实现** `coordinator_bridge.build_coordinator(ckpt_dir, predictor_names)`:对每个 name `build_predictor_from_ckpt` → `SubAgent(SubAgentSpec(name=f"{n}-norman_2019", bench_id="norman_2019", predictor_name=n), model)` → `Coordinator(subs, default_bench_id="norman_2019")`。`coordinator_eval.score_coordinator` 复用 EvalAgent。
- [ ] **Step 4: commit+push;远端测试**。**Gate**:praxis Coordinator(latent+gnn) dp == donor(<1e-3),~0.70。记 `docs/findings/finding_w4b_coordinator.md`。

---

## 外部模型(audit-first,风险隔离)

### Task 4:GEARS audit + 迁移 or 诚实降级

**Files:** `docs/findings/finding_w4b_gears_audit.md`;(若可行)`donor_bridge` 注册 GEARS + 锚定

- [ ] **Step 1: audit(远端,只读)**:① `vcell` 的 `cell-gears` 版本 + `gears_aux.yaml` 内容;② donor 有无 `predictors/gears*.py` 代码 + norman GEARS ckpt;③ GEARS 需要的 gene graph / go_essential 等辅助数据是否就位;④ 试 `conda run -n vcell python -c "import gears"` + 能否实例化。
- [ ] **Step 2: 决策**:
  - **可行**(donor 有 GEARS ckpt 或可快速加载现成):走 donor_bridge 迁移 + 锚定(新 test_ml_gears,remote),记分数。
  - **受阻**(无 ckpt / 需训练 / env 冲突 / 数据缺):**如实记录** `finding_w4b_gears_audit.md`(列具体阻塞点,呼应 [[p2b_external_models_blocked]]),降级为 Week 4c 携带项,**不阻塞 M1/M2**。
- [ ] **Step 3: commit finding**。**Gate**:audit 结论明确 + 路径决策落档(迁移成功 or 诚实降级二选一,均算通过)。

---

## M2 — predictor agent 化(接入 communicative 骨架)

### Task 5:真 MLBackedPredictorAgent 接入 core PredictorAgent

**Files:** 新 `predictors/ml/agent_adapter.py`(继承 `praxis_virtualcell.predictors.base.PredictorAgent`);`tests/test_ml_agent_bus.py`

- [ ] **Step 1: 写测试**(remote):构造 `MLBackedPredictorAgent`(持有 donor latent model + ckpt),放 MessageBus;① 无 `brain_retrieved` → `RetrieveBeforePredictError`;② 正常 → `assess_applicability` 过 + `run_prediction` 调真模型 → `PredictorResultMessage(status="success", prediction=...)`;③ unsupported species(如 bacteria)→ `status="rejected"`。
- [ ] **Step 2: 实现** `MLBackedPredictorAgent(base.PredictorAgent)`:
  - `__init__(donor_model, ckpt_stem)`:持有真模型 + 缓存一个 norman sample 作 control/pert_emb 源(或从 request.targets 查 esm2)。
  - `prepare_input(request, brain_context)`:schema→tensor 适配 —— 从 `donor_bridge.load_norman` 取 control + 对 `request.perturbation_targets` 查 esm2 pert_emb(复用 donor `load_pert_features`)。
  - `run_prediction(model_input)`:`mean = MLPredictorAgent(model).predict_tensor(control, pert_emb, kind, targets)` → 返回 `{"prediction": {"delta_mean": mean.tolist() 或摘要}, "uncertainty": {...}}`。
- [ ] **Step 3: commit+push;远端测试**。**Gate**:bus 上 success/rejected + retrieve-before-predict 门生效。

### Task 6:端到端 communicative workflow(真 predictor + reliability/abstain/provenance)

**Files:** 新 `workflows/predict_delta_expression_ml.py`(远端真模型版 build_runtime);`tests/test_ml_workflow_e2e.py`

- [ ] **Step 1: 写测试**(remote):norman-like request(species=human, targets=某真实 gene)→ 真 latent/gnn agent → `EnsembleCoordinatorAgent` → `ReliabilityAgent` → `ProvenanceAgent`。验:① trace 完整含 `predictor_result`;② retrieve-before-predict 合规;③ provenance 含真模型来源(ckpt);④ unsupported(bacteria 或未知 gene)→ abstain。
- [ ] **Step 2: 实现** `build_runtime_ml`:复制 `predict_delta_expression.build_runtime`,把 `MockLinear/MockCPA/MockGEARS` 替换为 `MLBackedPredictorAgent`(latent/gnn 真模型);其余 agent(ensemble/reliability/critic/provenance/report)复用。
- [ ] **Step 3: commit+push;远端测试**。**Gate**:端到端 trace + provenance + abstain 验收(对齐 GPT §6/§8)。

---

## Task 7:conftest/Mac 零回归 + push

- [ ] **Step 1: Mac 全套零回归**:`find praxis_virtualcell -name '._*' -delete && .venv/bin/python -m pytest praxis_virtualcell/tests -q`。预期 48 + offline 全 pass;新增 ml `remote` 测试 Mac skip;0 failed。
- [ ] **Step 2: 远端全 ml 套确认**:SSH `pytest praxis_virtualcell/tests/test_ml_*.py -q`(export ckpt env),全 pass。
- [ ] **Step 3: 更新 memory + ROADMAP;final push**。

---

## 验收(DoD)
1. **M1**:latent/gnn/decoder/cpa/scGPT 5 predictor 各自锚定复现(<1e-3)+ 等价性(atol 1e-6)。
2. **M1**:donor Coordinator(latent+gnn)~0.70 在 praxis 复现(<1e-3)。
3. **GEARS**:audit 结论明确(迁移成功 or 诚实降级,均可)。
4. **M2**:真 predictor 接入 communicative 骨架 —— bus 通讯 + retrieve-before-predict + success/rejected + reliability/abstain + provenance/trace 端到端。
5. Mac 零回归;远端全 ml pass。
6. 留 Week 4c:GEARS 训练(若降级)/mechanistic/tabular/cross-species(W5)/abstain 强化(W6)/ablation(W7)。
