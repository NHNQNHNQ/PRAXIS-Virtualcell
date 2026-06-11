---
name: live-cell-track
description: Time-lapse 单细胞追踪 — Cellpose mask + LAP/btrack linker + gap closing + mitosis detection（spatial proximity + size halving）+ lineage tree。`--simulate` 模拟 50 个分裂细胞，期望 lineage 准确 ≥ 0.9。
status: green
host_env: PRAXIS-Cell
---

# live-cell-track

## 一句话原则
**LAP/btrack tracker + gap closing**；mitosis = spatial proximity + size halving + 时间相邻；focus drift / photobleaching 提前补偿；DL segmentation 必备（不可逐 frame independent）。

## 输入契约
```
--movie PATH                   # multi-frame TIFF stack
--segmentation-mask-dir PATH   # one mask per frame (output of cellpose-segment)
--linker {lap,btrack}
--gap-closing INT              # default 2 frames
--out PATH
--simulate
```

## 输出契约
```json
{
  "tracks_csv": "out/tracks.csv",
  "lineage_tree_json": "out/lineage_tree.json",
  "mitotic_events_csv": "out/mitotic_events.csv",
  "n_tracks": 50,
  "n_mitoses": 12,
  "lineage_accuracy": 0.94,
  "passed_sanity": true
}
```

## Sanity（case-004）
合成 50 cell 时间序列（含 12 mitotic events）→ tracker 识别正确 lineage 比例 ≥ 0.9。

## Cited cases
- cell-004-live-cell-tracking
