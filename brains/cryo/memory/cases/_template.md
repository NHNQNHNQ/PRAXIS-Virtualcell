---
case_id: cryo-XXX-short-slug                # required
schema_version: 1
sample_type: soluble_oligomer               # soluble_oligomer | membrane_protein_complex | supercomplex | virus_capsid | ribonucleoprotein | in_situ_complex | heterogeneous_complex | large_complex | any
target_pdb: ""                              # PDB ID OR null
target_emdb: ""                             # EMDB ID OR null
molecular_weight_kda: 0                     # number, kDa
symmetry_group: C1                          # C1..Cn | D2..Dn | T | O | I | helical | none
resolution_target: "3-4"                    # bin: <2 | 2-3 | 3-4 | 4-6 | >6
resolution_achieved_a: 0.0                  # achieved Å (FSC 0.143)
detector_type: K3                           # K3 | K2 | Falcon4 | Falcon3 | Apollo | none
detergent_or_lipid: none                    # DDM | DDM_CHS | nanodisc | amphipol | SMA | LMNG | GDN | none
method_choice: []                           # tokens: relion_5, cryosparc_v4, ctffind4, topaz, modelangelo, phenix, ...
tools: []                                   # display strings: ["RELION 5", "cryoSPARC v4", ...]
status: proposed                            # proposed | validated | rejected
provenance:
  source_type: literature                   # literature | preprint | methodology | inhouse
  doi: ""
  citation: ""
  extracted_at: 2026-04-29
  extraction_confidence: high               # high | medium | low
  unverified_details: []
tags: []
---

# {Case title}

## Background
{Why this case matters; the technical challenge.}

## What I actually did
{Step-by-step pipeline used.}

## ★ 排除/不做的事
{What NOT to do — at least 4 bullet points. Empty bullets = QA failure.}

## ★ 失败模式
{Failure modes observed — at least 4 bullet points.}

## Lessons → seeds for rules
{Numbered takeaways that distill into rules.}
