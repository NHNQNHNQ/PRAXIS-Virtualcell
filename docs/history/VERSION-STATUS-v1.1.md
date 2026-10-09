# v1.1 现状(增量稿)

> 锁定:2026-05-23 · base:`v1.0-uplift`(7a4fde0)→ HEAD `3cd19d1`
> 完整 152 skill uplift 见 `VERSION-STATUS-v1.0-uplift.md`,本文只列 v1.0-uplift 之后增量

## 1. 增量(2 commits)

| commit | 主题 | 文件 |
|---|---|---|
| `ccaaac5` | test(skills) 全量 schema-match 也跳过 hand-written run.py | tests/skills/test_schema_match.py |
| `3cd19d1` | fix(config+deploy) production HTTP 真打一发暴露的 2 个 bug | praxis2/config.py + deploy/push_backend.sh |

## 2. 修了什么

1. **`praxis2/config.py`** — `PRAXIS_SKILL_SSH_HOST/REMOTE_BRAINS/CONDA_INIT/TIMEOUT_S` 4 个 env 入 `_KNOWN_KEYS` 白名单。**修复 production-fatal bug**:v0.9.4 严格 fail-fast 把它们当未知拒掉,gunicorn 启动即 `ConfigError`。
2. **`deploy/push_backend.sh`** —
   - 拆 rsync(原写法把 `praxis2/* brains/* deploy/*` 平铺合并)
   - 新增 `PRAXIS_SKILL_REMOTE_BRAINS` 路径同步(SkillExecTool ssh 真跑路径)
   - `SERVICE_NAME=skip` 短路 systemctl restart(无 systemd/sudo 场景)

## 3. 验证证据

- `pytest tests/test_config.py` 8 / 8(白名单)
- `pytest tests/skills/` 931 passed / 2 skipped(uplift 全量,无回归)
- 真 push 一次 → `.53:/home/zkyd/data1/mzy/praxis2-{backend,brains}/` 双路径落地
- **production `/chat/stream` SSE 真打一发**:Mac gunicorn + ssh .53 真跑 `vina_gnina_dock`,24s,**392 events**(369 text_delta + 11 tool_start/end + 1 final),SSE 路径全通

## 4. v0.9.4 §7 边界状态(关掉的项)

- ✓ production `/chat/stream` SSE 端到端(§7 #2,30 min 估)→ 已验
- ✓ `deploy/push_backend.sh` 补 brains rsync(§7 #3,5 min 估)→ 已补
- 剩余 `v1.0-uplift §4 TODO #1`:141 个 GREEN `real()` 把 echo placeholder 换成真 CLI(70-140h,下一 milestone)
