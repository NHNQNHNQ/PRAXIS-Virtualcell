---
name: spatial-proteomics-pipeline
description: CODEX/IMC multiplex 影像端到端 pipeline — segmentation (Mesmer 优先) + arcsinh + z-score + Knowledge-based + Leiden cell typing + Squidpy/scimap neighborhood enrichment + germinal-center-like sanity。`--simulate` 模拟 30-marker tonsil ROI，期望 GC cluster 含 CD20+ B + Ki67。
status: green
host_env: PRAXIS-Cell
---

# spatial-proteomics-pipeline

## 一句话原则
**Mesmer/TissueNet 用于 tissue**（Cellpose 是 single-cell oriented）；arcsinh 必备（不能 linear）；double-method cell typing（knowledge + cluster）；marker QC mandatory；spatial sanity（known biology anchors）。

## 输入契约
```
--image-dir PATH          # multiplexed TIFF stack
--panel PATH              # CSV: marker, channel, RRID
--modality {codex,imc}
--segmentation-model {mesmer,cellpose,deepcell}
--out PATH
--simulate
```

## 输出契约
```json
{
  "cell_typing_csv": "out/cell_typing.csv",
  "neighborhood_csv": "out/neighborhood.csv",
  "umap_png": "out/umap.png",
  "cluster_labels_csv": "out/cluster_labels.csv",
  "germinal_center_cluster_present": true,
  "passed_sanity": true
}
```

## Sanity（case-003 / case-009）
Tonsil 模拟 → GC cluster (Leiden cluster 中) 含 CD20+ B + Ki67+ 同时 enriched.

## Cited cases
- cell-003-codex-spatial-proteomics
- cell-009-imc-multiplex
