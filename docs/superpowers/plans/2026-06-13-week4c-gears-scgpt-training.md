# Week 4c plan — GEARS / scGPT 专项训练 + 集成

> inline 远端执行。**双 Phase + 双 env**:GEARS 在 `virtualcell`(torch 2.6 + PyG + cell-gears);scGPT 在 `vc-scgpt`(torch 2.3 + torchtext 0.18 + scgpt)。

**Spec:** [docs/superpowers/specs/2026-06-13-week4c-gears-scgpt-training-design.md](../specs/2026-06-13-week4c-gears-scgpt-training-design.md)

**已并行启动(background)**:① 建 `vc-scgpt` env;② GEARS 原生 norman spike(5ep,验证 pipeline)。

**远端约定**:donor `/home/zkyd/data1/mzy/Virtual cell`(空格引号);仓 `/home/zkyd/data1/mzy/PRAXIS-virtualcell`;GEARS 数据 `/home/zkyd/data1/mzy/gears_data`;ml 测试标 `remote`(Mac skip);commit 前清 `._*`。

---

## Phase 1 — GEARS(virtualcell,原生 norman)

### Task 1:GEARS 原生 norman 训练 + eval
- [ ] spike(5ep)验证 pipeline(下载 + train + eval metrics 探索)。
- [ ] 正式脚本 `benchmarks/gears_norman.py`:`PertData.load('norman')` + `prepare_split(seed=1)` + `GEARS.train(epochs=20)` + `gears.inference.evaluate/compute_metrics` → 记 `pearson_delta` / `pearson_delta_de` 等。
- [ ] **Gate**:GEARS norman 训练跑通,记 metrics → `finding_w4c_gears.md`(标注原生 split 不与 donor base 直接可比)。

### Task 2:GEARS predictor-agent
- [ ] `predictors/ml/gears_agent.py`:包 `GEARS.predict([['gene']])` → delta 向量;暴露 `predict_tensor`/communicative agent 接口(对齐 Week 4b `MLBackedPredictorAgent` 风格)。
- [ ] **Gate**:GEARS agent predict 一个 gene 跑通。

### Task 3:GEARS 测试(remote,virtualcell)
- [ ] `tests/test_ml_gears.py`(标 remote):GEARS agent 加载训好的 ckpt + predict success;未知 gene → reject/异常处理。
- [ ] **Gate**:远端 virtualcell pass;Mac skip。

---

## Phase 2 — scGPT(vc-scgpt,torch 2.3)

### Task 4:vc-scgpt env 确认 + SCGPTAdapter 构建
- [ ] 确认 background env(`scgpt.model` import OK + cuda True)。
- [ ] 远端验证 `PretrainedBackbonePredictor(backbone_name="scgpt", ckpt_dir=..., gene_names=...)` 能构建 + encode(SCGPTAdapter 加载 196MB ckpt)。
- [ ] **Gate**:scGPT backbone 前向跑通(非 mock)。装不通/ABI 仍坏 → 如实记录,Phase 2 降级(不阻塞 Phase 1)。

### Task 5:scGPT 训 head on donor norman
- [ ] 在 vc-scgpt:donor `pretrained_backbone(backbone_name="scgpt")` frozen encoder + 轻量 head,在 donor norman 训练(复用 donor train_predictor)。
- [ ] **Gate**:训练跑通,记 norman ΔPearson(与 base 同 split 可比)→ `finding_w4c_scgpt.md`。

### Task 6:scGPT 集成 + 测试
- [ ] scGPT predictor-agent(donor_bridge 加载训好 ckpt,对齐 Week 4b)。
- [ ] `tests/test_ml_scgpt.py`(标 remote,vc-scgpt 跑)。

---

## Task 7:findings + memory + push
- [ ] 汇总 `finding_w4c_{gears,scgpt}`;更新 memory(W4c done);Mac 零回归;push。

## 验收(DoD)
1. GEARS 原生 norman 训练跑通 + 记 metrics + predictor-agent 集成 + 测试。
2. scGPT vc-scgpt env + 训 head on norman(可与 base 比)+ 集成 + 测试。
3. 跨 env 测试隔离;Mac 零回归。
4. findings + memory;诚实标注 GEARS 原生 split 不可比、任何降级。
5. 留:GEARS donor norman 适配 / scGPT 全微调 / cross-species(W5) / ablation(W7)。
