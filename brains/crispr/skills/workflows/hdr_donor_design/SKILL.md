---
skill_id: hdr_donor_design
description: HDR donor design — choose donor type (ssODN / dsDNA / AAV); compute homology arms (asymmetric for ssODN); enforce PAM destruction (silent codon swap); design 5'/3' junction primers (primer3-py, NON-OVERLAPPING); HDR enhancer recommendation (NU7441/Scr7) for low-HDR cell types.
inputs:
  - locus_seq: 200+ nt of genomic context around the cut site
  - cut_position: 0-indexed location of Cas9 cut (3 nt 5' of PAM)
  - pam_position: 0-indexed start of NGG PAM
  - insert_seq: cargo (could be GFP CDS, point mutation, etc.)
  - cell_context: HEK293T | iPSC | HSC | hepatocyte
outputs:
  - donor_type: ssODN | dsDNA_plasmid | AAV
  - donor_sequence_5to3: full donor with arms + insert + PAM-destroyed
  - left_arm_length / right_arm_length (asymmetric for ssODN)
  - pam_destruction_changes: list of substitutions
  - junction_primers: {5_prime: F+R, 3_prime: F+R} — non-overlapping
  - southern_blot_probe: recommended internal probe
  - hdr_enhancer_recommendation: NU7441 + Scr7 for iPSC / HSC
sanity_check: AAVS1 GFP knock-in mock — PAM destroyed in donor + 5'/3' junction primers do NOT overlap + amplicon length plausible
reference_case: crispr-008-hdr-donor-design
---

## Don't (Reviewer-enforced)

- ❌ Donor without PAM destruction (re-cutting → indel reversal).
- ❌ Single junction PCR validation (false positives — both 5' AND 3' required).
- ❌ Cut→insert distance > 30 bp (efficiency drops sharply).
- ❌ Long insert (> 1.5 kb) via plasmid dsDNA (use AAV donor instead).
- ❌ iPSC / HSC HDR without enhancer.

## 输出契约

```json
{
  "skill_id": "hdr_donor_design",
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
