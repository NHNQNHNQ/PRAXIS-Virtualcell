---
case_id: omics-023-theodoris-2023-geneformer-foundation
schema_version: 1
modality: scRNA_seq
study: "Theodoris et al 2023, Transfer learning enables predictions in network biology (Geneformer)"
public_accession: "Genecorpus-30M (Hugging Face); pretrain weights https://huggingface.co/ctheodoris/Geneformer"
doi: 10.1038/s41586-023-06139-9
organism: "Homo sapiens (pretrain ~95% human + ~5% organism-shared)"
tissue: "multi-tissue pretrain corpus (immune / cardiac / renal / hepatic / etc.) + fine-tune downstream tasks"
study_design: foundation_model_pretraining
assay_subtype: pretrained_transformer_30m_cells
cell_type_focus: [foundation_model_zero_shot, cell_state_embedding, in_silico_perturbation]
tools: [Geneformer 30M params, transformers 4.x, datasets, anndata, scanpy, sklearn]
method_choice: [pretrain_30m_cells, rank_value_encoding, finetune_classification, in_silico_perturbation, zero_shot_embedding]
status: validated
validated: true
source: praxis_seed
case_class: success
provenance:
  source_type: literature
  doi: 10.1038/s41586-023-06139-9
  extracted_at: 2026-05-01
tags: [foundation_model, transformer, pretrained, transfer_learning, in_silico_perturb]
---

# Theodoris 2023 Geneformer：scRNA foundation model 的范式（30M cells pretrain）

## Background
Geneformer 是当前最具代表性的 scRNA foundation model：30M cells 跨 ~40 tissues pretrain 一个 BERT-style transformer，下游 zero-shot embedding / fine-tune classification / in-silico perturbation 全适用。**case-based learning 关键**：与 cases 001-022 的"对每个数据集做完整 pipeline"截然不同，foundation model 重点变成"如何 fine-tune + 验证 transfer 是否成功"。这是 PRAXIS-Omics 第一个 foundation model case，覆盖 2024+ 主流分析路线（scGPT / scFoundation / Geneformer 同范式）。

## What I actually did (in a downstream fine-tune scenario)
1. **数据准备**：raw scRNA AnnData → tokenize 成 Geneformer 格式
   - 每 cell：取 expressed gene → rank by expression → top 2048 ranked genes 作为 token sequence
   - **rank-value encoding**（不是 absolute count）：cell 内基因排名，对 cell-cell scale 鲁棒
2. **Choose mode**：
   - **Zero-shot embedding**: 直接拿 pretrain CLS token 做 embedding → cell-state similarity
   - **Fine-tune classification**: 加 head + 训练 (cell type / disease state) → 比 random init 高 5-15% F1
   - **In-silico perturbation**: 屏蔽某 gene token，看 embedding 偏移量 → predict perturbation effect
3. **训练设置 (fine-tune)**：
   - learning rate 5e-5（小于 BERT 标准 2e-5 的 2.5x，因为细胞数据 noise 高）
   - batch size 12（GPU memory bound）
   - 3-5 epoch 通常足够
   - **冻结底 6 层 + 训顶 6 层 + head**（小数据时；大数据 unfreeze 全部）
4. **Evaluation**：
   - **Cell type embedding distance** matches ontology distance: CD4 vs CD8 distance < CD4 vs B-cell
   - **In-silico KO** of TBX5 in cardiomyocyte → predicted dysmorphic phenotype matches in-vitro KO
5. **Domain shift check**：
   - Pretrain 主体是健康 + 部分 disease；mouse data → 不可直接 zero-shot；先 fine-tune adapter

## ★ 排除/不做的事
- **Raw count + log1p + 直接喂 transformer**：Geneformer 用 rank-value encoding，不要预先 normalize（rank 已是相对量）
- **Fine-tune on < 1000 cells**：foundation model 容易 overfit；至少 5-10k cells per class
- **Cross-organism zero-shot without adapter**：mouse cell pretrain coverage 弱；先小 fine-tune
- **拿 cell-level prediction 直接当机制结论**：transformer prediction 是 statistical pattern，不是因果；`in_silico` perturbation 应作为 hypothesis generator 不是 final answer
- **Drug perturbation extrapolation**：pretrain corpus 没看过该 drug → embedding shift 可能 spurious
- **Cell state in disease that wasn't in pretrain**：例如某罕见 disease subtype；zero-shot 表现好可能是 hallucination
- **Fine-tune 不 freeze 时小 batch**：不冻结全部 + 12 batch size 容易 catastrophic forgetting；上小 batch 时必冻结
- **Embedding 当 ground truth pseudotime**：transformer embedding 不是 trajectory；要走 RNA velocity (rule 17) 等

## ★ 失败模式
- **Tokenize 时 rare gene 损失**：top-2048 token 截断，长尾基因丢；rare TF 在 cell state 中有作用但被截断 → 该 fine-tune 时调 max_length=4096
- **MLM (masked LM) pretrain 不等于 contrastive**：embedding 在 batch effect 上不天然鲁棒；finetune 还要 batch correct
- **Pretrain 物种偏 human 主**：~95% human + 5% mouse/rat；其他物种性能 dropoff
- **Zero-shot 在 disease-specific cell state 上失败**：罕见疾病 cell state 没在 pretrain 出现，embedding 集中到最近健康 state，掩盖 disease signal
- **Fine-tune metric overfit**：dev set leakage 极常见；按 sample/donor split 而非 cell split
- **GPU memory blow on long sequence**：max_length 增加内存平方涨；batch_size 必须降
- **In-silico KO false negative**：基因不在 cell 的 top-2048 token → KO 等于无 effect → 假阴
- **跨 dataset reproducibility 弱**：相同 cell type 在不同 lab 的 dataset 上 fine-tune 可能不一致

## ★ 方法选择决策链
```
Foundation model 应用?
├─ Zero-shot → 仅当任务 close to pretrain task
│   ├─ Cell type embedding → OK (Geneformer CLS token)
│   └─ Disease state classification → 不行 (need fine-tune)
├─ Fine-tune classification
│   ├─ < 1k cells per class → STOP，会 overfit
│   ├─ 1k-10k → freeze 底层，train head + 顶 6 层
│   └─ ≥ 10k → 全部 unfreeze
├─ In-silico perturbation → hypothesis only，不是 mechanism
└─ Cross-organism / cross-disease → adapter fine-tune 必做

Tokenize?
├─ rank-value encoding (Geneformer / scGPT 都用)
├─ max_length 2048 默认 → rare cell type 必试 4096
└─ NO log1p / scale 预处理 (rank 本身就 normalize)

Validation?
├─ Cell type embedding distance vs ontology distance
├─ In-silico KO vs published wet-lab KO 一致性
├─ Train/val split by sample/donor (not by cell)
└─ Compare to a from-scratch baseline (transfer learning vs random init)
```

## ★ QC sanity check (known answer)
- Anchor (Theodoris 2023 cardiomyocyte regeneration)：
  - **TBX5 在 cardiomyocyte 的 in-silico KO** → predicted "dilated cardiomyopathy" embedding shift；与 published TBX5 KO mouse phenotype 一致
  - **Cell type embedding distance**: CD4 vs CD8 < CD4 vs B-cell < CD4 vs cardiomyocyte
  - **Fine-tune 5k-cell binary classifier (disease vs healthy)** F1 ≥ 0.80 (vs random-init baseline F1 ≤ 0.65)
  - **Mouse zero-shot test**: domain-adapter fine-tune 后比 raw zero-shot ≥ 10% F1 提升
- Pass criterion: ontology-respecting embedding distance + KO 与文献一致
- Fail criterion: same-cell-type cluster mixed with very-different cell types → embedding 没学到 biology

## Lessons → seeds for rules
1. **Foundation model 是补充不是替代**：仍需走 rule 02-06 标准 QC + integration；FM 是 embedding/predictor，不是 pipeline
2. **Rank-value encoding 替代 normalize**：tokenize 时不要 log1p
3. **Cross-organism / cross-disease 必 fine-tune adapter**：zero-shot 不可信
4. **Fine-tune split 按 donor/sample 不按 cell**：避免 leakage
5. **In-silico perturbation 是 hypothesis** 不是 mechanism；wet-lab 验证仍是 gold
6. **Pretrain corpus check** 是 first sanity：你的 cell type / disease 在 pretrain 中表征如何？没有 → 警惕
7. **GPU 内存 + max_length 双约束**：设计实验时同时考虑
