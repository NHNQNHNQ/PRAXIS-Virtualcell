---
rule_id: 05-task-aware-tool-routing
schema_version: 1
applies_to:
  immuno_tasks: ["ALL"]
  hla_classes: ["ALL"]
  antigen_classes: ["ALL"]
evidence_cases: ["immuno-001-mhci-netmhcpan", "immuno-002-mhcii-long-peptide", "immuno-004-tcr-seq-clonality", "immuno-005-bcr-seq-lineage", "immuno-007-hla-imputation-rnaseq", "immuno-010-tcr-pmhc-docking"]
confidence: high
last_updated: 2026-04-29
---

## 规则
Tool 选择必须 task-aware；通用工具不可替代 task-specific 工具。具体路由表：MHC Class I → {NetMHCpan-4.1, MHCflurry-2, BigMHC}；MHC Class II → {NetMHCIIpan-4.3, MARIA, MixMHC2pred, MHCflurry-II}；TCR repertoire → {MiXCR-4.6, Immcantation, scirpy(scTCR)}+ {GLIPH2 / TCRdist3} for clustering；BCR repertoire → {MiXCR + IgBLAST + Immcantation suite (Change-O / Alakazam / SCOPer / Shazam)} + {dowser / partis} for lineage；HLA typing → ≥ 3 of {OptiType, arcasHLA, HLA-LA, seq2HLA, xHLA, Polysolver}；TCR-pMHC docking → TCRdock（NOT generic AF-Multimer / HADDOCK / ClusPro）。

## 依据
- **immuno-001**：MHC-I 用 IIpan 模型彻底跑偏；NetMHCpan EL_rank trained on MS data，BA score trained on 体外 binding，两个 score 含义不同
- **immuno-002**：MHC-II register prediction 不在 NetMHCpan model；用 generic Class I model 截断 long peptide 丢失 flanking + register 信息
- **immuno-004**：TCR-seq 用 generic short-read aligner 不合适；MiXCR 内置 V/J/CDR3 segmenter + UMI 处理 + correctness statistics；无 OOF rate 报告则结果不可信
- **immuno-005**：BCR lineage 与 TCR 不同 —— BCR 有 SHM (somatic hypermutation) + class switching，必须 Immcantation 全栈（MiXCR 仅做 V/J/CDR3）
- **immuno-007**：HLA typing 单 caller (OptiType only) 错误率 5-10%；3-caller consensus 才 ≥ 95% accuracy
- **immuno-010**：通用 PP-docker (HADDOCK / ClusPro) 不知 TCR-pMHC 几何先验 (CDR3α/β over peptide center, MHC restriction)；TCRdock 内置 prior，准度高 ~10x

## 边界 (★ 必填)
- 罕见任务（非 10 任务之一）走 cold-start bootstrap rule，但仍需声明 cold_start label
- ESM-IF / AF-Multimer 可作 TCR-pMHC 的 secondary validation（非主），需多 seed
- 已知反例：HLA-LA 在某些样本上 graph alignment 失败 → fallback 到 OptiType + arcasHLA 二 caller，需标 `low_consensus`

## How to apply
- **Scoping**：candidate_strategies 必须按上述路由表选 tool_chain；error 工具（如 NetMHCpan 跑 Class II）直接 reject
- **Design**：design_pipeline.skill_id 必须与 task 匹配（mhc_class_i_predict 不能跑 Class II）
- **Execution**：单 skill 不允许内部 fallback 到错误工具家族
- **Reviewer**：检测 mhc_class_ii_predict 用 NetMHCpan-4.1 → block；tcr_pmhc_dock 用 generic docker → block；hla_typing_from_rnaseq callers < 3 → warn (med severity)
