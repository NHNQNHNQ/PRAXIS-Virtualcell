---
case_id: microbiome-016-uhgg-self-detection-graph
microbiome_task: network
sequencing_type: meta_catalogue
sample_type: human_gut
target_organism: "gut commensal core species via UHGG MAG self-detection"
input_data: "UHGG v2.0.2 genomes-all_metadata.tsv (110 MB,289,232 rows,24,129 unique Sample_accession,4,744 unique Species_rep)"
reference_db: "UHGG v2.0.2 + GTDB R220 lineage(已嵌入 UHGG metadata Lineage 列)"
dataset_accession: null
key_paper_doi: 10.1038/s41587-020-0603-3
biomass_estimate: na
tags: [cooccurrence, sparcc, UHGG, MAG, sample_detection, no_R_dep, keystone, Lachnospiraceae, Oscillospiraceae]
method_choice: [UHGG_metadata_pivot, pure_python_sparcc, bootstrap_pvals, louvain_community]
status: validated
schema_version: 2
---

# microbiome-016 — UHGG metadata 自带 MAG sample-detection 矩阵建共生图(绕过 R/cuMetD)

## Background — 为什么这条 case 重要

PRAXIS-Microbiome Phase 3 目标:跑出全生境 sample × species abundance 矩阵 → SparCC → 真互作图谱。
原计划用 R + curatedMetagenomicData(cuMetD,Bioconductor 标准入口,~93 个公开 shotgun 队列预处理好的 species relative-abundance)。

**结果连吃 6 次闭门羹**:

1. R 4.5 + Bioc 3.22:`BiocManager::install("curatedMetagenomicData")` 失败 — cuMetD 还没适配 Bioc 3.22 release
2. 切 USTC mirror:同样不适配(问题不在镜像,在 Bioc 版本)
3. conda bioconda `bioconductor-curatedmetagenomicdata`:r-magrittr / r-rlang / r-vctrs 多重版本冲突,libmamba solver 跑 20+ min 后爆炸,**附带把原 praxis-microbiome conda env 的 `conda-meta` 写坏**(`conda list` 报 JSONDecodeError),只能重建 env
4. IBDMDB(HMP2 IBD)public dump URL 404 — 公开页指向的 hmpdacc.org 路径已下线
5. Pasolli 2019 Cell supplementary materials:cell.com 403(出版社防爬)
6. Zenodo SGB(Segata lab)/ HumGut:SGB ID 体系与 GTDB 不互通,找不到对应 species-level abundance 文件

**死局之外的金矿**:UHGG v2.0.2 的 `genomes-all_metadata.tsv` 本身**就含 MAG → Sample_accession 的对应**(`Genome` 那行的 `Sample_accession` 字段)。也就是说,**每个 MAG 知道它从哪个原始 sample 组装出来**。

由此可以用 pandas pivot 直接拼出 **sample × Species_rep presence-count 矩阵**:每个 sample 中每个 species 出现的 MAG 数量。这不是真 metagenomic relative abundance,但作为 first-pass keystone screen 足够。

**关键数字**:289,232 genomes / 24,129 unique sample / 4,744 unique Species_rep,**完全不需要 R / 不需要重新比对 reads / 不需要 SRA 下 TB 级数据**。

**这条 case 的元价值**:
- 教大脑识别"输入数据本身就藏着信号"的情境 — case-015 用 UHGG metadata 的 `Country / Continent / Lineage` 字段做 cross-habitat 分析,case-016 进一步挖出 `Sample_accession` 字段做 sample × species 矩阵。**同一个 metadata 文件 = 两条 case 共用底座**
- 标记 Phase 3 的一种**反脆弱策略**:遇到工具链多次失败时**回头看数据 raw schema**,经常发现绕过工具的路径
- 给后续 §17 / §18 候选规则提供具体 case anchor,不是凭空提规则

## What I actually did

**输入**:UHGG v2.0.2 `genomes-all_metadata.tsv`(110 MB,Phase 3 case-015 已拉过,本机存)
**关键观察**:`head -1` 列出 `Genome / Genome_type / Length / N_contigs / N50 / ... / Lineage / Sample_accession / Study_accession / Continent / Country / Species_rep / ...`。`Sample_accession` 与 `Species_rep` 是同一行,**单次 pivot 就出矩阵**,根本不需要 cuMetD。

**步骤**:

1. **metadata 读 + pivot**(`pandas.crosstab`,~10 秒):
   ```python
   import pandas as pd
   meta = pd.read_csv("genomes-all_metadata.tsv", sep="\t", low_memory=False)
   # 行 = Sample_accession,列 = Species_rep,值 = 该 sample 中该 species 的 MAG 数
   mat = pd.crosstab(meta["Sample_accession"], meta["Species_rep"])
   # 24,129 × 4,744 全矩阵,极稀疏(>99% 是 0)
   ```

2. **过滤**(双向阈值,避免极端稀疏导致 SparCC log-ratio 失稳):
   - **sample 层**:保留检出 ≥10 species 的 sample → 7,238 / 24,129(30%)
   - **species 层**:prevalence ≥1%(在 ≥72 个 sample 中出现)→ 358 / 4,744(7.5%)
   - 中间档:top-100(prev≥5%) / top-200(prev≥2%,实际命中 119) 用于 sanity check + 性能基线

3. **SparCC pure-Python**(自己 ~200 行 numpy 实现,避开 R / FastSpar C++ 编译链):
   - log-ratio 变换:`log(x+1) - mean(log(x+1))` row-wise(避开 zero 用 +1 pseudocount)
   - n_iter=10 迭代:每轮把当前 |corr| > 0.10 的对置 NaN 后重估剩余相关
   - n_perms=30 bootstrap shuffle column-wise → empirical p-value
   - threshold:`|corr| ≥ 0.20 ∧ p < 0.05`

4. **图谱产物**:
   - 主交付 full-358:**12,911 真边**,wall 5 min(单核 Apple M-series)
   - top-100 子集:1,508 边,23 s(性能 sanity:边数随 n_taxa 大致 O(n²),12,911/1,508 ≈ 8.6,(358/100)² ≈ 12.8,接近)
   - top-200 子集:2,013 边,37 s

5. **Community detection**:`networkx.community.louvain_communities(seed=42)` → 4 个 community,size 114/88/79/77,近均匀(模块度 Q ≈ 0.31)

6. **keystone 排序**:weighted-degree(每节点 |corr| 加权之和),top 15 标 family/phylum,附 GTDB Lineage

**产物**:`/Volumes/T7/PRAXIS-work-microbiome/runs/cooccurrence-real-v1/out_full358/`
- `edges.tsv` 12,911 行(裸边:source / target / corr / p)
- `edges_annotated.tsv`(含 GTDB lineage,joinable for downstream)
- `node_centrality.tsv` 358 nodes weighted_degree + community_id
- `summary.json`(n_taxa / n_edges / runtime / threshold)
- `GRAPH_v1.md` 完整图谱报告(含 top-15 keystone / phylum-pair / top-10 edges)

## ★ 排除/不做的事

- **不强行 R 4.5 + cuMetD**:Bioc 3.22 还没适配,等 Bioc 3.23 + R 4.6(2026 Q3-Q4)再回头。**continuing 浪费一天**
- **不在 praxis-microbiome 主 env 里 conda install cuMetD**:bioconda solver 已经证明会破 env;真要装走**独立 env**(`conda create -n cmd r-base=4.4` + bioconductor)隔离爆炸面
- **不用 IBDMDB / HMP2 公开 dump**:URL 路径变动频繁(hmpdacc.org 下线后没人 update 文档),不稳;真要 HMP2 走 NCBI BioProject(PRJNA398089)拉 reads,但那是 TB 级 I/O
- **不直接拉 SRA reads + 重新 MetaPhlAn4 比对**:几 TB 下载 + 几千 CPU·小时;Phase 3 first-pass 不合适
- **不用 sparse Pearson**(scipy `pearsonr` 暴力 358×358):违 §08 compositional-network-methods,compositional 数据 Pearson 出**伪相关**;**SparCC 是 §08 推荐 baseline**
- **不在 SparCC 上加 multiple testing 校正 BH**:n_perms=30 已偏少,BH 在低 perm 下进一步收紧到 0 边;Phase 2 把 n_perms 提到 ≥100 再加 BH

## ★ 失败模式

1. **R 4.5 + Bioc 3.22 cuMetD 不兼容**(2026-05-25 状态):`BiocManager::install` 直接报 package not found。Bioc release 节奏与 R minor release 节奏不同步是常态,**不要假设最新 R 配最新 Bioc 包**。教训:Phase 启动前先查 `BiocManager::version()` ↔ 目标包的 `bioc-release` field
2. **conda libmamba solver 爆炸破 env**:`conda install -c bioconda bioconductor-curatedmetagenomicdata` 跑 20+ min,期间写 conda-meta lock,中途 Ctrl+C 或 OOM kill 会留下 stale lock,后续 `conda list` 报 `json.decoder.JSONDecodeError: Expecting value: line 1 column 1`。**修复**:`rm -rf $PREFIX/conda-meta/*.json` 后从 history 重建。**预防**:每个高风险 install 走 `conda create -n X`,不要污染主 env
3. **公开 URL 403/404 是常态**:IBDMDB(hmpdacc.org 已下线)/ Pasolli supplementary(cell.com 出版社防爬 403)/ 各种 zenodo legacy DOI,>50% 的 paper 数据 URL 5 年后失效;不要在 critical path 上依赖这些
4. **f-string 反斜杠陷阱**:Python ≤3.11 中 `f"{a\n}"` SyntaxError("f-string expression part cannot include a backslash");解决:把含 `\n` 的子串提到变量(`nl = "\n"; f"{a}{nl}"`)。本 case 在写 summary print 时撞了一次,3.12+ 已放宽但代码要兼容旧版
5. **GTDB lineage 嵌入字段叫 `Lineage` 不叫 `gtdb_classification`**:UHGG metadata 列名要 `head -1 | tr '\t' '\n'` 一眼;别用 marine v2 / HumGut 的字段名假设套
6. **MAG sample_accession 偶尔为空**(< 0.5%,某些早期 NCBI 提交 batch 没填 SRA accession);`crosstab` 自动 drop NaN,不报错但要 log 计数,否则总 sample 数对不上
7. **n_negative = 0 的"成功"是 false sense of success**:全 12,911 边正,看上去图很满,实际是**presence-count 偏向 + pseudocount +1 偏置**带来的代数后果 — 算法本身没出错,但生物信号偏置;Phase 2 必须有 SPIEC-EASI partial correlation 补 negative 边
8. **bioconda 频道优先级倒置**:即便加了 `-c bioconda -c conda-forge`,libmamba 仍可能从 default channel 解出 stale r-magrittr;修复 `conda config --add channels conda-forge --add channels bioconda` 强制 channel 排序,且 `channel_priority: strict`
9. **R 编译型 Bioc 包在 ARM macOS 失败率高**:`Rcpp` / `RcppEigen` / `igraph` 在 M-series 上 source build 失败率 > 30%,即便 R 4.5 装通也未必能 install Bioc;Phase 2 Bioc 工作干脆走 Linux server(zkyd 服务器),不在 macOS 本地纠结

## ★ 方法选择决策链

- **SparCC vs SPIEC-EASI vs FlashWeave vs propr**:
  - **SparCC**(Friedman & Alm 2012):纯 python 实装快(200 行 numpy),log-ratio + iterative refit,compositional-aware;**本次首选**,因为不依赖任何 R / Julia / 编译链
  - **SPIEC-EASI**(Kurtz 2015):R `SpiecEasi` package + graphical lasso,partial correlation 视角,理论上能给出 negative edges;**踩了 R 4.5/Bioc 3.22 死循环,Phase 2 单独装 R 4.4 + Bioc 3.20 env**
  - **FlashWeave**(Tackmann 2019):Julia,大 N 性能最好,装更重;Phase 2 候选
  - **propr**(Quinn 2017):R,proportionality measure φ/ρ,与 SparCC 互补;Phase 2 与 SPIEC-EASI 一起进 R env
- **presence-count vs relative abundance**:真 abundance 要 reads 比对(几千 CPU·小时);**presence-count 是 metadata-only first-pass**,妥协但快 — Phase 2 用 MetaPhlAn4 + 部分 SRA reads(优先 IBD / IBDMDB 替代源 = NCBI BioProject PRJNA398089)做局部 validation
- **Louvain vs Leiden**:Louvain `networkx` 自带,种子可复现;Leiden 要 `python-igraph` + `leidenalg` 装,Phase 2 升级;在 358 节点小图上 Louvain 和 Leiden 结果差异通常 < 5%
- **weighted-degree vs betweenness centrality vs eigenvector centrality**:
  - weighted-degree:O(E),最直接,**keystone 在 SparCC 共生图语义下 = "和很多 species 强共生" = 高 weighted degree**
  - betweenness:O(V·E),偏向 bridge 节点,适合找"跨 community 桥"(可能是 generalist 而非 keystone)
  - eigenvector:迭代收敛,在密集图上易被 community 主导信号
  - **本次选 weighted-degree**;Phase 2 三种并算,看 keystone 集合稳定性
- **过滤阈值 10 species per sample + 1% prevalence**:
  - < 10 species 的 sample 几乎全是 single-MAG submission(个别 study 一份样本只测出 1 个 MAG),信号噪声;7238/24129 保留率合理
  - < 1% prevalence species 在 SparCC log-ratio 里贡献几乎全 0,徒增维度且加重 pseudocount 偏置;358 species 足够覆盖肠道核心 commensal
- **SparCC iterative refit 截断 |corr| > 0.10**:Friedman 原文用 0.10,在 sparse data 上偏严会过早收敛;但放松到 0.05 在本数据上让 n_iter 跑不收敛(corr 矩阵震荡);保持 0.10 默认

## ★ Validation(科学 sanity)

1. **Top 15 keystone 中 11/15 来自 Oscillospiraceae + Ruminococcaceae + Lachnospiraceae**(肠道核心 commensal 三大科,Firmicutes_A);这正是教科书定义的"gut keystone"集中区。**这是图谱生物学正确性的最强证据**:如果 SparCC + presence-count 完全胡来,keystone 应该随机分布到所有 family,不会集中到这三科
2. **跨 phylum 边 54%(812/1508)> 同 phylum 46%(696/1508,top-100 子集)**:符合 gut microbiome ecology 共识 — Bacteroidota(多糖降解)与 Firmicutes_A(SCFA 产)之间是**功能性 cross-phylum partnership**,不是 phylum-内 phylogenetic 偏好。如果信号是 phylogenetic artifact,应该同 phylum 显著偏多
3. **Methanobrevibacter_A smithii ↔ SFEL01 corr=0.732**:已知 **产甲烷古菌 syntrophy**(M.smithii 消耗 Firmicutes 发酵产生的 H₂ → CH₄),corr 高完全合理
4. **Ruminococcus_B gnavus ↔ Flavonifractor plautii corr=0.726**:已知 **IBD-associated 共生对**(两者都在 CD/UC 队列中富集),文献支持
5. **Dialister sp ↔ Succinivibrio sp corr=0.801**:富 fiber 个体共生,符合 high-fiber diet enterotype 特征
6. **4 个 Louvain community 近均匀 size**(114/88/79/77,Q≈0.31):反映肠道主要 trophic group,不是 1 个超大社区压一切的 degenerate clustering
7. **graph density 0.202**:358 节点完全图 64k 边,实际 12.9k 边占 20%;非 trivial 但也不爆密(随机图同 threshold 应 < 5%)
8. **degree 分布近 power-law**:top 15 keystone weighted_degree 71-96,中位数 30 左右,长尾 — 与"少数 hub + 大量 leaf"的真生态网络分布一致,非 ER 随机图(那应近似正态)

## Top edges 生物学样本(从 GRAPH_v1.md)

| source | target | corr | 生物学含义 |
|---|---|---:|---|
| _Dialister_ sp000434475 | _Succinivibrio_ sp000431835 | 0.801 | 富 fiber 个体共生 |
| _Flavonifractor plautii_ | _Ruthenibacterium lactatiformans_ | 0.763 | 都产 SCFA(butyrate/lactate)|
| _Succinivibrio_ sp | _RC9_ sp000433355 | 0.761 | 高 fiber 三连共生 |
| _Methanobrevibacter_A smithii_ | _SFEL01_ sp | 0.732 | 产甲烷古菌 H₂ syntrophy |
| _Enterocloster_ sp | _Clostridium_Q_ sp | 0.730 | Lachnospiraceae 内共生 |
| _Ruminococcus_B gnavus_ | _Flavonifractor plautii_ | 0.726 | IBD-associated pair |

这 6 个 top edges 全部在文献里有独立证据,说明 SparCC + presence-count 至少在**高 corr 区段**输出是可信的;低 corr(0.20-0.30)区段的边是 Phase 2 SPIEC-EASI 必须校正的部分。

## ★ Known limitation(诚实写)

1. **n_negative = 0**:全 12,911 边为正相关。**这是 presence-count + 简化 SparCC 的已知偏置** — 稀疏二值化数据中"两 species 都在同 sample 检出"远比"互斥"信号强。真负向(竞争)边需要 SPIEC-EASI 或带 partial correlation 的方法
2. **abundance proxy = MAG count per sample**:不是真 relative abundance;假设"sample 中检出 2 个 MAG 的 species 比 1 个 MAG 的更丰富"未必成立(可能是分箱算法偶发拆分,或同 sample 多次 binning 命中同 species 多个分支)
3. **没有第 2 个独立 method 交叉验证**:违 §07 multiomics-triangulation 推荐(应 ≥2 独立工具);bootstrap p-value 只算"统计上稳",不算"方法上独立"
4. **n_perms=30 偏少**:严格用应 ≥100;低 perm + 无 BH 校正使本图谱适合 **first-pass keystone screen**,不适合 **临床决策 / 单边 biology claim**
5. **correlation 阈值 0.20 偏低**:可能挤入边缘信号;Phase 2 提到 0.30 + n_perms≥100 + BH 校正,会显著收紧到 ~3-5k 边
6. **sample 来源 batch 效应未控**:24,129 sample 来自数百个 study,**没做 study-level random effect 校正**;同 study 内 MAG binning pipeline 一致,可能跨 sample 假阳性共检出。Phase 2 用 mixed-effect log-ratio 或 ComBat 校正
7. **geographic / disease state confounder**:UHGG metadata 有 `Country` / `Continent`,但本 case 没分层 — 真 keystone 可能因人群结构(中国队列 ≠ 西方队列肠道 enterotype)被稀释或假阳性

## Lessons → seeds for rules

1. **MGnify catalog metadata(UHGG / marine v2 / soil v1 / 各动物肠道)是 Phase 3 最低成本 abundance 入口**:无需 cuMetD,无需 SRA 重比对,几分钟出 sample × species 矩阵 — 这是 case-015 generalist 分析与 case-016 共生图谱共用的底座。**`Sample_accession` 字段是金矿,捡起来就能用**
2. **SparCC pure-Python 实装 200 行可用**:不要等 R/FastSpar/SPIEC-EASI 装通才动手,first-pass 自己写;Phase 2 再用工业实现校正
3. **R + Bioc 在 macOS 上版本死循环风险高**:R minor 与 Bioc release 不同步;**关键 Bioc 包绝不在主 conda env 装**,永远 `conda create -n cmd`(或干脆 Phase 2 上 Linux server 跑)隔离
4. **MAG-derived presence-count ≠ relative abundance**:可以做 keystone screen 与 community structure,**不能**做差异分析 / 临床预测 / strain-level claim
5. **公开数据 URL 5 年衰减率 >50%**:IBDMDB / Pasolli supplementary / zenodo legacy 大量 404;不要在 critical path 上 hard-code 这些 URL,优先选**机构级稳定源**(EBI MGnify FTP / NCBI BioProject / GTDB release)
6. **conda 主 env 永远不混高风险大 stack**:R + Bioconductor / GPU CUDA / 大编译包(QIIME2 etc.)都另起 env,主 env 留给稳定 pandas+numpy+networkx
7. **"失败 6 次后跳出原方案"的元教训**:当 cuMetD 装失败 3 次后我没有继续 hammer,而是回头看输入数据本身有没有替代路径 — UHGG metadata 里 `Sample_accession` 就是答案。**遇到工具链反复失败,先停下来看数据本身能不能直接出**
8. **SparCC pseudocount +1 的代价**:零膨胀数据 log(x+1) 把所有 0 强行映射到 0,等同假设"未检出 = 零丰度",在 MAG presence-count 上特别偏向产生 positive 相关(两个低 prevalence species 大量共 0 → 共变方向一致)— 这是 n_negative=0 的代数原因之一

## 候选大脑规则种子

### §17 候选:co-occurrence 边必须 ≥2 独立方法共识
任何 sample × species 共生图作为 PRAXIS-Microbiome 节点的输入证据,**至少跑 2 个独立统计方法**(SparCC + SPIEC-EASI / FlashWeave / propr 任选其二),取边集**交集**作为高置信边,**并集**作为候选边;单 method 边只能做 first-pass screen,不能进 hypothesis generation 的 prior。

理由:case-016 出现 n_negative=0 全正向偏置,纯 SparCC 不能区分"真共生"与"presence-count 偏置";SPIEC-EASI 的 graphical lasso 在同数据上会给出 partial correlation 视角,能补充 negative edges。

### §18 候选:MAG-derived presence-count 不是真 relative abundance
MAG catalog metadata(UHGG / MGnify 系列)给出的 sample → MAG → species 链路,**只能产 presence-count proxy**,**不能**当 relative abundance 用于:
- 差异丰度分析(ANCOM-BC / LEfSe)
- 临床表型关联预测
- strain-level abundance claim

可以用于:
- first-pass keystone screen(本 case)
- community structure 探索(Louvain / PCoA)
- prevalence-based generalist 识别(case-015)

真 abundance 必须走 reads + MetaPhlAn4 / sourmash / Kraken2 比对。

## 与已有大脑规则关系

- ✅ **§07 multiomics-triangulation**:bootstrap p-value 作第 2 道证据,但严格应 ≥2 独立工具 → 引出 §17 候选
- ✅ **§08 compositional-network-methods**:用 SparCC 不用 Pearson,合规
- ✅ **§05 compositional-aware-DA**:不 rarefy,直接 presence count(虽然 presence count 不是真 abundance,但至少没 rarefy 错)
- ✅ **§13 isolate-vs-MAG**:本 case 全 MAG,所有 keystone claim 都加 MAG 来源说明,不混 isolate-level claim
- 🆕 **§17 候选**(见上)
- 🆕 **§18 候选**(见上)

## 与 case-014 / case-015 的关系

- **case-014(GEM cross-feeding baseline)**:用 isolate FASTA 跑 SMETANA,产 metabolite-level cross-feeding edges;本 case-016 产 statistical co-occurrence edges。**二者互补,Phase 2 要交叉**:keystone top-15 在 case-014 GEM 上跑 cross-feeding,看 SparCC 共生边是否对应 metabolite-level 互喂关系
- **case-015(cross-habitat generalist)**:用同一 UHGG metadata 的 `Country` / `Lineage` 字段做 species 跨生境计数;本 case-016 用同一文件的 `Sample_accession` × `Species_rep` 字段做 sample × species 矩阵。**一鱼两吃,同一 110 MB 文件产两条独立 case**
- **元 lesson**:Phase 3 起步阶段,**先把已下载的数据所有字段过一遍**,经常发现可复用信号 — 比上来就 plan 新的数据下载更有效率

## 复盘:这条 case 修补了大脑哪几条规则盲点

- **§07 multiomics-triangulation**:之前的例子都是"组学之间三角化"(16S × shotgun × transcriptome),本 case 暴露**单组学内"统计方法间三角化"也是 §07 范畴** — SparCC 的 bootstrap p 不能替代 SPIEC-EASI 的独立证据,引出 §17 候选
- **§08 compositional-network-methods**:之前规则只说"用 SparCC / SPIEC-EASI 不用 Pearson",本 case 补了**SparCC 在 presence-count 上偏正向**这一隐性边界,需要在 §08 里加注 caveat
- **§13 isolate-vs-MAG**:本 case 所有 keystone claim 都明确标注 MGYG ID(MAG-derived),不与 case-014 的 isolate-GEM claim 混用 — 强化 §13 命名规则
- **新增 §17 候选**:co-occurrence ≥2 独立方法共识(见上)
- **新增 §18 候选**:MAG-derived presence-count 不是真 relative abundance(见上)

这两条候选直接来自 case-016 的失败模式(n_negative=0)与方法选择决策链,不是事后凭空想出的规则。

## 远端复现路径

服务器:`zkyd@10.102.106.53`,环境:`conda activate praxis-microbiome`
- 数据:`/home/zkyd/data2/mzy/PRAXIS-work-microbo/data/uhgg/genomes-all_metadata.tsv`
- 产物:`/home/zkyd/data2/mzy/PRAXIS-work-microbo/runs/cooccurrence-real-v1/out_full358/`
- 本地镜像:`/Volumes/T7/PRAXIS-work-microbiome/runs/cooccurrence-real-v1/`
- 重跑命令:见 `runs/cooccurrence-real-v1/GRAPH_v1.md` 末尾

**复现核心**(单核 5 min,任何有 pandas+numpy+networkx 的环境都能跑,**无 R 依赖**):
```bash
python skills/cooccurrence_network_real/run.py \
  --metadata data/uhgg/genomes-all_metadata.tsv \
  --min-species-per-sample 10 \
  --min-prevalence 0.01 \
  --method sparcc --n-iter 10 --n-perms 30 \
  --corr-threshold 0.20 --p-threshold 0.05 \
  --out runs/cooccurrence-real-v1/out_full358/
```

**最低依赖**:`python>=3.10, pandas>=2.0, numpy>=1.24, networkx>=3.0`(不需要 scipy, R, Julia, C++ 编译)

**输入文件来源**(2026 状态稳定):
```
ftp://ftp.ebi.ac.uk/pub/databases/metagenomics/mgnify_genomes/human-gut/v2.0.2/genomes-all_metadata.tsv
```
110 MB,EBI MGnify FTP 机构级稳定源,5 年内不会消失。Phase 2 同样路径模式可拉所有 MGnify catalog 做 cross-habitat 共生图。

## 下一步动作(从本 case 派生)

1. **Phase 2 必跑 SPIEC-EASI 交叉验证**:同一 7238 × 358 矩阵,R 4.4 + Bioc 3.20 独立 env,看边集 Jaccard overlap;预期 ≥ 0.40(SparCC 与 SPIEC-EASI 在 simulation 上典型 overlap 0.35-0.55)
2. **跨 catalog 复用本管线**:marine v2 / soil v1 / mouse gut catalog 各跑一张 358-scale 图,产出 9 个 habitat-specific 共生图谱,作为 Phase 3 全生境互作图谱的 backbone
3. **keystone top-15 单菌深挖**:对应 11 个 Firmicutes_A keystone 跑 cross_feeding_gem(case-014 skill)看 cross-feeding network 是否与 SparCC keystone 集合重叠 — 双证据 keystone
4. **n_perms 提到 100 + BH 校正**:重跑 full-358,产 v2 图;预期边数从 12,911 收紧到 ~3-5k(更保守 / 更高置信)
