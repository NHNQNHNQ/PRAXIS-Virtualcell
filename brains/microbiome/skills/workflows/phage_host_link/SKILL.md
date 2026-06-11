---
name: phage_host_link
description: |
  Phage-host link 边推断:基于 iPHoP(host prediction)+ CRISPR spacer 匹配,
  对一组细菌 host genome 和一组 viral contig,推断 phage → host 的边。
  履行 §07 multiomics-triangulation(两路独立证据:iPHoP score + CRISPR spacer match)。

  与 cooccurrence_network_real / cross_feeding_gem 互补:co-occurrence 给共变信号,
  cross-feeding 给代谢机制,本 skill 补"谁吃谁(裂解/溶原)"的捕食/寄生维度。
  Phase 0 五种边里的第 4 种(strain coexistence 是第 5 种)。

inputs:
  host_manifest:          TSV (required)  genome_id<TAB>fasta_path(细菌基因组)
  viral_manifest:         TSV (required)  contig_id<TAB>fasta_path(噬菌体 contig)
  crispr_spacer_db:       TSV (optional)  spacer_id<TAB>sequence<TAB>host_genome_id
  iphop_db:               str (default 自带 /data/db/iphop_db)
  iphop_score_min:        float (default 90)  iPHoP confidence score 阈值(MGnify default)
  spacer_min_identity:    float (default 0.95) blastn identity
  spacer_min_coverage:    float (default 0.95) blastn 覆盖度
  out_subpath:            str (required)
  timeout_s:              int (default 7200)

outputs:
  edges_tsv:    TSV  phage_id<TAB>host_id<TAB>iphop_score<TAB>spacer_hit<TAB>edge_class
  summary_json: JSON  {n_phages, n_hosts, n_pairs_tested, n_significant_edges, n_dual_evidence}

env: praxis-microbiome-phage (remote — iPHoP + blastn,需要 GPU 或大内存)
status: scaffold
stage: execution
domain: network
rules: [7, 13]
---

# phage_host_link

## 为什么需要这个 skill

Co-occurrence 出"共变"、cross-feeding 出"代谢互补",但都解释不了**捕食/寄生**这种本质上"谁吃谁"的关系。Phage-host 边是微生物群落动力学里最被严重低估的一块——肠道里 phage 丰度和宿主菌强相关但方向恰恰相反,**phage 才是真正的"top-down 调控者"**。

PRAXIS-Microbiome Phase 0 最小闭环要求 5 种边:
1. co-occurrence(SparCC)— 已实装
2. metabolic cross-feeding(GEM)— 已实装
3. BGC antagonism(antiSMASH)— 在做
4. **phage-host link** — 本 skill
5. strain coexistence(`strain_tracking_real`)— 已实装

## 流程

```
host_manifest.tsv        viral_manifest.tsv
        │                        │
        │                        ├── iPHoP predict ──→ host prediction + confidence
        │                        │     (k-mer + blast + RaFAH ensemble)
        │                        │
        └── CRISPR spacer DB ────┴── blastn-short ──→ spacer-protospacer hit
              (host → spacers)              (identity ≥ 0.95)
                                                │
                                                ▼
                                  merge by (phage_id, host_id)
                                                │
                                                ▼
                                            edges.tsv
                          edge_class ∈ {iphop_only, crispr_only, dual_evidence}
```

阈值(可由 inputs 覆盖):
- iPHoP confidence score > 90(MGnify 推荐默认,score 是 0–100)
- CRISPR spacer blastn identity ≥ 0.95 且 coverage ≥ 0.95
- edge_class:
  - `dual_evidence` — 同时通过两路 → 最强证据,直接进 Tier-1 边
  - `iphop_only` — 只有 iPHoP,可能是新宿主预测 / 历史感染信号
  - `crispr_only` — 只有 spacer hit,说明 host 曾被感染并存活,但当前 phage 可能已绕过免疫

## 规则锚

- **§07 multiomics-triangulation**:每条边 ≥2 独立证据。本 skill 用 iPHoP(k-mer 同源 + RaFAH)+ CRISPR spacer(历史感染留下的免疫记录)— 两条**生物学独立**,不同时间窗口、不同机制
- **§13 isolate-wgs-vs-metagenome**:有 isolate WGS host 优先(CRISPR array 提取更准确,iPHoP 也更可靠)— 上游 `cultured_isolate_wgs_real` 已经把 isolates 前置

## Sanity baseline

`tests/baselines/phage_host_demo/`(待造):
- 3 个肠道 host:_E. coli K-12_、_B. fragilis NCTC 9343_、_Lactobacillus reuteri_
- 3 个 GPD(Gut Phage Database)phage:ε15-like(E. coli)、crAss-like(B. fragilis)、Lj928 prophage(L. reuteri)
- 通过条件:edges_tsv 中至少 2 条 `dual_evidence`(对应 ε15 → E. coli、crAss → B. fragilis)

## 用法

```bash
# 本地 simulate(Mac/CI 都可):
echo '{"simulate": true, "seed": 42}' | python3 run.py

# 远端 real(server-only,需 iPHoP + blastn):
echo '{
  "simulate": false,
  "host_manifest": "data/gut_demo/hosts.tsv",
  "viral_manifest": "data/gut_demo/viral.tsv",
  "crispr_spacer_db": "data/gut_demo/spacers.tsv",
  "iphop_db": "/data/db/iphop_db",
  "iphop_score_min": 90,
  "spacer_min_identity": 0.95,
  "spacer_min_coverage": 0.95,
  "out_subpath": "runs/phage-host-001/out"
}' | python3 run.py
```

环境变量:
- `PRAXIS_SKILL_DRY_HOST=1` → 跳过 subprocess,只回 envelope(给 SkillExecTool 干跑用)

## 输出契约

```json
{
  "ok": true,
  "skill_id": "phage_host_link",
  "n_samples": 0,
  "taxonomy_table": "",
  "diversity_metrics": {
    "shannon": 0.0,
    "observed_otus": 0
  },
  "diagnostics": {
    "brain": "microbiome",
    "archetype": "microbiome_pipeline",
    "n_phages": 0,
    "n_hosts": 0,
    "n_pairs_tested": 0,
    "n_significant_edges": 0,
    "n_dual_evidence": 0,
    "edges_tsv": "",
    "summary_json": "",
    "tool_versions": {"iphop": "", "blastn": ""}
  }
}
```

`taxonomy_table` 复用为 edges_tsv 绝对路径;`diversity_metrics.observed_otus` 复用为 n_significant_edges。envelope 兼容代价,不爽但跨 skill 一致。

## 已知限制

1. **iPHoP 慢**:full-mode 几分钟/contig(RaFAH + CRISPR + blast 三 stacker),viralome 级别(10k+ contig)需 GPU 加速或分 batch
2. **CRISPR spacer DB 要预提**:用 CRISPRCasFinder / MinCED 从 host genome 抽 spacer 才能跑 — 不是本 skill 的职责,假设上游已给
3. **iPHoP DB 占盘**:full DB ~500 GB,远端服务器需提前下;若只 host genus 级,可用 Sept_2021_pub_rw mini DB(~50 GB)
4. **edge 方向**:phage → host(感染方向),与 cross-feeding 的 donor → receiver 方向是**完全不同语义** — 下游聚合时注意区分
5. **没处理 prophage / temperate**:当前只看 lytic 信号;溶原(prophage 整合)需要另跑 PHASTER / VIBRANT,留给后续 skill
