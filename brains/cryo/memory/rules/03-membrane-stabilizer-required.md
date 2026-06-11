---
rule_id: 03-membrane-stabilizer-required
schema_version: 1
rule_type: case_distilled
applies_to:
  sample_types: [membrane_protein_complex]
  molecular_weight_kda_below: 200
evidence_cases:
  - cryo-002-membrane-protein-gpcr
confidence: high
last_updated: 2026-04-29
---

## 规则
**Membrane protein samples below 200 kDa MUST include a stabilizer / size-extender.**

Pure GPCR (~40 kDa) or small membrane proteins are below the cryoEM size cutoff. Detergent micelle alone hurts more than it helps (it adds noise without contrast). Standard stabilizers:

| Stabilizer | When to choose |
|---|---|
| **scFv16** | Gαi-Gβ interface stabilization; GPCR-G complexes |
| **mini-Gs / mini-Gi fusion** | Constitutive G-protein activation; lock active state |
| **BRIL T4 lysozyme fusion** | Generic crystallographic stabilizer (also useful in cryoEM) |
| **Camelid nanobody** | When validated nanobody exists for the receptor |
| **Nanodisc / amphipol / SMA / GDN** | When detergent-free reconstitution is preferred |

## Excluded actions
- DDM-only sample preparation for < 100 kDa membrane proteins (almost always fails).
- Skipping the stabilizer to "save time" — failure rate at the microscope is far higher than the prep effort.

## Reviewer block code
`CRYO_REVIEW_MEMBRANE_NO_STABILIZER`
