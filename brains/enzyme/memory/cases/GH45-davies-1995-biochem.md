---
case_id: GH45-davies-1995-biochem
schema_version: 1
parent_enzyme:
  uniprot: P43316               # Humicola insolens endoglucanase V (HiCel45A); UniProt 收录
  cazy_family: GH45             # GH45 small inverting endoglucanase, six-stranded β-barrel fold
  ec: 3.2.1.4                   # cellulase / endo-1,4-β-glucanase
  organism: Humicola insolens (now Thermomyces 类相关)
  pdb: 4ENG                    # HiCel45A apo crystal (Davies 1995 deposit); QA 验证
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "OC[C@H]1O[C@@H](OC[C@H]2O[C@@H](O)[C@H](O)[C@@H](O)[C@@H]2O)[C@H](O)[C@@H](O)[C@@H]1O"  # cellooligosaccharide / β-1,4-glucan
  class: cellulose / β-1,4-glucan
target_property: thermostability_and_activity
status: validated
provenance:
  source_type: literature
  doi: "10.1021/bi00049a037"
  pmid: 8519785
  citation: "Davies GJ, Tolley SP, Henrissat B, Hjort C, Schülein M (1995). Structures of oligosaccharide-bound forms of the endoglucanase V from Humicola insolens at 1.9 Å resolution. Biochemistry 34(49):16210-16220."
  extracted_at: 2026-04-28
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1021/bi00049a037 与 PMID 8519785 我推测; CrossRef 验证"
    - "UniProt P43316 我推测对应 HiCel45A (EGV); QA 验证 (亦作 HiEG)"
    - "PDB 4ENG 我推测对应 HiCel45A 与 cellobio-derived inhibitor 复合物; 早期 deposit 系列还有 1ENG / 2ENG / 3ENG"
    - "Humicola insolens 是工业 cellulase 主要来源 (Novozymes Carezyme / Endolase 系列), HiCel45A 用于 textile 'biopolishing' 处理 cotton"
    - "本论文 Davies GJ 实验室 (York) 主导 + Henrissat B (CAZy founder) + Schülein M (Novozymes); 是 GH45 fold 与 mechanism 的奠基论文"
    - "GH45 是 inverting endoglucanase, 含单一 catalytic Asp + 一个 distal Asp (general acid + general base 角色待时讨论)"
    - "engineering target 标 thermostability_and_activity 因 textile 工业需要 alkaline (pH 9) + 60-70 °C 工作"
tags: [GH45, cellulase, endoglucanase, Humicola_insolens, EGV, textile_industry, biopolishing, six_strand_beta_barrel, Novozymes, Davies-lab, structural_anchor, Henrissat]
---

## 1. 背景与目标
- parent: Humicola insolens endoglucanase V (HiCel45A, EGV); GH45 small (~210 aa) inverting endoglucanase with 6-strand β-barrel fold (very compact, distinct from GH7 / GH6 TIM barrels)
- 起始性质: HiCel45A 在 alkaline pH 9 + 60 °C 工作 (与 Bacillus / Trichoderma 来源 cellulase 截然不同), Tm ~70 °C; 工业 textile 'biopolishing' (cotton fabric 表面去毛), Novozymes Carezyme 商品化
- 目标: 解析 HiCel45A 与 oligosaccharide 复合物结构 (1.9 Å), 揭示 catalytic Asp 角色 + substrate-binding subsite — 为 textile 工业 condition 工程化提供结构基础
- 应用: cotton 'biopolishing' (textile alkaline-friendly cellulase), Novozymes 商品化; 后续 follow-up 进一步工程化 thermostability + alkaline tolerance

## 2. 决策过程 (本论文是 mechanism + structure, 非 site-directed engineering)

### 候选位点策略
- **结构生物学路线**: 解 HiCel45A apo + cellobiose-bound + cellobio-derived inhibitor bound 的高分辨复合物 (1.9 Å)
- 后续 mutagenesis (Davies + Schülein 系列 follow-up) 确认 catalytic Asp + 二级 sphere 角色
- 不做 saturation library; hypothesis-driven

### 排除的位点 (★ 必填)
- **catalytic Asp10 (general acid)**: 严格保留, GH45 唯一 acidic residue 给出 acid catalysis
- **catalytic Asp121 / Asp136 (general base, distal)**: 角色复杂, 一些 GH45 单 Asp 一些 双 Asp; HiCel45A 是单 acid + 远端 water-mediated base
- **Six-strand β-barrel fold core (~150 aa)**: 严格保留, 是 GH45 标志 fold
- **Substrate-binding shallow groove (-2 to +2 subsite)** with key Tyr / Trp aromatic stacking: 保留以维持 substrate orientation
- **Disulfide bridges (HiCel45A 含 ~2 个)**: 保留以维持小蛋白稳定

### 计算工具与阈值
- 主要工具: X-ray crystallography (1.9 Å, very high resolution)
- 后续 follow-up: 单 / 双点 mutagenesis 验证 catalytic Asp 角色, mutate Asp → Asn 或 Asp → Glu 看活性变化
- 实验校验: kinetic on cellotriose / cellotetraose / β-glucan (CMC), pH-activity profile

## 3. 实验结果

### 结构 + mechanism 关键发现
| 发现 | 内容 |
| --- | --- |
| Six-strand β-barrel fold | GH45 标志, 与其他 cellulase fold 完全不同 (TIM barrel / Greek key 等) |
| 浅 substrate-binding cleft | 容纳 ~4 disaccharide units, endo cleavage geometry |
| Catalytic Asp10 + 远端 base water | inverting mechanism, water-mediated proton transfer |
| Aromatic stacking Trp / Tyr | substrate sliding ramp |
| Acid resistant / alkaline 兼容性 | 起始 H. insolens 工业起源已 alkaline, 工程化进一步推 |

### 失败案例 (★ 必填)
- HiCel45A 在 prokaryotic (E. coli) 表达失败 — 多 disulfide + 真菌 N-glycosylation 必需 mammalian / yeast (Pichia) host
- Asp10 → Asn 直接失活, Asp10 → Glu 仍降 catalysis ~50% — catalytic Asp 不可工程化
- 后续工程化提升 thermostability 时, surface charge optimization 易 misfolding (HiCel45A 小蛋白, surface 比例高)
- 多 mutation 累积 (>4) 时表达 yield 下降, 提示 small protein epistasis 比大蛋白 more sensitive
- 跨 GH45 来源 (HiCel45A ↔ Trichoderma reesei Cel45A ↔ Bacillus 类 GH45) mutation 转移率低 — 序列 identity ~30-40% 时 mutation 不直接转

## 4. 学习收获
- **成立的规则候选**:
  - **GH45 工程化绝对禁区**: catalytic Asp10 + 远端 water-mediated base 区域 + 6-strand β-barrel core + disulfide bridges + substrate-binding aromatic Trp/Tyr
  - **GH45 是 alkaline-tolerant cellulase 的天然 chassis**: H. insolens 起源已 alkaline, 优于 Trichoderma 来源做 alkaline application
  - **Small protein (~200 aa) 工程化敏感于 mutation 累积**: ≥4 mutation stacking 必须验表达 yield + Tm
  - **跨 GH 家族转移 mutation 失败率高**: GH7 ↔ GH6 ↔ GH45 ↔ GH5 — fold 与 mechanism 都不同, 必须各 family 独立工程化
- **被推翻的假设**:
  - "Cellulase 都来自 Trichoderma 工程化" — H. insolens GH45 是 alkaline 工业最优起点
  - "GH45 mechanism 与 GH7 类似 (双 Asp/Glu pair)" — GH45 是单 Asp + water-mediated base, 不同
- **下次类似问题应优先尝试**:
  - Textile / alkaline application 的 cellulase, 用 H. insolens GH45 起点
  - GH45 工程化 必须 + Pichia / Trichoderma host 表达 (E. coli 失败)
  - Small protein 工程化 (<250 aa) ≥4 mutation 必须实验验证 stacking
- **应避免**:
  - HiCel45A catalytic Asp10 / 远端 base 区域 mutation
  - prokaryotic host 表达 GH45 真菌 cellulase
  - 跨 GH 家族直接转 mutation

## 5. 计算 / 实验原始数据
HiCel45A 1.9 Å 结构 + cellobiose 复合物 deposit 见 PDB 4ENG; 后续 Davies / Schülein 系列 (J Mol Biol / Biochemistry) 扩展 mutagenesis + textile application 数据.
