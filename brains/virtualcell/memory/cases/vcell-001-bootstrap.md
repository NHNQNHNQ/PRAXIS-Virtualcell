---
case_id: vcell-001-bootstrap
schema_version: 1
task: perturbation_response_prediction
input_data: scRNA-seq baseline + perturbation spec
image_modality: null
sample_dimension: null
cell_type: generic
assay_format: null
channel_count: null
dataset_accession: null
antibodies_rrid: []
software_versions: {}
tools: [Coordinator, ExperienceQuery, EvalAgent]
key_paper_doi: null
provenance:
  source_type: bootstrap
  doi: null
  citation: "PRAXIS-virtualcell bootstrap seed (no literature)."
  extracted_at: 2026-06-11
  extraction_confidence: low
  unverified_details: ["placeholder case; replaced by real perturbation cases in Week 3/5"]
tags: [bootstrap, placeholder, virtualcell]
status: draft
---

# vcell-001:bootstrap 占位 case

## Background
PRAXIS-virtualcell 从 PRAXIS-2(b124d66)复制改造,`virtualcell` brain 初始化时的占位 case。
真实 perturbation cases(Norman / Replogle / Sciplex)与 species 分库自 Week 3 / Week 5 起填充。

## What I actually did
- 仅作为 brain 非空种子,保证运行时可载入 `virtualcell` 大脑。

## Lessons → seeds for rules
- 见 `memory/rules/_default_bootstrap.md`:benchmark 必比对、跨物种先查负迁移、simulated 自标、abstain 诚实报告。

## 关联
- donor 项目 `/Volumes/T7/Virtual-cell` 的 finding_015(abstain 三 bench 3/3 PASS)。
- 统一 Coordinator + abstain 路径(Week 4)。
