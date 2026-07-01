# finding v0.5 R1 — Stem/progenitor 分化 fate case:红系 vs 髓系(真跑)

> 目标:补 State/fate 例 3A(stem/progenitor → differentiation fate)。证据类型:`[Mac确定性]`。**自主完成**(scanpy 自带 paul15)。对应 `docs/PLAN-v0.5-complete-remaining.md` R1。

## 1. 数据 + 分析

- 数据:`scanpy.datasets.paul15()`(Paul et al. 2015 小鼠髓系祖细胞分化,2730 cells)→ committed 子集 `data/cellstate/paul15_fate_subset.json`(750 cells,红系/髓系/其它 lineage × marker,119KB;provenance `PROVENANCE_paul15.json`)。
- route:`(mouse, gene, state) → state_scoring`。fate score = 红系 marker(Gata1/Klf1/Hbb-b1/Car2/Zfpm1/Epor/Car1)− 髓系 marker(Elane/Mpo/Prtn3/Cebpe/Csf1r/Ctsg),复用 `scoring.py`。

## 2. 结果 + 治理(实跑)

| lineage | fate score(红系−髓系) |
|---|---|
| 红系 cells | **+1.27** |
| 髓系 cells | **−2.76** |

**Cohen's d = 4.32**,marker 覆盖 100% → **accept**(fate 评分强分离两谱系)。

- 治理:两谱系 panel 覆盖须都够(取 min),任一 <50% → **downgrade**(缺红系 marker 就定不了命运);谱系细胞不足 → abstain。测试 `test_fate_case.py`(4 passed)。

## 3. 诚实边界

- fate 评分是 **marker-based lineage 相对量**(红系−髓系),**非**绝对命运概率或 pseudotime。
- paul15 小鼠祖细胞子集;marker/阈值为设定默认。
- **原生小鼠 scRNA marker 分析,非 human→mouse predictor 迁移** → route 的 mouse ortholog caution **不适用**(已在 case note 标明)。
- 本 case 证明 agent 能把输出扩到 **differentiation fate** 并受治理,非造血分化的完备刻画。**不训练模型**。
