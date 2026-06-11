---
name: cross_feeding_gem
description: |
  Genome-scale Metabolic Model (GEM) 驱动的 metabolic cross-feeding 边推断。
  对一组 genome 跑 CarveMe → SMETANA(global + detailed),再用 KEGG MODULE
  互补性做正交证据(满足规则 §07 multiomics-triangulation,2 独立证据)。
  输出 species-level directed edges:donor → receiver,标 metabolite + 置信。

  与 cooccurrence_network_real 互补:co-occurrence 给共变信号,本 skill 给
  机制信号。两条合一,才算"互作"。

inputs:
  genome_manifest:        TSV (required)  genome_id<TAB>fasta_path[<TAB>gem_sbml_path]
  kegg_module_table:      TSV (optional)  genome_id<TAB>module_id<TAB>completeness(0-1)
  out_subpath:            str (required)
  candidate_pair_filter:  str (default kegg_module)  kegg_module | all
  smetana_score_min:      float (default 0.1)        SMETANA global score 阈值
  metab_prob_min:         float (default 0.5)        SMETANA detailed metabolite 概率阈值
  carveme_template:       str (default auto)         gramneg | grampos | archaea | auto
  community_media:        str (default M9)           SMETANA 模拟培养基
  timeout_s:              int (default 7200)

outputs:
  edges_tsv:              TSV  donor, receiver, metabolite, smetana_prob, smetana_global, kegg_module_support, edge_class
  gem_manifest_json:      JSON {genome_id: sbml_path, checksum}
  summary_json:           JSON {n_genomes, n_pairs_tested, n_significant_edges, params}

env: praxis-microbiome-cobra (remote — carve + smetana + cobrapy + python3 ≥ 3.10)
status: scaffold
stage: execution
domain: network
rules: [7, 13]
---

# cross_feeding_gem

## 为什么需要这个 skill

Co-occurrence 边只是"共变",**互作机制**要靠代谢互补 / 拮抗 BGC / 物理 contact 三条证据。本 skill 出第一条:**directed metabolic cross-feeding**。

PRAXIS-Microbiome 大脑现有 `cooccurrence_network_real`(共变)+ `multiomics_integration_real`(跨组学三角化)。`cross_feeding_gem` 是 Phase 0 最小闭环里把"代谢机制"补上的关键一环。

## 流程

```
genome_manifest.tsv
       │
       ├──[若无 GEM]── CarveMe(carve --fbc2)──→ <id>.xml
       │
       ├──[若有 KEGG MODULE 表]── 互补预筛 ──→ candidate pairs(O(k·n) 而非 O(n²))
       │
       └── SMETANA detailed(对每对 candidate)──→ donor/receiver/metabolite/prob
                                                │
                                                ├── + KEGG MODULE 正交支持
                                                │   (donor 完整 produces;receiver 缺失 consumes)
                                                │
                                                └── edges_tsv + summary
```

阈值(可由 inputs 覆盖):
- SMETANA global score > 0.10
- SMETANA detailed metabolite prob > 0.50
- edge_class = `metabolic_cross_feeding`(可加 `_kegg_supported` 后缀)

## 规则锚

- **§07 multiomics-triangulation**:每条边 ≥2 证据 — 这里是 SMETANA detailed + KEGG MODULE 完整/缺失互补
- **§13 isolate-wgs-vs-metagenome**:有 isolate WGS 优先(质量更高,GEM 构建更可靠)— 上游 habitat_router 已经把 isolates 前置

## Sanity baseline

引用 `tests/baselines/cross_feeding_demo/manifest.tsv`(待造)
- 3 个肠道菌:_Bacteroides thetaiotaomicron_ + _Eubacterium rectale_ + _Faecalibacterium prausnitzii_(经典 fiber → acetate/lactate → butyrate 三级链)
- 通过:edges_tsv 至少含 `B.theta → E.rectale (acetate)` 和 `E.rectale → F.prausnitzii (lactate)`,两边都 smetana_prob > 0.5

## 用法

```bash
# 本地 simulate(Mac/CI 都可):
echo '{"simulate": true, "seed": 42}' | python3 run.py

# 远端 real(server-only):
echo '{
  "simulate": false,
  "genome_manifest": "data/gut_demo/manifest.tsv",
  "kegg_module_table": "data/gut_demo/kegg_modules.tsv",
  "out_subpath": "runs/cross-feed-001/out",
  "candidate_pair_filter": "kegg_module",
  "smetana_score_min": 0.1,
  "metab_prob_min": 0.5
}' | python3 run.py
```

环境变量:
- `PRAXIS_SKILL_DRY_HOST=1` → 跳过 subprocess,只回 envelope(给 SkillExecTool 干跑用)

## 输出契约

```json
{
  "ok": true,
  "skill_id": "cross_feeding_gem",
  "n_samples": 0,
  "taxonomy_table": "",
  "diversity_metrics": {
    "shannon": 0.0,
    "observed_otus": 0
  },
  "diagnostics": {
    "brain": "microbiome",
    "archetype": "microbiome_pipeline",
    "n_genomes": 0,
    "n_pairs_tested": 0,
    "n_significant_edges": 0,
    "edges_tsv": "",
    "gem_manifest_json": "",
    "summary_json": "",
    "tool_versions": {"carve": "", "smetana": ""}
  }
}
```

`taxonomy_table` 复用为 edges_tsv 的绝对路径;`diversity_metrics.observed_otus` 复用为 n_significant_edges。这是 envelope 兼容的代价,不爽但跨 skill 一致。

## 已知限制

1. CarveMe 需要 LP solver(CPLEX/Gurobi/GLPK)— 远端服务器需提前装好
2. KEGG MODULE 表需要先跑 `kofamscan + KEGGmapper`(或现成 anvi'o estimate-metabolism)— 不是这个 skill 的职责
3. SMETANA O(n²) pair simulation,n > 100 时建议先 KEGG 预筛
4. 当前不处理 strain-level(species pooled GEM);需要 strain 时改用 `strain_tracking_real` 后接小集合 GEM
