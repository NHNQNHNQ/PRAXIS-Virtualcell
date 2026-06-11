---
name: md-gromacs
description: GROMACS 命令与排错规范。覆盖 gmx/gmx_mpi 区分、GPU/CPU 资源判断、标准 mdrun 模板、续跑和常见报错处理。
host_env: praxis-md
---

# GROMACS Command And Error Skill

## 一句话原则

先判断 `gmx` 还是 `gmx_mpi`，再看 GPU 和 CPU 空闲情况，最后选择合适模板；默认一块 GPU 跑一个任务，通常配 18 个 CPU 线程。

## 先检查环境

```bash
which gmx
which gmx_mpi
gmx --version
gmx_mpi --version
nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv,noheader
nproc
ps -ef | grep mdrun
```

## GPU 可见性诊断

- `gmx --version` 里看到 `GPU support: CUDA` 只说明二进制支持 GPU，不代表当前终端一定能访问设备。
- 如果 `gmx mdrun -gpu_id 0` 报 `0 detected device(s)`，先检查当前 shell 是否真的可见 GPU 设备，再决定是否切换到宿主机终端或 CPU fallback。
- 最小检查命令：

```bash
gmx mdrun -deffnm em -nsteps 0 -ntmpi 1 -ntomp 18 -gpu_id 0 -pin on -pinoffset 0
ls -l /dev/nvidia* /dev/dri
nvidia-smi -L
```

## 资源判断

- 默认 1 个模拟任务占 1 块 GPU。
- 默认给 18 个 CPU 线程，再按空闲情况调整。
- 不要在同一块 GPU 上并发多个生产任务。
- 同一个 `deffnm` 绝不能并发运行两个 `mdrun`。

## 普通 gmx 模板

### 单 GPU

```bash
gmx mdrun -deffnm md -ntmpi 1 -ntomp 18 -gpu_id 0 -nb gpu -pin on -pinoffset 0
```

### CPU only

```bash
gmx mdrun -deffnm md -ntmpi 1 -ntomp 18 -nb cpu -pme cpu -pin on -pinoffset 0
```

### 双 GPU 双任务

```bash
nohup gmx mdrun -deffnm jobA -ntmpi 1 -ntomp 18 -gpu_id 0 -nb gpu -pin on -pinoffset 0 &
nohup gmx mdrun -deffnm jobB -ntmpi 1 -ntomp 18 -gpu_id 1 -nb gpu -pin on -pinoffset 18 &
```

## gmx_mpi 模板

```bash
mpirun -np 1 gmx_mpi mdrun -deffnm md -ntomp 18 -gpu_id 0 -pin on
```

### 规则

- `gmx_mpi` 由 `mpirun` 或 `mpiexec` 控制 rank。
- `gmx_mpi` 不要机械再写 `-ntmpi 1`。
- 真正要不要用 `gmx_mpi`，取决于当前安装和环境，而不是习惯。

## 标准阶段命令

```bash
gmx grompp -f step6.0_minimization.mdp -c step5_input.gro -r step5_input.gro -p topol.top -o em.tpr
gmx mdrun -deffnm em -ntmpi 1 -ntomp 18 -gpu_id 0 -nb gpu -pin on -pinoffset 0

gmx grompp -f step6.1_equilibration.mdp -c em.gro -r em.gro -n index.ndx -p topol.top -o eq1.tpr
gmx mdrun -deffnm eq1 -ntmpi 1 -ntomp 18 -gpu_id 0 -nb gpu -pin on -pinoffset 0

gmx grompp -f step7_production.mdp -c eq6.gro -r eq6.gro -n index.ndx -p topol.top -o md.tpr
nohup gmx mdrun -deffnm md -ntmpi 1 -ntomp 18 -gpu_id 0 -nb gpu -pin on -pinoffset 0 &
```

## 续跑与延长

```bash
gmx mdrun -deffnm md -cpi md.cpt
gmx convert-tpr -s md.tpr -extend 100000 -o md_extend.tpr
gmx mdrun -deffnm md_extend -cpi md.cpt
```

## 分析前先做 PBC 校正

```bash
printf '1\n0\n' | gmx trjconv -s md.tpr -f md.xtc -o md_noPBC.xtc -pbc mol -center
```

## 常见报错处理

### Unknown cmap torsion

- 优先怀疑整张混合膜输入的边界解析失败。
- 不要继续硬修整张 PDB。
- 切换到“拆分拓扑后重组总体系”。

### Invalid order for directive atomtypes

- 小分子 `itp` 里可能有重复 `[ atomtypes ]`。
- 统一原子类型定义位置并修正 include 顺序。

### atoms are not part of any of the T-Coupling groups

- 优先怀疑 `index.ndx` 里有脏组或覆盖不全。
- 重建只包含 `Protein`、`Membrane`、`Water_and_ions` 的干净组。

### Group referenced in the .mdp file was not found in the index file

- `tc-grps`、`comm-grps` 等组名必须和 `index.ndx` 中的真实组名逐字一致。
- 如果 `index` 里实际组名是 `Bath`，就不要在 `mdp` 里写成 `SOD_CLA_Water`。
- 先修正 `mdp` 或重建 `index`，再重新 `grompp`。

### mdrun 报缺少 topol.tpr 或 <deffnm>.tpr

- 这通常不是 `mdrun` 本身的问题，而是前一步 `grompp` 没成功。
- 先检查最近一次 `grompp` 是否真的生成了目标 `.tpr`，再继续启动。

### libmkl_intel_lp64.so not found

- 直接切换到较新的 `gmx` 版本。

### 没有轨迹文件

- 检查 `mdp` 里是否明确设置 `nstxout-compressed`。
- 没有可分析轨迹时，不要假装进入分析阶段。

## 运行前检查清单

- 已确认使用 `gmx` 还是 `gmx_mpi`
- 已确认 GPU 和 CPU 空闲情况
- 已确认 `topol.top`、`itp`、`mdp`、`index.ndx` 齐全
- 已确认 `grompp` 通过
- 已确认没有同名前缀任务在跑

## 输出契约

```json
{
  "ok": true,
  "skill_id": "md-gromacs",
  "result": {},
  "diagnostics": {
    "brain": "Naruto-main",
    "archetype": "generic"
  }
}
```
