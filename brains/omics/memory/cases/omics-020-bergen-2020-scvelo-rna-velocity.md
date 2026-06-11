---
case_id: omics-020-bergen-2020-scvelo-rna-velocity
schema_version: 1
modality: scRNA_seq
study: "Bergen et al 2020, Generalizing RNA velocity to transient cell states through dynamical modeling"
public_accession: "scVelo demos: pancreas (GSE132188), dentate gyrus (GSE95315), erythroid (10.1038/nature25979 reanalysis)"
doi: 10.1038/s41587-020-0591-3
organism: "Mus musculus / Homo sapiens"
tissue: "pancreas / dentate gyrus / erythroid lineage (multi-tissue demonstrations)"
study_design: time_course
assay_subtype: 10x_chromium_v2_with_intron_quantification
cell_type_focus: [trajectory_inference, transient_cell_state]
tools: [scVelo 0.3, velocyto 0.17, kallisto 0.50, alevin-fry 0.8, anndata 0.10, scanpy 1.10]
method_choice: [rna_velocity_dynamical, spliced_unspliced_quantification, velocity_inference, latent_time]
status: validated
validated: true
source: praxis_seed
case_class: success
provenance:
  source_type: literature
  doi: 10.1038/s41587-020-0591-3
  extracted_at: 2026-04-29
tags: [rna_velocity, scvelo, dynamical_model, trajectory, latent_time]
---

# Bergen 2020 scVelo：RNA velocity dynamical model（trajectory 推断的二阶方法）

## Background
RNA velocity（La Manno 2018 首发）用 spliced (s) vs unspliced (u) mRNA 比例推断每个细胞的 transcriptomic 变化方向。**Bergen 2020 scVelo** 升级到 dynamical model（不假设 steady-state），可处理 transient cell state（迅速 turnover 的中间态）。**重要 case**：现代 trajectory 分析的 default tool；与 Palantir / cellRank 互补但不替代。

## What I actually did
1. **Quantification**：必须输出 spliced + unspliced count matrices（不是普通 Cellranger output）
   - **velocyto**: 老牌，慢但稳定
   - **kb_python (kallisto + bustools)** with `--workflow lamanno`：现代快速选择
   - **alevin-fry** with `--rad`：最快，scVelo 0.3 推荐
2. **Read into scVelo**：`adata = scv.read_loom(...)`，spliced 在 `.X`，unspliced 在 `.layers["unspliced"]`
3. **QC + normalize** with scVelo wrappers：`scv.pp.filter_and_normalize(adata, min_shared_counts=20, n_top_genes=2000)` + `scv.pp.moments(adata, n_pcs=30, n_neighbors=30)`
4. **Velocity model 选择**：
   - **stochastic**: 适合大 cell count、相对稳态系统 (legacy steady-state)
   - **dynamical**: 适合 transient state + branch point；slower but more accurate (Bergen 2020 推荐)
5. `scv.tl.recover_dynamics(adata)` → fit per-gene transcription/splicing/degradation rates (kinetic params)
6. `scv.tl.velocity(adata, mode='dynamical')` + `scv.tl.velocity_graph(adata)`
7. **可视化**：
   - **stream plot**: `scv.pl.velocity_embedding_stream` 在 UMAP 上画箭头
   - **grid plot**: `scv.pl.velocity_embedding_grid`
   - **per-gene phase plot**: `scv.pl.velocity` 看 spliced vs unspliced 散点，识别 transient transcriptional bursts
8. **Latent time**: `scv.tl.latent_time(adata)` 给每 cell 一个 0-1 的 pseudotime，比传统 diffusion pseudotime 更稳
9. **Driver gene identification**: `scv.tl.rank_velocity_genes` 找 lineage 特异 driver
10. **Validation**：sanity → 已知 differentiation 轴方向（如 endocrine progenitor → α / β / δ cell）

## ★ 排除/不做的事
- **跑 RNA velocity 但只有 spliced count**：信息量减半；必须 alevin-fry / velocyto / kb_python with intron 模式
- **steady-state 模式跑 transient lineage**：Bergen 2020 证明 steady-state 在 transient state 给反向 velocity
- **Velocity 当 ground-truth trajectory**：是 noisy estimate，需要与 PAGA / Palantir 交叉验证
- **跨 batch / 跨 dataset 直接合并 velocity**：metabolism rate constants 与 batch confound；建议 per-batch fit
- **以 velocity 长度判 transcription rate**：长度受 noise + neighbor density 影响，rank velocity genes 才是正解
- **Skip moments calculation**：`scv.pp.moments` 是 graph-based denoising 必需步
- **Outlier-driven 卡点**：少数 high-velocity outlier cell 会拉箭头方向；建议 robust scaling

## ★ 失败模式
- **Cycling cell biased trajectory**：cell cycle gene 主导 velocity → 推断箭头沿 cycle 方向，掩盖 lineage 信号；解：`scv.tl.score_genes_cell_cycle` 后回归或仅在非 cycling cell 上做
- **Reverse arrows in transient state**：steady-state 模式典型失败；切换到 dynamical
- **Sparse intron counts**：3' 10x library intron 少；read 越长越好（Smart-seq2 全长更佳）
- **Maturation noise**：dropout 高的 gene velocity 估计不稳；filter 共享 count 阈值
- **Latent time 不连续**：branch point 处 latent time discontinuous → mark 为 ambiguous
- **Cross-species velocity**：ortholog 替换基因后 kinetic params 不可比
- **Stochastic noise > biology**：cell count < 200 在 lineage 内难收敛
- **Splicing inhibitor / drug 实验**：扰动了 splicing rate 假设 → velocity 解释完全失效

## ★ 方法选择决策链
```
是否做 RNA velocity?
├─ Trajectory 数据（development / differentiation） → YES, scVelo dynamical
├─ Steady-state 数据（健康成体 atlas） → 没意义；用 scVI cluster + DE
└─ Drug perturbation → 谨慎；splicing 假设可能 broken

Quantification?
├─ 重新跑 fastq → alevin-fry (--rad) 最快，kallisto-bustools 备选
├─ 已有 BAM → velocyto (慢但接受) 
└─ Cellranger output 直接读 → 不行；intron count 缺失

Velocity model?
├─ Default → dynamical (Bergen 2020 推荐)
├─ Cell count > 50k 且要快 → stochastic
└─ Transient state focus → dynamical 必选

下游?
├─ Pseudotime 排序 → latent_time
├─ Driver gene → rank_velocity_genes
├─ Branch probability → integrate with cellRank
└─ Cell-cell communication along trajectory → CellChat 不适合 trajectory，用 SCENIC + velocity 联合
```

## ★ QC sanity check (known answer)
- Anchor (scVelo pancreas 教学数据 GSE132188)：
  - **Endocrine progenitor → α / β / δ / ε cell** velocity 方向应一致（不反向）
  - **β cell mature**: latent_time → 1 端
  - **Ngn3-low → Ngn3-high → Fev+ → mature endocrine**：latent_time 单调上升
  - **scv.tl.terminal_states** 应该把 mature β / α 标记为 terminal
- Pass criterion：lineage 方向正确 + latent_time 单调 + terminal_states 命中已知 mature cell
- Fail criterion：箭头反向 → steady-state 模式问题；latent_time 跳变 → branch 不稳

## Lessons → seeds for rules
1. **RNA velocity 需要 spliced + unspliced 双 matrix**：从 quantification 阶段决定
2. **Dynamical model 默认**（Bergen 2020）；steady-state 仅在 large + steady cohort 用
3. **Cell cycle confound**：不规避会 dominate velocity 方向
4. **Velocity ≠ ground truth trajectory**：与 PAGA / Palantir 交叉验证
5. **Latent time 比传统 pseudotime 稳定**：但 branch point 仍需 caveat
6. **跨 batch fit velocity 分别做**：metabolism 速率常数 batch confound
7. **Validation by known terminal state + lineage marker**：airway smooth muscle / endocrine / blood lineage 都有已知 anchor
