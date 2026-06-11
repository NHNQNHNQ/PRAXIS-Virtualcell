---
name: snugdock_antibody
description: PyRosetta SnugDock 抗体-抗原 docking — CDR 全 flex + paratope 限制 (CDR_only) + epitope hint 必填 + CDR H3 长度 gate (>18 aa 自动 low-conf)。PyRosetta 需用户 license + GPU build；通过 SSH bridge 在远程 zkyd@10.102.106.53 跑。
status: usable
source_case: dock-004-snugdock-antibody-cdr-flex
host_env: DL-masif
---

# snugdock_antibody — Antibody-antigen docking with CDR flexibility

## 一句话原则
**抗体走专用 docker（不通用 PP）+ epitope hint + CDR H3 ≤ 18 aa（>18 自动 low-conf）+ ≥ 1000 trajectories**。通用 PP docker 在抗体上假阳率高（framework 朝向抗原）。

## 适用阶段
Stage 3 (Execution) — `docking_type == antibody_antigen`.

## 输入契约

```json
{
  "antibody_fv_pdb": "/path/to/abfv_from_igfold.pdb",
  "antigen_pdb": "/path/to/antigen.pdb",
  "epitope_residues": [417, 484, 501],
  "paratope_restriction": "CDR_only",
  "n_trajectories": 1000,
  "use_h3_kink_rebuild": true,
  "rosetta_n_threads": 16,
  "remote_gpu": true,
  "out_dir": "/runs/{tid}/snugdock_antibody/"
}
```

## 输出契约

```json
{
  "skill_id": "snugdock_antibody",
  "version": "PyRosetta 4.0+",
  "antibody_prep": {
    "cdr_h3_length": 14,
    "cdr_h3_length_warning_low_confidence": false,
    "fv_method": "IgFold",
    "framework_check_passed": true
  },
  "epitope_hint_used": [417, 484, 501],
  "n_trajectories_run": 1000,
  "top_n_models": [
    {"rank": 1, "interface_energy": -34.5, "packstat": 0.71,
     "shape_complementarity": 0.78, "interface_rmsd_to_crystal_A": 2.3,
     "model_pdb": "/runs/{tid}/snugdock_antibody/model1.pdb"}
  ],
  "capri_quality": "medium",
  "passed_sanity": true,
  "provenance": {"command": "...", "runtime_sec": 8743.2, "remote_executed": true}
}
```

## ★ 强制 sanity checks (case dock-004 lessons)

1. **CDR H3 长度 gate**：> 18 aa → metadata.cdr_h3_length_warning_low_confidence=true，confidence 自动降至 low（不阻塞，但报告中 caveat）
2. **Epitope hint 必填**：`epitope_residues=[]` → SanityFail（"epitope blind 时 SnugDock 也降到 < 20% success"）
3. **Antibody framework 高质量**：必须 IgFold/ImmuneBuilder 出，不要 traditional homology model（输入文件 metadata 必有 `fv_method` 字段）
4. **N trajectories ≥ 1000**：< 1000 sampling 不足 → warn
5. **Glycan-shielded epitope 警告**：用户提供 `glycan_resids` 列表则 surface 到 caveats（spike, gp120 等）
6. **IgG / bispecific 不能单 dock**：检测输入是 full IgG（含 Fc）则 SanityFail，要求拆 Fab 或用 multi-paratope mode

## 实现状态: usable (binary 依赖 PyRosetta license + GPU build)
- `run.py` 完整可跑：通过 SSH bridge 在 zkyd@10.102.106.53 调 PyRosetta SnugDock
- PyRosetta license: https://www.pyrosetta.org/ (academic free; commercial paid)
- 远程 conda env `praxis-dock-pyrosetta`（需 license activation 后单独装）
- 缺 PyRosetta 时 raise EnvUnavailable + 给安装命令

## 引用案例
- **dock-004-snugdock-antibody-cdr-flex**: 1IQD (Anti-FactorVIII Fab) benchmark, CAPRI medium-acceptable rate ~40% with epitope hint vs ~10% for generic PP docker
- 失败模式: CDR H3 > 20 aa（所有方法都失败）, conformational epitope, glycan shield, allosteric Ab, IDR antigen, bispecific cooperativity
