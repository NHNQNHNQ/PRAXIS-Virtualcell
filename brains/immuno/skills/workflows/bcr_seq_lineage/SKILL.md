# bcr_seq_lineage

BCR-seq longitudinal lineage tree + SHM + BASELINe selection (rule 05).

## Inputs

```json
{
  "fastq_paths_per_timepoint": {"d0": ["pre.fq"], "d28": ["post.fq"]},
  "modality": "bulk" | "sc",
  "germline_db": "IMGT" | "OGRDB",
  "clone_definition": {"V_match": true, "J_match": true,
                       "CDR3_length_match": true, "identity_threshold": 0.9},
  "lineage_tool": "dowser"
}
```

## Outputs

```json
{
  "clones": [...],
  "lineage_trees": [
    {"clone_id": "C0001", "newick": "(...)",
     "root_germline_v": "IGHV1-69",
     "members": [{"seq_id": "...", "timepoint": "d28", "shm_count": 14, "isotype": "IgG1"}]}
  ],
  "shm_distribution": {"mean": 12.4, "p95": 28},
  "baselineselection_per_clone": {"C0001": {"pi_cdr": 0.32, "pi_fr": -0.08}},
  "aid_motif_enrichment": {"WRC": 0.63, "WGCW": 0.21},
  "isotype_switching_events": [{"clone": "C0001", "from": "IgM", "to": "IgG1"}]
}
```

## Tools (real runner, Linux)

- Immcantation suite: Change-O, Alakazam, SCOPer, Shazam
- MiXCR + IgBLAST (V/J/CDR3 + germline)
- dowser (lineage tree)
- partis (HMM clone partitioning)

## --simulate behavior

Mock 5 clones × 3 timepoints with random SHM accumulation + BASELINe selection signal.

## Sanity QC

- ≥ 1 clone with CDR positive selection (BASELINe pi_cdr > 0)
- Class switch correctly detected (≥ 1 isotype switch event)
- Rule 05: Immcantation full stack used (not just MiXCR)
