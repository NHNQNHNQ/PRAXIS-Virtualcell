---
case_id: synth-bad-003-bad-task-enum
task: pretend_this_is_a_real_synth_task
host_organism: E. coli K-12 MG1655
tools: [COBRApy]
key_paper_doi: 10.1038/nbt.3956
status: validated
---

# Bad case 3: task not in canonical enum

## Background
The `task` field uses a value that is not in the 9-enum (or its ancestor mapping).

## ★ 排除/不做的事
- Inventing new task types

## ★ 失败模式
- Task enum drift over time without migration
