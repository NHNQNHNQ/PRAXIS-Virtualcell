# Figures — PRAXIS-VirtualCell v0.1 manuscript

Publication-grade figures (Nature Methods style), generated with Python/matplotlib via
[`make_figures.py`](make_figures.py). Every number is hard-coded from `docs/findings/*` and annotated
with its source finding in the script. **No values are computed or fabricated at plot time** — the script
is a faithful renderer of the verified findings.

## Regenerate

```bash
cd docs/paper/figures
python3 make_figures.py
```

Requires `matplotlib`, `numpy`, `Pillow` (TIFF). Uses the system `python3` (the project `.venv` does not
ship matplotlib). Each figure is written as **`.svg`** (primary, editable `<text>` nodes), **`.pdf`**,
**`.tiff`** (600 dpi, LZW), and a low-dpi **`.png`** preview (QA only, not for submission).

## Figure index

| File | Manuscript | Conclusion it defends | Data source |
|------|-----------|----------------------|-------------|
| `Fig1_architecture` | Fig 1 | The 10 agent roles communicate only over one auditable MessageBus, with a hard retrieve-before-predict gate and an abstain branch; LLM agents are optional and outside the prediction core. | architecture `file:line` map (this session); finding_w5/w6 |
| `Fig2_norman_performance` | Fig 2 | The communicative wrapper is performance-neutral: the all-5 Coordinator reaches ΔPearson 0.7039, +0.032 over the strongest single base. | finding_w4b_multi_anchor, finding_w4b_coordinator, finding_w4a |
| `Fig3_ablation` | Fig 3 | Five reliability axes move 0→1 from arm A (ML-only) to arm D (full OS) on the same shared predictors. | finding_w7 |
| `Fig4_cross_species` | Fig 4 | Species-aware routing of one fixed task: human applicable, mouse applicable+ortholog caution, bacteria/yeast/unknown rejected → abstain, with no fabricated evidence for the unknown species. | finding_w5 |
| `Fig5_reliability` | Fig 5 | The disagreement→abstain/downgrade→critic→report-split mechanism, with declarative-but-not-yet-active components honestly marked (`*`). | finding_w6 |

## Honesty conventions baked into the figures

- **Fig 2** label states the claim as a +0.032 ensemble gain over the strongest base, not as an
  architecture accuracy gain (the wrapper is element-wise identical to the donor model, atol 1e-6).
- **Fig 3** marks the desired direction per metric (`↑`/`↓ better`) and footnotes the offline-deterministic
  6-seed protocol; the contrast is presence-vs-absence of the OS, not a graded scale.
- **Fig 4** includes an `Unknown (martian)` row and the explicit note "no fabricated rule references for
  unknown species".
- **Fig 5** marks `core-predictor-failed`, `disagreement`, and `cell-type-unsupported` with `*` =
  declarative (unit-test-activated, not firing in the offline mock end-to-end path; finding_w6).

## Editing for submission

SVG text is editable (font not outlined). Open in Illustrator/Inkscape to adjust label positions or
substitute the journal font. Colors follow one neutral + one signal (teal/blue) + directional (green gain /
amber abstain / red reject) family per the nature-figure contract.
