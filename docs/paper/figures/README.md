# Historical research figures

These figures illustrate earlier framework and governance experiments. They are retained
with their source renderer for inspection; they do not replace the current
[preprint](https://arxiv.org/abs/2609.29221v1) or establish current model eligibility.

The renderer uses recorded numerical constants and source finding identifiers. Supporting
English summaries are in [the analysis summary](../../ANALYSIS-SUMMARY.md),
[the data inventory](../v0.3/data-inventory.md), and
[the consolidated results](../v0.4/RESULTS-CONSOLIDATED.md). Scientific ledger records remain
under `docs/findings`.

| Figure | Topic |
|---|---|
| `Fig1_architecture` | Deterministic message bus, retrieval, and agent roles |
| `Fig2_norman_performance` | Recorded Norman donor/ensemble performance |
| `Fig3_ablation` | Historical governance ablation |
| `Fig4_cross_species` | Species routing, caution, and abstention |
| `Fig5_reliability` | Reliability checks and report structure |

Regenerate with `python make_figures.py` in this directory after installing Matplotlib,
NumPy, and Pillow. The script exports SVG, PDF, TIFF, and PNG. The figures distinguish
mock fixtures, native predictions, advisory rules, and evidence limitations where applicable.
