---
name: md-dependency-bootstrap
description: 模拟与分析依赖自检和自动安装规范。任务需要 GROMACS、PACKMOL-Memgen、AmberTools、PyMOL 或 MDAnalysis 而本地缺失时调用。
host_env: praxis-md
---

# MD Dependency Bootstrap Skill

## 目的

在进入模拟构建、正式运行或轨迹分析前，先检查本地是否已有必需工具。只要任务确实需要，而本地又没有，就自动补装，不要假装“环境已经齐全”。

## 适用

- 需要 `gmx` 或 `gmx_mpi` 跑构建、`grompp`、`mdrun`、分析
- 需要 `PACKMOL-Memgen` 构建膜体系
- 需要 `AmberTools` 做小分子参数化
- 需要 `PyMOL` 画结构图
- 需要 `MDAnalysis` 做 Python 轨迹分析

## 总原则

1. 先判断任务需要哪些工具。
2. 再检查本地有没有。
3. 缺失时立即补装，再继续任务。
4. 不为“可能会用到”而提前装一整套无关软件。
5. 尽量优先装到当前用户可控环境，不优先走系统级破坏性安装。

## 默认检查项

```bash
which gmx || true
which gmx_mpi || true
which packmol-memgen || true
which antechamber || true
which parmchk2 || true
which pymol || true
python3 -c "import MDAnalysis; print(MDAnalysis.__version__)" || true
```

## 缺失时的默认安装顺序

### 第一选择

- 优先使用当前用户可写的 `conda` 或 `mamba` 环境。
- 推荐环境名：`openclaw-md`
- 如果 `mamba` 可用，优先用 `mamba`，没有再用 `conda`。

### 第二选择

- 如果本地没有 `conda/mamba`，再考虑 `apt`。
- 只有在明确需要系统级安装且当前机器允许时，才使用 `sudo apt install`。

### 第三选择

- 纯 Python 包优先用 `python3 -m pip install --user`。
- 不要把需要复杂二进制依赖的软件优先丢给 `pip`。

## 推荐环境准备

### 如果还没有专门环境

```bash
conda create -y -n openclaw-md python=3.11
conda activate openclaw-md
```

### 如果用 mamba

```bash
mamba create -y -n openclaw-md python=3.11
mamba activate openclaw-md
```

## GROMACS

### 什么时候需要

- 只要要做 `pdb2gmx`
- 要做 `grompp`
- 要做 `mdrun`
- 要做 `trjconv`、`rms`、`rmsf`、`hbond` 等分析

### 检查

```bash
which gmx
gmx --version
which gmx_mpi
gmx_mpi --version
```

### 缺失时默认安装

优先：

```bash
mamba install -y -n openclaw-md -c conda-forge gromacs
```

或：

```bash
conda install -y -n openclaw-md -c conda-forge gromacs
```

如果只能走系统包：

```bash
sudo apt update
sudo apt install -y gromacs
```

### 安装后复查

```bash
gmx --version
which gmx
```

## PACKMOL-Memgen

### 什么时候需要

- 膜蛋白或跨膜小分子体系需要本地构膜

### 检查

```bash
which packmol-memgen
packmol-memgen --help
```

### 缺失时默认安装

优先通过 `AmberTools` 环境补齐，因为 `PACKMOL-Memgen` 通常和 AmberTools 工作流一起提供：

```bash
mamba install -y -n openclaw-md -c conda-forge ambertools
```

或：

```bash
conda install -y -n openclaw-md -c conda-forge ambertools
```

如果装完还是找不到，先检查环境是否已激活，再重新查：

```bash
conda run -n openclaw-md packmol-memgen --help
```

### 安装后复查

```bash
which packmol-memgen || conda run -n openclaw-md which packmol-memgen
packmol-memgen --help || conda run -n openclaw-md packmol-memgen --help
```

## AmberTools

### 什么时候需要

- 小分子参数化
- 需要 `antechamber`
- 需要 `parmchk2`
- 需要 `tleap`

### 检查

```bash
which antechamber
which parmchk2
which tleap
antechamber -h | head
```

### 缺失时默认安装

```bash
mamba install -y -n openclaw-md -c conda-forge ambertools
```

或：

```bash
conda install -y -n openclaw-md -c conda-forge ambertools
```

### 安装后复查

```bash
conda run -n openclaw-md antechamber -h | head
conda run -n openclaw-md parmchk2 -h | head
```

## PyMOL

### 什么时候需要

- 需要渲染结构图
- 需要检查配体、残基、链和构象展示

### 检查

```bash
which pymol
pymol -cq || true
```

### 缺失时默认安装

优先开源版：

```bash
mamba install -y -n openclaw-md -c conda-forge pymol-open-source
```

或：

```bash
conda install -y -n openclaw-md -c conda-forge pymol-open-source
```

### 安装后复查

```bash
conda run -n openclaw-md pymol -cq
```

## MDAnalysis

### 什么时候需要

- 需要写 Python 轨迹分析脚本
- 需要批量处理 `xtc/trr/gro/pdb`
- 需要比 `gmx` 命令更灵活的分析逻辑

### 检查

```bash
python3 -c "import MDAnalysis; print(MDAnalysis.__version__)"
```

### 缺失时默认安装

优先装到当前分析环境：

```bash
python3 -m pip install --user MDAnalysis
```

如果分析统一走 `openclaw-md` 环境：

```bash
mamba install -y -n openclaw-md -c conda-forge mdanalysis
```

或：

```bash
conda install -y -n openclaw-md -c conda-forge mdanalysis
```

### 安装后复查

```bash
python3 -c "import MDAnalysis; print(MDAnalysis.__version__)"
```

## 自动安装触发规则

- 任务要跑 MD，而 `gmx/gmx_mpi` 缺失：立即安装 `GROMACS`
- 任务要本地构膜，而 `packmol-memgen` 缺失：立即安装 `AmberTools` 并复查 `PACKMOL-Memgen`
- 任务要做小分子参数化，而 `antechamber/parmchk2` 缺失：立即安装 `AmberTools`
- 任务要画结构图，而 `pymol` 缺失：立即安装 `PyMOL`
- 任务要跑 Python 轨迹分析，而 `MDAnalysis` import 失败：立即安装 `MDAnalysis`

## 执行时的默认行为

- 缺工具时，不要只报“本地没有安装”然后停住。
- 如果安装不需要额外决策，就直接执行安装。
- 如果涉及 `sudo`、系统包冲突或环境选择不明确，再向用户确认。
- 安装后必须立刻复查版本和可执行路径。
- 复查失败时，不要假装环境已经可用。
- 在环境未配置完成前，不要跳去其他体系构建办法凑结果。

## 不要做的事

- 不要因为膜体系就引导到 `CHARMM-GUI`
- 不要把网页工具当默认替代方案
- 不要混用多个不同环境却不说明当前实际使用的是哪个
- 不要安装完不验证
- 不要绕过环境检查直接开始 `pdb2gmx`、`packmol-memgen` 或参数化

## 交接格式

完成依赖补装后，至少明确报出：

- 哪些工具原本缺失
- 实际安装了什么
- 装到了哪个环境
- 复查命令是否通过
- 后续任务应使用哪个 `gmx`、`packmol-memgen`、`antechamber`、`pymol` 或 Python 环境

## 输出契约

```json
{
  "ok": true,
  "skill_id": "md-dependency-bootstrap",
  "result": {},
  "diagnostics": {
    "brain": "Naruto-main",
    "archetype": "generic"
  }
}
```
