---
case_id: protein-001-af3-rbd-spike-prediction
design_task: structure_prediction_complex
target_pdb: 6M0J (RBD-ACE2)
target_uniprot: [P0DTC2, Q9BYF1]   # P0DTC2 = SARS-CoV-2 spike full (RBD = domain 319-541); Q9BYF1 = human ACE2
fold_class: spike_RBM + protease
tools: [AlphaFold3, AlphaFold-Multimer 2.3, ESMFold, ColabFold, PyMOL, ChimeraX]
key_paper_doi: 10.1038/s41586-024-07487-w
status: validated
schema_version: 1
source: praxis_seed
extracted_at: 2026-04-29
---

# RBD-ACE2 复合物预测：AF 系列工具的对比与陷阱

## Background
SARS-CoV-2 RBD（Spike receptor binding domain，~200 aa）与人 ACE2 的复合物（PDB 6M0J）是反复用于 benchmark 的接口预测案例。RBD 突变（Omicron 等）改变 ACE2 亲和——是评估"AF 能否捕捉 affinity-modulating mutation"的标准。

## What I actually did
1. **三个工具并跑**：
   - AlphaFold3（webserver/local with weights）：default seed=1
   - AlphaFold-Multimer 2.3（local 5 model + 5 seed = 25 prediction）
   - ESMFold：单链 RBD only（不支持 multimer）
2. **MSA 控制**：AF3 默认拉 UniRef90+BFD+MGnify；AF-Multimer 用 paired MSA（关键！unpaired 会让 interface 预测崩）
3. **关键 metric**：
   - **iPTM > 0.85**（RBD-ACE2 真复合物预期）
   - **pAE_interface（界面残基对的 PAE）< 5 Å**——比单 pLDDT 更可靠
   - 全长 pLDDT > 80
4. **结构验证**：与 6M0J 比对（PyMOL `align`），interface RMSD < 1.5 Å
5. **Mutant 测试**：N501Y（Alpha）、E484K（Beta）跑同样流程，看 iPTM 变化是否与已知亲和变化同方向（AF3 trend 相对 OK，绝对值不准）
6. **结构对齐 rapid screen**：Foldseek vs PDB 100% TM-score → 找到正确 6M0J、6LZG 等同源

## ★ 排除/不做的事
- **AF-Multimer 不用 paired MSA**：界面接触面预测错位，iPTM 会假高（自身链对自身评估）但实际乱
- **只信 pLDDT**：interface 处单链 pLDDT 都高但相对位置可能完全错——必须看 pAE_interface
- **Single seed/single model**：高 confidence prediction 也要 ≥ 5 seed，挑 top by composite score（iPTM × pLDDT mean）
- **不验证 MSA depth**：< 30 sequence MSA 的预测置信度暴跌（病毒序列容易，新设计蛋白可能 MSA 深度不够）
- **当成定量亲和预测**：AF3 的 iPTM 不是 KD；趋势可信，绝对值不可信
- **混 ESMFold 做 multimer**：ESMFold 不支持 multimer，硬拼接两条链会得到伪结构

## ★ 失败模式
- **Domain swapping/flexible linker 区段** pLDDT 低：不是 AF 错，是该区段确实柔性——别强行 cluster pose
- **Glycosylation 影响**：AF3 不放糖，spike 的 glycan 屏蔽不在结构里——下游 docking/MD 时要补
- **Cofactor 缺失**：金属/血红素/底物 AF3 部分支持但不稳定，复合物常见的关键辅基缺失会让 active site 塌陷
- **Antibody-antigen 接口**：AF-Multimer 在抗体 case 假阴率 > 50%（CDR loop 柔性 + MSA 浅）；要用专门 IgFold/AbodyBuilder 后再 docking
- **Interface 错配但 iPTM 高**：尤其 helical bundle interface，错位 helix 拼接也能给高 iPTM——视觉验证不可省

## Lessons → seeds for rules
1. **复合物预测三件套指标**：iPTM ≥ 0.85 + pAE_interface ≤ 5 Å + pLDDT mean ≥ 80。三个都过才算 high confidence
2. **Multimer 必须 paired MSA**——否则 interface 等于乱猜
3. **多 seed/多 model 投票**（≥ 5），挑 composite score top
4. **AF3 不出 affinity**——它出 confidence，affinity 估计需 FEP 或 docking + MM-GBSA
5. **抗体复合物用专 tool**（IgFold + AbodyBuilder + docking 链路）而非 AF-Multimer
6. **Glycan/cofactor 缺失意识**：AF3 输出后必须人工列出"模型里缺什么"
