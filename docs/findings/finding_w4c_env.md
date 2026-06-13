# Finding W4c — env 破解 + scGPT backbone 验证

> Week 4b audit 降级的两个 env 阻塞已破解;真 scGPT backbone 前向验证通过(Phase 2 Task 4 gate ✅)。

## env 破解
### GEARS (virtualcell, torch 2.6)
- `pip install torch_geometric`(PyG 2.8.0)+ `cell-gears 0.0.2` → `from gears import GEARS, PertData` **import OK**。
- 阻塞:GEARS 原生 dataverse 下载远端 ~25kiB/s(norman 数据大,数小时)不可接受 → 改用 donor norman h5ad 适配(Phase 1)。

### scGPT (vc-scgpt, torch 2.3) — torchtext 死结破解
- 新建 conda `vc-scgpt`:py3.11 + **torch 2.3.1+cu121**(driver 570 向后兼容)+ **torchtext 0.18.0**(匹配 torch 2.3,破 ABI 死结)+ scgpt 0.2.4 + IPython(scgpt 漏的依赖)+ donor 依赖(pint/pyyaml/jsonschema)。
- `from scgpt.model import TransformerModel` import OK,cuda True。

## scGPT backbone 验证(Phase 2 Task 4 gate ✅)
- `PretrainedBackbonePredictor(backbone_name="scgpt", backbone_kwargs={gene_names(2000), ckpt_dir})` 构建成功(**53.8M params**)。
- `backbone.encode(control)` → z shape **(1, 512)**。**真 scGPT encoder 前向跑通(非 mock_backbone)**。
- ckpt:`data/raw/pretrained/scgpt`(args.json / best_model.pt 196MB / vocab.json)。
- donor `train_predictor`(scripts/run_bench.py)在 vc-scgpt import OK → 复用训 head。

## 下一步
- Phase 2 Task 5:训 head on donor norman(frozen scGPT + 轻量 head)→ 记 ΔPearson(与 base 同 split 可比)。
- Phase 1:GEARS donor h5ad 适配(避 dataverse 慢下载)+ 训练。
