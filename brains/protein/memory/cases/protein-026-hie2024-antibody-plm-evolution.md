---
case_id: protein-026-hie2024-antibody-plm-evolution
design_task: antibody_design
target_pdb: 6M0J                   # SARS-CoV-2 spike RBD - one of antigens in cohort
target_uniprot: P0DTC2             # SARS-CoV-2 spike (representative target in cohort)
fold_class: immunoglobulin
length_range: 110-130
tools: [ESM-1v, ESM-2, protein_language_model, single_round_evolution, BLI, ELISA]
key_paper_doi: 10.1038/s41587-023-01763-2
key_metrics:
  antibodies_evolved: "approx 7 mature human antibodies tested"
  affinity_improvement: "average 2-7x KD improvement over starting antibody"
  rounds_to_improvement: "1 single round (no directed evolution loop)"
  best_KD_improvement: "ebola GP antibody: ~7-fold KD improvement"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [antibody, language-model, ESM, single-round-evolution, affinity-maturation, training-free]
unverified_details:
  - "Specific 2-7x KD improvement is paper-claimed range; per-antibody varies"
  - "Tested antibodies span SARS-CoV-2, ebola GP, others (full list in supp)"
---

# Antibody affinity maturation via PLM zero-shot（Hie et al. Nat Biotech 2024）

## Background
- 起点：抗体 affinity maturation 通常通过 phage display + multiple selection rounds（month-long, expensive）
- 目标：用 general protein language model (ESM-1v / ESM-2) 在 zero-shot 设置下预测哪些 CDR 突变会提升亲和——单轮 evolution，不需要训练任何 antibody-specific model
- 应用：突破"必须深度 evolution loop"的成本瓶颈；展示 PLM 在结构未必参与的进化任务上的预测能力

## What I actually did（基于论文）
1. **Starting antibodies**：~7 mature human antibodies（已经过 in vivo affinity maturation）；针对 SARS-CoV-2 RBD, ebola GP 等 viral targets
2. **PLM masked LM scoring**：
   - 输入抗体 sequence
   - mask 每个 position
   - 预测每位置的 amino acid distribution
   - 比 wild-type aa probability ratio 高的位置 = candidate site
3. **Top-N candidates**：对每抗体 pick ~10-20 single-point mutations（最高 PLL ratio）
4. **In silico → in vitro**：所有 candidate 单点突变都做实测（不用 deep selection）
5. **Validation**：mammalian display + BLI 测 KD vs WT
6. **结果**：average 2-7x KD improvement 跨 7 抗体；ebola GP 抗体最佳 7x KD
7. **关键观察**：PLM identifies improved variants 即使在已经 mature 的抗体上 — 因为 PLM 看到比 in vivo 进化更广的"可能 variant 空间"

## ★ 排除的位点/区域
- **Framework regions**：本论文 focus on CDRs；FR 不动
- **Disulfide bonds**：保留
- **Conserved framework residues**：W36, Y36 类 fold-critical 不动
- **CDR-H3 长度变异**：本论文不改 CDR length，只 single-point mutation
- **N-glycosylation 位点**：保留
- **Asn deamidation hotspots (NG, NS)**：可能引入但论文未明显 filter

## ★ 失败模式
- **某些 candidate 突变实测 KD 反而下降**：~30% candidates 实测 KD 增加（worse），尽管 PLL 高
- **PLM 没建模具体抗原**：generic protein LM 不知道 paratope-epitope 几何；某些 mutation PLL 高但破坏特定 antigen 结合
- **Specificity 漂移**：单点 mutation 偶尔增加 off-target binding（不是本论文 main metric）
- **Already over-matured antibody（picomolar）变化更小**：起点亲和越高，提升空间越小（diminishing returns）
- **某些 CDR-H3 长度变异不能解决**：仅 single-point；deletions/insertions 不在 design space
- **PLM 偏向 "natural" amino acid frequency**：更偏向常见 aa，可能错过 rare-but-effective 突变（如 Trp or Cys 引入）

## ★ 方法选择决策链
- **为什么 ESM PLM 而非 antibody-specific LM**：generic PLM 训练数据 (>10^9 protein sequences) 远多于 antibody-specific； zero-shot 性能 surprisingly OK
- **为什么 single-round 而非 deep evolution**：cost + time；论文证明 PLM 已经 capture 大部分 useful single-point improvement
- **为什么 mask + PLL ratio 而非 direct binding prediction**：mask LM 是 PLM 的 native task；不需要训练 antibody-specific predictor
- **为什么 7 抗体 cohort**：generalization 验证；跨 viral/cancer/cytokine 各类 antigen
- **为什么 BLI 验证 而非 ELISA**：BLI 量化 KD（ELISA 仅 qualitative binding signal）

## ★ In silico vs in vitro 差距
- **In silico top PLL → 实测 KD ≤ WT**（即 binding 不变差）：~70%
- **In silico top PLL → KD 提升 ≥2x**：~30%
- **In silico top PLL → KD 提升 ≥7x**：rare (~5%, single antibody)
- **总有用率（in silico → useful improvement）**：~30%
- **vs case 025 (Mason 2021 DL specificity 1.5%)**：Hie 高约 20x 因为是 affinity-only 任务（不要求 specificity 同时改变）+ single-point 难度低
- **vs traditional directed evolution multiple rounds**：1 round PLM 提升 ~2-7x；3 rounds DE 通常 10-100x。PLM 不替代 DE，是 cost-efficient first pass
- **No standard pLDDT/iPTM/Rosetta_ddG**：纯 sequence-based PLM scoring + BLI KD

## Lessons → seeds for rules
1. **PLM zero-shot 在 antibody affinity 上 surprisingly effective**——generic protein LM 而非 antibody-specific
2. **Single-point + single-round** 已可拿到 2-7x KD 提升——cost-efficient first iteration
3. **mask LM PLL ratio** 是简洁 + interpretable 的 mutation prioritization 信号
4. **Already mature antibody diminishing returns**：picomolar 起点 → 提升 < 2x typical
5. **PLM 不知道具体 antigen geometry**：~30% PLL-high 突变破坏特定 antigen binding——结构未参与是 limitation
6. **No specificity guarantee**：single-point 可能引入 off-target
7. **PRAXIS implication**：mutation_effect_scan 在 antibody 任务上可加 ESM-1v/ESM-2 mask LM 作为额外 predictor（已经在 esmfold env 中）；rule 01 multi-method consensus 可包含 PLM

## 数据指针
- 论文 + supp: https://doi.org/10.1038/s41587-023-01763-2
- 7 抗体序列 + KD measurements 在 supp Table
- ESM-1v / ESM-2 模型: facebook/fair-esm GitHub
