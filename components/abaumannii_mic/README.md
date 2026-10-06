# 鲍曼不动杆菌直接 MIC 辅助模型

本组件从原 `Ab-虚拟细胞世界模型/abaumannii-world-model` 中提取分子结构 → MIC 的训练、清洗和推理代码。保留原 `DirectMICBaseline` 参数结构与 Morgan 半径 2、1024 位、含手性特征；不调用细胞状态、扰动或世界模型，不输出蛋白靶点和杀菌率。

这是辅助评分工具，作用范围为鲍曼不动杆菌物种层面的 MIC。现有模型不输入菌株、基因组或培养条件。MIC 分布宽度未经外部校准，不能解释为临床置信区间。单个模型依据冻结划分训练，导入的模型没有用全部数据重新拟合。

## 数据和版本

导入的是 **2026-09-13 trained-v2 交付包**中的 12 个直接 MIC 权重：compound/scaffold/study/isolate × seeds 17/42/2026。对应 **v3** 清洗和划分有 12,349 条测量、5,807 个结构母体、488 篇来源文献。8,671 条菌株身份未解析。交付包名称中的 v2 与其中 MIC 划分的 v3 是不同版本层次。

2026-09-23 SyntheMol 评估使用 seeds 17/42/314159，其中 314159 权重目前仅在原服务器。本次没有复制该服务器权重，也没有重训或把旧权重冒充最新模型。历史 SyntheMol 报告保留在 `reports/antibacterial/synthemol/`。本组件的真实推理复现报告单独存放在 `reports/antibacterial/direct_mic/`。

仓库数据在 `data/antibacterial/abaumannii/{curated,splits,raw}`；本地权重在 `models/abaumannii/direct_mic/`。清洗表保留原 `source_file` 路径，表示上游获取记录；上游原件没有包含在 trained-v2 包中，不应把该列当作当前仓库可读文件。选择性提取文件、字节数和 SHA-256 见 `reports/antibacterial/direct_mic/migration_manifest.json`；权重元数据见 `artifact_manifest.json`。

## 运行

从仓库根安装 `python -m pip install -e components/abaumannii_mic`，或设置 `PYTHONPATH=components/abaumannii_mic/src`。Python 至少 3.11，推理需要 PyTorch、RDKit、NumPy、Pandas。

```bash
python -m abwm predict \
  --input reports/antibacterial/direct_mic/examples/direct_mic_input.json \
  --model-root models/abaumannii/direct_mic --seed 42 --scheme compound \
  --output /tmp/ab_direct_mic.json
```

输入仅接受 `task=mic`、`model=direct`、`smiles`。`--scheme` 用于复现不同冻结划分模型，默认 compound。程序明确拒绝 world/state/target 和菌株输入；不接受未来组学、真实 MIC 或由目标 MIC 定义的条件。

`curate --data-root PATH` 只清洗 PATH 下的 ChEMBL 原件；`acquire --data-root PATH` 显式获取 ChEMBL MIC 并保存来源记录。本次迁移没有运行获取。已有冻结划分禁止原位覆盖。若需实验训练，`train --data-root PATH --model-root NEW_PATH --output-root NEW_PATH` 只训练 direct MIC，要求新的输出目录，不覆盖迁入的历史模型。

## 来源与许可

- 源代码来自用户拥有的原 abwm 项目；原子项目没有独立 LICENSE。本次纳入 PRAXIS 主仓库代码许可。第三方数据和模型的许可分别保留，不能由代码许可替代。
- ChEMBL 37 数据来自 EMBL-EBI ChEMBL API，物种 target `CHEMBL614425`、taxon 470；原获取清单标记 **CC BY-SA 3.0**。清洗表、来源关联、衍生标签和 MIC 预测结果保留该数据归属及许可证要求。见 [ChEMBL](https://www.ebi.ac.uk/chembl/)、[CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/)。清洗排除、单位转换、结构归组和 v3 划分为本项目处理；清洗数据没有被改写成合成标签。
- PubChem 提供固定药物结构；清单标记 `PubChem public data; retain provenance`，CID、结构来源及获取事件保留在 `curated/drugs.json` 和 `raw/manifest.jsonl`。
- Abaucin 生长筛选来自 Liu et al., *Nature Chemical Biology* (2023), DOI [10.1038/s41589-023-01349-8](https://doi.org/10.1038/s41589-023-01349-8)，附件 MOESM3/MOESM4；原始 Excel 和导出的实测生长表仅本地保留，未在本地确认可再分发许可。保留工作表、Excel 行号和旧模型预选背景；`Activity` 预测列不作为实测标签。
- 直接 MIC 权重是原 abwm 训练产物，本次从原交付包选择提取；本地保留，不上传 Git。没有导入世界模型权重。

含原服务器位置的下载恢复资料及原始运行环境清单位于 `local/server_recovery/ab_world_model/`，仅本地保存。
