---
name: phenotype-landscape
description: 化合物 phenotype landscape — UMAP + Leiden / hdbscan cluster + reference compound MoA anchor + novel cluster 标记。`--simulate` 注入 reference compounds + 1 novel cluster，验证 known compound 同 cluster + 标 novel。
---

# phenotype-landscape

## 一句话原则
**PCA → UMAP → Leiden** 标准 pipeline；reference compound anchor 必须；multi-resolution Leiden sweep；novel cluster（远离任何 reference）单独标记 follow-up；t-SNE 不用（UMAP 在 high-dim 表现 better）。

## 输入契约
```
--profiles-csv PATH          # 1500-feature compound profile
--reference-compounds PATH   # CSV: compound, known_moa
--resolution FLOAT           # Leiden resolution; default 0.8
--out PATH
--simulate
```

## 输出契约
```json
{
  "umap_png": "out/umap.png",
  "cluster_labels_csv": "out/cluster_labels.csv",
  "moa_call_csv": "out/moa_call.csv",
  "novel_clusters_csv": "out/novel_clusters.csv",
  "n_clusters": 7,
  "n_novel": 1,
  "reference_recovery_rate": 0.91,
  "passed_sanity": true
}
```

## Sanity（case-010）
模拟 30 compound（含 4 microtubule reference + taxol query + 1 novel cluster），taxol 应与 microtubule 同 cluster；novel 标记。

## Cited cases
- cell-010-phenotype-clustering
