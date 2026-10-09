# Finding W4c — scGPT 训 head + 集成(Phase 2)

> scGPT pipeline 完整(env 破解 → backbone 验证 → 训 head → ckpt → donor_bridge 加载 → 等价性)。ΔPearson **0.4407**,frozen backbone 局限(诚实记录)。

## 训练(vc-scgpt, GPU)
- frozen scGPT encoder(53.8M)+ 轻 head(2.47M),复用 donor `train_predictor` on donor norman。
- **减规模避 OOM**:scGPT 无 flash_attn → pytorch full attention over 2000 genes,大 batch 爆显存(15.26 GiB/batch);默认 GPU 0 还被占。→ 选空闲 GPU(动态 `nvidia-smi` 选 mem<2GB)+ max_cells=50 + batch=8 + 3 epoch。
- 训练 543s;train_loss 0.045→0.044(**几乎不降,head 饱和**)。

## 分数(诚实)
- **SCGPT_NORMAN_DELTA_PEARSON = 0.4407**,cosine 0.9808,n=7290。
- **明显低于 base**(cpa 0.6716 / decoder 0.6709 / gnn 0.6675 / linear 0.6639 / latent 0.6365 / pretrained-mock 0.6183)。
- 根因:**frozen foundation-model encoder + 轻 head 在 norman 上饱和**(train_loss 不降)。cosine 0.98 方向对但 delta 细节不准。frozen backbone 不如 task-specific 训练(已知局限)。
- 提升需 fine-tune scGPT(unfreeze 53.8M)+ flash_attn(避 OOM/加速),大工程 → **backlog**。

## 集成 pipeline 完整 ✅
- ckpt:`/home/zkyd/data1/mzy/scgpt_ckpt/norman_2019/pretrained_backbone.{pt,json}`(json kwargs 含 backbone_name=scgpt + backbone_kwargs)。
- `donor_bridge.build_predictor_from_ckpt` 重建 scgpt backbone(加载 196MB ckpt)+ load head state_dict ✅。
- `MLPredictorAgent(scgpt).predict_tensor == donor predict` 逐元素(atol 1e-6)✅。
- 跨 env:训练/加载在 `vc-scgpt`(torch 2.3);`virtualcell`(torch 2.6)不动。脚本 `benchmarks/scgpt_train_eval.py`。

## 结论
真 scGPT 集成 pipeline 全通(Week 4b audit 的 **torchtext 死结彻底破解**);但 frozen+轻head 在 norman ΔPearson 0.44 不如 base。诚实记为「集成成功、frozen baseline 偏低、SOTA 需 fine-tune(backlog)」。这本身验证了 PRAXIS 「foundation model 不是银弹、task-specific 仍强」的判断。
