# PRAXIS-2 项目状态 + 下一步(2026-05-27 交接)

> 本文档给新会话窗口用。读完即可接续工作。所有路径 = 仓库根目录 `/Volumes/T7/clade-learn/PRAXIS-2/`。

---

## 1. 已 ship milestones

```
v0.11.0  M9    user-center (auth + register + billing + ledger)
v0.11.1  M10.5 LLM client OpenAI format (litellm proxy 在 .53:4000)
v0.12.0  M11.1 spawn 后台异步 LLM 任务 (4 endpoint, 19 测试)
v0.13.0  M11.2 MD + HPC + GPU pool (5 endpoint, 3 sim_type, 30+ 测试)  ← 最新
```

每个 milestone 的设计稿 + 实现 plan 都在 git:

| Milestone | Spec(design 稿) | Plan(实施 task list) |
|---|---|---|
| M9 user-center | `docs/superpowers/specs/2026-05-24-m9-user-center-design.md` | `docs/superpowers/plans/2026-05-24-m9-user-center.md` |
| M10 agents+files | `docs/superpowers/specs/2026-05-25-m10-agents-files-design.md` | `docs/superpowers/plans/2026-05-25-m10-agents-files.md` |
| M10.5 LLM OpenAI | `docs/superpowers/specs/2026-05-25-m10.5-llm-client-openai-format-design.md` | `docs/superpowers/plans/2026-05-25-m10.5-llm-client-openai-format.md` |
| M11.1 spawn | (无单独 spec,设计写进 plan) | `docs/superpowers/plans/2026-05-26-m11.1-spawn.md` |
| M11.2 MD+HPC | `docs/superpowers/specs/2026-05-26-m11.2-md-hpc-design.md` | `docs/superpowers/plans/2026-05-26-m11.2-md-hpc.md` |

GitHub:https://github.com/NHNQNHNQ/PRAXIS-2

---

## 2. 架构关键决策(必须记住)

### 2.1 v1 / v2 链路分离(冻结)

- **v1 链路 = v0.7.x 老 backend**,跑在 `.53:7788`(无 user 系统、无 ledger、单租户)。**全程冻结**,M9-M12 期间不动。
- **v2 链路 = PRAXIS-2 当前 backend**,跑在 `.40:?`(多租户、auth、ledger、async)。本仓库即 v2。
- **M13(deferred)**:v1 切换关闭 + 反代瘦身 + 夺 8088 端口。需 M9-M12 全 ship + 完整测试 + 用户显式批准 3 条件,目前**无 ETA**。

详见 memory:`~/.claude/projects/-Volumes-T7-clade-learn/memory/project_m13_deferred.md`

### 2.2 LLM 路由(M10.5 后)

```
backend (.40) ──POST /v1/chat/completions──> litellm proxy (.53:4000)
                                                    │
                                                    └──> deepseek-v4-pro / deepseek-v4-flash
```

backend 不直接接 anthropic SDK。`PRAXIS_MODEL=deepseek-v4-pro`(env 配)。如要换 model(claude / GPT 等),改 litellm proxy 端 config 而非 backend。

### 2.3 HPC 拓扑(2026-05-27 user 决策更新)

**新决策**:GPU 节点 = 提交端,单 host 既跑 SLURM 又跑 GROMACS。`.53` 自己是 GPU 节点,**不再** ssh-loop 到 `bio000071-74` 子节点。

含义:
- `scripts/check_gpus.sh` 需简化:去掉 ssh-loop,直接在 `.53` 本地 `nvidia-smi`(已部署的 1737 字节版本还是 ssh-loop 版,需重写)
- sbatch 模板可不动(SLURM 在单 host 时自我调度也能跑)
- M11.2 spec / plan 里写 "bio000071-074" 节点列表是 stale 假设,但 backend 没 hardcode 这个,影响只在 check_gpus.sh
- "后面的服务器"(M11.2 之后扩展到多 host 时)同样模型 — 每个 host 自带 GPU + SLURM

### 2.4 计费 / Ledger

- 1 元 = 10 li(`amount_li` 字段全用整数)
- spawn / MD / chat 完成后 `Ledger.record(conn, user_id, -cost_li, kind, ref_type, ref_id, meta)` 同事务扣费
- `users.balance_li` 是当前余额,`ledger` 表是 append-only 流水
- 单价 env 可调:
  - `PRAXIS_LLM_PRICE_IN_PER_M_LI=1500` / `OUT_PER_M_LI=6000`(spawn / chat)
  - `PRAXIS_MD_PRICE_GPU_PER_H_LI=10000` / `CPU_PER_H_LI=500`(M11.2,**placeholder**,未校准)

---

## 3. 当前状态(2026-05-27 ship 后)

### 3.1 已部署文件

- `.53:~/check_gpus.sh`(1737 bytes,owner=zkyd,chmod 755)— **但是 ssh-loop 版**,user 决策后需简化为本地 nvidia-smi 版

### 3.2 backend 跑哪里(待 user 在新窗口确认)

未知:M11.2 ship 后 backend 是否真 reload 了。可能选项:
- 本机 dev:`.venv/bin/python -m praxis2.server.app`
- `.40` 远端 systemd
- 其他

若要真验 `/api/md/gpu-pool` 通连,backend 必须先 reload 拉到 v0.13.0 代码 + export 11 个 M11.2 env(见 §4.3)。

---

## 4. 下一步具体待办

### 4.1 [必做] check_gpus.sh 简化为本地版

**现版本**(`scripts/check_gpus.sh`)假设 4 个 sub-node ssh-loop。按 user 决策需改成:

```bash
#!/usr/bin/env bash
# 本机直接 nvidia-smi(GPU 节点 = 提交端,单 host)
set -euo pipefail
HOST=$(hostname -s)
python3 - "$HOST" <<'PY'
import json, subprocess, sys
host = sys.argv[1]
try:
    out = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,utilization.gpu",
         "--format=csv,noheader,nounits"],
        text=True, timeout=10,
    )
except subprocess.SubprocessError as e:
    print(json.dumps({"total_slots":0,"busy_slots":0,"free_slots":0,
                      "hosts":[host],"gpus":[],
                      "error":f"nvidia-smi failed: {e}"}))
    sys.exit(0)

gpus = []
for line in out.strip().splitlines():
    idx, name, mem_used, mem_total, util = [s.strip() for s in line.split(",")]
    busy = int(util) > 5 or int(mem_used) > 500
    gpus.append({"host":host, "gpu_id":int(idx), "name":name,
                 "mem_mb":f"{mem_used}/{mem_total}",
                 "util_pct":int(util),
                 "busy":busy, "busy_label":None if not busy else "in_use"})
busy_n = sum(1 for g in gpus if g["busy"])
print(json.dumps({
    "total_slots":len(gpus), "busy_slots":busy_n,
    "free_slots":len(gpus)-busy_n,
    "hosts":[host], "gpus":gpus,
}))
PY
```

部署:`scp scripts/check_gpus.sh 10.102.106.53:~/check_gpus.sh && ssh 10.102.106.53 'chmod +x ~/check_gpus.sh'`

验证:`ssh 10.102.106.53 'bash ~/check_gpus.sh'`(应返 JSON,total_slots 是 .53 上的 GPU 数)

未来要扩多 host 时,这个 ssh-loop 拓扑模式得回来 — carry。

### 4.2 [必做] 验证 .53 SLURM + GROMACS 装齐

```bash
ssh 10.102.106.53 'which sbatch squeue sacct scancel gmx; sbatch --version; gmx --version'
```

预期:全部命令在 PATH 里。

若 **SLURM 不在**:M11.2 sbatch 路径全废,backend 要改成直接 bash + nohup + pid 跟踪(carry 大改,M11.x 后)。

若 **gmx 不在**:节点上装。两条路:
1. **module load gromacs** — HPC 通用方式,需联系 admin 装 module
2. **conda env / from source** — 装到 `/opt/gromacs/`,`source /opt/gromacs/bin/GMXRC`(sbatch 模板里已含 fallback)

无论哪种,sbatch 模板第一行 `module load gromacs 2>/dev/null || source /opt/gromacs/bin/GMXRC` 大概率要改成你真装的路径。改完更新 `praxis2/md/sbatch.py` 里 `_BASE_HEADER` 常量。

### 4.3 [必做] backend 配 env + reload

backend 启动前 export(对应 `_KNOWN_KEYS` 白名单):

```bash
# M11.2 SSH
export PRAXIS_HPC_SSH_HOST=10.102.106.53
export PRAXIS_HPC_SSH_USER=zkyd
export PRAXIS_HPC_SSH_KEY_PATH=~/.ssh/id_rsa
export PRAXIS_HPC_SSH_TIMEOUT_S=15

# HPC account(严区分大小写,SCW6CHB=GPU 包月,scw6chb=CPU 按需)
export PRAXIS_MD_HPC_ACCOUNT=SCW6CHB

# 计费(单价 placeholder,跑通后校准!)
export PRAXIS_MD_PRICE_GPU_PER_H_LI=10000
export PRAXIS_MD_PRICE_CPU_PER_H_LI=500
export PRAXIS_MD_FREE_CPU_HOURS_PER_JOB=1

# 限流 / poll
export PRAXIS_MD_MAX_CONCURRENT_PER_USER=2
export PRAXIS_MD_POLL_INTERVAL_S=30
export PRAXIS_MD_CHECK_GPUS_SCRIPT_PATH=~/check_gpus.sh
```

(M11.1 spawn 的 5 个 env 也别忘了:`PRAXIS_SPAWN_MAX_CONCURRENT_PER_USER=2` / `_KEEP_LAST_PER_USER=100` / `_PARTIAL_FLUSH_CHUNKS=20` / `PRAXIS_LLM_PRICE_IN_PER_M_LI=1500` / `_OUT_PER_M_LI=6000`)

reload backend 后跑:

```bash
# 1. 取 admin cookie(用 admin 账号 register flow 拿)
ADMIN_TOKEN=...  # 从某次 login 的 set-cookie 抽

# 2. 验 gpu-pool
curl http://localhost:8001/api/md/gpu-pool -b "praxis_session=$ADMIN_TOKEN"
# 期望:200 + {total_slots, busy_slots, free_slots, hosts, gpus}

# 3. 上传 fake pdb + 真提一个 standard MD
curl http://localhost:8001/api/files -b "praxis_session=$ADMIN_TOKEN" \
  -F "file=@some.pdb" -F "purpose=md_input"
# 拿 file_id, 然后:
curl -X POST http://localhost:8001/api/md/submit -b "praxis_session=$ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"structure_file_id":"...","force_field":"amber99sb","water_model":"tip3p",
       "ensemble":"NPT","temperature_k":300,"time_ns":1,"timestep_fs":2,
       "sim_type":"standard"}'
# 期望:200 + {id, status:queued, slurm_job_id}

# 4. 等 ~30s poll worker 跑一次,再 GET /api/md/jobs/{id}
# 期望:status 从 queued → running → done(几秒到几分钟,视 time_ns)
```

如果 step 3 返 502 hpc_unreachable:看 backend log,asyncssh.connect 失败原因多半是 SSH key 路径 / known_hosts。

### 4.4 [可选] M12 brainstorm + 实现

**M12 = admin v2 + proposals,~7d,ship v0.14.0**

FE 已有 13 个 endpoint shape 等 backend 接(`frontend/src/lib/admin.ts` + `extras.ts`):

**A. Admin v2(8 endpoint)**:
- `GET /api/admin/users?q=&page=&limit=` 用户列表 + 搜索 + 分页
- `POST /api/admin/users/{id}/adjust` 手动调 balance
- `POST /api/admin/users/{id}/freeze` 冻结
- `POST /api/admin/users/{id}/unfreeze` 解冻
- `POST /api/admin/reconcile` 余额账本对账
- `GET /api/admin/ledger?...` 全局流水查询
- `GET /api/admin/audit-log?...` 审计日志查询
- `GET /api/admin/stats` 仪表盘(users/balance/runs/consumption)

**B. Proposals(5 endpoint)**:
- `POST /api/proposals` 用户提交 idea/feature/bug
- `GET /api/me/proposals` 我的列表
- `GET /api/admin/proposals?status=&page=&limit=` admin 列出全部
- `POST /api/admin/proposals/{id}/decide` admin 决策(ship/promote/hold/reject)
- proposal row 含 `admin_verdict` / `admin_scores` / `shipped_to`(可能含投票打分流,MVP 可简化)

新表:
- **006_audit_log.py** — `audit_log(id BIGSERIAL, user_id, actor, action, resource, resource_id, ip, ua, meta JSONB, created_at)`
- **007_proposals.py** — `proposals(id UUID, user_id, kind, title, body, status, state, admin_verdict, admin_scores JSONB, shipped_to, decision_note, decided_at, created_at)`

技术特点:
- 没有 SSH / HPC / async worker 依赖,**最简单的 milestone**
- audit middleware:所有 admin endpoint 拦截写 `audit_log`
- 复用 M9 已有的 `Ledger.record` 实现 admin adjust
- 同 M11.1/M11.2 流程:brainstorming → spec → plan → subagent-driven TDD → ship

启动新窗口想跑 M12 时,直接说 "走 M12 brainstorm",我会 invoke superpowers:brainstorming skill 启动 Q&A。

### 4.5 [carry 池] M11.x 小项

任一可挑出来做,1-2d 完成:

| Carry | 优先级 | 描述 |
|---|---|---|
| spawn 进程 crash → stale running 修复 | 高 | backend 重启时 startup hook 标 stale running → failed,避免无限 stuck |
| MD 进程 crash → stale running 修复 | 高 | 同上,sacct 拉所有 active job 终态 |
| FE MdModal smd/plumed 表单 | 中 | submit 时让 user 在网页填 sim_params,不再手动 POST JSON |
| spawn auto-retry on 429 | 中 | LLM rate-limit 自动退避重试,联动 RATE_LIMITED enum |
| artifacts SSH-cat 流下载 | 中 | M10 storage 远程 + FE 下载按钮真生效 |
| .53 work_dir 清理 | 低 | `~/praxis-md/<uuid>/` 累积,加 cron 归档 |
| gpu_pool caching | 低 | 每个 GET 调一次 ssh 开销大,加 30s in-memory cache |
| ssh known_hosts pinning | 低 | 目前 `known_hosts=None` 宽松,生产应配 |
| MD umbrella / remd | 低 | 含 parent_id + dispatch_strategy + N children sbatch 编排 |
| progress 精度 | 低 | 目前 0,可解析 mdrun log step 行 |

### 4.6 [战略级] staging 验收 24h-2 周

路线图 §11(M13 准入):**M9-M12 全 ship + staging 验收 24h-2 周 + 用户显式批准** = M13 触发条件。

staging 验收做什么:
- v0.13.0 backend 部署到一个独立 instance(.40 当前跑的可能就是?)
- 用户在 FE 实跑 spawn / MD / file upload / 看 ledger 余额扣费 / 看 audit log(M12 后)
- 24h-2 周内没出严重 bug → 触发 M13

当前阻塞:**没有 M12 不能 staging**(audit log 不存在,无法追溯异常)。所以 staging 之前必先 M12。

---

## 5. 下个会话最快路径

```
你打开新窗口 →
   1. cat docs/history/2026-05-27-project-status-and-next.md(本文件)
   2. 决定走哪条:
      a) "先验证 M11.2 真连":跟 § 4.1 + § 4.2 + § 4.3 的命令对照走,贴每步 output 给我
      b) "走 M12 brainstorm":一句话起,我 invoke brainstorming skill
      c) "做 carry 项 X":说哪一项,我起 spec
      d) "上 staging":我看 .40 现状 + 给部署 plan
   3. memory 系统会自动 load,git log / spec / plan 都在仓库可查
```

---

## 6. memory 关键条目

会自动 load 到新窗口的 context(`~/.claude/projects/-Volumes-T7-clade-learn/memory/`):

- `MEMORY.md` 索引
- `project_m13_deferred.md` — M13 推迟,v1 链路冻结

新窗口如果还要新记忆,我会自动写。

---

## 7. 几个还没填的 placeholder

新窗口工作时该顺手补的:

- **`PRAXIS_MD_PRICE_GPU_PER_H_LI` 真值**(v0.7 老 backend 应该有,或你内心估个数)
- **`PRAXIS_MD_PRICE_CPU_PER_H_LI` 真值**
- **`.53` 上 GROMACS 安装路径 / module 名**(sbatch 模板 `module load gromacs` 是占位)
- **`.53` 上 SLURM 真在用吗,还是需要换成裸 bash + pid 跟踪**

---

End of handoff. 新窗口愉快。
