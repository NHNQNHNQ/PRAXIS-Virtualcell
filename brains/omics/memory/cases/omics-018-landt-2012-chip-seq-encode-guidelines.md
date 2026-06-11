---
case_id: omics-018-landt-2012-chip-seq-encode-guidelines
schema_version: 1
modality: chip_seq
study: "Landt et al 2012, ChIP-seq guidelines and practices of the ENCODE and modENCODE consortia"
public_accession: "ENCODE Project (multiple datasets); landmark guidance paper"
doi: 10.1101/gr.136184.111
organism: "Homo sapiens / Mus musculus / Drosophila melanogaster / Caenorhabditis elegans"
tissue: "multi-tissue (cell lines: K562, GM12878, HepG2, H1-hESC + tissues)"
study_design: reference
assay_subtype: chip_seq_tf_and_histone
cell_type_focus: [bulk_tissue_or_cell_line]
tools: [bowtie 2.3, BWA 0.7, MACS2 2.2, MACS3 3.0, IDR 2.0.4, ChIPseeker 1.32, deepTools 3.5, samtools 1.17, ENCODE_ataqv]
method_choice: [macs2_peak_calling, idr_consistency, irreproducibility_discovery_rate, blacklist_filter, encode_tier_qc]
status: validated
validated: true
source: praxis_seed
case_class: success
provenance:
  source_type: literature
  doi: 10.1101/gr.136184.111
  extracted_at: 2026-04-29
tags: [chip_seq, encode_guidelines, peak_calling, idr, methodology]
---

# Landt 2012：ChIP-seq ENCODE 指南（社区做正确 ChIP-seq 的圣经）

## Background
ENCODE 在 ChIP-seq 大规模生产前发布的 community guidelines paper。覆盖 input control 必要性、library complexity 阈值、replicate consistency (IDR)、peak caller 选择、blacklist region 等。**任何做 ChIP-seq / CUT&RUN / ATAC-seq peak calling 的人都该先读这篇**。case-based learning 角度：定义了"什么算合格的 ChIP-seq 实验"。

## What I actually did
1. **Library QC（必查）**：
   - **NSC (Normalized Strand Cross-correlation)** ≥ 1.05 (acceptable), ≥ 1.1 (good)
   - **RSC (Relative Strand Cross-correlation)** ≥ 0.8
   - **PBC (PCR Bottleneck Coefficient)** ≥ 0.5（< 0.5 表示 library 复杂度差）
2. **Read alignment**：BWA-MEM 或 bowtie2，过滤 MAPQ < 30 + duplicates + blacklist regions（ENCODE 提供 hg38/mm10 blacklist BED）
3. **Peak calling**：
   - **TF (point-source)**: MACS2 with `--qvalue 0.05`，narrow peak
   - **histone (broad / mixed)**: MACS2 with `--broad`，broad peak (H3K27me3 / H3K9me3 / H3K36me3)
   - **active marks (H3K4me3 / H3K27ac)**: narrow peak
4. **Replicate consistency（必做）**：**IDR** at threshold 0.05 between biological replicates；非 ENCODE 标准的"两次 peak 取交集"是 inferior
5. **Input control**：每个 IP 必须有 input control（同 chromatin / 同 cell number）；用作 MACS2 control + visualization normalize
6. **Effective genome size**：MACS2 用 hg38 default ~2.9e9（不是 raw genome size）
7. **deepTools 可视化 + correlation**：跨 replicate 计算 fingerprint + heatmap，bigWig coverage track

## ★ 排除/不做的事
- **No input control**：不可解释，任何 enrichment 都可疑；ChIP-seq 没有 input 几乎是 invalidating factor
- **Library complexity (PBC) < 0.5 还跑分析**：duplicate 主导，结果不可信
- **不做 IDR**：随机抽两次 ChIP 都会有"重复" peak，没 IDR 控制率假阳显著
- **Peak caller 不区分 TF vs histone**：用 MACS2 narrow 跑 H3K27me3 → 只能找到几百个超强 peak（错过 broad domain）；用 broad 跑 TF → 边界过宽
- **跨 cell type 的 peak set 直接合并**：cell-type-specific peak 应保留；用 union peak set 跑 differential
- **跳过 blacklist filter**：ENCODE blacklist 是已知伪 enrichment region (rRNA, satellite repeats, etc.)
- **Low duplication 也用默认 dedup**：tissue ChIP 复杂 library 不该 aggressive dedup

## ★ 失败模式
- **Antibody specificity 差**：ChIP-seq 假信号主源；ENCODE 要求 antibody 通过 dot blot + WB 验证，最好 ChIP-MS 鉴定
- **Cross-reactivity**：H3K9me3 antibody 也识别 H3K9me2 → broad domain 过度
- **Input ≠ same chromatin state**：input 来自 sonicated chromatin (correct) vs whole-cell extract (wrong)
- **Library too low complexity**：dup rate > 30% → 真信号被 dup 浪费；考虑重做 library 而非 dedup
- **Cross-laboratory replicate**：不同 lab 用不同 antibody lot → IDR 失败；ENCODE 要求 same lab + same lot biological replicate
- **Blacklist 不够**：tissue 特异 repeat 区不在标准 blacklist 中；需要 per-tissue empty input enrichment 复算
- **Peak caller q-value 调过松**：q < 0.5 的 "peak" 不是 peak

## ★ 方法选择决策链
```
ChIP-seq target type?
├─ TF / point-source → MACS2 narrow + IDR replicate consistency
├─ Active histone (H3K4me3 / H3K27ac / H3K4me1) → MACS2 narrow
├─ Repressive histone (H3K27me3 / H3K9me3) → MACS2 broad
├─ Mixed (H3K36me3) → MACS2 broad with --nomodel + --extsize
└─ CUT&RUN / CUT&Tag → SEACR (sparse signal, narrow / stringent mode)

Replicate consistency?
├─ ≥ 2 biological replicates → IDR (gold standard)
├─ 1 replicate → 强烈 caveat；建议 split sequencing pseudo-replicate IDR
└─ ENCODE Tier 1: ≥ 2 replicates + IDR 0.01 + 各 NSC > 1.1
```

## ★ QC sanity check (known answer)
- Anchor (ENCODE TF ChIP-seq 标准)：
  - **NSC ≥ 1.1**, **RSC ≥ 0.8**, **PBC ≥ 0.5**
  - **IDR pass peak count** 在 known TF (e.g., CTCF) 通常 30k-60k
  - **% reads in peaks (FRiP)**：narrow ≥ 1%, broad ≥ 5%
  - **Replicate correlation (deepTools)**：Spearman ρ > 0.85 between same-target replicates
  - **Known motif enrichment** in top peaks (HOMER findMotifs)：CTCF → CTCF motif top 1, GATA1 → GATA motif top 1
- Pass criterion：3 个 cross-correlation metric 达标 + IDR 通过 + 有 motif enrichment
- Fail criterion：FRiP < 0.5% → 抗体特异性差或 input mishandled

## Lessons → seeds for rules
1. **Input control 是 ChIP-seq 必备**（不是可选） — 缺即 invalidating
2. **IDR 是 replicate consistency 标准**（不是手工取交集）
3. **Peak caller 区分 narrow vs broad target** — H3K27me3 不能用 narrow
4. **NSC + RSC + PBC + FRiP** 是 ENCODE 标准 4 个 library/IP QC metric — 全部必跑
5. **Blacklist filter mandatory** — ENCODE-provided + per-tissue empty input 增量
6. **Antibody validation** 在实验阶段就该做（dot blot + WB）；分析端无法补救特异性差的 ChIP
