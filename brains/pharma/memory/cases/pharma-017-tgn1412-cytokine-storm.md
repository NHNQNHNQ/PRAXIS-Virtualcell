---
case_id: pharma-017-tgn1412-cytokine-storm
task: first_in_human_dose_disaster_postmortem
input_compound: TGN1412 (CD28 superagonist anti-CD28 mAb)
target_drug: TGN1412 (theralizumab; TeGenero AG)
target_population: healthy_volunteer
drug_class: antibody
target_indication: rheumatoid_arthritis_or_B_CLL
route_of_admin: IV
tools: [fih_dose_design (MABEL mode), receptor occupancy modeling, EMA risk-based approach 2007]
key_paper_doi: 10.1056/NEJMoa063842
status: validated
provenance:
  source_type: literature
  citation: "Suntharalingam G et al. 2006 N Engl J Med 355:1018-1028 'Cytokine Storm in a Phase 1 Trial of the Anti-CD28 Monoclonal Antibody TGN1412'"
  extracted_at: 2026-05-01
  extraction_confidence: high
tags: [TGN1412, theralizumab, CD28_superagonist, FIH_disaster, MABEL, NOAEL_failure, cytokine_storm, receptor_occupancy, EMA_2007, immune_modulator, biologic, healthy_volunteer]
---

# TGN1412 March 2006 cytokine storm: NOAEL × 1/10 failure → MABEL mandate

## Background
2006 年 3 月 13 日, TeGenero AG 公司在伦敦 Northwick Park 医院开展抗 CD28 单抗 TGN1412 (theralizumab) Phase I FIH 试验。给 6 名健康志愿者 0.1 mg/kg IV 输注（基于 NOAEL × 1/500 的 "保守" 起始剂量），90 分钟内全部 6 人发生 cytokine release syndrome (CRS)。
- 1 小时：发热、寒颤、严重头痛、肌肉痛
- 2-4 小时：低血压、缺氧、急性肺水肿、肝肾衰竭、DIC
- 48 小时：血液 IL-1, IL-2, IL-6, IL-8, IL-10, IFN-γ, TNF-α 浓度峰值 1000-10000× 基线
- All 6 patients hospitalized in ICU; one developed multi-organ failure with prolonged ICU stay; 1 patient lost finger/toe tips to gangrene; long-term immune dysregulation in survivors.

**Pre-clinical safety**：cynomolgus monkey × 500-1000 mg/kg single dose 无毒性反应；NOAEL = 50 mg/kg；× 1/500 safety factor → 0.1 mg/kg human IV (similar molar in vitro receptor binding).

**关键失败**：人 vs 猴 CD28 superagonist signaling 完全不同。人 CD4+ effector memory T cells 对 CD28 superagonism 强敏感，cyno 不一样。NOAEL approach 完全没 capture 物种间 immunopharmacology 差异。

## What I actually did (post-mortem reconstruction)
1. **Pre-clinical NOAEL** in cyno: 50 mg/kg with no findings → BSA-scaled HED ≈ 16 mg/kg human → MRSD with SF=500 → 0.1 mg/kg
2. **MABEL post-hoc calc**：
   - In vitro CD28 receptor occupancy at 0.1 mg/kg estimated systemic = 90% RO!
   - Target ≤10% RO floor (current EMA 2017 guideline)
   - True MABEL would have been ~ **0.001-0.01 mg/kg** (100-1000× lower)
3. **Cytokine release in vitro assay (CRA)** post-hoc：
   - High-density preculture human PBMC + immobilized TGN1412 → MASSIVE cytokine release at sub-clinical doses
   - This assay was NOT performed pre-clinically (didn't exist as standard); now mandatory for any T-cell agonist
4. **Regulatory response (EMA 2007)**:
   - Replace "NOAEL × safety factor" sole basis → MABEL-based dose for high-risk biologics
   - "Anticipated risk" classification: novel mechanism + immune modulator + first-in-class → highest risk → MABEL with extra-low safety factor (50-100×)
   - Sequential dosing (not parallel) for high-risk FIH
   - Onsite CRO with ICU capability mandatory
5. **Lessons cascade**: every immune modulator FIH since 2006 follows MABEL-with-CRA paradigm; NOAEL alone hard-rejected by Reviewer rule HR-04.

## ★ 排除的 dose / population / 方法
- **NOAEL × safety factor alone for immune modulator FIH**: hard-rejected (HR-04); MABEL co-method mandatory.
- **Parallel dosing in FIH for high-risk biologic**: must be sequential with observation between subjects (≥1 h IV; ≥24 h SC).
- **Cynomolgus-only preclinical for human CD28 / immune-targeted biologic**: species differences in T-cell biology mean cyno ≠ human; need additional in vitro human cell assays.
- **Sub-MRSD safety factor < 50 for novel-mechanism immune biologic**: current EMA 2017 guidance requires SF ≥ 50, often 100-1000.
- **Healthy volunteers for highest-risk biologics**: shifted to patient population for some classes (e.g. CAR-T → only in cancer patients).
- **Receptor occupancy ceiling > 10% for FIH first dose**: case-017 lesson; MABEL targets ≤10% RO at predicted Cmax.

## ★ 失败模式
- **Cross-species mechanism gap**: cynomolgus CD28 superagonist signaling weaker than human; cyno didn't predict human CRS.
- **NOAEL with no observed effect**: when preclinical has no adverse finding, NOAEL is whatever the highest tested dose was — but that doesn't mean human response is bounded by that.
- **In vitro CRA absent at the time**: high-density preculture PBMC assay didn't exist pre-2006; now mandatory and would have caught TGN1412 cytokine release at predicted clinical dose.
- **Parallel dosing of all 6 subjects at once**: when first subject reacted, dose 2-6 already given — couldn't pause cohort; sequential dosing now mandatory for first-in-class biologics.
- **TeGenero failure to communicate intermediate findings**: when first patient deteriorated, 5 had already been infused — communication delays exacerbated.
- **CRO + sponsor liability gap**: post-event legal complexity around responsibility for trial design vs execution.

## ★ 方法选择决策链
- **MABEL > NOAEL** for immune modulator FIH (mandatory post-2006).
- **Multi-species + in vitro human cell assays**: cynomolgus alone insufficient for immune biologics; add human PBMC assays + iPSC-derived T cell assays where available.
- **Sequential vs parallel dosing**: sequential for novel-mechanism biologics with > 1 h gap; only parallel for low-risk well-characterized agents.
- **Sentinel-subject** design: first subject single-dose with multi-day observation before cohort dosing.
- **Precise risk classification** (FDA / EMA): integrated risk based on novel-mechanism + immune-related + first-in-class flags drives MABEL safety factor (10× standard, 50-100× novel, 100-1000× highest).
- **Site preparedness**: ICU on-site, anti-cytokine rescue (steroids, anti-IL-6, anti-TNF) immediately available.

## ★ Validation
- **Suntharalingam 2006 NEJM 355:1018**: complete clinical course documented in healthy volunteers.
- **EMA 2007 + 2017 guideline updates**: regulatory codification of MABEL approach + risk-based stratification.
- **Stebbings 2013 Br J Pharmacol 168:1605**: in vitro PBMC CRA validated for predicting cytokine storm risk; would have caught TGN1412 at pre-clinical stage.
- **Subsequent CD28 / OX40 agonist programs**: all use MABEL-based starting dose with much lower clinical doses (some drugs entering clinic at ~ 0.0001 mg/kg).

## Lessons → seeds for rules
1. **MABEL mandatory** for immune modulator FIH (rule_06 already encoded; this is the original anchor case).
2. **In vitro human cell assays** (PBMC CRA, iPSC-derived) supplement preclinical animal data for immunopharmacology.
3. **Sequential dosing** + sentinel subject for high-risk FIH.
4. **Receptor occupancy ≤ 10%** ceiling at FIH first dose for novel agonist mechanisms.
5. **Risk-based safety factor stratification** (10× / 50× / 100-1000×).
6. **On-site ICU + rescue medication** mandatory for FIH high-risk biologics.
7. **Cyno limitations**: species-mechanism gap requires human cell-based supplement.
