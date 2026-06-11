---
case_id: md-adeb-rnd
sim_type: standard
domain: membrane_protein_md
target: "AdeB RND三聚体外排泵 (Resistance-Nodulation-Division)"
tools: [GROMACS, MDAnalysis, pytraj]
status: validated
schema_version: 1
source: agent_run
tags: [AdeB, RND外排泵, 三聚体, 构象不对称, 内Gate, 外Gate, 亚基协同, 膜蛋白, pytraj, MIC距离]
---

# AdeB RND三聚体构象动力学：三亚基协同性分析

- 领域: molecular_simulation
- 标签: AdeB, RND外排泵, 三聚体, 构象不对称, 内Gate, 外Gate, 亚基协同, 膜蛋白, pytraj, MIC距离

## 背景

用户要求计算AdeB RND（Resistance-Nodulation-Division）三聚体外排泵的500纳秒MD轨迹数据，要求进行链特异性构象分析。这是一个多链膜蛋白复合物构象动力学的中高级案例。

## 核心问题

用户要求计算AdeB RND（Resistance-Nodulation-Division）三聚体外排泵的500纳秒MD轨迹数据，要求进行链特异性构象分析。这是一个多链膜蛋白复合物构象动力学的中高级案例。

## 过程摘要

1. 时间序列：观察开闭动态。
2. 直方图：识别开放/闭合状态分布。
3. 百分位数：P50（中位数）、P5、P95等。
4. 三条链的Gate距离随时间是否呈现负相关？（一条开则另一条闭？）

## 结果与学到什么

- 第一，链特异性选择和距离计算。使用MDAnalysis分别选择PROA、PROB、PROC三条链，计算各链的Gate距离。确认pytraj PSF格式单位是Angstrom（÷10得nm）。
- 第二，内Gate距离分析。三条链的L137-F612（内Gate）距离：
- 关键发现：所有三条链的内Gate距离均>1.5nm（开放阈值），100%时间内完全开放。这与"内Gate是限速步骤"的传统假设矛盾。
- AdeB是AdeABC RND外排泵的转运蛋白组分，形成三聚体跨膜通道。结构特征：
