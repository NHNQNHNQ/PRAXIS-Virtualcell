# Finding W4a — 远端环境 + donor ckpt recon

> Week 4a Task 1(M0)产出。记录远端 GPU 环境、`virtualcell` conda 环境、donor linear ckpt 与**精确复现配方**。供 Task 2–6 与未来对话引用。

## 远端 GPU
- 主机:`zkyd@10.102.106.53`(免密 SSH OK)
- GPU:**8× NVIDIA A100-SXM4-40GB**(driver `570.148.08`,支持 CUDA 13.x)
- conda init:`source /home/zkyd/software/miniconda3/etc/profile.d/conda.sh`

## conda 环境 `virtualcell`(Task 1 新建)
- `python 3.11`、lightning 2.6.5、anndata 0.12.16、numpy/scipy/pint/pyyaml/jsonschema
- torch 见下「GPU/torch 修复」(PyPI 默认 cu130 与 driver 不兼容,改 cu124)。

## GPU/torch 修复(P2-B env 坑实录)
driver 570.148.08 支持 **CUDA 12.8**(`nvidia-smi` runtime 12080),**不支持 cu130**(需 driver≥580):
- ❌ PyPI 默认 `torch 2.12.0+cu130`:`is_available()` 首次误报 True,实际 GPU op `RuntimeError: driver too old (12080)` → CPU fallback。
- ❌ `download.pytorch.org/whl/cu124|cu128`:curl HEAD 返回 200,但 pip 拉大 wheel 反复 `SSLError(SSL: UNEXPECTED_EOF)`(该服务器对 pytorch.org 大文件不稳)。
- ✅ 改**清华 PyPI 镜像**:`pip install torch==2.6.0 -i https://pypi.tuna.tsinghua.edu.cn/simple`(默认 linux wheel = cu124,国内传输稳)→ virtualcell 最终 **`torch 2.6.0+cu124`、`cuda True`、ndev 8**;virtualcell 自跑 ml 4 passed + GPU 锚定逐位复现 S0(DoD 1 满足)。
- **`vcell` 环境**(donor "Virtual cell" 原环境,`torch 2.6.0+cu124 cuda True` + anndata/scipy/pint/yaml/jsonschema 全套)是 Week 4a GPU 验证(锚定 + ml 4 passed)的实际运行环境,亦为 virtualcell 的现成 fallback。

## 远端 praxis 仓
- `/home/zkyd/data1/mzy/PRAXIS-virtualcell`(Task 1 `git clone`,HEAD = `a0aaea2`,与 Mac 同步)
- 同步约定:Mac `commit + push` → 远端 `git pull`

## donor linear ckpt(只读复用,勿改)
- donor 根:`/home/zkyd/data1/mzy/Virtual cell`(**路径含空格,SSH 务必加引号**)
- 锚定 ckpt:`runs/full_bench_20260521_060815/checkpoints/norman_2019/linear_additive.{pt,json}`(另有 `full_bench_20260525_075729` 备选)
- `.json` sidecar:`class_name=LinearAdditivePredictor`,`kwargs={pert_dim:5120, n_genes:2000}`,`meta={bench, epochs, delta_pearson}`
- **anchor `S0 = meta.delta_pearson = 0.6638587363779742`**(⚠ 旧 handoff 写的 0.5886 不准,以此为准)
- `.pt` 是 **bundle dict**(非纯 state_dict):key = `state_dict / class_name / kwargs / provenance / meta / saved_at`
- donor `scripts/checkpoint.py::load_predictor`:`torch.load(path, weights_only=False, map_location="cpu")` → `bundle["state_dict"]`。**torch≥2.6 必须 `weights_only=False`**。

## 复现配方(精确复现 S0=0.6639 的唯一配置)
full_bench 默认 `--seed=0`、`--max-cells=200`;test split 用 `rng_seed=seed+1=1`、`max_cells_per_pert=200`、`pert_features_id="esm2_pert_features"`(=loader 默认;`BENCHES[0]=("norman_2019","esm2_pert_features",...)`,norman 是 gene pert):
```python
load_vcbench_split("norman_2019", "test", max_cells_per_pert=200, rng_seed=1)
```
- `linear_additive` 是 **deterministic 不可训**(`is_trainable`=False,跳训练直接 eval)→ ckpt + 同采样 = 逐位复现。
- EvalAgent:`EvalAgent(batch_size=*, device="cuda").evaluate(model, ds)` → `.metrics.delta_pearson / .cosine`、`.n_samples`(batch_size 不影响 metric 值)。

## 对 plan 的修正(基于 recon,Task 2–6 落实)
1. anchor `S0 = 0.6638587`(非 0.5886)。
2. 锚定脚本 + `norman_eval` 须加 `max_cells_per_pert=200`(否则采样不同,偏离 S0)。
3. `donor_bridge.build_predictor_from_ckpt` 的 `torch.load` 加 `weights_only=False`(匹配 donor、防 torch≥2.6 坑)。
4. Task 6 conftest:`remote` skip 须放在 `llm` 的 early-return **之前**(Mac `.env` 有 DEEPSEEK key → 提前 return,否则 remote 测试跳不到 → 无 torch 时 ERROR)。
