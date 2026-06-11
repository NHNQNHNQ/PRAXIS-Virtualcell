---
case_id: drug-001-vina-egfr-screening
project_phase: hit_id
target_uniprot: P00533
target_pdb: 1M17 (EGFR with erlotinib)
target_class: kinase
indication: NSCLC
modality: small_mol_inhibitor
hit_id_method: virtual_screen
representative_compound:
  - chembl_id: CHEMBL553 (erlotinib)
    inchikey: AAKJLRGGTJKAMG-UHFFFAOYSA-N
    smiles: COCCOc1cc2ncnc(Nc3cccc(C#C)c3)c2cc1OCCOC
    activity: IC50=2nM
tools: [AutoDock Vina 1.2.5, GNINA 1.0, RDKit, OpenBabel, Meeko]
key_paper_doi: 10.1002/jcc.21334
status: validated
validated: true
source: praxis_seed
---

# EGFR 虚拟筛选：Vina + GNINA 双 docking + 后筛

## Background
EGFR T790M 是 NSCLC 经典驱动靶点。1M17 与 erlotinib 共结晶，是 docking benchmark 用的"已知答案"——任何 docking 流程跑 erlotinib 应给出贴近 crystal pose 的 top score。

## What I actually did
1. **Receptor prep**：1M17 → 去掉 erlotinib → 加 H（通过 reduce 或 OpenBabel）→ 计算 partial charge → PDBQT 格式（Meeko 处理）
2. **Pocket 定位**：active site center 用 erlotinib 重原子坐标平均；box 22 × 22 × 22 Å
3. **Library prep**：取 ChEMBL EGFR active 1000 条 + decoy 9000 条（DUD-E EGFR set）；3D 化（RDKit ETKDGv3）+ enumerate stereo + protonation states (pH 7.4 用 Dimorphite-DL)
4. **Vina screening**：`vina --receptor egfr.pdbqt --ligand lib.pdbqt --center_x ... --exhaustiveness 32 --num_modes 9`；并行
5. **GNINA 平行**（CNN re-scoring）：vina 给 affinity proxy，GNINA CNN 重新打分 pose——已知 GNINA 在 enrichment 优于 Vina ~5-10%
6. **Top 1% (~100) 取 consensus**：vina 排名 + GNINA 排名加权，两者一致 top → 进入 next stage
7. **Pose visual inspection**：Erlotinib pose RMSD vs crystal < 2 Å = pipeline OK；≥ 5 个已知 EGFR active 在 top 10% = enrichment EF1% > 5
8. **下一步**：Top hits → 50ns MD 稳定性 → MM-GBSA → 选 5-10 进湿实验

## ★ 排除/不做的事
- **Receptor 不去水/去 cofactor**：water-mediated H-bond 在 receptor prep 阶段建模不易，docking 大多数情况水删了；保留特定 conserved water（hinge backbone water）需文献支持
- **不 enumerate protonation states**：~30% 化合物 pH7.4 多种带电状态（咪唑/羧酸），单一态会漏 pose
- **不 enumerate stereo / tautomer**：丢失 50% true binder
- **Box 太大**（40 Å+）：搜索空间膨胀，pose 飘到 surface；box 限 active site ±5 Å
- **Single-conformer ligand**：刚性 ligand OK，柔性 ligand 必须 Vina 内部 enumerate（默认开）
- **跳过 known active 验证**：不测 enrichment 直接 screen 是 black box——已知 active 至少 5 个进 library 跑
- **Apo receptor 直接用**：apo conformation 与 holo 差异大，建议 use holo 结构（已含 ligand 共结晶）

## ★ 失败模式
- **Receptor flexibility 忽略**：kinase DFG-in/DFG-out 影响巨大；docking 单一 conformation 漏掉 type II inhibitor
- **Pose RMSD 假阳**：top score pose 与 crystal RMSD > 4 Å——score 高但 pose 错，下游 MD 无意义
- **Enrichment 太低 (EF1% < 2)**：library prep 或 receptor prep 有错，先排查再 trust 排名
- **ChEMBL noise**：active 数据混 single-replicate 实验、不同 cell line/assay；需筛 ≥ pIC50 6 + reproducible
- **Decoy 选择偏差**：DUD-E decoy 物理性质和 active 太像，docking 难区分；现代 benchmark 用 LIT-PCBA 更严
- **Tautomer state**：guanidinium / hydroxyl / amide 等多 tautomer，错 tautomer 影响 H-bond 模式

## ★ 方法选择决策链
- **为什么 Vina + GNINA 双 docking 而不是单 Vina**：GNINA 的 CNN re-scoring 在 DUD-E enrichment 比 Vina 提升 ~5-10%，但 GNINA 单跑 geometry 不如 Vina 稳；consensus rank（RRF over Vina rank + GNINA rank）兼顾两者。
- **为什么用 1M17 (holo) 而不是 EGFR apo**：apo 与 holo conformation 差异大，docking apo 容易漏掉 type II inhibitor；holo 已经 pre-shape 好 pocket 给类 erlotinib 系列用。
- **为什么 box 22×22×22 Å 而不是更大**：> 30 Å 时搜索空间膨胀，pose 飘到 surface；active site ±5 Å 即可覆盖 ATP pocket。
- **为什么不用 DiffDock**：DiffDock 在已知 ligand pose 重构表现好，但对 novel scaffold pose 准确度不如 Vina/GNINA；新化学空间下用 Vina/GNINA 更稳。

## ★ Multi-objective tradeoff
- **predicted_activity vs selectivity**：EGFR 与 ErbB2 (HER2) 高度同源，强 activity 必须配 selectivity panel（against ErbB1/2/3/4 + 相邻 kinase 30+）。
- **predicted_activity vs ADMET**：高 logP 提高潜在 activity 但触发 hERG 软警告（rule-08 hard-stop = hERG IC50 < 1 μM）；权衡靠 5D composite score。
- **synthesis (sa_score) vs novelty**：novelty 高（与 ChEMBL EGFR active 距离远）通常意味着 unusual heterocycle → SAscore 上升；用 AiZynth 实证步数过滤。
- **decision rule**：top 候选 = composite_score > 0.6 AND no hard_stop_failed AND aizynth_steps ≤ 6。

## Lessons → seeds for rules
1. **Vina + GNINA 双 docking**，consensus rank
2. **Receptor prep 必步**：去 ligand/water (with consideration) + 加 H + 检查 protonation
3. **Ligand prep 三件套**：3D 化 + stereo enum + tautomer/protonation enum
4. **Box 紧**（active site ±5 Å），不放飞
5. **Enrichment 验证强制**：known actives spike-in，EF1% ≥ 5 才 trust
6. **下游 MD 验证**：top docking pose 单一 conformation 不够，50-100ns MD 看 stable
