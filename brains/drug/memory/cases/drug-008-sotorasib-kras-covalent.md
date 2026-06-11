---
case_id: drug-008-sotorasib-kras-covalent
project_phase: hit_id_to_lead
target_uniprot: P01116 (KRAS)
target_pdb: 6OIM (KRAS G12C with sotorasib)
target_class: gtpase
indication: NSCLC_KRAS_G12C
modality: covalent_small_mol
hit_id_method: covalent_screening
representative_compounds:
  - name: sotorasib
    chembl_id: CHEMBL4535757
    inchikey: NXQKSXLFSAEQCZ-SFHVURJKSA-N   # corrected via ChEMBL standard_inchi_key
    smiles: C=CC(=O)N1CCN(c2nc(=O)n(-c3c(C)ccnc3C(C)C)c3nc(-c4c(O)cccc4F)c(F)cc23)[C@@H](C)C1   # ChEMBL canonical SMILES (5-membered methylpiperidine, ortho-fluorophenol); IK NXQKSXLFSAEQCZ-SFHVURJKSA-N
tools: [Vina with covalent restraints, AutoDock-CrankPep, GNINA, RDKit reactive groups]
qa_notes:
  - "Original SMILES was a wrong tautomer (=N- instead of =O on the pyrimidone ring). ChEMBL canonical SMILES + standard_inchi_key (NXQKSXLFSAEQCZ-SFHVURJKSA-N) is the verified form."
key_paper_doi: 10.1038/s41586-019-1694-1
status: validated
validated: true
source: praxis_seed
---

# Sotorasib：covalent KRAS G12C inhibitor，cryptic pocket + acrylamide warhead

## Background
KRAS G12C 曾被认为 "undruggable" 30 年——直到 2013 Shokat lab 发现 G12C 半胱氨酸可被 acrylamide 共价结合 + 揭示 cryptic pocket（switch II）。Sotorasib（Amgen, 2019, FDA approved 2021）是首个临床 KRAS 抑制剂。Covalent design 的 case study。

## What I actually did
1. **Target prep**：KRAS G12C apo 结构 → MD 100ns 揭示 cryptic switch II pocket；用 holo (sotorasib bound) 6OIM 也行
2. **Reactive cysteine 识别**：G12C 的 Cys12 是 unique reactive site；E.coli purified protein 测 alkylation kinetics
3. **Warhead 选择**：
   - **Acrylamide**: classic, mild electrophile, good selectivity
   - **Chloroacetamide**: more reactive, off-target risk
   - **Sulfonyl fluoride**: SuFEx, milder
   - **Cyanoacrylamide**: reversible covalent
4. **Covalent docking**：Vina 加 covalent restraint（Cys12 SG 与 warhead C 距离 < 2 Å）；或专用 Schrödinger Covalent Docking
5. **GFE 分析**：covalent 不像 reversible，亲和不能用 IC50；用 kinact/Ki（reactive site engagement rate）
6. **Selectivity 关键**：~100 reactive Cys 在 proteome；selectivity 来源是 (a) reversible binding 先固定 pose (b) 然后 covalent reaction；(a) 决定 selectivity，(b) 决定 efficacy
7. **Mass spectrometry confirmation**：MS/MS 证明 mod site 在 Cys12 而非 off-target

## ★ 排除/不做的事
- **传统 docking 直接用**：忽略 covalent geometry，pose 不准
- **过反应 warhead**（α-haloketone / Michael acceptor with EWG）：proteome-wide off-target
- **不测 kinact/Ki**：covalent 用 IC50 表征是错的（time-dependent）
- **Apo 结构 docking 错过 cryptic pocket**：必须 MD 或 holo 结构
- **Cysteine mutation panel 不跑**：selectivity 验证需 G12C vs G12V vs WT KRAS 比对（G12V 应不结合，因 V 不反应）
- **Reactive group 在 metabolite 处释放**：parent 安全但 metabolite 有 michael acceptor → 隐性毒性
- **不评估 GSH 反应**：低 K_m for GSH 的 warhead 体内被 detox 失活

## ★ 失败模式
- **Cryptic pocket 不存在 in apo**：纯 apo docking 拿不到 hit，必须 induced fit / MD
- **Reversible binding 弱 → 选错 Cys**：体内 reactive Cys ~100 个，弱 reversible binder 反应到不该反应的 Cys，毒
- **Resistance**：G12C → G12C+H95Q 耐药突变（H95Q 改 pocket）
- **Off-target Cys covalent**：proteomics 验证 sotorasib 也 modify 其他 Cys < 1% 但需评估
- **Time-dependent toxicity**：covalent 累积效应，长期毒性与 IC50 无关
- **GSH adduct 假阳**：高 GSH 反应性 warhead → liver 中被 GSH conjugate，SAR 看似 OK 实际无效
- **Off-target proteomics screen 漏做**：发表前必做 thermal proteome profiling (TPP) / CETSA

## Lessons → seeds for rules
1. **Covalent 用 covalent docking 工具**（Vina 加 restraint 或 Schrödinger CovDock），不是普通 docking
2. **kinact/Ki 表征**而非 IC50（time-dependent）
3. **Warhead reactivity 谱**：acrylamide (mild) → chloroacetamide (mid) → sulfonyl fluoride (mid) → α-haloketone (high reactivity)
4. **Cryptic pocket awareness**：apo + holo + MD 三方看 pocket
5. **Mutation panel selectivity**：reactive Cys vs non-reactive 突变，vs paralog Cys
6. **Proteomics off-target screen 必跑**：CETSA / TPP 量化 off-target engagement
7. **GSH reactivity 评估**：避免 in vivo detox 失活
