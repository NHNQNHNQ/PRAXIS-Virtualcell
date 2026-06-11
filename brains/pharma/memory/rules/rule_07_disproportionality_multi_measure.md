---
rule_id: rule_07_disproportionality_multi_measure
rule_type: case_distilled
applies_to: [faers]
evidence_cases:
  - pharma-004-faers-mining
  - pharma-003-cyp3a4-ddi
  - pharma-009-pkpd-emax
confidence: medium
authoring_date: 2026-04-29
source_synthesis_section: §一 row 'PRR alone no comparator' & §七 #4
---

# FAERS signal detection requires PRR + ROR + IC25

Single disproportionality measure is unreliable due to reporting bias and
confounding. Mandatory multi-measure protocol:

| Measure | Threshold | Use |
|---|---|---|
| **PRR (Proportional Reporting Ratio)** | ≥ 2 with χ² ≥ 4 | EU EMA |
| **ROR (Reporting Odds Ratio)** | ≥ 2 with lower 95% CI > 1 | broader sensitivity |
| **IC25 (lower 95% CI of Information Component)** | > 0 | Bayesian (WHO UMC) |

Plus: cases ≥ 3 minimum; comparator = full FAERS OR drug class; time-series to
catch notoriety bias post-warning. Confidence label `medium` only when ≥ 2
measures agree on positive signal.

Reviewer HR-06 fires on FAERS signal output without all three measures.
