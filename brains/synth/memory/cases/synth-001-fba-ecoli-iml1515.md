---
case_id: synth-001-fba-ecoli-iml1515
task: flux_balance_analysis
host_organism: E. coli K-12 MG1655
model: iML1515 (Monk 2017, 1515 genes)
tools: [COBRApy, Cameo, escher visualization, OptKnock, MEMOTE]
key_paper_doi: 10.1038/nbt.3956
status: validated
---

# E.coli iML1515 FBA：metabolic engineering 基础

## Background
iML1515 是 E.coli MG1655 genome-scale metabolic model 当前 standard：1515 genes, 2719 reactions, 1192 metabolites。FBA (Flux Balance Analysis) 是 metabolic engineering 第一道工具——预测 KO / 上调 / 培养条件下细胞 growth + 代谢 flux。

## What I actually did
1. **Load model**：`cobra.io.read_sbml_model('iML1515.xml')`
2. **Default condition**：M9 minimal + glucose 10 mmol/gDW/h；O2 unlimited
3. **Optimize biomass**：`model.optimize()` → growth rate (~0.88 1/h aerobic glucose)
4. **Single gene KO scan**：`single_gene_deletion(model)` → 每 gene KO 后 growth rate；essential = growth ≤ 1% WT
5. **Pathway flux**：例如 lysine 生产 → set lysine demand reaction objective + co-optimize biomass + lysine
6. **OptKnock**：找最大 lysine + biomass tradeoff 的 KO set（typical 3-5 KO for industrial scale）
7. **MEMOTE quality check**：model 一致性 / mass balance / charge balance
8. **Validation**：predicted essential genes 与 Keio collection (real KO library) 比对

## ★ 排除/不做的事
- **跑 FBA 不 verify model with MEMOTE**：损坏 model 给 misleading prediction
- **Default reaction bound 不 audit**：max_lower_bound 错让 reaction 反向，predict 错
- **Single objective only**：实际 metabolic engineering multi-objective（biomass + product + co-factor）
- **KO 对 essential gene 不警告**：KO essential 让 growth = 0 = pipeline failure
- **不做 Pareto frontier**：只拿 max product 不显示 vs biomass tradeoff
- **Model strain mismatch**：iML1515 是 K-12，BL21 / W3110 略不同，need stra-specific model

## ★ 失败模式
- **FBA assumption 简化**：steady-state + linear，不抓 dynamics、enzyme kinetics、regulation
- **Substrate uptake bound 决定一切**：limit glucose uptake → 限 max growth；real cell 受 transporter capacity
- **Predicted essential vs experimental discrepancy**：~10% genes 模型预测 essential 但实际不（compensate by other path）
- **Aerobic vs anaerobic mode**：O2 bound 决定 metabolism type
- **Co-factor balance**：NADH/NADPH balance 是 metabolic engineering 关键，FBA 不直接显示
- **Gene-protein-reaction (GPR)**：复杂 GPR (isozyme + complex) KO 需谨慎解读

## Lessons → seeds for rules
1. **MEMOTE QC** before FBA 必步
2. **Multi-objective**：biomass + product + co-factor balance
3. **KO 对 essential 警告**
4. **Pareto frontier** for product-vs-biomass tradeoff
5. **Strain-specific model**（iML1515 for K-12, iJN1463 for Pseudomonas etc.）
6. **Substrate uptake bound 显式 audit**
7. **Validate vs Keio** (or relevant strain KO library)
