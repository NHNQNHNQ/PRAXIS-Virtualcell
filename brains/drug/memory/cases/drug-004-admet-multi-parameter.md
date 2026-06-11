---
case_id: drug-004-admet-multi-parameter
project_phase: lead_opt
target_uniprot: any
target_class: any
modality: small_mol
hit_id_method: na (downstream filter)
representative_compounds:
  - name: thalidomide  # 经典 ADMET 失败案例（teratogenicity；clinically racemic）
    chembl_id: CHEMBL468
    inchikey: UEJJHQNACJXSKW-UHFFFAOYSA-N   # ChEMBL stores achiral; (R)/(S) interconvert in vivo
    smiles: O=C1CCC(N2C(=O)c3ccccc3C2=O)C(=O)N1
  - name: terfenadine  # 撤市（hERG）
    chembl_id: CHEMBL17157   # corrected; original CHEMBL906 was a different molecule entirely
    inchikey: GUGOEEXESWIERI-UHFFFAOYSA-N
    smiles: CC(C)(C)c1ccc(C(O)CCCN2CCC(C(O)(c3ccccc3)c3ccccc3)CC2)cc1
tools: [ADMET-AI, Chemprop, DeepPurpose, SwissADME, RDKit, pkCSM]
qa_notes:
  - "Original CHEMBL906 was wrong entity (PRAXIS-Drug QA pipeline cross-check via ChEMBL search by name returned CHEMBL17157 as authoritative)."
  - "Thalidomide stored achirally in ChEMBL because (R) and (S) enantiomers interconvert in vivo at physiological pH — important for teratogenicity story."
key_paper_doi: 10.1093/bioinformatics/btae416
status: validated
validated: true
source: praxis_seed
---

# ADMET 多参数评估：哪些 endpoint 是红线 vs 可调

## Background
Thalidomide（致畸）、terfenadine（hERG → 撤市）、cerivastatin（横纹肌溶解）等多个药物因 ADMET 失败下市。现代 lead optimization **ADMET 与 potency 同等重要**，且某些 endpoint 是 hard stop（hERG IC50 < 1μM 直接 drop），其他是 soft（logP 5.5 仍 OK 若 PK 表现好）。

## What I actually did
1. **ADMET-AI 跑 50+ endpoint**（一次推理覆盖 absorption / distribution / metabolism / excretion / toxicity）：
   - Lipinski: MW, logP, HBA, HBD, rotatable bonds, TPSA
   - PAMPA permeability
   - Caco-2 permeability
   - Plasma Protein Binding (PPB)
   - hERG IC50（**critical**）
   - CYP inhibition (CYP3A4, CYP2D6, CYP2C9, CYP1A2, CYP2C19) - 主要 5 个
   - Ames 突变性
   - DILI（药物诱导肝损）
   - Skin sensitization
2. **Hard stop rules**（自动 reject）：
   - hERG IC50 < 1 μM
   - Ames 阳性 + 无 caveat
   - CYP3A4 强抑制（IC50 < 1 μM 且非选择性）
   - DILI 高风险
3. **Soft constraint**（warn but continue）：
   - logP > 5（permeability 可能 OK 但溶解度差）
   - PPB > 99%（free fraction 低，剂量难定）
   - Caco-2 permeability < 1e-6 cm/s（口服吸收差，但可改 IV）
4. **Multi-method consensus**：ADMET-AI + SwissADME + pkCSM——三方对 hERG 都报警的更可信
5. **应用到 olaparib (PARP)**：MW 434, logP 1.5, HBA 7, HBD 1 → Lipinski clean；hERG predict mid-low；CYP3A4 substrate（已知）→ DDI 警告
6. **Lead opt loop**：发现 hERG hit 在某 series → 加 polar group / 减 lipophilicity → 重测 → 平衡 potency

## ★ 排除/不做的事
- **单一 ADMET model 决策**：不同 model 训练数据不同，hERG 上 ML model 一致性 < 70%；多方法 vote
- **看绝对值不看 confidence interval**：hERG IC50 = 5 μM ± 4 μM 与 = 5 μM ± 0.5 μM 决策不同
- **忽略 species-specific**（人 vs 鼠）：rat clearance 不等于 human；ML 模型常是 human-trained
- **不分 Hard vs Soft**：把所有 endpoint 同等权重 → 失去优先级
- **优化 single endpoint 牺牲其他**：刷掉 hERG 但 potency 暴跌，得不偿失；多目标平衡
- **不做 metabolite prediction**：parent compound 安全但 metabolite 致毒（如 acetaminophen → NAPQI）
- **不报 confidence**：用户不知道 prediction 多可信

## ★ 失败模式
- **Domain shift**：ML 训练数据多为已上市药物或失败 candidate，OOD 化合物（macrocycle / PROTAC）预测不准
- **Activity cliff at edge of training data**：lead opt 阶段微小结构变化，ADMET predict 几乎不变但实验暴变
- **Static prediction 不反映 PK dynamics**：tmax / AUC / half-life 这些 dynamic property 静态 ML 模型不直接给
- **Multi-target effect**：化合物可能同时 inhibit CYP3A4 + 是 P-gp substrate → DDI 复杂，单 endpoint 模型不互通
- **Formulation effect 未考虑**：salt form、polymorph、co-formulation 影响 PK，纯化合物 prediction 不全
- **Cross-species extrapolation**：rat → dog → human 的 PK scaling 是工程问题不是 single ML 题

## Lessons → seeds for rules
1. **Hard stop list 强制执行**：hERG / Ames / 强 CYP3A4 / DILI = automatic reject 除非 user override
2. **Soft warning**：logP / PPB / permeability 等给 warn 不阻塞
3. **多方法 vote**：≥ 2 ADMET predictor 一致才 trust prediction
4. **Confidence interval / uncertainty 必报**
5. **Metabolite 评估**：跑 BioTransformer 或 SyGMa 预测主要 metabolite，再 ADMET 评估
6. **Multi-objective 与 potency 同窗优化**（不串行：先 potency 后 ADMET 是 anti-pattern）
