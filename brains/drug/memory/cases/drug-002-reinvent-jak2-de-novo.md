---
case_id: drug-002-reinvent-jak2-de-novo
project_phase: hit_id
target_uniprot: O60674 (JAK2)
target_pdb: 3KRR
target_class: kinase
indication: myeloproliferative_neoplasm
modality: small_mol_inhibitor
hit_id_method: de_novo_generative
representative_compound:
  - chembl_id: CHEMBL1789941 (ruxolitinib)
    inchikey: HFNKQEVNSGCOJV-OAHLLOKOSA-N
    smiles: N#CC[C@H](C1CCCC1)n1cc(-c2ncnc3[nH]ccc23)cn1   # ChEMBL canonical SMILES; chirality [C@H], not [C@@H]; IK HFNKQEVNSGCOJV-OAHLLOKOSA-N
tools: [REINVENT4, MolGPT, ChemBL35, RDKit, ADMET-AI, AiZynthFinder]
qa_notes:
  - "Original ChEMBL ID CHEMBL3046547 was incorrect (404). PRAXIS-Drug QA pipeline caught this; replaced with CHEMBL1789941 (verified pref_name=RUXOLITINIB, max_phase=4.0)."
key_paper_doi: 10.26434/chemrxiv-2023-jc2x6
unverified_details: [doi]   # ChemRxiv preprint; not indexed in CrossRef public API
status: validated
validated: true
source: praxis_seed
---

# JAK2 de novo：REINVENT4 多目标生成 + 实时 reward

## Background
REINVENT4 是 RNN/transformer-based 分子生成框架，支持多目标 reward shaping。JAK2 是经典 kinase，已知 selectivity issue（JAK1/2/3/TYK2 同 family），可用作演示如何在 reward 中加 selectivity 项。

## What I actually did
1. **Prior model**：REINVENT4 默认在 ChEMBL 全集预训练，输出 valid SMILES ~95%
2. **Reward components**（multi-objective）：
   - **Predicted activity** vs JAK2（用本地训练 QSAR model，e.g. ChemProp on ChEMBL JAK2 IC50 数据）
   - **Predicted activity vs JAK1/3**（要 select against）—— score = -predicted_activity for off-targets
   - **QED** ≥ 0.6
   - **SAscore** ≤ 4
   - **MW** ∈ [300, 500]
   - **logP** ∈ [1, 5]（Lipinski）
3. **Reinforcement learning loop**：500-1000 epochs，每 epoch 生成 batch 64 → 算 reward → policy update
4. **Diversity 监控**：sample 1000 molecules → unique scaffold 数（Murcko）；scaffold collapse （所有 sample 同一个 scaffold）是 reward over-fitting 信号
5. **后筛**：generate 10000 → unique → scaffold 多样化 → 5-metric 排序：activity + QED + SA + selectivity + novelty (Tanimoto vs ChEMBL nearest)
6. **Reality check**：top 100 用 docking (Vina) 进 JAK2 active site，看物理可行性
7. **Synthesis check**：top 50 跑 AiZynthFinder，路径 ≤ 6 步 + 商业可购起原料

## ★ 排除/不做的事
- **Single-objective reward**（只 activity）：会刷出 PAINS、不可合成、巨大分子
- **不带 selectivity**：JAK2 hit 同 ChEMBL ratio 60% 跨 JAK1/3 active；不 deselect 出来全是 pan-JAK
- **不限 MW/logP**：刷出 800+ 道氏分子，不可能成药
- **Reward weights 不归一化**：activity 数值范围 vs QED 0-1 scale 完全不同，QED 被淹没
- **不做 reality check（docking）**：QSAR model 假阳率高，物理 docking 是底线 sanity
- **Scaffold 单一收敛**：reward over-fit，多样性塌陷；要监控 unique scaffold 数趋势
- **不做 novelty filter**：generate 出 ChEMBL 已有化合物（就是 train set 里的）等于浪费

## ★ 失败模式
- **QSAR model 失效**：训 ChEMBL 数据混 cell-based + biochemical assay，predicted activity 不可比
- **Selectivity reward 反向**：`reward = -off_target` 与 `reward = on_target - alpha * off_target` 数学不同；alpha 调过头出全部 inactive 分子
- **Mode collapse**：late epoch sample 99% 同 scaffold，diversity 死
- **过滤后无几个剩**：reward 太严格，5000 generate → 后筛剩 5；用宽 reward + 大 sample（10x）
- **Synthesis 都 ≥ 8 步**：现代化学合理上限 6-8 步；8+ 不实用，要 SAscore + retrosynthesis 双 check
- **Activity 高但 PAINS**：QSAR model 学 PAINS 反应基团 → 推 michael acceptor / quinone 等

## Lessons → seeds for rules
1. **Multi-objective reward 必须** ≥ 4 项（activity + drug-likeness + selectivity + synthesis）
2. **Reward 归一化**到 0-1 后再加权
3. **Diversity monitoring** 全程：unique scaffold trend，崩塌阻断
4. **Reality check (docking) 后筛**：generative model 物理不可信
5. **Synthesis filter 强制**：SAscore ≤ 4 + AiZynthFinder ≤ 6 步双 check
6. **Novelty filter**：generate 后剔除与 ChEMBL Tanimoto > 0.7 hits（除非 explicit goal scaffold-hopping）
