#!/usr/bin/env bash
# SLURM 单节点部署 — 在 .53 (zkyd) 上以 sudo 跑
#   sudo bash /tmp/deploy_slurm.sh 2>&1 | tee /tmp/deploy_slurm.log
#
# 前提:/tmp/slurm.conf 和 /tmp/gres.conf 已 scp 就位

set -uo pipefail

echo "============= Step 1: apt install slurm-wlm munge ============="
apt-get update -qq
apt-get install -y slurm-wlm munge
dpkg -l | grep -E "slurm-wlm|munge" | head -5

echo ""
echo "============= Step 2: munge auth ============="
systemctl enable --now munge
sleep 1
systemctl status munge --no-pager 2>&1 | head -8 || true
echo "--- munge 自测 ---"
munge -n | unmunge 2>&1 | head -5 || true

echo ""
echo "============= Step 3: 部署 conf + 建目录 ============="
mkdir -p /etc/slurm /var/spool/slurmctld /var/spool/slurmd /var/log/slurm
cp /tmp/slurm.conf /etc/slurm/slurm.conf
cp /tmp/gres.conf /etc/slurm/gres.conf
chown slurm:slurm /var/spool/slurmctld /var/spool/slurmd /var/log/slurm
chmod 755 /var/spool/slurmctld /var/spool/slurmd
ls -la /etc/slurm/

echo ""
echo "============= Step 4: 启 slurmctld + slurmd ============="
systemctl enable --now slurmctld
sleep 2
systemctl enable --now slurmd
sleep 3
echo "--- slurmctld status ---"
systemctl status slurmctld --no-pager 2>&1 | head -10 || true
echo "--- slurmd status ---"
systemctl status slurmd --no-pager 2>&1 | head -10 || true

echo ""
echo "============= Step 5: sinfo + sbatch hello ============="
sinfo 2>&1 || true
echo "--- 提交 hello sbatch ---"
cat > /tmp/hello.sbatch <<'EOF'
#!/bin/bash
#SBATCH --job-name=hello
#SBATCH --output=/tmp/hello-%j.out
#SBATCH --time=00:01:00
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
hostname
nvidia-smi --query-gpu=index --format=csv,noheader | head -1
echo "done"
EOF
sbatch /tmp/hello.sbatch 2>&1 || true
sleep 6
squeue 2>&1 || true
echo "--- hello output ---"
cat /tmp/hello-*.out 2>&1 | tail -15 || echo "(no hello output yet)"

echo ""
echo "============= DONE ============="
echo "若任意 step 失败,看 /var/log/slurm/slurmctld.log 末尾 + /var/log/slurm/slurmd.log 末尾"
