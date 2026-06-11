---
name: environment-setup
description: 检测、安装、校验 PRAXIS-Enzyme 与 PRAXIS-MD 链路所需的全部外部二进制与 Python 依赖。Hard Rule 5 触发后的标准起手——先跑诊断脚本，缺什么补什么；按"sequence/structure/stability/cheminformatics/MD"五大类分级安装，每条命令都给 macOS / Linux 双平台版本，每装完一个都必须复查二进制与版本。PyRosetta 与 PACKMOL-Memgen 需学术许可,给出申请路径(PyRosetta 通过私有 conda channel 装);其余优先 conda/mamba。禁止以 pip 替代二进制安装、禁止 sudo 跨用户改系统 Python、禁止跳过 DSSP/mkdssp 这类隐性依赖。
---

# Environment Setup Skill

## 一句话原则
**先诊断、再安装、装完必复查**。任何"假装它装了"的捷径（symlink 假二进制、用 simulated 模式糊弄真任务、`pip install` 替代真二进制）都会在 Hard Rule 5 与 Hard Rule 7 上被拦截。

## 适用阶段
Hard Rule 5 触发的环境检查阶段；新机器初始化；工程任务前的兜底；把 simulated PyRosetta 切换到真 PyRosetta 时的强制校验。

## 第一步：跑诊断脚本（必须）

```bash
bash <<'EOF'
echo "=== Tier 1: PRAXIS-Enzyme core ==="
for bin in mmseqs foldseek pyrosetta mkdssp dssp; do
  printf "%-10s : " "$bin"; (which $bin && $bin --version 2>&1 | head -1) || echo "MISSING"
done
echo "=== Python core ==="
python -c "import Bio,rdkit,numpy,scipy,pandas; print('biopython',Bio.__version__,'rdkit',rdkit.__version__)" 2>&1
python -c "import biotite, MDAnalysis" 2>&1 | head -2
echo "=== Tier 3: PRAXIS-MD (optional) ==="
for bin in gmx packmol packmol-memgen tleap antechamber pymol plumed; do
  printf "%-15s : " "$bin"; which $bin || echo "MISSING"
done
EOF
```

把输出贴回上下文，再决定补装哪几个。**禁止凭印象判断"应该装了"。**

---

## Tier 1 — PRAXIS-Enzyme 核心（必装）

### 1. MMseqs2（序列相似性 / 家族检索）
**用途**：`indices/mmseqs2/` 的家族通道、新蛋白的 family hit。

```bash
# macOS（推荐）
brew install mmseqs2
# 或 conda
conda install -c bioconda mmseqs2

# Linux
conda install -c bioconda mmseqs2
# 或下编译好的静态二进制
wget https://mmseqs.com/latest/mmseqs-linux-avx2.tar.gz
tar xvfz mmseqs-linux-avx2.tar.gz && export PATH=$PWD/mmseqs/bin:$PATH
```
**校验**：`mmseqs version` 应返回 14+；`mmseqs easy-search --help` 不报错。

### 2. Foldseek（结构相似性）
**用途**：`indices/foldseek/` 的结构通道、跨家族结构邻居检索。

```bash
# macOS
brew install foldseek
# 或 conda
conda install -c bioconda foldseek

# Linux
conda install -c bioconda foldseek
# 或静态二进制
wget https://mmseqs.com/foldseek/foldseek-linux-avx2.tar.gz
tar xvfz foldseek-linux-avx2.tar.gz && export PATH=$PWD/foldseek/bin:$PATH
```
**校验**：`foldseek version` ≥ 8；`foldseek easy-search --help` 不报错。

### 3. PyRosetta(稳定性 ΔΔG)—— 学术许可,conda 装包
**用途**:`pyrosetta-stability-scan` skill 的真实 Python API;缺失则全程必须打 simulated 标签。
**staging `.53` 状态**:已在 `antibody` env 装好,直接 `conda activate antibody` 即用。

```bash
# Linux / macOS 通用步骤(若新机器)
# 1. 在 https://www.pyrosetta.org/downloads 申请 academic license,拿到 PyRosetta channel 密码
# 2. 用 conda 装(强烈不要从源码编译,极慢)
conda create -n antibody -c https://USERNAME:PASSWORD@conda.graylab.jhu.edu pyrosetta python=3.11
conda activate antibody

# 3. 验证
python -c "import pyrosetta; pyrosetta.init(); print(pyrosetta.__version__)"
```
**校验**:`python -c "import pyrosetta; pyrosetta.init(); print(pyrosetta.__version__)"` 输出版本号(应 ≥ 2024.x)。
**踩坑**:
- PyRosetta 是纯 Python wheel,**不需 rotabase.txt**(那是 FoldX 的依赖)。
- `pyrosetta.init()` 第一次跑会下载 Rosetta database(~1 GB),网慢的机器加 `-mute all` 减日志。
- 多核扫描用 `pyrosetta.distributed.cluster.PyRosettaCluster` 或 `pmut_scan_parallel`,推荐 ≥ 16 核。

### 4. RDKit（底物 fingerprint）
```bash
# 强烈推荐 conda（pip 装的 wheel 在 macOS 上常缺 boost）
conda install -c conda-forge rdkit
# pip 兜底（大多数情况能用）
pip install rdkit
```
**校验**：`python -c "from rdkit import Chem; print(Chem.MolFromSmiles('CCO'))"`。

### 5. BioPython（UniProt / PDB 解析）
```bash
pip install biopython
# 或
conda install -c conda-forge biopython
```
**校验**：`python -c "import Bio; print(Bio.__version__)"` ≥ 1.83。

### 6. DSSP / mkdssp(二级结构标注)
**用途**:RSA 标注、二级结构提取(PyRosetta 自带 DSSP 算法,但外部 mkdssp 输出更标准、可被其他工具消费)。

```bash
# macOS
brew install brewsci/bio/dssp
# Linux
conda install -c salilab dssp        # 老版
# 或
sudo apt-get install dssp            # Ubuntu
# 新版命名为 mkdssp
conda install -c bioconda mkdssp
```
**校验**：`mkdssp --version || dssp --version`。
**踩坑**:部分下游脚本写死 `dssp` 命名而非 `mkdssp`,符号链接补上:`ln -s $(which mkdssp) /usr/local/bin/dssp`。

---

## Tier 2 — 推荐（高频但非阻塞）

### 7. Biotite（结构操作 / 序列对齐）
```bash
pip install biotite
```
**校验**：`python -c "import biotite.structure.io.pdbx as p"`。

### 8. PyMOL（无 GUI / CLI 模式）
```bash
# macOS / Linux 都用 conda 最稳
conda install -c conda-forge pymol-open-source
# 校验
pymol -cq -d "print(cmd.get_version())"
```

### 9. HMMER（家族 profile 搜索）
```bash
# macOS
brew install hmmer
# Linux
conda install -c bioconda hmmer
```

### 10. BLAST+（兜底序列搜索）
```bash
# macOS
brew install blast
# Linux
conda install -c bioconda blast
```

---

## Python 包管理器层

### conda / mamba / micromamba
**强烈建议 mamba 或 micromamba**，比 conda 快一个量级。

```bash
# macOS（推荐 micromamba，比 mamba 还轻）
brew install micromamba
micromamba shell init -s zsh -p ~/micromamba
exec zsh

# Linux
"${SHELL}" <(curl -L micro.mamba.pm/install.sh)
```

### uv（现代 Python 包管理）
作为 pip 替代，速度快、依赖解析强。
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# PRAXIS-Enzyme 一键起
cd /Volumes/T7/EnzymeAgent
uv venv && source .venv/bin/activate
uv pip install -e .
```

### 项目自身 pip 依赖
```bash
cd /Volumes/T7/EnzymeAgent
pip install -e .                # 装 pyproject.toml 声明的全部
pip install -e ".[dev]"         # 含 pytest / ruff / ipython
```

---

## Tier 3 — PRAXIS-MD 链路（可选，需要时再装）

> **说明**：PRAXIS-Enzyme 主线**不依赖** MD 工具；只有当案例涉及"突变后做 MD relaxation 校验"或与 PRAXIS-MD 协作时才需要。

### 11. GROMACS
```bash
# macOS（推荐 conda）
conda install -c bioconda gromacs
# 或 brew
brew install gromacs

# Linux（conda 最省心）
conda install -c bioconda gromacs

# 源码编译（需 GPU / 自定义优化时）
wget https://ftp.gromacs.org/pub/gromacs/gromacs-2024.tar.gz
tar xfz gromacs-2024.tar.gz && cd gromacs-2024
mkdir build && cd build
cmake .. -DGMX_BUILD_OWN_FFTW=ON -DREGRESSIONTEST_DOWNLOAD=ON
make -j8 && make install
source /usr/local/gromacs/bin/GMXRC
```
**校验**：`gmx --version`。

### 12. AmberTools（参数化 / tleap / antechamber）
```bash
conda install -c conda-forge ambertools
```
**校验**：`tleap -h && antechamber -h | head -5`。

### 13. PACKMOL-Memgen（膜体系构建）—— 含许可
```bash
# 通过 AmberTools 自带的 packmol-memgen
conda install -c conda-forge ambertools
which packmol-memgen
# 独立 PACKMOL（不带 memgen 包装）
conda install -c conda-forge packmol
```
**校验**：`packmol-memgen --help | head -5`。
**注意**：CHARMM-GUI 在你的 Hard Rule 7 黑名单里，**不要**作为膜构建默认路线。

### 14. MDAnalysis（轨迹分析）
```bash
pip install MDAnalysis
# 或
conda install -c conda-forge mdanalysis
```
**校验**：`python -c "import MDAnalysis as mda; print(mda.__version__)"`。

### 15. PLUMED（增强采样 bias plugin）
```bash
conda install -c conda-forge plumed
# 与 GROMACS patching（如果 conda 装的 GMX 已经 patch 过 PLUMED 则跳过）
plumed-patch -p -e gromacs-2024
```

---

## 可选与外围

| 工具 | 用途 | 一行装法 |
|---|---|---|
| ProteinMPNN | 反向折叠序列设计 | `pip install git+https://github.com/dauparas/ProteinMPNN.git` |
| ESM (esm-2) | 蛋白语言模型 zero-shot | `pip install fair-esm` |
| ESMFold | 单序列折叠 | 同上，需 GPU；`torch.hub.load('facebookresearch/esm:main','esmfold_v1')` |
| Boltz-1 | 结构 + 复合物预测 | `pip install boltz` |
| AlphaFold2 (local) | 全功能折叠 | 推荐用 ColabFold 的 `localcolabfold` 安装脚本 |
| ColabFold | AF2 轻量本地版 | `pip install "colabfold[alphafold]"` |
| FreeSASA | 溶剂可及表面积 | `pip install freesasa` |
| ProDy | 弹性网络 / NMA | `pip install prody` |

---

## 失败模式与排查

| 现象 | 根因 | 解法 |
|---|---|---|
| `ModuleNotFoundError: No module named 'pyrosetta'` | 当前 env 没装 | `conda activate antibody` 切到已装 env;若新机器走 §3 的 conda channel 装 |
| `pyrosetta.init()` 卡很久首启 | 第一次下载 Rosetta database (~1 GB) | 等下载完成,或预先 `mkdir -p ~/.cache/PyRosetta && rsync` 已下载副本 |
| `mkdssp: not found` 但 PyRosetta 报 dssp 缺失 | 命名不匹配 | `ln -s $(which mkdssp) /usr/local/bin/dssp` |
| RDKit `boost.so` 报错 (macOS) | pip wheel 不全 | 卸 pip 版改 conda 版：`pip uninstall rdkit; conda install -c conda-forge rdkit` |
| MMseqs2 / Foldseek 索引报 magic byte 错 | 旧版索引不兼容新二进制 | 删 `indices/` 重建：`python scripts/retrieval/build_indices.py` |
| GROMACS `gmx_mpi` vs `gmx` 命令混乱 | conda 装的是 mpi 版 | 用 `alias gmx=gmx_mpi` 或重装非 mpi 版 |
| Python 报 `No module named 'X'` 但确认装过 | 装到了系统 Python，没装到 venv | `which python && pip list \| grep X` 双确认 |
| PyRosetta FastRelax (cartesian) 卡住 / 报段错误 | 输入 PDB 有 alt loc 或 hetatm 杂质 | 先用 `pdb-fetcher` 跑标准化清洗 |

---

## 装完必复查（强制）

```bash
# 重新跑首段诊断脚本，确认全部 Tier 1 不再 MISSING
bash scripts/check_env.sh   # 如果项目里有；没有就重跑顶部诊断块
# 重建索引（任何二进制版本变化后都要做）
python scripts/retrieval/build_indices.py
# 跑最小 smoke test
python scripts/engineer_enzyme.py --uniprot P62694 --target-property thermostability
```

---

## 与上下游 skill 的衔接

- 上游：Hard Rule 5 触发本 skill
- 下游：本 skill 通过后才允许进入 `uniprot-fetcher` / `pdb-fetcher` / `pyrosetta-stability-scan` / `cazy-crawler`
- 写回：装好的真 PyRosetta 让 simulated 标签自动从 recommendation 里去掉；这一变化必须记入 `runs/{task_id}/learning_envelope.json` 的 `fix_action` bucket（参见 RMCP Phase 1）

---

## 红线（与 Hard Rule 7 对齐）

- 禁止用 pip 装的"假 PyRosetta wrapper"代替真二进制
- 禁止用 CHARMM-GUI / SwissParam / ParamChem / genmixmem 作为默认参数化路线
- 禁止把"装不上 → 改 simulated 模式"当作长期方案；必须记录 attempted_install_method 与失败原因
- 禁止 sudo 改用户级 Python；安装层面冲突必须通过新建 conda env / venv 解决

## 输出契约

```json
{
  "skill_id": "environment-setup",
  "wt_score": 0.0,
  "scan_csv": "",
  "top_mutations": [
    {
      "position": 1,
      "from_aa": "A",
      "to_aa": "V",
      "ddg": 0.0
    }
  ],
  "diagnostics": {
    "brain": "enzyme",
    "archetype": "mutation_scan"
  }
}
```
