The organism tools load measured baseline context independently of prediction
models. `list_profiles`, `load_profile`, and `OrganismProfile` are exported from
`praxis_virtualcell.omics`. Only native gene IDs and measured baseline expression
are returned to callers; unknown IDs are listed in `missing_gene_ids`.

The first local profile is `AB5075-AZI000`: PRJNA658638, AB5075, CA-MHB,
untreated Abaum_0017/Abaum_0023 arithmetic condition mean. Its native scale is
`author_log2_tpm_qc_unscaled_ABUW_namespace`; it is not relabelled as TPM or
log2(TPM+1). Time, temperature, growth phase, and detailed genotype remain
unknown. The annotated proteins are reference translations, not measured
sample-specific protein abundance. Treated expression, delta, and MIC cannot
be included in the baseline NPZ or profile provenance schema.

Rebuild the profile into a new output root from the six declared local source
files, without downloading or training:

```sh
.venv/bin/python -m praxis_virtualcell.omics.prepare_ab5075 \
  --source-root data/organisms/_sources \
  --data-root /private/tmp/praxis-organism-rebuild
```

The source directory must contain:

- `abwm/delta_response_v1/ab5075/arrays.npz` and `pairs.csv`
- `abwm/ortholog_response_v1/orthology/reference_features.csv`
- `abwm/ortholog_response_v1/expression_ortholog_mapping.csv`
- `abaumprecise/raw_data/metadata.csv`
- `abaumprecise/interim/metadata_qc.csv`

The adapter selects only `control[0]` for the verified AZI_000 source sample IDs,
checks the strain/medium/condition against metadata, and joins the exact
AB5075_original annotation. It reads no treated or delta array. Existing output
profiles are not overwritten. The original source assets remain single local
entities under `data/organisms/_sources`, with relative links at their archived
paths. Their redistribution terms have not been verified, so source and derived
datasets stay local. Git carries the reconstruction code and request example.

The restored `data_packs` readers support model-independent AnnData/MuData
Pack validation and feature alignment. They do not restore the old predictor
registry, selected-content execution, or multiomics model compiler. A v0.4
selected-content execution Pack is rejected by the standalone validator.
