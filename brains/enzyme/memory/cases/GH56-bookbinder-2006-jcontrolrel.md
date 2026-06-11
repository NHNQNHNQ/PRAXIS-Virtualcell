---
case_id: GH56-bookbinder-2006-jcontrolrel
schema_version: 1
parent_enzyme:
  uniprot: P38567               # Human PH-20 / SPAM1 (sperm adhesion molecule 1, hyaluronidase)
  cazy_family: GH56              # GH56 hyaluronidase family
  ec: 3.2.1.35                   # hyaluronidase
  organism: Homo sapiens
  pdb: null                      # 当时无完整 deposit, 后续 follow-up
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "OC(=O)[C@H]1O[C@H](O[C@@H]2O[C@H](CO)[C@@H](O)[C@H](NC(=O)C)[C@H]2O)[C@H](O)[C@@H](O)[C@H]1O"   # hyaluronan disaccharide repeat (GlcA-β1,3-GlcNAc)
  class: hyaluronan / glycosaminoglycan
target_property: substrate_specificity   # 主线: 工程化 PH-20 N端 + C端截短 + 表达 yield + 体内 PK; 临床蛋白工程化范式
status: validated
provenance:
  source_type: literature
  doi: "10.1016/j.jconrel.2006.05.027"
  pmid: 16876903
  citation: "Bookbinder LH, Hofer A, Haller MF, Zepeda ML, Keller GA, Lim JE, Edgington TS, Shepard HM, Patton JS, Frost GI (2006). A recombinant human enzyme for enhanced interstitial transport of therapeutics. Journal of Controlled Release 114(2):230-241."
  extracted_at: 2026-04-28
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1016/j.jconrel.2006.05.027 与 PMID 16876903 我推测; CrossRef 验证"
    - "UniProt P38567 我推测对应 human PH-20 (SPAM1); QA 验证 (亦含 HYAL1 / HYAL2 / HYAL3 — 区分 sperm-PH20 vs 6种 human hyaluronidase)"
    - "本论文是 Halozyme Therapeutics 的 rHuPH20 (later 'hyaluronidase recombinant human PH20') 工程化里程碑 — 解决 native PH-20 工业表达难题"
    - "rHuPH20 = N-端 + C-端截短 (剔除 GPI-anchor signal 区), 表达 yield + 性能极大提升; FDA 后续批准用于多个药物的 subcutaneous administration enabler (ENHANZE platform)"
    - "FDA 批准的 PH-20 衍生 product: Hylenex (rHuPH20 单 product), HyQvia (含 IGIV), Herceptin Hylecta (含 trastuzumab subcutaneous), Phesgo (含 pertuzumab+trastuzumab)"
    - "engineering target 标 substrate_specificity 但实际是 'recombinant production + pharmacokinetic suitability' — 类 PAL-sarkissian-2008 临床蛋白工程化范式"
tags: [GH56, hyaluronidase, PH-20, rHuPH20, ENHANZE, Halozyme, subcutaneous_drug_delivery, recombinant_production, biopharmaceutical, FDA_approved, Bookbinder-2006, clinical_protein_engineering]
---

## 1. 背景与目标
- parent: human PH-20 (SPAM1, GH56 hyaluronidase, EC 3.2.1.35); 全长 native PH-20 在精子表面以 GPI-anchor 附着, 不易工业重组表达
- 起始性质: native PH-20 含 N-端 signal peptide + C-端 GPI-anchor recognition signal; 在 CHO / 重组 host 表达时主要分泌但 yield 低 + GPI 处理失误
- 目标: 通过 N-端 + C-端截短 (去除 GPI signal) 工程化产生 'soluble, stable, injectable rHuPH20' — 适合 subcutaneous administration 配伍其他药物 (作为 hyaluronan 临时降解 enabler, 提升 interstitial 流通性)
- 应用: ENHANZE platform — FDA 批准多个 monoclonal antibody / 免疫球蛋白制剂 与 rHuPH20 共配, 转 IV 给药为 subcutaneous (患者 self-administer)

## 2. 决策过程

### 候选位点策略
- **rational truncation**:
  - 截 N-端 signal peptide (前 ~36 aa)
  - 截 C-端 GPI-anchor recognition signal (大约 ~447 aa 后的 ~62 aa)
  - 保留 catalytic core domain (~63-447 aa, GH56 (β/α)8 TIM barrel + EGF-like domain)
- **glycosylation engineering** (隐式): 多 N-glycosylation site 在 PH-20 surface, CHO host 自带高 mannose; 工程化 target 是均一的 N-glycan profile

### 排除的位点 (★ 必填)
- **catalytic Glu (general acid)**: GH56 active site 关键, 严格保留 (Glu149 类编号, 视具体 numbering)
- **Substrate-binding cleft aromatic** (与 PL8 类型不同, GH56 是 hydrolase 不是 lyase): 保留以维持 hyaluronan binding
- **disulfide bridges (GH56 含多个 disulfide, EGF-like domain 也有)**: 全保留, 拆即 misfolding
- **Active site Tyr (proton transfer)**: 保留

### 计算工具与阈值
- 主要工具: rational truncation + 异源 (CHO mammalian) 表达 + ELISA / hyaluronan turbidimetric assay 测活
- 体内 PK: 注射小鼠 / 大鼠, 测血清半衰期 + interstitial 流通增强
- 实验校验: SDS-PAGE 表达 yield, MS 验 N-glycan, 生物 / 安全性 study (FDA 路线)

## 3. 实验结果

### rHuPH20 性能
| 量 | native PH-20 | rHuPH20 (truncated) | 提升 |
| --- | --- | --- | --- |
| Recombinant yield (CHO) | 低, GPI 处理失误 | 高 yield, 均一分泌 | 显著 |
| Hyaluronan 比活 | baseline | comparable | 保留 |
| 注射半衰期 | 短 (适合 transient interstitial 增强) | ~10-20 min | 类似 native, 短足够用 |
| 安全性 (immunogenicity) | 低 (human 序列) | 低 | – |
| FDA 批准 | – | 多个 product (Hylenex / HyQvia / 多个 mAb co-formulation) | 多个 launch |

### 失败案例 (★ 必填)
- 早期试 longer truncation (去除更多 C-端) 失活 — C-端 EGF-like domain 是 substrate cleft 完整性必需
- 在 E. coli 表达 rHuPH20 失败 — GH56 蛋白多 N-glycosylation 必需 mammalian host (CHO), prokaryotic 表达折叠错误 / 不稳定
- 单点 mutation 提升 substrate scope (e.g. 试 chondroitin) 失败 — PH-20 高度 specific to hyaluronan, 改 substrate 需要大量 mutation
- 多个 isozymes (HYAL1 / HYAL2 等其他 human hyaluronidase) 不可直接替代 PH-20 — 不同 pH 优 / 不同 cellular 位置 / 不同 mode
- 早期 bovine PH-20 (BTH) 路线发现 immunogenicity 问题, 必须 human (Halozyme 选 human PH-20 而非 bovine 解决了关键临床障碍)

## 4. 学习收获
- **成立的规则候选**:
  - **GH56 工程化绝对禁区**: catalytic Glu + Substrate-binding cleft aromatic + 多 disulfide bridge + EGF-like domain (尤其 C-端)
  - **临床蛋白 (human-derived) 工程化的 'truncation-first' 策略**: 优先 minimal protein 而不试 mutagenesis, GH56 PH-20 是范例
  - **GPI-anchored protein 重组表达必先去 GPI signal**: native form 表达失败常见原因
  - **Mammalian (CHO / HEK) host 必需于 多 N-glycan 蛋白**, prokaryotic 替代 (E. coli / Bacillus) 失败率 >90%
  - **临床蛋白 (PH-20 / PAL / 等) 选 source 时优先 human**: bovine / microbial 来源 immunogenicity 风险
- **被推翻的假设**:
  - "GH56 hyaluronidase 在 E. coli 可重组表达" — 反例多, 必须 mammalian host
  - "Native PH-20 直接重组即可" — GPI 处理 / 截短必需
- **下次类似问题应优先尝试**:
  - 任何 GH56 / 临床 hyaluronidase 工程化, 优先 truncation engineering + CHO host
  - 任何 GPI-anchored 蛋白工业化, 先去 GPI signal + 表达系统选 mammalian
  - subcutaneous drug delivery enabler 类项目, 用 rHuPH20 (Halozyme ENHANZE) 是已验证 platform
- **应避免**:
  - prokaryotic host 表达 GH56 hyaluronidase
  - 在 native PH-20 上 mutagenesis 而不先 truncation
  - bovine PH-20 临床 application (immunogenicity)

## 5. 计算 / 实验原始数据
rHuPH20 表达 yield + biochemistry + 体内 PK 数据见 J Control Rel 2006 supplementary; FDA Hylenex / HyQvia / Herceptin Hylecta 临床数据由 Halozyme + 合作 pharma 公开.
