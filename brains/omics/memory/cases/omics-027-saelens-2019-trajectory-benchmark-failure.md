---
case_id: omics-027-saelens-2019-trajectory-benchmark-failure
schema_version: 1
modality: scRNA_seq
study: "Saelens et al 2019, A comparison of single-cell trajectory inference methods (dynverse benchmark)"
public_accession: "(meta-analysis: 45 trajectory tools × 110 real + synthetic datasets via dynbenchmark)"
doi: 10.1038/s41587-019-0071-9
organism: "Homo sapiens / Mus musculus / synthetic (cross-organism benchmark)"
tissue: "multi-tissue (gold-standard trajectory datasets across tissues)"
study_design: meta_analysis_failure
assay_subtype: trajectory_inference_benchmark
cell_type_focus: [trajectory_topology, branching, cyclic, lineage_inference]
tools: [dynverse 1.0, Slingshot, Monocle 2/3, PAGA, RaceID/StemID, Wishbone, Wanderlust, scTour, Palantir]
method_choice: [trajectory_method_critique, topology_correctness, cell_ordering_correlation, scaling_behavior]
status: validated
validated: true
source: praxis_seed
case_class: failure_landscape
provenance:
  source_type: literature_failure_review
  doi: 10.1038/s41587-019-0071-9
  extracted_at: 2026-05-01
tags: [failure_case, trajectory_inference, benchmark, dynverse, anti_pattern, NEG]
---

# Saelens 2019 dynverse：trajectory inference 方法选择的系统性失败地图

## Background
Saelens 等用 dynverse 基础设施系统比较 45 trajectory 工具 × 110 数据集（gold-standard real + synthetic 拓扑），是 trajectory inference 当前最权威的 benchmark。**核心发现震撼整个 trajectory 社区**：没有方法在所有任务上都赢；选错工具一个 dataset 上得到完全错误的拓扑（线性 vs 分支 vs 环 vs 多分支）；许多论文用了不合适的工具但没意识到。这是 case 020 (scVelo success) 的 counter-balance：trajectory tool 不是即插即用。

## What this paper actually did (and what it found)
1. 用 dynverse 把 45 工具标准化输入输出
2. 110 个 dataset（real cell + synthetic 包括已知拓扑：linear / bifurcation / convergence / cyclic / disconnected）
3. 评估维度：
   - **Topology correctness**: 工具推断的拓扑结构（branching/cyclic/linear）vs ground truth
   - **Cell ordering correlation** (per branch)
   - **Feature importance** ranking
   - **Scaling**: 时间 / memory vs cell count
4. **关键发现**：
   - **Slingshot / PAGA / Monocle DDRTree** 综合表现最好但**仍 ~30% 任务推断错拓扑**
   - **Linear-only methods** (Wanderlust, Wishbone) 在 branching data 上**强迫线性化** → 完全错的 lineage
   - **Cyclic-detection methods** 极少（只 ~5 工具）；非 cyclic 工具应用到 cyclic data → 看似线性但 missing cycle closure
   - **Disconnected components** 多数工具不能正确处理，会强制连接成单 trajectory
   - **跨数据集**: 没有方法在 ≥ 80% 任务上 top-3
   - **小 dataset (< 100 cells)**: 工具间差异大；trajectory 不可信
   - **大 dataset (> 50k cells)**: scaling 差异巨大；多数工具 OOM 或 > 24h

## ★ 排除/不做的事 (反面教材)
- **拿一个 trajectory 工具的输出当 ground truth**：rule 05 在此场景的强化（≥ 2 工具 cross-check 是必备）
- **拓扑信息未知时用 linear-only 工具** (Wanderlust, Wishbone)：会把 branching 强行掰直
- **不做 known anchor (terminal state / starting state) 验证**：trajectory 方向 / 顺序未必生物正确
- **小 dataset (< 200 cells per branch) 下信任 trajectory**：power 不够，结果 seed 敏感
- **Disconnected lineage 用 Monocle DDRTree**：会强制连接形成假桥
- **不报 topology correctness vs cell ordering correlation 双指标**：单指标误导
- **不参考 dynverse benchmark 表选工具**：盲选导致 rate-of-failure 高
- **直接拿 UMAP layout 当 trajectory**：UMAP 是降维不是 trajectory；嵌入拓扑可能与真实 lineage 不同

## ★ 失败模式 (论文记录的)
- **Linear forced on branching**: Wanderlust 在 hematopoiesis (4 lineage) 给出单一 trajectory，误把 erythroid 当 myeloid 中间态
- **Cyclic forced linear**: cell cycle dataset 只看到 G1 → S → G2 → M 线性，missing 闭环
- **Disconnected merged**: PBMC 的 T / B / Mono 各自独立 lineage，被 Monocle 强连成一棵树，不可解释
- **Branching missed**: 弱 branching signal (~5% cells in minor branch) 被 RaceID 等 cluster 类方法 merge
- **Cell ordering correct but topology wrong**: 一些工具 cell-cell distance 学得对但 topology 给错
- **Scaling collapse**: > 50k cells 时 Monocle 2 OOM；scTour 等 GPU 类工具才能 handle
- **Seed-instability**: 不同 random seed → 不同 trajectory；论文需要 ≥ 5 seed 取共识 robust path
- **Pseudotime ≠ real time**: pseudotime 是 latent 排序，不是绝对 time；与 real time-course 关联差时被误解

## ★ 方法选择决策链 (Saelens 给出的)
```
Trajectory inference 任务?
├─ Step 1: 拓扑先验
│   ├─ 已知 linear (单分化轴) → Slingshot / Palantir / Wanderlust
│   ├─ 已知 branching (多 lineage) → Slingshot / PAGA / Monocle 3
│   ├─ 已知 cyclic (cell cycle / circadian) → reCAT / cyclum (rare; few tools)
│   ├─ 多个 disconnected lineage → 分别处理；不强连
│   └─ 拓扑未知 → PAGA + ≥ 2 alternative cross-check
├─ Step 2: 验证 anchor
│   ├─ 已知 terminal state marker
│   ├─ 已知 starting state (e.g. progenitor marker)
│   └─ 沿 trajectory 验已知 differentiation gene 单调
├─ Step 3: cell number per branch ≥ 200; ≥ 5 seed
└─ Step 4: 报 topology + cell ordering 双指标; cite dynbenchmark 表
```

## ★ QC sanity check (known answer)
- Anchor (Saelens dynverse benchmarks)：
  - **Slingshot / PAGA** 在 ~70% 任务上 topology 正确
  - **Linear-only methods** 在 branching data 上 topology 错误 ≥ 50%
  - **Method agreement (≥ 2 tools cross-check)** 显著提高 topology 准确率
  - **Known terminal state** 应位于 trajectory 终点（如 mature β cell）
  - **Cell ordering Spearman ≥ 0.7** with known marker monotonic axis
- Pass criterion: 同一 dataset 上 ≥ 2 tool topology 一致 + cell ordering 与已知 marker 单调
- Fail criterion: 单工具 trajectory 不做 cross-check → 30% 概率拓扑错

## Lessons → seeds for rules
1. **Trajectory inference 必须 ≥ 2 工具 cross-check**（rule 05 强化）— 单工具 30%-50% 错拓扑率
2. **拓扑先验决定工具选择**：linear / branching / cyclic / disconnected 不同分支
3. **Known anchor 是必备验证**：terminal state marker / starting state / sanity 单调
4. **Cell number per branch ≥ 200 + 多 seed**：seed 敏感是 trajectory 普遍问题
5. **UMAP layout ≠ trajectory**：嵌入只是降维，不是 lineage
6. **Pseudotime ≠ real time**：解释时显式区分
7. **dynbenchmark 是 trajectory 工具选择的标准参考表**
