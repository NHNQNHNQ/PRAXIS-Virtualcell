---
case_id: pharma-012-cyp2d6-codeine
task: pharmacogenomic_dose_individualization
input_compound: codeine
target_drug: codeine (prodrug; bioactivated to morphine by CYP2D6)
target_population: patient
drug_class: small_mol
target_indication: pain
route_of_admin: PO
tools: [CPIC guidelines, NONMEM PG-popPK, Pumas pgxPK module]
key_paper_doi: 10.1038/clpt.2013.254
status: validated
provenance:
  source_type: literature
  citation: "Crews KR et al. 2014 Clin Pharmacol Ther 95:376–382 'Clinical Pharmacogenetics Implementation Consortium guidelines for cytochrome P450 2D6 genotype and codeine therapy: 2014 update'"
  extracted_at: 2026-04-30
  extraction_confidence: high
tags: [codeine, CYP2D6, pharmacogenomics, pediatric, ultrarapid_metabolizer, respiratory_depression, tdm, dose_individualization]
---

# CYP2D6 codeine：从基因型推到剂量 + 安全风险

## Background
Codeine 是 prodrug：体内由 CYP2D6 O-去甲基化生成 morphine（实际止痛活性体）。CYP2D6 表型决定 morphine 暴露：
- **Poor metabolizer (PM, *3/*4/*5/*6/*1×N=0 等)** ~5-10% 白人、~1% 中国人 → 几乎不生成 morphine → **无止痛效果**
- **Intermediate metabolizer (IM)** → 减半
- **Extensive (EM, "normal")** ~70% → 标准止痛
- **Ultra-rapid (UM, *1xN copies, *17 等)** ~5-10%（北非/阿拉伯人最高 30%）→ morphine 浓度 5-10× → **呼吸抑制 / 死亡**

**FDA 2017 black-box 禁忌**：codeine 在 < 12 岁儿童禁用（特别 OSA 术后扁桃体切除）；妊娠+哺乳 UM 母亲 → 婴儿 morphine 中毒经母乳转移。CPIC 2014 guideline 强制推荐：UM → 用替代镇痛（tramadol 也是 CYP2D6 prodrug，同坑）；PM → tramadol/codeine 都不有效，用非 CYP2D6 镇痛（NSAIDs / morphine 直接给）。

## What I actually did
1. **Phenotype assignment**：CYP2D6 genotype → activity score → phenotype（CPIC table）
   - PM: AS = 0
   - IM: AS = 0.25-1.0
   - EM: AS = 1.25-2.25
   - UM: AS ≥ 2.25
2. **Bayesian dose individualization**（如果 codeine 仍要用）：popPK model with CYP2D6 phenotype as multiplicative factor on bioactivation rate
   - Morphine AUC_PM ≈ 0.1 × AUC_EM
   - Morphine AUC_UM ≈ 5-10 × AUC_EM
3. **Risk classification + alternative**：
   - PM → switch to non-prodrug analgesic (NSAID, IV morphine)
   - UM → AVOID codeine entirely; use hydromorphone or oral morphine with explicit dose
   - IM/EM → standard codeine dosing OK
4. **Critical populations**:
   - **Children < 12** post-tonsillectomy/adenoidectomy: contraindicated regardless of phenotype (FDA 2017)
   - **Lactating mothers**: UM mother + breastfed infant → morphine in breast milk → infant respiratory depression (Koren 2006 case report Lancet 368:704)
5. **Output**：phenotype-based recommendation table + alternative analgesic suggestions + monitoring plan

## ★ 排除的 dose / population / 方法
- **Children < 12 post-T&A**: FDA contraindicated (2017 BBW); CPIC 2014 strong recommendation. Switch to NSAID/acetaminophen.
- **CYP2D6 UM**: codeine and tramadol both contraindicated (both bioactivated by CYP2D6 → respiratory depression). Use morphine directly with weight-based dose.
- **Lactating mothers + UM phenotype**: switch analgesia to non-CYP2D6 substrate.
- **Phenotype-only dose increase for PM without checking analgesia mechanism**: PM patients get NO benefit from codeine; doubling dose just doubles toxicity without efficacy. Switch class.
- **Single CYP2D6 genotype panel without ×N copy number assay**: misclassifies UM as EM; 30% of African ancestry have *1×N+1 (≥3 copies) → UM phenotype.

## ★ 失败模式
- **Children's death case (Koren 2006)**: lactating mother UM phenotype taking codeine → morphine in milk → 13-day-old infant cyanotic episode + death. Mother's CYP2D6 genotype was not tested before prescription.
- **Genotype panel misses *17, *41 alleles**: standard CYP2D6 panels (*2/*3/*4/*5/*6/*9/*10) miss African-prevalent *17 (intermediate function) and Caucasian-prevalent *41 (decreased) → wrong phenotype assignment.
- **Drug-drug-gene interaction**: paroxetine / fluoxetine (strong CYP2D6 inhibitors) + codeine → phenoconversion to PM regardless of underlying genotype → no analgesia. Concomitant medication review (rule_05) critical.
- **Activity score ambiguity in IM range**: AS 0.5–1.0 has variable phenotype expression; some patients in this range respond to standard codeine, some don't. Therapeutic monitoring (pain VAS) indicated.

## ★ 方法选择决策链
- **Genotype-guided vs trial-and-error**: pre-emptive genotyping is cost-effective for high-volume drugs (Crews 2014 cost-benefit table); trial-error wastes 1-3 days while patient suffers and risks UM toxicity.
- **CYP2D6 panel breadth**: 5-allele core panel misses ~10% of meaningful variants; recommend full sequencing for high-risk drugs (codeine, tamoxifen).
- **Activity score system (CPIC) vs traditional phenotype labels**: AS gives gradient (0/0.25/0.5/1/1.5/2/3+) more granular than PM/IM/EM/UM categorical; AS preferred for popPK modeling.
- **PM patient analgesia alternative**: NSAID first (if not contraindicated for renal/GI/CV); IV/oral morphine if NSAID inadequate; AVOID tramadol (same CYP2D6 prodrug pathway).

## ★ Validation
- **CPIC 2014 levels of evidence**: A-rated for codeine; multi-center retrospective cohort + RCT confirms phenotype-driven outcome differences.
- **Pharmacogenomic implementation outcomes**: Vanderbilt PREDICT, St. Jude Children's, Mayo Clinic — large-scale clinical implementations report adverse-event reduction with pre-emptive genotype-guided prescribing.
- **Linked outcomes**: child morphine intoxication case reports (Koren 2006, Madadi 2007) — UM phenotype in mother/child caused fatal respiratory depression at standard codeine doses.

## Lessons → seeds for rules
1. **Genotype-driven phenotype prediction** (CYP2D6 → PM/IM/EM/UM) and dose adjustment > universal dose. (Generalize: rule_03 CYP3A5 tacrolimus → broader rule_PG covering CYP2D6, CYP2C19, TPMT, DPYD).
2. **Drug-drug-gene interaction** review at every visit (CYP2D6 inhibitor co-administration phenoconverts).
3. **Avoid prodrug pathway altogether** in PM and UM phenotypes — use non-bioactivated alternatives.
4. **Vulnerable populations** (children, lactating mothers) — pre-emptive genotyping or empirical avoidance.
5. **Activity score** (numerical 0-3+) > categorical phenotype for popPK modeling.
