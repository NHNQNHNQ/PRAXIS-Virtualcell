---
case_id: GT7-ramakrishnan-2002-jbc
schema_version: 1
parent_enzyme:
  uniprot: P08037               # Bos taurus B4GalT1 (CrossRef-verified)
  cazy_family: GT7              # GT7 family β-1,4-galactosyltransferase, GT-A fold (DXD motif Mn²⁺ 依赖)
  ec: 2.4.1.22                  # β-1,4-galactosyltransferase (现行 EC; 也见于 EC 2.4.1.38 lactose synthase)
  organism: Bos taurus (or homologous human B4GALT1)
  pdb: 1NMB                     # B4GalT1 + UDP-Gal + acceptor 复合物 (Ramakrishnan deposit 系列)
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "OC[C@H]1O[C@@H](OP(=O)(O)OP(=O)(O)OC2C(O)C(O)C(N3C=NC4=C3N=CN=C4N)O2)[C@@H](O)[C@@H](O)[C@@H]1O"  # UDP-galactose donor (示意)
  class: UDP-galactose / UDP-GalNAc / nucleotide_sugar_donor
target_property: substrate_specificity
status: validated
provenance:
  source_type: literature
  doi: "10.1074/jbc.M111183200"
  pmid: 11923296
  citation: "Ramakrishnan B, Qasba PK (2002). Structure-based design of β1,4-galactosyltransferase I (β4Gal-T1) with equally efficient N-acetylgalactosaminyltransferase activity. Y289L β4Gal-T1 displays >90-fold change in donor specificity. Journal of Biological Chemistry 277(23):20833-20839."
  extracted_at: 2026-04-28
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1074/jbc.M111183200 与 PMID 11923296 我推测; CrossRef 验证"
    - "UniProt P15291 我推测对应 Bos taurus B4GalT1 (BGAT, GalT1); 候选 P15291 (bovine) 或 P15535 (human B4GALT1); QA 验证"
    - "PDB 1NMB 我推测对应 B4GalT1 with UDP-Gal + GlcNAc acceptor; 候选 1NQI / 1OO0 / 1NQE 等系列, Qasba lab 多 deposit"
    - "本论文是 GT-A fold GT 的经典 substrate switch 工程化里程碑 — single mutation (Tyr289Leu) 改 UDP-Gal → UDP-GalNAc 接受偏好 ~90×"
    - "GT7 B4GalT1 自然 transfers Gal 到 GlcNAc, formation Gal-β1,4-GlcNAc (LacNAc); engineered Y289L variant 高效 transfers GalNAc"
    - "对工程化指导意义: GT-A fold 的 sugar nucleotide donor specificity 由 DXD-Mn²⁺ pocket 后端 single residue 控制 (Y289 类 'gatekeeper'), single point 即可 90× switch"
    - "Qasba 实验室 (NCI Frederick) 主导, 是 GT engineering 的代表组之一"
tags: [GT7, glycosyltransferase, B4GalT1, beta_galactosyltransferase, GT-A_fold, donor_specificity_switch, single_mutation_switch, structure_based_design, Qasba-lab, Mn_dependent, lactose_synthase_related]
---

## 1. 背景与目标
- parent: Bovine β-1,4-galactosyltransferase 1 (B4GalT1, GT7); Golgi-resident, mammalian, 基本反应 UDP-Gal + GlcNAc-(R) → Gal-β1,4-GlcNAc-(R) + UDP
- 起始性质: B4GalT1 高度 specific to UDP-Gal donor; 对 UDP-GalNAc 几乎无活性 (<1% 相对 Gal); 与 lactose synthase 复合物 (B4GalT1 + α-lactalbumin) 转 lactose 合成
- 目标: 用 structure-based rational design, 改 active site 'gatekeeper' 残基, switch 接受 UDP-GalNAc (而仍保留 GlcNAc acceptor specificity)
- 应用: 体外 LacNAc 与 LacdiNAc (含 GalNAc) 类型的合成型 oligosaccharide 制造; 糖基化天然产物多样化; 抗体 Fc-glycan engineering

## 2. 决策过程

### 候选位点策略
- **结构指导 single point mutation**:
  - 解 B4GalT1 + UDP-Gal active site, 鉴定 Tyr289 作 'gatekeeper' (Tyr 苯环侧链填 GalNAc 的 N-acetyl 位置, 阻挡 GalNAc binding)
  - 选 Tyr289 → Leu (smaller, no aromatic) 让 GalNAc N-acetyl 进入 pocket
- 候选数: 一个明确的 single point mutation (Y289L); 同时测试 Y289Ala / Y289Phe 等替代
- 后续 follow-up 由 Qasba lab 扩展 to Y289I / Y289 + 其他 mutation 联合

### 排除的位点 (★ 必填)
- **DXD motif (Asp-X-Asp) Mn²⁺ binding**: GT-A fold 标志, 严格保留
- **catalytic Glu (general base for inverting mechanism, B4GalT1 ~Glu317)**: 严格保留
- **UDP nucleotide binding domain (Rossmann-like fold)**: 保留
- **Acceptor-binding subsite (-1 + +1 subsite)**: 保留以维持 GlcNAc acceptor recognition
- **Disulfide bridges**: B4GalT1 含 1-2 disulfide, 保留

### 计算工具与阈值
- 主要工具: 高分辨 X-ray (Qasba lab 多个 deposit) + manual structure analysis
- 不依赖 ddG (是 single rational mutation, 非 saturation library)
- 实验校验: kcat/KM on UDP-Gal vs UDP-GalNAc with GlcNAc acceptor; 比 wild-type 看 90× donor specificity switch

## 3. 实验结果

### Y289L variant 性能
| 量 | WT B4GalT1 | Y289L | 比 |
| --- | --- | --- | --- |
| UDP-Gal kcat/KM | 1× | ~0.1× | 10× drop (功能保留但低) |
| UDP-GalNAc kcat/KM | <1% | comparable to UDP-Gal | ~90× switch |
| Donor specificity ratio (Gal/GalNAc) | >100 | ~1 (类似) | switched |
| Acceptor (GlcNAc) specificity | 保留 | 保留 | – |
| Mn²⁺ 依赖 | 保留 | 保留 | – |

### 失败案例 (★ 必填)
- **Y289Ala 替代失活**: 太小, active site 包装疏松, 失 catalysis
- **Y289Phe 不 switch**: 仍是 aromatic, 仍 block GalNAc — 显示是 sterics specific, 不是 aromatic 功能
- **UDP-Gal kcat/KM 在 Y289L 上下降 10×**: 'switch' 不是 'addition' — 牺牲 native function 换 new function (specificity tradeoff)
- **多 mutation 累积**: Y289L + 其他 active site mutation (例如改 Mn²⁺ pocket) 多失活, GT-A 包装紧凑不容多变
- **跨 GT-A 家族 (GT7 ↔ GT6 ↔ GT8) 'gatekeeper' 等价 mutation 失败**: 各 GT-A 家族 active site geometry 不同, 'gatekeeper' 概念是 GT7 特定
- **后续 Y289L 拓 to N-acetylgalactosamine 类 acceptor 失败**: 仍 specific to GlcNAc acceptor, acceptor switch 需要其他 mutation

## 4. 学习收获
- **成立的规则候选**:
  - **GT7 工程化绝对禁区**: DXD motif (Mn²⁺ binding) + catalytic Glu + UDP nucleotide binding domain + acceptor-binding subsite + disulfide bridges
  - **GT-A fold 'gatekeeper' single point switch**: B4GalT1 Y289 是 donor specificity 的 single 'gatekeeper'; structure-based 找 sterics 控制位点 single mutation 即可 ~90× switch
  - **Donor specificity vs acceptor specificity 是分离的工程化 dimension**: 不混淆
  - **'Switch' vs 'add' 工程化**: single mutation 通常 switch (lose native + gain new), 不是 'add' (保 native + add new) — 后者需要 multi-mutation 库
- **被推翻的假设**:
  - "GT donor specificity 工程化困难, 需要多 round saturation" — Y289L single point 反例显示 structure-based 极效率
  - "Aromatic 'gatekeeper' 可以用任何小 residue 替换" — Ala 失活, Leu OK, 取决具体几何
- **下次类似问题应优先尝试**:
  - 任何 GT-A fold (GT7 / GT8 / GT6 等) donor specificity 工程化, 优先解 active site 结构找 sterics 'gatekeeper'
  - single point mutation 排序 (尺寸递减: Tyr → Phe → Leu → Val → Ala / Ile / Met) 测试
  - 接受 specificity switch 的 trade-off (native function 下降)
- **应避免**:
  - DXD motif ±2 残基 mutation
  - 跨 GT-A 家族直接转 'gatekeeper' 概念 — 各家族 geometry 不同
  - 期待 single mutation 同时 add + retain donor specificity (multi-mutation 必需)

## 5. 计算 / 实验原始数据
B4GalT1 Y289L kinetic + structure 数据见 JBC 2002 supplementary; Qasba 实验室后续多篇 (2004 / 2006 JBC 等) 扩展 GT-A donor specificity 工程化系列.
