---
rule_id: 18-metabolomics-priors
rule_type: case_distilled
applies_to:
  modality: [metabolomics]
  study_design: ALL
  tissue_class: ALL
  task: [QC, peak_picking, alignment, annotation, pathway]
evidence_cases:
  - case_id: omics-021-pluskal-2010-mzmine-metabolomics
    page_hint: "MZmine 3 / XCMS workflow + annotation tiers + QC pool"
confidence: high
status: active
created: 2026-04-29
---

# Untargeted LC-MS metabolomics priors

## Statement
1. **QC pool injection every 5–10 samples is mandatory** — without it,
   injection drift is invisible and ruins downstream comparisons.
2. **Isotope + adduct grouping is mandatory** — collapses per-feature counts
   from ~20k to ~5k metabolite-level; without it pathway analysis is wrong.
3. **Annotation tier (Level 1–4) must be tracked** — mechanistic conclusions
   only on Level 1 (authentic standard) or Level 2 (MS² library match).
4. **Cross-mode (positive + negative) — analyze separately, merge at
   annotation level only.**
5. **Internal standards (deuterated) spike-in** for quantitative
   metabolomics — mandatory for cross-batch comparison.
6. **m/z tolerance 5–10 ppm** for high-resolution Orbitrap / TOF; no looser.
7. **Sample prep dominates** — plasma vs urine vs tissue have entirely
   different workflows.

## Annotation level rubric (from Schymanski et al 2014 + Pluskal context)
| Level | Description | Allowed downstream use |
|---|---|---|
| 1 | Authentic standard (m/z + RT + MS²) | mechanistic claims OK |
| 2 | Spectral library match (MS²) | putative annotation; mechanism with caveat |
| 3 | Class match (functional group) | broad-stroke pathway only |
| 4 | Unknown but reproducible feature | statistical only; cannot interpret |

## Decision tree
```
Untargeted LC-MS metabolomics?
├─ Sample
│   ├─ Plasma / serum → both pos/neg modes; protein precipitation prep
│   ├─ Urine → pos primary; creatinine normalize
│   ├─ Tissue → polar + nonpolar extracts separate
│   └─ Cell extract → quench rapidly
├─ Instrument
│   ├─ Orbitrap (HRMS) → MZmine 3 / XCMS
│   ├─ TOF DIA-friendly → MS-DIAL
│   └─ Triple quad targeted → different workflow (skip this rule)
├─ Quantification
│   ├─ Untargeted relative → MZmine 3 default
│   └─ Quantitative absolute → spike-in calibration curve required
└─ Annotation
    ├─ Maximum Level 2 → public databases (METLIN/NIST/GNPS/HMDB)
    ├─ Level 1 → in-house standard library required
    └─ Unknown → SIRIUS 5 in silico annotation OK (still Level 3)
```

## Cold-start fallback
- If instrument unknown → ask; tolerance and noise threshold differ.
- Without QC pool → confidence: low; cross-batch comparisons not allowed.
- Without internal standards → confidence: low for any quantitative claim.

## Sanity anchors
- Plasma untargeted positive mode: 5000–10000 features post-grouping
  (Orbitrap typical).
- Pooled QC injection CV < 20% on top 80% features.
- Internal standard RT shift < 0.05 min, intensity CV < 15%.
- Known abundant: creatinine in urine, glucose in plasma — should be in top
  20 intensity peaks.

## Linked anti-rule sections (rule 11)
Metabolomics-specific: skip QC pool, miss isotope/adduct grouping, cross-
mode merge as features, mechanistic claims on Level 3 annotations,
inter-laboratory direct merge.
