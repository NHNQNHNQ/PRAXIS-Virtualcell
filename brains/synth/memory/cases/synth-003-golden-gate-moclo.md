---
case_id: synth-003-golden-gate-moclo
task: plasmid_construction
strategy: MoClo (Modular Cloning) Golden Gate
target_construct: pTet-RBS-mCherry-T1::Cas9-T2 dual cassette plasmid
tools: [Benchling, j5/DeviceEditor, NEBuilder, SnapGene, Plasmidsaurus (sequencing)]
key_paper_doi: 10.1371/journal.pone.0016765
status: validated
---

# MoClo Golden Gate：modular plasmid 装配 standard

## Background
Golden Gate（Type IIS restriction enzymes BsaI/BsmBI/SapI）+ MoClo (Modular Cloning) = 多 fragment 一锅装配，4 nt overhang 决定顺序。**优势**：scarless（无残留 enzyme site）、scalable（10+ fragment 可一锅）、standardized (parts library)。

## What I actually did
1. **Parts 选择**：从 MoClo standard parts library（promoter / 5'UTR-RBS / CDS / 3'UTR-Term / connector）
2. **每 part 在 level-0 backbone with BsaI overhang**：A1-B1（promoter） / B2-C2（RBS） etc.；overhang 决定 assembly 顺序
3. **Level 1 装配**：BsaI 切 + ligate → transcriptional unit (TU) e.g., pTet-RBS-mCherry-T1
4. **Level 2 装配**：BpiI/BsmBI 切 level-1 TU → 多 TU plasmid（Cas9 + sgRNA + selection marker）
5. **Reaction setup**：50 ng each part + BsaI-HFv2 + T4 ligase + buffer，37°C 30 cycle / 16°C 5 min cycle，75°C heat-kill
6. **Transform + colony screen**：white/blue (lacZα 替换) + colony PCR + Sanger
7. **Plasmidsaurus full-plasmid sequence**：~10 USD/sample, 完整 verify
8. **典型成功率**：5 fragment ~70%, 10 fragment ~30%

## ★ 排除/不做的事
- **Overhang sequence collision**：4 nt overhang 中 2 个相同 → assembly 错位
- **Internal BsaI / BsmBI site in parts**：必 first scan + remove via silent mutation
- **不用 standard parts library**：custom parts 浪费 effort，library 已 validate
- **Single colony pick**：MoClo 装配偶有 deletion；3-5 colony screen
- **不 full-plasmid sequence**：Sanger only 看 junction，miss internal mutation
- **Linearize backbone manually**：Golden Gate 直接环化 destination vector，不需 pre-linearize

## ★ 失败模式
- **Overhang re-ligate**：palindrome overhang (e.g., GCGC) 自连，efficiency drop
- **High GC overhang**：> 75% GC overhang ligation 效率低
- **Part size mismatch**：超大 part (> 5 kb) ligation 慢
- **Internal BsaI in CDS**：plant / mammalian gene 经常有，需 codon-silent destroy
- **Transformation inhibitor**：reaction 中 NaCl 等需 dilute or purify 前 transform
- **Re-cutting**：destination vector / level-2 backbone 也带 BsaI site → 自切；MoClo 设计避免（e.g., BsaI vs BsmBI 隔代）

## Lessons → seeds for rules
1. **Standard parts library** 优先
2. **Overhang collision check** mandatory
3. **Internal Type IIS site scan + remove**（silent mutation）
4. **Plasmidsaurus / Nanopore full sequencing** for verify
5. **3-5 colony screen** for assembly
6. **Two enzyme system (BsaI + BsmBI)**: level-1 vs level-2
7. **Overhang GC ≤ 60%** 推荐
