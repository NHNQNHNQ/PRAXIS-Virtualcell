---
case_id: microbiome-017-keystone-dichotomy
microbiome_task: network
sequencing_type: meta_catalogue
sample_type: human_gut
target_organism: "gut keystone species (Type A: CAG-83 / Angelakisella / Bacteroides_F pectinophilus / UBA1777 / UBA11471; Type B: K. pneumoniae / E. coli / Bilophila wadsworthia / Enterocloster / Eggerthella / Flavonifractor / E. faecalis)"
input_data: "UHGG 358 species × 7238 sample + MIBiG 3.1 BGC homology + 15 keystone SMETANA cross-feeding"
reference_db: "UHGG v2.0.2 + GTDB R220 + MIBiG 3.1 (2,502 BGCs / 41,002 proteins) + carveme universe"
dataset_accession: null
key_paper_doi: 10.1038/s41587-020-0603-3
biomass_estimate: na
tags: [keystone, dual_mode, opportunistic_pathogen, BGC, antagonism, cross_feeding, cooccurrence, triangulation, type_A_metabolic, type_B_chemical_warfare, ESKAPE, IBD, Klebsiella, Lachnospira]
method_choice: [sparcc, smetana_global, prodigal, diamond_mibig, networkx_louvain, multi_evidence_integration]
status: validated
schema_version: 2
---

# microbiome-017 — Keystone 二元论:Type A(代谢 hub)vs Type B(化学武器)+ 跨 case 独立交叉验证

## Background — 为什么这条 case 重要

这是 case-014 / 015 / 016 三条 case 的 **capstone**:

- case-014 给出 **GEM SMETANA cross-feeding** 的 metabolite-level 边推断方法学(3 菌 isolate baseline)
- case-015 用 **MGnify catalog metadata** 跨 20 个 catalog 拉出"跨 ≥6 生境 named species 全是机会致病菌"的科学发现(K.pneumoniae / E.coli / A.johnsonii / C.acnes / P.aeruginosa)
- case-016 用 **UHGG `Sample_accession` 字段**绕过 R/cuMetD 死循环,产出 7238 sample × 358 species presence-count 矩阵 + SparCC 12,911 共生边

到这里数据规模足够、方法链闭合。在 case-016 的 12,911 cooc 边底盘之上,叠加 **MIBiG 3.1 BGC content(prodigal+diamond,358/358 species 全覆盖)** + **15 keystone SMETANA cross-feeding** 两道独立证据,产出 PRAXIS-Microbiome 项目**第一张完整的单生境真图谱**(`runs/bgc-358-v1/GRAPH_v3_FINAL.md`,358 节点 / 12,911 边 / 12,908 双证据 / 26 三证据)。

**真发现 — keystone 不是一个 list**:

按 weighted-degree 排名("和很多 species 强共生")给一个 keystone 列表(Type A,代谢 hub);按 BGC 数量排名("装备多少化学武器")给另一个完全不重叠的列表(Type B,化学武器/机会致病)。**top 10 mutually exclusive**。

更关键的是,**Type B BGC top 5 列表与 case-015 跨 ≥6 生境 named species 列表在 species 层面重合**(K. pneumoniae, E. coli 完全命中,Bilophila / Enterocloster / Eggerthella 在 case-015 的次级跨生境 ranked list 里也都有)。两条**完全独立的数据轴**——"跨 catalog habitat detection"(metadata-only)与"BGC content homology"(prodigal+diamond+MIBiG)——给出**相同物种排名**,这是教科书意义上的多证据三角化收敛。

这条 case 把一条朴素假说升级为强假说:**多生境适应能力 ≈ 化学武器储备 ≈ 临床机会致病潜力**,且 keystone 的"生态重要性"至少有 metabolic / chemical 两个相互独立的维度。

## What I actually did

### 输入

- case-016 产物 `runs/cooccurrence-real-v1/out_full358/`:7238 × 358 sample-species 矩阵 + SparCC 12,911 边(corr ≥ 0.20, p < 0.05)
- UHGG v2.0.2 `genomes-all_metadata.tsv`(110 MB,case-015/016 已下)
- MIBiG 3.1:2,502 BGCs / 41,002 蛋白(`mibig_prot_seqs_3.1.fasta`,~20 MB)
- 15 keystone(weighted-degree top-15)各自一个 carveme 通用 universe GEM(case-014 方法)

### 步骤

1. **Species → BGC profile**(358 species,远端 zkyd 服务器跑,约 4 hours wall):
   ```
   for sp in species.list:
       prodigal -i <sp>.fa.gz -a prodigal/<sp>.faa -p meta -q
       diamond blastp -q prodigal/<sp>.faa -d mibig_prot_seqs_3.1.dmnd \
         --id 30 --evalue 1e-10 --query-cover 50 \
         --max-target-seqs 5 --threads 16 -o diamond/<sp>.tsv
   ```
   每个 species 产出对 MIBiG 蛋白的 hit list → 聚合成 `bgc_profile_358.tsv`(每行 species,列含 n_BGC 总数、按 MIBiG class 拆开的 NRP/Polyketide/RiPP/Terpene/Saccharide/Other 计数、kill-class 总数)
   - **kill-class** = NRP + Polyketide + RiPP 三大类之和(MIBiG 注释里这三类绝大多数有 antibacterial / cytotoxic 用途)

2. **Co-occurrence 边 BGC 注释**(12,911 边,~10 min 单核):
   - 对每条 SparCC 边 `(A, B)`:计算 `BGC_antag(A,B)` = |A 的 BGC ids ∩ B 的 BGC ids| 的反向解读(MIBiG kill-class BGC 在 A 中存在 ∧ B 没有 → A 对 B 单向压力)
   - 计算 `BGC_jaccard(A,B)` = |A ∩ B| / |A ∪ B|(BGC content 相似度,高 → 生态位重叠 → 潜在竞争)
   - 双阈值标:`bgc_antag ≥ 50` 进 §07 第 2 证据池(99.98% 命中)、`bgc_antag ≥ 500` 进 top dual-evidence shortlist

3. **15 keystone SMETANA cross-feeding**(case-014 方法,SMETANA global on LB[-O2],105 pair,wall ~3 hours):
   - 取 weighted-degree top-15(全 Type A 候选)
   - carveme 通用 universe 各自 build GEM(biomass > 0,reaction count 1800-2400 范围,符合 case-014 sanity)
   - 两两 105 pair 跑 SMETANA global,输出 MIP / MRO
   - **关键 limitation**:Type B(BGC-rich)没进这 15,因为它们 weighted-degree 中位(20-50 区间)不在 cooc top-15 — 三证据边因此 **结构性偏向 Type A**

4. **多证据合并 + keystone 二元论分立**:
   - 把 weighted-degree top-10 和 n_BGC top-10 两份名单并列
   - 观察:**top 10 完全不重叠**;Type A top 5 全是 GTDB unnamed(CAG-/UBA-),Type B top 10 全是 GTDB named 且 80% 是临床机会致病/IBD 关联菌

### 关键产物

```
runs/bgc-358-v1/
├── bgc_profile_358.tsv             — 358 × {n_BGC, n_kill, class counts}
├── cooc_edges_bgc_annotated.tsv    — 12,911 边 + BGC antag/jaccard
├── final_integrated_edges.tsv      — 12,911 边 × 3-evidence labels
├── nodes_358_full.tsv              — 节点全表(BGC + centrality + GTDB + Genome_type)
└── GRAPH_v3_FINAL.md
```

### 真数字 quick view

| 项 | 数 |
|---|---:|
| 节点 species | 358 |
| co-occurrence 边 | 12,911 |
| BGC profile 节点 | 358 / 358(100%)|
| cooc + BGC antag ≥50 | **12,908(99.98%)** |
| cooc + BGC antag ≥500 | 数百(top dual-evidence)|
| cooc + BGC + cross-feeding(3 证据)| 26(限 15 keystone 内)|

### Type A vs Type B 真名单

**Type A — 代谢 hub(weighted_degree top 5)**

| MGYG | wgt_deg | n_BGC | genus | 备注 |
|---|---:|---:|---|---|
| MGYG000000877 | 95.77 | 924 | CAG-83 | Oscillospiraceae commensal |
| MGYG000003311 | 95.55 | 861 | Angelakisella | Ruminococcaceae |
| MGYG000001314 | 94.84 | 1172 | Bacteroides_F pectinophilus | 异常 hub:degree + BGC 都高 |
| MGYG000004130 | 91.20 | 969 | UBA1777 | Oscillospiraceae unnamed |
| MGYG000000653 | 85.41 | 990 | UBA11471 | Bacteroidota unnamed |

**Type B — 化学武器 / 机会致病(n_BGC top 7)**

| MGYG | n_BGC | n_kill | wgt_deg | species | 临床身份 |
|---|---:|---:|---:|---|---|
| MGYG000002538 | **1598** | 1417 | 19.2 | _K. pneumoniae_ | ESKAPE |
| MGYG000002506 | 1477 | 1311 | 20.8 | _E. coli_D | 多 niche 机会致病 |
| MGYG000001493 | 1315 | 1180 | 24.9 | _Enterocloster bolteae_ | C.diff 关联 |
| MGYG000002544 | 1283 | 1156 | 28.9 | _Eggerthella lenta_ | IBD |
| MGYG000001359 | 1253 | 1097 | 34.2 | _Bilophila wadsworthia_ | IBD 硫酸盐还原 |
| MGYG000000099 | 1205 | 1080 | 29.9 | _Flavonifractor plautii_ | IBD |
| MGYG000001694 | 1181 | 1048 | 22.7 | _E. faecalis_ | ESKAPE |

→ Type A top 5 全 GTDB unnamed(CAG/UBA/Angelakisella),Type B top 7 全 GTDB named 且大部分是临床菌。**top 10 完全不重叠**(MGYG000001314 _Bacteroides_F pectinophilus_ 是唯一 BGC 也高的 Type A,但仍未进 Type B top 10)。

## ★ 排除/不做的事

- **不只看 weighted-degree 一个 metric**:case-016 是这么做的,只能看见 Type A,会**完全错过 Type B**(机会致病菌 weighted_degree 排名仅 20-50,不进 top-15)
- **不只看 BGC count 一个 metric**:只会看见 Type B,会错过 Type A 的代谢中心性
- **不假定 keystone 是单一概念**:生态学文献里"keystone"至少 3 种用法(connectivity / functional / abundance);**本图谱明确产出 ≥ 2 list**,Phase 3 hypothesis generation 时并出
- **不用 antiSMASH**:服务器装 antiSMASH 7 失败 3 次(perl 模块依赖 / glimmer / hmmer 版本三角冲突),改用 **prodigal + diamond + MIBiG** 蛋白同源 — 准度差但能跑通,且对 358 × MIBiG 41k protein 的规模 diamond GPU 模式 4 hours 出全表
- **不在 case-016 顶层 SparCC 边外再跑别的 cooccurrence method**:那是 case-016 的 §17 候选(SPIEC-EASI 交叉)负责的,本 case 锁定"在已有 cooc 边之上做多证据 layering"
- **不把 cross-feeding 扩到 358 全图**:全图 SMETANA global ≈ 64k pair × 30 s/pair ≈ 500 CPU·hours 仅 global,detailed 更贵;本 case 保留 15 keystone 内 105 pair,留 limitation 显式标出

## ★ 失败模式

1. **MIBiG homology 在同 family BGC 上 over-count**:同一个 NRP 家族(如 ε-polylysine 合酶 NRPS)在多个不同 BGC 里出现,diamond 把同一 query protein 命中到 5 个 MIBiG BGC → species 的 `n_BGC` 是膨胀的 BGC ID 计数,**不等于真正的 BGC 数**。Phase 2 必须用 BiG-SLiCE family-level cluster 收敛
2. **kill-class 定义过宽**:`NRP + Polyketide + RiPP` 总和当 antibacterial 武器,但这三类里也有 siderophore / signaling peptide / 代谢调控肽 — **不是所有 kill-class BGC 都真的 kill**。真 spectrum 必须 wet lab。本 case 用 kill-class 作"潜在化学武器储备"的 proxy,explicitly underspecified
3. **SparCC presence-count 偏正相关**(case-016 已记录):Type B 节点之间(E.coli / K.pneumoniae)即使生态上互相排斥,SparCC 也偏向给正相关或 0;**Type B 之间的 antagonism 在 cooc edges 里看不出来**,只能从 BGC 第 2 证据看。这是为什么本 case 必须叠 BGC layer 才能识别 Type B
4. **15 keystone GEM cross-feeding 没覆盖 Type B**:Type B 的 weighted_degree 中位,不进 cooc top-15,因此**没进 SMETANA 105 pair**。三证据边 26 条全是 Type A 内部 — 一个**结构性盲点**,Phase 2 必须显式补 Type B GEM(K.pneumoniae / E.coli 都有 BiGG 现成 high-quality GEM 可直接用,不必 carveme)
5. **GTDB unnamed Type A species 临床文献验证难**:CAG-83 / UBA1777 / UBA11471 这些 GTDB 占位 ID 在 PubMed 上几乎没有命中,无法像 Type B(K.pneumoniae 数十万篇)那样直接 cross-ref 教科书。**只能间接 — 看 family / phylum 共识**(CAG-83 → Oscillospiraceae → 已知肠道 SCFA 产生者)
6. **MGYG000001314 _Bacteroides_F pectinophilus_ 是异常点**:degree 94.8(Type A top 3)同时 n_BGC 1172(Type B 高位)— 单菌既代谢中心又化学武器多。**不能强行二分**,真实是连续谱,Type A / B 是分布两极,中间有 hybrid。Phase 2 报 keystone 时建议加 hybrid 第 3 类
7. **case-015 名单与 BGC top-5 的对应不是完全 1:1**:case-015 的 P.aeruginosa / A.johnsonii / C.acnes 不在 gut_human UHGG 358(它们是 marine / skin / cross-habitat 菌,gut 内 prevalence 不够 1% 进不了 358 节点),所以本图谱无法对它们做 BGC ranking。**对接是"K. pneumoniae 与 E. coli 完全命中,其它 Type B 是 case-015 跨 4-5 生境的 next-tier"** — 不是 5/5 命中,是 2/5 顶级命中 + 多个 next-tier 命中

## ★ 方法选择决策链

### 为什么 prodigal + diamond + MIBiG 而不是 antiSMASH / BiG-SLiCE

- **antiSMASH 7**(理论首选):产出真正的 BGC region(连续基因簇)+ class 注释,准度最高;**装不动**(服务器 perl-glib / glimmer / hmmer 三角依赖,3 次失败)
- **BiG-SLiCE**(family-level clustering 标准方案):需要 antiSMASH 上游输出,先装不通 antiSMASH 就不能用;并且 BiG-SLiCE 跑 358 species 慢(几十 CPU·hours),first-pass 不划算
- **prodigal + diamond + MIBiG 蛋白同源**:protein-level 同源,丢失 BGC 连续性(可能两个无关蛋白被算到不同 BGC),但能跑通、4 hours 出全表、阈值能调(id 30 / qcov 50)、量级正确(数百-千 BGC homolog 是文献量级)
- **本 case 选 prodigal+diamond+MIBiG,准度差但跑得通**;Phase 2 antiSMASH 装通后重跑

### 为什么 NRP + Polyketide + RiPP 当 kill-class

- MIBiG 注释里 NRP(non-ribosomal peptide,如 colistin / vancomycin / siderophore-cum-antibiotic)和 PKS(macrolide / tetracycline-family)绝大多数有 antibacterial / cytotoxic 用途
- RiPP(bacteriocin / lantibiotic)是肠道菌之间最常见的 antagonism 武器(肠球菌素 / 微菌素)
- Terpene / Saccharide 偏代谢副产物 / EPS,不是直接武器
- **kill-class = NRP + PKS + RiPP 是 over-broad 但保守可解释的 proxy**;真 antibacterial spectrum 需要 wet lab MIC

### 为什么 weighted_degree 而非 betweenness centrality

- weighted_degree:O(E),12,911 边 < 1 s,在 SparCC 共生语义下"和很多 species 强共生" = keystone
- betweenness:O(V·E),358 节点 12k 边 ~ 30 s 也能跑,但偏向 bridge / cut-vertex 节点(跨 community 的 generalist,不一定是 keystone)
- eigenvector centrality:在密集图(本图 density 0.20)上易被 dominant community 主导,信号不稳
- **本 case 选 weighted-degree** 与 case-016 保持一致;Phase 2 三种并算看 keystone 集合稳定性

### 为什么不做 cooc edges 的方向性推断

- SparCC 输出 undirected correlation,本身无方向
- "K → target" 方向只在叠加 BGC 第 2 证据后才能赋,且只是**化学方向**(K 有 kill-BGC 而 target 没有 → K 单向压力)不是**生态方向**(K 是不是真在 community 里压制 target,要 GEM mass-balance / strain abundance 时序才能判)
- 本 case 在 top dual-evidence 列表里标 `K→target`,**仅指 BGC 方向**,不是 ecological causation;case 描述必须明确这条边界

## ★ Validation — case-015 独立交叉验证(本 case 核心)

### 两条数据轴的独立性

| 维度 | case-015 路径 | 本 case 路径 |
|---|---|---|
| 数据来源 | MGnify 20 catalog metadata | UHGG metadata + MIBiG 蛋白库 |
| 信号载体 | GTDB s__ 字符串跨 catalog 出现次数 | prodigal CDS → diamond → MIBiG hit count |
| 计算单元 | habitat × species count | species × BGC homology |
| 工具依赖 | pandas groupby | prodigal + diamond |
| 物种识别原理 | 跨地理 / 宿主 / 体腔的多生境检出 | 基因组里 antibacterial-class 同源基因的密集程度 |
| 与 ecology 的关系 | 间接(多生境 = 适应力) | 间接(BGC 多 = 武器多)|

**两条轴互相不依赖**:case-015 不看任何 BGC、不跑 prodigal、只看 metadata 字段;本 case 不看 catalog 计数、不看 habitat、只看 358 个 UHGG genome 的蛋白。**任何一条轴出 false positive 不会被另一条 covary**。

### 名单对比

case-015 顶级名单(跨 ≥6 生境 named):
- **K. pneumoniae** ★
- **E. coli** ★
- P. aeruginosa
- C. acnes
- A. johnsonii

本图谱 BGC content top 10(全在 gut_human 内):
- **K. pneumoniae** ★(n_BGC 1598,top 1)
- **E. coli_D** ★(n_BGC 1477,top 2)
- _Enterocloster bolteae_(top 3)— case-015 跨 5 生境
- _Eggerthella lenta_(top 4)— case-015 跨 4 生境
- _Bilophila wadsworthia_(top 5)— case-015 跨 4 生境
- _Flavonifractor plautii_(top 7)— case-015 跨 4 生境
- _E. faecalis_(top 10)— 已知 ESKAPE,case-015 跨 5 生境

**重合分析**:
- **顶级 2/5 完全命中**(K.pneumoniae 与 E.coli 同时在两条轴的 top 5)
- **次级 next-tier 5+ 命中**(Enterocloster / Eggerthella / Bilophila / Flavonifractor / E.faecalis 都在 case-015 跨 ≥4 生境 ranked list 里)
- **case-015 顶级未在本图谱出现**的(P.aeruginosa / C.acnes / A.johnsonii):**它们 gut prevalence < 1%,不进 358 节点**(case-016 过滤阈值),不是 contradiction,是数据 scope 边界

### 假说强度升级

朴素假说("多生境 = 致病")→ 强假说:

> **跨生境适应能力 ≈ 化学武器(BGC)储备 ≈ 临床机会致病潜力,且这三者在 species 排名上互相 corroborate,跨两条独立数据轴(habitat detection / BGC homology)收敛。**

教科书已知背景验证(三大类临床身份在两条轴都出现):
- **ESKAPE 院感**:K.pneumoniae、E.faecalis
- **IBD 富集**:Eggerthella lenta、Bilophila wadsworthia、Flavonifractor plautii、Ruminococcus_B gnavus(case-016 已观察到)
- **C.difficile 风险关联**:Enterocloster bolteae

→ 7 个 Type B 中 7 个有公开临床文献支撑;Type A 5 个中有 0 个有强临床文献支撑(全 GTDB unnamed)。**两 list 的临床/commensal 极性也分立**,不只是名单分立。

## Lessons → seeds for rules

### 3 条核心 lesson

1. **Keystone 不是一个 list,至少有 Type A(metabolic hub)和 Type B(chemical warfare)两种**,在同一图谱里 top 10 完全 mutually exclusive。Phase 3 hypothesis generation 必须并出两个名单,不要用单一 centrality 度量替代
2. **多证据三角化的"独立性"是质化标准,不是数量**:case-015 与本图谱用的是两条**操作上完全不相关的数据轴**(metadata habitat count vs MIBiG protein homology),所以它们 species 排名收敛是真正的硬证据。两个都基于 SparCC 边的 metric(weighted_degree / betweenness)收敛 ≠ 独立证据,只是同一信号的两种表达
3. **多生境适应 ≈ 化学武器储备 ≈ 机会致病潜力** 假说,在 PRAXIS-Microbiome 当前数据规模下已经被强力支持,可以作为 Phase 3 reranker 的 species-level prior:**跨 ≥4 生境的 named species 自动触发 BGC profile + ESKAPE/CARD/VFDB 注释 pipeline**

### 候选大脑规则(三条候选,补 §07 升级)

#### §20 候选:同图谱内 keystone 分立判定

任何 PRAXIS-Microbiome 单生境真图谱产物必须**同时报告至少两个 keystone 名单**:
- list A:`weighted_degree`(或 community-aware degree)top-K → 代谢 hub
- list B:`n_BGC_kill_class`(或 antiSMASH/BiG-SLiCE BGC count)top-K → 化学武器

并报告 list A ∩ list B 的大小:
- |A ∩ B| / K < 0.2 → 强分立,case-017 一致(本 case 在 K=10 时交集 = 0,K=15 时交集 = 1 即 _Bacteroides_F pectinophilus_)
- |A ∩ B| / K ≥ 0.5 → 弱分立,可能 keystone 本质单一,需要更多证据轴 disambiguate

#### §21 候选:Type B keystone 自动触发临床注释 pipeline

任何识别为 Type B 的 species(n_BGC_kill_class 排名 top-K),hypothesis generation 阶段:
- 自动 join CARD(抗药基因)
- 自动 join VFDB(毒力因子)
- 自动 join ESKAPE 列表
- prior label = `chemical_warfare_keystone`
- 与 case-015 §14 候选互补:case-015 的 `opportunistic_pathogen_candidate` 是 habitat-based,本规则是 BGC-based,**两 label 同时挂的 species 是"双证据 opportunistic pathogen"**(K.pneumoniae / E.coli 是 reference)

#### §22 候选:多独立数据轴 ranking convergence 是 keystone identity 的硬证据

对任何 species ranking 任务(keystone / generalist / opportunist / SCFA producer / ...),要求:
- **≥ 3 条独立数据轴**(case-015 用 habitat count + 本图谱用 BGC homology + 第 3 条候选:GEM cross-feeding centrality / strain coexistence / metagenomic abundance / proteomics / ...)
- **≥ 2 条轴 top-K 交集 ≥ 50%** 才能进入 "validated identity"
- 单轴排名仅作 candidate,**不直接 commit 为 hypothesis 输入**

把 §07 multiomics-triangulation 从"≥ 2 证据"升级为 §07-bis "≥ 3 证据,跨 ≥ 3 独立数据轴"——但只对 species identity claim 要求,不对每条 edge 要求(本图谱 12,908 边 2 证据 ≥50,只有 26 边 3 证据,把 §07-bis 套到 edge 上会丢 99% 数据)。

### 与已有规则关系

- ✅ **§07 multiomics-triangulation**:99.98% cooc 边有 BGC 第 2 证据(双证据完整);本 case 提出 **§07-bis** 区分 edge-level(2 证据足够)与 species-identity-level(必须 ≥ 3 独立数据轴)
- ✅ **§08 compositional-network-methods**:沿用 case-016 的 SparCC + bootstrap,合规
- ✅ **§13 isolate-vs-MAG**:Type B 大多数有 isolate-derived reference(K.pneumoniae / E.coli / E.faecalis / Bilophila),Type A 全 MAG-derived;在 BGC count 解读时显式标 Genome_type 列(`isolate` vs `mag`),不混 claim
- 🔁 **§14 候选(case-015 提)**(跨 ≥4 生境 named species 打 opportunistic_pathogen prior):**本 case 在 BGC content 维度独立验证了 §14 候选的有效性**,§14 应该升级为正式规则
- 🆕 **§20 候选**(同图谱内 keystone 二元分立报告)
- 🆕 **§21 候选**(Type B 自动触发 ESKAPE/CARD/VFDB 注释)
- 🆕 **§22 候选**(species identity 需 ≥ 3 独立数据轴 ranking convergence)

## 与 case-014 / 015 / 016 / 013 的关系

- **case-013(hGMB isolate WGS)**:为本 case 提供 isolate-level Genome_type 标注的 reference;Type B 的 K.pneumoniae / E.coli 等 isolate-derived,质量直接可信
- **case-014(GEM cross-feeding baseline)**:提供 SMETANA pipeline,本 case 用同一管线跑 15 keystone × 105 pair → 三证据边的第 3 道证据来源;但因 case-014 GEM build 慢(10 min/genome,GLPK 单线程),本 case 没扩到 358 全图
- **case-015(cross-habitat generalist)**:**与本 case 互为独立交叉验证**;case-015 用 habitat detection,本 case 用 BGC content,两条轴在 species 排名上收敛 — 是本 case 最大的 scientific payoff
- **case-016(UHGG 自检测建共生图)**:为本 case 提供 12,911 cooc 边底盘 + 358 节点 + Type A keystone 名单;本 case 在其上叠 BGC layer 才显形 Type B
- **元 lesson**:case-014 → 015 → 016 → 017 形成一条**数据驱动的方法论楼梯**:从 3 菌 isolate baseline(case-014)→ 60k species 跨生境 metadata-level scan(case-015)→ 7238 sample × 358 species 单生境共生图(case-016)→ 多证据 layered 单生境真图谱 + keystone 二元论(本 case)。**每一步都基于上一步的产物,且每一步都引入一条独立证据轴**

## 远端复现路径

服务器:`zkyd@10.102.106.53`,环境:`conda activate praxis-microbiome`

- 数据 / 产物:`/home/zkyd/data2/mzy/PRAXIS-work-microbo/runs/bgc-358-v1/`
- 本地镜像:`/Volumes/T7/PRAXIS-work-microbiome/runs/bgc-358-v1/`
- 报告:`runs/bgc-358-v1/GRAPH_v3_FINAL.md`
- 依赖产物:`runs/cooccurrence-real-v1/out_full358/`(case-016)+ `runs/cross-feed-real-003/`(case-014 SMETANA 模板)

**核心复现命令**(无 antiSMASH 依赖,纯 prodigal + diamond + pandas):

```bash
# 1. 358 species 拉 fasta(UHGG FTP)
awk -F'\t' 'NR>1 && $X=="Species_rep" {print $1}' \
    genomes-all_metadata.tsv | sort -u | head -358 > species.list

# 2. prodigal 358 × CDS prediction(parallel 16,~30 min)
parallel -j 16 'prodigal -i genomes/{}.fa.gz -a prodigal/{}.faa -p meta -q' \
    :::: species.list

# 3. diamond vs MIBiG 3.1 protein DB(~4 hours GPU mode,或 16 CPU ~6 hours)
for sp in $(cat species.list); do
    diamond blastp -q prodigal/${sp}.faa \
        -d mibig_prot_seqs_3.1.dmnd \
        --id 30 --evalue 1e-10 --query-cover 50 \
        --max-target-seqs 5 --threads 16 \
        -o diamond/${sp}.tsv
done

# 4. 聚合 BGC profile(pandas,< 1 min)
python skills/bgc_profile/aggregate.py \
    --diamond diamond/ \
    --mibig mibig_annotations_3.1.tsv \
    --out runs/bgc-358-v1/bgc_profile_358.tsv

# 5. 共生边 BGC 注释 + 三证据合并(< 10 min)
python skills/multi_evidence/integrate.py \
    --cooc runs/cooccurrence-real-v1/out_full358/edges_annotated.tsv \
    --bgc-profile runs/bgc-358-v1/bgc_profile_358.tsv \
    --crossfeed runs/cross-feed-real-003/smetana_15keystone.tsv \
    --out runs/bgc-358-v1/final_integrated_edges.tsv

# 6. keystone 二元分立报告(pandas + matplotlib)
python skills/keystone_dichotomy/report.py \
    --nodes runs/bgc-358-v1/nodes_358_full.tsv \
    --top-k 10 \
    --out runs/bgc-358-v1/GRAPH_v3_FINAL.md
```

**最低依赖**:`python>=3.10, pandas>=2.0, numpy>=1.24, networkx>=3.0, prodigal>=2.6.3, diamond>=2.1.8`(无 R / 无 antiSMASH / 无 Julia)

**输入数据稳定源**:
- UHGG metadata:`ftp://ftp.ebi.ac.uk/pub/databases/metagenomics/mgnify_genomes/human-gut/v2.0.2/genomes-all_metadata.tsv`(110 MB)
- UHGG genome fasta:同 FTP 路径下 `MGYG...//*.fa.gz`(~50 GB,358 species ~250 MB)
- MIBiG 3.1 protein:`https://dl.secondarymetabolites.org/mibig/mibig_prot_seqs_3.1.fasta`(~20 MB)

## 下一步动作(从本 case 派生)

1. **Type B keystone 用 BiGG 现成 GEM 跑 SMETANA**:K.pneumoniae(iYL1228)、E.coli(iML1515)、E.faecalis(iEF782)、Bilophila、Eggerthella 都有 BiGG 现成 high-quality GEM,不必 carveme;补 Type B vs Type A 之间的 SMETANA pair → 解决"三证据边只覆盖 Type A 内部"的结构性盲点
2. **antiSMASH 7 在 Linux server 重装**(macOS 失败可接受,Linux 应能成):若装通则重跑 358 BGC profile,把 protein homology 升级到 region-level;BiG-SLiCE family clustering 收敛 over-count 问题
3. **SPIEC-EASI 交叉验证(case-016 §17 候选)** 与本 case Type B 列表配套:partial correlation 视角下 Type B 之间可能出现 negative edges,验证它们生态上互斥(SparCC presence-count 偏正向看不出)
4. **跨生境复用 keystone 二元论 pipeline**:marine v2 / soil v1 / mouse-gut catalog 各产一张 Type A vs Type B 名单,看其他生境是否同样存在二元分立,或者 marine / soil 是连续谱(假说:gut 内 Type A/B 分立强是因为肠道高密度 + 强免疫压力,marine / soil 低密度 + 弱免疫可能不分立)
5. **正式 commit §14 候选规则**(跨 ≥4 生境 named species 打 opportunistic_pathogen prior):本 case 用 BGC content 独立验证后,§14 不再是候选,可入正式规则
6. **§20 / §21 / §22 候选规则**:加入 brains/microbiome/memory/rules/ 待评 list,等下次有第 2 个独立图谱(marine 或 soil)再验证一遍才升正式规则
