---
rule_id: 20-anti-rules-from-NEG-cases
schema_version: 1
rule_type: anti_rule                     # 新类: 显式负向规则
applies_to:
  cazy_families: ALL
  cazy_class: ALL
  property: ALL
  enzyme_classes: ALL
evidence_cases:
  - NEG-KE07-khersonsky-2010-jmb           # 计算设计 baseline 不实用
  - NEG-EPISTASIS-bershtein-2006-nature    # multi-mutation epistasis
  - NEG-RETROALDO-jiang-2008-science       # de novo design 30% hit rate 上限
  - NEG-DEEVOLVE-obexer-2017-natchem       # evolution >> design
  - NEG-BFACTOR-sun-2019-chemrev           # B-factor saturation 30% 反向失败
  - NEG-DRIFT-tokuriki-2009-nature         # chaperonin 缓冲 → 工业 host 失稳
  - NEG-AFMUTATION-buel-2022-natstrmolbiol # AF model 不能用于 mutation effect
  - NEG-CONSENSUS-jackel-2010-jmb          # naive consensus phylogenetic bias
  - NEG-SCHEMA-otey-2004-chembiol          # SCHEMA chimera 命中率 ~10-20%
  - NEG-DOCKING-warren-2006-jmedchem       # docking system-dependent + score 不可信
  - NEG-FEP-cournia-2017-jcim              # FEP RMSE > 2 kcal/mol 在工业 case
  - NEG-RECOMBINATION-drummond-2005-pnas   # recombination conservatism, 多样性 trade-off
confidence: high                         # 12 evidence cases 跨多种工程化方法 + 多 enzyme class
last_updated: 2026-04-28
---

## 规则 — 12 条系统化反向规则 (Anti-Rules)

每条 anti-rule 是 explicit negative claim, 进入 `indices/anti/` 反向索引, 在 design agent 生成候选时作为 veto 信号.

### Anti-rule 1: 计算 de novo 设计 baseline 不是可用 enzyme
**形式**: 任何只用计算设计 (Rosetta / RFdiffusion / 类似) baseline 而 不接 ≥10 round directed evolution 的项目, 起始 kcat/KM 距实用酶 4-7 个数量级.
**Evidence**: `NEG-KE07-khersonsky-2010-jmb` + `NEG-RETROALDO-jiang-2008-science` + `NEG-DEEVOLVE-obexer-2017-natchem`
**Veto trigger**: 计算 design + 不评估 directed evolution 时间预算

### Anti-rule 2: Multi-mutation 加性假设错误
**形式**: 任何 ≥3 mutation 的 stacking 设计 (consensus / ProSAR / PyRosetta top-N / ML top-N) 必须直接构建 stacking variant 测试, 不能从 single-mutation 数据外推.
**Evidence**: `NEG-EPISTASIS-bershtein-2006-nature` + `NEG-DEEVOLVE-obexer-2017-natchem`
**Veto trigger**: ≥3 mutation 设计 + 不验证 stacking; 用 single-mutation 数据 ProSAR linear regression 外推 ≥4 mutation

### Anti-rule 3: B-factor saturation 不是默认 thermostability 协议
**形式**: B-factor 高位 saturation 在 ~30% case counter-productive — 必须先 explicit 排除 functional flexibility 位点 (substrate access loop / regulatory mobile loop). 低分辨结构 (>2.5 Å) 的 B-factor 排序工程化误导率高.
**Evidence**: `NEG-BFACTOR-sun-2019-chemrev`
**Veto trigger**: B-factor saturation 不做 functional flexibility 排除; 用 < 2.5 Å 分辨率结构 B-factor 排序

### Anti-rule 4: AF model 不可作 mutation effect predictor
**形式**: AlphaFold model (single mutant 输入) 输出几乎不变, 不能作 ΔΔG / mutation effect predictor. AF model 用于 active-site engineering 时必须 + X-ray 校正 (尤其 pLDDT < 70 区域).
**Evidence**: `NEG-AFMUTATION-buel-2022-natstrmolbiol`
**Veto trigger**: AF model + PyRosetta/Rosetta 单跑 mutation 排序; AF model active-site 不做 pLDDT 检查

### Anti-rule 5: Chaperonin-buffered 实验室稳定性 ≠ 工业稳定性
**形式**: lab E. coli (高 chaperonin) 工程化的 mutation 在 production host (Bacillus / Pichia / fed-batch fermentation) 失稳率上升 2-3 倍. 必须直接在 production host 验证.
**Evidence**: `NEG-DRIFT-tokuriki-2009-nature`
**Veto trigger**: 工业项目用 lab E. coli evolved variant 直接 ship + 不重新验证

### Anti-rule 6: Naive consensus 不是默认协议
**形式**: 直接 MSA frequency-counting 的 naive consensus 在 phylogenetic bias 下失败. 必须先 weighted MSA (按 phylogenetic distance) + 多 method (BLAST + HMM + tree) 互补 sanity check.
**Evidence**: `NEG-CONSENSUS-jackel-2010-jmb`
**Veto trigger**: consensus mutation + 不做 phylogenetic balance 检查; 用 NCBI BLAST top hits 直接当 MSA

### Anti-rule 7: SCHEMA chimera 命中率不超过 30%
**形式**: SCHEMA / DNA shuffling 等 intragenic recombination 的实测 chimera 命中率 ~10-20%, 与 de novo design 同量级. parent identity < 70% 时 SCHEMA 失败率急剧上升.
**Evidence**: `NEG-SCHEMA-otey-2004-chembiol` + `NEG-RECOMBINATION-drummond-2005-pnas`
**Veto trigger**: SCHEMA 期待 > 30% 命中率; parent identity < 70% 仍单 SCHEMA; cofactor-dependent enzyme 单 SCHEMA 不验 cofactor incorporation

### Anti-rule 8: Docking score 不直接对应 affinity
**形式**: 没有 universal best docking program; scoring function 整体不可信; cofactor-dependent enzyme docking 准确率显著低. 必须用 known X-ray binders 校准之后再用.
**Evidence**: `NEG-DOCKING-warren-2006-jmedchem`
**Veto trigger**: 单 docking score 排序候选 mutation; rigid + dry docking + 不 explicit water; 跨 system 转移 'best program' 经验

### Anti-rule 9: FEP/ABFE 工业 RMSE > 2 kcal/mol
**形式**: FEP 'easy' system retrospective RMSE < 1 kcal/mol, 工业 prospective system RMSE > 2 kcal/mol — 不 actionable. cofactor-dependent enzyme + 大 conformational change + multiple ionization states 是 FEP 'hard' system.
**Evidence**: `NEG-FEP-cournia-2017-jcim`
**Veto trigger**: FEP < 1 kcal/mol 假定外推到工业 case; 单 FEP 排序 ship 候选; 'hard' system 不 explicit treatment

### Anti-rule 10: 计算预测 ≠ 验证
**形式**: 任何计算工具 (PyRosetta / Rosetta / ML / FEP / docking) top-N 预测命中率 ~30-50%, 必须实验验证 top-N. 跳过实验直接 ship top-1 命中率 < 10%.
**Evidence**: `NEG-DEEVOLVE-obexer-2017-natchem` + `NEG-AFMUTATION-buel-2022-natstrmolbiol` + `NEG-DOCKING-warren-2006-jmedchem` + `NEG-FEP-cournia-2017-jcim`
**Veto trigger**: 任何计算工具 top-1 直接 ship 而无实验

### Anti-rule 11: Recombination 多样性 ≠ Random mutation 多样性
**形式**: SCHEMA / DNA shuffling 的 'usable variant diversity' 远低于 sequence-level 多样性. 大幅 substrate scope 改造时, random mutation + selection 比 recombination 更可能找到 distant variant.
**Evidence**: `NEG-RECOMBINATION-drummond-2005-pnas`
**Veto trigger**: 用 recombination 期待 fold-保 + 高多样性 双 win; parent identity < 50% 仍 SCHEMA

### Anti-rule 12: Random drift mutation 不是 'safe to compound'
**形式**: drift 后 mutation 是 'tolerable in starting context' 而非 'always tolerable'. 进一步 mutation 可让原 tolerable 变 lethal. 'lab-condition tolerable' 不等于 'production-condition tolerable'.
**Evidence**: `NEG-EPISTASIS-bershtein-2006-nature` + `NEG-DRIFT-tokuriki-2009-nature`
**Veto trigger**: random drift mutation 直接 stack 4+ 而无验证; lab Tm 数据外推 production yield

## 边界

- 12 条 anti-rules 不是 universal 否定, 是 'default skeptical priors' — 在 explicit 验证后可被 case-specific 推翻
- Anti-rule 优先级随 evidence 累积调整: rule 1 (12 evidence) > rule 7 (2 evidence)
- 与正向 rules (01 / 02 / 03 / 04 / family landscapes) 共存, 在 design phase **同时**触发

## How to apply

- **Scoping / Design Agent**: 候选 mutation 列表生成时, 顺序对照 12 条 anti-rules:
  1. 是否触发 anti-rule 1-12 的任一条件?
  2. 触发时, 标 candidate 为 'vetoed' + 写明 evidence_case_id
  3. 设计师必须 explicit 反驳或修正 vetoed 候选才能继续
- **Reviewer**: 检每个 anti-rule 是否被 explicit 检查过 (而不是默认通过)
- **RMCP Phase 4**: 新 evidence case 进 _proposed/ 时, 自动比对 anti-rules; 与既有 anti-rule 矛盾的 case 触发 conflict detection (Phase 3)

## 升级路径

每条 anti-rule 单独升级: ≥ 5 evidence cases + 至少 1 反例 (即 'anti-rule 在某 context 不成立' 的反向证据) 后, 重新评估 anti-rule 表述精度.
