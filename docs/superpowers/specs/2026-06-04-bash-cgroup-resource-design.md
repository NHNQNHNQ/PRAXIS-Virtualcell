# v0.18 子项目2:BashTool cgroup 资源隔离(systemd-run --scope)

**日期**: 2026-06-04 · **状态**: 设计待批 · **范围**: v0.18 第二个子项目
**前置**: v0.18 子项目1 文件系统隔离(unshare userns)已 ship;v0.17.0 GA 软沙盒

---

## 0. 目标与非目标

### 目标
用 cgroup(`systemd-run --user --scope -p MemoryMax -p CPUQuota`)限制 BashTool 命令的内存/CPU,**资源限制覆盖整个进程树(含孙子进程)**——补 v0.17 rlimit 只管直接子进程的短板(孙子进程逃逸)。与子项目1 文件系统隔离正交叠加。

### 非目标(本子项目明确不做)
- **文件系统隔离** — 子项目1 已做(unshare),本子项目只加 cgroup 资源
- **网络隔离 / PID 隔离** — v0.18 后续 / 不做
- **真隔离的安全维度** — cgroup 是资源限制(防 DoS/资源耗尽),非数据安全(那是子项目1)

---

## 1. 关键决策(brainstorm 结论)

| # | 决策 | 理由 |
|---|---|---|
| 1 | 机制 = `systemd-run --user --scope -p MemoryMax/CPUQuota` | rootless(已验 user-scope-OK);`--scope` 同步拿 stdout/exit(已验);cgroup 覆盖整树含孙子(已验 D:MemoryMax=64M 杀吃 256M 的孙子 dd,exit 137) |
| 2 | 开关 = **独立 `PRAXIS_BASH_CGROUP`** | 与子项目1 `PRAXIS_BASH_ISOLATION`(文件系统)正交;不破坏已 ship 的 isolation 语义;可单独/组合 |
| 3 | 降级 = **fail-open 降级 rlimit** | cgroup 是资源增强(防 DoS),非安全前置;不可用时降级 v0.17 rlimit(直接子进程)+ 命令仍跑;资源耗尽是 DoS 非数据泄漏,rlimit 兜底可接受 |
| 4 | 与文件系统隔离叠加:`systemd-run --scope -- unshare -- command` | scope 在外限资源整树,unshare 在内做文件系统;已验 C 嵌套可行 |

### 探测记录(2026-06-04 staging .53)
- A:`systemd-run --user --scope --quiet -- sh -c "echo X; exit 5"` → stdout `X` + exit 5(同步拿输出)
- B:`-p MemoryMax=512M -p CPUQuota=100%` 接受(exit 0)
- C:`systemd-run --scope -- unshare --user --map-root-user --mount -- sh -c "..."` → 嵌套 OK
- D:`-p MemoryMax=64M -- sh -c "dd ... bs=256M"` → `Killed` / exit 137(cgroup 覆盖孙子)

---

## 2. 架构

`BashTool.run` 命令包装扩展为 **cgroup × isolation 两个正交开关**的组合:

| cgroup | isolation | 命令包装 |
|---|---|---|
| off | off | `create_subprocess_shell(command, cwd=)`(v0.17 软沙盒) |
| off | on | `create_subprocess_exec(*unshare_argv)`(v0.18-1,不设 cwd) |
| on | off | `create_subprocess_exec(*cgroup_argv, "/bin/bash", "-c", command, cwd=)` |
| on | on | `create_subprocess_exec(*cgroup_argv, *unshare_argv)`(不设 cwd) |

- cgroup on 时 `systemd-run --user --scope` 在**最外层**(cgroup 限资源整树),包住 unshare(isolation on)或 `bash -c command`(isolation off)。
- 全程 `create_subprocess_exec(argv)`(off+off 除外,仍用 shell)。command 走 argv 位置参数(`bash -c` 的参数 / SETUP 的 `$3`),不拼接 → 注入防护延续。
- `--scope` 同步,stdout/stderr 直连(已验 A),后续 drain/超时/截断不变。

### 职责边界
- cgroup 是执行层在 isolation 之上再叠一层 systemd-run 前缀;两层正交(资源 vs 文件系统),各自开关、各自探测、各自 fail 行为(cgroup fail-open / isolation fail-closed)。

---

## 3. cgroup 机制

### 3.1 cgroup argv 前缀
```python
def _cgroup_argv(*, mem_mb: int, cpu_pct: int) -> list[str]:
    """systemd-run --user --scope 前缀:cgroup 限内存/CPU,覆盖整个进程树。"""
    return [
        "systemd-run", "--user", "--scope", "--quiet",
        "-p", f"MemoryMax={mem_mb}M",
        "-p", f"CPUQuota={cpu_pct}%",
        "--",
    ]
```
拼在 inner 命令(unshare argv 或 `["/bin/bash","-c",command]`)之前。

### 3.2 探测
```python
@functools.lru_cache(maxsize=1)
def scope_available() -> bool:
    """探测 systemd-run --user --scope 是否可用(fail-open 用)。"""
    try:
        r = subprocess.run(
            ["systemd-run", "--user", "--scope", "--quiet", "--", "true"],
            capture_output=True, timeout=5,
        )
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
```

### 3.3 资源值
- `MemoryMax={mem_mb}M`:默认 `mem_mb=1024`(1GB,与 v0.17 `rlimit_mem_bytes` 1GB 对齐)。
- `CPUQuota={cpu_pct}%`:默认 `cpu_pct=100`(1 核)。
- 可配:`PRAXIS_BASH_CGROUP_MEM_MB` / `PRAXIS_BASH_CGROUP_CPU_PCT`。

### 3.4 cwd 处理
- isolation on(unshare):**不设** `cwd=`(SETUP 内 `cd "$5"` 在 namespace 切换,延续 v0.18-1)。
- isolation off + cgroup on(`bash -c command`):**设** `cwd=str(cwd_resolved)`(systemd-run 继承 cwd → bash 继承)。

### 3.5 run() 二分逻辑(伪码)
```python
isolation = self._isolation
cgroup = self._cgroup  # app.py 已 and scope_available()(fail-open)
if not isolation and not cgroup:
    proc = create_subprocess_shell(command, cwd=cwd_resolved, ...)  # v0.17
else:
    if isolation:
        inner = _isolation_argv(command=..., sandbox=root_resolved,
                                files_root=root_resolved.parent,
                                mask=_mask_paths(self._isolation_mask), cwd=cwd_resolved)
        exec_cwd = None  # SETUP cd "$5"
    else:
        inner = ["/bin/bash", "-c", command]
        exec_cwd = str(cwd_resolved)
    argv = (_cgroup_argv(mem_mb=self._cgroup_mem_mb, cpu_pct=self._cgroup_cpu_pct) + inner
            if cgroup else inner)
    kw = {} if exec_cwd is None else {"cwd": exec_cwd}
    proc = create_subprocess_exec(*argv, **kw, stdout=PIPE, stderr=PIPE,
                                  preexec_fn=preexec, env=_sanitized_env())
```

---

## 4. 集成 + 开关 + 探测 + fail-open

- **config.py**:`bash_cgroup: bool = False` + `bash_cgroup_mem_mb: int = 1024` + `bash_cgroup_cpu_pct: int = 100` + `_KNOWN_KEYS`(`PRAXIS_BASH_CGROUP` / `_MEM_MB` / `_CPU_PCT`)+ load_from_env(bool 用 `_get_bool`;int 配置用 `int(e.get(key, str(default)))`,若 config.py 已有 `_get_int` helper 则复用;解析失败回退默认值,plan 时确认现有 helper)。
- **BashTool.__init__**:加 `cgroup: bool = False` + `cgroup_mem_mb: int = 1024` + `cgroup_cpu_pct: int = 100`。
- **chat_registry.build_chat_registry**:加 `bash_cgroup` / `bash_cgroup_mem_mb` / `bash_cgroup_cpu_pct`,透传 BashTool。
- **app.py**:`bash_cgroup = getattr(settings, "bash_cgroup", False) and scope_available()`(fail-open:scope 不可用 → False → 不加 cgroup 层,但 Bash 仍注册 + isolation/rlimit)。透传给 build_chat_registry。
- **app 启动 warning**:`bash_tool_enabled and bash_cgroup(配置) and not scope_available()` → `logging.warning("PRAXIS_BASH_CGROUP=true 但 systemd-run --scope 不可用,fail-open 降级 rlimit(资源限制仅覆盖直接子进程)")`。

注:fail-open 在 app.py 算(与子项目1 fail-closed 同位置),BashTool 只收最终 cgroup on/off。

---

## 5. 资源/安全分析

### 覆盖(cgroup 生效后)
- ✓ 内存/CPU 限制覆盖**整个进程树含孙子**(已验 D)——补 v0.17 rlimit 只管直接子进程的短板
- ✓ 与文件系统隔离叠加(systemd-run --scope -- unshare),资源 + 安全双隔离

### 仍不覆盖(诚实声明,写进 release note)
- 磁盘 IO / PID 数 / 文件描述符未限(可后续加 `-p IOMax` / `TasksMax` 等)
- fail-open 降级时(scope 不可用)资源限制弱化到 rlimit(直接子进程),孙子逃逸——此时退回 v0.17 状态
- cgroup 只限资源,不防数据泄漏(那是子项目1 文件系统隔离)

---

## 6. 测试策略

### 单测(`tests/test_tools_bash_cgroup.py` 或并入 isolation 测试)
- `scope_available()`:monkeypatch subprocess 返 0/异常 → True/False
- `_cgroup_argv`:验 argv 结构(systemd-run --scope + MemoryMax/CPUQuota + `--`)
- 4 组合 argv 构造(monkeypatch create_subprocess_exec/shell 捕获):
  - off+off → create_subprocess_shell(command)
  - off+on → create_subprocess_exec,argv[0]=unshare(无 systemd-run)
  - on+off → create_subprocess_exec,argv[0]=systemd-run,末尾 `bash -c command`,设 cwd=
  - on+on → create_subprocess_exec,argv[0]=systemd-run 且含 unshare,不设 cwd=
- 命令注入:on+off 时 command 作 `bash -c` 的 argv 项(不拼接)
- 资源值:mem_mb/cpu_pct 进 argv(MemoryMax=512M 等)

### e2e(staging,`PRAXIS_BASH_CGROUP=true`)
- cgroup OOM kill 孙子:命令 `sh -c 'dd if=/dev/zero of=/dev/null bs=256M count=1'`(MemoryMax 默认下吃超量)→ 验被 kill(或用小 MemoryMax 配置验);对比 cgroup off 时不 kill
- 正常命令(df -h / echo)在 cgroup 下正常
- cgroup + isolation 同开:跨用户读被挡(isolation)+ 资源受限(cgroup)
- fail-open:临时模拟 scope 不可用(难;或单测覆盖)→ 降级 rlimit 命令仍跑

---

## 7. DoD

- [ ] config `bash_cgroup` + `bash_cgroup_mem_mb` + `bash_cgroup_cpu_pct` + `_KNOWN_KEYS` + 单测
- [ ] `scope_available()` 探测 + 单测
- [ ] `_cgroup_argv()` + 单测
- [ ] BashTool `cgroup`/`cgroup_mem_mb`/`cgroup_cpu_pct` 参数 + run() 4 组合二分 + 单测
- [ ] 命令注入防护延续(on+off 的 command 走 argv)+ 单测
- [ ] chat_registry / app.py 透传 + fail-open(scope 不可用降级)+ 启动 warning + 单测
- [ ] 全量回归零回归(cgroup off == 子项目1 状态)
- [ ] e2e staging:cgroup kill 超量孙子 / 正常命令 OK / cgroup+isolation 同开
- [ ] 文档:release note 更新(cgroup 资源覆盖孙子 + fail-open + 仍不覆盖)
- [ ] commit + 部署 + 观察

---

## 8. 依赖 + 部署影响

- **无新 pip 依赖**(systemd-run = systemd,staging 有;subprocess stdlib)
- **staging env**:`PRAXIS_BASH_CGROUP=true`(e2e)
- **不动**:litellm / FE / MCP / 主链 / v0.17 软沙盒 / v0.18-1 文件系统隔离
- **回滚**:`PRAXIS_BASH_CGROUP=false`(或不配)→ 行为 == v0.18-1
- **前提**:`systemd-run --user --scope` 可用(staging 已验);否则 fail-open 降级 rlimit

---

## 9. 后续(v0.18 其它子项目)

- 网络隔离(`unshare --net`)
- 磁盘 IO / TasksMax 限制(cgroup `-p IOMax` / `-p TasksMax`)
- RemoteBashTool / MCP HTTP transport / mid-call 重连 / CC npx 适配(node18+)
