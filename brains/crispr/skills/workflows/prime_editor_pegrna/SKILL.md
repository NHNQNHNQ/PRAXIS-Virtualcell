---
skill_id: prime_editor_pegrna
description: Design pegRNA + nicking sgRNA for prime editing (PE3 / PE5 + epegRNA). PBS (10-17 nt, Tm 25-35°C) + RT template (10-25 nt, no G runs) + tevopreQ1 motif. ≥3 pegRNA × 2 nicking combos for in vitro screen. MMR status note.
inputs:
  - target_seq: 60+ nt context around edit site
  - edit_position: 1-indexed start of edit in target_seq
  - edit_to: substituted/inserted bases (≤ 20 bp)
  - cell_context: HEK293 / HSC / hepatocyte / neuron
outputs:
  - pegrna_candidates: list of {spacer, pbs, rt_template, full_pegrna_5to3, pbs_tm, n_pegrna_combos}
  - nicking_sgrnas: 2 paired guides on non-edited strand 50-90 nt from edit
  - epegRNA_motif: tevopreQ1 (3' addition)
  - mmr_status_note: MMR-deficient cell types boost PE 7×
  - cell_efficiency: typical efficiency table
sanity_check: KRAS G12D → G12G mock — ≥1 pegRNA with PBS Tm 25-35°C, no G run > 5, scaffold has no edit-identical sequence, PE3 nicking on alternate strand
reference_case: crispr-004-prime-editor-pegrna
---

## Protocol

1. Find spacer (NGG PAM) within 30 nt of edit site (cut to edit < 30 nt).
2. PBS design (10-17 nt) — Tm 25-35°C target (sweet spot 30°C); no G run > 5; no scaffold-self-edit overlap.
3. RT template (10-25 nt) — encodes desired edit + 3'-flanking homology arm.
4. epegRNA: append tevopreQ1 motif (3'-AAACAAACAA—from Nelson et al. 2022 — 2-3× boost).
5. PE3 nicking sgRNA on opposite (non-edited) strand 50-90 nt from edit.
6. Cell-type efficiency note (HEK293 high; HSC/neuron 5-10× lower).
7. MMR-deficient cell line warning (PE5 / dnMLH1 boost).

## Don't

- ❌ PE2-only without nicking sgRNA (efficiency < 5%).
- ❌ PBS Tm outside 25-35°C.
- ❌ RT template containing G run > 5 (synthesis fail).
- ❌ Scaffold contains the edit-identical sequence (self-editing readout failure).
- ❌ Single pegRNA design directly to clinical without ≥3 in vitro screened.

## 输出契约

```json
{
  "skill_id": "prime_editor_pegrna",
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
