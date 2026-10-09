# Week 4c 设计 — GEARS / scGPT 专项训练 + 集成

> Week 4b audit 降级的两个外部模型本期专项:训练 + 集成为 predictor-agent。用户决策:**两者都做(scGPT 建 torch 2.3 新 env)**、**GEARS 先用原生 norman 跑通**。

## 0. 目标
- **GEARS**:在 virtualcell(torch 2.6 + PyG + cell-gears)用原生 norman 训练 + 集成 predictor-agent。
- **scGPT**:建 torch 2.3 新 env `vc-scgpt`(torchtext 0.18 匹配)+ 训 head on norman + 集成。

## 1. 现状(spike 确认)
- **GEARS 可行**:virtualcell import OK(PyG 2.8.0 + cell-gears 0.0.2);`PertData.load('norman')` dataverse 可达(303→S3);标准 API:`PertData(data_path)` / `prepare_split(split='simulation',seed=1)` / `get_dataloader(batch_size)` / `GEARS(pert_data,device).model_initialize(hidden_size=64).train(epochs=20).predict([['GENE']])`。donor 已有辅助数据(essential_genes + gene2go)。
- **scGPT torchtext 死结**:scgpt 0.2.4 依赖 torchtext,torch 2.6 无匹配(torchtext 0.18 是停维最后版,匹配 torch 2.3)→ 建 torch 2.3 `vc-scgpt`。donor `SCGPTAdapter`(pretrained_backbone)已有框架,ckpt 在 `data/raw/pretrained/scgpt`(196MB:args.json/best_model.pt/vocab.json)。

## 2. 决策(ADR)
- **ADR-W4c-1 GEARS 原生 norman**:用 cell-gears 内置 norman(用户定,prototype-first)。split 与 donor base **不严格可比** → 诚实标注,不直接进 donor 同表 ablation(留后)。
- **ADR-W4c-2 scGPT 独立 env**:torch 2.3 `vc-scgpt`(torchtext 0.18);virtualcell torch 2.6 **不动**。跨 env 测试隔离(GEARS 测试 virtualcell / scGPT 测试 vc-scgpt)。
- **ADR-W4c-3 都需训练**(无 ckpt):GEARS train 原生;scGPT 走 donor `pretrained_backbone(backbone_name="scgpt")` 训 head on donor norman。
- **ADR-W4c-4 集成**:GEARS/scGPT 各包 predictor-agent;GEARS 用原生 PertData,scGPT 用 donor norman(可与 base 同 split 比)。
- **ADR-W4c-5 prototype-first**:先训练跑通 + 拿分数 + 基本集成;调优/ablation 留后。

## 3. 风险
- GEARS 原生 split 不可比(标注,呼应 [[w45_abstain_granularity]] 粒度精神)。
- scGPT env + 训 head 工程大;scgpt 依赖重(scvi-tools/scib/cell-gears)可能版本冲突(p2b 教训)。
- 跨 env 测试隔离;训练耗时(GEARS 20ep + scGPT head)。

## 4. 留后续
GEARS donor norman 适配(同表可比)/scGPT 全 backbone 微调/cross-species(W5)/4 组 ablation(W7)。
