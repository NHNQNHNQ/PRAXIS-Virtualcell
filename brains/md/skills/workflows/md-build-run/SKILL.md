---
name: md-build-run
description: 固化本地体系构建与运行模拟的方法。覆盖水溶液体系、细胞膜体系、小分子参数化和正式进入 GROMACS 运行前的验收。
host_env: praxis-md
---

# MD Build And Run Skill

## 目的

收到模拟任务后，优先给出一条本地可复现的构建与运行路线。背景故事和案例学习过程不放在这里，这里只保留以后重复任务还能直接复用的方法。

## 总判断

1. 先确定起始结构和体系类型。
2. 先让用户明确确认 `PDB` 或起始结构来源。
3. 如果是 `AlphaFold/AFDB` 蛋白且任务涉及膜环境，先确认取向和膜方向。
4. 先完成模拟环境配置与依赖补装，再进入任何本地体系构建。
5. 水溶液体系默认用本地 `gmx` 构建。
6. 细胞膜体系默认用 `PACKMOL-Memgen` 构建膜环境。
7. 小分子参数默认用本地 `AmberTools` 构建。
8. 只有 `grompp` 通过，才进入 `EM -> NVT -> NPT -> MD`。

## 依赖前置检查

- 如果任务需要 `gmx`、`PACKMOL-Memgen`、`AmberTools`、`PyMOL` 或 `MDAnalysis`，先检查本地是否存在。
- 本地缺失时，不要停在“环境没装”；直接按 `skills/workflows/md-dependency-bootstrap/SKILL.md` 的默认顺序补装并复查。
- 不要在环境未确认前就尝试替代性构建路线。

## 力场目录

### 默认力场包

- `docs/charmm36-feb2026_cgenff-5.0.ff.tgz`
- `docs/charmm36-jul2022.ff.tgz`

### 强制要求

- 必须显式指定力场目录，例如：

```bash
WORKDIR=/path/to/project
FORCEFIELD_DIR="$WORKDIR/charmm36-feb2026_cgenff-5.0.ff"
```

- 如果当前目录没有解压后的力场目录，就先从 `docs/` 解压：

```bash
tar -xzf /home/hipeson/mzy/Naruto-main/Naruto-main/docs/charmm36-feb2026_cgenff-5.0.ff.tgz -C "$WORKDIR"
```

- 不要把“系统默认力场目录”当作唯一来源。

## 水溶液体系

### 默认路线

```bash
gmx pdb2gmx -f protein.pdb -o processed.gro -p topol.top -ff charmm36-feb2026_cgenff-5.0 -water tip3p
gmx editconf -f processed.gro -o boxed.gro -bt cubic -d 1.2
gmx solvate -cp boxed.gro -o solv.gro -p topol.top
gmx grompp -f ions.mdp -c solv.gro -p topol.top -o ions.tpr
gmx genion -s ions.tpr -o ions.gro -p topol.top -neutral -conc 0.15 -pname NA -nname CL
```

### 规则

- 水溶液体系默认直接走本地 `gmx`，默认采用正方体盒子。
- 每一步后都检查坐标文件和 `[ molecules ]` 是否一致。
- 这是所有复杂体系前的默认基线路线。

## 细胞膜体系

### 默认路线

- 细胞膜体系默认用 `PACKMOL-Memgen` 构建，不默认手写整张膜。
- 起始蛋白如果来自 `AlphaFold/AFDB`，先确认取向，再交给后续膜环境构建。
- 基本步骤：
  - 让用户确认 `PDB` 或起始结构来源
  - 清理蛋白输入
  - 确认膜方向
  - 用 `PACKMOL-Memgen` 生成膜环境和初始坐标
  - 再进入本地 `GROMACS` 和 `CHARMM36` 路线

### 示例

```bash
packmol-memgen \
  --pdb protein_oriented.pdb \
  --lipids POPC \
  --dist 12 \
  --dist_wat 15 \
  --salt \
  --saltcon 0.15 \
  -o membrane_system
```

### 规则

- 如果是细胞膜体系，默认先构好膜环境，再做后续 `gmx` 处理。
- `PDB` 未确认前，不进入正式体系构建。
- `AlphaFold/AFDB` 蛋白未确认取向前，不进入膜环境构建。
- `PACKMOL-Memgen` 生成后，要继续检查残基命名、膜方向、离子条件和导出结构是否适合进入后续拓扑阶段。

## 小分子参数化

### 默认路线

- 小分子参数默认用本地 `AmberTools`。
- 常见工具链：`antechamber -> parmchk2 -> tleap/acpype -> GROMACS`

### 示例

```bash
antechamber -i ligand.sdf -fi sdf -o ligand.mol2 -fo mol2 -at gaff2 -c bcc -s 2
parmchk2 -i ligand.mol2 -f mol2 -o ligand.frcmod
```

### 规则

- 不依赖网页参数化。
- 参数生成后必须检查原子质量和 `atomtypes` 区块。
- 如果最后要混入 `CHARMM36` 体系，必须额外检查 include 顺序和兼容性。

## 正式进入 GROMACS 前的验收

### 最低标准

```bash
gmx grompp -f em.mdp -c system.gro -p topol.top -n index.ndx -o em.tpr
```

### 通过前不要做的事

- 不要先跑长时间 NVT 或 NPT。
- 不要先解释生物学意义。
- 不要把“文件已经生成”当作体系已经正确。

## 运行入口

- 具体命令模板、资源判断和 `gmx/gmx_mpi` 区分，统一交给 `skills/workflows/md-gromacs/SKILL.md`。

## 常见 fallback

- 膜体系持续报 `Unknown cmap torsion`：切到拆分拓扑后重组总体系。
- `tc-grps` 报错：重建干净 index。
- 混合力场崩溃：先检查原子质量和重复 `atomtypes`。

## 输出契约

```json
{
  "ok": true,
  "skill_id": "md-build-run",
  "result": {},
  "diagnostics": {
    "brain": "Naruto-main",
    "archetype": "generic"
  }
}
```
