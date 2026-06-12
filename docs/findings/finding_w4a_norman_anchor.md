# Finding W4a — donor linear Norman 锚定(M1)

> Week 4a Task 2(M1)产出。锚定 donor linear ckpt 在 Norman test 的 ΔPearson,确立 M2 对照真值 `S_anchor`。

## 锚定结果(远端 virtualcell)
脚本:`praxis_virtualcell/benchmarks/_anchor_donor_linear.py`;ckpt = `runs/full_bench_20260521_060815/checkpoints/norman_2019/linear_additive`。

| 量 | 值 |
|---|---|
| `S0_recorded`(ckpt `meta.delta_pearson`) | 0.6638587363779742 |
| **`S_eval`(本次复算)** | **0.6638587246223396** |
| 差异 | **1.2e-8**(浮点级逐位复现) |
| cosine | 0.9910358569479936 |
| n_samples | 18874 |

**复现配方**:`load_vcbench_split("norman_2019", "test", max_cells_per_pert=200, rng_seed=1)`(linear_additive deterministic 不可训 → ckpt + 同采样 = 逐位复现)。

## M2 对照真值
**`S_anchor = 0.6638587246223396`**(Task 5 的 praxis 复现须 `abs(s_praxis - S_anchor) < 1e-4` 命中;因同 ckpt+loader+EvalAgent,预期差异 ~0)。

## 备注:GPU 现状
首跑时 `torch 2.12.0+cu130` 与 driver 570(CUDA 12.8)不匹配 → `cuda.is_available()=False`,eval **CPU fallback**(linear deterministic,结果不受影响)。env 修复(重装 `torch cu128`)见 [finding_w4a_env.md](finding_w4a_env.md)。
