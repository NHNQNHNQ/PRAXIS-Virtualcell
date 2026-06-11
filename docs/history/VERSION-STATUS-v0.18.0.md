# v0.18.0 GA(BashTool 真隔离三件套:文件系统 + 资源 + 网络)

> **GA 锁定**: 2026-06-04 · **base**: v0.17.0(`b1dfc1c`)→ 三件套代码截至 `dee7971` · **tag**: `v0.18.0`(集齐三件套统一打,指向本 GA 收尾 commit)
> **关联文档(三子项目 spec/plan)**:
> - 子项目1 文件系统:`docs/superpowers/specs/2026-06-03-bash-isolation-userns-design.md`(+ plan 同名)
> - 子项目2 cgroup 资源:`docs/superpowers/specs/2026-06-04-bash-cgroup-resource-design.md`(+ plan 同名)
> - 子项目3 网络:`docs/superpowers/specs/2026-06-04-bash-netns-network-design.md` + `docs/superpowers/plans/2026-06-04-bash-netns-network.md`
> **GitHub**: `main` push + tag `v0.18.0`

---

## 0. GA 总览(真隔离三件套闭环)

v0.18 给 v0.17 的 BashTool 软沙盒补齐**经典隔离三维**,全 opt-in 默认关,正交可叠加:

| 维度 | 子项目 | 机制 | fail 策略 | 补的 v0.17 短板 |
|---|---|---|---|---|
| 文件系统 | 1 | `unshare --user --map-root-user --mount` + tmpfs 遮蔽 | fail-closed | 同 uid 绝对路径跨用户读 |
| 资源(内存/CPU) | 2 | `systemd-run --user --scope -p MemoryMax/CPUQuota` | fail-open(降级 rlimit) | rlimit 只管直接子进程,孙子逃逸 |
| 网络 | 3 | `unshare --net`(空 netns 无 veth 无路由) | fail-closed | 可外联(黑名单挡不全) |

- **开关**:`PRAXIS_BASH_TOOL_ENABLED` + `PRAXIS_BASH_ISOLATION`(+`_MASK`)+ `PRAXIS_BASH_CGROUP`(+`_MEM_MB`/`_CPU_PCT`)+ `PRAXIS_BASH_NETNS`,三维各自独立开关、各自探测、各自 fail 行为。
- **命令注入防护**全程延续(user command 走 argv 位置参数,不拼接进固定脚本)。
- **测试**:全量 **2025 / 0 fail**。三子项目各 staging e2e 实证(跨用户读 BLOCKED / cgroup 杀孙子 exit 137 / netns 外联 Network unreachable + 对比 CONNECTED + 三层叠加)。
- **回滚**:任一开关置 false → 回退该维度;全 false → v0.17 软沙盒(零回归)。

## 0.1 GA 范围 + 延后 backlog(诚实声明)

**GA 收的就是三件套**(子项目1/2/3)。以下**刻意不进 GA**——均为**基建门控**或 YAGNI,经深度核查后挂起,等前置就绪再单独立项:

| 延后项 | 状态 | 阻塞 / 原因(已实测核查) |
|---|---|---|
| 出站白名单(allowlist) | 基建门控 | rootless 无 host CAP_NET_ADMIN、`sudo` 要密码、`slirp4netns`/`pasta` 未装 → 连通层做不了(过滤层 nft-in-netns 已验可做)。ops 装 `passt` 后可做 pasta+nft 版 |
| cgroup 磁盘 IO 限制 | 基建门控 | user slice 只 delegate `memory pids`,`io` 未 delegate + 本机 systemd 不认 `IOMax`(`Unknown assignment`)。ops 配 `Delegate=io`(+ 可能升 systemd)后可做 |
| cgroup PID/进程数(TasksMax) | rootless 可做但延后 | 已验 `TasksMax` rootless 生效(pids 已 delegate,设 8 → pids.max=8 强制);但 BashTool opt-in、fork-bomb 危害有限,边际价值低,不值再走一整轮全流程。需要时单独做 |
| RemoteBashTool | YAGNI | staging 单机,多节点才需 |
| MCP HTTP transport / mid-call 重连 | 另一方向 | 非隔离论题 |
| CC npx 适配 | 基建门控 | staging node v12,需 ops 升 node18+ |
| 2 非阻塞 polish | 技术债 | config int 解析抛 ValueError 非 ConfigError(项目其它 int 同风格,统一债)/ app 层 fail 运行期可观测(debug 日志) |

---

## 1. 一句话定位

v0.18 子项目1 = **BashTool 文件系统真隔离(opt-in)** —— 命令在 user+mount namespace 内运行,绝对路径读不到其它用户 `files_root` 子目录与敏感配置,补 v0.17 软沙盒「同 uid 跨用户读」最大短板。

## 2. 重要改动(7 task,subagent-driven + 两阶段 review)

- **config**:`PRAXIS_BASH_ISOLATION` + `PRAXIS_BASH_ISOLATION_MASK`(默认关)
- **bash.py**:
  - `userns_available()` 启动探测(lru_cache)
  - `SETUP_TEMPLATE`:namespace 内 bind 遮蔽脚本——tmpfs 遮蔽整个 `files_root`(藏所有 user_id)→ bind 回 this_user sandbox;mask 遮蔽敏感(目录 tmpfs / 文件 bind /dev/null)
  - `_isolation_argv`:**命令注入防护**(user command 走 argv 位置参数 `$3`,不拼进 setup 脚本)
  - `run()` 执行二分:isolation on → `create_subprocess_exec(unshare ...)`;off → v0.17 软沙盒(零回归)
- **chat_registry + app.py**:透传 `bash_isolation` + **fail-closed**(userns 不可用 → 不注册 Bash + 启动 warning)

## 3. 隔离覆盖(staging e2e 实测,直接调 BashTool(isolation=True))

- ✓ 跨用户读 `files_root/{other}/secret.txt` → **BLOCKED-OK**(读不到,stdout 空)
- ✓ sandbox 内读写正常(`echo > t.txt && cat` → hello-isolated)
- ✓ `df -h` 正常(系统目录在)
- ✓ `cd` 出沙盒受 namespace 视图约束(修 v0.17「cd 出沙盒」短板)

## 4. 仍不覆盖(诚实声明)

- **资源(内存/CPU)**:仍靠 rlimit(只管直接子进程;孙子进程逃逸 → cgroup 留 v0.18 后续子项目)
- **网络**:未隔离(黑名单挡 `curl|sh`)
- **userns map-root**:命令在 namespace 内是 uid 0,对宿主仍是 zkyd、无新增权限(userns 隔离保证);理论内核 userns 提权 CVE 风险(系统层,非本设计引入)
- 系统只读目录(`/etc` 等非敏感)可读;敏感系统文件(`/etc/shadow`)靠 OS 权限 + v0.17 黑名单

## 5. 机制选型记录(探测驱动)

- **systemd-run `--user` 文件系统 sandboxing**:实测失效(`ProtectHome`/`InaccessiblePaths` 不生效、`TemporaryFileSystem` 报 `Failed to set up mount namespacing: Operation not supported`,用户态无 mount ns 权限)→ **弃**
- **unshare `--user --map-root-user --mount` + tmpfs 遮蔽**:rootless 已验(`unprivileged_userns_clone=1`)→ **采用**
- **docker**:zkyd 有 daemon 权限但重(镜像+启动开销)→ **弃**

## 6. 回滚

`PRAXIS_BASH_ISOLATION=false`(或不配)→ v0.17 软沙盒。userns 不可用时自动 fail-closed(不注册 Bash + 警告)。

## 7. 测试

全量 **1995 / 0 fail**(+ config 3 / isolation ~9 / chat_registry 2)。e2e 直接调 BashTool 验隔离生效 + 单测验集成链路(fail-closed 4 组合 / 注入防护 / off 零回归)。

## 8. 后续(子项目1 当时列)

cgroup 资源隔离(**已做,见下子项目2**)/ 网络隔离(`unshare --net`)/ RemoteBashTool / MCP HTTP transport / mid-call 重连 / CC npx 适配(需 node18+)。

---

# 子项目2:cgroup 资源隔离(2026-06-04)

> **代码 HEAD** `e3b0624` · spec `docs/superpowers/specs/2026-06-04-bash-cgroup-resource-design.md` · plan `docs/superpowers/plans/2026-06-04-bash-cgroup-resource.md`

## S2.1 一句话定位

**BashTool cgroup 资源隔离(opt-in)** —— 命令经 `systemd-run --user --scope -p MemoryMax/CPUQuota` 运行,内存/CPU 限制**覆盖整个进程树含孙子**,补 v0.17 rlimit 只管直接子进程的短板。与子项目1 文件系统隔离正交叠加。

## S2.2 重要改动(4 代码 task,subagent-driven + 两阶段 review)

- **config**:`PRAXIS_BASH_CGROUP`(默认关)+ `PRAXIS_BASH_CGROUP_MEM_MB`(1024)/ `_CPU_PCT`(100)
- **bash.py**:`scope_available()` 探测 + `_cgroup_argv()`(systemd-run --scope 前缀)+ run() 扩 **cgroup × isolation 4 组合矩阵**(cgroup on → systemd-run 最外层包 unshare 或 `bash -c command`;command 走 argv 位置参数,注入防护延续)
- **chat_registry + app.py**:透传 cgroup 三参 + **fail-open**(scope 不可用 → 降级 rlimit,Bash 仍注册 + 启动 warning)

## S2.3 cgroup 覆盖(staging e2e 实测,直接调 BashTool(cgroup=True))

- ✓ **杀孙子**:cgroup_mem_mb=64,孙子 `dd` 吃 256M → cgroup OOM **kill(exit 137)**;cgroup off 同命令不 kill(rlimit 1GB 兜底)—— 证明 cgroup 覆盖整树(rlimit 做不到)
- ✓ `df -h` 正常
- ✓ **cgroup + isolation 叠加**:跨用户读被挡(隔离)+ 资源受限(cgroup),两层正交

## S2.4 探测记录(2026-06-04)

`systemd-run --user --scope`:同步拿 stdout/exit ✓ / 接受 MemoryMax/CPUQuota ✓ / 嵌套 unshare ✓ / cgroup kill 孙子(MemoryMax=64M 杀 256M dd exit 137)✓

## S2.5 降级 + 回滚

- **fail-open**:scope 不可用 → 降级 rlimit(直接子进程,孙子逃逸)+ 启动 warning;命令仍跑(资源耗尽是 DoS 非数据泄漏,与子项目1 文件系统隔离 fail-closed 不同)
- `PRAXIS_BASH_CGROUP=false`(或不配)→ 子项目1 状态(无 cgroup)

## S2.6 仍不覆盖

磁盘 IO / PID 数 / 文件描述符未限(可后续 `-p IOMax`/`TasksMax`);fail-open 降级时资源弱化到 rlimit。

## S2.7 测试

全量 **2009 / 0 fail**(+ config 3 / cgroup helper 3 / run 4 组合 5 / chat_registry 2)。e2e 直接调 BashTool 验 cgroup kill 孙子 + cgroup off 对比 + 叠加。

## S2.8 后续(v0.18 其它子项目)

网络隔离(`unshare --net`)/ 磁盘 IO+PID(cgroup `-p IOMax`/`TasksMax`)/ RemoteBashTool / MCP HTTP transport / mid-call 重连 / CC npx 适配(node18+)。

---

# 子项目3:网络隔离(unshare --net)(2026-06-04)

> **代码 HEAD** `dee7971` · spec `docs/superpowers/specs/2026-06-04-bash-netns-network-design.md` · plan `docs/superpowers/plans/2026-06-04-bash-netns-network.md`

## S3.1 一句话定位

**BashTool 网络隔离(opt-in)** —— 命令在独立 net namespace(`unshare --user --map-root-user --net`)内跑,空 netns 无 veth 无路由 → 外网/内网外联全封(SSRF、数据外泄、调外部下载)。补"**真隔离三件套**"最后一块:文件系统✓(子项目1)资源✓(子项目2)**网络✓(本子项目)**。与 isolation/cgroup 正交叠加。

## S3.2 重要改动(4 代码 task,subagent-driven + 两阶段 review + opus final review)

- **config**:独立 `PRAXIS_BASH_NETNS`(默认关)
- **bash.py**:`netns_available()` 探测(lru_cache,独立探 `--net`)+ `_netns_argv()` 轻量路径(isolation off + netns on:`unshare --net + bash -c`,无遮蔽脚本)+ `_isolation_argv` 加 `netns` 参数(条件插 `--net`,与 `--mount` 同次 unshare)+ run() inner **2→3 情形**(isolation / netns-only / 仅cgroup),零回归 shell 判据加 `not netns`;command 全程走 argv 位置参数(注入防护延续)
- **chat_registry + app.py**:透传 `bash_netns` + **fail-closed**(netns 不可用 → 不注册 Bash;判据与 isolation 合并 `(iso & !userns) or (netns & !netns_available)`,启动独立 warning 精确归因)

## S3.3 netns 覆盖(staging e2e 实测,直接调 BashTool)

- ✓ **netns=True 连 .40:8080** → `OSError [Errno 101] Network is unreachable`(外联封);**netns=False 对比** → `CONNECTED`(证明是 netns 在挡)
- ✓ **netns+isolation 叠加** → BLOCKED(`--mount --net` 同次 unshare,文件系统+网络双隔离)
- ✓ **netns+cgroup 叠加** → BLOCKED(systemd-run 包 unshare --net,资源+网络)
- ✓ `df -h` 正常(非网络操作无回归)
- ✓ 启动 log 无 fail-closed warning(staging netns 可用,Bash 正常注册)
- 覆盖面:AF_INET/INET6 egress + abstract AF_UNIX socket + DNS(无路由)+ **IPv6 / raw socket 同封**(空 netns 无设备无路由,一并到不了)

## S3.4 探测记录(2026-06-04 staging .53)

`unshare --user --map-root-user --net -- true` rc=0 / `+--mount` rc=0 / `systemd-run --scope -- unshare --net` rc=0;netns 内 egress `Network unreachable`、无 netns CONNECTED、netns 内只 `lo`(operstate unknown=DOWN,127.0.0.1 不可达)。

## S3.5 fail-closed + 回滚

- **fail-closed**:netns 不可用 → 不注册 Bash + 启动 warning(与子项目1 isolation 同策:外联/SSRF 是安全边界,黑名单无法可靠覆盖出口;宁可不给 Bash 也不给"缺一层隔离"的 Bash,避免静默安全降级)。**与 cgroup fail-open 不同**(资源是 DoS 可降级 rlimit)。
- `PRAXIS_BASH_NETNS=false`(或不配)→ 子项目2 状态(无网络隔离)

## S3.6 仍不覆盖(诚实声明)

- **pathname AF_UNIX socket 不隔离**(netns 只管 AF_INET/INET6 + abstract unix):host 文件路径 unix socket(如 `/var/run/docker.sock`)若可见仍可连 → 靠**子项目1 filesystem mask** 兜
- **lo down 副作用**:依赖 127.0.0.1 的命令(罕见)在沙盒内失败(取舍:沙盒内无合法 localhost 服务)
- **fail-closed 取舍**:netns 不可用 → Bash 整体不注册(不像 cgroup 可降级),启用环境必须支持 userns(staging 已验)

## S3.7 测试

全量 **2025 / 0 fail**(+ config 3 / netns helper+argv 5 / run 3 情形 6 / chat_registry 2;较子项目2 净增 16)。final review 本机 delta 复核:base 与 HEAD 同 62 pre-existing fail(dev box 缺 mcp 模块,与改动无关),净增 16 pass 0 新失败 → 零回归坐实。e2e 直接调 BashTool 验 netns 封外联 + netns off 对比 + isolation/cgroup 叠加 + df-h 无回归。

## S3.8 后续

出站白名单 / 受控代理(veth+NAT 放行特定目标)/ 磁盘 IO+PID(cgroup)/ RemoteBashTool / MCP HTTP transport / mid-call 重连 / CC npx(node18+)。**v0.18 GA**:集齐子项目统一打 tag(含两个非阻塞 polish:config int ValueError / app 层 fail-closed 运行期可观测)。
