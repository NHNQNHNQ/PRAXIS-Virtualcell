---
case_id: pharma-008-protein-binding-fu
task: plasma_protein_binding_assessment
target_compound: warfarin (highly protein bound, ~99% to albumin)
tools: [equilibrium dialysis, ultrafiltration, MS quantification, in silico predictors (PKCSM, ADMET-AI)]
key_paper_doi: 10.1016/j.bbagen.2013.05.005
status: validated
_doi_provenance: Yamasaki K et al. 2013 Biochim Biophys Acta 1830:5435 "Albumin-drug interaction and its clinical implication" — comprehensive review of plasma protein binding mechanism + clinical implications including warfarin's high-affinity albumin binding and DDI displacement risk.
---

# 血浆蛋白结合 fu：warfarin DDI + special population 关键

## Background
Plasma protein binding (PPB) 决定 free fraction (fu) — 只有 free drug active + clearable。Warfarin fu ~ 0.01 (99% bound to albumin)。**问题**：(1) DDI displacement (NSAIDs displace warfarin → free fu 升 → bleeding risk)；(2) hypoalbuminemia (liver/kidney disease) → fu 升；(3) species difference → cross-species PK extrapolation 错。

## What I actually did
1. **Equilibrium dialysis** （gold standard）：dialysis membrane separate plasma & buffer，平衡后 measure free vs total
2. **Ultrafiltration**：faster but suffer non-specific binding to membrane
3. **In silico predictor**：ADMET-AI / PKCSM 给 fu prediction，accuracy ~70-80%
4. **Concentration dependence**：non-linear binding → fu changes with concentration; test at 3-5 levels
5. **Species comparison**：human vs rat vs dog vs monkey fu，跨 species 可差 5-20×
6. **Disease state**：hypoalbuminemia plasma → in vitro spike test → fu shift 量化
7. **DDI displacement risk**：sequentially add competitor (e.g., aspirin) → fu rise
8. **Output**：fu_human + concentration dependence + species comparison + clinical implications

## ★ 排除/不做的事
- **Single concentration fu**：non-linear binding miss
- **Single method (only ultrafiltration)**：non-specific binding inflate fu
- **In silico predictor 当 final**：accuracy 不够 clinical decision
- **Species 直接 extrapolate**：fu 跨 species 差大，必须 measure each species
- **Disease state 不评估**：hypoalbuminemia / uremia / hyperbilirubinemia 改变 PPB
- **Forget alpha-1-acid glycoprotein (AAG)**：basic drugs bind AAG not albumin

## ★ 失败模式
- **Non-specific binding to plasticware / membrane**：apparent fu 偏高
- **Drug instability in plasma**：incubation 中 drug degrade
- **Active metabolite binding**：parent + metabolite 同时 binding，需分别 measure
- **Free fraction concentration too low to detect**：极 high binding (fu < 0.001) 难 measure
- **Endogenous interference**：albumin 富 fatty acid 或 bilirubin 时 binding 变
- **Multiple binding site competition**：site I + site II albumin 不同
- **Drug binds RBC**：plasma fu vs blood fu 不同

## Lessons → seeds for rules
1. **Equilibrium dialysis (gold) + ultrafiltration (fast) cross-check**
2. **Concentration range testing**
3. **Species-specific measurement**
4. **Hypoalbuminemia plasma testing**
5. **DDI displacement evaluation**
6. **AAG vs albumin** for basic vs acidic drug
7. **In silico predictor as triage** not final
