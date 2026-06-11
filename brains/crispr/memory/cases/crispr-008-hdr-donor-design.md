---
case_id: crispr-008-hdr-donor-design
schema_version: 1
edit_type: knock_in_hdr
target_gene: PPP1R12C
target_organism: hg38
cell_context: iPSC
editing_system: SpCas9
delivery_method: plasmid_transfection
tools:
- Benchling
- SnapGene
- NEBuilder
- CHOPCHOP donor design
key_paper_doi: 10.1038/s41587-019-0325-6
status: validated
provenance:
  source_type: literature
  doi: 10.1038/s41587-019-0325-6
  citation: Roth TL et al. (2018) Nature 559:405-409 — Pooled knockin (HDR donor design
    principles)
  extracted_at: '2026-04-29'
  source: praxis_seed
tags:
- knock_in_hdr
- iPSC
- SpCas9
- AAVS1
- GFP
- PAM_destroy
- HDR_enhancer
- NU7441
- Scr7
delivery_method_list:
- plasmid_transfection
- ssODN_RNP
- dsDNA_RNP
- AAV_donor
cell_context_list:
- iPSC
- HEK293T
---

# HDR donor 设计：safe harbor knock-in 与同源臂优化

## Background
AAVS1（PPP1R12C intron 1）是公认 safe harbor locus——integration 不破坏关键基因 + 表达稳定。GFP knock-in 是 iPSC reporter line 的标准操作。**HDR efficiency 受同源臂长度、donor 类型（ssODN vs dsDNA）、insert 大小、cell type 影响巨大**。

## What I actually did
1. **sgRNA design at AAVS1**：选 well-validated guide (e.g., CCAAATCTCCAGTCACTATG)
2. **Donor type 选择**：
   - **ssODN**（≤ 200 nt）：小 edit / point mutation
   - **dsDNA**（200 nt - 5 kb）：knock-in cassette
   - **AAV donor**：长 cassette + in vivo
3. **Homology arm 长度**：
   - ssODN：35-45 nt each side（asymmetric: PAM-distal arm 长更高效）
   - dsDNA：500-1000 bp each side（plasmid backbone）
4. **Cas9 cut site → insert junction**：< 10 bp 是 ideal；> 30 bp 效率暴跌
5. **PAM destruction**：donor 中 silent mutate PAM 防 re-cutting；synonymous codon 替换
6. **Insertion design**：homology arm + insert + selection cassette（puro/neo + flox）+ optional fluorescent marker
7. **HDR enhancer**：NU7441（DNA-PK inhibitor）+ Scr7（NHEJ inhibitor）增 HDR 2-3×
8. **Validation**：5'/3' junction PCR + Sanger + Southern blot（off-target integration）+ FACS GFP

## ★ 排除/不做的事
- **PAM 不 destroy in donor**：integrated allele 被 re-cut，indel 反复
- **Symmetric homology arm 时不试 asymmetric**：asymmetric arm 提升 HDR 1.5-3×
- **Cut site ≠ insert site**：> 30 bp 距离 efficiency 极低
- **Single junction PCR validate**：5' OR 3' single junction 假阳常见，必双 junction
- **不加 selection**：HDR rate 1-5%，没 selection 找不出
- **iPSC 不优化 HDR enhancer**：iPSC HDR 极低（< 1%），enhancer + Scr7 必备
- **Donor + Cas9 同 plasmid**：donor template 自身被 cut，效率降

## ★ 失败模式
- **Random integration**：dsDNA 高比例 random integration，即使 5'/3' junction PCR 正确仍可能 multiple copy
- **Asymmetric donor 方向错**：ssODN target sense vs antisense strand 影响效率（target non-cut strand 更好）
- **HDR vs MMEJ vs NHEJ 竞争**：cell cycle phase 影响（HDR 仅 S/G2）
- **Cell type sensitivity**：HEK293T HDR ~10%；iPSC ~1%；HSC < 0.5%
- **Off-target HDR**：donor 整合到 off-target Cas9 cut site
- **Long insert efficiency drop**：> 1.5 kb insert HDR efficiency < 1%

## Lessons → seeds for rules
1. **PAM destruction in donor 强制**
2. **Asymmetric homology arm**：试 PAM-distal 长 / proximal 短
3. **Cut site → insert site < 10 bp**
4. **5'/3' junction PCR 双 验证**
5. **HDR enhancer (NU7441/Scr7)** for low-HDR cell type（iPSC/HSC）
6. **Selection cassette + flox** for clean line
7. **Southern blot** for integration copy count
8. **Long cassette → AAV donor** 效率优于 dsDNA plasmid
