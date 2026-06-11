---
skill_id: salmon_quant
status: ready
description: |
  Quantify transcripts from FASTQ using salmon. Mandatory flags (rule 03):
  --gcBias --seqBias --validateMappings --libType A. Reads paired/single-end
  layout, captures mapping rate from log, summarizes via tximeta to gene-level
  counts. Refuses to silently default --libType ISR/ISF (case 010 anti-rule).
  Production: real subprocess dispatch when salmon is on PATH; plan-only mode
  emits the exact command for user-driven runs when binary missing.
inputs:
  fastq_paths: "list[str] (paired or single-end .fastq.gz)"
  index_path: "salmon prebuilt index (FASTA + GTF version-locked)"
  gencode_release: "e.g. v44 — must match index"
  threads: 8
  paired: true
  random_seed: 0
outputs:
  quant_dirs: "list[runs/<task_id>/salmon_quant/<sample>]"
  tximeta_se: "runs/<task_id>/salmon_quant/tximeta.rds (SummarizedExperiment)"
  metrics:
    mapping_rate_per_sample: dict[str, float]
    mapping_rate_min: float
    mapping_rate_median: float
    libtype_detected_per_sample: dict[str, str]
    n_samples: int
qc_check:
  must_emit: [mapping_rate_per_sample, libtype_detected_per_sample]
  warn_if:
    mapping_rate_min: "< 0.7"     # case 010: < 70% triggers MultiQC gate
    libtype_inconsistent: true     # different samples got different libtypes
  reject_if:
    libtype_hardcoded_without_check: true
evidence_cases:
  - omics-010-bulk-airway-salmon-deseq2
related_rules:
  - 03-bulk-de-priors
  - 11-anti-rules-failure-modes
  - 12-reproducibility-and-provenance
---

# salmon_quant

## Purpose
Quantify transcripts the right way. Three failure modes (rule 03 / 11) avoided:
1. Hard-coded `--libType ISR/ISF` losing 50% of reads silently → use `A` and verify.
2. Skipping `--gcBias --seqBias` → biased DE rank → wrong pathway calls.
3. Reference version mismatch (index v44 vs metadata v40) → ~5–10% transcripts "missing".

## Algorithm
1. Verify `index_path/info.json` exists and `gencode_release` matches.
2. Per sample, dispatch:
   ```
   salmon quant -i {index} --libType A --validateMappings --gcBias --seqBias \
     -1 R1.fq.gz -2 R2.fq.gz -p {threads} -o quant/{sample}
   ```
3. Parse `quant/{sample}/logs/salmon_quant.log` for mapping rate +
   detected libtype.
4. tximeta::tximeta() → summarizeToGene() → save SummarizedExperiment.
5. If any sample mapping_rate < 0.7 OR libtypes inconsistent → flag for
   MultiQC gate to surface.

## Reference: case 010
> `salmon quant -i gencode_v44_index --libType A --validateMappings --gcBias --seqBias`
> `--libType A` 让 salmon 自动检测链特异性 — 错填半数 read 丢；用 `A` 自动检测后核对 log。

## 输出契约

```json
{
  "skill_id": "salmon_quant",
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
