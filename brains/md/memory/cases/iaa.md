---
case_id: md-iaa
sim_type: umbrella_sampling
domain: membrane_permeation_md
target: "IAA (Indole-3-acetic acid, 吲哚乙酸) 跨磷脂膜"
tools: [GROMACS, WHAM]
status: validated
schema_version: 1
source: agent_run
tags: [IAA, 吲哚乙酸, 血脑屏障, BBB通透性, 伞形采样, Umbrella Sampling, WHAM, 膜通透性, 肠-脑轴, 分子力学]
---

# 微生物代谢物IAA血脑屏障通透性：伞形采样研究

- 领域: free_energy_sampling
- 标签: IAA, 吲哚乙酸, 血脑屏障, BBB通透性, 伞形采样, Umbrella Sampling, WHAM, 膜通透性, 肠-脑轴, 分子力学

## 背景

用户需要针对IAA（Indole-3-acetic acid，吲哚乙酸）分子穿越磷脂膜的伞形采样自行运行模拟生成轨迹，再计算其血脑屏障（BBB）通透性。这是一个物理化学、生物学和分子模拟交叉的综合性案例。

## 核心问题

用户需要针对IAA（Indole-3-acetic acid，吲哚乙酸）分子穿越磷脂膜的伞形采样自行运行模拟生成轨迹，再计算其血脑屏障（BBB）通透性。这是一个物理化学、生物学和分子模拟交叉的综合性案例。

## 过程摘要

1. 最低点位置：代表最稳定的位置（对于带电分子，通常在膜头基层附近）。
2. 最高点位置：代表能量最大点（通常在膜疏水核心中心）。
3. 跨膜能垒：从一端水相到另一端水相的ΔG。
4. 斜率变化：反映电荷与膜疏水性的相互作用强度。

## 结果与学到什么

- 第一，PMF曲线重建。使用WHAM方法合并各窗口采样数据，重建沿Z轴（膜法向）的自由能曲线。
- 最低点位置：z=1.79nm（膜头基层，细胞外侧）。
- 最高点位置：膜中心（疏水核心）。
- 吲哚乙酸（IAA，分子式C13H16N2O2，分子量175.19Da）是色氨酸的微生物代谢产物。在生理pH 7.4条件下，羧基（pKa=4.8）完全去质子化，带-2电荷（双阴离子）。这使IAA成为极性分子，难以通过被动扩散跨越脂质双分子层。
