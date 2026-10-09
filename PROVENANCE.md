# Provenance

PRAXIS-virtualcell 派生自 PRAXIS-2。

- **Imported from**: PRAXIS-2 @ commit `b124d66` (import tag: `praxis2-import-b124d66`)
- **Import date**: 2026-06-11
- **Method**: `rsync`(精简复制),fresh `git init`(不保留 PRAXIS-2 git 历史;provenance 用本文件 + tag 记录)
- **Excluded on copy**: `.git/ .venv/ frontend/ 备案/ __pycache__/ .pytest_cache/ .ruff_cache/ *.egg-info/ ._* .DS_Store .gstack/`
- **Python package name**: 保持 `praxis2`(project name = `praxis-virtualcell`;不改 import 路径以免炸全仓)
- **Discipline brains**: 已移除 13 个通用学科脑(cell/crispr/cryo/dock/drug/enzyme/immuno/md/microbiome/omics/pharma/protein/synth),替换为单一 `virtualcell` 大脑(metadata + AGENT-PROMPT + 1 case + 1 rule + skill `perturbation_predict`;见 `brains/INDEX.md`);`_common` 共享基础设施保留。`DISCIPLINE_SLUGS=["virtualcell"]`。
- **Baseline**: 见 `BASELINE.md`。基线1(复制后)2051 passed / 24 pre-existing failed;基线2(去脑+补脑后)1099 passed / 14 pre-existing failed / 0 去脑引入失败(~48 个去脑失败全部靠重写修复)。
- **Tag**: `praxis2-import-b124d66`
- **Upstream remote**: `git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git`
