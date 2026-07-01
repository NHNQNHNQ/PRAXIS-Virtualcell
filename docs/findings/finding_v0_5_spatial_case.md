# finding v0.5 R5 — Spatial niche 依赖状态 case:间质微环境 → 肿瘤 EMT(真跑)

> 目标:补应用 5 例 5B(spatial niche → 同细胞不同 niche 的响应差异)。证据类型:`[Mac确定性]`。**自主完成**(squidpy imc)。对应 `docs/PLAN-v0.5-complete-remaining.md` R5。

## 1. 数据 + 分析

- 数据:`squidpy.datasets.imc()`(乳腺癌 Imaging Mass Cytometry,4668 cells,34 蛋白 marker,含空间坐标)→ committed 子集 `data/cellstate/imc_niche_subset.json`(3909 肿瘤细胞 × 空间 niche + Vimentin/ECadherin,346KB;provenance `PROVENANCE_imc.json`)。
- **niche 定义**:空间 **k-NN(k=15)邻域的间质细胞占比**(建子集时预计算)→ stroma_adjacent(≥25%)/ stroma_poor(<5%)。
- route:`(human, medium, state) → spatial_niche`(medium=微环境/niche)。EMT niche score = Vimentin − ECadherin。

## 2. 结果 + 治理(实跑)

| niche | EMT score(Vim−ECad,肿瘤细胞) |
|---|---|
| 间质邻接(stroma_adjacent,n=70) | **−1.90** |
| 间质贫瘠(stroma_poor,n=2899) | **−4.70** |

**Cohen's d = 0.74**(中等)→ **caution**(niche 效应真实但非强)。

- 分项:间质邻接肿瘤 Vimentin↑(d=0.45)、ECadherin↓(d=−0.75)→ 部分 EMT。
- 治理:niche 差异强(d≥0.8)→accept,中等(0.3–0.8)→**caution**,弱→downgrade;niche 细胞不足→abstain。测试 `test_spatial_niche_case.py`(4 passed)。

## 3. 意义

**同一肿瘤细胞类型,在不同空间 niche(间质邻接 vs 贫瘠)呈不同 EMT 状态** → 证明 agent 能做**空间 niche 依赖分析**(应用 5 environment 维度),并按效应强度受治理裁决(d=0.74 → caution,不硬报强 niche 效应)。

## 4. 诚实边界

- EMT niche score 是 IMC 蛋白表达相对量(Vim−ECad),**非**绝对 EMT 程度或空间因果。
- niche 由空间 k-NN 邻域间质占比定义(k=15、阈值为设定默认);imc **单样本**乳腺癌。
- 间质邻接肿瘤更间质性是**可检验锚点**(间质诱导 EMT,教科书);d=0.74 → caution 是诚实的中等置信。**不训练模型**。
