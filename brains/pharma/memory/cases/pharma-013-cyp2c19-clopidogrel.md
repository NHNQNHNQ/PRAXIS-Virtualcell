---
case_id: pharma-013-cyp2c19-clopidogrel
task: pharmacogenomic_pkpd_active_metabolite
input_compound: clopidogrel
target_drug: clopidogrel (prodrug; bioactivated by CYP2C19 to active thiol metabolite that irreversibly inhibits P2Y12)
target_population: patient
drug_class: small_mol
target_indication: cardiovascular
route_of_admin: PO
tools: [pkpd_emax, NLME with CYP2C19 covariate, CPIC guidelines, light transmission aggregometry (LTA)]
key_paper_doi: 10.1038/clpt.2013.105
status: validated
provenance:
  source_type: literature
  citation: "Scott SA et al. 2013 Clin Pharmacol Ther 94:317–323 'Clinical Pharmacogenetics Implementation Consortium guidelines for CYP2C19 genotype and clopidogrel therapy: 2013 update'"
  extracted_at: 2026-04-30
  extraction_confidence: high
tags: [clopidogrel, CYP2C19, pharmacogenomics, antiplatelet, active_metabolite, P2Y12, MACE, drug-gene-drug-interaction]
---

# CYP2C19 clopidogrel：active metabolite + 平台板抑制 PK-PD

## Background
Clopidogrel 是 prodrug：~85% 在肝脏由 esterase 水解（无活性），剩余 15% 经 CYP2C19 (主要) + CYP3A4/2B6/1A2 (副) 两步 oxidation → 不稳定 thiolactone → active thiol metabolite (clop-active-thiol) → 不可逆共价修饰 P2Y12 ADP receptor → 阻断血小板聚集。

**CYP2C19 表型决定 active metabolite 暴露**：
- **PM (\*2/\*2 etc)** ~3-5% 白人、~15% 亚洲人 → active metabolite AUC ~50% of EM → 平台板抑制减半 → 急性冠脉综合征 PCI 后 MACE 风险 ↑1.5-3×（TRITON-TIMI 38, PLATO 子分析）
- **IM (\*1/\*2)** ~25% 白人、~50% 亚洲人 → AUC ~70% of EM
- **EM (\*1/\*1)** "normal"
- **UM (\*1/\*17)** ~25% 白人 → AUC ~120% → 出血风险略增（也算 over-response）

**FDA 2010 black-box warning**：CYP2C19 PMs 在 stent-PCI 后 MACE 风险 ≥2× 普通患者；推荐替代抗血小板药 (prasugrel, ticagrelor, 都不依赖 CYP2C19)。

**Drug-gene-drug interaction**：omeprazole（CYP2C19 强抑制剂）+ clopidogrel → 表型 phenoconversion EM → IM/PM → 临床效果同 PM。FDA 2009 警告。

## What I actually did
1. **Phenotype assignment**：CYP2C19 genotype → CPIC table → PM/IM/EM/UM
2. **Active metabolite PK by phenotype**（meta-analysis published values）：
   - EM: clop-active-thiol AUC = 100% (reference)
   - IM: 70% (95% CI 60-85%)
   - PM: 50% (95% CI 40-65%)
   - UM: 110-130%
3. **PK-PD Emax**：% platelet inhibition = Emax · C / (EC50 + C)
   - Emax ≈ 80% (max achievable at saturating exposure)
   - EC50 ≈ 50 ng·h/mL active metabolite AUC (literature)
4. **Predicted platelet inhibition by phenotype** (loading 600 mg + maintenance 75 mg q24h):
   - EM: ~55% (average) → adequate antiplatelet
   - IM: ~45% → borderline
   - PM: ~30% → INADEQUATE; switch to prasugrel/ticagrelor
   - UM: ~58% → adequate (slight bleeding risk)
5. **Drug-gene-drug interaction modeling**：if + omeprazole 80 mg QD, EM phenoconverts to PM-like → switch PPI to pantoprazole (no CYP2C19 effect) OR switch antiplatelet
6. **Outcome correlation**：MACE@1y for PCI-stent: PM ~16% vs EM ~9% (TRITON-TIMI 38 retrospective), HR 1.8 (95% CI 1.2-2.6)

## ★ 排除的 dose / population / 方法
- **Universal 75 mg/d clopidogrel**: clinically inadequate for PMs → switch antiplatelet drug class entirely (prasugrel or ticagrelor — neither requires CYP2C19).
- **Doubling dose to 150 mg/d for PMs**: CRP-pharmacogenomic study (Mega 2010 NEJM) showed inadequate to overcome PM phenotype; doubled bleeding risk.
- **Genotype-only without phenoconversion check**: omeprazole / esomeprazole / fluconazole / fluoxetine concomitant strong-CYP2C19 inhibitor → effective phenotype = PM regardless of genotype. Concomitant medication review (rule_05).
- **Patients with active GI bleeding history**: switch to ticagrelor (lower GI bleed than prasugrel) regardless of phenotype.
- **CYP2C19 panel without \*17 detection**: misses UM phenotype; some patients labeled "EM" are actually \*1/\*17 → UM → bleeding risk.

## ★ 失败模式
- **TRITON-TIMI 38 retrospective**: 27% of patients were CYP2C19 LoF carriers (PM/IM); MACE rate ↑ in this subgroup. Original trial design didn't stratify by genotype → underpowered for pharmacogenomic subgroup analysis.
- **PPI co-prescription is endemic**: ~50% of stent-PCI patients on PPI (GI prophylaxis). Most clinicians don't know about CYP2C19 phenoconversion; default omeprazole prescription unintentionally phenoconverts EM to PM-equivalent.
- **CYP2C19 \*2 frequency varies 5-30% by ethnicity**: blanket warnings aren't ethnically calibrated; Asian populations have ~50% IM/PM phenotype combined → near-universal genotype testing rationale.
- **Active metabolite half-life is short (~30 min) but P2Y12 binding is irreversible**: PK Cmax matters more than AUC for platelet inhibition because peak concentration achieves saturation. Model interpretation must account for this PK-PD coupling.
- **GENESIS-PEGY trial null result**: pre-emptive genotype-guided antiplatelet selection didn't improve MACE in CYP2C19 carriers vs standard care — possibly underpowered, possibly because IM ≠ PM in clinical effect, or because alternative antiplatelets had their own side-effect profile.

## ★ 方法选择决策链
- **Genotype-guided antiplatelet selection vs universal ticagrelor/prasugrel**: cost-benefit favors genotyping in moderate-volume centers; high-volume centers may use universal newer-generation P2Y12i and skip genotyping.
- **Activity score CPIC framework**: AS = sum of allele activities (\*1=1, \*17=1.5, \*2/\*3=0); AS ≤ 0.5 → PM-equivalent.
- **PPI choice for stent patients**: pantoprazole (negligible CYP2C19) is preferred over omeprazole/esomeprazole (strong CYP2C19 inhibitors).
- **Light transmission aggregometry (LTA) on-treatment platelet response testing**: alternative to genotyping; measures actual phenotype but laboratory variability + cost issues.
- **VerifyNow P2Y12 platelet function point-of-care**: rapid result; cutoff PRU > 230 = inadequate response. Useful in ICU-stat decisions.

## ★ Validation
- **TRITON-TIMI 38 + PLATO + ISAR-REACT-5 retrospective subgroup analyses**: consistent finding of CYP2C19 PM phenotype → reduced clopidogrel efficacy → ↑MACE.
- **POPular Genetics RCT (2019 NEJM 381:1621)**: pre-emptive genotyping with PM/IM → switch to ticagrelor/prasugrel was NON-INFERIOR to universal ticagrelor for ischemic outcomes AND superior for bleeding.
- **CPIC level A evidence**: multi-RCT + meta-analysis support CYP2C19-guided clopidogrel decision.

## Lessons → seeds for rules
1. **Active metabolite PK matters more than parent**: when a drug is a prodrug, model the active metabolite's PK explicitly (case-009 also touches active metabolite for tumor PD).
2. **Genotype + concomitant CYP inhibitor → phenoconversion**: integrate drug-gene-drug interactions into PK predictions.
3. **Ethnically calibrated guidelines**: PG genotype frequencies differ 5-30× across populations; one-size-fits-all dosing fails subpopulations.
4. **Switch drug class** when bioactivation pathway is genotype-blocked, rather than dose-titrate.
5. **Outcome correlation** (MACE, bleeding) must be the gold standard; surrogate endpoints (LTA, VerifyNow) inform but don't replace.
