# finding v0.3 L4 — GEARS same-split / same-metric donor-eval(解 R8:同协议外部专用 baseline)

> 目标:把专用 SOTA GNN(GEARS)放到**与表 A 完全同协议**(donor Norman test split · per-cell ΔPearson · 同 EvalAgent · n=18874)下评估,解决"表 A 无同协议外部强 baseline"。证据类型:`[远端实跑]`(远端 A100 单次)。
> 远端 `zkyd@10.102.106.53` env `virtualcell`,2026-07-01 见证。脚本:`praxis_virtualcell/benchmarks/gears_donor_eval.py`;runbook:`docs/L4-gears-remote-runbook.md`。

## 1. 结果(实跑数字)

```
GEARS_DONOR_EVAL: delta_pearson=0.487662  cosine=0.986365  n=18874  epochs=5  total_t=4303s
```

| 系统(同协议:donor test split · per-cell ΔPearson · n=18874) | ΔPearson |
|---|---|
| **PRAXIS Coordinator (all-5)** | **0.7039** |
| 6 donor base predictor | 0.6716–0.6183 |
| **GEARS(same-split donor-eval,5ep)** | **0.4877** |
| mean-perturbation(naive 下界) | 0.4615 |
| scGPT frozen(n=7290) | 0.4407 |

→ **同协议下 GEARS = 0.4877**:略高于 mean-baseline(0.4615),**低于所有 donor base**(≥0.6183),远低于 PRAXIS Coordinator(0.7039)。

## 2. 为什么这解 R8(而非 off-axis 对比)

- GEARS **原生** `pearson_de` = 0.8392(重训 0.8461):是 **DE-gene 绝对表达 pearson** + GEARS 自带 `simulation` split → 与表 A 的 per-cell ΔPearson **不可比(off-axis)**,此前不入表。
- 本 finding 用 **donor `EvalAgent`** 在 **donor norman test split** 上评 GEARS,指标口径与表 A 0.7039 **完全一致** → 首次给出**同协议外部专用 baseline**,表 A 不再"准确性侧无强外部对照"。

## 3. 防泄漏(已坐实)

- GEARS 用 **custom split**:训练扰动池 = donor train conditions − donor test conditions(互斥),test = donor 151 test 扰动。日志:`[split] train=62 val=6 test=150`。
- test 151→150:**IER5L** 不在 GEARS GO graph,被 GEARS 自身 pipeline 过滤丢 1 个扰动(诚实标注)。
- eval 用 `load_norman("test",seed=1)`(= 表 A 的 18874 cells),GEARS **在不含 test 扰动的 train 上训练**,无泄漏。

## 4. 诚实标注(务必带进论文)

1. **condition→cell broadcast**:GEARS 是 **condition 级**(每扰动一个平均 delta),per-cell ΔPearson 是 cell 级。适配把 GEARS 平均预测 broadcast 到该扰动所有 test cell → 用 EvalAgent 算 per-cell。这是 GEARS **固有粒度限制**下的对齐,per-cell 指标对 condition 级模型天然不利 → **0.4877 不代表 GEARS 无能,而是"同一 per-cell 尺子下 condition 级模型的读数"**。
2. **训练预算对齐**:5 epoch、hidden=64,**与产生原生 0.8392 那次完全相同**(`finding_w4c_gears`);GEARS 训练无固定 seed(重训噪声 0.8392→0.8461),本次单次。
3. **GEARS 训练扰动少**:GEARS PertData/GO-graph 把 donor 137 train conditions 过滤到 62 可训练 → GEARS 见的训练扰动比 donor predictor 少(其自带 pipeline 所致,如实记)。
4. **不作"PRAXIS 赢 SOTA"标题**:论文立场是**不以准确性赢 SOTA 为卖点**。本结果的正确读法:**指标/协议选择极大影响读数**(off-axis 0.8392 vs same-protocol 0.4877),同协议下 PRAXIS ensemble+治理具竞争力;GEARS 的 condition 级粒度是其读数偏低的主因之一。

## 5. 结论

- **R8 解除**:表 A 现有同协议外部专用 baseline(GEARS 0.4877)。
- 强化 v0.2 主叙事:**规模/专用性非解药,指标口径决定结论**——off-axis 指标(0.8392)会高估;拉到同协议 per-cell ΔPearson,专用 GNN 读数 0.4877,PRAXIS ensemble 0.7039 领先(带 GEARS 粒度 caveat)。
- **入表 A**:已更新 `docs/paper/v0.3/data-inventory.md` §1、`docs/paper/v0.4/RESULTS-CONSOLIDATED.md` R2。
