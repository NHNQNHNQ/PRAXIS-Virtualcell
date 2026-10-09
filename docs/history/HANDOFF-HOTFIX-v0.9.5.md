# Hotfix 待提交说明(给另一个会话)

> 写给:正在 PRAXIS-2 补 51 个 skill `real()` 的那个会话
> 写者:跑"production /chat/stream 真打一发"的会话
> 日期:2026-05-23
> 当前 HEAD:`7a4fde0 docs(v1.0-uplift)`(你那边的)
> 上一个 tag:`v0.9.4` → `9f797a1`

---

## 一句话

我这边把 v0.9.4 §7 P0 的两件 **后两件** 做完了(真打 /chat/stream + push 脚本补 brains rsync),过程中暴露并修了一个 **server 起不来的 production-fatal bug**。这三处改动应该 **先于你后续 skill 提交独立打一个 hotfix commit** 入版本,然后你继续干你的。

---

## 我的改动(working tree)

```
deploy/push_backend.sh   | 47 +++++++++++++++++++-----------
praxis2/config.py        |  4 ++++
```

**不要带** `frontend/package-lock.json`(那是你那边的版本号 bump,跟 hotfix 无关)。

### 1. `praxis2/config.py` — production-fatal bug 修复

`_KNOWN_KEYS` 严格白名单 + fail-fast 把 `PRAXIS_SKILL_SSH_HOST / REMOTE_BRAINS / CONDA_INIT / TIMEOUT_S` 当未知拒掉。**结果:任何按 v0.9.4 §5.3 文档把 SkillExec env 注入 server 的人,gunicorn 直接抛 `ConfigError` 死在启动**。

`tools/skill_exec.py:33,185-187` 是从 `os.environ` 直接读这 4 个 env 的,config 不解析它们 —— 所以白名单加进去就够,无字段、无校验。改动:

```python
# 末尾追加
"PRAXIS_SKILL_SSH_HOST", "PRAXIS_SKILL_REMOTE_BRAINS",
"PRAXIS_SKILL_CONDA_INIT", "PRAXIS_SKILL_TIMEOUT_S",
```

验证:`pytest tests/test_config.py -x` 8/8 全过。

### 2. `deploy/push_backend.sh` — 3 处真改

A. **拆 rsync**(原写法是 bug):
```
# 原(把 3 个 source 的内容平铺合并到同一个 dest,brains/* 跟 praxis2/* 混在一起)
rsync ... praxis2/ brains/ deploy/ ${REMOTE}:${BACKEND_PATH}/

# 新(各落独立子目录)
rsync ... praxis2/ ${REMOTE}:${BACKEND_PATH}/praxis2/
rsync ... brains/  ${REMOTE}:${BACKEND_PATH}/brains/
rsync ... deploy/  ${REMOTE}:${BACKEND_PATH}/deploy/
```

B. **新增 SkillExec 真路径同步**(v0.9.4 §6 边界写的"未补"):
```
if [ -n "${PRAXIS_SKILL_REMOTE_BRAINS:-}" ]; then
    ssh "${REMOTE}" "mkdir -p '${PRAXIS_SKILL_REMOTE_BRAINS}'"
    rsync ... brains/ ${REMOTE}:${PRAXIS_SKILL_REMOTE_BRAINS}/
fi
```
SkillExecTool ssh 到 `${PRAXIS_SKILL_REMOTE_BRAINS}/<brain>/...` 跑 run.py,跟 `${BACKEND_PATH}/brains/`(server 本地枚举 SKILL.md 用)是两个独立位置,都得有。

C. **`SERVICE_NAME=skip` 短路**:无 systemd unit / 无 sudo 的开发场景跳过 `sudo systemctl restart`。

---

## 已验证(给你信心)

1. **真 push 到 .53 跑过一次**:`/home/zkyd/data1/mzy/praxis2-backend/{praxis2,brains,deploy}` 落地 + `/home/zkyd/data1/mzy/praxis2-brains/` 增量同步,均成功。
2. **production /chat/stream SSE 真打一发**(Mac 本地 gunicorn + ssh .53 跑 skill,24s):
   - 392 SSE events:369 text_delta + 11 tool_start/end + 1 final
   - LLM(DeepSeek anthropic-compat)→ tool_use `SkillExec({name:"vina_gnina_dock", inputs:{...}})` → `exec_via: "ssh zkyd@10.102.106.53"` → 远端 run.py 真跑 → 回结构化 JSON
   - 最终 `final: escalated` 是因为 LLM 把 `receptor_pdb:"1IEP"` 当字符串而不是文件路径传(SKILL.md input contract 没强约束),不是 server 路径问题 —— SSE 路径全通

---

## 建议提交方式

只提我那两个文件,独立 commit:

```bash
git add deploy/push_backend.sh praxis2/config.py
git commit -m "fix(config+deploy): production HTTP 真打一发暴露的 2 个 bug

1. praxis2/config.py: PRAXIS_SKILL_* (SSH_HOST/REMOTE_BRAINS/CONDA_INIT
   /TIMEOUT_S) 4 个 env 入 _KNOWN_KEYS 白名单 — v0.9.4 严格 fail-fast
   把它们当未知拒掉,导致按 §5.3 文档注入 SkillExec env 起 gunicorn
   直接抛 ConfigError;tools/skill_exec.py 是从 os.environ 直接读,
   config 不解析,只需白名单放行。

2. deploy/push_backend.sh:
   - 拆 'praxis2/ brains/ deploy/ → BACKEND_PATH/' 平铺为 3 路独立子目录
     (原写法把 praxis2/* / brains/* / deploy/* 平铺合并)
   - 新增可选 brains/ → \${PRAXIS_SKILL_REMOTE_BRAINS}/ 同步(SkillExecTool
     ssh 真跑路径,与 BACKEND_PATH/brains 是两处独立位置)
   - SERVICE_NAME=skip 短路 systemctl restart(无 systemd/sudo 场景)

验证:
- pytest tests/test_config.py 8/8 全过
- 真 push 一次 → .53 双路径落地
- production /chat/stream SSE 真打一发(Mac gunicorn + ssh .53 真跑
  vina_gnina_dock)24s,392 events,SSE 路径全通
"
```

---

## 之后(看你节奏)

你那边 5 个 skill commit + 这个 hotfix 提交后,够打一个 **v0.9.5** tag:

```bash
git tag -a v0.9.5 -m "v0.9.5: P0 skill real-uplift 起步 + production HTTP 真验通过"
```

VERSION-STATUS 状态文档要更新的两处(可在 v0.9.5 状态文档里改):
- §6 边界 "真 chat-stream HTTP(SSE)端到端 | 未验" → 已验
- §6 边界 "deploy/push_backend.sh 加 brains rsync | 未补" → 已补
- §7 P0 "production /chat/stream SSE(30 min)" → done
- §7 P0 "deploy/push_backend.sh 补 rsync brains/(5 min)" → done
- §7 新增条目:配置白名单 hotfix(已修在本 commit)

但不强求,你看节奏决定。

---

## 当前还在运行的资源(可关)

- Mac docker compose:`deploy-postgres-1` + `deploy-redis-1`(端口 5432/6379)
  关:`cd deploy && POSTGRES_PASSWORD=praxis2-dev-pw docker compose down`(加 `-v` 清 volume)
- 我那边 gunicorn 已经 kill 干净,不留进程

SSE 真跑日志在 `/tmp/praxis_sse_run/{sse.log,gunicorn.log,chat_body.json}`,需要复看就在那。
