# 06 增强采样、CV 与版本兼容

## 核心规则

做膜体系增强采样时，先确认反应坐标的物理意义，再确认软件栈兼容；这两步都不能省。

## CV 与 PBC

- 膜体系做 `SMD`、伞形采样或元动力学时，必须确认反应坐标不会因 `PBC` 边界而失真。
- 如果初始位置和距离定义不合理，整个 `PMF` 都会失去物理意义。

## PLUMED 兼容性

- 进入 `PLUMED` 路线前，要先确认 `PLUMED`、`GROMACS`、MPI 与 GPU 环境是否兼容。
- 检查 PLUMED 支持：`gmx mdrun -plumed /dev/null` 若返回 `Unknown command-line option -plumed` 说明该 GROMACS 未编译 PLUMED 支持（conda-forge 预编译包无此支持，需源码打 patch）。
- `.53` 当前状态：`praxis-md-cuda`（gmx 2026.0）无 PLUMED；`praxis-md-plumed`（gmx 2024.2-conda_forge）PLUMED 库已装但 gmx 未 patch，元动力学需 ops 编译专用 gmx+plumed。

## 适用

- `pull geometry`
- 窗口提取
- `PMF` 路线
- 元动力学
- 带 `-plumed` 的增强采样

## 为什么

- `PBC` 边界是膜体系反应坐标失真的高频根源。
- 版本和编译方式不匹配时，命令层和运行层都会报错。

