---
name: hcs-hit-call
description: HCS (high-content screening) hit calling — per-well features → B-score (median polish) + z-score / SSMD → hit list + plate heatmap + edge-effect QC。`--simulate` 生成 384-well synthetic plate（含 edge effect + cytotoxic + DMSO + pos ctrl）。Agent 3 (Execution) 标准 HCS pipeline。
---

# hcs-hit-call

## 一句话原则
**B-score + z-score combine 必备**；DMSO control z 中位数应 ~0；pos ctrl z > 3；cytotoxic compound（cell count drop > 50%）必须 separate 标签。

## 输入契约
```
--features-csv PATH      # per-well CSV (columns: plate, well, cell_count, intensity_*, ...)
--plate-layout PATH      # well → compound mapping (DMSO / pos_ctrl 标记)
--normalization {b_score,z_score,ssmd,npi}
--threshold FLOAT        # default 3 for z; 2 for SSMD
--out PATH
--simulate
```

## 输出契约
```json
{
  "hits_csv": "out/hits.csv",
  "b_score_distribution_png": "out/b_score_dist.png",
  "plate_heatmap_png": "out/plate_heatmap.png",
  "n_hits": 12,
  "dmso_z_median": 0.05,
  "pos_ctrl_z_median": 5.2,
  "edge_effect_detected": false,
  "passed_sanity": true
}
```

## Sanity（来自 case-002）
DMSO z median ∈ [-0.3, 0.3]；pos ctrl z median > 3。`--simulate` 合成 384-well plate（4-row gradient + rim evaporation + 12 known active wells），断言以上两条。

## Cited cases
- cell-002-hcs-hit-calling
