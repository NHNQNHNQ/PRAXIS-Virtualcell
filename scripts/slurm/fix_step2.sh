#!/usr/bin/env bash
# 修 slurm step 2: 加 MailProg + restart slurmctld/slurmd + 验 sbatch hello
# 在 .53 上: sudo bash /tmp/fix_step2.sh

# 消除 MailProg warning (Ubuntu 没 /usr/bin/mail)
if ! grep -q "^MailProg" /etc/slurm/slurm.conf; then
  echo "MailProg=/bin/true" >> /etc/slurm/slurm.conf
fi

echo "============= restart slurmctld + slurmd ============="
systemctl restart slurmctld
sleep 2
systemctl restart slurmd
sleep 4

echo "--- slurmctld ---"
systemctl is-active slurmctld
systemctl status slurmctld --no-pager 2>&1 | head -10
echo ""
echo "--- slurmd ---"
systemctl is-active slurmd
systemctl status slurmd --no-pager 2>&1 | head -10

echo ""
echo "============= sinfo + squeue (以 zkyd 跑) ============="
su - zkyd -c 'sinfo; squeue'

echo ""
echo "============= 验 sbatch hello ============="
su - zkyd -c 'sbatch /tmp/hello.sbatch 2>&1'
sleep 6
su - zkyd -c 'squeue; echo "--- hello output ---"; cat /tmp/hello-*.out 2>&1 | tail -15'

echo ""
echo "============= slurmctld.log tail (新启动后) ============="
tail -20 /var/log/slurm/slurmctld.log
