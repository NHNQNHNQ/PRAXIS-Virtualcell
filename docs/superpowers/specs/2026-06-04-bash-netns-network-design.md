# v0.18 子项目3:BashTool 网络隔离(unshare --net)

**日期**: 2026-06-04 · **状态**: 设计待批 · **范围**: v0.18 第三个子项目
**前置**: v0.18 子项目1 文件系统隔离(unshare userns)+ 子项目2 cgroup 资源隔离(systemd-run --scope)已 ship;v0.17.0 GA 软沙盒

---

## 0. 目标与非目标

### 目标
用 network namespace(`unshare --net`)隔离 BashTool 命令的网络:命令在**空 net namespace** 内跑(无 veth → 无任何外部路由),封堵外网/内网外联(SSRF、数据外泄、调外部下载)。补"真隔离三件套"最后一块:**文件系统✓(子项目1)资源✓(子项目2)网络✓(本子项目)**。与 isolation/cgroup **正交叠加**,opt-in 默认关。

### 非目标(本子项目明确不做)
- **文件系统隔离 / 资源隔离** — 子项目1/2 已做,本子项目只加网络维度
- **拉起 loopback** — 决策:lo 保持 down(见 §1 决策3),127.0.0.1 不可达(沙盒内无合法 localhost 服务)
- **pathname AF_UNIX socket 隔离** — netns 不隔离文件路径 unix socket(如 host docker.sock),靠子项目1 filesystem mask 兜
- **出站白名单 / 受控代理 / veth+NAT 放行特定目标** — 本子项目是"全禁外联";细粒度放行留后续(YAGNI)
- **磁盘 IO / PID 限制** — cgroup 后续维度,非本子项目

---

## 1. 关键决策(brainstorm 结论)

| # | 决策 | 理由 |
|---|---|---|
| 1 | 机制 = `unshare --user --map-root-user --net` | unprivileged netns 需 userns 兜底(同子项目1 基础);空 netns 无 veth → 无外部路由(已验探针4 `Network is unreachable`) |
| 2 | 开关 = **独立 `PRAXIS_BASH_NETNS`** | 与子项目1 `PRAXIS_BASH_ISOLATION`、子项目2 `PRAXIS_BASH_CGROUP` 三者正交;真"三件套"三个对等开关;netns 单开走轻量路径(见 §3.3),无耦合 footgun(对比"耦合进 isolation":netns=on+isolation=off 会静默不生效) |
| 3 | 降级 = **fail-closed**(镜像子项目1) | 外联/SSRF 是**安全边界**,与文件系统泄漏同级:黑名单无法可靠覆盖外联出口(curl/wget/nc/python socket/`/dev/tcp`/DNS 无穷多)→ netns 不可用时**不注册 Bash + 启动 warning**(对比 cgroup fail-open:资源是 DoS 可降级 rlimit) |
| 4 | lo 保持 **down**(不拉起) | 最简、最严、不依赖 ip/iproute2;netns-only 路径无需额外 sh 脚本包裹;沙盒内无合法 localhost 服务,127.0.0.1 连不通更彻底(已验探针7 fresh netns lo operstate unknown/DOWN) |
| 5 | 与 isolation 叠加:`_isolation_argv` 加 `--net` 标志(SETUP_TEMPLATE 不动) | netns 与 mount ns 同一次 unshare 一起开(已验探针2);lo 不拉起 → SETUP 脚本无需改 |
| 6 | 与 cgroup 叠加:`systemd-run --scope -- unshare --net ...`(矩阵不变) | scope 在最外层包 unshare(已验探针3 嵌套 OK);沿用子项目2 包裹逻辑 |

### 探测记录(2026-06-04 staging .53,确定性探针 `/tmp/probe_netns.sh`)
- **1** `unshare --user --map-root-user --net -- true` → **rc=0**(netns 可用)
- **2** `unshare --user --map-root-user --mount --net -- true` → **rc=0**(isolation+netns 叠加底座)
- **3** `systemd-run --user --scope --quiet -- unshare --user --map-root-user --net -- true` → **rc=0**(cgroup×netns 嵌套)
- **4** netns 内 `socket.create_connection(('10.102.106.40',8080),3)` → **`OSError [Errno 101] Network is unreachable`**(核心:外联被封)
- **5** 无 netns 同命令 → **`CONNECTED`**(对比:证明是 netns 在挡,非目标不可达)
- **6** netns 内 `/proc/net/dev` → **只 `lo`**(无 veth/eth)
- **7** netns 内 `lo` operstate → **unknown**(fresh netns lo DOWN,127.0.0.1 不可达,印证决策4)

---

## 2. 架构

`BashTool.run` 命令包装由**子项目2 的 cgroup × isolation 两维**扩为 **cgroup × isolation × netns 三维**。但 netns **不新增矩阵列**:它作为 isolation 路径的 `--net` 修饰(isolation on 时)+ 一条新的轻量 inner 分支(isolation off + netns on 时)。run() 的 inner 构造由 **2 情形 → 3 情形**:

| isolation | netns | inner 命令(cgroup 包裹层正交,不变) |
|---|---|---|
| on | on/off | `_isolation_argv(..., netns=netns)`(unshare --user --mount [--net] + SETUP,cwd 走 `cd "$5"`) |
| off | on | `_netns_argv(command)` = `unshare --user --map-root-user --net -- /bin/bash -c <command>`(无遮蔽脚本,cwd 走 subprocess `kw`) |
| off | off | `["/bin/bash","-c",command]`(子项目2 现状) |

零回归 shell 分支(`create_subprocess_shell`)判据由 `not isolation and not cgroup` → **`not isolation and not cgroup and not netns`**(netns 单开必须走 exec 路径)。

cgroup 包裹层完全不变:`argv = _cgroup_argv(...) + inner if cgroup else inner`。

### 职责边界
- netns 是执行层第三个正交隔离维度(网络 vs 文件系统 vs 资源),各自开关、各自探测(`netns_available()`)、各自 fail 行为(netns/isolation fail-closed;cgroup fail-open)。
- 命令注入防护延续:isolation 路径 command 走 SETUP 的 `$3`;netns-only 路径 command 走 `bash -c` 的单 argv 元素(同子项目2 isolation-off 路径,不拼接)。

---

## 3. netns 机制

### 3.1 探测(新 lru_cache)
```python
@functools.lru_cache(maxsize=1)
def netns_available() -> bool:
    """探测 unprivileged user+net namespace 是否可用(fail-closed 用)。
    跑一次 `unshare --user --map-root-user --net -- true`,returncode==0 即可用。"""
    try:
        r = subprocess.run(
            ["unshare", "--user", "--map-root-user", "--net", "--", "true"],
            capture_output=True, timeout=5,
        )
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
```
独立探针(探正要跑的 `--net`,不复用 `userns_available()` 的 `--mount` 探测——理论上系统可能 mount ns 可用而 net ns 受限)。

### 3.2 `_isolation_argv` 加 netns 修饰
```python
def _isolation_argv(*, command, sandbox, files_root, mask, cwd, netns=False):
    flags = ["unshare", "--user", "--map-root-user", "--mount"]
    if netns:
        flags.append("--net")
    return [*flags, "--", "/bin/sh", "-c", SETUP_TEMPLATE,
            "praxis-bash", sandbox, files_root, command, mask, cwd]
```
`SETUP_TEMPLATE` **不动**(lo 不拉起,netns 内文件系统遮蔽逻辑与网络无关)。

### 3.3 `_netns_argv`(isolation off + netns on 轻量路径)
```python
def _netns_argv(*, command: str) -> list[str]:
    """isolation=off + netns=on:仅 net namespace,无 mount 遮蔽。
    command 走 bash -c 单 argv 元素(同 isolation-off 路径,注入防护)。
    cwd 由 subprocess kw 设(无 mount ns,宿主 cwd 可见)。"""
    return [
        "unshare", "--user", "--map-root-user", "--net", "--",
        "/bin/bash", "-c", command,
    ]
```

### 3.4 cwd 处理
- isolation on:**不设** `cwd=`(SETUP 内 `cd "$5"`,延续子项目1/2)。
- isolation off + netns on(`_netns_argv`):**设** `cwd=str(cwd_resolved)`(无 mount ns,unshare 继承宿主 cwd → bash 继承)。
- isolation off + netns off:同子项目2(`bash -c` 设 cwd / shell 设 cwd)。

### 3.5 run() 三情形 inner 构造(伪码,替换子项目2 的二情形)
```python
isolation, cgroup, netns = self._isolation, self._cgroup, self._netns
if not isolation and not cgroup and not netns:
    proc = create_subprocess_shell(command, cwd=cwd_resolved, ...)  # v0.17 零回归
else:
    if isolation:
        inner = _isolation_argv(command=..., sandbox=root_resolved,
                                files_root=root_resolved.parent,
                                mask=_mask_paths(self._isolation_mask),
                                cwd=cwd_resolved, netns=netns)  # netns → 插 --net
        exec_cwd = None  # SETUP cd "$5"
    elif netns:
        inner = _netns_argv(command=command)
        exec_cwd = str(cwd_resolved)  # 无 mount ns,宿主 cwd 可见
    else:
        inner = ["/bin/bash", "-c", command]
        exec_cwd = str(cwd_resolved)
    argv = (_cgroup_argv(mem_mb=..., cpu_pct=...) + inner) if cgroup else inner
    kw = {} if exec_cwd is None else {"cwd": exec_cwd}
    proc = create_subprocess_exec(*argv, **kw, stdout=PIPE, stderr=PIPE,
                                  preexec_fn=preexec, env=_sanitized_env())
```

---

## 4. 集成 + 开关 + 探测 + fail-closed

- **config.py**:`bash_netns: bool = False`(接 cgroup 系列后)+ `_get_bool(e, "PRAXIS_BASH_NETNS", False)` + `_KNOWN_KEYS` 注册 `PRAXIS_BASH_NETNS`。
- **BashTool.__init__**:加 `netns: bool = False` → `self._netns = netns`。
- **chat_registry.build_chat_registry**:加 `bash_netns: bool = False`,透传 `BashTool(netns=bash_netns)`。
- **app.py `_chat_stream`(~660)**:netns fail-closed **并入现有 isolation fail-closed 判据**(import `netns_available`):
  ```python
  want_isolation = getattr(settings, "bash_isolation", False)
  want_netns = getattr(settings, "bash_netns", False)
  if (want_isolation and not userns_available()) or (want_netns and not netns_available()):
      pass  # fail-closed:不注册 Bash(启动已 warning)
  else:
      bash_root = ...; bash_isolation = want_isolation; bash_netns = want_netns
      bash_cgroup = getattr(settings, "bash_cgroup", False) and scope_available()  # fail-open 不变
  ```
  透传 `bash_netns` 给 build_chat_registry。
- **app.py 启动 warning(~1114)**:加 netns fail-closed **独立 warning**(与 isolation warning 并列,告知 admin 是哪一项失败 → Bash 不注册):
  ```python
  if (getattr(settings, "bash_tool_enabled", False)
          and getattr(settings, "bash_netns", False)
          and not netns_available()):
      logger.warning("PRAXIS_BASH_NETNS=true 但 user+net namespace 不可用,"
                     "fail-closed:BashTool 将不注册。需启用 unprivileged userns 或关闭网络隔离。")
  ```
  (沿用现有 isolation warning 的 `getattr` 风格,~1118 同位置)
- **tests/_auth_test_helpers.py `_TestSettings`**:加 `bash_netns: bool = False`(雷区:显式字段 dataclass,不加则 app.py 访问/构造回归)。

注:fail-closed 在 app.py 算(与子项目1 同位置),BashTool 只收最终 netns on/off。判据两处镜像(_chat_stream + 启动 warning),改动同步。

---

## 5. 网络/安全分析

### 覆盖(netns 生效后)
- ✓ 外网/内网 IP 外联全封(已验探针4 `Network is unreachable`):curl/wget/nc/python socket/`/dev/tcp`/任意出站 socket 无路由
- ✓ DNS 解析失败(无路由到 resolver)→ 域名外联也断
- ✓ 内网 SSRF 封堵:命令无法摸 litellm 127.0.0.1:4000(lo down)与内网 .102.106.x 邻居
- ✓ abstract AF_UNIX socket 隔离(abstract namespace socket 是 per-netns 的)
- ✓ 与 isolation/cgroup 三层正交叠加(已验探针2/3 底座可用)

### 仍不覆盖(诚实声明,写进 release note)
- **pathname AF_UNIX socket 不隔离**(netns 只管 AF_INET/INET6 + abstract unix):host 文件路径 unix socket(如 `/var/run/docker.sock`)若可见仍可连 → 靠**子项目1 filesystem mask**(把敏感 socket 路径列入 mask)兜
- **lo down 副作用**:依赖 127.0.0.1 的命令(罕见)在沙盒内失败(决策4 取舍)
- **fail-closed 取舍**:netns 不可用 → Bash 整体不注册(不像 cgroup 可降级);代价是 netns 启用环境必须支持 userns(staging 已验)
- netns 不防本机进程间非网络 IPC(共享内存/信号等,受 isolation/cgroup 其它维度约束)

---

## 6. 测试策略

### 单测(`tests/test_tools_bash_netns.py`)
- `netns_available()`:monkeypatch subprocess 返 0/异常 → True/False
- `_netns_argv`:验 argv 结构(unshare --user --map-root-user --net -- /bin/bash -c command,末尾 command 单元素)
- `_isolation_argv(netns=True)`:argv 含 `--net`;`netns=False`:不含 `--net`(回归保护)
- run() 组合(monkeypatch create_subprocess_exec/shell 捕获 argv + kw):
  - off+off+off → `create_subprocess_shell`(零回归)
  - netns-only(iso off, cgroup off, netns on)→ `create_subprocess_exec`,argv[0]=unshare 且含 `--net` 不含 `--mount`,设 `cwd=`
  - iso on + netns on → argv 含 unshare + `--mount --net`,不设 `cwd=`
  - cgroup on + netns on(iso off)→ argv[0]=systemd-run,内含 unshare `--net`
  - cgroup on + iso on + netns on(三开)→ systemd-run 包 unshare `--mount --net`
- 命令注入:netns-only 时 command 作 `bash -c` 的 argv 项(不拼接)
- 零回归判据:netns 单开**不**走 shell 分支
- config 单测:`PRAXIS_BASH_NETNS` 解析(_get_bool)+ `_KNOWN_KEYS` 接受
- chat_registry 单测:`bash_netns` 透传 BashTool

### e2e(controller 亲做,staging `PRAXIS_BASH_NETNS=true`,确定性探针直调 BashTool)
- `BashTool(netns=True)` 跑连 .40:8080 → **Network unreachable**(隔离生效);`netns=False` → 连通(对比)
- `BashTool(netns=True, isolation=True)` 叠加:跨用户读被挡(isolation)+ 外联被挡(netns)
- `BashTool(netns=True, cgroup=True)` 叠加:外联挡 + 资源限(sanity)
- `df -h` / `echo` 在 netns 下正常(非网络操作无回归)

---

## 7. DoD

- [ ] config `bash_netns` + `_KNOWN_KEYS` 注册 + `_get_bool` + 单测
- [ ] `netns_available()` 探测(lru_cache)+ 单测
- [ ] `_isolation_argv` 加 `netns` 参数(条件插 --net)+ 单测(含 netns=False 回归)
- [ ] `_netns_argv()` 轻量路径 + 单测
- [ ] BashTool `netns` 参数 + run() 三情形 inner + 零回归判据加 `not netns` + 单测
- [ ] 命令注入防护延续(netns-only command 走 argv)+ 单测
- [ ] chat_registry / app.py 透传 + fail-closed(netns 不可用不注册)+ 启动 warning + 单测
- [ ] `_TestSettings` 加 `bash_netns` 字段
- [ ] 全量回归零回归(netns off == 子项目2 状态)
- [ ] e2e staging:netns 封外联 / netns off 对比 / netns+isolation+cgroup 叠加 / df-h 无回归
- [ ] 文档:release note 更新(网络隔离 + 三件套齐 + fail-closed + 仍不覆盖)
- [ ] commit + 部署 + 观察

---

## 8. 依赖 + 部署影响

- **无新 pip 依赖**(unshare = util-linux,staging 有;subprocess stdlib)
- **staging env**:`PRAXIS_BASH_NETNS=true`(加 ~/praxis2.env,grep -q 幂等)
- **不动**:litellm / FE / MCP / 主链 / v0.17 软沙盒 / v0.18-1 文件系统 / v0.18-2 cgroup
- **回滚**:`PRAXIS_BASH_NETNS=false`(或不配)→ 行为 == v0.18-2
- **前提**:`unshare --user --map-root-user --net` 可用(staging 已验探针1);否则 fail-closed 不注册 Bash

---

## 9. 后续(v0.18 其它子项目)

- 出站白名单 / 受控代理(veth + NAT 放行特定目标,细粒度网络)
- 磁盘 IO / PID 限制(cgroup `-p IOMax` / `-p TasksMax`)
- RemoteBashTool / MCP HTTP transport / mid-call 重连 / CC npx 适配(node18+)
- **v0.18 GA**:集齐子项目后统一打 tag(含两个非阻塞 polish:config int ValueError / app 层 cgroup fail-open 单测)
