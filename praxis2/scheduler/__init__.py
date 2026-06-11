"""重算力调度(总纲 §7.3.9/§7.5.5/§11.5/§11.7)。

Web ≠ 计算端:重算力工具不在 Web 进程内跑。本包提供:
- `quota.py`:每用户并发配额 + 加权公平队列 + 全局上限
- `resource_gate.py`:五分支提交闸(立即/排队/降配/CPU 回退/拒绝),
  决策回喂模型让其自主选(§4④)
- `registry.py`:SchedulerRegistry.reserve 资源预留
- `hpc_submit.py`:HPC 提交端接口(submit/poll/cancel/timeout),
  真 SSH 投 bio000070 标 integration(M7 接口位,M8 实测)
"""
