---
case_id: pharma-XXX-short-slug
task: short_underscore_label    # e.g. cross_species_pk_scaling | drug_drug_interaction_prediction
input_compound: chemical name or class
target_population: healthy|patient|pediatric|elderly|special
drug_class: small_mol|biologic|antibody|peptide|oligonucleotide|gene_therapy
target_indication: oncology|cardio|cns|infection|...|null
route_of_admin: PO|IV|IM|SC|TD|null
tools: [list of tools used]
key_paper_doi: "10.xxxx/xxxxx"   # CrossRef-verifiable
status: validated|draft|deprecated
provenance:
  source_type: literature|guidance|case_report
  pmid: "00000000"
  citation: "Author Y. Title. Journal Year;Vol:Pages."
  extracted_at: 2026-04-29
  extraction_confidence: high|medium|low
  unverified_details: []
tags: [pharma_task, drug_class, target_indication, ...]
---

# {Case title — drug × method × outcome in one sentence}

## Background
What clinical / regulatory / scientific context this case sits in. Why this
particular drug + method illustrates a generalizable lesson.

## What I actually did
Numbered, executable steps. Specific values, doses, parameters. Show the math
where relevant. Include the validation step (clinical PK comparison / VPC /
E-R / TDM real-world feedback).

## ★ 排除的 dose / population / 方法
- **Unsafe dose / contraindicated DDI**: …
- **Not validated population**: pediatric / pregnant / hepatic / renal / genotype …
- **Methods deliberately not used and why**: e.g. NCA over popPK because …

## ★ 失败模式
- **Cross-species gap (e.g. TGN1412)**: …
- **Non-linear PK at high dose**: …
- **Hypoalbuminemia / disease state**: …
- **DDI escalation over time**: …
- **Active metabolite uncaptured**: …

## ★ 方法选择决策链
- **NOAEL vs MABEL** for FIH: …
- **3+3 vs BLRM** for escalation: …
- **NCA vs popPK** for rich vs sparse data: …
- **Equilibrium dialysis vs ultrafiltration** for fu: …

## ★ Validation
- **Clinical PK comparison**: predicted vs observed within 2× / VPC pass
- **E-R analysis**: dose-exposure-response analysed
- **TDM real-world feedback**: bayesian forecasting deployed

## Lessons → seeds for rules
1. (high-confidence rule candidate)
2. …
