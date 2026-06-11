---
case_id: pharma-001-allometric-scaling
task: cross_species_pk_scaling
input_compound: any small mol with rat PK
target_species: human
tools: [mrgsolve, R PKreport, GastroPlus, allometric scaling formulas]
key_paper_doi: 10.1007/BF01062336
status: validated
_doi_provenance: Boxenbaum H 1982 J Pharmacokin Biopharm 10:201–227 "Interspecies scaling, allometry, physiological time, and the ground plan of pharmacokinetics" — foundational paper for BW^0.75 allometric framework.
---

# Allometric scaling：从大鼠 PK 推 human first-in-human dose 估计

## Background
Allometric scaling = 用 body weight (BW) 跨物种 scale clearance / volume of distribution。Empirical formula：CL_human ≈ CL_rat × (BW_human / BW_rat)^0.75。**简单但常被滥用**：仅适合 well-stirred, hepatically cleared, low-extraction compound；对 renal、protein-bound、active-transported 不准。

## What I actually did
1. **Inputs**：rat single-dose IV PK, Cl_rat 20 mL/min/kg, Vd 2 L/kg
2. **Body weight allometric**：CL_human (mL/min) = CL_rat × (70/0.25)^0.75 = 20 × 70 = ~1400 mL/min for 70 kg human
3. **Maximum lifespan potential (MLP) correction**：long-lived species（人 vs 鼠）lower clearance per BW^0.75；mostly correct prediction
4. **Brain weight correction**：CNS-active drug 用 brain weight scale (b ~ 0.97)
5. **Single species → human**：低 confidence (factor 2-5x error)；**multi-species (mouse + rat + dog + monkey)** → 拟合 power law，confidence 升
6. **In vitro IVIVE 替代**：human hepatocyte / microsome CL_int → scale to in vivo CL → 比 allometric 更准
7. **Validation**：与 published human PK 比对 (e.g., warfarin known PK → see if rat allometric correctly predicts)
8. **Combined approach**：allometric + IVIVE + PBPK = best estimate

## ★ 排除/不做的事
- **Single rat PK → human single value**：无 confidence interval = misleading
- **Drugs with active transport**：efflux/uptake transporter 不 scale by BW
- **Renal-cleared drug**：scale by GFR not by BW^0.75 alone
- **Protein-binding 不一致**：fu_rat ≠ fu_human → CL_unbound difference
- **Allometric 对 non-linear PK**：non-linear (metabolism saturation) compound 不适用
- **BW^0.75 for everything**：not all PK params scale at 0.75；Vd 通常 1.0 (linear with BW)

## ★ 失败模式
- **Inter-species metabolism difference**：CYP isoform expression differ；prediction 偏
- **Active metabolite formation**：parent + metabolite combined PK 不 capture
- **Pharmacogenomics**：human CYP2D6 poor metabolizer (~5%) 完全不同 PK
- **Drug-drug interaction inducer**：ext PK in poly-pharmacy patient 不一样
- **Tissue distribution difference**：fat content, plasma protein 等 inter-species 不同
- **Linear / non-linear regime**：dose escalation 进 non-linear region 失败

## Lessons → seeds for rules
1. **Multi-species data > single-species**：≥ 3 species fit power law
2. **IVIVE + allometric** combined 最准
3. **Transporter / renal / protein-binding** flag for non-allometric compound
4. **Confidence interval 必报**（factor 2-5× 误差 typical）
5. **PK linearity check** in dose range
6. **Brain weight / GFR correction** for specific case
7. **Active metabolite** 单独 model
