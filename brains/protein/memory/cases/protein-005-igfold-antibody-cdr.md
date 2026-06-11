---
case_id: protein-005-igfold-antibody-cdr
design_task: antibody_cdr_modeling
target_pdb: 7K9I (anti-SARS-CoV-2 RBD ab)
target_uniprot: nan (custom Ab)
fold_class: immunoglobulin
tools: [IgFold, ImmuneBuilder, AbLang2, AntiBERTy, AlphaFold-Multimer, Rosetta SnugDock]
key_paper_doi: 10.1038/s42003-023-04927-7
status: validated
schema_version: 1
source: praxis_seed
extracted_at: 2026-04-29
---

# 抗体 CDR 建模：IgFold + 序列模型联用，避免 AF-Multimer 在抗体 case 的盲区

## Background
抗体 fold 高度保守（Ig fold），但 CDR loop（特别 H3，长度 5-30 aa）柔性极大、AF-Multimer 在抗体上 known fail。抗体专用模型（IgFold/ImmuneBuilder）训练数据全是 antibody 结构，CDR 准确率显著优于通用 AF。

## What I actually did
1. **Numbering**：序列经 ANARCI 转 Chothia/Kabat numbering 标准化
2. **IgFold predict**：3 model 集成、~10 秒/Ab，输出 backbone + per-residue confidence（CDR 处通常 1-2 Å RMSD wrt crystal）
3. **ImmuneBuilder 平行跑**：第二个 antibody-specific predictor，CDR 预测取交集
4. **AbLang2 生成**：humanization / 序列 design 时用 antibody language model 推荐残基替换（保 framework 人性化）
5. **AntiBERTy** 评估序列 likelihood：异常 CDR 序列（non-natural 模式）log-likelihood 显著低 → flag review
6. **Antibody-antigen complex**：IgFold 出 Fv → AF-Multimer (Fv + antigen) **with paired MSA + initial guess**；或 Rosetta SnugDock 主动 docking
7. **CDR H3 specifically**：长 H3（>15 aa）所有方法 RMSE > 2 Å，需 ensemble + Rosetta refinement

## ★ 排除/不做的事
- **直接 AF-Multimer 跑 Ab-Ag 不预 CDR**：AF 在抗体 framework 准，但 H3 + interface 假阳率 > 50%；先 IgFold 出 Fv 再 docking
- **不做 numbering 标准化**：CDR 定义会偏，下游所有比较失效
- **CDR H3 信任 single model**：H3 长 loop 是 antibody 难点，必须 ensemble + 物理 refinement
- **Humanization 不用 antibody-specific LM**：通用 ESM 给的人性化建议不达标——AbLang2 才是
- **复合物不验证 epitope**：模型可能 dock 到错 paratope；要看 CDR vs framework 哪边贡献接触面

## ★ 失败模式
- **CDR H3 长度极端**（> 20 aa）：所有 antibody-predictor RMSE > 3 Å；这种 case 必须 X-ray/cryoEM 真实结构
- **轻链 V/J 错配**：lambda vs kappa light chain 混了，模型给伪结构
- **Glycosylation 在 framework**：N-glycan 在 CH2 等区段的影响 IgFold 不建模——影响 effector function 评估
- **Multi-specific Ab（bispecific）**：当前模型默认 monospecific Fv，bispecific scaffold 需另设
- **Non-natural amino acid CDR**（药物级 antibody-drug conjugate 等）：所有 ML 模型 OOD
- **Antibody-antibody interaction**（HMW aggregates）：单分子模型不评估自相互作用

## Lessons → seeds for rules
1. **抗体用专 tool**：IgFold/ImmuneBuilder/AbLang2 而非通用 AF/ESM
2. **Numbering 标准化是 step 0**（ANARCI Chothia 或 Kabat）
3. **CDR H3 > 15 aa 标 low confidence**——所有方法这里都不准
4. **复合物 = IgFold 出 Fv → 再 AF-Multimer 或 SnugDock**，不一步到位
5. **Humanization 用 antibody-LM**（AbLang2）评估候选
6. **Effector function（FcγR/C1q binding）单独评估**：framework 模型不直接给
