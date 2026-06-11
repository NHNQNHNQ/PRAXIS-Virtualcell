---
rule_id: 04-task-aware-tool-routing
schema_version: 1
applies_to:
  design_tasks: ["ALL"]
  fold_classes: ["ALL"]
evidence_cases: ["protein-005-igfold-antibody-cdr", "protein-006-foldseek-remote-homology", "protein-007-af-multimer-heterodimer", "protein-008-esmfold-throughput"]
confidence: high
last_updated: 2026-04-29
---

## 规则
工具选择必须**任务+fold-class 感知**——不是 hammer。Reviewer gate 阻塞已知错配：

| design_task | 必须用 | 不允许用 |
|---|---|---|
| antibody_cdr_modeling / antibody_design | IgFold + ImmuneBuilder + AbLang2 + (复合物时) SnugDock or AF-Multimer | 通用 AF-Multimer 单跑 / ESMFold（CDR 长度变异 OOD） |
| complex_prediction / structure_prediction_complex | AF-Multimer / AF3 / Boltz-1 with paired MSA | ESMFold（不支持 multimer，concat 是 pseudo-structure） |
| high_throughput_structure_prediction | ESMFold / OmegaFold + length-bucket batching | AF2 full（dbs 太慢）；不许跑 multimer |
| structure_search_homology | Foldseek + MMseqs2 并行 union | 单走结构 / 单走序列（远源同源会漏） |
| de_novo_binder | RFdiffusion + ProteinMPNN + AF2 with initial guess | 直接 AF2 from sequence（confidence 低）；超长 binder > 200 aa |
| stabilization | ProteinMPNN (T=0.1) + ThermoMPNN + Rosetta ddG (≥2/3 vote) | 单一 predictor；MPNN T ≥ 0.5 default |
| symmetric_oligomer_de_novo | RFdiffusion symmetric + tied-position MPNN + AF-Multimer | 普通 MPNN（破对称） |
| mutation_effect_prediction | ThermoMPNN ∩ Rosetta ∩ (PyRosetta or ESM-2 zero-shot) ≥ 2/3 vote | 任何单一 predictor 给 lab 推荐 |

## 依据
- **protein-005**：明文 "AF-Multimer > 50% false negatives on antibody-antigen"——必须 IgFold 走专用 stack
- **protein-006**：Foldseek + MMseqs2 union 才能 cover twilight zone（seq id < 25%）；TM-score 单跑膜蛋白 50+ false positive
- **protein-007**：ESMFold concat = pseudo-structure；AF-Multimer / AF3 / Boltz-1 是合法 multimer 工具
- **protein-008**：明文 "ESMFold cannot do multimer"；length-bucket batching 是 GPU 资源关键

## 边界 (★ 必填)
- "high throughput" 阈值是模糊的——本规则定义为 ≥ 100 sequence；< 100 应该用 AF2 full 求精度
- ESMFold 跑长链（> 1024 aa）需 chunking with loss of global context
- 不适用于"我已有结构"场景（structure_search_homology 已有 query → 跳过预测）

## How to apply
- **Scoping**：从 problem.design_task + problem.target 推荐 candidate_strategies[].tool_chain
- **Design**：design_pipeline 必须只用允许的工具
- **Reviewer**：扫描 design_pipeline 的 (skill_id, design_task) 对照表，命中 anti-pattern → block
  - `predict_complex` + tool == "ESMFold" → block
  - `antibody_pipeline` + tool ∈ {AF-Multimer-only, ESMFold} → block
  - `mutation_effect_scan` 的 design_pipeline 中 predictor 数 < 2 → block
  - `de_novo_binder_pipeline` length > 200 → warn (severe) → require user override
