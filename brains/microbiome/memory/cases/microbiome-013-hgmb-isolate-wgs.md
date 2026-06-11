---
case_id: microbiome-013-hgmb-isolate-wgs
microbiome_task: isolate_wgs_pipeline
sequencing_type: WGS_isolate
sample_type: anaerobic_pure_culture
target_organism: human_gut_cultivable_bacteria
reference_db: hGMB + GTDB R220 + KEGG + CARD
dataset_accession: PRJNA482748
biomass_estimate: high
doi: 10.1038/s41587-018-0008-8
key_paper: "Zou Y, Xue W, Luo G, ... Liu SJ. 1,520 reference genomes from cultivated human gut bacteria enable functional microbiome analyses. Nat Biotechnol 37:179–185 (2019)"
key_paper_doi: 10.1038/s41587-018-0008-8
tags: [culturomics, isolate_wgs, anaerobic, hGMB, type_strain, SCFA, butyrate, ARG, comparative_genomics, Liu_Shuangjiang]
method_choice: [SPAdes_or_Unicycler, QUAST, Prokka, dRep, GTDB-tk_or_skani, KEGG_KO, abricate_CARD, fastANI]
status: validated
schema_version: 2
---

# microbiome-013 — 人源肠道菌库 (hGMB) 分离株全基因组流程

## Background — 刘双江老师团队的核心范式

刘双江老师（山东大学微生物技术国家重点实验室 / 中国普通微生物菌种保藏管理中心 CGMCC 主任）团队的标志性贡献：**hGMB（human Gut Microbial Biobank）—— 1,520 株**人源肠道菌（338 物种）的纯培养、全基因组测序与功能注释（Zou Y et al. 2019 *Nat Biotechnol*, DOI 10.1038/s41587-018-0008-8）。后续 mGMB（mouse, Liu C et al. 2020 *Nat Commun*）将这套范式扩展到鼠肠道。

**核心方法学**（这是这条 case 要让 PRAXIS-Microbiome 学会的）：
1. **严格厌氧培养**（修改 GAM/PYG/YCFA 等培养基 + Hungate/Anaerobe Box）
2. **多挑落（multi-pick）+ 16S Sanger** 初筛
3. **分离株 WGS**（HiSeq/NovaSeq PE150）
4. **SPAdes/Unicycler 组装**（不是 MEGAHIT，因为是单基因组）
5. **QUAST + CheckM2 评估**（completeness >95%, contamination <5%）
6. **GTDB-tk / type-strain ANI** 物种鉴定（>95% ANI = 同种）
7. **Prokka 注释 + KEGG KO + CAZy + antiSMASH BGC**
8. **比较基因组学 dRep**（>99.99% ANI 视为同菌株重复）
9. **重点通路**：SCFA（butyrate / propionate / acetate）、ARG（CARD）、bile acid metabolism

## What was done

**Input**：粪便样本 → 厌氧匀浆 → 系列稀释 → 厌氧培养基 96 孔板培养 7–14 天 → 单菌落挑取 → 16S 鉴定（V3V4） → 选择代表菌 WGS。

**Output (in the paper)**：
- 1,520 strains / 338 species / 92 genera
- 264 species 是首次培养（previously uncultured）
- 平均 genome size 3.0 Mb；平均 contigs 47 个
- 揭示 hGMB 拓宽了 16S/shotgun 参考库覆盖 → 基于 hGMB 的 mapping 把 77.6% reads 比对率（vs 50–60% with HMP only）
- 关键 SCFA 产生菌：*Faecalibacterium*、*Roseburia*、*Eubacterium hallii*、*Anaerostipes*、*Butyricicoccus*

## ★ 方法选择决策链

```
"我有一管纯培养分离株 reads"
        │
        ▼
判断: pure culture (single strain) ── ✓ ──→ 分离株 WGS pipeline (本 case 适用)
                                        ├─ SPAdes/Unicycler（不要 MEGAHIT/metaSPAdes）
                                        ├─ QUAST + CheckM2 验质
                                        ├─ GTDB-tk OR fastANI vs hGMB type strain
                                        ├─ Prokka + KEGG KO 注释
                                        └─ 重点通路: SCFA + ARG + 次级代谢
        │
        ✗
        ▼
是 metagenome（社区） ── ✓ ──→ shotgun_taxonomy + mag_assembly_pipeline
```

**Rule-13 触发**：当 `microbiome_task = isolate_wgs_pipeline` AND 用户提交 metagenome pipeline → Reviewer block `MICROBIOME_REVIEW_METAGENOME_FOR_ISOLATE`。

## ★ 排除/不做的事

- ❌ 不用 MEGAHIT 或 metaSPAdes 组装（适用于宏基因组，会浪费时间）
- ❌ 不做 binning（单菌！没有 bin 这件事）
- ❌ 不用 Kraken2/MetaPhlAn 做"群落组成"（只有一株菌）
- ❌ 不用 ASV/OTU 流程（这不是扩增子）
- ❌ 不假设 reference DB 完整 —— hGMB 的核心贡献就是补 264 个 *previously uncultured* 物种

## ★ 失败模式

1. **培养偏好（cultivation bias）**：~30% 肠道菌至今 unculturable；hGMB 也只覆盖 cultivable 部分
2. **单一培养基偏好**：YCFA 偏 SCFA producers，TSA 偏 facultatives —— 多基（multi-medium）必要
3. **污染**：CheckM2 contamination >5% 必须丢弃，常因培养时未单挑干净
4. **物种界定**：95% ANI 是物种阈值，但 *Lactobacillus*/*Faecalibacterium* 内部杂；建议 99.99% ANI 用于同菌株判定
5. **ARG 假阳性**：CARD/RGI 必须用 strict 模式 + protein homology >90%，否则把进化保守序列误判为耐药基因

## ★ Validation

- **Mock community（ZymoBIOMICS D6300）**：8 株分离 WGS → 全部回收，物种 100% 正确（>99% ANI）
- **hGMB 重复测序**（intra-strain 重复）：>99.99% ANI（用于检验单挑纯度）
- **SCFA 通路验证**：*Faecalibacterium prausnitzii* 必须含 butyryl-CoA pathway（K00929 + K01034 + K01035）；如缺则提示分类错误
- **ARG 已知阳性**：*Bacteroides fragilis* CGMCC 1.2415 必须能检出 *cfxA*（cefamycinase）

## Pipeline (which PRAXIS-Microbiome 包装)

```bash
# 1. 质控
fastp --in1 R1.fq.gz --in2 R2.fq.gz --out1 clean_R1.fq.gz --out2 clean_R2.fq.gz \
      -q 20 -l 50 --detect_adapter_for_pe

# 2. 单基因组组装
spades.py -1 clean_R1.fq.gz -2 clean_R2.fq.gz --isolate -t 16 -o assembly/
# 或 unicycler -1 ... -2 ... --short_only

# 3. 评估
quast.py assembly/scaffolds.fasta -o quast/
checkm2 predict -i assembly/scaffolds.fasta -o checkm2/

# 4. 物种鉴定（任一）
gtdbtk classify_wf --genome_dir assembly/ --out_dir gtdbtk/ --extension fasta --cpus 16
# 或（更轻）
skani search assembly/scaffolds.fasta --db skani_hgmb_db/ -o skani.tsv
fastANI -q assembly/scaffolds.fasta --rl hgmb_type_strains.txt -o fastani.tsv

# 5. 注释
prokka --outdir prokka/ --prefix isolate --kingdom Bacteria --addgenes \
       assembly/scaffolds.fasta

# 6. 重点通路 — SCFA / ARG / BGC
diamond blastp -q prokka/isolate.faa --db kegg_ko.dmnd --id 50 --query-cover 70 \
        -k 1 --outfmt 6 -o ko_hits.tsv
abricate --db card prokka/isolate.fna > arg_card.tsv
antismash --output-dir antismash/ assembly/scaffolds.fasta
```

## Output we report

- Assembly stats（contigs / N50 / size）
- CheckM2 completeness + contamination
- Species call (with ANI to nearest hGMB type strain)
- KEGG KO 通路覆盖（特别标注 SCFA 通路 K-numbers）
- ARG 列表（CARD strict）
- BGC 列表（antiSMASH cluster types）
- `reproduce.sh` + `environment.yml` + DB versions

## Related rules

- `13-isolate-wgs-vs-metagenome`（new）— 单菌 vs 社区流程选择
- `04-shotgun-uses-humann-not-picrust`（功能预测一致原则）
- `11-negative-control-low-biomass`（如果是低生物量稀释液，仍需 blank）

## Cross-agent

- → **PRAXIS-Drug**：`natural_product_bgc_from_isolate`（antiSMASH BGC → 药物候选）
- → **PRAXIS-Cell**：分离株细胞表型（如果有）
- ← **PRAXIS-Pharma**：drug-microbe metabolism testing（分离株 in vitro biotransformation）
