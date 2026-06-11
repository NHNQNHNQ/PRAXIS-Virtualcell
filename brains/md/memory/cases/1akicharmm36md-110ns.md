---
case_id: md-1akicharmm36md-110ns
sim_type: standard
domain: soluble_protein_md
target: "Lysozyme 1AKI (鸡蛋白溶菌酶, CHARMM36)"
tools: [GROMACS, CHARMM36]
status: validated
schema_version: 1
source: benchmark
tags: [GROMACS, CHARMM36, MD, 溶菌酶, 1AKI, PBC校正, PCA, 自由能]
---

# 1AKI溶菌酶CHARMM36力场MD模拟 - 110ns成品分析

- 领域: molecular_simulation
- 标签: GROMACS, CHARMM36, MD, 溶菌酶, 1AKI, PBC校正, PCA, 自由能

## 背景

用户提出了一个经典的GROMACS分子动力学入门任务，要求使用CHARMM36力场对1AKI溶菌酶蛋白质进行110纳秒生产MD模拟，并完成完整的轨迹分析。这是分子动力学模拟领域最基础的基准案例之一。

## 核心问题

用户提出了一个经典的GROMACS分子动力学入门任务，要求使用CHARMM36力场对1AKI溶菌酶蛋白质进行110纳秒生产MD模拟，并完成完整的轨迹分析。这是分子动力学模拟领域最基础的基准案例之一。

## 过程摘要

1. 能量最小化（EM）：消除原子碰撞和不良接触。判断标准：Fmax < 1000 kJ/mol/nm。典型步数：5000-10000步。
2. NVT平衡（100ps, 303K）：使用v-rescale控温，固定蛋白位置（POSRES），让水分子和离子松弛。
3. NPT平衡（100ps, 1atm）：使用C-rescale或Parrinello-Rahman控压，让体系达到正确密度。
4. 生产MD（110ns）：每10ps输出压缩坐标（nstxout=10000），共约11000帧。

## 结果与学到什么

- 第一，GROMACS版本问题成功解决。通过将gmx路径从/opt/software/gmx2021/bin/gmx切换到/opt/packages/gromacs-2025.3/bulid/bin/gmx，解决了libmkl缺失的问题。新版本编译时链接了Intel MKL的正确版本。
- 第二，模拟轨迹确认。110ns生产MD，每10ps输出压缩坐标（.xtc），共约11000帧。模拟条件：温度303K，压力1atm，步长2fs。GPU加速配置下通量达到约340 ns/day。
- 第三，PBC校正执行。Agent首先对轨迹进行PBC校正：
- 本次模拟使用CHARMM36力场对1AKI鸡蛋白溶菌酶进行110纳秒成品分子动力学模拟。模拟条件：温度303K，压力1atm，步长2fs。采用了单 GPU + 18 线程的规范 GROMACS 配置，通量达到约340 ns/day。
