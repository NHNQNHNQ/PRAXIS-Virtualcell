#!/usr/bin/env bash
# 修 SLURM 启动失败 step 1: chmod conf 644 + 拉 log 看 fatal
# 在 .53 上: sudo bash /tmp/fix_step1.sh

echo "============= slurmctld.log 完整 ============="
cat /var/log/slurm/slurmctld.log
echo ""
echo "============= slurmd.log (last 40) ============="
tail -40 /var/log/slurm/slurmd.log
echo ""
echo "============= chmod conf 文件 644 (世界可读) ============="
chmod 644 /etc/slurm/slurm.conf /etc/slurm/gres.conf
ls -la /etc/slurm/
echo ""
echo "============= 用 user (zkyd) 验 sinfo 现在能不能读 conf ============="
su - zkyd -c 'sinfo 2>&1 || echo "(sinfo 还报错 — slurmctld 没起来正常)"'
