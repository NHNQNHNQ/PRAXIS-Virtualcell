---
case_id: protein-022-ingraham2023-chroma
design_task: hallucination_de_novo
target_pdb: nan
target_uniprot: nan
fold_class: any
length_range: 50-1000
tools: [Chroma, Generative_Diffusion_Model, Conditional_Generation, ESM-2]
key_paper_doi: 10.1038/s41586-023-06728-8
key_metrics:
  scale: "designed proteins from 50 to 3000+ aa"
  conditional_generation_modes: "fold prompt, symmetry prompt, motif scaffolding, function annotation"
  experimental_validation_passes: "31 designs, ~50% folded as predicted by various assays (CD + mass spec + SAXS + NMR + X-ray subset)"
  novel_topologies_in_diversity_set: "yes; multiple fold types not seen in CATH database"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [generative-model, diffusion, conditional-generation, multi-scale, novel-fold, Chroma, programmable]
unverified_details:
  - "31 designs validated; specific 50% pass rate is approximate from supp"
  - "Length range 50-3000 aa is from paper claim; very long designs (1000+) are challenging in vitro"
---

# Chroma: programmable generative model for protein design（Ingraham et al. Nature 2023）

## Background
- 起点：之前 protein design tools（RFdiffusion, hallucination）多 focused on small fragments；scaling to large + diverse design space + conditional generation 是开放问题
- 目标：建立 single generative model（Chroma）支持：
  - Length scale 50-3000+ aa
  - Fold-conditional generation
  - Symmetry-constrained generation
  - Motif scaffolding
  - Function annotation conditioning
- 应用：与 RFdiffusion 是同期 + 互补的 generative model；Generate Biomedicines 公司核心工具

## What I actually did（基于论文）
1. **Architecture**：noise-conditioned diffusion model 在 protein backbone (Cα + sidechain torsion) 上；conditional inputs 通过 cross-attention 注入
2. **Training**：PDB + UniRef + ESM-2 embeddings 联合训练（混合 supervised structure + unsupervised sequence）
3. **Conditional modes**：
   - Unconditional generation (sample diverse structures)
   - Length-conditional (fixed L)
   - Fold prompt (prompt with fold class label)
   - Symmetry prompt (Cn / Dn / Tn)
   - Motif scaffolding (fix subset of residues)
   - Function annotation prompt (e.g. "kinase", "GPCR")
4. **Generation**：~10^4-10^5 designs across length scales + symmetry types
5. **Selection**：filter by predicted pLDDT + structural diversity + symmetry consistency
6. **In vitro 验证**：31 selected designs 跨 multiple modes
7. **Validation**：CD（secondary structure）+ SEC（monomer/oligomer state）+ mass spec + 部分 SAXS / NMR / X-ray subset
8. **结果**：~50% 设计 fold as predicted；novel topologies (some not in CATH)；长设计 (>500 aa) 表达 / fold 难度大

## ★ 排除的位点/区域
- **过长设计 (> 1000 aa)**：在 vitro 表达 challenging；论文中 ~50% 不可溶
- **Conditional 不一致**：fold prompt + length 必须 compatible（不能要 100 aa TIM-barrel）
- **跨膜段 / 信号肽**：default 不生成
- **极端 disulfide pattern**：未训练 enforce specific Cys-Cys 配对
- **Modified residues / non-standard aa**：不 supported
- **Small motifs (< 30 aa)**：扩展空间太小，diffusion 易 collapse 到 trivial pattern

## ★ 失败模式
- **CD 显示 unstructured**：~30-40% 设计在 CD 上没有清晰 helix/sheet；diffusion confidence ≠ in vitro fold
- **SEC 多聚 / aggregate**：~25% 在 SEC 上多峰
- **Length > 500 aa 表达失败**：~50% 不可溶（mini-protein 易表达，长设计难）
- **Conditional fidelity issues**：fold prompt "TIM-barrel" 输出有时不是 TIM-barrel——条件 conditioning 不严格 enforce
- **Symmetry breaking**：~20% C3 设计在 SEC 上是 dimer / hexamer
- **跨 length 转化率不均**：50-200 aa 高，500-1000 aa 中，1000+ aa 低
- **Function annotation prompt 验证有限**：论文没全面评估 function-conditioned designs 的 functional activity

## ★ 方法选择决策链
- **为什么 diffusion 而非 hallucination**：diffusion 提供 explicit denoising trajectory + density modeling；可 do conditional generation cleanly
- **为什么 mixed supervised + unsupervised training**：sequence-level ESM-2 embedding 给 generative model 隐性 evolutionary prior
- **为什么 Chroma 比 RFdiffusion 灵活**：Chroma multi-modal conditioning（fold + symmetry + function 一起）；RFdiffusion 当时主要针对 binder + symmetry
- **为什么 31 design in vitro 而非更多**：cost + time；focus on diversity rather than per-design 验证
- **为什么 multi-modality validation (CD + SEC + SAXS + NMR + X-ray)**：每 modality 检测不同 failure mode；CD 看 secondary，SEC 看 oligomer，SAXS 看 globular，NMR / X-ray 看 unique fold

## ★ In silico vs in vitro 差距
- **In silico → CD pattern correct**：31 → ~22 (~71%)
- **CD correct → SEC monomer**：~22 → ~17 (~77%)
- **SEC monomer → unique fold (NMR/X-ray)**：~17 → ~15 (~88%)
- **总转化率**：~15/31 ≈ **48%**
- **vs case 015 (Anishchenko hallucination 27%)**：Chroma 比 trRosetta hallucination 高约 1.7x
- **vs case 002 (RFdiff binder 5-15%)**：Chroma fold-only 任务转化率显著高（因为没加 binder 要求）
- **No standard pLDDT/iPTM/Rosetta_ddG**：fold + diversity 任务，主 metric 是 structure-prediction confidence (Chroma 自己的) + CD/SAXS

## Lessons → seeds for rules
1. **Diffusion + conditional generation > pure hallucination**：可 do clean fold/symmetry/motif/function 联合 conditioning
2. **Mixed supervised + unsupervised training**：sequence ESM-2 prior 提升 generative quality
3. **Multi-modality validation 必要**：CD + SEC + SAXS + NMR/X-ray subset
4. **48% fold-correct rate 是 generative model 在 fold-only 任务上的 SOTA baseline**
5. **Length scaling 是 hard**：500+ aa designs 表达 / fold 难度大
6. **Conditional fidelity 不严格 enforce**：fold prompt → output not always exact fold
7. **Function-conditional 验证不充分**：function annotation prompt 在论文中验证 limited——开放 question
8. **PRAXIS implication**：predict_structure_monomer 可加 Chroma 作为 alt structure prediction model；hallucination_de_novo skill 可同时用 Chroma + RFdiffusion 跨工具 ensemble

## 数据指针
- 论文 + supp: https://doi.org/10.1038/s41586-023-06728-8
- 代码 + 模型 (开源 + 商业混合): https://github.com/generatebio/chroma
- 31 设计验证 PDB IDs / 数据 在 supp materials
