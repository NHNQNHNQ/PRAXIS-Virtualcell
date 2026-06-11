---
name: dose-response-fit
description: 4PL dose-response 拟合 (scipy.optimize.curve_fit)，输出 EC50 + 95% CI + Hill + R² + plateau check + bell-shape detection。`--simulate` 注入 taxol-like EC50 ≈ 5 nM 数据，断言拟合在 published 5× 内。
---

# dose-response-fit

## 一句话原则
8-12 concentration × 4 orders of magnitude；plateau 必须达到；CI on EC50 不能跨 10×；Hill ~ 1（>4 通常 fit artifact）。

## 输入契约
```
--data-csv PATH     # columns: concentration_M, response, replicate
--x-col STR         # default 'concentration_M'
--y-col STR         # default 'response'
--model 4PL         # only 4PL supported in v0.1
--out PATH
--simulate
```

## 输出契约
```json
{
  "ec50": 5.1e-9,
  "ec50_ci_low": 3.0e-9,
  "ec50_ci_high": 8.5e-9,
  "hill": 1.05,
  "top": 100.0,
  "bottom": 2.1,
  "r2": 0.992,
  "plateau_reached": true,
  "bell_shape_detected": false,
  "plot_png": "out/dr_curve.png",
  "passed_sanity": true
}
```

## Sanity（case-006）
合成 taxol-like dose-response (EC50=5e-9 M) → 拟合得到 EC50 ∈ [1e-9, 25e-9]（5× 范围）。

## Cited cases
- cell-006-dose-response-fitting
