---
case_id: cryo-003-supercomplex-ribosome
schema_version: 1
sample_type: ribonucleoprotein
target_pdb: 4UG0
target_emdb: EMD-2847
molecular_weight_kda: 3500
symmetry_group: C1
resolution_target: "3-4"
resolution_achieved_a: 2.9
detector_type: K3
detergent_or_lipid: none
method_choice: [relion_5, cryosparc_v4, multibody_refine, focused_refine, cryodrgn, modelangelo, phenix]
tools: [RELION 5, cryoSPARC v4, Phenix 1.20, Coot 0.9, ModelAngelo 1.0, cryoDRGN]
status: validated
provenance:
  source_type: literature
  doi: "10.1038/nature17943"
  citation: "Khatter H, et al. Structure of the human 80S ribosome. Nature 2015"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
tags: [ribosome, 80S, supercomplex, RNA_protein, multibody, focus_refine, cryoDRGN, large_complex, intersubunit_rotation]
---

# 80S 核糖体：超大复合物的 multibody + focus refinement

## Background
80S 核糖体 ~3.5 MDa (60S + 40S subunits) 是 cryoEM 经典超大复合物。挑战：(1) 40S 与 60S 之间相对运动（intersubunit rotation）→ rigid full refinement 模糊 → multibody / focus refinement；(2) 含 RNA + protein 混合，建模工具不同；(3) 多 functional state（pre-translocation, post, with tRNA, with translation factors）heterogeneity 高。

## What I actually did
1. **Data**：~50k movies K3，足够 particle count (~300k particles)
2. **Initial 3D**：full ribosome refinement → ~3.5 Å（但 40S 区模糊）
3. **Multibody refinement**：split 60S + 40S 作 two rigid bodies → 60S 2.8 Å + 40S 3.0 Å
4. **Focus refinement**：进一步 mask 40S head domain → 改善 head 区 resolution（intersubunit movement 主源）
5. **Heterogeneity (3D classification)**：pre-trans / post-trans / EF-G bound 等 state 分类
6. **3D variability analysis (cryoSPARC)** or **cryoDRGN**：连续 conformational landscape，比 discrete 3D class 信息更多
7. **Model building**：rRNA 先（DRRAFTER / RNAforester），ribosomal protein 用 ModelAngelo + Phenix；tRNA 在合适 state 才能 build
8. **Final**：核心 subunit 2.5-3.0 Å，flexible region (L1 stalk, L7/L12) 5-7 Å 可见但不可建详细 model

## ★ 排除/不做的事
- **不 multibody / focus refinement**：full rigid refinement 在大 complex 必模糊
- **3D classification 不 explore**：functional state 不分开等于平均
- **RNA 用 protein-only model builder**：RNA 残基 mismatch；用 RNA-specific tool
- **Map 整体 sharpening 一刀切**：core vs periphery resolution 差大，local resolution-aware sharpening 才对
- **All-atom build at low-res region**：< 4 Å 区不可信原子级建模；用 polyalanine 或 backbone-only
- **Tab between subunits 不 separately refine**：bridge contacts (eB7 等) 是关键功能区

## ★ 失败模式
- **Intersubunit rotation**：40S 与 60S 之间 ratchet motion 是主要 heterogeneity 源
- **L1 stalk movement**：极柔性区，多 conformer averaged
- **rRNA modification（m6A, pseudouridine）**：cryoEM 不能识别 chemical mod，结构上模糊
- **tRNA occupancy 不一**：A/P/E site tRNA 比例不同，class 中混
- **Ions（Mg²⁺）modeling**：~3000 Mg in ribosome，high-res 才看到
- **Computational cost**：300k particle multibody refine 几天

## Lessons → seeds for rules
1. **Multibody refinement** 对大复合物
2. **Focus refinement** for specific 模糊区
3. **3D classification or cryoDRGN**：functional state 必分
4. **RNA-specific model building tool** for nucleic
5. **Local resolution-aware sharpening**
6. **Ion 建模 only at high local res**
7. **Plan for compute**：大复合物处理 days-weeks 很正常
