---
skill_id: multiqc_aggregate
status: ready
description: |
  Parse MultiQC's structured JSON (`multiqc_data.json`) and apply the rule 03
  gate. Returns per-sample mapping_rate / adapter_pct / rrna_pct / library_size
  CV plus the overall pass/fail. **No external dependencies** — Python stdlib
  only — so this skill runs in any environment. MultiQC itself must be invoked
  upstream (via the user pipeline) to produce the JSON.
inputs:
  qc_input_dirs: "list[str] (e.g. fastp/, salmon/, star/)"
  output_dir: "runs/<task_id>/multiqc"
  gate_thresholds:
    mapping_rate_min: 0.70
    adapter_pct_max: 30.0
    rrna_pct_max: 50.0
    library_size_cv_max: 0.5
outputs:
  html_report: "runs/<task_id>/multiqc/multiqc_report.html"
  json_data: "runs/<task_id>/multiqc/multiqc_data/multiqc_data.json"
  gate_result: "runs/<task_id>/multiqc/gate_result.json"
  metrics:
    overall_pass: bool
    failed_samples: list[str]
    failed_metric_per_sample: dict[str, list[str]]
qc_check:
  must_emit: [overall_pass, failed_samples]
  warn_if:
    overall_pass: false  # gate fail = surface to user
evidence_cases:
  - omics-010-bulk-airway-salmon-deseq2
related_rules:
  - 03-bulk-de-priors
  - 12-reproducibility-and-provenance
---

# multiqc_aggregate

## Purpose
Mandatory per rule 03 (case 010): "MultiQC 聚合是 mandatory step 不是可选;
mapping rate < 70% 阻塞 pipeline". This is the gate the bulk_de_pipeline
skill checks before proceeding to DE.

## Algorithm
1. Run `multiqc {qc_input_dirs} -o {output_dir}` to generate HTML + JSON.
2. Parse `multiqc_data.json` to extract per-sample metrics:
   - salmon: `Mapped pct`, library type
   - fastp: `pct_adapter`, `Q30_rate`, `read1/read2 mean length`
   - STAR (if used): `Uniquely mapped %`, `% reads mapped to multiple loci`
   - rRNA contamination (sortmerna or salmon biotype): `pct_rrna`
3. Apply gate thresholds; record per-sample which metrics failed.
4. Emit `gate_result.json` with `overall_pass`, `failed_samples`,
   `failed_metric_per_sample`.

## Reference: case 010
> 不看 MultiQC 直接进 DE：mapping rate 50% 也能跑出 DE 但全部 noise。
> rRNA contamination：library prep 不干净 → 80%+ reads 比对到 rRNA, 剩余太少 power 不足。

## 输出契约

```json
{
  "skill_id": "multiqc_aggregate",
  "matrix_path": "",
  "n_cells_post_qc": 0,
  "cluster_sizes": {},
  "marker_genes_per_cluster": {},
  "umap_png": "",
  "diagnostics": {
    "brain": "omics",
    "archetype": "omics_scrna"
  }
}
```
