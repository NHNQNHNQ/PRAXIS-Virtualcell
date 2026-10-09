# v0.18 子项目1:BashTool 文件系统真隔离(unshare user namespace)

**日期**: 2026-06-03 · **状态**: 设计待批 · **范围**: v0.18 第一个子项目
**前置**: v0.17.0 GA(软沙盒 opt-in,`b1dfc1c` / tag v0.17.0)

---

## 0. 目标与非目标

### 目标
让启用 BashTool 的命令在 **user + mount namespace** 内运行,文件系统视图被遮蔽:绝对路径**读不到其它用户的 `files_root` 子目录**,也读不到敏感配置(`praxis2.env` / `.ssh` 等)。补 v0.17 软沙盒「同 uid 跨用户读」的最大短板。

### 非目标(本子项目明确不做)
- **资源隔离(cgroup MemoryMax/CPUQuota)** — 保留 v0.17 rlimit;cgroup 资源(管孙子进程)留 v0.18 后续子项目(用户本轮只选了文件系统维度)
- **网络隔离(PrivateNetwork / unshare --net)** — 不做
- **进程隔离(PID namespace)** — 不做
- **RemoteBashTool / MCP HTTP transport** — v0.18 其它独立子项目

---

## 1. 关键决策(brainstorm 结论)

| # | 决策 | 理由 |
|---|---|---|
| 1 | 隔离维度 = **仅文件系统视图** | v0.17 软沙盒最大短板(同 uid 跨用户读);资源/网络本轮不做 |
| 2 | 机制 = **unshare user+mount namespace + tmpfs 遮蔽** | rootless(staging `unprivileged_userns_clone=1` 已验);systemd-run `--user` 做不了 mount sandboxing(实测 `Operation not supported`);docker 太重(镜像+daemon+~100ms)。(实现阶段从 bind empty 目录升级为 tmpfs,见 §3.1) |
| 3 | 降级 = **fail-closed** | 启动探测 userns;不可用 → 警告 + Bash 不注册(启用隔离即为安全,不悄悄降级软沙盒) |
| 4 | **opt-in 开关 `PRAXIS_BASH_ISOLATION`,叠加在 v0.17 防护上(正交)** | 不替换黑白灰 policy / cwd 校验 / rlimit / env 裁剪 |

### 探测记录(2026-06-03 staging .53)
- systemd 249 / cgroup v2 / `unprivileged_userns_clone=1` / `unshare` ✓ / `docker` ✓(zkyd 有 daemon 权限)/ `bwrap` ✗ / node v12.22.9
- **systemd-run `--user` 文件系统 sandboxing 实测失效**:`--pipe --wait` 能拿输出+exit code,但 `InaccessiblePaths`/`ProtectHome` 不生效、`TemporaryFileSystem` 报 `Failed to set up mount namespacing: Operation not supported`(用户态无 mount ns 权限)
- **`unshare --user --map-root-user --mount` 内 `mount --bind` 实测生效**(bind empty 遮蔽 secret → 读不到)

---

## 2. 架构

`BashTool.run` 执行层二分(由 isolation 开关决定):
- **isolation off**(默认 / v0.17 现状):`create_subprocess_shell(command, ...)`
- **isolation on**:`create_subprocess_exec("unshare", "--user", "--map-root-user", "--mount", "--", "/bin/sh", "-c", SETUP, "praxis-bash", sandbox, files_root, command, ...)`

其余执行机制**全部不变**:cwd 校验、`wait_for` 超时、rlimit preexec_fn、env 裁剪(`_sanitized_env`)、流式 drain、输出截断。命令裁决(`BashCommandPolicy` 黑/白/灰 + ASK bridge)在 permission 层,与执行层正交,不变。

### 职责边界
- **隔离是执行层的一个新分支**:off 走 shell,on 走 unshare-exec。除 subprocess 创建方式外,两分支共享后续处理(超时/drain/截断/ToolResult)。
- **启动探测**(独立函数):一次性检测 userns 可用性,缓存结果,供注册决策。

---

## 3. 隔离机制

### 3.1 unshare 包装(命令注入防护)
用 **argv 模式**(`create_subprocess_exec`),user command 作为位置参数传入,**不拼进 shell 脚本字符串**:

```python
argv = [
    "unshare", "--user", "--map-root-user", "--mount", "--",
    "/bin/sh", "-c", SETUP_TEMPLATE,
    "praxis-bash",   # $0
    sandbox,         # $1  server 配置(已 cwd 校验的 sandbox_root)
    files_root,      # $2  server 配置
    command,         # $3  user command(位置参数 → 不参与脚本解析 → 无注入)
    mask_paths,      # $4  敏感遮蔽清单(Python 侧算好,换行分隔的绝对路径)
]
```

`SETUP_TEMPLATE`(固定常量,只用位置参数 `$1..$5`,不含任何拼接的 user input):

```sh
set -e
mkdir -p /tmp/.praxis-sbref
mount --bind "$1" /tmp/.praxis-sbref      # 1. 保存 this_user sandbox 真实内容
mount -t tmpfs praxis-empty "$2"          # 2. tmpfs 遮蔽整个 files_root(藏所有 user_id;namespace 私有+退出回收)
mkdir -p "$1"                              # 3. 在遮蔽层上重建 this_user 挂载点(写 tmpfs,不穿透 host)
mount --bind /tmp/.praxis-sbref "$1"      # 4. 把真实 sandbox 暴露回原路径
# 遮蔽敏感($4 = Python 侧算好的绝对路径,换行分隔;不依赖 namespace 内 env)
printf '%s\n' "$4" | while IFS= read -r p; do
  [ -z "$p" ] && continue
  if [ -d "$p" ]; then mount -t tmpfs praxis-empty "$p" 2>/dev/null || true
  elif [ -e "$p" ]; then mount --bind /dev/null "$p" 2>/dev/null || true
  fi
done
cd "$5"                                    # cwd($5);命令工作目录(plan 细化:用位置参数而非 $1)
exec bash -c "$3"
```

- **用 tmpfs 遮蔽**(staging userns 内 e2e 实测可行 + namespace 私有 + 退出回收 + 不污染 host)。最初设计用 bind empty 目录,但 code review 发现 `mkdir "$1"`(sandbox 在 files_root 下)会穿透 bind 写到 host empty 目录、累积 user_id,改 tmpfs 根治。
- **命令注入防护**:`command` 是 `$3` 位置参数,`exec bash -c "$3"` 执行;`SETUP_TEMPLATE` 固定不含 user input,即使 command = `x"; rm -rf /; "` 也只是 `$3` 的值,不破坏脚本。
- 内层 `bash -c "$3"` 保留 v0.17 的 shell 语义(管道/重定向),与软沙盒行为一致。

### 3.2 敏感遮蔽清单
**由 BashTool 在 Python 侧算好完整绝对路径清单**(换行分隔传入 `$4`,不依赖 namespace 内 env):默认 = `~/praxis2.env` / `~/.pgpass` / `~/.netrc`(文件)+ `~/.ssh` / `~/.aws` / `~/.config/gcloud`(目录),`~` 用 `os.path.expanduser` 展开。可经 `PRAXIS_BASH_ISOLATION_MASK`(逗号分隔绝对路径)追加。SETUP 脚本对每条:目录 bind empty、文件 bind `/dev/null`。

### 3.3 遮蔽语义
- `files_root` 整个被 empty 遮蔽 → 其它 `user_id` 目录全不可见;仅 this_user sandbox bind 回来,可见可写。
- 敏感配置读到空(`/dev/null`)或目录为空。
- 系统目录(`/usr` `/bin` `/lib` `/etc`)不动 → 命令正常运行。
- `/etc/passwd` 等系统文件仍可读(只读),但 v0.17 黑名单已挡这些 token。

---

## 4. 集成 + 开关 + 启动探测

- **config.py**:`bash_isolation: bool = False` + `PRAXIS_BASH_ISOLATION`(`_get_bool`)+ `_KNOWN_KEYS`;`bash_isolation_mask: str = ""`(可选追加遮蔽)。
- **BashTool.__init__**:加 `isolation: bool = False` + `isolation_mask: list[str] = []`。
- **启动探测**(`praxis2/tools/bash.py` 模块级函数 `userns_available() -> bool`):跑一次 `subprocess.run(["unshare","--user","--map-root-user","--mount","--","true"], timeout=5)`,returncode==0 → 可用。结果在 app 启动时算一次。
- **chat_registry.build_chat_registry**:加 `bash_isolation: bool = False` 参数,透传 BashTool。
- **app.py**:`bash_isolation = settings.bash_isolation and userns_available()`;构造 BashTool 时传入。

### fail-closed 实现
`PRAXIS_BASH_ISOLATION=true` 但 `userns_available()` 为 False:
- 启动时 `logging.warning("PRAXIS_BASH_ISOLATION=true 但 userns 不可用,fail-closed:BashTool 不注册")`
- **BashTool 不注册**(`bash_sandbox_root` 即使有值也跳过注册)→ 模型看不到 Bash 工具(fail fast)
- **不降级软沙盒**(避免悄悄失去隔离保护)

---

## 5. 安全分析

### 覆盖(隔离生效后)
- ✓ 跨用户读 `files_root/{other_uid}`(empty 遮蔽整个 files_root)
- ✓ 读敏感配置 `praxis2.env` / `.ssh` / `.pgpass` 等(遮蔽)
- ✓ `cd` 出 sandbox 后仍受 namespace 视图约束(files_root 其它部分已遮)—— 修复 v0.17「cd 出沙盒」短板

### 仍不覆盖(诚实声明,写进 release note)
- 系统目录只读内容(`/etc/os-release` 等非敏感)仍可读;敏感系统文件(`/etc/shadow`)靠 OS 权限(root-only)+ v0.17 黑名单
- **userns 内 map-root**:命令在 namespace 内是 uid 0,可在 namespace 内 mount;对宿主仍是 zkyd、无新增权限(user namespace 的隔离保证)。理论上存在内核 userns 提权 CVE 风险(系统层面,非本设计引入;缓解 = 内核及时打补丁)
- 资源(内存/CPU)仍靠 rlimit(只管直接子进程;孙子进程逃逸未根治 → cgroup 留后续子项目)
- 网络未隔离(命令可外联;黑名单挡 `curl|sh`)

---

## 6. 测试策略

### 单测(`tests/test_tools_bash_isolation.py`)
- isolation off → `run` 用 `create_subprocess_shell`(不含 unshare),零回归
- isolation on → 构造的 argv 含 `unshare`/`--map-root-user`/`--mount` + SETUP + sandbox/files_root/command/mask 四个位置参数(monkeypatch `create_subprocess_exec` 捕获 argv 断言结构)
- **命令注入**:command = `'x"; rm -rf /; "'` 时,argv[-1] 精确等于该字符串(验位置参数隔离,SETUP 不被污染)
- fail-closed:isolation on + `userns_available()` 返 False → BashTool 不注册(build_chat_registry 不含 Bash)
- `userns_available()`:monkeypatch subprocess 返 0/非0 验 True/False

### e2e(staging,`PRAXIS_BASH_ISOLATION=true`)
- **跨用户**:预置 `{files_root}/{other_uid}/probe.txt`,命令 `cat {files_root}/{other_uid}/probe.txt` → 读不到(no such file,files_root 被遮)
- **敏感**:`cat ~/praxis2.env` → 读不到/空
- **sandbox 内**:在 sandbox 写文件 + 读回 → 正常
- **白名单兼容**:`df -h` → 正常(系统目录在)
- **常见命令**:`ls`/`cat`/`grep`/`python --version` 在隔离下正常

---

## 7. DoD

- [ ] config `bash_isolation` + `bash_isolation_mask` + `_KNOWN_KEYS` + 单测
- [ ] `userns_available()` 启动探测函数 + 单测
- [ ] BashTool `isolation`/`isolation_mask` 参数 + unshare argv 构造 + `SETUP_TEMPLATE`
- [ ] isolation on/off 二分执行;off 零回归
- [ ] 命令注入防护(位置参数)+ 单测
- [ ] fail-closed:userns 不可用 → 不注册 + `logging.warning` + 单测
- [ ] chat_registry / app.py 透传 isolation
- [ ] 全量回归零回归(isolation off == v0.17)
- [ ] e2e staging:跨用户读挡 / 敏感读挡 / sandbox 内正常 / df-h 正常
- [ ] 文档:release note 更新(隔离能力 + 仍不覆盖)
- [ ] commit + 部署 staging(`PRAXIS_BASH_ISOLATION=true`)+ 观察

---

## 8. 依赖 + 部署影响

- **无新 pip 依赖**(`unshare` = util-linux,staging 有;subprocess 是 stdlib)
- **staging env**:`PRAXIS_BASH_ISOLATION=true`(e2e 用)
- **不动**:litellm / FE / MCP / 主链 / 现有工具 / v0.17 软沙盒所有机制
- **回滚**:`PRAXIS_BASH_ISOLATION=false`(或不配)→ 行为 == v0.17.0 软沙盒
- **前提**:宿主 `unprivileged_userns_clone=1`(staging 已验);否则 fail-closed 不注册 Bash

---

## 9. 后续(v0.18 其它子项目)

- **cgroup 资源隔离**(systemd-run `--user --scope` MemoryMax/CPUQuota,管孙子进程)—— 可与本文件系统隔离叠加(--scope 资源在 --user 下可用,已验 user-scope-OK)
- 网络隔离(`unshare --net`)
- RemoteBashTool / MCP HTTP transport / mid-call 重连 / CC npx 适配(需 node18+)
