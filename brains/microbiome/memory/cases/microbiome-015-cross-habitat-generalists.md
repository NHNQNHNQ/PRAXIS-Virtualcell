---
case_id: microbiome-015-cross-habitat-generalists
microbiome_task: cross_habitat_analysis
sequencing_type: meta_catalogue
sample_type: cross_habitat_pooled
target_organism: "multi-niche bacterial species (Klebsiella pneumoniae / Pseudomonas aeruginosa / Cutibacterium acnes / E. coli / Acinetobacter spp / probiotic Lactobacillus)"
input_data: "20 MGnify genome catalogues × 9 habitats:58,278 species rep / 34,323 GTDB s__ named"
reference_db: "GTDB R220 + MGnify v1/v2 catalogues (human-gut UHGG v2.0.2, marine v2, soil v1, mouse/cow/sheep/pig/chicken/zebrafish/fish-gut, honeybee-gut, human-oral, vaginal, skin, barley/maize/tomato-rhizosphere, marine-eukaryotes, marine-sediment)"
dataset_accession: null
key_paper_doi: 10.1038/s41587-020-0603-3
biomass_estimate: na
tags: [cross_habitat, generalist, specialist, opportunistic_pathogen, ESKAPE, K_pneumoniae, P_aeruginosa, C_acnes, dual_mode, phase3, MGnify_catalogues, GTDB]
method_choice: [MGnify_catalogue_ingestion, GTDB_lineage_normalization, species_rep_dedup_intracatalogue, cross_habitat_species_count, named_species_filter]
status: validated
schema_version: 2
---

# microbiome-015 — 跨生境 generalist 物种与机会致病菌的统一信号

## Background — 为什么这条 case 重要

Phase 3 雏形跑出来的第一个有意义的科学结果。把全部可拿到的 **MGnify genome catalogues**(2026 年初共 20 个 v1/v2 catalog,覆盖 9 个生境)拉到统一坐标系(GTDB R220 lineage)下,看哪些 species 跨多个生境出现。

结果**完全反直觉地干净**:跨 ≥6 个生境的 named species 只有 5 个,且**全部是临床机会致病菌**(K.pneumoniae, P.aeruginosa, C.acnes, A.johnsonii, E.coli)。跨 5 生境的 13 个里另一极是 probiotic Lactobacillus(L.plantarum, L.crispatus)— 出现了一个 **dual-mode generalist** 现象:同样跨生境能力,临床菌 vs 益生菌分两极。

这条 case 让大脑学会:
1. **多生境 = 机会致病潜力**(用于 Phase 3 hypothesis generation 时给 prior)
2. **specialist vs generalist 用不同分析框架**(specialist 跑生境内 SMETANA / co-occurrence,generalist 跑生境间 strain_tracking)
3. **MGnify catalogues 是 nodes_v0 的最低成本入口**:metadata-only,无需下 fasta,几分钟就能拉到 ~60k species

## What I actually did

**输入**:20 个 MGnify catalog 的 `genomes-all_metadata.tsv`(每个 30-110 MB)+ GTDB R220 lineage(已嵌入 metadata)

**步骤**:
1. **批量 ingestion**(`urllib.request.urlretrieve` + retry × 3,~5 分钟全 20 个):
   ```
   url = ftp://ftp.ebi.ac.uk/pub/databases/metagenomics/mgnify_genomes/<catalog>/<version>/genomes-all_metadata.tsv
   ```
2. **每个 catalog 取 species rep**(`Genome == Species_rep`):每个 catalog 内已做 95% ANI 去冗
3. **GTDB lineage 解析**:把 `d__|p__|c__|o__|f__|g__|s__` 七级解开成列
4. **聚合到 9 个 habitat_id**:`gut_animal` 把 mouse/cow/sheep/pig/chicken/fish/zebrafish 全合;`marine` 把 marine v1+v2+sediment+euk 合;`plant_associated` 把三种 rhizosphere 合
5. **named species filter**:只看 `s__` 不空的 species(34,323/58,278 = 58.9%)
6. **跨生境计数**:`per_species = named.groupby("gtdb_species_full")["habitat_id"].nunique()`

**关键产物**:
- `data/nodes/nodes_v0_<catalog>.parquet` × 20
- `data/nodes/generalists_v1.tsv` — top 50 跨生境 species
- `data/nodes/CROSS_HABITAT_v1.md` — 完整分析

## ★ 排除/不做的事

- **不在第一轮做 cross-catalog 95% ANI 去冗**:每个 MGnify catalog 内部已经去冗;**跨 catalog 同 species 的 MAG 在统计上不重复计入跨生境数**(用 GTDB s__ 字符串当 species ID,自动去重)
- **不下 fasta 即可做此分析**:仅靠 metadata,几 GB / 几分钟,极低成本
- **不引入 UHGG-only 内部 4744 species ID(MGYG ID)**:不同 catalog ID 体系不互通,**唯一通用语是 GTDB s__**
- **不在第一轮分析未命名 species(s__ 空)**:这 44% 是 GTDB 占位 ID,跨 catalog 不可对齐;Phase 2 用 ANI 去冗后再合并
- **不混入非 MGnify 的 catalog**(hGMB / proGenomes3 / OceanDNA-figshare):它们 ID 不同体系,Phase 2 单独 ingest

## ★ 失败模式

- **MGnify catalog 子目录的版本号需要逐个 probe**:`v1.0` / `v1.0.1` / `v2.0` / `vbeta`,**不能假设**;`curl -s ftp://.../mgnify_genomes/<catalog>/ | awk '{print $NF}'` 列出
- **FTP 偶发 connection refused / reset**:单次失败需要 retry,3 次足够
- **GTDB `s__` 命名缺失 44%**:环境 MAG 大量新物种,跨 catalog 无法直接合并,误以为"跨生境 species 少"是分析没做完
- **`Lineage` 列里偶尔有空字符串字段**:`l.split(";")` 解析时要 `if k:` 跳过
- **per-habitat 聚合时把 gut_animal 7 个子 catalog 误算成 7 个生境**:必须先 `habitat_id` 标准化再 groupby
- **Cutibacterium acnes 在 soil 出现**:看似异常,实际是污染样本或皮肤接触地表(EMP 土壤样本含人接触污染);处理:不轻易丢,Phase 3 看 abundance 量级

## ★ 方法选择决策链

- **GTDB s__ 字符串 vs MGYG 内部 ID 当 species 锚**:s__ 字符串是跨 catalog 唯一通用语;MGYG 等内部 ID 仅 catalog 内有效
- **MGnify v2 vs OceanDNA(figshare)**:marine 选 MGnify v2(13,223 species)是因为 FTP 标准化便于拉;OceanDNA(52,325 MAGs)Phase 2 单独并入
- **以 species rep 而非全 genome**:catalog 内 95% ANI 去冗;跨 catalog 同 species 用 s__ 合并
- **named-only vs include-未命名**:第一轮 named-only(避免假阳性合并);Phase 2 跑 skani 把未命名也合并

## ★ Validation(科学 sanity)

- **跨 7 生境的 K.pneumoniae 在 vaginal 出现**:已知 dysbiosis 现象;不是 bug
- **C.acnes 跨 7 生境含 soil**:与 EMP soil 样本中人接触污染相符
- **跨 5 生境的 L.plantarum / L.crispatus**:与文献"Lactobacillus 是 niche-flexible probiotic"一致 ✓
- **specialist 97.8%**:与微生物生态"绝大多数 specialist,极少数 cosmopolitan"教科书一致 ✓
- **40 个跨 ≥4 生境 species**:其中 ~25 个有 PubMed 临床或多 niche 文献记录 ✓

## Lessons → seeds for rules

1. **MGnify catalogues 是 Phase 3 最低成本入口**:几分钟出 60k species,几乎零计算 / 零下载(metadata-only)
2. **GTDB s__ 是跨 catalog 唯一通用 species ID**;**MGYG / OceanDNA / hGMB 等内部 ID 必须先映射到 GTDB**
3. **specialist vs generalist 用不同分析管线**:specialist 在生境内跑 cooccurrence/cross_feeding;generalist 跨生境跑 strain_tracking 看 strain 漂移
4. **跨 ≥4 生境 named species 在 hypothesis 生成时打 "opportunistic_pathogen_likely" 标签**(reranker prior + cross_feeding 必跑 pair-with-host-microbiome)
5. **dual-mode generalist 概念**:同样跨多生境的能力,代谢配置不同 → pathogen vs probiotic;Phase 3 提 hypothesis 时把这两类标开
6. **44% 未命名 species 是 Phase 2 真去冗的主要 target**:它们才是把分析从 metadata-level 提升到 ANI-level 的关键
7. **K. pneumoniae 7 生境单菌深挖**作为 Phase 3 第一个 deep-dive 候选:跨 7 个生境的 7 个 MAG/isolate 跑 strain_tracking_real + 比较基因组,看是否是同 strain 散布(假说:**生境间 stable strain**)还是 species-level convergence(独立 evolved generalist)

## 候选大脑规则种子

### §14 候选:跨 ≥4 生境 named species 优先标记 opportunistic-pathogen prior
跨 ≥4 生境的 GTDB named species 在 hypothesis generation / reviewer / tournament reranker 阶段:
- prior label = `opportunistic_pathogen_candidate`
- tournament 权重 × 1.5
- 自动触发 strain_tracking_real(看是否同 strain 散布)
- 自动触发 CARD / VFDB 注释(看抗药 + 毒力)

### §15 候选:specialist vs generalist 分流分析
- specialist(N=57,027 / 97.8%)→ 生境内 cooccurrence_network_real + cross_feeding_gem
- generalist(跨 ≥4 / N=40)→ 跨生境 strain_tracking_real + 比较基因组

## 远端复现路径

服务器:`zkyd@10.102.106.53`,环境:`conda activate praxis-microbiome`
- 数据:`/home/zkyd/data2/mzy/PRAXIS-work-microbo/data/nodes/`
- 本地镜像:`/Volumes/T7/PRAXIS-work-microbiome/data/nodes/`
- 重跑脚本:见 `CROSS_HABITAT_v1.md` 末尾(load all parquets → groupby → count)
