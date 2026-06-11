---
case_id: synth-009-strain-engineering-ko
task: strain_engineering_for_production
target_compound: lysine (industrial scale)
host_organism: Corynebacterium glutamicum (industrial workhorse)
tools: [OptKnock, OptStoic, iCW773 model, COBRA Toolbox, Cameo]
key_paper_doi: 10.1002/bit.10803
status: validated
---

# Lysine 生产菌种工程：OptKnock 推荐 KO 组合

## Background
Lysine 是大宗 amino acid 工业产品（饲料添加剂）。Corynebacterium glutamicum 是天然 producer。OptKnock 是 mathematical optimization 找 "KO 哪几个 gene 让 lysine 与 biomass 强 coupled"——cell 必须产 lysine 才能 grow。

## What I actually did
1. **Model**：iCW773 C.glutamicum genome-scale model
2. **Define objective**：max lysine production
3. **OptKnock formulation**：bilevel MILP → outer max product flux, inner cell max biomass flux subject to KO
4. **KO set size limit**：3-5 KOs (实际 strain engineering feasible 上限)
5. **Top KO sets**：典型 OptKnock 给 5 个 KO combo each predicted lysine yield
6. **Manual review**：逐 KO 是否实际可行（essential gene 不能 KO；regulatory gene 不能 KO）
7. **Wet lab validation**：构造 KO mutant → fermentation → measure lysine titer
8. **Iterative**：实测 vs predicted 差距 → refine model + new OptKnock round
9. **Scale-up considerations**：小 scale optimal vs industrial scale 不同 (oxygen transfer, fed-batch dynamics)

## ★ 排除/不做的事
- **Single KO trial**：industrial production 几乎都 multi-KO
- **不限 KO size**：> 7 KO 实际不可行（每 KO 时间 + cost 累积）
- **OptKnock predicted essential KO**：outer optimization 不知 essential，需手动 audit
- **不做 manual review**：math optimal ≠ biological feasible
- **跳过 in silico → in vivo gap**：FBA prediction 与实际 yield 通常 30-50% gap
- **Single OptKnock seed**：multiple seed run 取 robust solution

## ★ 失败模式
- **Promoter / regulator bypass**：KO 后 cell 通过 regulatory rewiring 部分 compensate
- **Co-factor balance**：OptKnock 关注 carbon flux but NADPH balance 同等重要
- **Toxicity at high product titer**：lysine 高浓度抑制 own biosynthesis
- **Substrate uptake limit**：optimization 假设 substrate unlimited 但实际 transporter 限速
- **Model gap**：iCW773 不含 all reactions，predicted KO 可能 hit 模型外 essential
- **Strain stability**：long fermentation 中 mutant 不稳

## Lessons → seeds for rules
1. **Multi-KO (3-5) optimization** > single KO
2. **OptKnock + manual review**
3. **Co-factor balance check** alongside carbon flux
4. **Predicted vs actual gap**：30-50% common
5. **Iterative model refinement** with experimental data
6. **Scale-up considerations** at design stage
7. **Strain stability monitoring** over generations
