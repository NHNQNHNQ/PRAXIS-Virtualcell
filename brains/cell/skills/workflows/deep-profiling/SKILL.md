---
name: deep-profiling
description: Cell Painting per-well morphological profile (CellProfiler features 或 DeepProfiler embedding) → DMSO+plate normalize → feature select → UMAP + Leiden cluster → reference compound MoA matching。`--simulate` 注入 known kinase/microtubule/DMSO compounds，期望相同 MoA 落入同 cluster。
---

# deep-profiling

## 一句话原则
**Per-well profile（median of cells）+ per-cell distribution**；DMSO 控制 + plate 归一；feature variance + correlation prune；CellProfiler + DeepProfiler 双 backend cross-check；reference MoA 必须对锚（taxol → microtubule etc.）。

## 输入契约
```
--features-csv PATH         # per-cell features
--backend {cellprofiler,deepprofiler}
--normalize per_plate_median
--reference-compounds PATH  # CSV: compound, smiles, moa
--out PATH
--simulate
```

## 输出契约
```json
{
  "compound_profile_csv": "out/compound_profile.csv",
  "umap_png": "out/umap.png",
  "moa_match_csv": "out/moa_match.csv",
  "n_compounds": 24,
  "moa_recovery_rate": 0.92,
  "passed_sanity": true
}
```

## Sanity（case-007）
模拟 24 化合物（4 kinase, 4 microtubule, 4 DNA-damage, 4 ER-stress, 4 cytotoxic, 4 DMSO）→ 同 MoA 落入同 cluster ≥ 0.7。

## Cited cases
- cell-007-deep-profiling
