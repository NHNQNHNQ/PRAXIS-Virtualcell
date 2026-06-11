---
rule_id: 04-restriction-site-destroy
schema_version: 1
rule_type: case_distilled
applies_to:
  synth_tasks: [plasmid_assembly, codon_opt]
  host_organisms: [ALL]
  scale: [ALL]
evidence_cases: [synth-003-golden-gate-moclo, synth-006-dnachisel-restriction-removal]
confidence: high
last_updated: 2026-04-29
---

## 规则
所有进入 Golden Gate / MoClo / 同类 Type-IIs 流水线的 DNA cassette 必须通过 codon-silent 解构内部 BsaI / BsmBI / SapI（视使用酶）位点。未解构的内部 site 视为 fatal error。

## 依据
- **synth-003**：内部 BsaI 是 Golden Gate 失败原因 #1（cleaved internally → fragments don't ligate）
- **synth-006 (Zulkower 2020, DNA Chisel)**：DNAchisel 算法在保持氨基酸序列前提下解构 1×BsaI + 2×BsmBI，GC 40-60% 同时维持

## 边界 (★)
- Gibson assembly 不需要这一步（无 type-IIs）
- 若 cassette 完全合成且尚未引入限制酶位点，可跳过（但 audit 仍需记录）
- 反例：未报道

## How to apply
- **Design** stage：`computational_pipeline` 中 `golden_gate_assembly` 之前必须紧跟 `dna_constraint_solve` 或 `codon_optimize`（with `forbidden_sites: [BsaI, BsmBI, SapI]`）
- **Execution**：`golden_gate_assembly.run()` 内部 `internal_sites_count` 必须 == 0；否则 `passed_qc=false`
- **Reviewer**：检查 `execution_results.steps[].kind=golden_gate_assembly` 的 `internal_sites_count` 字段
