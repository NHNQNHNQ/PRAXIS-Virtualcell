---
case_id: synth-bad-004-empty-tools
task: flux_balance_analysis
host_organism: E. coli K-12 MG1655
tools: []
key_paper_doi: 10.1038/nbt.3956
status: validated
---

# Bad case 4: empty tools list

## Background
Required soft-field `tools` is empty; QA should flag.

## ★ 排除/不做的事
- Empty tools list (every case must specify what tools were used)

## ★ 失败模式
- No tool provenance
