---
name: nature_plot
description: Shared publication plotting guidance and a bootstrap execution receipt
status: ready
scope: shared
---

# Publication plotting guidance

Use reproducible seeds, accessible colors, clear units, and traceable source
values. Export vector figures and a suitable raster preview. Declare the styling
utility and environment used to generate each scientific figure.

The bundled `run.py` is a bootstrap placeholder. It emits structured simulation
or execution receipts and does not generate publication figures. The actual
repository figure generators are under `docs/paper/figures` and
`docs/paper/v0.8-NMI/figures`.

An external `praxis_plot` helper may be used only when its installation path is
explicitly configured through `HERMES_PLOT_STYLE_DIR`. It is not bundled here.

## Inputs

- `simulate`: return a marked simulation receipt.
- `seed`: reproducible seed, default 42.

## Output contract

```json
{
  "skill_id": "nature_plot",
  "matrix_path": "",
  "n_cells_post_qc": 0,
  "cluster_sizes": {},
  "marker_genes_per_cluster": {},
  "umap_png": "",
  "diagnostics": {"brain": "_common", "archetype": "omics_scrna"}
}
```

Empty fields are placeholders and do not indicate completed scientific analysis.
