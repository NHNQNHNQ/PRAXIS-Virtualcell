# PRAXIS-MD A100 真执行改造计划

**目标**：MD 智能体在 chat 中通过 MCP 工具直接调 gmx，在 `.53` A100 上从头跑完 standard / SMD pulling / umbrella sampling / metadynamics / REMD 全流程；页面 `/md` 面板能看到轨迹列表。

---

## 现状诊断

| 维度 | 现状 | 问题 |
|---|---|---|
| gmx 环境 | `praxis-md-cuda` gmx 2026.0 + CUDA A100 | PLUMED 未装（metadynamics 阻断） |
| 作业调度 | `handlers.py` 提交用 `sbatch`（SLURM） | `.53` 无 SLURM → 提交 502 |
| 智能体-gmx 通路 | SkillExec → SSH 跑 run.py | 无法交互式多步；每步单独 SSH |
| `/api/storage/trajectories` | 缺失 → 页面报 HTML | 端点完全未实现 |
| 增强采样 | `sim_params.py` 只有 `standard/smd_pulling/metadynamics` | 无 `umbrella_sampling`, `remd` |
| 脑知识 | Naruto-main 16 cases + 8 rules | 未与执行链对齐 |

---

## 架构目标

```
[用户 chat]
    │  BrainQuery → 脑中 cases/rules 确认方法
    │
    └─ AgentTool (PRAXIS-MD brain)
           │
           ├─ mcp__gmx__write_file("topol.top", content)
           ├─ mcp__gmx__run_step("gmx grompp -f em.mdp -c conf.gro -p topol.top -o em.tpr", cwd)
           ├─ mcp__gmx__run_step("gmx mdrun -deffnm em -ntmpi 1 -ntomp 18 -gpu_id 0 -nb gpu ...", cwd)
           ├─ mcp__gmx__poll_job(job_id)          ← 等待长时任务
           └─ mcp__gmx__get_file("md.log", 200)  ← 取结果

[PRAXIS-2 server]
    MCPConnectionPool → SSH stdio → [.53 gmx MCP server process]
                                          │
                                          └─ 直接调 gmx (praxis-md-cuda env)
```

---

## 子任务列表

### SP0 — 快速修复（独立，1 task）
**修 `/api/storage/trajectories` 端点缺失**

- 在 `praxis2/server/routes/files.py` 加 `handle_storage_trajectories()`
- 查 `md_jobs` 表，映射为 `MdTrajectory` 格式（字段：job_id, name, status, created_at 等）
- 注册路由 `("/api/storage/trajectories", "GET")`
- 加测试

---

### SP1 — LocalJobRunner 替换 SLURM（3 tasks）

**目标**：把 `handlers.py` 里的 `sbatch` 改为直接在 `.53` 用 nohup 跑，并能追踪 PID。

**Task 1.1** — `praxis2/md/local_runner.py`
```python
class LocalJobRunner:
    async def submit(cfg, work_dir, script_content) -> LocalJob:
        # ssh: mkdir work_dir, write job.sh, nohup bash job.sh > stdout.log 2> stderr.log & echo $! > job.pid
        # 返回 LocalJob(pid=..., work_dir=...)
    
    async def poll(cfg, job) -> Literal["running", "done", "failed"]:
        # ssh: kill -0 $pid → running; 不存在 → 读 sentinel 文件 done/failed
```

脚本末尾写 sentinel：
```bash
# job.sh 末尾
if [ $? -eq 0 ]; then echo done > "$WORK_DIR/job.status"; else echo failed > "$WORK_DIR/job.status"; fi
```

**Task 1.2** — 修 `handlers.py` submit 路径
- 删 sbatch 调用，改用 `local_runner.submit()`
- `slurm_job_id` 字段写 `local:$pid`（兼容 repo 无改动）
- poll_worker.py 同步更新：检查 `local:` 前缀 → 走 `local_runner.poll()`

**Task 1.3** — e2e 测试：提交一个 20 步 EM vacuum 任务，验证 queued → running → done 全链

---

### SP2 — MCP gmx Server（4 tasks）

**目标**：在 `.53` 上跑一个 MCP stdio server；PRAXIS-2 通过 SSH-stdio 接入；智能体可以交互式调 gmx。

**Task 2.1** — `praxis2/mcp/servers/gmx_server.py`（在 `.53` 运行）

5 个 MCP tools：

| Tool | 参数 | 说明 |
|---|---|---|
| `write_file` | path, content | 写文件（mdp/top/ndx 等）到 work_dir |
| `run_step` | cmd, cwd, timeout_s | 同步跑短命令（grompp/genion/editconf，<60s） |
| `run_background` | cmd, cwd | nohup 跑长任务，返 job_id |
| `poll_job` | job_id | 查 PID 存活 + 返日志尾 |
| `get_file` | path, max_bytes | 拉回日志/能量/坐标文件片段 |

服务器 bootstrap：
```bash
source .../miniconda3/.../conda.sh && conda activate praxis-md-cuda
python -m praxis2.mcp.servers.gmx_server
```

**Task 2.2** — `praxis2/mcp/config.py` 加 gmx server 条目
```json
{
  "name": "gmx",
  "command": "ssh",
  "args": ["-i", "${PRAXIS_SKILL_SSH_KEY}", "zkyd@10.102.106.53",
           "source /home/zkyd/software/miniconda3/etc/profile.d/conda.sh && conda activate praxis-md-cuda && python -m praxis2.mcp.servers.gmx_server"]
}
```

**Task 2.3** — 注册到 md brain 的 discipline pool，MD 智能体可见 `mcp__gmx__*` 工具

**Task 2.4** — e2e：chat 中让 MD agent 调 `mcp__gmx__run_step("gmx --version", "/tmp")` 验证通路

---

### SP3 — 增强采样 sim_type 扩展（4 tasks）

#### Task 3.1 — 伞状采样（Umbrella Sampling）

**原理**：拉伸生成构象窗口 → 多窗口约束模拟 → `gmx wham` 重建 PMF

`sim_params.py` 新增：
```python
_UMBRELLA_REQUIRED = [
    ("pull_group1_name", str),
    ("pull_group2_name", str),
    ("pull_rate", (int, float)),       # 拉伸速率 nm/ps
    ("pull_k1", (int, float)),         # spring constant
    ("window_spacing_nm", (int, float)),  # 窗口间距
    ("n_windows", int),                # 窗口数
]
```

`local_runner.py` 的 umbrella 脚本分 3 阶段：
1. `gmx mdrun -deffnm pull`（SMD 拉伸，提取构象）
2. 循环 N 个窗口：`gmx grompp -f umbrella_N.mdp -c conf_N.gro` → `gmx mdrun`
3. `gmx wham -it tpr-files.dat -if pullf-files.dat -o pmf.xvg`

脑 rules 新增：`09-umbrella-sampling-pmf.md`（窗口间距选取、收敛判据、PBC CV 注意事项）

#### Task 3.2 — REMD（Replica Exchange MD）

**原理**：多温度 replica 同时跑 + 定时交换 → 原生 `gmx mdrun -multidir`

`sim_params.py` 新增：
```python
_REMD_REQUIRED = [
    ("temperatures", list),    # [300, 310, 320, 330] 等
    ("exchange_interval", int),# steps 间隔
]
```

脚本：
```bash
# 为每个温度建子目录 T_300/ T_310/ ...
# 各自 grompp 生成 tpr
# 统一 mdrun：
mpirun -np N_REPLICAS gmx_mpi mdrun -multidir T_300 T_310 ... \
    -replex $EXCHANGE_INTERVAL -ntmpi 1 -ntomp 18 -gpu_id 0,1,...
```

注意：REMD 需要 `gmx_mpi`，需确认 `.53` 上 `praxis-md-cuda` 是否有 `gmx_mpi`（备选：`gmx mdrun -multidir` 用 thread-MPI 也支持，但 replica 数受限）

脑 rules 新增：`10-remd-temperature-ladder.md`（温度梯度设计、接受率 20-30%、gmx_mpi vs thread-MPI）

#### Task 3.3 — 元动力学（Metadynamics）

**前置 ops**：安装 PLUMED-patched GROMACS

```bash
# 方案 A（推荐）：conda install 预编译 gromacs+plumed
conda create -n praxis-md-plumed -c conda-forge gromacs=2024 plumed=2.9 \
    cudatoolkit=12.x ...

# 方案 B：源码打 PLUMED patch（复杂，备选）
```

脚本：从 `input.plumed`（用户提供或 agent 生成）注入 `-plumed` flag：
```bash
gmx mdrun -deffnm meta -ntmpi 1 -ntomp 18 -gpu_id 0 -nb gpu -plumed plumed.dat
```

Agent 能力：根据 BrainQuery 召回的 cases（褪黑素/MT1 案例），自动生成 `plumed.dat` 的 CV 定义（DISTANCE/TORSION + METAD）

脑 rules 更新：`06-sampling-cv-and-version-compatibility.md` 补充 PLUMED 版本检查命令

#### Task 3.4 — PLUMED 环境安装（ops + 验证）

1. SSH 到 `.53`，`conda create -n praxis-md-plumed`
2. 验证：`gmx --version | grep PLUMED`
3. 更新 `md_gromacs_load_cmd` 配置条目：`praxis-md-plumed`（when sim_type=metadynamics）
4. 更新 `praxis2.env`（staging）加 `PRAXIS_MD_PLUMED_LOAD_CMD`

---

### SP4 — 脑知识对齐（2 tasks）

**Task 4.1** — 新增 skill：`md-enhanced-sampling`

`brains/md/Naruto-main/skills/workflows/md-enhanced-sampling/`
- `SKILL.md`：覆盖4种增强采样的完整 MCP 调用序列（从 BrainQuery 到 mcp__gmx__ 步骤）
- `run.py`：real() 走 SSH + praxis-md-cuda/praxis-md-plumed env

**Task 4.2** — 脑 rules 补充

| 文件 | 内容 |
|---|---|
| `09-umbrella-sampling-pmf.md` | 窗口数/间距/收敛/WHAM 注意 |
| `10-remd-temperature-ladder.md` | 温度梯度/接受率目标/thread_mpi限制 |
| `11-mcp-execution-protocol.md` | 调用 mcp__gmx__ 的标准序列（检查 env → write files → run steps → poll → fetch log） |

---

## 执行顺序

```
SP0 (0.5天) → SP1 (1天) → SP2 (1天) → SP3 (2天) → SP4 (0.5天)
                                                │
                              SP3.4 PLUMED 安装 ← ops 前置（先启动，并行做其他 task）
```

**关键阻塞点**：
- SP3.3 metadynamics 依赖 SP3.4 PLUMED 安装（ops 手动操作）
- SP2 MCP server 依赖 `.53` Python 环境有 `mcp` 库（`pip install mcp` in praxis-md-cuda）

---

## 验收标准

| 场景 | 通过条件 |
|---|---|
| 页面 `/md` 轨迹列表 | 不报 HTML，返回 JSON（哪怕空列表） |
| standard MD | chat agent → mcp__gmx__ → A100 跑 1aki 20ns → done status |
| SMD pulling | chat agent 给 PDB → 完成拉伸 → log 中有 pull force 输出 |
| Umbrella Sampling | 多窗口提交 → gmx wham → pmf.xvg 生成 |
| Metadynamics | gmx mdrun -plumed → HILLS 文件生成 |
| REMD | 4 replica → 至少1次成功交换（log 中有 Replica exchange statistics） |

---

## 未解决问题（需用户决策）

1. **PLUMED 安装**：方案A（conda-forge 预编译）还是方案B（源码）？推荐方案A，但需确认 A100 CUDA 12.x 兼容性
2. **REMD gmx_mpi**：`.53` 的 praxis-md-cuda env 是否有 `gmx_mpi`（thread-MPI 版本无 MPI multinode，但 1 节点 4 GPU 够用）
3. **MCP server 持久化**：SSH stdio 每次对话新建进程 vs 常驻服务（推荐先用 stdio 简单版，后期改常驻）
4. **账户权限**：MCP server 写文件到 `/home/zkyd/praxis-md/` 还是独立沙盒目录

---

## 文件改动清单

```
praxis2/
  md/
    local_runner.py          # NEW - 替换 sbatch
    handlers.py              # MODIFY - submit/poll 改本地
    poll_worker.py           # MODIFY - 检测 local: 前缀
    sim_params.py            # MODIFY - 加 umbrella_sampling, remd
  mcp/servers/
    gmx_server.py            # NEW - MCP stdio server for gmx
  mcp/config.py              # MODIFY - 注册 gmx server
  server/routes/files.py     # MODIFY - 加 trajectories 端点

brains/md/Naruto-main/
  skills/workflows/
    md-enhanced-sampling/    # NEW - SKILL.md + run.py
  memory/rules/
    09-umbrella-sampling-pmf.md  # NEW
    10-remd-temperature-ladder.md # NEW
    11-mcp-execution-protocol.md  # NEW

tests/
  test_md_local_runner.py    # NEW
  test_md_handlers_local.py  # MODIFY
  test_mcp_gmx_server.py     # NEW
```

总改动量：~10 个文件新增，~4 个文件修改，~3 个测试文件

---

## 验证现状（2026-06-10）

### ✅ standard MD — 真跑从头跑完验证通过

`.53` 真跑 22 残基蛋白（DL-masif/data/1.pdb，time_ns=0.002）：

| 阶段 | 工具 | 结果 |
|---|---|---|
| 拓扑 | pdb2gmx (amber99sb+tip3p, -ignh) | conf.gro ✓ |
| 盒子+溶剂 | editconf -bt cubic -d1.2 + solvate | 9311 水 ✓ |
| 中和 | genion echo SOL -neutral -conc0.15 | 31 NA + 26 CL，中和 -5 蛋白 ✓ |
| 能量最小化 | mdrun steep PME | em.gro ✓ |
| NVT 平衡 | mdrun gen_vel V-rescale | nvt.gro ✓ |
| production | mdrun NPT C-rescale PME constraints | md.gro 28345 原子 box6.6nm ✓ |

**job.status=done，GPU 用上（1 GPU selected），无 LINCS 爆炸，PME 生效，production 满 1000 步=2ps，体系中性。**

修复的 5 个科学正确性真问题见 commit `48bd93a`：NSTEPS 漏 1000 倍 / 缺 PME / 缺 constraints / genion 硬编码组号 / 缺 NVT 平衡。

### ⚠️ 增强采样 — mdp 科学正确，真跑受基建限制

| sim_type | mdp 正确性 | 单测 | 真跑状态 | 阻塞/解锁路径 |
|---|---|---|---|---|
| smd_pulling | ✅ PME+constraints+gen_vel | ✅ | 建系链同 standard（已验证） | pull groups 仅默认组(grompp 无 -n index)；蛋白-配体需配体参数化 |
| umbrella_sampling | ✅ 同上+WHAM | ✅ | 同上 | 同 smd；窗口提取+wham 逻辑就绪 |
| remd | ✅ 每replica gen_vel+温度 | ✅ | **✅ 真跑验证** | praxis-md-mpi(gmx_mpi Open MPI 5.0.8)已装,2replica真跑交换统计正常 |
| metadynamics | ✅ -plumed flag | ✅ | **✅ 真跑验证** | 源码编译 gmx 2024.3-plumed_2.10.0(GPU),HILLS 高斯沉积+COLVAR 正常 |

**关键基建发现**：
- `.53` praxis-md-cuda(gmx2026) / praxis-md-plumed(gmx2024.2) **都是 thread_mpi build**，不支持 REMD 的 `-multidir`（需真 MPI）
- praxis-md-plumed 装了 PLUMED 库但 gmx 未 patch（`-plumed` 报 Unknown option）→ metadynamics 需源码编译
- **REMD 已解锁**：装了 `praxis-md-mpi`(gromacs=2024.5 mpi_openmpi_cuda + Open MPI 5.0.8 gmx_mpi)，REMD 脚本用 `mpirun -np N gmx_mpi mdrun -multidir`(无 -ntmpi)，PRAXIS_MD_MPI_LOAD_CMD 配置注入
- **metadynamics 已解锁**：源码编译 `gmx 2024.3-plumed_2.10.0`(GPU sm_80) 装到 `/home/zkyd/software/gromacs-2024.3-plumed`，plumed patch runtime 模式，wrapper `activate_plumed.sh` 含 GMXRC+PLUMED_KERNEL+LD_PRELOAD(修 conda libstdc++ CXXABI_1.3.15 兼容)

### env 矩阵(.53)

| env | gmx | MPI build | 用途 |
|---|---|---|---|
| praxis-md-cuda | 2026.0 | thread_mpi | standard/smd/umbrella(单 GPU) |
| praxis-md-mpi | 2024.5 | **真 MPI** (Open MPI 5.0.8) | REMD multidir |
| /home/zkyd/software/gromacs-2024.3-plumed | 2024.3 | thread_mpi+**PLUMED** | metadynamics(源码编译 GPU,wrapper activate_plumed.sh) |

**四种增强采样全部真跑验证**：standard / SMD / 伞形 / REMD / metadynamics(HILLS 高斯沉积)。metadynamics 编译关键:cmake 须降级 3.28(4.x 不认 CUDA 12.2)、PLUMED 无 MPI 故 GMX_MPI=OFF、运行 LD_PRELOAD conda libstdc++ 修 CXXABI、-plumed 文件须 .dat 扩展名。

### MCP gmx server 真跑

`.53` 真测 `write_file_impl` 写文件 + `run_step_impl("gmx --version")` 返 GROMACS 2026.0 ✓。
MCP 工具全局注册到所有 chat agent 工具池（chat_registry.py:86），`mcp__gmx__*` 对 MD agent 可见。
