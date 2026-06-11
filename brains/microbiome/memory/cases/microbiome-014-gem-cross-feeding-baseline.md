---
case_id: microbiome-014-gem-cross-feeding-baseline
microbiome_task: network
sequencing_type: WGS_isolate
sample_type: human_gut_isolate
target_organism: "Bacteroides thetaiotaomicron + Eubacterium rectale + Faecalibacterium prausnitzii"
input_data: "3 个 RefSeq isolate protein FASTA(GCF_000011065.1 + GCF_000020605.1 + GCF_003312465.1)"
reference_db: "GTDB R220 + KEGG MODULE + BiGG universe_bacteria(via CarveMe)"
dataset_accession: null
key_paper_doi: 10.1093/nar/gky852
biomass_estimate: high
tools: [carveme 1.6.6, smetana 1.2.1, cobra 0.31.1, diamond 2.2.0, GLPK]
tags: [GEM, CarveMe, SMETANA, cross_feeding, MIP, MRO, gut, butyrate, baseline, phase0]
method_choice: [CarveMe_protein_input, universe_bacteria, gap_fill_LB_anaerobic, SMETANA_global_and_detailed, KEGG_MODULE_complementarity_prefilter]
status: validated
schema_version: 2
---

# microbiome-014 — GEM-driven cross-feeding 边推断 baseline(肠道三菌)

## Background — 为什么这条 case 重要

PRAXIS-Microbiome 的 **cross_feeding_gem** skill 在 Phase 0 闭环里第一次跑通真数据。结果暴露出几个**反直觉的方法学陷阱**,不固化为 case 下次会重蹈覆辙:

1. CarveMe **必须用 protein 输入**(prodigal/RefSeq `_protein.faa`),`--dna` 模式 diamond blastx 把整条 chromosome 当 1 个 query + `--top 10` 过滤,**只留 13-25 hits**,导致 universe 几乎不被命中,GEM 反应数 < 300,biomass = 0
2. CarveMe **不要用 `-u grampos` / `-u gramneg` 错配**:B.theta(Bacteroidetes)是革兰阴性,E.rectale/F.prausnitzii 是革兰阳性;**`-u bacteria` 通用 universe 最稳**(避免 gram-typing 错误)
3. **Gap-fill media 必须显式指定**:`carve -g "LB[-O2]" -i "LB[-O2]"`,否则模型在任何 media 下都 biomass = 0
4. **SMETANA `-m` 必须配 `--mediadb`**(carveme 自带 `media_db.tsv`),否则报 "Please provide media library"
5. **LB[-O2] detailed = 0 行 不等于 没有 cross-feeding**:富营养下两菌都自给自足,SMETANA detailed 这是算法正确的"no necessary cross-feed"。**必须同时跑 global mode 看 MIP/MRO**

## What I actually did

**输入**:3 个 NCBI RefSeq isolate(每个含 `_protein.faa`)
- _B. thetaiotaomicron_ VPI-5482(GCF_000011065.1)— 革兰阴性 Bacteroidetes,fiber generalist
- _E. rectale_ (Agathobacter rectalis) ATCC 33656(GCF_000020605.1)— 革兰阳性 Firmicutes,acetate→lactate
- _F. prausnitzii_ APC918/95b(GCF_003312465.1)— 革兰阳性 Firmicutes,butyrate producer

**步骤**:
1. **下 protein FASTA**(不是 DNA),3 个文件 ~5MB 总和
2. **CarveMe**(每个基因组 ~10 分钟 wall,GLPK LP gap-fill 单线程):
   ```
   carve --fbc2 -u bacteria \
         --mediadb $CARVEME/data/input/media_db.tsv \
         -g "LB[-O2]" -i "LB[-O2]" \
         -o gems2/<id>.xml <id>.faa
   ```
   产出:b_theta 2329 rx / 96.1 biomass,e_rectale 1862 rx / 90.6,f_prausnitzii 1921 rx / 81.6
3. **KEGG MODULE 互补预筛**(donor 完整 ≥0.8 ∧ receiver <0.6):6 candidate directed pairs
4. **SMETANA global**(每对 ~30 秒):
   ```
   smetana --global --flavor fbc2 --molweight -m "LB[-O2]" --mediadb $CARVEME/data/input/media_db.tsv -o <prefix> <sbml_a> <sbml_b>
   ```
5. **SMETANA detailed**(每对 ~10 分钟):
   ```
   smetana --detailed --flavor fbc2 --molweight -m "LB[-O2]" --mediadb $CARVEME/data/input/media_db.tsv -o <prefix> <sbml_a> <sbml_b>
   ```

## ★ 排除/不做的事

- **不用 `--dna` + DNA FASTA 输入 CarveMe**:diamond blastx 单 chromosome → 13-25 hits → 反应数不够 → biomass = 0
- **不用 `-u grampos` / `-u gramneg`**:除非你 100% 确定 gram type 且菌的代谢和 universe 高度匹配。**默认 `-u bacteria`**
- **不在 SMETANA 调用里写裸 `-m M9` / `-m LB`**:没有 `--mediadb` 会硬错
- **不只跑 detailed 模式**:富营养 media 下 detailed 经常 0 行,只跑 detailed 会误以为"无互作";**global 必须并跑**
- **不用 LB 富营养 media 评估 cross-feeding**:LB 全 amino acid + 维生素,菌自给自足,MIP=n/a 几乎一定。真要看 detailed metabolite-level edges 必须用 **minimal media + 单一碳源**(starch / cellobiose / mucin glycan / fiber)
- **不下 NCBI 的 `_genomic.fna.gz`**:除非真要做 prodigal/gene prediction;直接 `_protein.faa.gz`

## ★ 失败模式

- **GEM biomass = 0(沉默失败)**:CarveMe 不报错,但模型空转。**FBA sanity check 必跑**(`model.optimize().objective_value > 0`)
- **diamond `--top 10` 过滤**:对长 sequence 致命,正确做法用 protein query
- **gram-typing 错误**:B.theta 表面像革兰阴性但有些教科书归为 Bacteroidetes 特殊外膜;混淆会让 universe 完全错。**用 `-u bacteria` 兜底**
- **SMETANA `LB[-O2]` 检测不到 detailed edges**:这是 algorithm 正确的"高营养下自给自足",不是 bug
- **MIP=n/a vs MIP=0**:n/a 意思"两菌一起反而需要更多营养",不是"无互作";`-z` flag 让 zeros 也输出便于诊断
- **GLPK LP solve 慢**:carve 默认 GLPK,单线程,144 核 server 大部分时间 idle;装 cplex/gurobi 可大幅加速

## ★ 方法选择决策链

- **CarveMe vs gapseq vs ModelSEED**:CarveMe 最快(BiGG-based,~10min/genome),适合大量 isolate;gapseq 准但 50+ min/genome;ModelSEED 需 web API
- **SMETANA vs MICOM vs cobra co-culture**:SMETANA 标准 + 输出 MIP/MRO 直接可用;MICOM 适合多 community 模拟但需要 abundance;cobra co-culture 需手动 implement
- **detailed mode 与 global mode 并跑**:detailed 给 metabolite-level 但贵且对 media 敏感;global 便宜且鲁棒,community-level
- **KEGG MODULE 互补预筛**:对 N 个 genome 把 O(N²) 候选对 → O(k·N) 显著候选(k=互补 module 数);3 菌 → 6 pair 无意义,N≥20 时必带
- **protein 输入 vs prodigal-on-the-fly**:RefSeq 直接有 protein,何必再 prodigal

## ★ Validation(scientific sanity)

- **GEM FBA biomass > 0**:b_theta 96.1 / e_rectale 90.6 / f_prausnitzii 81.6 on LB[-O2] ✓
- **GEM reaction count 合理**:1800-2400(BiGG-based bacteria GEM 标准范围)✓
- **MRO 与 ecology 一致**:三菌都是 gut anaerobe,营养重叠 0.71-0.86 高度重叠,符合"共栖竞争"实情 ✓
- **MIP 与已知 biology 一致**:**E. rectale ↔ F. prausnitzii MIP=3.0**(lactate→butyrate 链的下游两菌确有显著 cross-feeding 潜力);B.theta ↔ others MIP=n/a(B.theta 在 LB 是 generalist 不耦合)✓
- **方向性正确**:KEGG MODULE 预筛挑出的 6 directed pair 全部 SMETANA 成功跑完,无 false positive

## Lessons → seeds for rules

1. **CarveMe 必须 protein 输入 + `-u bacteria` + 显式 `-g/-i` gap-fill media**(三条同时,缺一 GEM 不可用)
2. **每个 GEM 出来必跑 FBA sanity**:biomass > 0 才算 valid;biomass = 0 直接丢
3. **SMETANA 评估永远同跑 global + detailed**,二者互补;只 detailed 会误以为"无互作"
4. **media 选择决定 cross-feeding 信号**:LB 看 community-level(MIP/MRO),minimal+单碳源看 metabolite-level
5. **KEGG MODULE 互补预筛**:N≥20 个 genome 必上;N<10 全 pair 也可接受
6. **MIP=n/a ≠ 无互作**:意思"一起反而需要更多 substrate"。要区分 n/a / 0 / ≥1
7. **CarveMe LP solver 瓶颈**:大规模 (n>100 genome) 必装 cplex/gurobi 替换 GLPK,否则单线程跑死

## 复盘:这条 case 修补了大脑哪几条规则盲点

- **§07 multiomics-triangulation** 之前只举 16S+shotgun 或 microbe+transcriptome 例子,**本 case 补了"GEM SMETANA + KEGG MODULE"两源三角化**,是 cross_feeding_gem skill 的核心
- **§13 isolate-vs-MAG**:本 case 用 RefSeq isolate 验证了 GEM build 质量(2300 rx)与 MAG-derived GEM(常 1200-1700 rx 缺反应)的显著差距 — 强化 §13
- **新建议规则 §14 candidate**:_GEM 跨喂养评估永远同跑 global + detailed,LB 上 detailed=0 不否定互作;真要 detailed metabolite edges 用 minimal media + 单一碳源_

## 远端复现路径

服务器:`zkyd@10.102.106.53`,环境:`conda activate praxis-microbiome`
产物路径:`/home/zkyd/data2/mzy/PRAXIS-work-microbo/runs/cross-feed-real-003/`
本地镜像:`/Volumes/T7/PRAXIS-work-microbiome/runs/cross-feed-real-003/`(已 rsync 回拉)
重跑命令:见 `runs/cross-feed-real-003/RESULTS.md`
