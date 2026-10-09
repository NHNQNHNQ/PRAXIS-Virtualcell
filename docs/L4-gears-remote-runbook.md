# L4 远端 runbook — GEARS same-split / same-metric 入表 A(解 R8)

> 目标:让 GEARS 在 **donor norman test split** 上、用 **per-cell ΔPearson(同表 A 口径)** 评估 → 入表 A(PRAXIS Coordinator 0.7039 旁),解"无同协议外部 baseline"。
> 远端 `zkyd@10.102.106.53`,`conda activate virtualcell`,先 `git pull`。**本 runbook:确定的接口直接给(Mac 已核实调用方式),未知的标【远端探查】(donor 源码 Mac 看不到,不臆造)。**

## 为什么必须远端(不是偷懒)
GEARS 自带 `pearson_de`(DE-gene 绝对表达,`simulation` split)与表 A 的 per-cell ΔPearson **不可比**。要同协议,得用 **donor EvalAgent** 在 **donor norman test split** 上评 GEARS。donor 的 `EvalAgent`/`Subagent`/`load_vcbench_split` 都是 `sys.path` 注入的 donor 私有代码(`/home/zkyd/data1/mzy/Virtual cell`),Mac repo 无源码、无数据 → 适配只能远端写+验证。

## 已确定的接口(Mac 从 `coordinator_eval.py` / `donor_bridge.py` 核实,直接复用)

```python
# 1) 拿 donor norman test split(= 表 A 的 151 test 扰动口径, n≈18874)
from praxis_virtualcell.predictors.ml.donor_bridge import load_norman
ds = load_norman(split="test", seed=1)          # = load_vcbench_split("norman_2019","test", rng_seed=1, max_cells_per_pert=200)

# 2) per-cell ΔPearson 评估(与表 A 0.7039 完全同一路径)
from coordinator.eval_agent import EvalAgent
rep = EvalAgent(batch_size=64, device="cuda").evaluate(MODEL, ds)
print(rep.metrics.delta_pearson, rep.n_samples)  # ← 这就是要入表 A 的 ΔPearson + n
```

→ 只要把 GEARS 包成 `MODEL`(满足 `EvalAgent.evaluate` 期望的接口),分数就与表 A 同协议、可直接并列。

## 远端探查点(Mac 看不到 donor 源码,必须先确认再写 adapter)

```bash
ssh zkyd@10.102.106.53
conda activate virtualcell
cd <praxis repo>   && git pull
D="/home/zkyd/data1/mzy/Virtual cell"
# 探查1:EvalAgent.evaluate 怎么调 MODEL?期望什么 predict 接口/返回什么形状?
grep -n "def evaluate" "$D/coordinator/eval_agent.py"
sed -n '1,80p' "$D/coordinator/eval_agent.py"        # 看它对 model 调的方法(predict/forward)、batch 结构、delta 怎么算
# 探查2:Coordinator/Subagent 的 predict 签名(GEARS adapter 要实现同一个)
grep -n "def predict\|def forward\|def __call__" "$D/coordinator/coordinator.py" "$D/agents/subagent.py"
# 探查3:ds 的 sample/batch 字段(perturbation 标识、control、true delta 在哪)
python -c "from praxis_virtualcell.predictors.ml.donor_bridge import load_norman; ds=load_norman('test',seed=1); b=ds[0]; print(type(b), getattr(b,'__dict__',b))"
```

## 适配思路(GEARS condition-level → donor per-cell ΔPearson)

- GEARS 是 **condition 级**:对一个扰动给一个平均预测 delta。donor ΔPearson 是 **per-cell**。
- 对齐:GEARS 对 ds 中每个扰动预测平均 delta → **broadcast 到该扰动的所有 test cell** → 喂 EvalAgent 算 per-cell ΔPearson。(condition-level model 在 per-cell 指标上评估,是 GEARS 的固有粒度限制,finding 须诚实标注。)
- adapter 骨架(**接口待探查1/2 确定后填**):

```python
class GearsDonorAdapter:                 # 实现 EvalAgent 期望的 MODEL 接口(见探查1/2)
    def __init__(self, gears_model, gene_order): ...
    def predict(self, batch):            # ← 方法名/签名/返回形状以探查为准
        # 对 batch 内每个 cell 取其 perturbation → GEARS 预测该扰动 delta → 对齐 donor gene order → 返回
        ...
```

## 防泄漏(关键!)
- donor test split(`load_norman("test",seed=1)`)就是表 A 的 151 test 扰动。**GEARS 必须在不含这些 test 扰动的 train 上训练**,否则泄漏。
- GEARS 现用 `pd.prepare_split(split="simulation", seed=1)` 自带划分 → **须确认/改成与 donor norman train/test 扰动划分一致**(只用 train 扰动训练,test 扰动留评估)。这是入表前必须坐实的一点。

## 步骤
1. `ssh` + `conda activate virtualcell` + `cd repo && git pull`。
2. 跑上面探查 1/2/3,确定 `EvalAgent.evaluate` 期望的 model 接口 + ds 结构。
3. 在 `benchmarks/gears_norman.py` 加 `--donor-eval` 路径:训练 GEARS(train 扰动)→ 包 `GearsDonorAdapter` → `rep = EvalAgent(64,"cuda").evaluate(adapter, load_norman("test",seed=1))` → print `delta_pearson, n`。
4. **把 `delta_pearson + n` 贴回**(连同是否解决了 split 对齐),我入表 A、写 finding、更新 data-inventory §1 + 解 R8。

## 诚实标注(写 finding 时带上)
- 用 `rep.metrics.delta_pearson`(per-cell ΔPearson),**非** GEARS `pearson_de`。
- GEARS 训练无固定 seed(重训噪声:0.8392→0.8461);报多次或注明单次。
- condition→cell broadcast 是 GEARS 粒度限制下的对齐方式,非 per-cell 原生预测。
- 若 split 对齐有残留差异(GEARS go-graph 过滤 IER5L 等),如实记。
