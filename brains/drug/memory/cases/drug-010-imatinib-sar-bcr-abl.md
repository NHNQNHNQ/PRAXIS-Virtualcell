---
case_id: drug-010-imatinib-sar-bcr-abl
project_phase: lead_opt_to_clinic
target_uniprot: P00519 (ABL1)
target_pdb: 1IEP (ABL with imatinib)
target_class: kinase
indication: CML_BCR_ABL
modality: small_mol_inhibitor (Type II, DFG-out binder)
hit_id_method: rational_optimization
representative_compounds:
  - name: imatinib (Gleevec)
    chembl_id: CHEMBL941
    inchikey: KTUFNOKKBVMGRW-UHFFFAOYSA-N
    smiles: Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc1nccc(-c2cccnc2)n1
  - name: nilotinib (2nd gen, T315I-resistant)
    chembl_id: CHEMBL255863
    smiles: Cc1cn(-c2cc(NC(=O)c3ccc(C)c(Nc4nccc(-c5cccnc5)n4)c3)cc(C(F)(F)F)c2)cn1
tools: [Schrödinger Maestro / FEP+, RDKit, AutoDock Vina, AlphaFold mutation modeling, MD GROMACS]
key_paper_doi: 10.1038/sj.leu.2402091
status: validated
validated: true
source: praxis_seed
---

# Imatinib SAR：从 phenylaminopyrimidine hit 到 nilotinib（T315I-resistant）的全 SAR

## Background
Imatinib（Novartis 2001 FDA approved，Druker）是 BCR-ABL 第一个靶向药，CML 治疗革命。后来出现耐药 mutation（T315I gatekeeper）→ nilotinib (2007)、dasatinib (2006)。是经典 SAR 演进 case：从 high-throughput screen hit → 5 步 lead optimization → 临床 → 耐药对策。

## What I actually did（in silico SAR 复盘）
1. **Imatinib core scaffold**：phenylaminopyrimidine（PAP）binding hinge region of ABL kinase
2. **关键 SAR points**：
   - 甲基（ortho-methyl）防止酰胺旋转：构象锁定，亲和 100x ↑
   - 哌嗪 + N-methyl：solubility（不影响 binding）+ 与 selectivity 相关
   - Pyridine ring：与 hinge backbone H-bond
3. **Type II binder（DFG-out）模式**：与多数 type I（DFG-in）抑制剂不同，imatinib 占用 hydrophobic back pocket（DFG flip 后暴露）；selectivity 来自这种 unique mode
4. **T315I 耐药**：gatekeeper Thr → Ile，Ile 侧链 bulky 占据 pocket，imatinib 无法 fit；nilotinib 重设计 group avoid Ile clash
5. **Nilotinib 改进**：N-methyl piperazine 替换为 imidazole + CF3——imidazole 更高 lipophilic + CF3 增 metabolic stability + 重塑 H-bond pattern
6. **Selectivity panel**：ABL vs c-Kit vs PDGFR（同 family kinase）；imatinib 实际 multi-kinase inhibitor（c-Kit/PDGFR 也抑制，部分用于 GIST）
7. **MD 验证耐药**：T315I mutant 结构（AF2 mutate + MD）vs WT，imatinib pose 在 mutant simulation 中 escape rate 高

## ★ 排除/不做的事
- **不考虑 conformational state（DFG-in vs out）**：所有 docking 在 DFG-in 结构，会漏 type II inhibitor opportunity
- **不评估 mutation panel**：临床耐药突变 (T315I, F317L, V299L 等) 必须在 lead-opt 阶段 docking + MD
- **Selectivity panel 缺失**：ABL hit 在 ABL family + tyrosine kinase 全 panel cross-react
- **Solubility 与 binding 混淆 SAR**：piperazine 加上去主要为 solubility 不为 affinity——不要把所有改进都归 binding
- **不区分 Type I/II/III**：mechanism 完全不同，SAR strategy 不同
- **耐药对策不同步规划**：第一代药都耐药，第二代必须前置考虑

## ★ 失败模式
- **DFG flip 不在 docking 中体现**：rigid receptor docking 漏掉 DFG-out 形态
- **Selectivity 改善牺牲 efficacy**：dasatinib 比 imatinib selectivity 差，但 efficacy 高 → 在 BCR-ABL 上有用，但脱靶副作用多
- **Cross-resistance**：T315I 对 imatinib + nilotinib + dasatinib 全耐；新一代 ponatinib 才解决（但有 vascular toxicity 副作用）
- **Off-target 副作用**：imatinib c-Kit 抑制 → 治疗 GIST 有效但意外发现的；当初 c-Kit cross 是 risk
- **Long-term resistance evolution**：长期治疗诱导 compound mutation（T315I + 其他），单 mutation panel 不够
- **PK 在长期治疗中 drift**：CYP3A4 substrate，长期 induction 改变 exposure

## Lessons → seeds for rules
1. **Kinase docking 必须 multi-conformation**（DFG-in + DFG-out + αC-in + αC-out）
2. **Mutation panel 在 lead-opt 阶段**：known clinical resistance mutations 全跑 docking + MD
3. **Selectivity panel 同 family**：ABL → ABL/c-Kit/PDGFR/Src 全 panel
4. **SAR attribution 分项**：affinity vs selectivity vs solubility vs metabolic stability，每项独立分析
5. **Type I/II/III 分别策略**：scaffold 选择、conformational state 不同
6. **Resistance forecast**：lead-opt 时模拟下一代耐药突变，前置规划第二代化合物
