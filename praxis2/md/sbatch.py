"""MD 任务脚本生成器 — standard / smd_pulling / metadynamics / umbrella_sampling / remd。

生成完整 bash 脚本(#SBATCH header 被 bash 忽略,可直接 nohup bash 跑):
- SBATCH header (被 bash 当注释,兼容 SLURM 和 LocalJobRunner)
- GROMACS conda env 加载
- 完整建模链:pdb2gmx → editconf → solvate → genion → EM → NVT 平衡 → production
- 状态哨兵:成功写 done,失败写 failed(poll_worker 据此判断)

科学正确性要点(2026-06-10 修订):
- 所有 mdp 显式 coulombtype = PME + cutoff-scheme = Verlet(默认 cutoff 静电物理错误)
- production mdp 加 constraints = h-bonds(2fs 步长必须约束氢键,否则 LINCS 爆炸)
- NVT 平衡阶段 gen_vel = yes 生成初速度(EM 后无速度)
- production 步数 = time_ns * 1e6 / timestep_fs(ns→fs→步,此前漏 1000 倍)
- genion 用组名 SOL(此前硬编码组号 13,随体系变会选错组)
"""
from __future__ import annotations

_BASE_HEADER = """#!/bin/bash
#SBATCH --account={account}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --time=24:00:00
#SBATCH --job-name=praxis_md_{sim_type}
#SBATCH --output={work_dir}/slurm.out
#SBATCH --error={work_dir}/slurm.err

set -eo pipefail   # 不带 -u: conda activate 会 source GMXRC.bash, 内部 ref unset vars
# 失败时写 sentinel(LocalJobRunner poll 依赖此文件)
trap 'echo "failed" > "{work_dir}/job.status"' ERR
cd {work_dir}

# GROMACS 加载(由 PRAXIS_MD_GROMACS_LOAD_CMD 注入;默认 zkyd 的 praxis-md-cuda)
{gromacs_load_cmd}

# ---- 1. 拓扑构建:input.pdb + force_field/water → topol.top ----
gmx pdb2gmx -f input.pdb -o conf.gro -p topol.top \\
    -ff {force_field} -water {water_model} -ignh

# ---- 2. 盒子 + 溶剂 ----
gmx editconf -f conf.gro -o boxed.gro -bt cubic -d 1.2
gmx solvate -cp boxed.gro -cs spc216.gro -o solv.gro -p topol.top

# ---- 3. 加离子中和(genion 用组名 SOL,不硬编码组号) ----
cat > ions.mdp <<'IONS_MDP'
integrator      = steep
nsteps          = 0
cutoff-scheme   = Verlet
coulombtype     = PME
rcoulomb        = 1.0
rvdw            = 1.0
IONS_MDP
gmx grompp -f ions.mdp -c solv.gro -p topol.top -o ions.tpr -maxwarn 2
echo SOL | gmx genion -s ions.tpr -o ions.gro -p topol.top \\
    -neutral -conc 0.15 -pname NA -nname CL

# ---- 4. 能量最小化 ----
cat > em.mdp <<'EM_MDP'
integrator      = steep
emtol           = 1000.0
emstep          = 0.01
nsteps          = 50000
nstlist         = 10
cutoff-scheme   = Verlet
coulombtype     = PME
rcoulomb        = 1.0
rvdw            = 1.0
pbc             = xyz
EM_MDP
gmx grompp -f em.mdp -c ions.gro -p topol.top -o em.tpr -maxwarn 2
gmx mdrun -deffnm em -ntmpi 1 -ntomp 18 -gpu_id 0 -nb gpu -pin on -pinoffset 0

# ---- 5. NVT 平衡(gen_vel 生成初速度,~100ps) ----
cat > nvt.mdp <<NVT_MDP
integrator      = md
dt              = {timestep_fs_ps}
nsteps          = 50000
nstlist         = 10
cutoff-scheme   = Verlet
coulombtype     = PME
rcoulomb        = 1.0
rvdw            = 1.0
constraints     = h-bonds
constraint_algorithm = lincs
tcoupl          = V-rescale
tc-grps         = System
tau_t           = 0.1
ref_t           = {temperature_k}
pcoupl          = no
pbc             = xyz
gen_vel         = yes
gen_temp        = {temperature_k}
gen_seed        = -1
NVT_MDP
gmx grompp -f nvt.mdp -c em.gro -p topol.top -o nvt.tpr -maxwarn 2
gmx mdrun -deffnm nvt -ntmpi 1 -ntomp 18 -gpu_id 0 -nb gpu -pin on -pinoffset 0

# ---- 6. 生产模拟(步数 = time_ns * 1e6 / timestep_fs) ----
NSTEPS=$(python3 -c "print(int({time_ns} * 1e6 / {timestep_fs}))")
cat > md.mdp <<MDP
integrator      = md
dt              = {timestep_fs_ps}
nsteps          = $NSTEPS
nstxout-compressed = 5000
nstenergy       = 5000
nstlog          = 5000
continuation    = yes
nstlist         = 10
cutoff-scheme   = Verlet
coulombtype     = PME
rcoulomb        = 1.0
rvdw            = 1.0
constraints     = h-bonds
constraint_algorithm = lincs
tcoupl          = V-rescale
tc-grps         = System
tau_t           = 0.1
ref_t           = {temperature_k}
{ensemble_block}
pbc             = xyz
{extra_mdp}
MDP
gmx grompp -f md.mdp -c nvt.gro -t nvt.cpt -p topol.top -o md.tpr -maxwarn 2

# 生产 mdrun — A100 单 GPU
gmx mdrun -deffnm md -ntmpi 1 -ntomp 18 -gpu_id 0 -nb gpu -pin on -pinoffset 0 \\
    {extra_mdrun_flags}

echo "done" > "{work_dir}/job.status"
exit 0
"""

# ---- umbrella sampling 脚本 ----
_UMBRELLA_SCRIPT = """#!/bin/bash
#SBATCH --account={account}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --time=48:00:00
#SBATCH --job-name=praxis_md_umbrella
#SBATCH --output={work_dir}/slurm.out
#SBATCH --error={work_dir}/slurm.err

set -eo pipefail
trap 'echo "failed" > "{work_dir}/job.status"' ERR
cd {work_dir}

{gromacs_load_cmd}

# 1. 构建起始体系(同 standard)
gmx pdb2gmx -f input.pdb -o conf.gro -p topol.top \\
    -ff {force_field} -water {water_model} -ignh
gmx editconf -f conf.gro -o boxed.gro -bt cubic -d 1.2
gmx solvate -cp boxed.gro -cs spc216.gro -o solv.gro -p topol.top

cat > ions.mdp <<'IONS_MDP'
integrator      = steep
nsteps          = 0
cutoff-scheme   = Verlet
coulombtype     = PME
rcoulomb        = 1.0
rvdw            = 1.0
IONS_MDP
gmx grompp -f ions.mdp -c solv.gro -p topol.top -o ions.tpr -maxwarn 2
echo SOL | gmx genion -s ions.tpr -o ions.gro -p topol.top \\
    -neutral -conc 0.15 -pname NA -nname CL

cat > em.mdp <<'EM_MDP'
integrator      = steep
emtol           = 1000.0
emstep          = 0.01
nsteps          = 50000
nstlist         = 10
cutoff-scheme   = Verlet
coulombtype     = PME
rcoulomb        = 1.0
rvdw            = 1.0
pbc             = xyz
EM_MDP
gmx grompp -f em.mdp -c ions.gro -p topol.top -o em.tpr -maxwarn 2
gmx mdrun -deffnm em -ntmpi 1 -ntomp 18 -gpu_id 0 -nb gpu -pin on

# 2. SMD 拉伸(生成沿反应坐标的构象系列;步数基于拉伸时间 ps)
NSTEPS_PULL=$(python3 -c "print(int({n_windows} * {window_spacing_nm} / {pull_rate} * 1000 / {timestep_fs} + 0.5))")
cat > pull.mdp <<MDP
integrator      = md
dt              = {timestep_fs_ps}
nsteps          = $NSTEPS_PULL
nstxout-compressed = 100
nstenergy       = 500
nstlog          = 500
nstlist         = 10
cutoff-scheme   = Verlet
coulombtype     = PME
rcoulomb        = 1.0
rvdw            = 1.0
constraints     = h-bonds
constraint_algorithm = lincs
tcoupl          = V-rescale
tc-grps         = System
tau_t           = 0.5
ref_t           = {temperature_k}
gen_vel         = yes
gen_temp        = {temperature_k}
gen_seed        = -1
pbc             = xyz
pull                     = yes
pull-ncoords             = 1
pull-ngroups             = 2
pull-group1-name         = {pull_group1}
pull-group2-name         = {pull_group2}
pull-coord1-groups       = 1 2
pull-coord1-geometry     = distance
pull-coord1-type         = umbrella
pull-coord1-rate         = {pull_rate}
pull-coord1-k            = {pull_k}
pull-nstxout             = 100
pull-nstfout             = 100
MDP

gmx grompp -f pull.mdp -c em.gro -p topol.top -o pull.tpr -maxwarn 2
gmx mdrun -deffnm pull -ntmpi 1 -ntomp 18 -gpu_id 0 -nb gpu -pin on

# 3. 提取窗口构象
mkdir -p windows
N_WIN={n_windows}
python3 - <<EXTRACT_PY
import subprocess
n = {n_windows}
spacing = {window_spacing_nm}
rate = {pull_rate}
for i in range(n):
    t_ps = i * spacing / rate   # 拉伸到 coord ≈ i*spacing 的时刻
    out = f"windows/conf_w{{i:03d}}.gro"
    subprocess.run(
        f"echo 0 | gmx trjconv -s pull.tpr -f pull.xtc -o {{out}} -dump {{t_ps}}",
        shell=True, check=False,
    )
print("window extraction done")
EXTRACT_PY

# 4. 各窗口独立约束模拟(步数 = time_ns * 1e6 / timestep_fs)
NSTEPS_WIN=$(python3 -c "print(int({time_ns} * 1e6 / {timestep_fs}))")
for i in $(seq 0 $((N_WIN-1))); do
    IDX=$(printf '%03d' $i)
    WIN_GRO="windows/conf_w${{IDX}}.gro"
    [ -f "$WIN_GRO" ] || continue
    DIST=$(python3 -c "print(round($i * {window_spacing_nm}, 3))")
    cat > windows/umbrella_w${{IDX}}.mdp <<MDP
integrator      = md
dt              = {timestep_fs_ps}
nsteps          = $NSTEPS_WIN
nstxout-compressed = 1000
nstenergy       = 1000
nstlog          = 1000
nstlist         = 10
cutoff-scheme   = Verlet
coulombtype     = PME
rcoulomb        = 1.0
rvdw            = 1.0
constraints     = h-bonds
constraint_algorithm = lincs
tcoupl          = V-rescale
tc-grps         = System
tau_t           = 0.5
ref_t           = {temperature_k}
pbc             = xyz
pull                     = yes
pull-ncoords             = 1
pull-ngroups             = 2
pull-group1-name         = {pull_group1}
pull-group2-name         = {pull_group2}
pull-coord1-groups       = 1 2
pull-coord1-geometry     = distance
pull-coord1-type         = umbrella
pull-coord1-init         = $DIST
pull-coord1-rate         = 0
pull-coord1-k            = {pull_k}
pull-nstxout             = 1000
pull-nstfout             = 1000
MDP
    gmx grompp -f windows/umbrella_w${{IDX}}.mdp -c $WIN_GRO -p topol.top \\
        -o windows/umbrella_w${{IDX}}.tpr -maxwarn 2
    gmx mdrun -s windows/umbrella_w${{IDX}}.tpr -deffnm windows/umbrella_w${{IDX}} \\
        -ntmpi 1 -ntomp 18 -gpu_id 0 -nb gpu -pin on
done

# 5. WHAM 重建 PMF
ls windows/*.tpr > tpr-files.dat
ls windows/*_pullf.xvg > pullf-files.dat
gmx wham -it tpr-files.dat -if pullf-files.dat -o pmf.xvg -hist hist.xvg -unit kCal

echo "Umbrella sampling done, PMF: pmf.xvg"
echo "done" > "{work_dir}/job.status"
exit 0
"""

# ---- REMD 脚本(真 MPI gmx_mpi + mpirun -multidir;.53 已验证) ----
# thread_mpi build 不支持 -multidir,必须用 mpi-build gmx_mpi(praxis-md-mpi env)
_REMD_SCRIPT = """#!/bin/bash
#SBATCH --account={account}
#SBATCH --nodes=1
#SBATCH --ntasks={n_replicas}
#SBATCH --gres=gpu:{n_replicas}
#SBATCH --time=48:00:00
#SBATCH --job-name=praxis_md_remd
#SBATCH --output={work_dir}/slurm.out
#SBATCH --error={work_dir}/slurm.err

set -eo pipefail
trap 'echo "failed" > "{work_dir}/job.status"' ERR
cd {work_dir}

# REMD 需要真 MPI build(gmx_mpi)支持 -multidir;thread_mpi 不支持
{mpi_load_cmd}

N_REPLICAS={n_replicas}
TEMPS=({temps_space})
NSTEPS=$(python3 -c "print(int({time_ns} * 1e6 / {timestep_fs}))")

# 1. 构建起始体系(gmx_mpi 单 rank 做预处理)
gmx_mpi pdb2gmx -f input.pdb -o conf.gro -p topol.top \\
    -ff {force_field} -water {water_model} -ignh
gmx_mpi editconf -f conf.gro -o boxed.gro -bt cubic -d 1.2
gmx_mpi solvate -cp boxed.gro -cs spc216.gro -o solv.gro -p topol.top

cat > ions.mdp <<'IONS_MDP'
integrator      = steep
nsteps          = 0
cutoff-scheme   = Verlet
coulombtype     = PME
rcoulomb        = 1.0
rvdw            = 1.0
IONS_MDP
gmx_mpi grompp -f ions.mdp -c solv.gro -p topol.top -o ions.tpr -maxwarn 2
echo SOL | gmx_mpi genion -s ions.tpr -o ions.gro -p topol.top \\
    -neutral -conc 0.15 -pname NA -nname CL

cat > em.mdp <<'EM_MDP'
integrator      = steep
emtol           = 1000.0
emstep          = 0.01
nsteps          = 50000
nstlist         = 10
cutoff-scheme   = Verlet
coulombtype     = PME
rcoulomb        = 1.0
rvdw            = 1.0
pbc             = xyz
EM_MDP
gmx_mpi grompp -f em.mdp -c ions.gro -p topol.top -o em.tpr -maxwarn 2
gmx_mpi mdrun -deffnm em -ntomp 18 -nb gpu -gpu_id 0

# 2. 为每个 replica 建子目录 + tpr(各自温度 + 随机初速度)
for i in $(seq 0 $((N_REPLICAS-1))); do
    T=${{TEMPS[$i]}}
    RDIR="replica_${{i}}"
    mkdir -p $RDIR
    cat > $RDIR/remd.mdp <<MDP
integrator      = md
dt              = {timestep_fs_ps}
nsteps          = $NSTEPS
nstxout-compressed = 5000
nstenergy       = 5000
nstlog          = 5000
nstlist         = 10
cutoff-scheme   = Verlet
coulombtype     = PME
rcoulomb        = 1.0
rvdw            = 1.0
constraints     = h-bonds
constraint_algorithm = lincs
tcoupl          = V-rescale
tc-grps         = System
tau_t           = 0.5
ref_t           = $T
pbc             = xyz
gen_vel         = yes
gen_temp        = $T
gen_seed        = -1
MDP
    gmx_mpi grompp -f $RDIR/remd.mdp -c em.gro -p topol.top -o $RDIR/remd.tpr -maxwarn 2
done

# 3. mpirun gmx_mpi mdrun -multidir(REMD);-replex 每 N steps 尝试交换
# 每 replica 占一块 A100(GPU_IDS 循环映射);.53 真跑验证交换统计正常产出
REPLICA_DIRS=$(for i in $(seq 0 $((N_REPLICAS-1))); do echo -n "replica_${{i}} "; done)
GPU_IDS=$(for i in $(seq 0 $((N_REPLICAS-1))); do echo -n $((i % 5)); done)
mpirun -np $N_REPLICAS gmx_mpi mdrun -multidir $REPLICA_DIRS \\
    -deffnm remd -replex {exchange_interval} \\
    -ntomp 9 -nb gpu -gpu_id $GPU_IDS -pin on

echo "REMD done, replicas: $REPLICA_DIRS"
echo "done" > "{work_dir}/job.status"
exit 0
"""

# ensemble_block 只含压力耦合部分(温度耦合已在模板写死,避免重复指令警告)
_ENSEMBLE_NVT = "pcoupl          = no"
_ENSEMBLE_NPT = (
    "pcoupl          = C-rescale\n"
    "pcoupltype      = isotropic\n"
    "ref_p           = 1.0\n"
    "tau_p           = 2.0\n"
    "compressibility = 4.5e-5"
)

_DEFAULT_GROMACS_LOAD_CMD = (
    "source /home/zkyd/software/miniconda3/etc/profile.d/conda.sh\n"
    "conda activate praxis-md-cuda"
)

# metadynamics 用源码编译的 gmx 2024.3-plumed_2.10.0(GPU);wrapper 含
# GMXRC + PLUMED_KERNEL + LD_PRELOAD(修 conda libstdc++ CXXABI 兼容)
_DEFAULT_PLUMED_LOAD_CMD = (
    "source /home/zkyd/software/gromacs-2024.3-plumed/activate_plumed.sh"
)

# REMD 用真 MPI build(gmx_mpi 支持 -multidir);.53 已装 praxis-md-mpi
_DEFAULT_MPI_LOAD_CMD = (
    "source /home/zkyd/software/miniconda3/etc/profile.d/conda.sh\n"
    "conda activate praxis-md-mpi"
)


def render_sbatch(
    *,
    sim_type: str,
    params: dict,
    sim_params: dict,
    work_dir: str,
    account: str,
    gromacs_load_cmd: str = _DEFAULT_GROMACS_LOAD_CMD,
    plumed_load_cmd: str = _DEFAULT_PLUMED_LOAD_CMD,
    mpi_load_cmd: str = _DEFAULT_MPI_LOAD_CMD,
) -> str:
    """生成完整任务脚本(bash 直接可跑,#SBATCH 被忽略)。

    `gromacs_load_cmd`: praxis-md-cuda(无 PLUMED) env 加载命令
    `plumed_load_cmd`: praxis-md-plumed(PLUMED) env 加载命令(metadynamics 用)
    `mpi_load_cmd`: praxis-md-mpi(gmx_mpi 真 MPI) env 加载命令(REMD multidir 用)
    """
    if sim_type == "umbrella_sampling":
        return _render_umbrella(params, sim_params, work_dir, account, gromacs_load_cmd)
    if sim_type == "remd":
        # REMD 需真 MPI build(gmx_mpi 支持 -multidir),用 praxis-md-mpi env
        return _render_remd(params, sim_params, work_dir, account, mpi_load_cmd)

    ensemble_block = (
        _ENSEMBLE_NPT if params["ensemble"].upper() == "NPT" else _ENSEMBLE_NVT
    )
    extra_mdp = _build_extra_mdp(sim_type, sim_params)
    extra_mdrun_flags = _build_extra_mdrun(sim_type, sim_params, plumed_load_cmd)
    # metadynamics 用 plumed env
    load_cmd = plumed_load_cmd if sim_type == "metadynamics" else gromacs_load_cmd
    return _BASE_HEADER.format(
        account=account,
        sim_type=sim_type,
        work_dir=work_dir,
        gromacs_load_cmd=load_cmd,
        force_field=params["force_field"],
        water_model=params["water_model"],
        timestep_fs=params["timestep_fs"],
        timestep_fs_ps=params["timestep_fs"] / 1000.0,
        time_ns=params["time_ns"],
        ensemble_block=ensemble_block,
        temperature_k=params["temperature_k"],
        extra_mdp=extra_mdp,
        extra_mdrun_flags=extra_mdrun_flags,
    )


def _render_umbrella(
    params: dict, sim_params: dict, work_dir: str, account: str, load_cmd: str,
) -> str:
    return _UMBRELLA_SCRIPT.format(
        account=account,
        work_dir=work_dir,
        gromacs_load_cmd=load_cmd,
        force_field=params["force_field"],
        water_model=params["water_model"],
        timestep_fs=params["timestep_fs"],
        timestep_fs_ps=params["timestep_fs"] / 1000.0,
        time_ns=params["time_ns"],
        temperature_k=params["temperature_k"],
        pull_group1=sim_params["pull_group1_name"],
        pull_group2=sim_params["pull_group2_name"],
        pull_rate=sim_params["pull_rate"],
        pull_k=sim_params["pull_k1"],
        window_spacing_nm=sim_params["window_spacing_nm"],
        n_windows=sim_params["n_windows"],
    )


def _render_remd(
    params: dict, sim_params: dict, work_dir: str, account: str, load_cmd: str,
) -> str:
    temps = sim_params["temperatures"]
    n_replicas = len(temps)
    temps_space = " ".join(str(t) for t in temps)
    return _REMD_SCRIPT.format(
        account=account,
        work_dir=work_dir,
        mpi_load_cmd=load_cmd,
        force_field=params["force_field"],
        water_model=params["water_model"],
        timestep_fs=params["timestep_fs"],
        timestep_fs_ps=params["timestep_fs"] / 1000.0,
        time_ns=params["time_ns"],
        n_replicas=n_replicas,
        temps_space=temps_space,
        exchange_interval=sim_params.get("exchange_interval", 500),
    )


def _build_extra_mdp(sim_type: str, sim_params: dict) -> str:
    if sim_type == "smd_pulling":
        return (
            "pull = yes\n"
            "pull_ncoords = 1\n"
            "pull_ngroups = 2\n"
            f"pull_group1_name = {sim_params['pull_group1_name']}\n"
            f"pull_group2_name = {sim_params['pull_group2_name']}\n"
            "pull_coord1_groups = 1 2\n"
            f"pull_coord1_geometry = {sim_params['pull_coord_geometry']}\n"
            "pull_coord1_type = umbrella\n"
            f"pull_coord1_rate = {sim_params['pull_rate']}\n"
            f"pull_coord1_k = {sim_params['pull_k1']}"
        )
    return ""


def _build_extra_mdrun(sim_type: str, sim_params: dict, plumed_load_cmd: str = "") -> str:
    if sim_type == "metadynamics":
        # gmx mdrun -plumed 要求 .dat 扩展名(.plumed 不被识别)
        return "-plumed plumed.dat"
    return ""
