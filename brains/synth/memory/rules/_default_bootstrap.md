---
rule_id: _default_bootstrap
schema_version: 1
rule_type: cold_start_defaults
note: 案例库 < 5 时使用；案例库扩充后逐步被具体规则替代
last_updated: 2026-04-29
---

# 冷启动默认规则

当 `memory/cases/` 中有效案例 < 5 个，无法做有效检索时，PRAXIS-Synth 使用以下默认规则。这些是从合成生物学常识总结的最低限度安全准则，**不应替代实际案例学习**。

## 通用（适用所有 synth_task）

- 必须先识别 `synth_task ∈ {fba, pathway_design, plasmid_assembly, codon_opt, circuit, cell_free, biosensor, strain_engineering, bgc_mining}` —— 8 个 task 走完全不同 pipeline
- `host_organism` 决定 codon usage / promoter / regulatory；改 host 必须重做 codon optimize
- `scale ∈ {test_tube, shake_flask, fermenter, industrial}` 决定 wet-lab assay
- 任何 in silico 数字需 `tool_provenance.{simulated|partial|full, version, wallclock_seconds}`，不允许凭空写数字
- 任何 wet-lab 提议必须包含 ≥3 colony pick / ≥3 replicate

## FBA（synth_task = fba | strain_engineering）

- 必须先跑 MEMOTE 一致性 / mass balance / charge balance 检查再 FBA
- Multi-objective Pareto（biomass + product + co-factor）；single objective 视为不允许
- KO 计划必须先 `single_gene_deletion()` 排除 essential gene（growth ≤ 1% WT）
- Strain-specific model：iML1515 ↔ K-12；BL21/W3110 不直接套用
- Substrate uptake bound 必须显式列出
- Predicted essential 必须与 Keio 库或对应物种实际数据对照

## Pathway design（synth_task = pathway_design）

- 至少 3 种来源候选 enzyme set（RetroPath / KEGG graph / Cameo / BioCyc 任三）
- Heterologous expression 必须 codon optimize（host vs source organism 不同时强制）
- P450 必须配对 CPR partner；活性 assay 不可省
- 终产物 toxicity / feedback inhibition 提前评估

## Plasmid assembly（synth_task = plasmid_assembly）

- Golden Gate：所有 5'→3' overhang 唯一；palindrome / GC > 75% 自动剔除
- 内部 BsaI/BsmBI/SapI site 必须用 codon-silent 解构（DNAchisel-like solver）
- ≥3 colony pick + colony PCR + 全质粒 sanger/Plasmidsaurus

## Codon opt（synth_task = codon_opt）

- 默认 host CAI 提升 ≥ 0.3
- 保留 ~5% rare codon（避免过度优化破坏折叠）
- GC 35-55%，5'UTR 头 50 nt MFE > -10 kcal/mol
- 必须移除 BsaI/BsmBI/SapI（避免 Golden Gate downstream 坏掉）

## Circuit / biosensor（synth_task ∈ {circuit, biosensor}）

- Bistable / toggle 必须做 parametric sweep（4-D 参数扫描）
- 单细胞 readout：flow cytometry，禁用 plate-reader bulk
- Biosensor 必须 cross-reactant panel（≥5 类似底物）
- Dynamic range ≥ 5×；response time ≤ 30 min 优选

## Cell-free（synth_task = cell_free）

- TX-TL vs PURE 选择必须明示；mg/mL（TX-TL extract）vs μg/mL（PURE）
- Mg²⁺ 8-15 mM optimal；4-8h 最佳反应时长
- 多点 replicate（≥3）；extract 批次效应明示

## Strain engineering（synth_task = strain_engineering）

- OptKnock 输出必须经 essential-gene audit
- Top-N KO sets：N ≥ 3，多 seed（n_seeds ≥ 5）
- In silico vs in vivo gap 30-50% 常见，明示

## BGC mining（synth_task = bgc_mining）

- antiSMASH + DeepBGC 双工具 consensus
- Cross-MIBiG 校验 novelty；80% 旧 cluster 重发现率为 baseline
- 大 BGC（>50 kb）需要 Gene cluster 整合 strategy

## 升级触发

当 `cases/` 有 ≥ 2 个案例支持同一具体规则时，提升为正式 case_distilled rule（写到 `memory/rules/NN-...md`）。
