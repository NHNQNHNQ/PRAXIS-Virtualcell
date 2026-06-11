---
case_id: protein-009-symmetric-rfdiffusion-oligomer
design_task: symmetric_oligomer_de_novo
target_pdb: nan (de novo)
fold_class: helical_bundle_C3
tools: [RFdiffusion symmetric mode, ProteinMPNN, AlphaFold-Multimer, Rosetta]
key_paper_doi: 10.1038/s41586-023-06415-8
status: validated
schema_version: 1
source: praxis_seed
extracted_at: 2026-04-29
---

# 对称 oligomer 设计：RFdiffusion C3/C4/D2 模式

## Background
对称 homo-oligomer（C3/C4/D2/icosahedral 等）有两个用途：(1) 自组装 nanocage / nanoparticle 抗原 display；(2) cooperative function（如 trimeric receptor agonist）。Watson 2023 RFdiffusion 论文展示对称模式生成 C3/C5/icosahedral nanocage。

## What I actually did
1. **Symmetric mode**：`--config-name=symmetry symmetry.symmetry='c3' contigs="120-120"`——120 aa monomer × 3 copies，C3 symmetry
2. **Hotspot 在 interface**：定义 monomer-monomer interface 期望接触残基
3. 生成 500 backbone（GPU 12 h）
4. **ProteinMPNN with symmetric tied positions**：让 3 copies 同位置 sample 同 aa（symmetric design 必须保证 sequence symmetry）
5. **AlphaFold-Multimer 验证**：input = 3 copies of designed sequence with `:`分隔；看预测 vs design 的 TM-score
6. **Symmetric metric**：
   - Per-copy pLDDT > 80
   - Inter-copy interface pAE < 5
   - Symmetry RMSD（每 monomer 间）< 1 Å
7. **In silico → in vitro**：~5-15% 设计成功表达 + SEC monomeric oligomer state correct

## ★ 排除/不做的事
- **Symmetric mode 但 ProteinMPNN 不 tied positions**：3 copies 序列不同破坏 symmetry，等于做 hetero
- **Asymmetric scaffold 后期强制 symmetric assembly**：fold funnel 不对，几乎不成
- **Interface contact 不指定 hotspot**：interface 飘忽，可能 interface 几乎无接触
- **不验证 oligomeric state in vitro**：SEC 是必须步骤，不少 design 实际是 monomer 或错 state（dimer 而非 trimer）
- **过大 oligomer 做 first try**：dodecahedron 等大对称体 in vitro 成功率 < 1%；先做 C3/C4 验证 pipeline
- **MD 不验证**：symmetric 在 MD 下可能 break symmetry（自由能 driven），需 100ns+ MD 检查 stability

## ★ 失败模式
- **Aggregation prone**：interface 设计过 sticky → 全部聚成 amorphous aggregate
- **Wrong oligomeric state**：设计 C3 但 SEC 出 dimer 或 hexamer——interface complementarity 错
- **Asymmetry breaking in MD**：design 在 X-ray 看似对称但 dynamics 下偏对称
- **Solubility 问题**：interface 残基设疏水（packing 好）但 monomer 阶段不溶
- **AlphaFold 验证假阳**：iPTM 高但 actual fold 在表达时 misfold（chaperone-dependent fold 不在模型里）
- **Dynamic equilibrium**：oligomer ↔ monomer 动态平衡，单一 SEC 看不出

## Lessons → seeds for rules
1. **Symmetric mode 必须 tied positions ProteinMPNN**
2. **Interface hotspot 指定**——否则 interface noise
3. **In vitro SEC 验证 oligomeric state 必做**（即使 in silico 通过）
4. **MD 100ns+ stability check**：检查 symmetry 是否 dynamic broken
5. **Solubility 评估单独做**（Aggrescan/SAP）
6. **Start small（C3/C4）**：复杂 symmetry 先在简单上验证 pipeline
