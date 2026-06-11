---
case_id: drug-005-aizynth-retrosynthesis
project_phase: hit_id_to_lead
target_uniprot: any
target_class: any
modality: small_mol
representative_compound:
  - name: imatinib
    chembl_id: CHEMBL941
    smiles: Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc1nccc(-c2cccnc2)n1
    inchikey: KTUFNOKKBVMGRW-UHFFFAOYSA-N
tools: [AiZynthFinder 4.0, Syntheseus, ASKCOS, RDKit, Reaxys (commercial)]
key_paper_doi: 10.1186/s13321-020-00472-1
status: validated
validated: true
source: praxis_seed
---

# AiZynthFinder：候选分子的合成可达性评估

## Background
Generative model 设计的分子如果合成 ≥ 8 步、要罕见起原料、需特殊试剂——实际不可成。AiZynthFinder 是开源 retrosynthesis tool，搜索可购起原料 (eMolecules / Enamine BB) 到目标分子的 ≤ N 步路径。Imatinib 是经典 case：实际 industrial synthesis 5-7 步，AiZynth 应能复现。

## What I actually did
1. **Run AiZynth on imatinib SMILES**：default policy network + filter network + value function
2. **Output**：top routes ranked by combined score（length + commercial availability + 反应类型可行性）。Imatinib 通常给 5-6 步路径，最后步是 amide coupling
3. **路径合理性 review**：
   - 反应类型分布：amide coupling、Suzuki、SNAr、Buchwald 等常见反应是 OK 的
   - 罕见反应（exotic photoredox / 罕见金属催化）路径 confidence 降
   - 起原料需 commercial（CAS 在 eMolecules 库中）
4. **Filter 应用到 candidate library**：1000 generated candidates → AiZynth → 仅 ≤ 6 步 + commercial 起原料 = pass。典型通过率 30-60%（视 generative model 训练数据）
5. **SAscore 与 AiZynth 一致性**：SAscore < 4 通常对应 AiZynth ≤ 6 步；SAscore > 6 几乎都 AiZynth 不出路径。但 SAscore 是 quick proxy，不替代 AiZynth full search

## ★ 排除/不做的事
- **只用 SAscore 不跑 AiZynth**：SAscore 是 heuristic，对 macrocycle / 多手性中心 系统不准
- **路径不评估反应可行性**：AiZynth 给路径不等于 wet lab 必成；某些 Buchwald 反应在特定 substrate 收率 < 5%
- **起原料不限 commercial**：路径要求 specific intermediate 不在 catalog，等于实际从更深起原料合成，步数低估
- **多手性中心忽略**：synthesis 路径需 stereo control，AiZynth 多数 policy 不考虑 stereo selectivity
- **保护基忽略**：合理路径常需 protect/deprotect；AiZynth 给的 minimal step 可能 missing protection chemistry
- **不评估 yield 与 cost**：5 步可能 overall yield 1%，理论可合实际不经济

## ★ 失败模式
- **Out-of-distribution chemistry**：罕见 heterocycle、binuclear metal complex 等，AiZynth policy network OOD
- **Macrocycle / large ring**：环化反应难，AiZynth 常给不出
- **Atropisomer 控制**：阻转异构（biaryl）需特殊条件，路径不显式
- **Late-stage diversification**：从一个 advanced intermediate 加 substituent——AiZynth 默认 disconnect 整个分子
- **Patent literature 命中**：某些 candidate 已有专利合成路径但 AiZynth 训练数据没包括（USPTO post-2018 缺）
- **Stoichiometry / scalability**：克级 vs 公斤级合成路径不同，AiZynth 不区分

## Lessons → seeds for rules
1. **Generative pipeline 必走 retrosynthesis filter**，仅 SAscore 不够
2. **路径长度阈值**：≤ 6 步推荐；7-8 步 review；> 8 reject
3. **反应类型分布检查**：> 80% 经典反应 (amide, Suzuki, SNAr, alkylation, reduction) = high confidence
4. **起原料 commercial 校验**：eMolecules / Enamine BB / Sigma catalog
5. **多手性中心 caveat**：≥ 3 手性中心需人工 review stereo control 路线
6. **Yield / cost 估计是 commercial chemistry 工作**，不靠纯 AiZynth
