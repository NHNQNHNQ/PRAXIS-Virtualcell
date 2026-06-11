# 11 MCP 执行协议（A100 本地跑模拟）

## 核心规则

通过 MCP gmx 工具发起模拟时，必须先用 BrainQuery 确认方案可行，再分步调用工具；不能跳过检索先行直接发送 mdrun。

## 工具使用顺序

```
1. BrainQuery → 查 cases/rules，确认参数范围合理
2. mcp__gmx__write_file → 写 mdp / top / ndx 到 work_dir
3. mcp__gmx__run_step   → grompp / editconf / solvate / genion（同步，<120s）
4. mcp__gmx__run_background → mdrun（异步，返 job_id）
5. mcp__gmx__poll_job(job_id) → 等待直到 status=done/failed
6. mcp__gmx__get_file    → 读 md.log / energy.xvg 验证结果
```

## work_dir 规范

- work_dir 必须是 `/home/zkyd/praxis-md/{job_id}/` 格式（SAFE_ROOT 下）。
- 每次模拟用独立目录，避免文件冲突。

## 能量最小化前置检查

任何 NPT/NVT/production 前必须先做 EM（能量最小化）：

```bash
# grompp EM
mcp__gmx__run_step("gmx grompp -f em.mdp -c conf.gro -p topol.top -o em.tpr", cwd)
# mdrun EM（短，同步用 run_step，timeout 300s）
mcp__gmx__run_step("gmx mdrun -deffnm em -ntmpi 1 -ntomp 18 -gpu_id 0 -nb gpu", cwd, timeout_s=300)
```

如果 EM 报 `Lincs Warning` 或 `nan energy`，停止并报告给用户，不要继续。

## poll_job 轮询策略

- 每次 poll 间隔 30–60s，避免过频。
- status=running 时读 tail 检查 `gmx performance` 输出是否正常推进。
- 超时判断：若 tail 连续 3 次相同且 job 仍 running，提示用户可能卡住。

## 错误处理

| 错误 | 处理 |
|---|---|
| run_step exit_code ≠ 0 | 读 stderr，报告给用户，不继续 |
| poll_job status=failed | 用 get_file 读 stderr.log，诊断原因 |
| get_file error=not found | 检查 work_dir 路径拼写 |
| CUDA 不可见 | 检查 `.53` 上 `/dev/nvidia*` 是否可见 |

## 环境选择

| sim_type | conda env | 命令前缀 |
|---|---|---|
| standard / smd_pulling / umbrella | praxis-md-cuda | gmx 2026.0 |
| remd（无 gmx_mpi） | praxis-md-cuda | gmx -ntmpi |
| metadynamics（需 PLUMED） | praxis-md-plumed | gmx 2024.2（待编译 PLUMED patch） |

## 适用

- 所有 MCP gmx 工具调用
- 智能体自主发起模拟
- 检索先行证据门配合使用

## 为什么

- `mdrun` 是长时任务（分钟～小时），必须异步；`grompp` 等是秒级，可同步。
- 不做 EM 直接上 NPT 高概率崩溃，浪费 A100 时间。
- 路径安全校验在服务端（SAFE_ROOT）而非客户端，agent 不需要自己做边界检查。
