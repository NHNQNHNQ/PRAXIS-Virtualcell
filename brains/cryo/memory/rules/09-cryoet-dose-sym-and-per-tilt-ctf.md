---
rule_id: 09-cryoet-dose-sym-and-per-tilt-ctf
schema_version: 1
rule_type: case_distilled
applies_to:
  sample_types: [in_situ_complex]
  modalities: [cryoET]
evidence_cases:
  - cryo-007-cryoet-subtomogram
confidence: high
last_updated: 2026-04-29
---

## 规则
**CryoET tilt series MUST use a dose-symmetric scheme AND per-tilt CTF estimation.**

- **Dose-symmetric (Hagen 2017)**: start at 0°, alternate ±3° steps outward. Continuous-tilt schemes burn the high-information low-tilt frames.
- **Per-tilt CTF (CTFFIND4 tilt-aware mode)**: defocus changes with tilt; assuming constant defocus introduces phase errors at high tilts.

Additional STA musts:
- Missing-wedge-aware refinement (RELION 4 / Warp+M).
- Multi-tomogram dataset (≥ 5).
- Low-pass filtered template (avoid model bias).
- FIB-milling lamella for cell thickness > 300 nm.

## Reviewer block codes
- `CRYO_REVIEW_TILT_NOT_DOSE_SYM`
- `CRYO_REVIEW_PER_TILT_CTF_MISSING`
