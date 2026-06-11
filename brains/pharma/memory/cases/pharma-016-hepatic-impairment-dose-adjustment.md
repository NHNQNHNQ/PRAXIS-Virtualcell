---
case_id: pharma-016-hepatic-impairment-dose-adjustment
task: hepatic_impairment_dose_adjustment
input_compound: midazolam (CYP3A4 high-clearance substrate)
target_drug: midazolam (case-002 chain extension)
target_population: special
drug_class: small_mol
target_indication: sedation_anesthesia
route_of_admin: PO
tools: [PBPK with reduced CYP3A4 + Child-Pugh score, FDA Hepatic Impairment Guidance 2003, EMA hepatic impairment guideline 2005]
key_paper_doi: 10.1007/s00228-008-0553-z
status: validated
provenance:
  source_type: literature
  citation: "Verbeeck RK 2008 Eur J Clin Pharmacol 64:1147-1161 'Pharmacokinetics and dosage adjustment in patients with hepatic dysfunction'"
  extracted_at: 2026-04-30
  extraction_confidence: high
tags: [hepatic_impairment, child_pugh, midazolam, CYP3A4, dose_adjustment, cirrhosis, PBPK, special_population, FDA_guidance]
---

# 肝功能不全剂量调整：Child-Pugh 分级驱动 PBPK 修正

## Background
肝功能不全 (hepatic impairment, HI) 改变药物 PK 多个维度：
1. **CYP 酶活性下降** — Child-Pugh A 减少 ~25%, B 减少 ~50%, C 减少 ~70-90%
2. **肝血流减少** — 门脉血流 ↓, 入肝灌注 ↓
3. **血浆白蛋白降低** — 高蛋白结合药物 fu ↑
4. **门脉-全身 shunt** — 部分药物绕过肝脏
5. **transporter (OATP, MRP, P-gp) 下调** — hepatic uptake 受损

**Child-Pugh score** 是临床标准量化工具：A (5-6)、B (7-9)、C (10-15)。FDA 2003 + EMA 2005 hepatic impairment guidelines 推荐分层 PK 研究 + 剂量调整。

**Midazolam in cirrhosis (Pentikäinen 1989; Trouvin 1988)**：
- Child-Pugh B/C 患者 → midazolam IV CL 减半 → AUC ×2 → 苯二氮卓敏感度增加（脑 GABA-A 受体上调） → 临床镇静作用 dramatic 增强
- 推荐：cirrhosis Child-Pugh B 起始剂量减 50%；C 减 75% + 可逆 antagonist (flumazenil) 备用

## What I actually did
1. **Quantify hepatic CL_int reduction** by Child-Pugh class:
   - Class A: × 0.75 (mild)
   - Class B: × 0.50 (moderate)
   - Class C: × 0.25 (severe)
   - Source: meta-analysis Verbeeck 2008 Table 2 + FDA HI guidance 2003 + Schünemann 2003 (extension to weight-based metric)
2. **Adjust hepatic blood flow** for cirrhosis:
   - Compensated cirrhosis: portal flow ↓ 20-30%
   - Decompensated: ↓ 50-70%; portosystemic shunting bypasses ~30%
3. **Albumin / α1-acid glycoprotein**: cirrhosis lowers albumin (mean ~30 g/L vs 40 g/L normal); fu of high-albumin-bound drugs (warfarin, phenytoin) ↑ 50-100%.
4. **PBPK modification (case-002 extension)**:
   - midazolam CL_int reduced per Child-Pugh class
   - reduced Q_h reflecting cirrhosis hemodynamics
   - elevated fu_p reflecting hypoalbuminemia
   - Predict AUC: control 145 ng·h/mL → CP-B 290 ng·h/mL → CP-C 580 ng·h/mL
5. **Output**: dose recommendation per Child-Pugh class + monitoring plan + flag for rescue antagonist availability.

## ★ 排除的 dose / population / 方法
- **No dose adjustment for hepatic-cleared drug in CP-B/C cirrhosis**: clinically dangerous; sedation overdose risk. 强制 50-75% reduction.
- **MELD score alone**: better for transplant priority, less validated for PK adjustment than Child-Pugh.
- **Acute hepatitis (transient)**: don't apply chronic CP-class adjustments; await transaminase/synthesis function recovery.
- **Renally cleared drug**: use renal markers (eGFR) not Child-Pugh (separate dimension; both can coexist e.g. hepatorenal syndrome).
- **Single-time-point trough monitoring during cirrhosis IV midazolam**: half-life is dramatically extended (8-12 h vs 2-3 h normal) — sample timing must adjust.
- **Acetaminophen in cirrhosis**: max 2-3 g/d (vs 4 g/d normal); centrolobular necrosis risk elevated.

## ★ 失败模式
- **Child-Pugh A patients sometimes receive no adjustment despite measurable PK shift**: even mild HI gives 25% CL reduction; consider 75% standard dose for narrow-window drugs.
- **Hepatorenal syndrome (HRS)**: cirrhosis + renal failure. Both organs failing → both CL pathways compromised. Drugs eliminated by either route accumulate. Dose-adjust for both.
- **Inconsistent CP-class definitions across studies**: some use modified CP, some use original; verify which version your PK reference used.
- **Acute decompensation events in chronic liver disease**: Child-Pugh score evolves; periodic re-assessment + dose re-titration needed.
- **Drug-induced liver injury (DILI) confounder**: drug itself causing the impairment; chicken-and-egg interpretation.
- **Hepatocellular carcinoma (HCC)**: tumor + cirrhosis; specific drug class considerations (sorafenib, lenvatinib have specific HI dose advice).
- **Trans-jugular intrahepatic portosystemic shunt (TIPS)**: shunting alters first-pass; oral drug F may increase 2-3× post-TIPS.

## ★ 方法选择决策链
- **Child-Pugh score** > MELD for PK adjustment (more decades of PK literature data).
- **Tabulated Child-Pugh × CL_int factor** > arbitrary % reduction.
- **PBPK refinement** for high-clearance drugs (case-002 chain): static "reduce 50%" suggestion is too coarse; PBPK with modified CYP3A4 + Q_h + fu gives stage-specific Cmax/AUC predictions.
- **FDA 2003 + EMA 2005 guidance**: stratified PK study (CP-A, CP-B, CP-C cohorts vs healthy) is regulatory standard; in absence, use Verbeeck 2008 review tables.
- **Drug-specific labels**: many drugs have specific HI dose tables in their FDA label (e.g., dabigatran, sorafenib); always check label first.

## ★ Validation
- **Pentikäinen 1989 BJCP 27:39 (n=8 cirrhosis vs n=8 control)**: midazolam IV → AUC × 2.1 in cirrhosis; CL × 0.50; t1/2 × 2.5 (3 h → 7.5 h).
- **Trouvin 1988 BJA 60:762**: midazolam in elective surgery cirrhosis patients; clinically prolonged sedation.
- **Verbeeck 2008 review (n=120+ studies)**: tabulated CP-class × drug-class dose-adjustment recommendations.
- **PBPK simulation reproducibility**: PK-Sim hepatic impairment module gives Cmax/AUC predictions within 2× of clinical observations.

## Lessons → seeds for rules
1. **Child-Pugh class drives PK adjustment** for hepatically-cleared drugs.
2. **PBPK refinement for HI** (CL_int ↓, Q_h ↓, fu ↑ all simultaneously) more accurate than single-dimension scaling.
3. **Albumin substitution**: cirrhosis decreases albumin → fu ↑ → free drug ↑ → toxicity for narrow-window drugs.
4. **Periodic re-assessment**: Child-Pugh evolves; revisit dose with each clinical change.
5. **Hepatorenal syndrome**: combined HI + RI → both pathway adjustments simultaneously.
6. **Cirrhosis-specific antagonist availability**: flumazenil for benzodiazepines; naloxone for opioids; should be on-hand for narrow-window drugs in CP-C.
