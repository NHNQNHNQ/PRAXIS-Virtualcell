# finding v0.5 R4 — Cancer EMT state 刻画 case:间质 vs 上皮(真跑)

> 目标:补 State/fate 例 3C(cancer EMT/resistance state)。证据类型:`[Mac确定性]`。**自主完成**(pertpy mcfarland_2020)。对应 `docs/PLAN-v0.5-complete-remaining.md` R4。

## 1. 数据 + 分析

- 数据:`pertpy.data.mcfarland_2020()`(MIX-seq 泛癌 scRNA,182875 cells,21 癌种)→ committed 子集 `data/cellstate/mcfarland_emt_subset.json`(900 cells,间质/上皮/hk marker × 肉瘤/上皮癌/其它,173KB;provenance `PROVENANCE_mcfarland.json`)。
- route:`(human, gene, state) → state_scoring`。EMT score = 间质 marker(VIM/FN1/CDH2/ZEB1/SNAI1/SNAI2/ZEB2/TWIST1)− 上皮 marker(CDH1/EPCAM/KRT8/KRT18/KRT19/CLDN4),复用 `scoring.py`。

## 2. 结果 + 治理(实跑)

| 癌类分组 | EMT score(间质−上皮) |
|---|---|
| 肉瘤 / rhabdoid(间质性) | **+0.03** |
| 上皮癌(结肠/乳腺/胰腺) | **−1.16** |

**Cohen's d = 1.72**,marker 覆盖 100% → **accept**(EMT 评分清晰分离间质性 vs 上皮性癌)。

- 治理:间质/上皮 panel 覆盖取 min,任一 <50% → **downgrade**;分组细胞不足 → abstain。测试 `test_emt_case.py`(4 passed)。

## 3. 诚实边界

- EMT score 是 **marker-based 相对量**(间质−上皮),**非**绝对 EMT 程度。
- **mcfarland 无 TGF-β 等 EMT 诱导扰动** → 本 case 是 **EMT 状态刻画**(哪类癌偏间质),**非扰动诱导的 EMT 转变**(已在 case note + boundary 标明)。
- 泛癌子集;marker/阈值为设定默认。
- 肉瘤按定义即间质来源,故 EMT 评分高——这是**可检验的生物学锚点**,验证评分有效性。**不训练模型**。
