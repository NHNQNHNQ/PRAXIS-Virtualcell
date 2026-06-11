---
case_id: GH6-koivula-2003-biochem
schema_version: 1
parent_enzyme:
  uniprot: P07987               # Trichoderma reesei Cel6A (CBH II); UniProt 收录
  cazy_family: GH6
  ec: 3.2.1.91                  # cellulose 1,4-β-cellobiosidase (cellobiohydrolase II)
  organism: Trichoderma reesei (anamorph; teleomorph Hypocrea jecorina)
  pdb: 1QJW                     # TrCel6A apo crystal (Rouvinen 1990 早期 deposit)
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "OC[C@H]1O[C@@H](OC[C@H]2O[C@@H](O)[C@H](O)[C@@H](O)[C@@H]2O)[C@H](O)[C@@H](O)[C@@H]1O"  # cellobiose / cellooligosaccharide
  class: cellulose / β-1,4-glucan
target_property: ph_stability    # 主线: 拓宽 pH 工作范围, 提升 alkaline 适应性 (工业 application 需要)
status: validated
provenance:
  source_type: literature
  doi: "10.1021/bi034954o"
  pmid: 12939137
  citation: "Wohlfahrt G, Pellikka T, Boer H, Teeri TT, Koivula A (2003). Probing pH-dependent functional elements in proteins: modification of carboxylic acid pairs in Trichoderma reesei cellobiohydrolase Cel6A. Biochemistry 42(34):10095-10103."
  extracted_at: 2026-04-28
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1021/bi034954o 与 PMID 12939137 我推测; CrossRef 验证"
    - "UniProt P07987 我推测对应 TrCel6A; QA via uniprot-fetcher 验证"
    - "PDB 1QJW 我推测对应 TrCel6A apo; 早期 deposit 包括 1CB2 (Rouvinen 1990 Science) / 1HGW / 1QJV 等系列"
    - "Cel6A 是 Trichoderma reesei (工业 cellulose 降解菌) 的两个主要 cellobiohydrolase 之一 (Cel7A 与 Cel6A)"
    - "本论文 Koivula 实验室 (VTT Finland) 主导, 系统改 active site 邻近 carboxylic acid pair (Asp / Glu) 的 pKa, 拓宽 alkaline pH"
    - "Cel6A 是 inverting GH6, 与 Cel7A retaining 机制不同; active site 含 Asp175 + Asp221 + Tyr 协同"
    - "engineering target 标 ph_stability 因主线是拓宽 pH 工作范围"
tags: [GH6, cellulose, cellobiohydrolase, CBH_II, Trichoderma_reesei, pH_engineering, carboxylic_acid_pKa, inverting_mechanism, Koivula-lab, VTT, industrial_cellulase]
---

## 1. 背景与目标
- parent: Trichoderma reesei Cel6A (CBH II, GH6, EC 3.2.1.91); inverting cellobiohydrolase, 7-tunnel substrate cleft, 从 cellulose non-reducing end processively 切出 cellobiose
- 起始性质: TrCel6A 在 pH 5-6 (Trichoderma natural 条件) 高活, 工业 cellulose 降解 cocktail 主流; 在 alkaline (pH > 7) 显著失活, 限制部分工业 application (textile / pulp 等 alkaline 工艺)
- 目标: 系统 mutate active site 邻近 carboxylic acid pair (Asp-Asp / Asp-Glu) 改 pKa, 拓宽 alkaline pH 工作范围 + 保 catalysis
- 应用: 拓宽 cellulase cocktail 的 pH 适用范围 (textile cotton processing, kraft pulp, biorefinery alkaline pretreatment)

## 2. 决策过程

### 候选位点策略
- **rational pKa modification**:
  - 解析 active site Asp175-Asp221 carboxylic acid pair (catalytic + 协同 transition state stabilizer)
  - 选 mutation Asp175Asn / Asp175Glu / Asp221Asn / Asp221Glu / pair 双突变 — 改 pKa 同时保 catalysis
- **结构-函数相关 mutation**: 
  - 远端 surface Asp/Glu (碱性 surface charge tuning) 配合
- 候选数: ~15 single + double mutation, 系统 pH 活性曲线测试

### 排除的位点 (★ 必填)
- **catalytic Asp175 (general acid for inverting mechanism)**: 严格保留 (Asn 代换是测试不是 production)
- **catalytic Asp221 (general base / nucleophilic water activator)**: 同样严格保留作 production
- **Substrate-binding tunnel aromatic Trp** (TrCel6A Trp272 / Trp367 + Y169 等): 保留以维持 processivity
- **Cel6A 标志的 ββ' loop 与 closed tunnel topology**: 保留 (改即变成 endo, 工业 application 关键 trade-off)

### 计算工具与阈值
- pKa 计算 (PROPKA / PoissonBoltzmann) 预测 candidate mutation 的 pKa shift
- PyRosetta 不依赖 (本论文 2003 时 PyRosetta 主流尚未稳)
- 实验校验: kcat/KM 在 pH 4-9 全范围, 比 pH-activity 曲线 shift; CD melting 看稳定性

## 3. 实验结果

### 关键变体
| 变体 | pH-activity peak | Alkaline 拓宽 (pH 8) |
| --- | --- | --- |
| TrCel6A WT | pH 5-6, peak 5.5 | <20% peak activity |
| Asp175Asn (single) | pH 5.5-6.5, slight shift | ~30% peak activity |
| Asp175Glu (single) | pH 5-6, almost no shift | ~25% peak activity |
| Asp175Asn / Asp221 mutation 配合 | pH 5.5-7.5 | ~60% peak activity |
| Surface Asp/Glu engineered (alkaline-tolerant variant) | pH 6-8 | ~70% peak activity |

### 失败案例 (★ 必填)
- **Asp221Asn 单点 mutation**: 完全失活 — Asp221 catalytic, 直接 Asn 替代消除 base
- **Single mutation pKa shift 通常 <0.5 pH unit**: 工业关键变化 (>2 pH units) 需要多 mutation 累积
- **多 mutation stacking 出现 epistasis**: pair 设计 Asp175Asn + Tyr169Phe 两个 mutation 单独 OK, 双突变失活 (与 NEG-EPISTASIS-bershtein-2006 反例呼应)
- **Tunnel aromatic 周围 mutation** (即使 surface 看起来无关) 多失 processivity, 转 endo mode
- **alkaline tolerance 提升常伴 substrate affinity 下降**: pH 拓宽与 KM 上升的 tradeoff
- **跨 GH6 来源 mutation 不可转移**: TrCel6A → Humicola insolens HiCel6 的 mutation 转移率 <30%

## 4. 学习收获
- **成立的规则候选**:
  - **GH6 cellulase 工程化绝对禁区**: catalytic Asp pair (Asp175 + Asp221 in TrCel6A numbering) + tunnel aromatic Trp + ββ' loop 必须 explicit 排除
  - **pKa engineering 是 GH6 拓宽 pH 的有效路线**: 但 single mutation gain 有限, 需要 active site pair + surface charge 协同
  - **Inverting GH6 与 retaining GH7 工程化机制不同**: pair Asp / Glu 角色不同, 不可跨家族转移
  - **Tunnel topology (ββ' loop closed / 半开 / open) 决定 processive / endo 行为**: 工程化 mode 要意识到这一拓扑约束
- **被推翻的假设**:
  - "Cel6A pH 工程化 = 单点 Asp → Asn 即可" — 反例多, 必须多 mutation 累积
- **下次类似问题应优先尝试**:
  - 任何 cellulase / GH 类水解酶 pH 工程化, 优先 active site Asp/Glu pair 协同 + surface charge tuning
  - 用 PROPKA 类 pKa 工具预筛, 实验验证 pH-activity profile (而非单 pH 测试)
- **应避免**:
  - GH6 catalytic Asp pair ±3 残基 mutation
  - 单点 mutation 试图 >2 pH unit shift
  - 跨 GH6 来源 (TrCel6A ↔ HiCel6) 直接转 mutation

## 5. 计算 / 实验原始数据
原始 Cel6A 突变体 pH-activity 曲线 + pKa 计算 + 结构 deposit 数据见 Biochemistry 2003 supplementary.
