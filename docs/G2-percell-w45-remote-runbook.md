# G2 远端 runbook — per-cell 解 W4.5 单 control(升级 disagreement 到 per-cell 全量)

> 目标:把 M1/M2 的 disagreement 从**单一 control**(`ds[0].control`)升级为 **per-cell 全量**(每 cell 用自己的 control),重建 ledger + 重算下游(reliability AUROC / risk-cov / bootstrap CI / OOD),看治理指标是否更严格/更强。
> 远端 `zkyd@10.102.106.53`,`conda activate virtualcell`(torch 2.6+cu124 已确认),先 `git pull`。

## W4.5 是什么(Mac 已定位根源)
`praxis_virtualcell/predictors/ml/agent_adapter.py:55`:
```python
MLBackedPredictorAgent(donor_model, control=ds[0].control, ...)   # ← 所有扰动共用单一 control
```
`prepare_input` 恒返回 `{"control": self._control, ...}`(同一 `ds[0].control`)→ 3 个 donor base 的预测都对**同一基线**做 delta → disagreement 是"单 control 下模型方向是否一致"。**真 per-cell**:每 cell 用**自己的 control**(`ds[i].control`,已确认 18874 样本各不相同)预测 → per-cell disagreement → 按扰动聚合。

## 已确定的事实(Mac 从 donor_bridge 远端探查核实)
- `load_norman("test",seed=1)` → 18874 samples;每样本 `.control`(2000 维 Tensor,**逐样本不同**)、`.perturbation`、`.target`。
- 即 **per-cell control 数据本就在 ds 里**,无需新数据 —— 只需改 adapter/ledger 用 `ds[i].control` 而非 `ds[0].control`。

## 改法(两选一,建议 A)

### 方案 A(推荐):per-cell 预测 → per-cell disagreement → 聚合
在 `benchmarks/m1_activation.py` / `eval_ledger` 的填充路径里,**按 cell 迭代**:
```python
# 伪码:对每个 test 扰动,取其所有 test cells,逐 cell 用自身 control 预测
for pert, cells in group_by_perturbation(ds):        # cells = 该扰动的所有样本
    per_cell_dis = []
    for s in cells:
        preds = [predict_delta(model, control=s.control, pert_emb=emb(pert)) for model in base_models]
        per_cell_dis.append(disagreement(preds))     # 同现 EnsembleCoordinator 的 disagreement 定义
    entry.disagreement_score = mean(per_cell_dis)     # 扰动级 = per-cell disagreement 的均值
    entry.disagreement_per_cell_n = len(cells)
```
- **复用**:`MLPredictorAgent.predict_tensor(control, pert_emb, kind, targets)` 已支持任意 control 传入;`EnsembleCoordinator` 的 disagreement 计算逻辑照搬(只是喂 per-cell 预测)。
- 最小改动:给 `MLBackedPredictorAgent.prepare_input` 加"每请求可传 control override",或在 ledger 填充脚本里绕过 agent 直接调 `predict_tensor` 逐 cell(更干净,避免动 runtime 语义)。

### 方案 B(轻量近似):per-perturbation control(每扰动用该扰动 cells 的 control 均值)
比单 control 严格、比 per-cell 便宜;但仍非全量,**不建议**作为终解(只当算力不足时的中间步)。

## 重算下游(改完 ledger 后)
per-cell ledger 落盘后,**Mac 可复算**(纯 Python,无需远端):
```bash
# 远端产出新 ledger:docs/findings/m1_ledger_151_percell.jsonl(同 schema,disagreement 为 per-cell)
# Mac 复算(复用现有 governance 包,只换输入 ledger):
python -m praxis_virtualcell.governance.reliability_model   # AUROC(per-cell disagreement 特征)
python -m praxis_virtualcell.governance.abstain_head        # risk-coverage AUC
# + bootstrap_ci / repeated_cv / ood_enrichment 用新 ledger 重跑
```
→ 对比单 control vs per-cell:corr(disagreement, dp)、AUROC 0.907、risk-cov 0.746 是否变化。

## 防泄漏 / 口径(不变)
- per-cell 只改 **control 基线粒度**,不动数据划分、不引入 label;仍 leave-perturbation-out、无泄漏。
- pert-level 聚合口径不变(per-cell disagreement 均值 → 扰动级),仍 ≠ per-cell 招牌准确性(那是 ΔPearson)。
- disagreement 定义(n_models、zero-vector 处理)照搬现 EnsembleCoordinator,只换基线。

## 步骤
1. `ssh` + `conda activate virtualcell` + `cd repo && git pull`。
2. 写 per-cell ledger 填充脚本(方案 A):逐扰动逐 cell 用 `s.control` 预测 3 base → per-cell disagreement → 聚合 → 落 `m1_ledger_151_percell.jsonl`(附 `disagreement_per_cell_n`)。
3. **把新 ledger 贴回 / push**;Mac 复算 reliability/abstain/CI/OOD,对比单 control。
4. 我更新 findings(m1_ledger_enriched / m2_*)把"disagreement 单 control(W4.5)"局限标为**已解**,报 per-cell 下指标变化;更新 data-inventory §9 缺口表 + RESULTS-CONSOLIDATED §4 诚实边界。

## 诚实标注(写 finding 带上)
- 报 **per-cell vs 单 control** 两套 disagreement 指标对比(corr/AUROC/risk-cov);方向变化如实写,即使 per-cell 让某些指标略降(更严格基线下的真实值)。
- per-cell 仍是 **disagreement 基线** 的升级,**不等于**解决 pert-level≠per-cell 的招牌准确性口径(那是另一回事)。
- 记 per-cell 每扰动用了多少 cells(覆盖)+ 算力/耗时。
