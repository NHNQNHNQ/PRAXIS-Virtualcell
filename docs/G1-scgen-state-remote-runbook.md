# G1 远端 runbook — scGen / STATE same-split / same-metric 入表 A

> 目标:把 **scGen** 与 **STATE** 两个外部专用 perturbation predictor,放到 **donor norman test split** 上、用 **per-cell ΔPearson(同表 A 口径,n=18874)** 评估 → 入表 A(GEARS 0.4877 / scGPT 0.4407 旁),把"同协议外部 baseline"从 1 个(GEARS)扩到 3 个。
> 远端 `zkyd@10.102.106.53`,`conda activate virtualcell`,先 `git pull`。**结构照搬已成功的 L4**(`docs/L4-gears-remote-runbook.md`);确定接口直接给,未知标【远端探查】。

## 为什么必须远端
scGen/STATE 的训练/预测都需 donor 私有数据(`/home/zkyd/data1/mzy/Virtual cell`)+ GPU;二者原生指标/split 与表 A per-cell ΔPearson 不可比。要同协议,须在 **donor train split 训练/适配 → donor EvalAgent 在 donor test split 评**。Mac 无 donor 数据/GPU/包,只能远端写+验证。

## 已确定的接口(Mac 从 `scgpt_train_eval.py` / `gears_donor_eval.py` 核实,直接复用)

```python
# 1) donor norman train/test split(= 表 A 口径;train 训练、test 评估,防泄漏)
from bench.vcbench.loader import load_vcbench_split
train_ds = load_vcbench_split("norman_2019", "train", rng_seed=0, max_cells_per_pert=None)
test_ds  = load_vcbench_split("norman_2019", "test",  rng_seed=1)   # = load_norman("test",seed=1), n≈18874
# 2) per-cell ΔPearson 评估(与表 A / GEARS 0.4877 完全同一路径)
from coordinator.eval_agent import EvalAgent
rep = EvalAgent(batch_size=64, device="cuda").evaluate(MODEL, test_ds)
print(rep.metrics.delta_pearson, rep.n_samples)   # ← 入表 A 的数
```
- `MODEL` 需实现 donor `Predictor` 接口(**L4 已核实**):`predict(ctx, pert) -> Prediction(mean=...)`;`Context.control`(2000 维 per-cell)、`Perturbation.kind/targets`。GEARS adapter(`gears_donor_eval.py::GearsDonorAdapter`)是现成范例,scGen/STATE adapter 照抄其骨架,只换内部预测调用。

## 安装(virtualcell env 现无 scgen/scvi/state → 先装)

```bash
ssh zkyd@10.102.106.53 && conda activate virtualcell
pip install scgen scvi-tools            # scGen(scvi-tools 生态)
pip install arc-state cell-load         # STATE(Arc Institute);包名以 pip 实际为准【探查】
python -c "import scgen, scvi; print(scgen.__version__, scvi.__version__)"
python -c "import state" 2>&1 | tail -1   # STATE import 名【探查:state / arc_state】
```
- torch 2.6+cu124(已确认)。若 scvi-tools 与 torch 2.6 冲突 → 仿 scGPT 单独建 `vc-scgen` env(见 scgpt 用 `vc-scgpt` 的先例)。STATE 若依赖冲突同样单独 env。

## A. scGen 路径(优先,较成熟)

scGen = scvi-tools 的 VAE + latent 向量运算预测扰动。需 norman **AnnData**(含 control/perturbed 标签)。

【远端探查】donor norman h5ad(GEARS 用过):`/home/zkyd/data1/mzy/Virtual cell/data/raw/tasks_data/unseen_perts/norman2019_comb_stack.h5ad`(obs `perturbation`)。scGen 训练需 `obs["condition"]`(control vs 各扰动)+ `obs["cell_type"]`。

```python
# scgen_donor_eval.py 骨架
import scanpy as sc, scgen, torch, numpy as np
from predictors.base import Predictor, Prediction
from coordinator.eval_agent import EvalAgent
from praxis_virtualcell.predictors.ml.donor_bridge import load_norman

# 1) 训练:只用 donor TRAIN 扰动(防泄漏)+ control
train_conds = donor_train_conditions()          # 同 gears_donor_eval.donor_conditions() 拿 train 扰动集
ad = sc.read_h5ad(NORMAN_H5AD)
ad.obs["condition"] = [ctrl_or_pert(p) for p in ad.obs["perturbation"]]
ad.obs["cell_type"] = "K562"
ad_train = ad[ad.obs["perturbation"].isin(train_conds | {"control"})].copy()
scgen.SCGEN.setup_anndata(ad_train, batch_key="condition", labels_key="cell_type")
m = scgen.SCGEN(ad_train); m.train(max_epochs=100)   # epoch 数【探查/按显存】

# 2) adapter:scGen predict_perturbation(ctrl → 目标扰动)→ per-cell 预测表达
class ScgenDonorAdapter(Predictor):
    name="scgen"
    def predict(self, ctx, pert):
        c = ctx.control if ctx.control.dim()>1 else ctx.control.unsqueeze(0)
        if pert.kind=="control": return Prediction(mean=c)
        pred = scgen_predict_for(m, targets=pert.targets, control=c)   # ← scGen API【探查 predict 签名】
        return Prediction(mean=pred, meta={"predictor":"scgen"})
    def supports(self, pert): return pert.kind=="control" or len(pert.targets)>0

rep = EvalAgent(64,"cuda").evaluate(ScgenDonorAdapter(), load_norman("test",seed=1))
print("SCGEN_DONOR_EVAL:", rep.metrics.delta_pearson, rep.n_samples)
```
【探查 scGen】`scgen.SCGEN.predict()` 的签名(需 `ctrl_key`/`stim_key`/`celltype_to_predict`);scGen 原生做二分类扰动迁移(ctrl→stim),多扰动 norman 需**每个扰动一个 stim 标签**分别 predict,或用 latent delta。确认 API 后填 `scgen_predict_for`。

## B. STATE 路径(次优,较重/较新)

STATE(Arc Institute)= transformer,输入 control cell + 扰动 → 预测扰动后表达。需其 config + `cell-load` 数据格式;可能有预训练 checkpoint 或需在 donor train 上 fine-tune。

【远端探查】:
```bash
python -c "import state; print(state.__file__)"      # 确认 import 名与路径
state --help 2>/dev/null || python -m state --help    # CLI?
# STATE 期望的数据/config schema(cell-load .toml / h5ad 要求)
```
- adapter 同 A:把 STATE 的 per-cell 扰动预测包成 `Predictor.predict(ctx,pert)->Prediction(mean=...)`,喂 donor EvalAgent。
- STATE 若只提供 condition-level 预测 → 同 GEARS 做 condition→cell broadcast(caveat 照 L4 标注)。

## 防泄漏(关键,同 L4)
- **只用 donor TRAIN 扰动训练**,donor test 151 扰动**严禁**进训练。用 `gears_donor_eval.donor_conditions()` 拿 train/test 扰动集,train pool = train − test。
- eval 用 `load_norman("test",seed=1)`(表 A 的 18874 cells)。
- scGen 的 setup_anndata 只喂 train 子集;STATE 的 split 配置须排除 test 扰动。

## 步骤
1. `ssh` + `conda activate virtualcell` + `cd repo && git pull`;装 scgen/scvi(+ STATE 包),冲突则单独 env。
2. 跑安装验证 + 【探查】scGen `predict` 签名 / STATE import+config。
3. 写 `benchmarks/scgen_donor_eval.py`(照 `gears_donor_eval.py`)→ 训练(train 扰动)→ adapter → `EvalAgent.evaluate(adapter, load_norman("test",seed=1))` → print `delta_pearson, n`。STATE 同理 `state_donor_eval.py`。
4. **把 `SCGEN_DONOR_EVAL` / `STATE_DONOR_EVAL` 的 delta_pearson + n 贴回**,我入表 A(GEARS 0.4877 旁)、写 finding、更新 RESULTS-CONSOLIDATED R2 + data-inventory §1。

## 诚实标注(写 finding 带上)
- 用 `rep.metrics.delta_pearson`(per-cell ΔPearson),非各模型原生指标。
- scGen/STATE 训练无固定 seed → 注明单次或报多次。
- 若 condition→cell broadcast(STATE)→ 同 GEARS caveat。
- 记训练 epoch/超参 + 是否单独 env;split 对齐(train∩test=∅)须坐实。
- 预期:同协议下外部 baseline 多半仍 < Coordinator 0.7039(与 GEARS 0.4877 一致的叙事:指标/协议决定结论,PRAXIS ensemble+治理具竞争力)——但**以实跑为准,不预设**。
