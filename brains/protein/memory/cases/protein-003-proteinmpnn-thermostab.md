---
case_id: protein-003-proteinmpnn-thermostab
design_task: stabilization
target_pdb: 1RX1 (DHFR)
target_uniprot: P00374
fold_class: rossmann
tools: [ProteinMPNN, ESM-2 zero-shot, ThermoMPNN, Rosetta ddG, PyRosetta]
key_paper_doi: 10.1126/science.add2187
status: validated
schema_version: 1
source: praxis_seed
extracted_at: 2026-04-29
---

# DHFR 稳定化：ProteinMPNN + ThermoMPNN + Rosetta 三方投票

## Background
ProteinMPNN（Dauparas 2022 Science）原论文展示对天然蛋白做 sequence redesign（保留 backbone）能提升表达 + 稳定性 + 溶解性。DHFR 是经典 enzyme，已知 thermo benchmark + 大量文献突变数据，是测稳定化方法的经典 testbed。

## What I actually did
1. **Backbone**：1RX1 干净化（去水/共结晶配体保留 / 缺失 loop 用 ESMFold 补全）
2. **ProteinMPNN redesign**：`temperature=0.1`, `num_seq_per_target=64`, **fix active site residues**（与 substrate/cofactor 6 Å 内 = freeze）—— **这是关键**，不固定催化残基会失活
3. **ThermoMPNN per-position scan**：所有非 active site 位点单点 ΔΔG 预测，挑 ΔΔG < -1.5 kcal/mol 的 candidate
4. **Rosetta ddG_monomer**（cartesian protocol）：交叉验证 ThermoMPNN top 100 candidate
5. **PyRosetta cartesian_ddg**：第三方法验证（精度差但快）
6. **三方投票 rule**：3/3 agree → high confidence；2/3 → medium；1/3 → discard
7. **Mutation combinatorial**：top 10 single mutations 做 epistasis check（pairwise additivity 假设常错），用 ProteinMPNN 重新打分含两个突变的序列
8. **In vitro plan**：CD melting curve（Tm shift）+ 酶活 assay 平行测，因稳定化常带活性降

## ★ 排除/不做的事
- **不固定 active site 跑 ProteinMPNN**：失活率 50%+——活性位点残基保守是有原因的
- **只信 single ΔΔG predictor**：PyRosetta RMSE ~1.5 kcal/mol；ThermoMPNN 0.9 但仍可错；Rosetta 0.8——三方至少 2/3 同意
- **加性假设（additive epistasis）做 multi-mutation**：> 2 突变就破坏假设；需 ProteinMPNN 重新打分组合或物理建模
- **MPNN 温度 0.5+**：偏离野生过远，引入未必稳定的不熟悉序列
- **Backbone 缺失 loop 不补**：ProteinMPNN 在缺失 loop 处 sample 出垃圾序列——先 ESMFold/AF 补全 backbone
- **Tm 上升 = 一切好**：Tm +10°C 可能伴随 kcat 降 100x；必须 Tm + activity 双 assay

## ★ 失败模式
- **Surface vs core 偏差**：ThermoMPNN 在 core 准（疏水核心 ΔΔG 主导稳定性）；surface 残基预测差异大
- **Disulfide 影响**：自然有 SS bond 的蛋白预测器普遍偏（PyRosetta 处理 cysteine 不稳）
- **Proline 与转角**：Pro 引入可稳定 turn 但破坏 helix；预测器对 secondary structure-specific 效应差
- **Cosolvent / cofactor 在 ΔΔG 模型外**：DHFR 与 NADPH 共结合，apo 形态稳定性 ≠ holo
- **Aggregation vs unfolding**：稳定化预测针对 unfolding，但 in vitro 不稳定常因聚集——需另算 patch 评分（Aggrescan）
- **Multi-mutant 反向 epistasis**：top 5 single 都 ΔΔG -2 但合在一起 ΔΔG +5（结构无法 accommodate）

## Lessons → seeds for rules
1. **必须 freeze active site 残基**（substrate/cofactor 6 Å 内 = 不可改）
2. **三方法投票**：ThermoMPNN + Rosetta ddG + PyRosetta；2/3 一致才推荐
3. **Multi-mutation 不靠加性**：> 2 mutation 必须 combinatorial 重新打分
4. **In vitro 必测 Tm + activity 双指标**——Tm 升活性必须 ≥ 50% 保留才合格
5. **Aggregation propensity 单独评估**（Aggrescan/AGGRESCAN3D）——稳定化不等于不聚集
6. **ProteinMPNN 温度 0.1 起步**，仅探索时升温
