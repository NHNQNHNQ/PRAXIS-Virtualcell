---
case_id: md-peptidoglycan-layer-pre-equilibration
sim_type: standard
domain: polymer_assembly_md
target: "肽聚糖层 (peptidoglycan, 非标准共价聚合体系)"
tools: [GROMACS, CHARMM36]
status: validated
schema_version: 1
source: agent_run
tags: [GROMACS, peptidoglycan, CHARMM36, topology-rebuild, explicit-parameters, solvation, GPU, index, grompp]
---

# 肽聚糖层非标准聚合体系预平衡复盘

- 领域: molecular_simulation
- 标签: GROMACS, peptidoglycan, CHARMM36, topology-rebuild, explicit-parameters, solvation, GPU, index, grompp

## 背景

目标是在本地 `/home/hipeson/MDAgent/taijutang` 中，对手工拼接得到的肽聚糖层进行加水、加盐和预平衡。起始输入不是标准蛋白或标准小分子，而是由最小重复单元 `LIG.itp` 和最终拼接坐标共同定义的非标准聚合体系。

## 核心问题

最终肽聚糖层不是多个独立 `LIG` 分子的简单堆叠，而是跨重复单元共价连接后的大片段。直接把最终坐标写成 `LIG x N` 会导致 `grompp` 失败。随后还出现了三类问题：

1. 跨单元连接引入缺失的 `bondtypes`、`angle/U-B types` 和 `dihedraltypes`
2. 原始本地 `charmm36.itp` 能支撑聚糖本体，但不自带可直接用于 `tip3p + NaCl` 的完整最小水离子定义
3. `index.ndx` 中实际存在的组名与 `mdp` 中 `tc-grps` 不一致，导致 `grompp` 先失败，随后 `mdrun` 再次报缺少 `.tpr`

## 过程摘要

1. 先从最终 PDB 的 `CONECT` 反推整层真实连通性，确认体系应表示为 6 个共价大片段，而不是若干独立 `LIG`。
2. 以最小重复单元拓扑为模板，生成单张片层的大分子拓扑 `PGSHEET.itp`，再把总体系写成 `PGSHEET 6`。
3. 对跨单元新增的缺失参数，按相似原子类型从本地 `charmm36.itp` 中选择近似模板，把缺失的键、角、Urey-Bradley 和二面角改写成显式参数，优先让体系先通过 `grompp`。
4. 不直接切回官方力场主目录，而是保留本地 `charmm36.itp` 作为聚糖本体参数底座；另外单独补 `water_ion_atomtypes.itp` 和 `nacl.itp`，以便本地体系继续 `solvate/genion`。
5. 在更紧凑的 `new/` 目录中复制必要文件，只沿实际存在富余的方向适度缩小盒子，从 `8.2 x 13.7 x 19.7 nm` 收紧到 `8.2 x 13.4 x 19.7 nm`。
6. 重新加水和加盐后，在 `new/` 中完成 `EM -> NVT -> NPT` 预平衡。
7. GPU 排查时，区分“GROMACS 二进制支持 CUDA”和“当前执行环境是否真的看得到 GPU 设备”。代理沙盒里 `gmx` 是 CUDA 版，但实际看不到设备；同一套输入在宿主机原生终端中可以正常以 `-gpu_id 0` 跑通。
8. 处理 `grompp` / `mdrun` 联动报错时，先修 `index.ndx` 与 `tc-grps` 组名不一致的问题，再继续 `mdrun`。

## 结果与学到什么

- 对于非标准聚糖聚合体系，首要任务不是立刻加水，而是先确认最终连通图，再决定总拓扑表示方式。
- 当目标是“先跑通预平衡”时，可接受基于相似原子类型的显式近似补参；但应在案例中明确这是可跑优先，而不是严格重新参数化终态。
- 如果保留本地 `charmm36.itp` 作为本体底座，水和离子最好采用最小兼容补丁，而不是粗暴切回另一套主力场目录。
- `tc-grps` 必须与 `index.ndx` 中实际组名逐字一致；否则 `grompp` 会先失败，后续 `mdrun` 缺少 `.tpr` 只是次生报错。
- 判断 GPU 问题时，要区分“命令模板错误”和“当前终端没有设备访问权”两种完全不同的故障来源。
- 本案例最终在 `new/` 目录成功完成 GPU 版预平衡，最后一步 `NPT` 成功运行 `100000` 步、`200 ps`。

## 关联案例

- `peptidoglycan-z3nm-graph-isomorphism-repair`：后续 z3nm 新基底 + 图同构修复 + tangju_A/F 药物插入，体系规模更大且发现了原子顺序与拓扑不一致的深层问题
