# PRAXIS-2 交接(2026-05-30):2 个真 bug 修复进行中(Bug B 未完成)

> 给新会话窗口。读完即接续。仓库根 `/Volumes/T7/clade-learn/PRAXIS-2/`。
> 前交接 `docs/history/2026-05-29-handoff-after-m12.md`(M12 ship 状态)。
> 本文件 = 2026-05-30 FE smoke 发现 2 个真 bug 后的修复进度。

---

## 0. 一句话现状

FE smoke(staging `.40:8080`,admin 账号密码见 env 不入仓)发现 **2 个真 bug**,根因都已坐实。**Bug B 修了一半(未 commit、未 deploy)**,Bug A 还没动。

---

## 1. 两个 bug(根因已坐实)

### Bug B —— 对话第 2 轮"(空响应)"【修复进行中】

- **现象**:deepseek-v4-pro 第 1 轮长回复正常(173s),第 2 轮"(空响应)"16s。FE 报"上游模型返回 0 tokens"。
- **根因**:`PRAXIS_MAX_TOKENS=4096`(`.53:~/praxis2.env`)对推理模型 deepseek-v4-pro **太小** → `finish_reason=length` 截断。`praxis2/core/query.py` 的 max_tokens recovery(M1 基础版)`continue` 重试时**不提高预算** → 确定性重复截断。
- **实测证据**(curl 生产 litellm `.53:4000`):
  | max_tokens | finish | content_len | reasoning_tok |
  |---|---|---|---|
  | 4096 | length(截断) | 5555 | 819 |
  | **8192** | **stop(完整)** | 4046 | 308 |
  | 12288 | stop | 3229 | 1769 |
  - **8192 就跨过截断点** → boost 修复方向正确。
- **deepseek-v4-pro 真实输出上限实测 = 393216(384K)**(不是 1M,1M 是上下文窗口)。`max_tokens=1000000` → litellm 报 `valid range is [1, 393216]`。

### Bug A —— 提案提交 422【未开始】

- **现象**:用户端 `POST /api/proposals → 422 invalid_kind`,提案模块 **100% 必现**提交失败。
- **根因**:纯 FE 契约错位。
  | 端 | kind 取值 |
  |---|---|
  | FE `frontend/src/components/ProposalsModal.tsx:75-78`(默认 `useState('experiment')`) | `experiment`/`dataset`/`paper`/`other` |
  | 后端 `praxis2/proposals/repo.py:10`(= M12 spec + DB `CHECK` 硬约束,权威) | `idea`/`feature`/`bug` |
  - **零交集** → 任何提交都 422。
- **修法**:纯 FE 改 `ProposalsModal.tsx`(4 个 `<option>` + `KIND_LABEL`(第6行)+ 默认值 → `idea`/`feature`/`bug`)。需 **rebuild dist + deploy FE**。
  - 顺带核对 `STATUS_LABEL`(第9-11行 `pending/shipped/held/rejected`)对不对后端真实 status 值。

---

## 2. Bug B 已做的改动(⚠️ 未 commit、未 deploy)

`git status`:`M praxis2/core/query.py` + `M praxis2/core/state.py` + `?? tests/test_core_query_maxtokens_boost.py`

1. **`state.py`** 加字段 `max_tokens_boost: int = 0`(recovery 累加的额外预算)✅ 已落
2. **`query.py:86`** `max_tokens=settings.max_tokens + state.max_tokens_boost` ✅ 已落
3. **`query.py` recovery 点②**:`state.max_tokens_boost += settings.max_tokens`(每次 recovery 倍增)✅ 已落
4. **`tests/test_core_query_maxtokens_boost.py`** 2 个测试 ✅ 已写,**19/19 query+state 测试全绿**(red→green 验过)

### ⚠️ 还差(必做,未完成)

- [ ] **`query.py` 加 boost 上限 cap**(防累加超 393216 让 litellm 报错)。原计划在 `AbortSignal` 类前加模块常量:
  ```python
  _MAX_TOKENS_CEILING = 393216  # deepseek-v4-pro 实测上限
  ```
  然后 `query.py:86` 改成 `max_tokens=min(settings.max_tokens + state.max_tokens_boost, _MAX_TOKENS_CEILING)`。
  **这次 Edit 上一轮被打断没落地(grep _MAX_TOKENS_CEILING = 0)**。当前生产配置 16384 base + 2 recovery = 最高 49152,远低于 384K,不会撞;但 cap 是防御性必加。
- [ ] **调 `.53:~/praxis2.env` 基础值**:`PRAXIS_MAX_TOKENS` 4096 → **16384**(用户认可方向;4096 对 384K 模型太保守是频繁截断根源)。改完重启 backend。
- [ ] 给 boost 测试补一个 **cap 边界测试**(boost 累加不超 ceiling)。
- [ ] commit + push + rsync `query.py`+`state.py` 到 `.53` + `kill -HUP` reload。

### 诚实保留项(根因不确定性)

我早前"reasoning 烧光 content=0"的判断基于 `max_tokens=120` 极端实验;真实 4096 下 content **出得来**(5555 字符),只是 `finish=length` 截断。**boost 修复确实解决"4096 截断"这个真问题**(实测 8192 跨过),但我**无法 100% 断言**它就是用户那次"16s 空响应"的唯一原因(那次可能是 tool-call 场景下 reasoning 占比更高的特例,未能精确复现)。修复有效且方向对,但别夸大成"必然根治"。

---

## 3. 部署/验证环境备忘

- SSH:`ssh zkyd@10.102.106.53`(已在 `.claude/settings.local.json` 放行;rsync 同)
- litellm 直测:`curl -s -X POST http://127.0.0.1:4000/v1/chat/completions -H "Authorization: Bearer <litellm-master-key,见 .53 env>" ...`(在 `.53` 上跑)
- backend:`.53` gunicorn,**stop+nohup-start 起的**(非 systemd,重启不自动拉起)。reload 用 `kill -HUP <master_pid>`(`pgrep -of "gunicorn.*praxis2"`)。
- ⚠️ **多文件 deploy 别用裸 HUP**:上次 HUP 把 backend 搞挂过(carry #6),已救回。多文件改动建议 stop+start 或确认 reload 成功。
- 本地全量测试有 4 类 `asyncssh` collection error + server_app 链 FAIL,**全是本地 venv 缺 asyncssh(prod-only),非回归**,忽略。

## 4. gstack FE smoke 教训(避免重蹈)

- gstack browse daemon **命令必须串行**,并行发多条会抢占重启 daemon → session 丢 → 全假阴性(我犯了 3 次)。用单进程 shell 脚本顺序跑。
- 这个 SPA 的 modal 容器 class 是 **`.modal`**(不是 `[role=dialog]`!),选择器要用 `.modal` 或 `.modal-backdrop`。
- 底栏图标按钮真实 title:`📁我的存储` `🪐后台任务` `📝我的提案` `👤个人资料` `📥Admin Inbox` `ℹ️后端信息`。

## 5. FE smoke 已验证(部分)

✅ 真实通过:登录/admin role、Balance modal、Chat(deepseek 真回复)、AgentsBook(13 学科手册)、主界面。
⚠️ 发现的额外问题:顶栏版本号 FE hardcode `v0.10.0`(后端已 v0.14.0)—— 又一处 FE stale,可顺手修。
❌ 未干净跑完:Storage/Profile/Spawn/MD/Admin 5tab/Proposal(daemon 折腾没跑完,但截图证明 modal 都正常打开,功能大概率 OK,Proposal 除外=Bug A)。

## 6. memory 已记

- `~/.claude/projects/-Volumes-T7-clade-learn/memory/project_two_bugs_20260530.md`(两 bug 根因)
- `MEMORY.md` 索引已加条目

---

## 7. 下个窗口最快路径

```
cd /Volumes/T7/clade-learn/PRAXIS-2 && cat docs/history/2026-05-30-handoff-two-bugs-WIP.md
```

接续顺序建议:
1. 先把 **Bug B 收尾**(§2 那 4 个 [ ]):加 cap → 补测试 → 调 env → commit/push/deploy/HUP → curl 验证生产 `/api/info` 还在 + deepseek 第 2 轮不再空响应。
2. 再修 **Bug A**(§1,纯 FE):改 ProposalsModal kind → rebuild FE dist → deploy → smoke 验证提案能提交。
3. 顺手:FE 版本号 `v0.10.0` → `v0.14.0`(§5)。
```
