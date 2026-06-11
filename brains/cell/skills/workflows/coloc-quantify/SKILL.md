---
name: coloc-quantify
description: 双 channel colocalization — Pearson r + Manders M1/M2 + Costes randomization 三方合报；自动 (Costes) 阈值；per-cell（mask required）；--simulate 注入 PMP70+catalase peroxisome-like 模拟，期望 Pearson > 0.6。
---

# coloc-quantify

## 一句话原则
**Pearson 永远不单独**：必须 + Manders M1/M2 + Costes randomization；threshold 用 Costes auto（不手设）；whole-image average 不可（per-cell mask）。

## 输入契约
```
--ch1 PATH
--ch2 PATH
--mask PATH              # cell mask (per-cell coloc); else whole-image (warn)
--methods pearson,manders,costes
--n-randomizations INT   # default 1000
--out PATH
--simulate
```

## 输出契约
```json
{
  "pearson": 0.72,
  "manders_m1": 0.65,
  "manders_m2": 0.83,
  "costes_p": 0.001,
  "costes_threshold_ch1": 12.4,
  "costes_threshold_ch2": 8.1,
  "n_cells_analyzed": 24,
  "passed_sanity": true
}
```

## Sanity（case-005）
合成 PMP70+catalase peroxisomal coloc → Pearson > 0.6。

## Cited cases
- cell-005-colocalization
