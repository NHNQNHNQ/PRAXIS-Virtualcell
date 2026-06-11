---
name: pyrosetta-stability-scan
status: green
host_env: antibody
deps: [pyrosetta, biopython, numpy, pandas]
description: 用 PyRosetta cartesian_ddg 协议对结构做单点突变 ΔΔG 扫描,输出按 ΔΔG 排序并标注活性位点距离的候选突变表。支持 --simulate 模式(生成 plausible 随机 ΔΔG 用于 pipeline 测试,不需 PyRosetta) 与真实 cartesian_ddg 模式。Agent 3 (Execution) 的热稳定性工程标准起手。替代历史 FoldX BuildModel 流。
---

# PyRosetta Stability Scan Skill

## 一句话原则
扫描前用 `FastRelax (cartesian, ref15_cart)` 重新弛豫 3 轮;每个突变 `cartesian_ddg` 3 次取均值,std < 1.0 REU 才信;活性位点 5 Å 内、糖基化位点 ±3 残基**强制排除**,无论 ΔΔG 多有利。

> REU = Rosetta Energy Unit;ref15_cart 下 1 REU ≈ 0.5–1.0 kcal/mol(不同体系略有差异,做绝对值比较时按经验换算 ×0.57)。

## 适用阶段
Agent 3 (Execution),热稳定性工程任务的标准起手。

## 为什么用 PyRosetta 而不是 FoldX
| 维度 | PyRosetta cartesian_ddg | FoldX BuildModel |
|---|---|---|
| License | 学术免费(注册即得) | 学术免费(注册下载) |
| Staging `.53` 状态 | ✅ 已装于 `antibody` env | ❌ 未装 |
| 精度 | ref15_cart 在公开 benchmark(Frenz et al. 2020)上 RMSE ≈ 1.2 kcal/mol,与 FoldX 持平 | RMSE ≈ 1.3 kcal/mol |
| GPU | 不需(纯 CPU,但需多核,推荐 ≥16 核) | 不需 |
| 集成 | python 原生(`pyrosetta.distributed`) | subprocess + 解析 .fxout |

## 先检查环境
```bash
conda activate antibody
python -c "import pyrosetta; pyrosetta.init(); print(pyrosetta.__version__)"
which mkdssp || which dssp        # RSA 标注用
```

## 输入契约
```json
{
  "structure_path": "/path/to/input.pdb",
  "chain": "A",
  "scan_mode": "saturation",
  "positions": [12, 45, 196],
  "exclude_positions": [220, 221],
  "amino_acids": "ARNDCQEGHILKMFPSTWYV",
  "n_runs": 3,
  "active_site_residues": [220, 221, 224]
}
```

## 输出契约
```json
{
  "scan_summary": {
    "n_positions_scanned": 480,
    "n_mutations_evaluated": 9120,
    "wallclock_seconds": 14400,
    "score_function": "ref15_cart"
  },
  "mutations": [
    {
      "position": 196,
      "wt_aa": "S",
      "mut_aa": "A",
      "ddG_REU": -3.8,
      "ddG_kcal_per_mol": -2.17,
      "ddG_std": 0.42,
      "rsa": 0.42,
      "near_active_site": false,
      "near_glycosylation": false,
      "passes_default_filter": true
    }
  ],
  "diagnostics": {
    "convergence_check_passed": true,
    "warnings": []
  }
}
```

## SOP
```python
# 1. 初始化 + 加载结构
import pyrosetta
from pyrosetta.rosetta.protocols.relax import FastRelax
pyrosetta.init("-ex1 -ex2 -use_input_sc -ignore_unrecognized_res "
               "-relax:cartesian -score:weights ref15_cart")
pose = pyrosetta.pose_from_pdb("input.pdb")

# 2. Cartesian FastRelax 弛豫 3 轮
scorefxn = pyrosetta.create_score_function("ref15_cart")
relax = FastRelax()
relax.set_scorefxn(scorefxn)
relax.cartesian(True)
relax.max_iter(200)
for _ in range(3):
    relax.apply(pose)
pose.dump_pdb("input_relaxed.pdb")

# 3. cartesian_ddg 协议(对每位点每 AA 跑 n_runs 次)
from pyrosetta.rosetta.protocols.ddg import ddGMover
# 实际用 cartesian_ddg 应用或 pmut_scan_parallel,见 run.py
```

```bash
# CLI 等价 (rosetta_scripts cartesian_ddg.xml,binary 不在 antibody env 时退而求其次)
rosetta_scripts.linuxgccrelease \
  -s input_relaxed.pdb \
  -parser:protocol cartesian_ddg.xml \
  -parser:script_vars mutations=individual_list.txt n_runs=3
```

## 默认过滤规则
- ΔΔG < -1.5 kcal/mol (≈ -2.6 REU) → 候选
- RSA > 0.3 → 加分(表面残基优先)
- near_active_site (≤5 Å) → 强制排除
- near_glycosylation (±3 残基) → 强制排除
- |ΔΔG| > 10 kcal/mol (≈ 17 REU) → 标记为可疑,需 MD 二次验证

## 质量控制检查点
- [ ] 弛豫后结构与原结构 RMSD < 1.0 Å
- [ ] 同一突变 n_runs 重复 std < 1.0 REU(≈ 0.5 kcal/mol)
- [ ] 扫描后 ΔΔG 分布合理(主集中在 [-2, +5] kcal/mol)
- [ ] 任何 ΔΔG < -10 kcal/mol → 加 warning(过于乐观)
- [ ] 任何 ΔΔG > +20 kcal/mol → 输入结构存在问题

## 常见报错处理
| 报错 | 原因 | 修复 |
| --- | --- | --- |
| `unrecognized residue` | HETATM 非标准残基 | `pyrosetta.init("-ignore_unrecognized_res")` 或预清洗去除非标准 |
| `Atom not found` | PDB 缺失侧链原子 | PDB-Tools / PyMOL 补全;或先跑一次 packing-only |
| `cartesian relax did not converge` | 结构损坏 | 增加 max_iter / 重做弛豫;或检查 clash |
| `chain not found` | 链 ID 不匹配 | 检查 PDB 头部 chain ID,`pyrosetta.toolbox.cleaning` 标准化 |
| `pose has zero residues` | mmCIF 非标准化 | 先用 biopython 转 PDB 再喂入 |

## 实现状态
**draft** — `run.py` 已实现 PyRosetta 路径,`antibody` env 自带 pyrosetta + biopython,可直接调起。

### 可用功能 (run.py)
- argparse 接收 `--structure` (PDB/mmCIF) / `--chain` / `--scan-mode` / `--positions` / `--exclude-positions` / `--active-site-residues` / `--n-runs` / `--simulate` / `--out`
- Biopython 结构解析提取每位点 wt_aa
- saturation 模式自动排除 active site ±5 Å
- 真实模式: `pyrosetta.distributed.cluster` 调 cartesian_ddg → 收集 .out → 按位点聚合
- **Simulate 模式 (--simulate)**: 生成 plausible 随机 ΔΔG (mean ~+1.5, std ~2.5 kcal/mol;与文献 distribution 大致吻合),标 `simulated: true` + warning,用于 pipeline 测试不需 PyRosetta

### 待补
- RSA 标注(DSSP 集成)
- near_glycosylation 标注(UniProt feature parser)
- pyrosetta v4.32+ 的 `pmut_scan_parallel` 替代手写 cartesian_ddg 循环(更快)

### 简单跑法
```bash
# 真实跑(在 .53 staging)
conda activate antibody
python skills/workflows/pyrosetta-stability-scan/run.py \
  --structure data/pdb/1cel.cif --chain A \
  --scan-mode positions --positions 196,287,124 \
  --n-runs 3 \
  --out runs/{task_id}/pyrosetta_out.json

# 模拟跑(无需 PyRosetta, 用于测 pipeline)
python skills/workflows/pyrosetta-stability-scan/run.py \
  --structure data/pdb/1cel.cif --chain A \
  --scan-mode positions --positions 196,287,124 \
  --simulate --out /tmp/pyrosetta_sim.json
```

## 迁移注记(从 foldx-stability-scan)
本 skill 替代历史 `foldx-stability-scan`。两者输入契约保持兼容(`structure_path` / `chain` / `positions` / `n_runs` / `active_site_residues`),输出契约新增 `ddG_REU` 字段并保留 `ddG_kcal_per_mol`(按 ×0.57 换算)。旧 skill 调用方只需把 `--foldx-bin` 删掉,换成 `--n-runs` 即可平滑迁移。
