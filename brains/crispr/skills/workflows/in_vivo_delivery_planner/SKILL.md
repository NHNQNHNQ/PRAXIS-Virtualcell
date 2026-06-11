---
skill_id: in_vivo_delivery_planner
description: In vivo delivery vehicle planner — tissue-specific capsid recommendation (liver: AAV8 / LK03 vs LNP+mRNA; brain: AAV9 BBB; muscle: AAV1/9; retina: AAV5/8); AAV size budget (4.7 kb cargo); SaCas9 / dual-AAV split if size-tight; AAV NAb screen MANDATORY for clinical; macaque NHP study required for IND; long-term off-target follow-up; immunogenicity panel.
inputs:
  - tissue: liver / brain / muscle / retina / lung / heart
  - editing_system: SpCas9 | SaCas9 | ABE8e | PE3 | RfxCas13d
  - clinical: bool
  - rare_disease: bool (may relax NAb screen)
outputs:
  - capsid_recommendation: AAV serotype list (or LNP)
  - alternative: LNP+mRNA if AAV size-tight or NAb-positive patient
  - cargo_size_budget: bp; flag if > 4.7 kb single-AAV
  - dual_aav_strategy: trans-splicing intein if needed
  - nab_screen_required: True if clinical AAV
  - macaque_study_required: True if clinical
  - immunogenicity_panel: Cas9 T-cell + cytokine response
  - long_term_followup: ≥12 month off-target panel
sanity_check: PCSK9 in vivo (case 010) — AAV8 + LNP both recommended; NAb screen flagged; macaque study required; long-term followup planned
reference_case: crispr-010-aav-in-vivo-delivery
---

## 输出契约

```json
{
  "skill_id": "in_vivo_delivery_planner",
  "n_guides": 0,
  "guides_csv": "",
  "best_guide": {
    "seq": "",
    "cfd_score": 0.0,
    "mit_score": 0.0
  },
  "diagnostics": {
    "brain": "crispr",
    "archetype": "crispr"
  }
}
```
