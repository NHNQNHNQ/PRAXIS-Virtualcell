# Finding W4b — GEARS / 真 scGPT audit(Task 4,外部模型)

> 用户选「含外部 GEARS/scGPT」。audit-first 结论:**两者本期受阻,诚实降级 Week 4c**(不阻塞 M1/M2)。呼应 [[p2b_external_models_blocked]]。

## GEARS — 受阻(缺依赖 + 无代码/ckpt + 需训练)
- donor **无** GEARS predictor 代码(`find`/`grep` 空),**无** norman GEARS ckpt。
- vcell `cell-gears 0.0.2` 包 **import 失败**:`ModuleNotFoundError: No module named 'torch_geometric'`(GEARS 依赖 PyG,未装)。
- `gears_aux.yaml` 有辅助数据(essential genes + gene2go),但需 GEARS 框架 + `PertData` 构建 + 训练。
- 用 GEARS 需:装 torch_geometric + 构建 norman `PertData` + 训练(或找预训练 norman ckpt)。**几小时-天级新训练**,非「迁移已有 ckpt」。

## 真 scGPT — 受阻(包 ABI 坏 + 无 norman-head ckpt)
- ckpt **在**:`data/raw/pretrained/scgpt/{args.json, best_model.pt(196MB), vocab.json}`(scGPT_human)。
- vcell `scgpt 0.2.4` 包 **import 失败**:`OSError: libtorchtext.so: undefined symbol`(torchtext 与 torch ABI 不兼容)。
- donor `pretrained_backbone` 的 norman ckpt 用 **mock_backbone**(非 scgpt)→ 没有 norman 上训过的 scGPT-head。
- 用真 scGPT 需:修 torchtext/torch ABI + `SCGPTAdapter` 构建 + 训练 head on norman。**修 env + 新训练**。

## 决策(ADR-W4b-3)
两者均**无 donor norman ckpt**(不像 latent/gnn/decoder/cpa 已训好)→ 不属「迁移」而属「新集成 + 训练」。按 prototype-first + p2b 教训,**降级 Week 4c 专项**,不在 Week 4b 硬啃(不阻塞 M1 复现 0.70 与 M2 agent 化)。

## Week 4c 若做的前置
- **GEARS**:`pip install torch_geometric`(vcell 或新 env)→ `PertData` 适配 norman → 训练。
- **scGPT**:修 torchtext(重装匹配 torch 2.6 的版本)→ `PretrainedBackbonePredictor(backbone_name="scgpt", ...)` + ckpt → 训练 head on norman。
- scGPT ckpt 已就位(196MB),阻塞仅在包 ABI + head 训练;比 GEARS 更接近可行。
