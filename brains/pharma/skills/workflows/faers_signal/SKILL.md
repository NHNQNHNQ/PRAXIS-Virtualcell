---
name: faers_signal
description: |
  FAERS adverse event signal detection — multi-measure disproportionality
  (PRR + ROR + IC25 Bayesian) with comparator (full database vs drug class)
  and time-series for notoriety bias. Per case-004 (rofecoxib MI signal
  retrospective) + rule_07.

  v0.1 STATUS: stub. Real implementation requires openFDA pulls of large
  count tables — `tools/openfda_client.py` has the base scaffolding; v0.2
  will compute PRR/ROR/IC25 over an aggregated count table.
inputs:
  drug_name: str
  ade_term: str           # MedDRA preferred term
  comparator: "full_db|drug_class|specific_drug"
  comparator_drug_class: str | null
  date_range: [str, str]  # ISO dates, YYYY-MM-DD
outputs:
  contingency_table: {a: int, b: int, c: int, d: int}
  prr:    {value: float, ci_95: [float, float], chi_sq: float, fired: bool}
  ror:    {value: float, ci_95: [float, float], fired: bool}
  ic25:   {value: float, lower_95: float, fired: bool}
  time_series: list[{month: str, prr: float, n_cases: int}]
  signal_classification: "none|weak|moderate|strong"
  flags: list[str]    # "indication_confounding_unevaluated", "single_country", "post_warning_bias"
env: praxis-pharma + openFDA API key (recommended)
status: stub
stage: design|execution|reporting
domain: pharmacovigilance
---

# faers_signal (v0.1 stub)

Real v0.2 implementation:

1. Pull counts via `openfda_client.faers_count(drug, ade_term)` (returns a, b, c, d).
2. **PRR** = (a/(a+b)) / (c/(c+d)); χ² ≥ 4 + cases ≥ 3 + PRR ≥ 2 → fire.
3. **ROR** = (a·d)/(b·c); 95% CI lower bound > 1 → fire.
4. **IC** (Bayesian) = log₂((a + 0.5) / E(a))where E(a) = (a+b)(a+c)/(a+b+c+d);
   lower 95% CI of IC > 0 → fire (WHO UMC threshold: IC025 > 0).
5. Time series per month → catch notoriety bias (PRR rises after public warning).
6. Flag indication confounding (e.g. NSAIDs given to elevated CV-risk patients).

Reviewer rule HR-06 fires if any FAERS skill_run lacks
`multi_measure_disproportionality` flag (require PRR + ROR + IC25 all run).

## 输出契约

```json
{
  "skill_id": "faers_signal",
  "n_compounds": 0,
  "admet_csv": "",
  "diagnostics": {
    "brain": "pharma",
    "archetype": "pharma"
  }
}
```
