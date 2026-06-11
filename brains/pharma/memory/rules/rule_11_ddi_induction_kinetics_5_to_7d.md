---
rule_id: rule_11_ddi_induction_kinetics_5_to_7d
rule_type: case_distilled
applies_to: [ddi, pbpk]
evidence_cases:
  - pharma-014-rifampin-induction-ddi
  - pharma-003-cyp3a4-ddi
  - pharma-002-pbpk-modeling
confidence: high
authoring_date: 2026-04-30
source_synthesis_section: induction kinetics + temporal DDI
---

# DDI 诱导 5-7 天动力学 (反向 vs MBI 时间尺度)

DDI mechanism dictates time-course:

| Mechanism | Onset | Offset | Magnitude |
|-----------|-------|--------|-----------|
| Reversible inhibition | hours | hours (after washout) | up to ~50× per FDA static |
| MBI (covalent) | hours-days | days (CYP turnover) | 5-15× typical |
| Induction (PXR/AhR) | **5-7 days** (de novo synthesis) | **5-7 days** (CYP3A4 t½ ~36h × 5) | up to 50-fold (rifampin) |

## Why it matters

- **Static FDA model gives the steady-state AUCR but ignores time-course.**
- Patient on rifampin day 1 = no induction yet → midazolam at standard dose works.
- Same patient day 7 = full induction → midazolam fails dramatically (case-014).
- Stop rifampin day 14 = CYP3A4 still elevated for 5-7 d after → drug interactions persist into "post-rifampin" window.

## Mandatory operations

1. **Specify time-of-prediction** in DDI analysis: pre-induction vs steady-state
   vs post-washout phases give different AUCR.
2. **Drug-holiday duration**: if switching off inducer, allow ≥7 d before
   re-introducing affected substrate; ≥14 d if substrate has narrow window
   (warfarin, statins, immunosuppressants).
3. **Auto-induction**: rifampin auto-induces its own metabolism — multiple-
   dose CL > single-dose CL. Use steady-state rifampin parameters in DDI predictions.
4. **Substitution rifampin → rifabutin** (Ind_max 4 vs 12) for HIV PI co-therapy.
5. **PBPK refinement** for high-magnitude inducers (>5× AUCR) — static under-
   predicts because gut-wall CYP3A4 induction not separately modeled (case-014).

## Reviewer soft-flag triggers

- DDI assessment without explicit timeframe → flag for clarification.
- Inducer + substrate co-prescription without inducer-substrate scheduling plan → flag.
