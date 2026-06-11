---
skill_id: scfa_butyrate_screen_real
status: ready
domain: functional
stage: execution
microbiome_task: scfa_pathway_screen
sequencing_type: shotgun_short
maps_to_case: microbiome-013-hgmb-isolate-wgs
maps_to_rule: 04-shotgun-uses-humann-not-picrust
schema_version: 2
host_env: praxis-microbiome-humann
---

# scfa_butyrate_screen_real

针对 SCFA / butyrate / propionate / acetate 通路的**专项 KEGG KO 筛查**。可用于：
1. 单个分离株基因组（hGMB 风格）
2. shotgun 元基因组的 HUMAnN3 输出
3. MAG 集合（dRep 后的代表基因组）

基于 Vital et al. 2014 (*mBio*) + Louis & Flint 2017 (*FEMS Microbiol Lett*) 的通路 KO 定义。

## Inputs
- `--input-faa` 蛋白 fasta（来自 Prokka 或 Prodigal）；OR
- `--input-humann-genefamilies` HUMAnN3 gene-family 表
- `--out-subpath`

## Output
- `scfa_pathway_summary.tsv` — 每条通路的 KO 完整度 + status (COMPLETE/PARTIAL/ABSENT)
- `scfa_producers.tsv` — 已知 SCFA 产生菌阳性比对（*Faecalibacterium*, *Roseburia*, *Eubacterium hallii*, *Anaerostipes*, *Butyricicoccus*, *Coprococcus*）
- `summary.json`

## Pipeline (real, on remote)
1. 若输入 .faa：diamond blastp vs UniRef90 (existing HUMAnN3 ChocoPhlAn DB)
2. 若输入 humann genefamily 表：直接抽 KO 行
3. `tools/scfa_ko_scan.py` 计算每条通路 KO 完整度
4. 与 hGMB type-strain SCFA 表比对，标注是否匹配已知 producer

## Confidence
- Real KEGG KO scan + ≥1 通路 COMPLETE → `high`
- 仅 PARTIAL 通路 → `medium`
- ABSENT 全通路 → `low`（可能不是 SCFA 产生菌或注释不全）

## 输出契约

```json
{
  "skill_id": "scfa_butyrate_screen_real",
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
