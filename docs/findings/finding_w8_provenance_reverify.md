# Finding W8 — 准确性数字诚信复核(远端当场重跑见证)

> 起因:复核论文准确性数字是否真实(防"为让论文好看而编造")。本 finding 记录在远端**当场重跑**
> donor 锚定、把"信任 finding"升级为"本会话亲眼见证 + 可追溯凭证"的过程与原始输出。

## 复核环境(可追溯)
- 远端 `zkyd@10.102.106.53`(8×A100),env `virtualcell`,repo 已 `git pull` 同步到 **390b67b**(与 Mac/论文一致)。
- donor ckpt:`/home/zkyd/data1/mzy/Virtual cell/runs/full_bench_20260521_060815/checkpoints/norman_2019/`
  (时间戳 2026-05-21,早于全部 PRAXIS 工作 — 即 finding_w4a/w4b 记的那次 benchmark)。
- 复现配方:`load_vcbench_split("norman_2019","test",max_cells_per_pert=200,rng_seed=1)` + donor `EvalAgent`。

## 1. linear 锚定 —— 逐位复现(最强证据)
`linear_additive` 确定性不可训 → 重新 eval 必须逐位复现 S0。命令:
`python -m praxis_virtualcell.benchmarks._anchor_donor_linear ".../norman_2019/linear_additive"`
```
S0_recorded          = 0.6638587363779742
S_eval delta_pearson = 0.6638587363779742    ← 16 位完全一致(diff 0)
cosine = 0.9910358597111228   n = 18874
```
→ **评测 harness(loader + EvalAgent)真实**;论文 linear 0.6639、n=18874 为真。
(cosine 与 finding_w4a 记录差 ~3e-9,正是该 finding 标注的 GPU/CPU 浮点微差;delta_pearson 逐位一致。)

## 2. 6 base 锚定 —— 全部复现,diff 与 finding 一字不差
命令:`python -m praxis_virtualcell.benchmarks._anchor_donor_multi ".../norman_2019"`
```
predictor                         S0      S_eval       diff
linear_additive             0.663859    0.663859   0.00e+00
latent_additive             0.636536    0.635952   5.84e-04
cpa_style                   0.671581    0.670821   7.60e-04
gnn_pert                    0.667487    0.668478   9.91e-04
decoder_only                0.670949    0.672399   1.45e-03
pretrained_backbone         0.618345    0.618499   1.54e-04
```
→ S0(ckpt meta)= 论文 6 base 值(cpa 0.6716/decoder 0.6709/gnn 0.6675/linear 0.6639/latent 0.6365/pretrained 0.6183);
S_eval 在文档容差内复现,**diff 与 finding_w4b_multi_anchor 记录完全相同**(非重新编造)。

## 结论(本轮)
- **评测 harness 与 6 个 base 准确性数字:本会话远端当场见证为真**(linear 逐位 + 6 base diff 一致)。
- 因 Coordinator/scGPT/GEARS 用**同一 harness**,这强力佐证其真实性;但仍应逐一见证(下轮)。
- 另:[[finding_w7_ablation]] 的 A↔D 0→1 表 + cross-species 已在 Mac 本地当场复跑见证(75 passed)。

## 待见证(下轮 /loop)
- [ ] Coordinator 组合 0.7039 / 0.7020 / 0.6847(coordinator_eval / coordinator_bridge)
- [ ] scGPT frozen 0.4407(vc-scgpt env)
- [ ] GEARS 原生 pearson_de 0.8392(标注与 base 不可比)
- 之后接 S2 mean-perturbation baseline(同 harness,顺带做)。
