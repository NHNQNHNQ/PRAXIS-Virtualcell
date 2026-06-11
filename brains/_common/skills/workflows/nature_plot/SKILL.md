---
skill_id: nature_plot
status: ready
scope: shared  # all 13 PRAXIS agents may use this
description: |
  Canonical plotting helper for any agent that emits figures. Enforces two
  invariants every analysis must satisfy:

  1. **Reproducibility** — same input + same seed → byte-identical PDF + PNG.
     The LLM-generated code path that calls matplotlib otherwise drifts each
     turn (different markers, colours, layout, PDF /CreationDate timestamp).

  2. **Nature MS submission style** — single/double-column widths (89/183 mm),
     7 pt body text in Liberation Sans (Arial-equivalent), 0.5 pt lines, no
     top/right spine, Wong color-blind palette, vector PDF (TrueType fonts,
     editable in Illustrator) plus 600 DPI raster fallback.

  Why this exists: agent users reported "two consecutive analyses give
  different plots" + "plots don't look like Nature". Fix the root cause
  once, in this shared skill, instead of patching each per-agent plotting
  call.
inputs:
  fig_kind: "scatter | volcano | umap | heatmap | survival | boxplot | bar"
  data: "anndata / DataFrame / numpy"
  out_path: "destination (without extension; both .pdf and .png will be written)"
  seed: 42
  width: "single (89mm) | double (183mm) | float-inches"
  height: 2.5  # inches
  palette: "WONG | OKABE_ITO | TOL_BRIGHT | SEQUENTIAL | DIVERGING"
outputs:
  pdf_path: "{out_path}.pdf — vector, TrueType fonts, 0 metadata timestamp"
  png_path: "{out_path}.png — 600 DPI, tight bbox"
  md5: "PDF md5 — should be byte-identical across reruns of same seed"
qc_check:
  must_emit: [pdf_path, png_path]
  reproducibility_invariant: "md5(run1.pdf) == md5(run2.pdf) when seed identical"

# How to invoke (Python, any env)
usage_python: |
  import os, sys
  sys.path.insert(0, os.environ['HERMES_PLOT_STYLE_DIR'])
  from praxis_plot import (
      apply_nature_style, set_seeds, fig, save_figure,
      add_panel_label, italicize_genes,
      WONG, OKABE_ITO, TOL_BRIGHT, SEQUENTIAL, DIVERGING,
  )

  apply_nature_style()         # rcParams: Liberation Sans 7pt, 0.5pt lines, no top/right spine
  set_seeds(42)                # pin random/np/torch/scanpy

  f = fig(width='single')      # 89mm × 2.5in
  ax = f.add_subplot(111)
  ax.scatter(x, y, c=WONG[6], s=3, edgecolor='none')
  add_panel_label(ax, 'a')     # bold 8pt panel label at top-left
  italicize_genes(ax)          # auto-italic for gene-name axis ticks

  save_figure(f, '/path/out')  # writes out.pdf + out.png@600dpi

# Acceptance criterion proven 2026-05-12
proof:
  test: "Same volcano plot, 2 consecutive runs, seed=42"
  result: "PDF md5 fe596630c4e36e604af1f6292b281653 == fe596630c4e36e604af1f6292b281653 (byte-identical)"
  result_png: "PNG md5 7f19cd4f7c31ad27afca6e0e5b3b329f == 7f19cd4f7c31ad27afca6e0e5b3b329f"

required_environment_variables:
  - HERMES_PLOT_STYLE_DIR   # /home/zkyd/data2/mzy/binaries/_styles
  - SOURCE_DATE_EPOCH       # 1700000000 (deterministic PDF metadata)

# Hard rules — agents that emit figures MUST observe
hard_rules:
  - "ALWAYS call apply_nature_style() before any plt.* op"
  - "ALWAYS call set_seeds(seed) BEFORE any stochastic op (UMAP/tSNE/clustering/scVI)"
  - "ALWAYS use save_figure() not plt.savefig() — only the former pins PDF metadata"
  - "PREFER WONG / OKABE_ITO / TOL_BRIGHT for categorical (≤8 classes); never rely on default tab10"
  - "PREFER SEQUENTIAL (viridis) for continuous; DIVERGING (RdBu_r) for log-fold-change / z-score"
  - "Single-column = 89 mm = fig(width='single'); double = 183 mm = fig(width='double')"
  - "Italicize gene names: use italicize_genes(ax) helper"
  - "Use add_panel_label(ax, 'a') for multi-panel figs; never plt.text(...,'a')"

## 输出契约

```json
{
  "skill_id": "nature_plot",
  "matrix_path": "",
  "n_cells_post_qc": 0,
  "cluster_sizes": {},
  "marker_genes_per_cluster": {},
  "umap_png": "",
  "diagnostics": {
    "brain": "_common",
    "archetype": "omics_scrna"
  }
}
```
