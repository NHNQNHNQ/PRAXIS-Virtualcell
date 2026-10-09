#!/usr/bin/env bash
# 阶段 0 采集脚本: 在 .53 上跑, 输出结构化文本到 stdout
# 用法: ssh zkyd@10.102.106.53 'bash -s' < collect_host.sh > _audit/host_raw.txt
# 全程只读, 不改 .53 任何状态
#
# v2: 显式 source conda.sh; 非交互 shell 默认不读 ~/.bashrc

set -u  # 严格但容错; 不用 -e (单条失败别中断)

# 显式加载 conda (~/software/miniconda3) - ssh 非交互不读 .bashrc
CONDA_SH="$HOME/software/miniconda3/etc/profile.d/conda.sh"
if [ -f "$CONDA_SH" ]; then
    # shellcheck disable=SC1090
    source "$CONDA_SH"
fi

emit() { printf '\n===[%s]===\n' "$1"; }

emit BASIC
hostname
uname -a
lsb_release -d 2>/dev/null || cat /etc/os-release 2>/dev/null
date

emit CPU
nproc
grep "model name" /proc/cpuinfo 2>/dev/null | head -1
free -h 2>/dev/null | head -3

emit GPU
nvidia-smi -L 2>/dev/null || echo "(no nvidia-smi)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || true

emit DISK
df -h 2>/dev/null | head -20

emit MODULE_AVAIL
type module >/dev/null 2>&1 && module avail 2>&1 | head -100 || echo "(no module system)"

emit CONDA_INFO
which conda 2>/dev/null
conda --version 2>/dev/null
which mamba 2>/dev/null

emit CONDA_ENVS
# 仅 env 名 (含 base, 跳过 '#' 注释 + 空行 + 不在 envs 目录的孤儿条目)
conda env list 2>/dev/null | awk 'NR>2 && NF>=2 && $1 !~ /^#/ && $1 !~ /^[*+]$/ {print $1}'

emit CONDA_ENV_PACKAGES
# 每个 env 列 conda 包 + pip 包名; 大头但只读
for env_name in $(conda env list 2>/dev/null | awk 'NR>2 && NF>=2 && $1 !~ /^#/ && $1 !~ /^[*+]$/ {print $1}'); do
    [ -z "$env_name" ] && continue
    printf -- '--- env: %s ---\n' "$env_name"
    conda list -n "$env_name" 2>/dev/null | awk 'NR>3 && NF>=2 {print $1"=="$2}' | sort -u
done

emit BIN_WHICH
BINS=(
  # 蛋白/结构
  alphafold alphafold2 alphafold3 colabfold_search colabfold_batch foldx pymol chimerax foldseek tmalign dali_lite hhblits hhsearch jackhmmer phmmer
  reduce mafft muscle clustalo modeller dssp stride
  rosetta_scripts rosetta_scripts.static.linuxgccrelease relax.static.linuxgccrelease
  # 对接 / 药物
  vina autodock_vina autodock4 smina gnina openbabel obabel qvina2 qvina-w psovina rdock dock6 ledock
  # 分子动力学
  gmx mdrun namd2 namd3 amber pmemd pmemd.cuda
  # cryo-EM
  relion_refine cryosparcm cryosparcw imod motioncor2 ctffind ctffind4 ctffind5 topaz cryolo
  # 单细胞 / RNA-seq
  cellpose star STAR hisat2 salmon kallisto bowtie2 bwa samtools bcftools featureCounts fastqc trim_galore cutadapt picard
  # 微生物组
  qiime kraken2 humann humann3 metaphlan metaphlan3 spades megahit prodigal checkm gtdbtk
  # 通用
  R Rscript snakemake nextflow singularity apptainer docker squeue sinfo sbatch
)
# 1) PATH 全局 which
for b in "${BINS[@]}"; do
    p=$(command -v "$b" 2>/dev/null || true)
    [ -n "$p" ] && printf 'global\t%s\t%s\n' "$b" "$p"
done
# 2) 每个 env 的 bin 目录 (conda envs 的 bin 不在 PATH; 单独枚举)
for env_dir in $HOME/software/miniconda3/envs/*/ $HOME/.conda/envs/*/; do
    [ -d "${env_dir}bin" ] || continue
    env_name=$(basename "${env_dir%/}")
    for b in "${BINS[@]}"; do
        if [ -x "${env_dir}bin/$b" ]; then
            printf 'env\t%s\t%s\n' "$env_name" "$b"
        fi
    done
done

emit LICENSE_DIRS
ls -la ~/.foldx ~/.schrodinger ~/.rosetta ~/Rosetta ~/foldx ~/schrodinger 2>/dev/null || true
for p in /opt/rosetta /opt/foldx /opt/schrodinger /opt/alphafold /opt/cryosparc /opt/relion /usr/local/foldx ~/software/rosetta ~/software/foldx ~/software/schrodinger ~/software/alphafold; do
    [ -e "$p" ] && ls -la "$p" 2>/dev/null | head -5
done

emit FPOCKET
[ -e ~/software/fpocket_src ] && ls ~/software/fpocket_src/ 2>/dev/null | head
[ -e ~/software/fpocket_src/bin/fpocket ] && echo "fpocket: ~/software/fpocket_src/bin/fpocket"

emit DATA_PATHS
for p in /data /home/zkyd/data1/mzy /home/zkyd/data1 ~/datasets ~/data ~/models /opt/databases /opt/data; do
    [ -e "$p" ] && ls "$p" 2>/dev/null | head -30
    [ -e "$p" ] && echo "--- $p ---"
done

emit DATA_SIZES
# 关键数据集大小 (du -sh 限深 1, 防超时)
for p in /home/zkyd/data1/mzy/PRAXIS-Brains /home/zkyd/data1/mzy/PRAXIS-DEMO /home/zkyd/data1/mzy/PRAXIS-2; do
    [ -e "$p" ] && du -sh "$p" 2>/dev/null
done

emit ENV_FILES
[ -f ~/praxis2.env ] && grep -E "^(PRAXIS_|LITELLM|POSTGRES|DEEPSEEK|SMTP)" ~/praxis2.env 2>/dev/null | sed 's/=.*$/=<redacted>/' || true

emit RUNNING_PROCESSES
# staging 后端跑啥
pgrep -af "gunicorn|litellm|uvicorn|tmux" 2>/dev/null | head -10 || true
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null | head -10 || true

emit DONE
echo "采集完成"
