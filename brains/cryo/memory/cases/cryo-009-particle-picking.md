---
case_id: cryo-009-particle-picking
schema_version: 1
sample_type: any
target_pdb: null
target_emdb: null
molecular_weight_kda: null
symmetry_group: any
resolution_target: any
resolution_achieved_a: null
detector_type: K3
detergent_or_lipid: any
method_choice: [topaz, cryolo, warp_picker, relion_autopick, cryosparc_blob, eman2_e2boxer]
tools: [Topaz 0.2.5, crYOLO 1.9, Warp 1.0, RELION autopick, cryoSPARC v4 blob picker, EMAN2 2.99]
status: validated
provenance:
  source_type: literature
  doi: "10.1038/s41592-019-0575-8"
  citation: "Bepler T, et al. Positive-unlabeled convolutional neural networks for particle picking in cryo-electron micrographs. Nat Methods 2019 (Topaz)"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: ["Methodology case — no specific PDB/EMDB; covers picking pipeline general"]
tags: [particle_picking, Topaz, crYOLO, blob_picker, multi_picker_consensus, 2d_classification, junk_class, training_set, pre_reconstruction]
---

# Particle picking：上游选择决定下游一切

## Background
错的 picking → 错的 dataset → 错的 reconstruction。手 pick 太慢（10k 粒子要 hours），template-based 引入 bias，DL-based（Topaz / crYOLO）成主流。**picking accuracy = recall + precision 之间 tradeoff**。

## What I actually did
1. **Manual picking 100 micrograph 训练 set**（200-500 particles）
2. **Topaz training**：positive picks + negative regions → CNN 训练 ~30 min on GPU
3. **Topaz pick all dataset**：threshold 决定 recall vs precision；start 中等 threshold
4. **crYOLO**：alternative，用 general model first，再 fine-tune
5. **2D classify after picking**：look at junk classes → estimate junk %；若 > 50% 重训 picker
6. **Blob picker (cryoSPARC)** as baseline：参数 size + shape；适合 isolated globular protein
7. **比对 multi-pickers**：Topaz + crYOLO + blob → consensus = high confidence picks
8. **典型工作流**：blob initial → 2D class → train Topaz on good 2D classes → re-pick → 2D again → 3D refine

## ★ 排除/不做的事
- **Template picking with high-res template**：model bias 引入 reconstruction
- **Single picker 无 cross-validation**：不同 picker miss 不同 particles
- **No 2D classify post-picking**：junk 不剔除 → noisy reconstruction
- **Pick threshold 太松**：太多 junk，2D classify 也清不干净
- **Pick threshold 太严**：丢 rare orientations / smaller particles
- **不更新 training data**：sample 改变（detergent / buffer）需重训

## ★ 失败模式
- **Carbon hole edge bias**：edge 粒子 overrepresented；center 应主筛
- **Large junk (gold beads, contaminants)**：pickers 学不会避开 → 必须先过滤
- **Crowded particles**：dense 区域 overlapping particles 选不准
- **Small particle (< 100 kDa)**：CNN 学不出，blob picker + manual review 仍主力
- **Mixed populations**：>1 species 同 grid，picker 会混合都选
- **Different defocus group bias**：defocus 大小影响 contrast，picker 在 high-defocus 表现好

## Lessons → seeds for rules
1. **DL picker (Topaz/crYOLO) > template picking**
2. **Manual training 200-500 particles** for fine-tune
3. **2D classify post-picking** 必步检查 junk %
4. **Multi-picker consensus** for high-quality
5. **Iterative refinement**：3D refine OK 后用其 2D class 当 picker training data
6. **Small particle / mixed populations** 警告
