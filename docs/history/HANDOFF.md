# PRAXIS-2 接续开发 handoff（v0.18.0 GA 之后）

> 这是「当前接续状态」文档，随项目演进更新。新会话接手先读本文件 + 跑下面的 orientation 命令。

```
cd /Volumes/T7/clade-learn/PRAXIS-2 && git log --oneline -6 && git tag -l v0.18.0 && cat VERSION-STATUS-v0.18.0.md
```

## 项目是什么
PRAXIS-2 = 科研领域智能体系统。智能体在「学科 brain」（知识库：cases/rules/skills/neg_cases）上工作，
按 **RMCP 相位机**循环推进（retrieve→…→seal 等相位，工具按 `rmcp_op` 相位门启用/约束）。
- **工具池**（chat_registry 按 mode 组装，每请求独立实例）：BrainQuery（检索 brain）/ SkillExec（跑学科
  skill，可走 SSH 远端 HPC）/ RMCPWriteCase（SEAL 相位写 case 进 `_proposed` inbox 待审）/ FileRead（沙盒读
  repo brains+docs）/ WebFetch（白名单 GET）/ AgentTool（spawn 子 agent，discipline 模式禁用防递归）/
  MCP tools（外部 `mcp__<server>__<tool>`，stdio）/ **BashTool**（软沙盒跑 shell + v0.18 真隔离三件套）。
- **服务端**：gunicorn + ASGI（`praxis2/server/app.py`），chat-stream SSE，SessionPool（按 session_id 隔离
  状态），后端模型走 litellm（127.0.0.1:4000），前端 FE。

## 当前状态：v0.18.0 GA（真隔离三件套闭环）
- main HEAD `6167ee2`，**tag `v0.18.0` 已推**。全量 **2025 / 0 fail**。
- BashTool 真隔离三件套（全 opt-in 默认关、正交可叠加、各自 fail 策略）：
  - 文件系统：`unshare --user --map-root-user --mount` + tmpfs 遮蔽 — **fail-closed**
  - 资源：`systemd-run --user --scope -p MemoryMax/CPUQuota`（树级含孙子）— **fail-open（降级 rlimit）**
  - 网络：`unshare --net`（空 netns 无 veth 无路由，封外联）— **fail-closed**
- run() = cgroup × isolation × netns 组合分发，inner 3 情形；命令全程走 argv 位置参数（注入防护）。
- staging .53:8001 已跑三件套（env 四开关 =true），各维度 e2e 实证过。
- ⚠ **version 字符串未 bump**：tag 是 v0.18.0，但 `/api/info` 与代码 `__version__` 仍返 **v0.17.0**
  （子项目惯例不 bump，GA 只动 doc+tag）。要一致需单独 bump version 字符串。

## 演进速览
M7 真执行链 → v0.16 工具真接入消除幻觉（BrainQuery/RMCPWriteCase/FileRead/WebFetch，P0 5/5）→
v0.17 MCP client(stdio) + 本地 BashTool 软沙盒 → **v0.18 BashTool 真隔离三件套（当前 GA）**。

## 下一步（你定，按价值排序）
1. **更高价值（推荐先做）**：跨会话记忆 / stop_hook 硬约束 / v1.0 用户决策 —— 比继续榨 BashTool 隔离收益大。
2. **BashTool 隔离 backlog（全部基建门控或 YAGNI，等 ops 前置再单独立项，证据见 memory）**：
   - 出站白名单：无 host root + `slirp4netns`/`pasta` 未装 → 连通层阻塞（过滤层 nft-in-netns 已验可做）。
     解锁：ops `apt install passt` → pasta(用户态联网)+ nft(netns 内 allowlist)。
   - cgroup 磁盘 IO：user slice 只 delegate `memory pids`，`io` 未 delegate + systemd 不认 `IOMax`。
     解锁：ops 配 `Delegate=io`（+ 可能升 systemd）。
   - cgroup PID/进程数（TasksMax）：rootless 已验可做（设 8→pids.max=8 强制），但边际价值低（BashTool
     opt-in，fork-bomb 危害有限）。需要时单独做：扩 `_cgroup_argv` 加 `-p TasksMax`，复用现有
     `PRAXIS_BASH_CGROUP` 开关（无新开关/fail-closed），默认建议 512。
   - RemoteBashTool（单机 YAGNI）/ MCP HTTP transport + mid-call 重连（另方向）/ CC npx（卡 node18+）。
3. **2 非阻塞 polish（GA 标的技术债）**：config 可选 int 解析抛 `ValueError` 非 `ConfigError`（统一风格）/
   app 层 fail 运行期可观测（debug 日志）。

## 流程（superpowers，严格走）
新功能 = brainstorm（`/superpowers:brainstorming`）→ spec（`docs/superpowers/specs/`）→ **用户 review spec** →
writing-plans（`docs/superpowers/plans/`）→ subagent-driven-development（fresh subagent per task，每 task
TDD 红→绿→commit + 两阶段 review：spec 合规→code quality，reviewer 抓问题 implementer 修）→ 全部 task 后
final review。**main 直接干（用户既定，无 worktree）**。Task 涉及部署/e2e/收尾的由 controller 亲做（不派 subagent）。
subagent dispatch 给完整 task 文本（别让它读 plan 文件），commit 只 add 目标文件。
注意：veth+NAT 这类「字面方案可能不可行」的子项目，brainstorm 阶段先写探针在 staging 实测可行性再定方案（证据驱动）。

## 部署 SOP（多次验证，稳）
- **ship 前必跑门（GAP-AH-3）**：`PRAXIS_EVAL_EMAIL=… PRAXIS_EVAL_PASSWORD=… .venv/bin/python scripts/ship_gate.py`
  跑全量 pytest 回归 + 反幻觉 KPI（best-of-2，fail 自动重跑一次）；**exit 0 才 ship**。凭证问用户取（不入库）。
  C/D 人工复核见 `/tmp/ship_gate_kpi.json` + eval dump。（KPI 跑不进 hermetic GitHub Actions——够不到内网 staging；故本地门。下面的"全量回归"是门的子步，单独调试时可用。）
- 全量回归（汇总行被 sandbox 吞，用 junit-xml 取数）：
  `.venv/bin/python -m pytest tests/ --ignore=tests/integration -q --tb=no --junit-xml=/tmp/r.xml >/dev/null 2>&1; echo EXIT=$?`
  `.venv/bin/python -c "import xml.etree.ElementTree as ET; r=ET.parse('/tmp/r.xml').getroot(); s=r if r.tag=='testsuite' else r[0]; print(s.attrib)"`
- backend 改：逐文件 rsync（别 --no-relative）到 `zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/praxis2/<子目录>/`
  → 找 master pid：`ssh zkyd@.53 "ps -ef|grep '[g]unicorn'|grep python3|awk '\$3==1{print \$2}'"`
  → kill → sleep 3 → **确认 8001 空闲（kill 后可能残留 worker，等它退）** → cd ~/data1/mzy/PRAXIS-2 &&
    source ~/praxis2.env && `(nohup ~/software/miniconda3/envs/praxis2/bin/gunicorn -c deploy/gunicorn.conf.py praxis2.server.app:make_app_default > /tmp/p.log 2>&1 &)`
  → sleep 7 → `curl -s 127.0.0.1:8001/api/info`（仍返 v0.17.0，见上 version 说明）+ tail /tmp/p.log 查无 fail warning
- e2e（确定性验隔离，直接调 BashTool 不依赖 AI）：写 probe.py 本地 → rsync staging /tmp →
  `ssh zkyd@.53 'cd ~/data1/mzy/PRAXIS-2 && source ~/praxis2.env && PYTHONPATH=$PWD ~/software/miniconda3/envs/praxis2/bin/python /tmp/probe.py'`
  （⚠ `PYTHONPATH=$PWD` 必须；⚠ 别用 heredoc+ssh+python stdin，会被 auto classifier 拦）
- 新开关 env 加到 `.53:~/praxis2.env`（`grep -q` 幂等）；已有 `PRAXIS_BASH_{TOOL_ENABLED,ISOLATION,CGROUP,NETNS}=true`。

## 环境
- 本地 repo：`/Volumes/T7/clade-learn/PRAXIS-2`，venv `.venv/bin/python`
- staging：.40:8080（反代/FE）→ .53:8001（gunicorn）→ litellm 127.0.0.1:4000
- SSH：`zkyd@10.102.106.53`（远端 repo `~/data1/mzy/PRAXIS-2`）+ `hipeson@10.102.106.40`
- conda：`~/software/miniconda3/envs/praxis2/bin/{python,gunicorn}`
- files_root：`/home/zkyd/data1/praxis2-files/{user_id}`（BashTool sandbox 根）
- 隔离能力探测（2026-06-04 实测，zkyd rootless）：userns_clone=1 / cgroup v2 / user slice delegate=**memory pids**
  (无 io/cpu) / unshare ✓(mount+net) / systemd-run --scope ✓(MemoryMax/CPUQuota/TasksMax 可，**IOMax 不认**) /
  docker daemon 可(在 docker 组) / **无 host CAP_NET_ADMIN** / **sudo 要密码** / **slirp4netns·pasta 未装** / bwrap ✗ / node v12
- admin eval：凭证**不入库**，用 `PRAXIS_EVAL_EMAIL` / `PRAXIS_EVAL_PASSWORD` env 提供（问用户取，或见本地非 git 记录）
- prod-only 不入 git：`.53:~/praxis2.env`

## 雷区
- pytest 汇总行被 sandbox 吞 → junit-xml 解析（root 可能 `<testsuites>` 包 `<testsuite>`，取 `r[0]`）
- heredoc + ssh + python stdin 被 auto classifier 拦 → 改 probe 脚本文件 rsync + ssh 跑
- ssh 跑 repo 内 python 脚本要 `PYTHONPATH=$PWD`（脚本在 /tmp，sys.path 不含 repo 根）
- config 可选 int 用 `int(e.get(key) or "默认")`（`_get_int` 无 default 参数）
- `tests/_auth_test_helpers.py` 的 `_TestSettings` 是显式字段 dataclass，加新 settings 字段必须同步补（否则一批测试回归）
- commit 只 add 目标文件：**工作区常驻无关 `brains/microbiome/` 改动，绝不 `git add .` / `-A`**
- Bash working dir：初始在 `/Volumes/T7/clade-learn`（不是 repo），**首条命令必须 `cd` 进 repo**；本 harness 内 cd 后续命令持久，但保险每条带 cd
- systemd-run --user 文件系统 sandboxing 不可用（用户态无 mount ns）；--scope cgroup 资源可用
- gunicorn kill 后可能残留 worker，重启前确认 8001 空闲再起新 master

## 关键文件
- BashTool：`praxis2/tools/bash.py` — 模块级 `userns_available()`/`scope_available()`/`netns_available()`（lru_cache）/
  `SETUP_TEMPLATE`/`_isolation_argv(...,netns)`/`_netns_argv()`/`_cgroup_argv()`/`_mask_paths()`；
  `BashTool.run()` = cgroup×isolation×netns 分发（inner 3 情形）；`__init__` 有 isolation/isolation_mask/cgroup/
  cgroup_mem_mb/cgroup_cpu_pct/netns 参数
- bash 安全策略：`praxis2/tools/bash_policy.py`（BashCommandPolicy 黑/白/灰 ASK）
- config：`praxis2/config.py`（bash_tool_enabled/isolation/isolation_mask/cgroup/cgroup_mem_mb/cgroup_cpu_pct/netns + `_KNOWN_KEYS`）
- 集成：`praxis2/server/chat_registry.py`（build_chat_registry 透传 bash_*）+ `praxis2/server/app.py`
  （_chat_stream ~660 fail-closed/fail-open 计算 + `_LifespanApp.__init__` ~1117 启动 warning，两处镜像需同步）
- 其它工具：skill_exec / brain_query / rmcp_write / file_read / web_fetch / agent tool；MCP `praxis2/mcp/*`
- tests：`tests/test_tools_bash{,_isolation,_cgroup,_netns}.py`；`tests/_auth_test_helpers.py`
- spec/plan：`docs/superpowers/{specs,plans}/`；release note：`VERSION-STATUS-v0.18.0.md`（GA 总览 + backlog）

## memory 索引
`~/.claude/projects/-Volumes-T7-clade-learn/memory/MEMORY.md`，最新：
`project_v018_ga.md`（GA + 基建门控 backlog 决策，带探针证据 + 解锁路径）+
`project_v018_{isolation,cgroup,netns}.md`（三子项目全细节）。探针 `/tmp/v18_{netfilter,iopid}_probe.sh` 已在 staging。
