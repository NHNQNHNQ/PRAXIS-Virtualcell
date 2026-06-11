---
skill_id: cultured_isolate_wgs_real
status: ready
domain: isolate_wgs
stage: execution
microbiome_task: isolate_wgs_pipeline
sequencing_type: WGS_isolate
maps_to_case: microbiome-013-hgmb-isolate-wgs
maps_to_rule: 13-isolate-wgs-vs-metagenome
schema_version: 2
host_env: praxis-microbiome-kraken
---

# cultured_isolate_wgs_real

人源/鼠源**纯培养分离株**全基因组分析的一站式 skill（hGMB 范式，刘双江老师团队风格）。

## Inputs
- `--reads-r1` `--reads-r2` PE150 reads (fastq.gz)
- `--strain-id` 菌株 ID（如 `hGMB_001`）
- `--out-subpath` 远程 runs/ 子目录

## Pipeline (real, on remote zkyd@10.102.106.53)
1. **fastp** PE QC (Q20, len ≥50, adapter auto-detect)
2. **SPAdes --isolate** 单基因组组装（不要 metaSPAdes）
3. **QUAST** N50 / contigs / size
4. **CheckM2** completeness + contamination
5. **skani search** 与 hGMB type strain DB 比对（>95% ANI 即同种；如 hGMB DB 缺，用 GTDB-tk 兜底）
6. **Prokka** 基因预测 + 注释
7. **diamond vs KEGG KO** 通路注释（重点提取 SCFA / propionate / acetate KOs）
8. **abricate --db card** ARG 筛查
9. （可选）**antiSMASH** 次级代谢簇

## Outputs
- `assembly/scaffolds.fasta`
- `quast/report.tsv`
- `checkm2/quality_report.tsv`
- `species_call.tsv`（top-3 ANI hits）
- `prokka/{isolate.gff, isolate.faa, isolate.fna}`
- `ko_hits.tsv`（KEGG KO 命中）
- `scfa_pathway_summary.tsv`（butyrate / propionate / acetate KO 完整性矩阵）
- `arg_card.tsv`（CARD ARG 列表）
- `summary.json`（一站式汇总，confidence_label 内置）
- `reproduce.sh` + `environment.yml`

## Confidence rules
- All 9 steps real + CheckM2 completeness >95% AND contamination <5% AND ANI hit >95% → `high`
- 缺 GTDB-tk/hGMB DB（用 fastANI vs CGMCC type strain 替代） → `medium`
- antiSMASH 缺失 → `medium`（核心鉴定+通路足够，但 BGC 需要补 PRAXIS-Drug）
- 任一 hard 阶段 simulate → `low`

## Reviewer interaction
- 触发 rule-13 强制：如用户传入"分离株"标签但选了 metagenome pipeline → block `MICROBIOME_REVIEW_METAGENOME_FOR_ISOLATE`
- 自动豁免低生物量 negative-control 要求（分离株是高密度纯培养，不适用 rule-11）

## Cross-agent
- BGC list → PRAXIS-Drug `natural_product_bgc_from_isolate`
- ARG list → 可触发 PRAXIS-Pharma 警示（如菌株将用作 drug-microbe metabolism testing）

## 输出契约

```json
{
  "skill_id": "cultured_isolate_wgs_real",
  "n_samples": 0,
  "taxonomy_table": "",
  "diversity_metrics": {
    "shannon": 0.0,
    "observed_otus": 0
  },
  "diagnostics": {
    "brain": "microbiome",
    "archetype": "microbiome_pipeline"
  }
}
```
