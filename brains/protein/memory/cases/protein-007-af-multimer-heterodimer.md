---
case_id: protein-007-af-multimer-heterodimer
design_task: complex_prediction
target_pdb: 1B41 (E.coli SecB-RBS)
target_uniprot: [P0AG86, P0AGD7]
fold_class: chaperone_complex
tools: [AlphaFold-Multimer 2.3, AlphaFold3, Boltz-1, Chai-1]
key_paper_doi: 10.1038/s41586-024-07487-w
status: validated
schema_version: 1
source: praxis_seed
extracted_at: 2026-04-29
---

# 异源二聚体预测：选 AF-Multimer / AF3 / Boltz-1 / Chai-1 的判据

## Background
AlphaFold-Multimer 2.3 是 2022-2024 年期间复合物预测主力；AF3（2024 Nature）+ Boltz-1（2024 开源）+ Chai-1（2024）后来居上。在异源二聚体 case 上各有所长——不能盲选。

## What I actually did
1. **建 input**：两条序列连 `:` 给所有 model；自动 paired MSA（AF-Multimer 用 `--use_paired_msa`）
2. **四模型并跑**：
   - AF-Multimer 2.3：5 model × 5 seed = 25 prediction
   - AF3（local）：default 5 seed
   - Boltz-1：开源 AF3-like，速度快 5x
   - Chai-1：开源，含 conditioning（pocket/contact 提示）
3. **Composite metric**：iPTM × pTM × pLDDT_mean — 取 top 5 prediction 进入 visual review
4. **Cross-model agreement**：4 个 model top 1 prediction 之间 RMSD < 3 Å = high consensus；> 5 Å = low confidence
5. **Interface 分析**：PISA 算 buried surface area（BSA），真复合物 BSA > 1000 Ų；< 600 Ų 通常假
6. **Validation**：1B41 是 known crystal，对齐验证 interface RMSD < 2 Å
7. **常见任务匹配**：transient interactions（signaling 动态复合物）AF 系列假阳率高；stable hetero-dimer（cofactor binding 等）准

## ★ 排除/不做的事
- **不用 paired MSA**：跨物种同源序列配对是 AF-Multimer 准确的关键；unpaired 等于猜
- **single seed/single model**：拒绝；至少 5 seed
- **复合物当 fusion protein 跑**（一条链）：interface 完全不准
- **用 AF2 monomer fold 两条链再 docking**：除非已知是 stable obligate 复合物且 docking 是显式目标，否则直接 multimer
- **iPTM 0.6-0.7 当作 negative**：是 ambiguous，需要看 BSA 与 cross-model agreement 综合
- **解读为 affinity**：iPTM 不是 KD；趋势可参考绝对值不可信

## ★ 失败模式
- **Antibody-antigen**：AF-Multimer 在抗体上 known fail（CDR H3）；用 IgFold + docking
- **Transient signaling complexes**（kinase-substrate）：MSA 浅，confidence 低也可能是 real biology
- **Order-of-magnitude size mismatch**：很大蛋白与小肽 (<20 aa)，小肽几乎随机定位
- **Symmetric homodimer 当 hetero**：会得到非对称结构，错
- **Membrane proteins**：膜环境缺失，TM helix 容易 splay 错位
- **Multi-state complexes**：AF 给单 conformation，dynamic complex 实际多 state
- **Cofactor-mediated dimerization**：cofactor 缺失下 interface 塌陷（如 NAD-bridge dimerization）

## Lessons → seeds for rules
1. **多 model 并跑**（AF-Multimer + AF3 + Boltz-1 任选 ≥ 2）取 cross-model agreement
2. **Paired MSA 强制**——unpaired 拒收
3. **3 个量化指标**：iPTM ≥ 0.6 + BSA ≥ 600 Ų + cross-model RMSD ≤ 5 Å
4. **Antibody/signaling 复合物 caveat**：AF 系列已知 weakness，flag
5. **Cofactor 列表必须出**：模型缺 cofactor 时下游验证警觉
6. **iPTM 不是 KD**：affinity 估计走 FEP / docking + MM-GBSA 路线
