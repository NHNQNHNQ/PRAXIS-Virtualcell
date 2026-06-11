# neoantigen_pipeline ⭐ MVP

Tumor neoantigen identification from somatic VCF + RNA-seq + 4-digit HLA. Implements rule 01 (multi-method MHC) + rule 02 (HLA 4-digit + LOHHLA) + rule 04 (self cross-reactivity).

## Inputs

```json
{
  "somatic_vcf_path": "tumor.snv.vcf.gz",
  "rna_seq_counts_path": "tumor.RSEM.genes.tsv",
  "hla_alleles_4digit": ["HLA-A*02:01", "HLA-A*03:01", "HLA-B*07:02", "..."],
  "normal_rna_seq_path": "normal.bam",            // optional, for LOHHLA
  "run_loh_check": true,                           // rule 02
  "predictors_class_i": ["NetMHCpan-4.1", "MHCflurry-2", "BigMHC"]
}
```

## Outputs

```json
{
  "skill_id": "neoantigen_pipeline",
  "n_epitopes": 0,
  "epitopes_csv": "",
  "diagnostics": {
    "brain": "immuno",
    "archetype": "mhc_epitope"
  }
}
```

## Tools (real runner, Linux)

- pVACseq (orchestrator), VEP / SnpEff (annotation), LOHHLA (HLA LOH)
- PyClone / SciClone (CCF), NetChop / NetCTL (processing)
- BigMHC-IM / PRIME-2.0 (immunogenicity beyond binding)
- blastp vs UP000005640 (self cross-reactivity)

## --simulate behavior

Read VCF line-count → emit deterministic mocked neoantigens. **Auto-fail** if `hla_alleles_4digit` not all 4-digit format (rule 02).

## Sanity QC

- 4-digit HLA enforcement (rule 02)
- `run_loh_check: true` enforced (rule 02)
- ≥ 2 MHC predictors (rule 01)
- self_similarity_pct ≤ 80% else flagged (rule 04)
