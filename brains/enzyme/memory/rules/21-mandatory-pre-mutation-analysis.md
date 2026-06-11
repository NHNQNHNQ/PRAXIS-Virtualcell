---
rule_id: 21-mandatory-pre-mutation-analysis
schema_version: 1
rule_type: hard_protocol                  # 与 anti-rule (rule 20) 同等强制力, 但是正向规则
applies_to:
  cazy_families: ALL
  cazy_class: ALL
  property: ALL
  enzyme_classes: ALL
evidence_cases:
  # 触发本规则形式化的 NEG- cases
  - NEG-AFMUTATION-buel-2022-natstrmolbiol     # AF 单跑 ddG 失败
  - NEG-BFACTOR-sun-2019-chemrev               # B-factor saturation 不滤功能 loop
  - NEG-CONSENSUS-jackel-2010-jmb              # naive consensus phylogeny bias
  - NEG-EPISTASIS-bershtein-2006-nature        # multi-mutation 加性失败
  - NEG-DEEVOLVE-obexer-2017-natchem           # 计算预测 top-1 不验
  # 与 6 个新分析 skill 的 evidence 对接
  - GH7-heinzelman-2009-pnas                    # SCHEMA + ConSurf-like analysis
  - GH7-goedegebuur-2017-jbc                    # MD + multi-tool validation
  - HHDH-fox-2007-natbiotechnol                 # ProSAR 多工具
  - GH11-turunen-2002-jbiotechnol               # multi-strategy analysis stack
confidence: high                          # 12 evidence + 6 强制工具 + 长期实证
last_updated: 2026-04-29
---

## 规则 — 突变候选生成前的强制分析清单 (Hard Rule 9 形式化)

任何 mutation 候选**进入 design_artifact 之前**, 必须有至少**3 类独立分析证据**支撑. 缺任一类, design 阶段被 review agent 拒绝, 不允许进入 execution.

### 强制分析的 6 个维度 + 对应 skill

| # | 分析维度 | 对应 skill | 强制度 |
|---|---|---|---|
| **1** | 催化 / 辅因子 / 界面位点排除 | `catalytic-site-annotator` | **入口必跑** (Hard Rule 4 强制) |
| **2** | 序列保守性 + co-evolution | `conservation-msa-analyzer` | **mutation 候选生成前必跑** |
| **3** | 结构上下文 (DSSP + RSA + depth) | `structural-context-analyzer` | **mutation 候选生成前必跑** |
| **4** | PLM zero-shot 突变效应 | `esm-mutation-scan` | **每个候选必有 ESM 分数** (PLM 不可用时显式降级 confidence) |
| **5** | 起始结构置信度 (X-ray 或 AF + pLDDT) | `pdb-fetcher` 或 `alphafold-plddt-analyzer` | **入口必跑** (Hard Rule 4) |
| **6** | 底物访问 / 口袋几何 (substrate / activity 工程化时) | `pocket-tunnel-analyzer` | **substrate-scope / regio / activity 任务强制** |

外加:
| **7** | 稳定性 ΔΔG | `pyrosetta-stability-scan` | thermostability 任务强制; 其他任务推荐 |

## 强制分析门控的最低组合 (按工程目标分)

| 工程目标 | 最低 skill 组合 |
|---|---|
| **Thermostability** | catalytic + conservation + structural + ESM + PyRosetta (5) |
| **Substrate scope / Specificity** | catalytic + conservation + structural + ESM + pocket-tunnel + 底物 SMILES 比对 (6) |
| **Activity / kcat** | catalytic + conservation + structural + ESM + pocket-tunnel + 可选 MD (5-6) |
| **Regio/Stereoselectivity** | catalytic + conservation + structural + ESM + pocket-tunnel + 多构象 docking 验证 (6+) |

## Mutation 候选必带字段 (★ design_artifact 强制)

每个候选 mutation 进入 design_artifact 时, 必须显式带以下 evidence_chain:

```json
{
  "mutation": "F87V",
  "evidence_chain": {
    "catalytic_check": {"position_in_excluded_positions": false, "from_skill": "catalytic-site-annotator", "rationale": "not catalytic, not cofactor, not disulfide, not interface"},
    "conservation": {"consurf_score": 2, "shannon_entropy": 2.34, "msa_freq_top3": [["F",0.42],["V",0.28],["L",0.15]], "verdict": "variable_engineerable", "from_skill": "conservation-msa-analyzer"},
    "structural_context": {"ss": "loop", "rsa": 0.42, "depth_A": 1.8, "loop_classification": "structural_loop_NOT_functional", "from_skill": "structural-context-analyzer"},
    "esm_score": {"esm1v_mean": -0.45, "esm1v_std": 0.18, "interpretation": "neutral_PLM_tolerated", "from_skill": "esm-mutation-scan"},
    "structure_basis": {"pdb_id": "1CEL", "plddt_or_resolution": "1.8 A X-ray", "from_skill": "pdb-fetcher"},
    "pocket_geometry": {"in_tunnel": false, "in_pocket": true, "lining_role": "shape_defining", "substrate_clash_pre_mut": false, "from_skill": "pocket-tunnel-analyzer"},  
    "ddG_simulated": {"pyrosetta_mean_kcal_mol": -0.8, "pyrosetta_std": 0.32, "is_simulated": true, "from_skill": "pyrosetta-stability-scan"},
    "case_evidence": ["GH7-heinzelman-2009-pnas", "GH7-goedegebuur-2017-jbc"],
    "rule_evidence": ["01-thermostab-mutation-priors", "GH-engineering-landscape"],
    "anti_retrieval_status": "not_vetoed",
    "anti_rule_triggers": []
  }
}
```

## 缺失分析时的兜底降级 (★ 不允许跳过)

| 缺失分析 | 兜底降级 |
|---|---|
| ESM 不可用 (无 GPU / 网络 / fair-esm 装不上) | confidence 上限 = low; 必须用 EVE / Tranception 替代且报 warning |
| AF model 但无 X-ray (pLDDT < 70 在活性位点) | confidence 上限 = cold_start; 强制等 X-ray 解出 |
| Conservation MSA < 50 sequences | confidence 上限 = low; 标 "low MSA support" |
| Pocket-tunnel 不可计算 (CAVER 装不上) | substrate engineering 任务 confidence 上限 = low |
| PyRosetta 缺 binary (simulated 模式) | thermostability 推荐永远标 simulated, 不允许 high confidence |

## 与 Anti-rule (rule 20) 的关系

本规则 (rule 21) 是**正向门控**: "必须做什么". Rule 20 是**反向门控**: "禁止做什么". 两者协同:

- 候选先过 rule 21 强制分析门控 → 拿到 evidence_chain
- 候选再过 rule 20 anti-retrieval 检查 → 与 12 anti-rule 比对
- 双关都通过才能进 execution 阶段

## 与 Hard Rule 9 的关系

Hard Rule 9 (强制结构化分析门控) 是 agent prompt 层的硬约束. Rule 21 是 memory 层的形式化对应——agent prompt 引用 rule 21 作为 design_artifact 的强制 schema.

## 边界

- **不适用**: 纯 retrieval 任务 (用户只问"GH7 cellobiohydrolase 有哪些已知突变") 不强制走全分析链
- **强制例外**: 计算 de novo 设计 + 接 ≥10 round DE 路线 (anti-rule 1) 时, 起点不需要全 evidence_chain (因为还没有候选), 但**evolved variant 进入 case 库前必须补全 evidence_chain**
- **degraded mode**: 当本地环境受限 (无 GPU + 无网络) 时, 允许 confidence 上限 = low 的 partial chain; 但必须在 design_artifact 显式标 `degraded_analysis: true`

## How to apply

- **Scoping Agent**: 识别工程目标后, 列出对应任务的最低 skill 组合 (见上表)
- **Design Agent**: 调用 6 个分析 skill, 等所有 skill 输出齐才允许生成候选 mutation; 每个候选必带完整 evidence_chain
- **Execution Agent**: 仅在 evidence_chain 齐全的候选上做后续 PyRosetta / docking
- **Reporting Agent**: recommendation 中必须显示每个推荐 mutation 的 evidence_chain 字段
- **Reviewer**: 检查 design_artifact 中每个 mutation 的 evidence_chain 完整性; 缺任一 required 字段直接 reject 整个 design_artifact

## 升级路径

本规则进入 high confidence 因为有 12 NEG- 反例直接证明 "不做这些分析就会出错" 的失败模式. 升至 domain_knowledge 需要在 ≥ 50 个新工程化项目的湿实验回流后, Memory-ECE 在带 evidence_chain 的推荐与不带的推荐之间显著分化 (差距 > 20 百分点).

## Failure mode 反例

虽然本规则是正向, 但其证据基础来自 NEG- cases 显示的失败模式:

- **NEG-AFMUTATION**: AF model 单跑 → 失败. 解法: 先跑 alphafold-plddt-analyzer 标 use_xray_first_required.
- **NEG-BFACTOR**: B-factor 单 metric saturation → 失败. 解法: structural-context-analyzer 输出 functional flexibility loop 列表, 强制排除.
- **NEG-CONSENSUS**: naive consensus → 失败. 解法: conservation-msa-analyzer 强制 phylogenetic weighting.
- **NEG-EPISTASIS**: 多突变加性外推 → 失败. 解法: esm-mutation-scan 输出 std + co-evolution 输出 strong pair, 多突变设计前显式 stack 验证.
- **NEG-DEEVOLVE**: 计算预测 top-1 不验 → 失败. 解法: 多分析共识 + 实验验证, evidence_chain ≥ 3 类.

## 引用 / 关联资源

- skills/workflows/catalytic-site-annotator/SKILL.md
- skills/workflows/conservation-msa-analyzer/SKILL.md
- skills/workflows/structural-context-analyzer/SKILL.md
- skills/workflows/esm-mutation-scan/SKILL.md
- skills/workflows/alphafold-plddt-analyzer/SKILL.md
- skills/workflows/pocket-tunnel-analyzer/SKILL.md
- skills/workflows/pyrosetta-stability-scan/SKILL.md
- memory/rules/20-anti-rules-from-NEG-cases.md (rule 20 反向门控)
