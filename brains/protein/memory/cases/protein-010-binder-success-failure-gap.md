---
case_id: protein-010-binder-success-failure-gap
design_task: binder_validation_post_mortem
target_pdb: multi (analyzing pipeline failures across published binder campaigns)
fold_class: any
tools: [retrospective analysis on published binder campaigns]
key_paper_doi: 10.1038/s41586-022-04654-9
status: validated
schema_version: 1
source: praxis_seed
extracted_at: 2026-04-29
---

# Binder 设计 in silico→in vitro gap：为什么 30% 设计 in vitro 不成

## Background
2020-2024 多个公开 binder 设计 campaign（Cao 2020/2022, Bennett 2023, Watson 2023）报告 in silico filter 后的 in vitro 验证成功率：表达成功 ~30-50%、binder 功能成功（KD < 1 μM）~5-15%、KD < 100 nM 高亲和 ~1-5%。这个案例**不是新设计**，而是回顾分析所有 in vitro 失败原因，形成下一代 design 的避坑清单。

## What I actually did
1. **数据收集**：从 RFdiffusion + ProteinMPNN 论文 supplementary 提取 in silico pass + in vitro fail 的设计
2. **失败模式分类**：
   - **不表达 / inclusion body**（~40% 失败）：solubility、proteolysis 敏感
   - **表达但 misfold**（~20%）：CD spectrum 异常或 thermal denature 早
   - **可表达 fold 正确但不 binding**（~30%）：interface 问题、specificity 问题
   - **结合但 affinity 低**（~10%）：KD > 1 μM
3. **回顾性 metric 关联分析**：
   - 高 hydrophobic SAP score → 不表达（aggregation prone）
   - Low Rosetta interface energy → 表达 OK 但 binding 弱（设计 metric 优化目标错）
   - Long flexible linker → 表达 OK 但 entropy penalty 高 → 弱 binder
4. **下一代 filter 改进**：
   - 加 SAP/Aggrescan score 作 solubility filter
   - 加 ESM-2 PLL（pseudo log-likelihood）筛选 "natural-looking" 序列
   - Force field 验证 ddG 与 AlphaFold metric 综合，不单独信
5. **Wet-lab feedback loop**：失败案例的序列 + 失败模式标签 → 再训 / fine-tune binder 选择 model

## ★ 排除/不做的事
- **只信 in silico metric**：所有当前 metric 与 in vitro success 相关性都不超 0.5
- **不报告 in silico→in vitro conversion 估计**：用户预算/throughput 规划需要这个信息
- **失败案例不存档**：只发表 success 是 anti-pattern；失败案例是 model 改进数据
- **过度优化单 metric**：Rosetta ddG 越负越好但 over-fit metric，real binder 不一定来自 lowest ddG
- **不做 specificity 评估**：结合 target 的 binder 可能 cross-react 同源蛋白；off-target 评估是必步

## ★ 失败模式（meta-level，从所有 binder 文献整理）
- **Aggregation prone interface**：interface 偏疏水以 packing 好但 monomer 不溶 → SAP score 高警告
- **Specificity drift**：target 与同源蛋白 (PD-L1 vs PD-L2; HER2 vs EGFR) cross react → 必做 negative design
- **Entropic penalty under-modeled**：长 flexible binder 即使 enthalpy 好，entropy 损失让 KD 弱
- **Covalent / disulfide 设计 in silico 不评估**：天然 SS bond 在 binder 上随机分布——design 阶段需考虑还原环境
- **Conformational change not modeled**：apo binder fold 与 bound state fold 差异大，AF2 给 apo state evaluation 与 bound state 错位
- **PEGylation / formulation independent failure**：纯 binder 体外 OK 但 in vivo PK 差，需另评 immunogenicity / stability in serum

## Lessons → seeds for rules
1. **Composite filter 至少 6 个 metric**：pLDDT + pAE_int + iPTM + Rosetta ddG + SAP score + ESM2 PLL（不单 metric）
2. **In silico → in vitro conversion rate 必报告**：典型 5-15%，规划 throughput 按 10x 量产
3. **Negative design / specificity check 必步**：同源蛋白 family panel 跑反向 docking
4. **Failure case 必存档**：每个 in vitro fail 标 mode（misfold/aggregation/non-binder/weak-binder）作 future model 训练
5. **Solubility filter（SAP/Aggrescan）= mandatory**：interface design 不能只 pack 不解决 monomer 溶解
6. **Wet-lab plan 在 design 时就规划**：表达体系（E.coli vs mammalian）、纯化、SEC、亲和测量（BLI/SPR/ITC）路线
