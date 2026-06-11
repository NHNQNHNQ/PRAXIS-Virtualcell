---
rule_id: 02-cell-context-aware-efficiency
rule_type: case_distilled
applies_to:
  edit_type: ALL
  cell_context: ALL
evidence_cases: [crispr-001, crispr-003, crispr-004, crispr-007, crispr-008]
confidence: high
---

# Cell-context-aware efficiency

CRISPR efficiency varies **5-10× across cell types**. Always provide a typical-efficiency note for the chosen cell context.

| Cell type | KO (SpCas9 indel) | HDR | Base edit (ABE8e) | Prime edit (PE3) |
|---|---|---|---|---|
| HEK293T | 70-90% | 5-15% | 60-80% | 20-30% |
| HeLa (3n) | 40-60% mosaic | 3-10% | 50-70% | 15-25% |
| K562 | 70-90% | 3-10% | 50-70% | 12-20% |
| iPSC | 60-80% | <1-3% (need NU7441!) | 40-60% | 10-15% |
| HSC (CD34+) | 60-80% | <0.5-2% | 60-80% (mRNA+LNP) | 4-8% |
| Primary T | 80-95% (RNP) | 1-3% | 60-80% | 8-12% |
| HAP1 | 80-95% | 5-15% (haploid simplifies) | 50-70% | 15-25% |
| Hepatocyte (in vivo) | 50-80% (LNP) | <1% | 50-80% (Verve!) | <5% |
| Neuron | 30-60% | <1% | 30-50% | <5% |

**Action:** Never quote a single-number efficiency without naming the cell type.
