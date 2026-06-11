---
case_id: md-mtr1-popc
sim_type: standard
domain: membrane_protein_md
target: "MTR1-POPC 膜蛋白体系 (Melatonin Receptor)"
tools: [GROMACS, CHARMM36]
status: validated
schema_version: 1
source: agent_run
tags: [GROMACS, CHARMM36, 膜蛋白, POPC, 拓扑重组, grompp, index]
---

# MTR1-POPC 膜蛋白体系本地构建复盘

- 领域: membrane_protein_md
- 标签: GROMACS, CHARMM36, 膜蛋白, POPC, 拓扑重组, grompp, index

## 背景

这个主题原先有两张近似案例卡：一张强调“拆分拓扑重组流程”，一张强调“为什么不能继续硬修整体系输入”。合并后保留完整脉络：从混合大体系反复失败，到切换为稳定的本地 fallback 路线。

## 核心问题

本地构建 MTR1-POPC 膜体系时，直接对蛋白加整膜混合输入运行 `pdb2gmx` 和 `grompp` 持续失败，并伴随 `Unknown cmap torsion`、残基名错位和链边界异常，需要找到一条可复用、可验收、可继续溶剂化与离子化的稳定流程。

## 过程摘要

1. 先验证力场包中真实包含 `POPC` 模板，避免把模板缺失和输入错误混为一谈。
2. 直接混合体系失败后，不再继续硬修整张混合结构。
3. 改为蛋白单独建拓扑、单脂质单独建拓扑，再按实际分子数重组总拓扑与坐标。
4. 先追求 `grompp` 自洽，再继续 `solvate`、`genion` 和平衡阶段。
5. 平衡前重建干净 `index`，只保留 `Protein`、`Membrane`、`Water_and_ions` 三组。
6. 额外记录运行管理教训：同名前缀并发会污染输出文件。

## 结果与学到什么

- 拆分拓扑后，蛋白加 87 个 POPC 的未溶剂化体系可以通过 `grompp`。
- 继续加水和加离子后，最终体系再次通过 `grompp`，说明拓扑与坐标自洽。
- 膜体系里“边界解析失败”比“力场缺模板”更常见。
- `Protein / Membrane / Water_and_ions` 的干净 `index` 是后续平衡成功的关键。
- 同名前缀任务并发会污染输出文件，这属于应长期保留的案例教训。

