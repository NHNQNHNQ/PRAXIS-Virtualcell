from praxis2.md.sbatch import render_sbatch


def _common_params() -> dict:
    return {
        "structure_file_id": "abc",
        "force_field": "amber99sb",
        "water_model": "tip3p",
        "ensemble": "NPT",
        "temperature_k": 300,
        "time_ns": 10,
        "timestep_fs": 2,
        "notes": "test",
    }


def test_standard_renders_basic_sbatch():
    s = render_sbatch(
        sim_type="standard",
        params=_common_params(),
        sim_params={},
        work_dir="/home/zkyd/praxis-md/job1",
        account="SCW6CHB",
    )
    assert s.startswith("#!/bin/bash")
    assert "#SBATCH --account=SCW6CHB" in s
    assert "/home/zkyd/praxis-md/job1" in s
    assert "gmx grompp" in s
    assert "gmx mdrun" in s
    # 模板末尾应有完成信号(为 sacct 拿 exit code)
    assert "exit 0" in s or "EXIT" in s


def test_standard_scientific_correctness():
    """科学正确性回归门:PME / constraints / NVT 平衡 / 步数公式 / genion 组名。"""
    s = render_sbatch(
        sim_type="standard", params=_common_params(), sim_params={},
        work_dir="/home/zkyd/praxis-md/jobx", account="SCW6CHB",
    )
    # 静电必须 PME(默认 cutoff 物理错误)
    assert "coulombtype      = PME" in s or "coulombtype     = PME" in s
    # 2fs 步长必须约束氢键
    assert "constraints     = h-bonds" in s
    # NVT 平衡阶段 gen_vel 生成初速度
    assert "gen_vel         = yes" in s
    assert "gmx mdrun -deffnm nvt" in s
    # 生产步数公式 = time_ns * 1e6 / timestep_fs(不是漏 1000 倍的旧版)
    assert "1e6 / 2" in s
    # genion 用组名 SOL,不硬编码组号 13
    assert "echo SOL | gmx genion" in s
    assert "echo 13 | gmx genion" not in s
    # NPT 压力耦合
    assert "pcoupl          = C-rescale" in s


def test_standard_nvt_ensemble_no_pressure_coupling():
    p = _common_params()
    p["ensemble"] = "NVT"
    s = render_sbatch(
        sim_type="standard", params=p, sim_params={},
        work_dir="/tmp/x", account="SCW6CHB",
    )
    assert "pcoupl          = no" in s
    assert "C-rescale" not in s


def test_smd_template_includes_pull_block():
    s = render_sbatch(
        sim_type="smd_pulling",
        params=_common_params(),
        sim_params={
            "pull_coord_geometry": "distance",
            "pull_rate": 0.01,
            "pull_k1": 1000,
            "pull_group1_name": "Protein",
            "pull_group2_name": "Ligand",
        },
        work_dir="/home/zkyd/praxis-md/job2",
        account="SCW6CHB",
    )
    assert "pull = yes" in s
    assert "pull_coord1_geometry = distance" in s
    assert "pull_coord1_rate = 0.01" in s
    assert "pull_coord1_k = 1000" in s
    assert "pull_group1_name = Protein" in s


def test_remd_uses_real_mpi_multidir():
    """REMD 必须用 gmx_mpi + mpirun -multidir(thread_mpi 不支持 multidir)。"""
    s = render_sbatch(
        sim_type="remd",
        params=_common_params(),
        sim_params={"temperatures": [300, 310, 320], "exchange_interval": 500},
        work_dir="/home/zkyd/praxis-md/jobremd",
        account="SCW6CHB",
    )
    # 真 MPI build + multidir 交换
    assert "mpirun -np" in s
    assert "gmx_mpi mdrun -multidir" in s
    assert "-replex 500" in s
    # 不能用 thread-mpi 的 -ntmpi(gmx_mpi 不接受)
    assert "-ntmpi" not in s
    # 用 praxis-md-mpi env(真 MPI)
    assert "praxis-md-mpi" in s
    # 3 个温度 → 3 replica
    assert "TEMPS=(300 310 320)" in s


def test_metadynamics_uses_plumed_flag():
    s = render_sbatch(
        sim_type="metadynamics",
        params=_common_params(),
        sim_params={"plumed_file_id": "xyz"},
        work_dir="/home/zkyd/praxis-md/job3",
        account="SCW6CHB",
    )
    # gmx mdrun 用 -plumed,文件须 .dat 扩展名(gmx 不识别 .plumed)
    assert "-plumed plumed.dat" in s


def test_account_strict_case():
    """§11.7 严区分大小写,模板必须原样填入,不归一化。"""
    s = render_sbatch(
        sim_type="standard", params=_common_params(), sim_params={},
        work_dir="/tmp/x", account="scw6chb",   # 小写 CPU 账户
    )
    assert "#SBATCH --account=scw6chb" in s
    assert "#SBATCH --account=SCW6CHB" not in s


def test_gromacs_load_cmd_override():
    """PRAXIS_MD_GROMACS_LOAD_CMD 经 caller 注入,sbatch 模板用注入值替代 default zkyd 路径。"""
    custom = "module load gromacs/2026.0\nmodule load cuda/12.1"
    s = render_sbatch(
        sim_type="standard", params=_common_params(), sim_params={},
        work_dir="/tmp/x", account="SCW6CHB",
        gromacs_load_cmd=custom,
    )
    assert "module load gromacs/2026.0" in s
    assert "module load cuda/12.1" in s
    # default 命令不应再出现(注释里的 "praxis-md-cuda" 字面提及不算)
    assert "conda activate praxis-md-cuda" not in s
    assert "source /home/zkyd/software/miniconda3" not in s
