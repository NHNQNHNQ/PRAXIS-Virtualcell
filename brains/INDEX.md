# PRAXIS-virtualcell — Agent Brains 索引

> 案例学习大脑:cases / rules / skills / prompts / memory。
> 从 PRAXIS-2(commit `b124d66`)复制改造:**已移除 13 个通用学科大脑**(cell/crispr/cryo/dock/drug/enzyme/immuno/md/microbiome/omics/pharma/protein/synth),改为单一虚拟细胞大脑。
> 物种分库(human / mouse / E.coli / yeast 等)自 Week 5 起填入 `virtualcell` brain。

## 大脑总览

| brain | cases | rules | skills | 说明 |
|---|---|---|---|---|
| virtualcell | 1(种子) | 1(bootstrap 先验) | 0 | 虚拟细胞多物种多任务预测(perturbation / drug / growth / essentiality);Week 3/5 起扩充 |
| _common | — | 1 | 1 | 跨学科共享规则/技能(基础设施,保留) |

`DISCIPLINE_SLUGS = ["virtualcell"]`(单源,见 `praxis2/brains/migrate.py`;与 `_SLUG_CASE_HINTS` / `loader._SLUG_KEYWORDS` / `server.app._AGENT_META` 四源对齐,由 `tests/test_correctness_slug_canonical.py` 锁)。
