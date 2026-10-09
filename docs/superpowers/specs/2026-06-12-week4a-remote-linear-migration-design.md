# Week 4a — 远端 ML predictor 迁移(linear 原型)设计 spec

- 日期:2026-06-12
- 状态:待用户复核
- 前置:Week 2/3 完成(praxis_virtualcell offline + LLM 层,48 tests 绿)
- 上游:iii-lite 计划 §6;方向决策 C(远端 GPU)

## 0. 决策(已与用户确认)
1. **远端执行(C)**:在 GPU 服务器 `zkyd@10.102.106.53`(6× A100 40GB)跑;Mac 只 SSH 编排,**torch 不进 Mac**。
2. **conda 环境 `virtualcell`**:不存在 → 本期新建。
3. **prototype-first**:先复现 donor 原 benchmark,再只迁 `linear_additive` 一个 predictor 打通链路。其余 base + Coordinator + ~0.70 留 Week 4b。

## 1. 现状(勘探所得)
- donor 完整副本在远端 `/home/zkyd/data1/mzy/Virtual cell`(predictors/bench/coordinator/data/runs/scripts 齐全)。
- 远端 Norman ckpt 全:`runs/full_bench_20260521_060815/checkpoints/norman_2019/{linear_additive,latent_additive,cpa_style,decoder_only,gnn_pert}.pt`;Norman 数据 `data/raw` 在远端。
- donor 依赖轻:`numpy/scipy/pint/pyyaml/jsonschema + torch>=2.2 + lightning>=2.2`(无 scanpy/gears/scgpt)。
- predictor 接口(donor `predictors/base.py`):`Predictor.predict(ctx: Context, pert: Perturbation) -> Prediction`,`Context.control` 是 torch baseline 表达 tensor;`bench/vcbench/loader.py` 加载 Norman。
- 远端**尚无** `PRAXIS-virtualcell` 副本。

## 2. 里程碑(本期 = M0+M1+M2-linear)

### M0 — 建 virtualcell 环境(远端)
- `conda create -n virtualcell python=3.11 -y`。
- 装 `torch>=2.2`(匹配 A100:先 `nvidia-smi` 看 driver/CUDA,选对应 cuXXX 的 torch index;装后断言 `torch.cuda.is_available()==True`)+ `lightning numpy scipy pint pyyaml jsonschema`。
- **Gate**:`python -c "import torch,lightning; print(torch.cuda.is_available())"` 为 True。

### M1 — 复现 donor 原 Norman benchmark(锚定数字,不迁移)
- 在 virtualcell 环境里、`/home/zkyd/data1/mzy/Virtual cell` 下跑 donor **自己的** benchmark 脚本(`scripts/run_bench.py` / `run_coordinator_only.py`,plan 时按远端实际签名定),指向 `runs/full_bench_20260521_060815/checkpoints/norman_2019`。
- 捕获 Norman 上各 base(linear/latent/cpa/gnn/decoder)+ Coordinator 的分数,写 `finding_w4a_norman_anchor.md`(作为后续迁移的对照真值)。
- **Gate**:linear_additive 跑出一个确定分数(记为 `S_linear_donor`);Coordinator 分数接近 0.70(若脚本跑得动)。环境/数据/ckpt 链路确认可用。

### M2 — 迁 linear_additive 成真 PredictorAgent(原型)
- 把 `PRAXIS-virtualcell` 弄到远端(`git clone` 自 `NHNQNHNQ/PRAXIS-Virtualcell.git`,或 rsync;plan 定)。在 virtualcell 环境装 praxis_virtualcell(`pip install -e .` 走 praxis2;另需把 donor 项目加入 sys.path 以复用其 predictor/loader)。
- 新增 `praxis_virtualcell/predictors/ml/`(**只此目录 import torch**):
  - `donor_bridge.py`:把 donor `Virtual cell` 加入 sys.path,import 其 `predictors.linear_additive`、`bench.vcbench.loader`、metric;封装"加载 ckpt + 构 Context/Perturbation + predict"。
  - `linear_additive_agent.py`:`LinearAdditivePredictorAgent(PredictorAgent)`,`run_prediction` 内:据 `VirtualCellRequest` + Norman control(donor loader 提供)构 donor torch `Context/Perturbation` → donor linear predict → 映射回 praxis `prediction` dict。
- 新增 `praxis_virtualcell/benchmarks/norman_eval.py`:远端 GPU 上用 donor loader 取 Norman,遍历 perturbation 跑 `LinearAdditivePredictorAgent`,用 donor metric 算分 → `S_linear_praxis`。
- **Gate**:`S_linear_praxis == S_linear_donor`(同 ckpt/数据/metric,数值应一致;容差按 metric 决定,plan 定)。证 rich↔torch 适配 + 远端 repro 链路通。

## 3. 架构边界
- praxis_virtualcell 的 `core / runtime / 4 deterministic agent / 4 LLM agent` 仍 **torch-free**;**仅** `predictors/ml/` import torch,且只在远端 virtualcell 环境跑。
- Week 2/3 的 48 个 offline/LLM 测试不依赖 torch,**零回归**(它们在 Mac 上照常跑;`predictors/ml/` 的测试标 `gpu`/`remote`,Mac 无 torch 时 skip)。
- Mac:SSH 编排 + 记录;远端:真算。

## 4. 交付物
- 远端 `virtualcell` conda 环境(torch+lightning+...)。
- `finding_w4a_norman_anchor.md`(M1 donor 各 base + Coordinator Norman 分数)。
- `praxis_virtualcell/predictors/ml/{donor_bridge,linear_additive_agent}.py` + `benchmarks/norman_eval.py`(远端可跑)。
- 迁移对照:`S_linear_praxis == S_linear_donor` 的运行记录。
- conftest:`predictors/ml` 测试标 `remote`(无 torch/无远端时 skip),Mac 全套仍绿。

## 5. 验收
1. 远端 virtualcell 环境 `torch.cuda.is_available()` True。
2. M1 复现 donor Norman:linear 有确定分数,记录 anchor。
3. M2 linear 经 praxis PredictorAgent 在远端跑 Norman,分数 == donor linear(同口径)。
4. Mac 端 Week 2/3 的 48 测试零回归(torch 只在远端)。
5. 不动 donor `Virtual cell`(只读复用;不写它的 runs)。

## 6. 风险(对齐 P2-B 教训)
- **CUDA/torch env 灾难**:先验 `cuda.is_available()`;装不上则用远端 `torch_gpu_pkgs` 缓存或匹配 index-url。装不通就停下报告,不硬凑。
- **ckpt-数据版本失配**:M1 先用 donor 原码复现锚定,M2 复用同 loader/同 ckpt,最大化一致。
- **donor 接口耦合**:M2 用 sys.path 复用 donor 代码(不 vendor),降低迁移面;真 vendor 留后续。
- **SSH/远端不稳**:每步可重入;失败如实记,不假装跑过。
- 范围:**只 linear**。latent/cpa/gnn/decoder + Coordinator + 0.70 明确留 Week 4b。
