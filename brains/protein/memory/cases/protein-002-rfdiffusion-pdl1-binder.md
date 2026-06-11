---
case_id: protein-002-rfdiffusion-pdl1-binder
design_task: de_novo_binder
target_pdb: 4Z18 (PD-L1)
target_uniprot: Q9NZQ7
fold_class: helical_bundle_or_mini_protein
tools: [RFdiffusion, ProteinMPNN, AlphaFold2-initial guess, PyRosetta]
key_paper_doi: 10.1038/s41586-023-06415-8
status: validated
schema_version: 1
source: praxis_seed
extracted_at: 2026-04-29
---

# PD-L1 mini-binder：RFdiffusion + ProteinMPNN + AF2 验证 pipeline

## Background
Watson 2023 (Nature) RFdiffusion 论文的 binder 案例之一。设计 60-100 aa 小蛋白结合 PD-L1（免疫检查点 target）。pipeline 模板：RFdiffusion 生成 backbone → ProteinMPNN 序列设计 → AF2 with initial guess 验证 → 排序筛选。

## What I actually did
1. **Target prep**：PD-L1 ECD（8-130 aa from 4Z18），定义 hotspot 残基（与 PD-1 接触的 Y56, M115, R125 等）
2. **RFdiffusion**：`scaffold_guided=True`, `noise_scale=0`, target hotspot list, `contigs="100-100"`（100 aa binder）；生成 1000 个 backbone（GPU ~6 h）
3. **每个 backbone 跑 ProteinMPNN**：`num_seq_per_target=8`, `temperature=0.1`（低温度更确定，但失多样性）
4. **AF2 with initial guess**：把 RFdiffusion 的 backbone 当 template 输入 AF2 monomer + multimer with target → 看是否 fold + 是否结合在 hotspot
5. **筛选 metric**：
   - pLDDT_binder ≥ 80
   - pAE_interaction（interface PAE）< 10
   - iPTM ≥ 0.6
   - Rosetta ddG 复合物界面 < -30 REU
   - ProteinMPNN sequence recovery > 30%（与 backbone 一致性高）
6. 1000 design → 这 5 个 cutoff 后剩 ~50；进一步 visual inspection（PyMOL clash）剩 ~10
7. **湿实验顺序**：Twist 合成 gene → E.coli BL21 表达 → SEC monomer 验证 → BLI 测亲和；典型成功率 in silico 通过 → in vitro fold 30%、binder 功能 5-15%

## ★ 排除/不做的事
- **不做 hotspot 标注**：RFdiffusion 不知道往哪 bind，输出 binder 是飘的（远离 epitope）
- **ProteinMPNN 温度 0.5+**：序列多样性高但折叠 funnel 浅，AF2 验证大量失败
- **不跑 AF2 initial guess**：直接 AF2 from sequence，confidence 低很多——initial guess 把 backbone 作为强 prior
- **只看 pLDDT**：binder 自身 fold 好但远离 target；必须看 pAE_interaction + iPTM
- **跳过 Rosetta ddG**：AF2 metric 没量化"结合自由能"，Rosetta 补一刀（虽然 ddG 也只是 proxy）
- **超长 binder（200+ aa）**：当前 RFdiffusion + ProteinMPNN 在 100-150 aa 表现最好，超长 in vitro 成功率暴跌

## ★ 失败模式（来自 Cao/Watson 等公开经验）
- **In silico → in vitro gap**：通过 AF2/Rosetta 全部 metric 的设计，~30% 在 E.coli 不表达或 inclusion body
- **Target 错构象**：用 apo PD-L1 设计的 binder 与 holo（已结合 PD-1 状态）冲突
- **Linker / disordered 区段抓上**：binder 选择结合柔性区而非 globular 表面——亲和测得到但功能无意义
- **Off-target 兄弟蛋白**：PD-L1 与 PD-L2 序列同源 ~37%，binder 可能交叉结合；需 negative design 或后续选择
- **Hotspot 占用偏差**：binder 其实结合 hotspot 的"邻居"残基而非真 hotspot——MD 验证 +/- 突变 hotspot 看亲和变化
- **AF2 假阳**：iPTM 0.85 但实际 SEC 出现寡聚/非 binder——AF2 在 de novo binder 上 false positive 率仍高

## Lessons → seeds for rules
1. **hotspot 标注是必需输入**——没有就别跑
2. **5-metric 联合筛选**：pLDDT + pAE_int + iPTM + Rosetta ddG + MPNN recovery，单一 metric 都不可信
3. **ProteinMPNN 温度 0.1-0.2**：偏 conservative；探索可加温度但 in vitro 成功率会降
4. **In vitro 成功率 in silico filter 后 ~10-30%**——预算和 throughput 按这个估
5. **Negative design 必要**：尤其同源蛋白家族（PD-L1/L2、HER 家族）需考虑 specificity
6. **湿实验链路（合成→表达→SEC→BLI）建议排好**：纯 in silico 没意义
