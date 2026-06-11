---
rule_id: _default_bootstrap
rule_type: bootstrap
applies_to: [any]
evidence_cases: []
confidence: cold_start
authoring_date: 2026-04-29
source_synthesis_section: cold_start_fallback
---

# Cold-start fallback for PRAXIS-Pharma

When fewer than 3 cases match the query, defer to this template:

1. **Start with NCA** of any available concentration-time data → AUC, Cmax, t1/2.
2. **If species data exist**: cross-species allometric (≥3 species, BW^0.75 default,
   add MLP correction if exponent in 0.55–0.70 band; brain-weight if >0.70 with CNS).
3. **For DDI questions**: identify all CYPs with substrate fm > 0.1; static FDA
   model first; PBPK if available.
4. **For TDM/dose individualization**: use Bayesian forecasting with literature
   popPK prior; never trough-only proportional scaling.
5. **For FIH**: NOAEL × 1/10 (BSA scaling for small mol; BW for biologic); ALWAYS
   add MABEL for any immune-modulating mechanism (post-TGN1412).
6. **Confidence label**: cold_start until ≥ 3 evidence cases accumulate for the
   specific (pharma_task, drug_class) pair.
7. **Always report 95% CI** on every PK estimate.
