---
name: imc-pipeline
description: IMC (Imaging Mass Cytometry) end-to-end pipeline — Steinbock standard：hot pixel removal **必须**, arcsinh transform, Ilastik pixel classifier, Mesmer cell segmentation, scimap neighborhood。检测 Reviewer 强制 hot-pixel block。`--simulate` 注入合成 hot pixels，验证 ratio ≤ 0.001 after filter。
---

# imc-pipeline

## 一句话原则
**Hot pixel 必须先 remove**（detector artifact）；**arcsinh transform 必备**（dynamic range > 1000×；linear 必假阳）；metal isobaric overlap 在 panel design 时检；multi-ROI per tissue 必抽取。

> ⚠️ **Reviewer hard gate**：design_plan 在 `image_modality == IMC` 时 pipeline_steps 必须含 `hot_pixel` step，否则 Reviewer 阻塞且 `required_repairs` 中含 "IMC pipeline missing hot-pixel removal step"。

## 输入契约
```
--mcd-dir PATH                # IMC raw (.mcd files)
--panel PATH                  # CSV: marker, metal, RRID
--hot-pixel-filter            # MUST be present (script aborts if not)
--out PATH
--simulate
```

## 输出契约
```json
{
  "denoised_tiff_dir": "out/denoised/",
  "cell_typing_csv": "out/cell_typing.csv",
  "neighborhood_csv": "out/neighborhood.csv",
  "n_hot_pixels_removed": 1024,
  "hot_pixel_ratio_after": 0.0008,
  "passed_sanity": true
}
```

## Sanity（case-009）
合成 IMC ROI 注入 hot pixel（强 outlier），filter 后 ratio ≤ 0.001。

## Cited cases
- cell-009-imc-multiplex
