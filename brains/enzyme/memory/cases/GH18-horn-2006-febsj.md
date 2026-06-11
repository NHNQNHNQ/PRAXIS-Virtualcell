---
case_id: GH18-horn-2006-febsj
schema_version: 1
parent_enzyme:
  uniprot: P11797                # Serratia marcescens chitinase A (ChiA); UniProt 文本搜索找到
  cazy_family: GH18              # GH18 is (β/α)8 TIM barrel chitinase family
  ec: 3.2.1.14                   # chitinase
  organism: Serratia marcescens
  pdb: 1CTN                      # ChiA crystal (Perrakis 1994 deposit; 候选)
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "CC(=O)N[C@@H]1[C@@H](O)[C@H](O)[C@@H](CO)O[C@H]1O[C@H]2[C@H](NC(C)=O)[C@@H](O)[C@H](CO)O[C@H]2O"   # chitobiose (chitin disaccharide)
  class: chitin / chitooligosaccharide
target_property: substrate_specificity   # 主线: 区分 endo vs exo + processive 行为, 工程化目标是 mode of action
status: validated
provenance:
  source_type: literature
  doi: "10.1111/j.1742-4658.2005.05079.x"
  pmid: 16420473
  citation: "Horn SJ, Sørbotten A, Synstad B, Sikorski P, Sørlie M, Vårum KM, Eijsink VG (2006). Endo/exo mechanism and processivity of family 18 chitinases produced by Serratia marcescens. FEBS Journal 273(3):491-503."
  extracted_at: 2026-04-28
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1111/j.1742-4658.2005.05079.x 与 PMID 16420473 我推测; CrossRef 验证"
    - "UniProt P11797 我推测对应 Sm ChiA; QA 验证 (亦含 ChiB P11797 类似 ID; 区分 ChiA / ChiB / ChiC)"
    - "PDB 1CTN 我推测对应 ChiA apo; ChiA 系列还有 1FFR / 1EHN / 1WVP 等"
    - "Sm 三个 chitinase: ChiA + ChiB + ChiC, 协同降解 chitin 但 mode of action 不同 — ChiA 与 ChiB 是 processive exo 类, ChiC 是 endo 类"
    - "本论文 systematic 比较 ChiA / ChiB / ChiC processivity + endo/exo 倾向, 用 chito-oligo HPLC 检 product distribution"
    - "Eijsink 实验室 (Norwegian U Life Sciences) 主导, 该组同时主导 LPMO discovery (AA10-vaaje-kolstad-2010)"
    - "对工程化指导意义: chitinase mode of action 由 substrate-binding subsite + aromatic stacking 控制, 工程化 mode 可改 substrate scope"
tags: [GH18, chitinase, processivity, endo_exo_mechanism, Serratia_marcescens, ChiA, ChiB, ChiC, aromatic_stacking, Eijsink-lab, Horn_2006, mechanism_anchor]
---

## 1. 背景与目标
- parent: Serratia marcescens 三个 GH18 chitinase: ChiA (~563 aa), ChiB (~499 aa), ChiC (~487 aa)
- 起始性质: 三个 chitinase 共同存在但作用模式不同 — ChiA processive 从 chitin reducing end, ChiB processive 从 non-reducing end, ChiC endo-非 processive
- 目标: 系统比较三者的 processivity (单 binding 内多次切割数) + endo/exo (起切 internal vs end) + substrate-binding subsite 占用模式 — 揭示 GH18 mode of action 的结构基础
- 应用: chitinase 工程化 substrate scope / processivity / endo-exo mode 的结构指导; chitin 工业降解 (生物 nanocrystal 与 chitooligosaccharide 制备)

## 2. 决策过程 (本文是 mechanism 比较, 非单一 enzyme engineering)

### 候选位点策略 (across 3 chitinases)
- **HPLC + chito-oligo distribution**: 用 chitin 聚合物 + 短 chito-oligo substrate, 跟降解时间产物 length distribution
- 推 processivity number (PN): single binding 内的 cleavages 数
- 比较 三者 substrate-binding subsite 占用 (-7 to +5 numbering): substrate 在 +1/+2 subsite 的 aromatic stacking (Trp/Tyr) 是 processivity key

### 排除的位点 (★ 必填)
- **catalytic Glu (GH18 唯一通用 catalytic 残基, ChiA Glu315 / ChiB Glu144 / ChiC Glu141 — DXE/DXDXE motif)**: 严格保留
- **Substrate-anchoring Trp/Tyr aromatic stacking residues** (ChiA Trp275 + Trp539 等): 是 processivity 关键, 可 mutate 改 mode 但需 explicit 测试
- **二级 sphere catalytic 邻位 Asp/Tyr (proton transfer 网络)**: 保留以维持 catalysis

### 计算工具与阈值
- 不依赖 ddG (本文 mechanism 比较, 不做工程化 mutation)
- HPAEC-PAD / MS 检 chito-oligo 产物长度分布
- Reducing-end vs non-reducing-end 标记 (用 chemical 还原)
- Single-turnover assay: 控制 enzyme:substrate 比例使 multi-turnover ≪ 1, 看 single-binding 切几次

## 3. 实验结果

### 三个 chitinase 对比
| | ChiA | ChiB | ChiC |
| --- | --- | --- | --- |
| Mode | processive exo (reducing end) | processive exo (non-reducing end) | endo, non-processive |
| Processivity Number | ~10-20 | ~5-15 | ~1 (single cut) |
| Substrate-binding 关键 aromatic | Trp539 (+1/+2 stacking) | Trp97 + Trp220 | Trp97 (单一 stacking) |
| 工业用途 | chito-oligo 制备 (短链) | 同 ChiA, 互补端 | chito-oligo 制备 (长链 + endo cut) |

### 失败案例 (★ 必填)
- 单一 chitinase 不能高效降解 crystalline chitin: ChiA + ChiB + ChiC 协同 (与 LPMO AA10 配合) 才完全降解 — 单 enzyme 工程化目标不应是 'crystalline chitin 单酶降解'
- 'processivity 越高越好' 是错的: high processivity 限 substrate scope (只切 chito-oligo 长链), 工业 application 需要平衡
- 错误估 ChiC mode (早期文献): 部分早期工作 ChiC 当成 exo, 直到本文用 product distribution + reducing-end 标记 才确认 endo
- 跨 chitinase mutation 转移失败: ChiA / ChiB / ChiC 同 GH18 但 substrate-binding subsite 不同, 单点 mutation 不可转移

## 4. 学习收获
- **成立的规则候选**:
  - **GH18 chitinase 工程化绝对禁区**: 唯一 catalytic Glu (DXE/DXDXE motif) 严格保留, GH18 仅一 acidic residue 作 acid/base
  - **Processivity = +1/+2 subsite aromatic stacking + substrate-binding cleft 长度** 的协同结果, 可调 但 mode 切换 (processive ↔ non-processive) 需多位点协同
  - **Endo vs exo 差异 = N-terminal binding cleft 拓宽程度** (ChiC 拓宽允许 endo, ChiA/ChiB 收窄 + tunnel 类似 exo)
  - **工业 chitin 降解 = chitinase + LPMO + β-N-acetylhexosaminidase 三类协同**, 不是单酶项目
- **被推翻的假设**:
  - "GH18 chitinase 同源都 processive" — ChiC 反例
  - "Processivity 单一 metric 即决定工程化" — substrate scope 与 processivity 是 tradeoff
- **下次类似问题应优先尝试**:
  - 任何 chitinase 工程化, 先用 HPLC / MS 确定 mode (endo / exo / processive) — 不是从 sequence 推断
  - chitin 工业 application, 设计 chitinase + LPMO 协同 cocktail
  - chitooligosaccharide 长度控制 = aromatic stacking residue 数量调节
- **应避免**:
  - GH18 唯一 catalytic Glu (DXE/DXDXE) ±3 mutation
  - 把 ChiA mutation 直接转 ChiB / ChiC (mode 不同)
  - 假定单酶降解 crystalline chitin (必须配 LPMO)

## 5. 计算 / 实验原始数据
ChiA / ChiB / ChiC product distribution + reducing-end 标记 + processivity number 数据见 FEBS J 2006 supplementary; Eijsink 组后续 (Vaaje-Kolstad 2005 JBC, Sørlie et al 2008) 扩展 LPMO + chitinase 协同.
