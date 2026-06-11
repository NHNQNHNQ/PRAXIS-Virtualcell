---
rule_id: 01-edit-type-pipeline-routing
rule_type: case_distilled
applies_to:
  edit_type: ALL
  cell_context: ALL
evidence_cases: [crispr-001, crispr-003, crispr-004, crispr-005, crispr-006, crispr-007, crispr-008, crispr-009, crispr-010]
confidence: high
---

# Edit-type-aware pipeline routing

The 8 CRISPR `edit_type` values **route to completely different pipelines** — a single "design CRISPR" agent that ignores edit_type will produce wrong output.

| edit_type | Required skill | Latest editor | Cardinal "don't" |
|---|---|---|---|
| knockout_indel | sgrna_design_score | SpCas9 | single guide on polyploid |
| off_target_landscape | off_target_predict | n/a | trust in silico for clinical |
| base_editing_a_to_g / c_to_t | base_editor_design | ABE8e / CBE4max | ABE7.10 / CBE3 |
| prime_editing | prime_editor_pegrna | PE3 + epegRNA | PE2-only |
| multiplex_knockout | multiplex_array_design | enAsCas12a | lentivirus for clinical |
| pooled_screen | screen_analysis_mageck | SpCas9 + Brunello | single time point |
| sge | sge_library_design | SpCas9 + ssODN | diploid cell line |
| knock_in_hdr | hdr_donor_design | SpCas9 | no PAM destroy |
| rna_targeting | cas13_grna_design | RfxCas13d | Cas13 as DNA editor |
| in_vivo | in_vivo_delivery_planner | SaCas9 / ABE8e | AAV without NAb screen |
