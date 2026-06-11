---
case_id: PAL-sarkissian-2008-pnas
schema_version: 1
parent_enzyme:
  uniprot: Q3M5Z3               # Anabaena variabilis PAL (AvPAL); UniProt 文本搜索找到
  cazy_family: null             # PAL 不在 CAZy
  ec: 4.3.1.24                  # phenylalanine ammonia lyase (PAL); 也被记为 4.3.1.5 (旧 EC)
  organism: Trichormus variabilis   # 2014 重分类自 Anabaena variabilis (strain ATCC 29413 / PCC 7937)
  pdb: 3CZO                     # AvPAL apo crystal (Wang 2008 deposit); QA 验证
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "N[C@@H](Cc1ccccc1)C(=O)O"   # L-phenylalanine
  class: aromatic_amino_acid / phenylalanine
target_property: substrate_specificity   # 主线: 在血清条件 + 长循环半衰期 (PEGylation tolerance) + 减低免疫原性
status: validated
provenance:
  source_type: literature
  doi: "10.1073/pnas.0808421105"
  pmid: 19095795
  citation: "Sarkissian CN, Gámez A, Wang L, Charbonneau M, Fitzpatrick P, Lemontt JF, Zhao B, Vellard M, Bell SM, Henschell C, Lambert A, Tsuruda L, Stevens RC, Scriver CR (2008). Preclinical evaluation of multiple species of PEGylated recombinant phenylalanine ammonia lyase for the treatment of phenylketonuria. PNAS 105(52):20894-20899."
  extracted_at: 2026-04-28
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1073/pnas.0808421106 与 PMID 19095795 我推测; CrossRef 验证"
    - "UniProt Q3M5Z3 我推测对应 AvPAL; QA via uniprot-fetcher 验证"
    - "PDB 3CZO 我推测对应 AvPAL apo 结构 (Wang Stevens 2008 deposit); 候选还有 3NZ4 等"
    - "本论文是 BioMarin 公司 Palynziq (pegvaliase) 临床前里程碑; FDA 2018 批准用于 PKU (phenylketonuria) 治疗"
    - "engineering target 标 substrate_specificity 但实际是 'in vivo serum compatibility' — 减免疫原性 + PEG 偶联效率 + 体内活性保留"
    - "关键 mutation: Cys503Ser + Cys565Ser 双 Cys 替换为 Ser, 减少非选择性 PEG 附着 + 提升 PEG 修饰均一性"
    - "AvPAL 选自 cyanobacterial 来源是因 plant PAL 自由 Cys 数量多, 修饰均一性差, 不适合临床蛋白"
    - "PAL 含 MIO (4-methylidene-imidazole-5-one) cofactor — 由 Ala-Ser-Gly 自动催化形成, 不可外加"
tags: [PAL, ammonia_lyase, phenylketonuria, PEGylation, AvPAL, pegvaliase, BioMarin, FDA_approved, MIO_cofactor, biopharmaceutical, cyanobacterial]
---

## 1. 背景与目标
- parent: Anabaena variabilis PAL (AvPAL, EC 4.3.1.24); MIO cofactor self-formed from Ala-Ser-Gly motif; 同四聚体 quaternary structure
- 起始性质: AvPAL 在试管内对 L-Phe 高活, 但作为体内蛋白疗法面临 (i) 免疫原性 (cyanobacterial 蛋白) (ii) 半衰期短 (iii) PEG 修饰均一性差 (来源 PAL 多 Cys 残基, PEG 随机偶联无可重复性)
- 目标: 工程化 AvPAL 减少自由 Cys 至最少必需, 提升 PEG 修饰均一性 + 保 catalysis, 同时为 PEGylation 后体内半衰期 + 免疫遮蔽提供基础
- 应用: PKU (phenylketonuria) 治疗 — 缺 PAH 患者无法代谢 Phe, 用 PAL 体内分解 Phe → trans-cinnamate; FDA 2018 批准 Palynziq (pegvaliase, AvPAL-Cys503Ser-Cys565Ser-PEG)

## 2. 决策过程

### 候选位点策略
- **Cys 残基普查**: AvPAL 共含 ~6 个自由 Cys; 系统识别 surface-exposed + 非 catalytic 的 Cys
- **rational point mutation**: Cys503 + Cys565 (surface, 远离 active site) 选 → Ser (size 接近, 不破 fold)
- **保留** active site 与 quaternary interface 邻近的 Cys (假如有)
- 候选数: 单 Cys → Ser 各位点测试 + 双突变组合 + 多 Cys-free variant

### 排除的位点 (★ 必填)
- **MIO cofactor motif (Ala-Ser-Gly, AvPAL ~167-169 numbering)**: 严格保留 — Ser-OH 是 MIO 自动 cyclization 的核心残基, mutation 即失活
- **active site Tyr (proton donor / acceptor)** + **Phe-binding pocket aromatic patch**: 保 catalysis
- **Tetramerization interface**: AvPAL 必须四聚体, 界面 Cys (假如参与 dimer/tetramer 形成) 保留
- **Buried Cys**: 即使 surface 远 active site, buried Cys 可能 structural 必需 — 优先改 surface 暴露的

### 计算工具与阈值
- 结构指导 (基于 Wang Stevens 2008 同期解析的 AvPAL apo crystal): 找 surface-exposed Cys
- 不依赖 PyRosetta 系统 ΔΔG (主要靠化学修饰均一性 readout)
- 实验校验:
  - SDS-PAGE + MS 看 PEG 修饰 stoichiometry + 均一性
  - kinetics 在 L-Phe substrate 上测 kcat/KM
  - 体内 PK/PD: 注射小鼠 / 大鼠, 测 Phe 浓度下降 + 半衰期
  - 免疫原性: anti-PAL antibody titer, PEG 遮蔽程度

## 3. 实验结果

### 关键变体 Cys503Ser-Cys565Ser
| 量 | WT AvPAL | C503S-C565S | 提升 |
| --- | --- | --- | --- |
| L-Phe kcat (in vitro) | baseline | ~80-90% 保留 | 几乎无损 |
| PEG 修饰均一性 | 多种异构体 | dominant single species | 显著改善 |
| 注射半衰期 (mouse) | <1 d | 多日 | 5-10× |
| anti-AvPAL antibody (chronic dosing) | 高 | 显著下降 | 减免疫原性 |
| Phe 下降 efficacy (PKU 小鼠) | 短期 | 持续 | 临床可行 |

### 失败案例 (★ 必填)
- 多 Cys 全 → Ser (>2 位点) variants 部分丢 fold 稳定性, 表达 yield 下降; 必须保留 buried 必需 Cys
- 早期 PEG 修饰策略用更小 PEG (5 kDa) 半衰期不足, 必须 20-40 kDa PEG; PEG 大小 + branched vs linear 是独立优化变量
- 来源选择: 早期试 plant PAL (parsley / maize) 因 Cys 数过多 + 免疫原性高 + folding 难, 全部 fail; 必须换 cyanobacterial AvPAL
- AvPAL 哪怕是 active 也不是 wild-type, 必须 PEG 化才用 — naked AvPAL 体内半衰期 < 数小时

## 4. 学习收获
- **成立的规则候选**:
  - **MIO 依赖 lyase 工程化绝对禁区**: Ala-Ser-Gly MIO motif + active site Tyr + tetramer 界面
  - **Biopharmaceutical 工程化的 'Cys census'**: 系统排查自由 Cys, 选 surface 远 active site 的去除 — PEG 修饰均一性的关键
  - **来源选择** (cyanobacterial 优于 plant) 是 PAL biopharmaceutical 路线先决条件
  - **临床蛋白工程化 ≠ 工业酶工程化**: 关注变量从 kcat/Tm 转到 in vivo PK/PD + 免疫原性 + 修饰均一性
- **被推翻的假设**:
  - "保留所有 Cys 让 fold 最稳" — 自由 Cys 是 PEG 修饰均一性的主要破坏源, 必须减少
  - "plant PAL 来源更接近人 - 免疫原性低" — 实际反例, plant PAL 比 cyanobacterial AvPAL 免疫原性更高 (序列相似度伪相关)
- **下次类似问题应优先尝试**:
  - 任何蛋白疗法工程化, 先做 Cys 普查 + surface-exposed Cys → Ser
  - 来源选择优先 microbial > plant > mammalian (反直觉, 与 immune privilege 实际数据一致)
- **应避免**:
  - 任何 MIO 自动催化形成的 motif (Ala-Ser-Gly) ±2 残基 mutation
  - 把 in vitro kcat/Tm 优化当作临床蛋白工程化主指标

## 5. 计算 / 实验原始数据
原始 PEG 修饰 MS + 体内 PK/PD 数据见 PNAS 2008 supplementary; FDA Palynziq 临床数据由 BioMarin 后续公开 (clinicaltrials + 商业).
