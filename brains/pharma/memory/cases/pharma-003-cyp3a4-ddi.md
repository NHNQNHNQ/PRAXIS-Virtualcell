---
case_id: pharma-003-cyp3a4-ddi
task: drug_drug_interaction_prediction
substrate_drug: simvastatin (CYP3A4 substrate, narrow therapeutic index)
perpetrator_drug: clarithromycin (CYP3A4 strong inhibitor)
tools: [Simcyp DDI module, PK-Sim, FDA DDI guidance flowcharts]
key_paper_doi: 10.2165/00003088-200241050-00003
status: validated
_doi_provenance: Williams D & Feely J 2002 Clin Pharmacokinet 41:343–370 "Pharmacokinetic-Pharmacodynamic Drug Interactions with HMG-CoA Reductase Inhibitors" — comprehensive review of statin × CYP3A4 inhibitor DDIs covering simvastatin × clarithromycin AUC ratios.
---

# CYP3A4 DDI：clarithromycin × simvastatin 经典 case

## Background
Simvastatin (HMG-CoA reductase inhibitor) 主要由 CYP3A4 代谢，狭治窗 (rhabdomyolysis at high concentration)。与 CYP3A4 strong inhibitor (clarithromycin / itraconazole / grapefruit juice) 共服 → AUC 升 5-10× → 横纹肌溶解风险。**FDA black-box warning**：simvastatin 禁与 strong inhibitor 共服。

## What I actually did
1. **Mechanism identification**：clarithromycin 是 mechanism-based inactivator (MBI) of CYP3A4 (k_inact, K_I)；simvastatin 是 substrate (k_cat, K_m)
2. **Static prediction (FDA guidance)**：
   - Reversible inhibitor: AUC ratio = 1 + (I_unbound / Ki)
   - MBI: more complex, 包括 enzyme synthesis rate (k_deg)
3. **Dynamic PBPK prediction**：PBPK 含 CYP3A4 turnover + inhibitor PK + substrate PK
4. **Predicted AUC ratio (clarithromycin co-admin)**：~5-10×
5. **Clinical observed (literature)**：~10× AUC 升 → 与 prediction 一致
6. **Risk classification**：
   - Strong (>5x AUC): contraindicated
   - Moderate (2-5x): dose adjust
   - Weak (<2x): monitor
7. **Output**：DDI risk table + recommended action + clinical reference

## ★ 排除/不做的事
- **不区分 reversible vs MBI**：MBI 影响延长 (enzyme 需要 days resynthesis)
- **Static prediction 当 final**：static 简单但 accuracy 低；dynamic PBPK 准
- **不考虑 transporter DDI**：CYP + transporter combined 影响（如 OATP1B + statin）
- **Single CYP isoform**：drug 多 CYP 代谢 (CYP2D6 + 3A4) 都需考虑
- **Genotype 不考虑**：CYP2D6 poor metabolizer 不 DDI 担心 (already minimal CYP2D6)
- **不报 clinical guidance**：prediction 给 number 无 actionable recommendation 没用

## ★ 失败模式
- **Hepatic uptake transporter**：OATP1B1 inhibition + CYP inhibition 双重 effect
- **Genotype-dependent risk**：CYP3A4*22 carrier baseline lower CYP3A4 activity
- **Time course**：MBI 起效 days；reversible 几小时；剂量时间表影响
- **Active metabolite**：substrate 的 active metabolite 同样需评估
- **Population variability**：CYP3A4 expression 个体差异 5-20×
- **Drug-induced liver injury (DILI)** independent of DDI

## Lessons → seeds for rules
1. **Reversible vs MBI** 区分必备
2. **Static + dynamic (PBPK) combined**
3. **Transporter DDI 同时考虑**
4. **Multi-CYP isoform** analyze
5. **Genotype / phenotype** for special population
6. **Risk classification + clinical guidance** strict
7. **FDA / EMA guidance follow**
