---
case_id: protein-008-esmfold-throughput
design_task: high_throughput_structure_prediction
target_pdb: nan
fold_class: any
tools: [ESMFold, OmegaFold, AlphaFold2 reduced_dbs, ColabFold]
key_paper_doi: 10.1126/science.ade2574
status: validated
schema_version: 1
source: praxis_seed
extracted_at: 2026-04-29
---

# ESMFold 高通量结构预测：100k 序列怎么跑

## Background
对 metaproteomics、de novo 设计候选库（10k-1M 序列）做结构预测时，AF2 因 MSA 计算慢（每序列分钟级）不可行。ESMFold 单 GPU 跑 10s/序列，无 MSA。Lin 2023 Science 论文用 ESMFold 跑了 ESM Atlas（600M+ 序列），是 throughput-precision tradeoff 案例。

## What I actually did
1. **Triage by length**：< 200 aa 用 ESMFold（GPU mem 11 GB enough）；200-700 用 OmegaFold（更低显存）；> 700 必须 AF2 reduced_dbs 否则不准
2. **Batch 化**：input fasta → batch by length bucket（<100, 100-200, 200-400）减少 padding 浪费
3. **GPU 资源估算**：A100 40GB ≈ 1200 sequence/h（150 aa 平均）；H100 ≈ 3000/h
4. **Quality control gate**：
   - pLDDT mean > 70 → keep
   - 50-70 → review（可能 partial fold）
   - < 50 → discard 或标 IDP/disordered
5. **Selection downstream**：高 pLDDT 候选才能进 docking/binder design / functional analysis
6. **复盘 vs AF2**：ESMFold 与 AF2 在 high-MSA-depth 蛋白 TM-score 平均 0.85；在 orphan / single-sequence ESM 反而比 AF2 better（AF2 缺 MSA 也跨）
7. **处理失败**：超过 model context length（~1024 aa）的蛋白要 chunk 或 fallback AF2

## ★ 排除/不做的事
- **ESMFold 跑 multimer**：不支持，硬拼接给伪复合物
- **依赖 ESMFold 评估突变 effect**：单点 mutation effect ESMFold 太粗（pLDDT 几乎不变）；用 ThermoMPNN 等专 mutation tool
- **不做 length triage**：均匀 batch 浪费 GPU mem
- **pLDDT < 50 当 IDP 自信**：可能是 orphan + folded 但模型不会
- **跨 organism domain decompose**：ESMFold 对 multi-domain 蛋白有断点 fold 错误的倾向
- **跳过 disorder predictor 联合验证**：单 pLDDT 不区分 "model fail" vs "intrinsically disordered"——加 IUPred / flDPnn

## ★ 失败模式
- **Coiled coil / repeat protein**：pLDDT 高但 register（哪个螺旋对哪个）可能错
- **Extreme multi-domain**：ESMFold 给整体 fold 但 domain orientation 不可信（缺 inter-domain MSA）
- **Cofactor-dependent fold**：apo 形态可能正确但 holo 才是 native
- **Out-of-distribution sequences**（合成蛋白、非天然 aa）：模型 OOD 不报警
- **GPU OOM**：长蛋白突然爆显存——必须 length-sorted batch
- **Numeric instability**：fp16 在某些序列上 NaN，需 fp32 fallback

## Lessons → seeds for rules
1. **Throughput task 用 ESMFold**，但小 task / multimer / mutation effect 不用
2. **Length-bucketed batching**：节省 GPU mem
3. **pLDDT-based triage gate**：< 50 标 IDP-or-fail，需 disorder predictor 区分
4. **ESMFold ≠ AF2**：domain orientation、cofactor、multimer 是已知短板
5. **GPU 资源公式**：~1000 sequence/h on A100，按这个估
6. **Out-of-distribution 警告**：query 序列与 ESM2 训练分布偏离（罕见 aa 频率）需 flag
