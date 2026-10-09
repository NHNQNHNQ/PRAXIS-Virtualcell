# 在 .53 (zkyd) 装 SLURM 单节点 — sudo 执行清单

> 全程在 `zkyd@10.102.106.53` 跑,需要 sudo 密码。每步贴 output 回会话。

## Step 1 — apt 装包

```bash
sudo apt-get update
sudo apt-get install -y slurm-wlm munge
dpkg -l | grep -E "slurm-wlm|munge" | head
```

预期:`slurm-wlm` 和 `munge` 都 `ii`。

## Step 2 — 启动 munge (SLURM auth)

```bash
sudo systemctl enable --now munge
sudo systemctl status munge --no-pager | head -10
munge -n | unmunge | head -5
```

预期:munge active,`unmunge` 返 STATUS Success。

## Step 3 — 部署 slurm.conf + gres.conf (我已写好,你 scp + sudo cp)

本地仓库已有文件,scp 到 .53 临时位置:

```bash
# 在本地 (MBP) 跑:
scp /Volumes/T7/clade-learn/PRAXIS-2/scripts/slurm/slurm.conf 10.102.106.53:/tmp/slurm.conf
scp /Volumes/T7/clade-learn/PRAXIS-2/scripts/slurm/gres.conf 10.102.106.53:/tmp/gres.conf
```

然后在 .53 上 sudo 部署:

```bash
sudo mkdir -p /etc/slurm /var/spool/slurmctld /var/spool/slurmd /var/log/slurm
sudo cp /tmp/slurm.conf /etc/slurm/slurm.conf
sudo cp /tmp/gres.conf /etc/slurm/gres.conf
sudo chown slurm:slurm /var/spool/slurmctld /var/spool/slurmd /var/log/slurm
sudo chmod 755 /var/spool/slurmctld /var/spool/slurmd
ls -la /etc/slurm/
```

## Step 4 — 启 slurmctld + slurmd

```bash
sudo systemctl enable --now slurmctld
sudo systemctl enable --now slurmd
sleep 2
sudo systemctl status slurmctld --no-pager | head -15
sudo systemctl status slurmd --no-pager | head -15
```

## Step 5 — 验调度通

```bash
sinfo
squeue
# 跑一个 hello sbatch
cat > /tmp/hello.sbatch <<'EOF'
#!/bin/bash
#SBATCH --job-name=hello
#SBATCH --output=/tmp/hello-%j.out
#SBATCH --time=00:01:00
#SBATCH --partition=gpu
hostname
nvidia-smi --query-gpu=index --format=csv,noheader | head -1
echo "done"
EOF
sbatch /tmp/hello.sbatch
sleep 5
squeue
cat /tmp/hello-*.out
```

预期:`sinfo` 显示 zkyd 状态 idle/mix,sbatch 返回 jobid,sleep 后 squeue 该 job 已 done,output 有 hostname/GPU/done。

如果节点状态是 `drain` 或 `down`,看 `/var/log/slurm/slurmctld.log` 末尾几行(`sudo tail -30 /var/log/slurm/slurmctld.log`)报错原因。
