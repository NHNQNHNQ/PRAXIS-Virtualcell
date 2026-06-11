# PRAXIS-2 状态 + 下一步(2026-05-29 M12 ship 后交接)

> 给新会话窗口。读完即接续。仓库根 `/Volumes/T7/clade-learn/PRAXIS-2/`。前交接 `docs/history/2026-05-27-project-status-and-next.md`。

---

## 1. 已 ship milestones(2026-05-29 终态)

```
v0.11.0  M9    user-center (auth + register + billing + ledger)
v0.11.1  M10.5 LLM client OpenAI format (litellm proxy 在 .53:4000)
v0.12.0  M11.1 spawn 后台异步 LLM 任务 (4 endpoint, 19 测试)
v0.13.0  M11.2 MD + HPC + GPU pool (5 endpoint, 3 sim_type, 30+ 测试)
v0.14.0  M12   admin v2 + proposals (12 endpoint, 62 测试)  ← 今日 ship
```

**M9-M12 全 ship**。M13 推迟无 ETA(关 v1 + 反代瘦身,需 staging ≥2 周 + 13 FE 面板 smoke + user 显式批准,见 §6)。

Spec/plan 全 git:

| Milestone | Spec | Plan |
|---|---|---|
| M9 | `docs/superpowers/specs/2026-05-24-m9-user-center-design.md` | `docs/superpowers/plans/2026-05-24-m9-user-center.md` |
| M10.5 | `.../2026-05-25-m10.5-llm-client-openai-format-design.md` | `.../2026-05-25-m10.5-llm-client-openai-format.md` |
| M11.1 | (无单独 spec) | `.../2026-05-26-m11.1-spawn.md` |
| M11.2 | `.../2026-05-26-m11.2-md-hpc-design.md` | `.../2026-05-26-m11.2-md-hpc.md` |
| **M12** | `.../2026-05-27-m12-admin-v2-proposals-design.md` | `.../2026-05-27-m12-admin-v2-proposals.md` |

GitHub: https://github.com/NHNQNHNQ/PRAXIS-2 head=`e11080b` tag=`v0.14.0`

---

## 2. 当前部署状态(2026-05-29 21:00 起)

### 拓扑(双端口并存,M13 未触发)

```
.40:8088 → 老 server.py → .53:7788  v1 PRAXIS-hou (在线用户,冻结)
.40:8080 → praxis2_proxy.py → .53:8001  v2 PRAXIS-2 v0.14.0 (今日 ship)
```

### .53 backend 状态(M12 deploy 后)

- 进程:`gunicorn -c deploy/gunicorn.conf.py praxis2.server.app:make_app_default` × 3 worker(master 在 ps 看,M12 deploy 时新 master)
- 仓库:`/home/zkyd/data1/mzy/PRAXIS-2/`
- conda env:`~/software/miniconda3/envs/praxis2/`
- env file:`~/praxis2.env`(M12 deploy 加了 2 行 PRAXIS_ADMIN_RECONCILE_MAX_USERS + PRAXIS_PROPOSALS_PER_USER_PER_DAY)
- DB schema:**`alembic head = 006_proposals`**(M12 加的)
- docker:`praxis2-pg` (5432) + `praxis2-redis` (6379) 跑了 7+ 天

### .53 HPC stack(M11.2 deploy 留下)

- SLURM 单节点 zkyd:slurm-wlm 21.08 + munge,partition `gpu`,8 × A100
- GROMACS:`praxis-md-cuda` env(2026.0 conda-forge CUDA build,sm_80)
- `scripts/check_gpus.sh` 本地 nvidia-smi 版部署在 `.53:~/check_gpus.sh`
- M11.2 sbatch 模板已含 `conda activate praxis-md-cuda` + `OCL_ICD_VENDORS` 优化

### Smoke 验通(2026-05-29 23:00)

`.40:8080` 反代 → `.53:8001` 13 路由全注册:
- 200(公开):`/api/info` `/api/spawn/tasks` `/api/agents`
- 401(需 auth):10 个其他(`/api/admin/*` × 8 + `/api/me/*` × 2 + `/api/proposals`)
- **0 个 404 / 5xx**

---

## 3. M12 期间发现并修的 bug(重要的 3 个)

1. **C1 — `Ledger.record` 返 `balance_after` 而非 ledger.id**(spec/plan/Task 5 集体误标)
   - 修:`adjust_balance` 单独 `SELECT id FROM ledger ORDER BY id DESC LIMIT 1` 拿真 ledger.id
   - 不动 Ledger.record 签名(4 caller 零影响)
   - commit `784d97f` + spec/plan errata

2. **errata — `1 元 = 100 li`(M9 真相)vs M12 spec 笔误 `1 元 = 10 li`**
   - 影响 `/_user_row.balance_yuan` / `adjust_balance` 的 amount_yuan↔li 换算 / `get_stats` 的 outstanding_yuan
   - 全 spec/plan/code 改 `* 100` `/ 100`,commit `c5f5006`

3. **`audit_log.ip` INET 列 asyncpg → IPv4Address,`json.dumps` 不可序列化** → `/api/admin/audit-log` 500
   - 修 `_audit_row` 加 `str(d["ip"])` + 7 个 unit test
   - commit `e11080b`(Task 17 deploy 时发现)

---

## 4. Carry 池(M12 后,共 ~10 项)

### M12 自留 carry

| 优先级 | Carry |
|---|---|
| 🟡 中 | `withdraw` endpoint(`proposals.state='withdrawn'` 字段已留位) |
| 🟡 中 | `archive` endpoint(同上) |
| 🟢 低 | audit decorator 化(现在每 handler 手动 `audit_repo.insert`) |
| 🟢 低 | reconcile 加 advisory lock(并发 admin 操作可能 false positive) |
| 🟢 低 | `shipped_to` 自动从 git/PR 抽(现 admin decide 时手填) |
| 🟢 低 | proposal 多人评分流(`admin_scores JSONB` 已留位) |
| 🟢 低 | rate limit 用 redis(现 SQL count) |
| 🟢 低 | stats cache 1 min(现实时算) |
| 🟢 低 | `/api/me/proposals` incremental(现 page+limit) |

### 历史 carry(M11.x 时积累,M12 没碰)

| 优先 | Carry | 出处 |
|---|---|---|
| 🟡 中 | litellm `deploy/litellm_deepseek.yaml` 丢失(M11.2 deploy 误删,litellm 进程仍活,重启后丢) | `2026-05-27` handoff |
| 🟡 中 | `/api/info` version 字符串 hardcode `v0.11.1`(`auth/routes.py:629`) | M11.2 + M12 都没改 |
| 🟢 低 | spawn 进程 crash → stale running 修复(backend 重启 hook 标 stale → failed) | M11.1 |
| 🟢 低 | MD 进程 crash → stale running 修复 | M11.2 |
| 🟢 低 | FE MdModal smd/plumed 表单(submit 时填 sim_params) | M11.2 |
| 🟢 低 | spawn auto-retry on 429 | M11.1 |
| 🟢 低 | artifacts SSH-cat 流下载 | M10 |
| 🟢 低 | `.53` `~/praxis-md/<uuid>/` 累积清理(cron) | M11.2 |
| 🟢 低 | gpu_pool 30s in-memory cache | M11.2 |
| 🟢 低 | ssh known_hosts pinning | M11.2 |
| 🟢 低 | GROMACS OpenCL → CUDA 已切(M11.2 lifecycle 时);老 `praxis-md`(OpenCL)env 可删 | M11.2 |
| 🟢 低 | SLURM conf `DebugFlags=NO_CONF_HASH` 消 hash mismatch warning | M11.2 |
| 🟢 低 | sbatch.py 中 `/home/zkyd/...` hardcode 改 env 配 | M11.2 |
| 🟢 低 | M11.2 e2e lifecycle 测试用的 `reload-test-*@local` 测试 admin 清理 | M11.2 |
| 🟢 低 | M12 deploy smoke 用的 `m12-test-*@local` 清理 | M12 |

---

## 5. M13 准入条件(路线图 §9,2026-05-24 user 决策)

要全部满足才能开 M13(关 v1 + 反代瘦身,~2.5d 工作):

| # | 条件 | 当前状态 |
|---|---|---|
| 1 | M9-M12 全 ship + staging ≥ 2 周无红牌 | M9-M12 ✅ / **staging 2 周 起算 2026-05-29** |
| 2 | user 主导 13 FE 面板真跑 smoke | ⏸️ TODO(task #35,清单在交接文档底) |
| 3 | v1 retention / 流量 / 投诉日志确认可承受切换 | ⏸️ 看 v1 在线用户 |
| 4 | user 显式说"开 M13" | ⏸️ 战略决策 |

**Scheduled task 已建**(`praxis2-m12-staging-14d-review`,fireAt = 2026-06-12 22:00 +08)— 自动跑 backend log + audit 活跃度 + carry + M13 准入度报告。

---

## 6. 下一步具体待办

### 6.1 [user 必做] 13 FE 面板 smoke(入口 `http://10.102.106.40:8080`)

按关键路径,每项 ✅ 或记 issue:

**Auth + 基础**
- [ ] 登录 / 登出(UserBar)— cookie + role 正确
- [ ] Profile(ProfileModal)— research_field 等保存 + 持久化
- [ ] Balance(BalanceModal)— 余额 + ledger 流水

**文件 / Agent / Chat**
- [ ] Storage(StorageModal)— 上传 small file + 列表 + 下载 + 删
- [ ] AgentsBook(AgentsBookModal)— 13 学科 agent 列表
- [ ] AgentSidebar + ConversationSidebar — 历史对话切换 / 删
- [ ] Chat(MessageBubble)— 发消息,看 deepseek 回复 + thinking

**核心 module**
- [ ] Spawn(SpawnModal)— 提交,看流式进度 + done
- [ ] MD(MdModal)— GPU pool / 上传 pdb / submit standard / poll 看 done

**Admin v2 + Proposals(M12 新)**
- [ ] AdminPanel users — list / 搜索 / 调整余额 / freeze / unfreeze
- [ ] AdminPanel ledger — filter by user/kind
- [ ] AdminPanel audit-log — **验 ip 字段是 "127.0.0.1" 不是 [object Object]**(commit e11080b 修)
- [ ] AdminPanel stats — users/balance/runs/consumption 合理
- [ ] Proposals(用户端)— 提交一个 idea/bug/feature
- [ ] AdminPanel proposals — list / decide(verdict=ship/hold/...)

**边界 / 全局**
- [ ] ErrorBoundary — 故意制造 endpoint 失败看 friendly toast
- [ ] StatusStrip — 通知 / 状态

### 6.2 [可选] 顺手清几个 carry

任一可挑出来,~1-2h 完成:

- **`/api/info` version 字符串改 v0.14.0**(`auth/routes.py:629`,1 行)
- **litellm yaml 重建**(用现有 env DEEPSEEK_API_KEY + LITELLM_MASTER_KEY + 2 model 名)
- **scripts 清 test admin**(SQL `DELETE FROM users WHERE email LIKE 'reload-test-%' OR email LIKE 'm12-test-%'`)
- **老 `praxis-md`(OpenCL)env 删**(`conda env remove -n praxis-md`,空出 disk)
- **sbatch.py `/home/zkyd/` hardcode → env 配**(M11.2 carry,改成 `PRAXIS_MD_GROMACS_LOAD_CMD` env)

### 6.3 [scheduled] 14d 复盘自动跑

`praxis2-m12-staging-14d-review` task 自动在 2026-06-12 22:00 +08 触发,跑这些:
- ssh .53 看 backend 进程 + log 末尾 error
- alembic current 确认 head=006_proposals
- /api/info 看版本
- audit_log 14 天活跃度(action 分布)
- carry 池紧急项
- 出 staging 健康度 + M13 准入度报告

不需要 user 干预 — 醒来自跑,报告新会话。

---

## 7. memory 关键条目(自动 load)

`~/.claude/projects/-Volumes-T7-clade-learn/memory/`:

- `MEMORY.md` — 索引
- `project_m13_deferred.md` — **M13 推迟,v1 链路冻结**(2026-05-24 user 决策)

注:memory 写于 M12 ship 前,有一句 "不要自动 tag v0.14.0(M13 ship 后的事)" — 这条已超越,M12 ship 时 user 同意用 v0.14.0。memory 待 update,但不阻塞工作。

---

## 8. 下个会话最快路径

```
你打开新窗口 →
   1. cat docs/history/2026-05-29-handoff-after-m12.md(本文件)
   2. 决定走哪条:
      a) "做 FE smoke":你打开 .40:8080 跑 §6.1 13 面板,出 issue 列给我
      b) "清 carry X":说哪一项(§6.2 / §4),我起 spec 或 inline 改
      c) "等 14d 复盘":task 自动跑(2026-06-12),收到 task 完成通知再聊
      d) "开 M13":必须满足 §5 4 个条件再说
   3. memory 自动 load,git log / spec / plan 全在仓库
```

---

## 9. 还没填的 placeholder / 不确定项

- M13 触发时间(等 staging 2 周 + user 真跑 13 面板 + 用户主导决策)
- v1 用户迁移要不要做(`scripts/migrate_v1_users.py` 已有 stub,M13 时再决)
- v3 上云路线(单 backend → cluster + R2_PATTERNS,路线图 §10 列约束;不在 M13 范围)
- `/api/info` 真正 version 来源(应该 git tag 自动 detect 而非 hardcode)— carry

---

End of handoff. M12 ship 完成,staging 观察期开始。新窗口愉快。
