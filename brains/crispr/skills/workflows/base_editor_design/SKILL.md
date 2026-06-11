---
skill_id: base_editor_design
description: Design ABE / CBE base editor sgRNA — pick latest editor (ABE8e / CBE4max); position target base in protospacer 4-8 window; predict bystander A/C edits with BE-Hive heuristic; flag Cas9-independent off-target (TadA hyperediting risk).
inputs:
  - target_seq: 30-50 nt context around target base (with target marked)
  - target_position: 1-indexed position in target_seq of base to edit
  - edit_type: A2G (ABE) or C2T (CBE)
  - cell_context: HSC / iPSC / etc.
outputs:
  - editor: ABE8e (default) or CBE4max
  - sgrna: 20-nt protospacer (target_pos within window 4-8)
  - bystander_table: list of (position, base, predicted_edit_rate)
  - cas9_independent_risk: HIGH/MED/LOW
  - delivery_recommendation: mRNA+LNP > lentivirus
sanity_check: HBB-mimic (BCL11A enhancer) — target A in window 4-8, bystander predicted, ABE8e default, Cas9-indep flag emitted
reference_case: crispr-003-base-editor-abe
---

## Protocol

1. Identify NGG PAMs around target_position; pick those that place target in protospacer 4-8 window.
2. Editor selection:
   - A2G → ABE8e (default; ABE7.10 BLOCKED)
   - C2T → CBE4max (default; CBE3 BLOCKED)
3. Bystander prediction: BE-Hive heuristic — same-window bases edited at scaled rate.
   - ABE8e window 4-8: peak at position 6 (~80% edit), drop-off ±2 positions
   - CBE4max window 4-8: peak at position 5-6 (~70%)
4. Cas9-independent off-target flag: ABE8e has known TadA hyperediting risk (RNA + ssDNA).
5. Delivery: mRNA+LNP recommended for HSC / clinical; lentivirus only for in vitro screen.

## Don't (Reviewer-enforced)

- ❌ ABE7.10 / CBE3 (legacy) — Reviewer blocks.
- ❌ Target base outside protospacer 4-8 window — efficiency drops > 5×.
- ❌ Bystander prediction not reported.
- ❌ Cas9-independent off-target ignored when clinical.

## 输出契约

```json
{
  "skill_id": "base_editor_design",
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
