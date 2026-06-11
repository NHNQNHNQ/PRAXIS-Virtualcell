---
case_id: crispr-004-prime-editor-pegrna
schema_version: 1
edit_type: prime_editing
target_gene: KRAS
target_organism: hg38
cell_context: Panc1
editing_system: PE3
delivery_method: plasmid_transfection
tools:
- PrimeDesign
- PEGG
- EpegRNA designer
- CRISPResso2 PE mode
- PrimeDel
key_paper_doi: 10.1038/s41586-019-1711-4
status: validated
provenance:
  source_type: literature
  doi: 10.1038/s41586-019-1711-4
  citation: Anzalone AV et al. (2019) Nature 576:149-157 — Prime editing
  extracted_at: '2026-04-29'
  source: praxis_seed
tags:
- prime_editing
- Panc1
- PE3
- KRAS
- G12D
- epegRNA
- MMR
editing_system_list:
- PE3
- PE5
- epegRNA-PE3
---

# Prime Editing：KRAS G12D 精准回复

## Background
Prime editing（Anzalone 2019）支持任意小 substitution + small indel 而无 dsDNA break。**比 BE 更灵活但效率低**（typical 5-20% vs BE 30-60%）。pegRNA = sgRNA + RT template + PBS（primer binding site）。设计极其敏感：PBS/RT length / spacer / nick 位置都要 tune。

## What I actually did
1. **目标编辑**：KRAS c.35G>A (G12D) → 反向 c.35A>G
2. **pegRNA 设计**（PrimeDesign）：
   - **Spacer**（20 nt sgRNA）：cut 距 edit 位 < 30 nt
   - **PBS（10-17 nt）**：复合 melting Tm ~30°C；过短 RT 启动差，过长 secondary structure
   - **RT template（10-25 nt）**：含 desired edit + 同源臂；最近 G/C run 影响 stability
3. **PE3 nicking sgRNA**：在 non-edited strand 距 edit 50-90 nt 处 nick → 提升 5-20×
4. **epegRNA optimization**：3' tevopreQ1 motif 防止 pegRNA 3' degradation，提升 2-3×
5. **PrimeDesign output ranking**：Top 3 pegRNA × 2 nicking sgRNA = 6 组合 → all in vitro test
6. **预计效率**：Panc1 cell line PE3 + epegRNA 通常 10-25% pure edit；indel byproduct 5-10%
7. **Validation**：amplicon-seq + CRISPResso2 PE mode（separately quantify pure edit / scaffold incorporation / indel）

## ★ 排除/不做的事
- **PE2 不加 nicking sgRNA**：效率 < 5%，临床场景不达 threshold
- **PBS Tm 跨 25-35°C 范围外**：< 25°C 不启动；> 35°C 二级结构主导
- **RT template 含 G run > 5**：合成 + 转录失败
- **pegRNA scaffold 内含编辑相同序列**：自我编辑 readout 错乱
- **Single pegRNA design 直接进 in vivo**：pegRNA 设计极敏感，必须 in vitro screen 多组合
- **不评估 scaffold incorporation**：pegRNA 3' RT 区被插入 genome 是 PE 特有 byproduct

## ★ 失败模式
- **Cell type-dependent efficiency**：HEK293 高效但 hepatocyte / HSC / neuron 低 5-10×
- **PBS / RT length 极敏感**：1-2 nt 改变效率 ±50%
- **Scaffold readthrough**：~3-5% 编辑伴随 pegRNA scaffold 残留
- **Mismatch repair 影响**：PE2 在 MMR-proficient cell 效率低；MLH1 KO + PE2 提升 7×（PE5 era）
- **Bystander indel**：nicking sgRNA 偶 indel
- **Long edit (> 20 bp)**：PE 适合 < 20 bp，长 edit 走 HDR 或 large-scale insertion 工具

## Lessons → seeds for rules
1. **PE3 + epegRNA 是 default**，PE2 only experimental
2. **多 pegRNA in vitro screen 必须**：每 target 设计 ≥ 3 pegRNA × 2 nick
3. **PBS Tm 30°C** sweet spot
4. **Cell type 报告效率**：临床应用预实验在 target cell type
5. **Validation 用 PE-aware tool**：CRISPResso2 PE mode，区分 pure / scaffold / indel
6. **MMR status 评估**：MMR-deficient 高效 PE；可能要并 dnMLH1
