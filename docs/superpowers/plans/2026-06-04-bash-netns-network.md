# BashTool 网络隔离(unshare --net)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 BashTool 加 opt-in 的网络隔离——命令在独立 net namespace(`unshare --net`)内跑,无 veth 无路由 → 外网/内网外联全封,补"真隔离三件套"最后一块(文件系统✓ 资源✓ 网络✓)。

**Architecture:** 独立开关 `PRAXIS_BASH_NETNS`(与 isolation/cgroup 正交)。netns 不新增矩阵列:isolation on 时给 `_isolation_argv` 加 `--net`;isolation off + netns on 走新轻量路径 `_netns_argv`(unshare --net + bash -c)。run() inner 由 2→3 情形,零回归 shell 判据加 `not netns`。cgroup 包裹层不变。netns 不可用时 fail-closed(不注册 Bash,镜像子项目1)。

**Tech Stack:** Python asyncio/subprocess + unshare(util-linux net namespace)+ pytest。无新 pip 依赖。

**Spec:** `docs/superpowers/specs/2026-06-04-bash-netns-network-design.md`

---

## 起点与约束

- 起点:`main` HEAD `473baa3`(子项目3 spec)= v0.18 子项目1+2 已 ship + 子项目3 spec。
- staging 已验探针(spec §1):`unshare --user --map-root-user --net` 单独/+mount/+systemd-run scope rc=0;netns 内 egress `Network unreachable`;无 netns 对比 CONNECTED;netns 内只 lo(down)。
- 雷区:工作区有无关 microbiome brains 改动,**每次 commit 只 add 目标文件,绝不 `git add .` / `-A`**。
- commit message 简体中文,末尾 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`。
- 部署 SOP / e2e 探针:见 Task 5(controller 亲做)。

## File Structure(本子项目要碰的文件)

| 文件 | 动作 | 职责 |
|---|---|---|
| `praxis2/config.py` | 改 3 处 | `bash_netns` 字段 + `_KNOWN_KEYS` + `load_from_env` |
| `praxis2/tools/bash.py` | 加 helper + run 改造 | `netns_available()` / `_netns_argv()` / `_isolation_argv` 加 netns 参数 / run 3 情形 + __init__ |
| `praxis2/server/chat_registry.py` | 改签名 + 注册 | `bash_netns` 透传 |
| `praxis2/server/app.py` | 改 3 处 | import netns_available + chat-stream fail-closed 合并 + 启动 warning |
| `tests/test_tools_bash_netns.py` | 新建 | netns 逻辑全覆盖 |
| `tests/test_config.py` / `test_chat_registry.py` | 追加 | 配置 + 透传 |
| `tests/_auth_test_helpers.py` | 追加字段 | `_TestSettings` 补 `bash_netns`(防缺字段) |

---

## Task 1: config 加 bash_netns

**Files:**
- Modify: `praxis2/config.py`(字段 125 后 / _KNOWN_KEYS 234 后 / load_from_env 339 后)
- Test: `tests/test_config.py`(追加)

- [ ] **Step 1: 写失败测试**

`tests/test_config.py` 末尾追加(先看文件里 `test_bash_cgroup_from_env` 等怎么调 `load_from_env`——用同样的 env 基底辅助,下面 `_base_env()` 是占位,对齐现有写法):

```python
def test_bash_netns_default(monkeypatch):
    monkeypatch.delenv("PRAXIS_BASH_NETNS", raising=False)
    from praxis2.config import load_from_env
    s = load_from_env(_base_env())
    assert s.bash_netns is False


def test_bash_netns_from_env(monkeypatch):
    monkeypatch.setenv("PRAXIS_BASH_NETNS", "true")
    from praxis2.config import load_from_env
    s = load_from_env(_base_env())
    assert s.bash_netns is True
```

注:`_base_env()` 指 test_config.py 里现有测试构造合法 env 的方式(对齐 `test_bash_cgroup_*` 的调用)。

- [ ] **Step 2: 跑测试确认红**

Run: `.venv/bin/python -m pytest tests/test_config.py -k bash_netns -v`
Expected: FAIL(Settings 无 `bash_netns` 字段)。

- [ ] **Step 3: 加 Settings 字段**

`praxis2/config.py` 第 125 行 `bash_cgroup_cpu_pct: int = 100 ...` 之后追加:

```python
    bash_netns: bool = False  # v0.18 子项目3:网络隔离(unshare --net)
```

- [ ] **Step 4: 加 _KNOWN_KEYS**

`_KNOWN_KEYS` 里 `"PRAXIS_BASH_CGROUP_CPU_PCT",`(第 234 行)之后追加:

```python
    "PRAXIS_BASH_NETNS",
```

- [ ] **Step 5: 加 load_from_env**

`load_from_env` 里 `bash_cgroup_cpu_pct=int(e.get("PRAXIS_BASH_CGROUP_CPU_PCT") or "100"),`(第 339 行)之后追加:

```python
        bash_netns=_get_bool(e, "PRAXIS_BASH_NETNS", False),
```

- [ ] **Step 6: 跑测试确认绿**

Run: `.venv/bin/python -m pytest tests/test_config.py -v`
Expected: 全 PASS。

- [ ] **Step 7: Commit**

```bash
git add praxis2/config.py tests/test_config.py
git commit -m "feat(config): 加 bash_netns 配置

v0.18 子项目3:PRAXIS_BASH_NETNS 开关网络隔离(unshare --net)。bool 用
_get_bool,与 isolation/cgroup 同风格。

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: bash.py netns helper(netns_available + _netns_argv + _isolation_argv 加 netns)

**Files:**
- Modify: `praxis2/tools/bash.py`(模块级:`scope_available` 后加 `netns_available`;`_isolation_argv` 加参数;新 `_netns_argv`)
- Test: `tests/test_tools_bash_netns.py`(新建)

- [ ] **Step 1: 写失败测试(新建 tests/test_tools_bash_netns.py)**

```python
"""BashTool 网络隔离单测(v0.18 子项目3)。"""
from praxis2.tools import bash as bashmod


def test_netns_available_true(monkeypatch):
    class _R:
        returncode = 0
    monkeypatch.setattr(bashmod.subprocess, "run", lambda *a, **k: _R())
    bashmod.netns_available.cache_clear()
    assert bashmod.netns_available() is True


def test_netns_available_false(monkeypatch):
    def _boom(*a, **k):
        raise OSError("no unshare")
    monkeypatch.setattr(bashmod.subprocess, "run", _boom)
    bashmod.netns_available.cache_clear()
    assert bashmod.netns_available() is False


def test_netns_argv_structure():
    argv = bashmod._netns_argv(command="echo hi")
    assert argv[:5] == ["unshare", "--user", "--map-root-user", "--net", "--"]
    assert argv[-3:] == ["/bin/bash", "-c", "echo hi"]  # command 单 argv 元素


def test_isolation_argv_netns_on_has_net():
    argv = bashmod._isolation_argv(
        command="echo hi", sandbox="/s", files_root="/f", mask="", cwd="/s", netns=True,
    )
    assert "--net" in argv
    assert "--mount" in argv  # mount + net 同次 unshare


def test_isolation_argv_netns_off_no_net():
    argv = bashmod._isolation_argv(
        command="echo hi", sandbox="/s", files_root="/f", mask="", cwd="/s",
    )
    assert "--net" not in argv  # 默认不含(回归保护)
    assert "--mount" in argv
```

- [ ] **Step 2: 跑测试确认红**

Run: `.venv/bin/python -m pytest tests/test_tools_bash_netns.py -v`
Expected: FAIL(无 `netns_available` / `_netns_argv`;`_isolation_argv` 无 `netns` 参数)。

- [ ] **Step 3: 实现 netns_available**

`praxis2/tools/bash.py` 在 `scope_available()` 函数之后(第 94 行 `return False` 之后、`_cgroup_argv` 之前)追加:

```python
@functools.lru_cache(maxsize=1)
def netns_available() -> bool:
    """探测 unprivileged user+net namespace 是否可用(网络隔离 fail-closed 用)。
    跑一次 `unshare --user --map-root-user --net -- true`,returncode==0 即可用。
    lru_cache:每进程只探一次。"""
    try:
        r = subprocess.run(
            ["unshare", "--user", "--map-root-user", "--net", "--", "true"],
            capture_output=True,
            timeout=5,
        )
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
```

- [ ] **Step 4: `_isolation_argv` 加 netns 参数 + 新增 `_netns_argv`**

把 `praxis2/tools/bash.py` 现有 `_isolation_argv`(第 145-158 行):

```python
def _isolation_argv(
    *, command: str, sandbox: str, files_root: str, mask: str, cwd: str
) -> list[str]:
    """构造 unshare 隔离命令 argv。user command 走位置参数 $3(防注入)。"""
    return [
        "unshare", "--user", "--map-root-user", "--mount", "--",
        "/bin/sh", "-c", SETUP_TEMPLATE,
        "praxis-bash",  # $0
        sandbox,        # $1
        files_root,     # $2
        command,        # $3
        mask,           # $4
        cwd,            # $5
    ]
```

替换为(加 `netns` 参数,条件插 `--net`):

```python
def _isolation_argv(
    *, command: str, sandbox: str, files_root: str, mask: str, cwd: str,
    netns: bool = False,
) -> list[str]:
    """构造 unshare 隔离命令 argv。user command 走位置参数 $3(防注入)。
    netns=True → 加 --net(网络隔离,与 mount ns 同次 unshare;lo 不拉起,
    SETUP_TEMPLATE 无需改)。"""
    flags = ["unshare", "--user", "--map-root-user", "--mount"]
    if netns:
        flags.append("--net")
    return [
        *flags, "--",
        "/bin/sh", "-c", SETUP_TEMPLATE,
        "praxis-bash",  # $0
        sandbox,        # $1
        files_root,     # $2
        command,        # $3
        mask,           # $4
        cwd,            # $5
    ]


def _netns_argv(*, command: str) -> list[str]:
    """isolation=off + netns=on 轻量路径:仅 net namespace,无 mount 遮蔽。
    command 走 bash -c 单 argv 元素(同 isolation-off 路径,不拼接 → 注入防护);
    cwd 由 subprocess kw 设(无 mount ns,宿主 cwd 可见)。"""
    return [
        "unshare", "--user", "--map-root-user", "--net", "--",
        "/bin/bash", "-c", command,
    ]
```

(`functools` / `subprocess` 已在顶部 import,无需再加。)

- [ ] **Step 5: 跑测试确认绿**

Run: `.venv/bin/python -m pytest tests/test_tools_bash_netns.py -v`
Expected: 5 passed。

- [ ] **Step 6: Commit**

```bash
git add praxis2/tools/bash.py tests/test_tools_bash_netns.py
git commit -m "feat(bash): netns_available() + _netns_argv() + _isolation_argv 加 netns

unshare --net 探测(fail-closed 用,lru_cache)。_isolation_argv 加 netns
参数条件插 --net(mount+net 同次 unshare)。_netns_argv 轻量路径(isolation
off + netns on:unshare --net + bash -c,无遮蔽脚本)。

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: BashTool netns 参数 + run() 3 情形 inner

**Files:**
- Modify: `praxis2/tools/bash.py`(__init__ 加参数 / run 247-286 二分扩 3 情形)
- Test: `tests/test_tools_bash_netns.py`(追加)

- [ ] **Step 1: 写失败测试**

`tests/test_tools_bash_netns.py` 末尾追加:

```python
import asyncio


def _run(tool, payload):
    return asyncio.run(tool.run(payload))


def _capture_exec(monkeypatch):
    cap = {}
    async def fake_exec(*argv, **kw):
        cap["argv"] = list(argv)
        cap["kw"] = kw
        raise RuntimeError("stop")
    monkeypatch.setattr(bashmod.asyncio, "create_subprocess_exec", fake_exec)
    return cap


def _capture_shell(monkeypatch):
    cap = {}
    async def fake_shell(cmd, **kw):
        cap["cmd"] = cmd
        cap["kw"] = kw
        raise RuntimeError("stop")
    monkeypatch.setattr(bashmod.asyncio, "create_subprocess_shell", fake_shell)
    return cap


def test_all_off_uses_shell(tmp_path, monkeypatch):
    cap = _capture_shell(monkeypatch)
    _run(bashmod.BashTool(sandbox_root=tmp_path), {"command": "echo hi"})
    assert cap["cmd"] == "echo hi"  # v0.17 shell,零回归(netns 不开不走 exec)


def test_netns_only_uses_exec_with_net(tmp_path, monkeypatch):
    cap = _capture_exec(monkeypatch)
    _run(bashmod.BashTool(sandbox_root=tmp_path, netns=True), {"command": "echo hi"})
    assert cap["argv"][0] == "unshare"
    assert "--net" in cap["argv"]
    assert "--mount" not in cap["argv"]                     # netns-only 不含 mount
    assert cap["argv"][-3:] == ["/bin/bash", "-c", "echo hi"]
    assert cap["kw"].get("cwd") == str(tmp_path.resolve())  # netns-only → 设 cwd


def test_netns_with_isolation_has_mount_and_net(tmp_path, monkeypatch):
    cap = _capture_exec(monkeypatch)
    _run(bashmod.BashTool(sandbox_root=tmp_path, isolation=True, netns=True),
         {"command": "echo hi"})
    assert cap["argv"][0] == "unshare"
    assert "--mount" in cap["argv"] and "--net" in cap["argv"]
    assert "cwd" not in cap["kw"]                           # isolation on → 不设 cwd(SETUP cd)


def test_netns_with_cgroup_wraps_unshare(tmp_path, monkeypatch):
    cap = _capture_exec(monkeypatch)
    _run(bashmod.BashTool(sandbox_root=tmp_path, cgroup=True, netns=True),
         {"command": "echo hi"})
    assert cap["argv"][0] == "systemd-run"                  # cgroup 最外层
    assert "unshare" in cap["argv"] and "--net" in cap["argv"]


def test_netns_all_three_on(tmp_path, monkeypatch):
    cap = _capture_exec(monkeypatch)
    _run(bashmod.BashTool(sandbox_root=tmp_path, isolation=True, cgroup=True, netns=True),
         {"command": "echo hi"})
    assert cap["argv"][0] == "systemd-run"
    assert "unshare" in cap["argv"]
    assert "--mount" in cap["argv"] and "--net" in cap["argv"]


def test_netns_injection_safe(tmp_path, monkeypatch):
    cap = _capture_exec(monkeypatch)
    evil = 'x"; rm -rf /; "'
    _run(bashmod.BashTool(sandbox_root=tmp_path, netns=True), {"command": evil})
    assert cap["argv"][-1] == evil  # command 作 bash -c 的 argv 项,不拼接
```

- [ ] **Step 2: 跑测试确认红**

Run: `.venv/bin/python -m pytest tests/test_tools_bash_netns.py -k "netns_only or isolation or cgroup or all_three or injection or all_off" -v`
Expected: FAIL(BashTool 无 netns 参数 / run 不处理 netns)。

- [ ] **Step 3: __init__ 加 netns 参数**

`BashTool.__init__` 签名里 `cgroup_cpu_pct: int = 100,`(第 185 行)之后、`) -> None:` 之前加:

```python
        netns: bool = False,
```

函数体末尾 `self._cgroup_cpu_pct = cgroup_cpu_pct`(第 197 行)之后加:

```python
        self._netns = netns
```

- [ ] **Step 4: run() 二分扩 3 情形**

把 `praxis2/tools/bash.py` 现有的(第 247-286 行,从 `if not self._isolation and not self._cgroup:` 到 `create_subprocess_exec(...)` 块):

```python
            if not self._isolation and not self._cgroup:
                # v0.17 软沙盒(零回归):shell 模式
                proc = await asyncio.create_subprocess_shell(
                    command,
                    cwd=str(cwd_resolved),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    preexec_fn=preexec,
                    env=_sanitized_env(),
                )
            else:
                # 内层:isolation on → unshare argv(SETUP cd "$5",不设宿主 cwd);
                #       isolation off → bash -c command(设宿主 cwd)
                if self._isolation:
                    inner = _isolation_argv(
                        command=command,
                        sandbox=str(root_resolved),
                        files_root=str(root_resolved.parent),
                        mask=_mask_paths(self._isolation_mask),
                        cwd=str(cwd_resolved),
                    )
                    kw = {}  # cwd 由 SETUP_TEMPLATE 内 cd "$5" 在 namespace 处理
                else:
                    inner = ["/bin/bash", "-c", command]
                    kw = {"cwd": str(cwd_resolved)}
                # cgroup on → systemd-run --scope 前缀包整树(含孙子)
                if self._cgroup:
                    argv = _cgroup_argv(
                        mem_mb=self._cgroup_mem_mb, cpu_pct=self._cgroup_cpu_pct,
                    ) + inner
                else:
                    argv = inner
                proc = await asyncio.create_subprocess_exec(
                    *argv,
                    **kw,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    preexec_fn=preexec,
                    env=_sanitized_env(),
                )
```

替换为(inner 三情形 + 零回归判据加 `not netns`):

```python
            if not self._isolation and not self._cgroup and not self._netns:
                # v0.17 软沙盒(零回归):shell 模式(三隔离全关才走)
                proc = await asyncio.create_subprocess_shell(
                    command,
                    cwd=str(cwd_resolved),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    preexec_fn=preexec,
                    env=_sanitized_env(),
                )
            else:
                # 内层 inner 三情形:
                #   isolation on        → unshare --mount[--net] + SETUP(cd "$5",不设宿主 cwd)
                #   isolation off+netns → unshare --net + bash -c command(设宿主 cwd)
                #   仅 cgroup(iso/netns 全 off)→ bash -c command(设宿主 cwd)
                if self._isolation:
                    inner = _isolation_argv(
                        command=command,
                        sandbox=str(root_resolved),
                        files_root=str(root_resolved.parent),
                        mask=_mask_paths(self._isolation_mask),
                        cwd=str(cwd_resolved),
                        netns=self._netns,
                    )
                    kw = {}  # cwd 由 SETUP_TEMPLATE 内 cd "$5" 在 namespace 处理
                elif self._netns:
                    inner = _netns_argv(command=command)
                    kw = {"cwd": str(cwd_resolved)}  # 无 mount ns,宿主 cwd 可见
                else:
                    inner = ["/bin/bash", "-c", command]
                    kw = {"cwd": str(cwd_resolved)}
                # cgroup on → systemd-run --scope 前缀包整树(含孙子)
                if self._cgroup:
                    argv = _cgroup_argv(
                        mem_mb=self._cgroup_mem_mb, cpu_pct=self._cgroup_cpu_pct,
                    ) + inner
                else:
                    argv = inner
                proc = await asyncio.create_subprocess_exec(
                    *argv,
                    **kw,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    preexec_fn=preexec,
                    env=_sanitized_env(),
                )
```

- [ ] **Step 5: 跑测试确认绿 + bash/isolation/cgroup 不回归**

Run: `.venv/bin/python -m pytest tests/test_tools_bash_netns.py tests/test_tools_bash.py tests/test_tools_bash_isolation.py tests/test_tools_bash_cgroup.py -v`
Expected: 全 PASS(netns 新测试 + 原 bash/isolation/cgroup 测试零回归)。

- [ ] **Step 6: Commit**

```bash
git add praxis2/tools/bash.py tests/test_tools_bash_netns.py
git commit -m "feat(bash): BashTool netns 参数 + run() 3 情形 inner

run() inner 由 2→3 情形:isolation(加 netns→--net)/ netns-only(轻量
unshare --net)/ 仅 cgroup。零回归 shell 判据加 not netns(netns 单开走
exec)。cgroup 包裹层不变。command 走 argv(注入防护延续)。

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: chat_registry + app.py 集成(fail-closed + warning)

**Files:**
- Modify: `praxis2/server/chat_registry.py`(签名 31 后 / 注册 96 后)
- Modify: `praxis2/server/app.py`(import 63 / chat-stream 660-683 / warning 1136 后)
- Modify: `tests/_auth_test_helpers.py`(`_TestSettings` 补 `bash_netns`)
- Test: `tests/test_chat_registry.py`(追加)

- [ ] **Step 1: 写失败测试**

`tests/test_chat_registry.py` 末尾追加(先确认文件里 `test_bash_cgroup_*` 的 build_chat_registry 调法,对齐 import / 断言风格):

```python
def test_bash_netns_passed_to_tool(tmp_path):
    reg = build_chat_registry(bash_sandbox_root=str(tmp_path), bash_netns=True)
    assert reg.get("Bash")._netns is True


def test_bash_netns_default_off(tmp_path):
    reg = build_chat_registry(bash_sandbox_root=str(tmp_path))
    assert reg.get("Bash")._netns is False
```

- [ ] **Step 2: 跑测试确认红**

Run: `.venv/bin/python -m pytest tests/test_chat_registry.py -k bash_netns -v`
Expected: FAIL(build_chat_registry 无 bash_netns 参数)。

- [ ] **Step 3: chat_registry 加参数 + 透传**

`praxis2/server/chat_registry.py` 签名 `bash_cgroup_cpu_pct: int = 100,`(第 31 行)之后加:

```python
    bash_netns: bool = False,
```

注册 BashTool 处(第 90-97 行)的 `cgroup_cpu_pct=bash_cgroup_cpu_pct,` 之后加:

```python
            netns=bash_netns,
```

- [ ] **Step 4: _auth_test_helpers 补字段**

`tests/_auth_test_helpers.py` 的 `_TestSettings`,`bash_cgroup_cpu_pct: int = 100`(第 91 行)之后加:

```python
    bash_netns: bool = False
```

(对齐 config.py Settings 字段,防 app.py 访问/构造缺字段。)

- [ ] **Step 5: app.py import netns_available + chat-stream fail-closed 合并**

`praxis2/server/app.py` 顶部第 63 行 `from praxis2.tools.bash import scope_available, userns_available` 改为:

```python
from praxis2.tools.bash import netns_available, scope_available, userns_available
```

chat-stream 处(第 660-683 行,`bash_root = None` 到 build_chat_registry 调用)替换为:

```python
                bash_root = None
                bash_isolation = False
                bash_cgroup = False
                bash_netns = False
                if getattr(self._deps.settings, "bash_tool_enabled", False):
                    want_isolation = getattr(self._deps.settings, "bash_isolation", False)
                    want_netns = getattr(self._deps.settings, "bash_netns", False)
                    if (want_isolation and not userns_available()) or (
                        want_netns and not netns_available()
                    ):
                        pass  # fail-closed:isolation/netns 启用但对应 namespace 不可用 → 不注册 Bash(启动已 warning)
                    else:
                        bash_root = os.path.join(self._deps.settings.files_root, user_id)
                        bash_isolation = want_isolation
                        bash_netns = want_netns
                        # cgroup fail-open:scope 不可用 → 降级 rlimit(去 cgroup,Bash 仍注册)
                        bash_cgroup = (
                            getattr(self._deps.settings, "bash_cgroup", False)
                            and scope_available()
                        )
                reg = build_chat_registry(
                    selection=selection,
                    mcp_tools=self._mcp_pool.all_tools(),
                    bash_sandbox_root=bash_root,
                    bash_isolation=bash_isolation,
                    bash_isolation_mask=getattr(self._deps.settings, "bash_isolation_mask", ""),
                    bash_cgroup=bash_cgroup,
                    bash_cgroup_mem_mb=getattr(self._deps.settings, "bash_cgroup_mem_mb", 1024),
                    bash_cgroup_cpu_pct=getattr(self._deps.settings, "bash_cgroup_cpu_pct", 100),
                    bash_netns=bash_netns,
                )
```

- [ ] **Step 6: app.py 启动 warning(netns fail-closed 可观测)**

`praxis2/server/app.py` 的 `_LifespanApp.__init__` 里,现有 cgroup fail-open warning 块(第 1126-1136 行,以 `"fail-open 降级 rlimit(...)"` 结尾)**之后**追加:

```python
        # 注:与 _chat_stream 的 netns fail-closed 逻辑镜像(bash_tool_enabled &
        # bash_netns & !netns_available),改动需两处同步。
        if (
            getattr(settings, "bash_tool_enabled", False)
            and getattr(settings, "bash_netns", False)
            and not netns_available()
        ):
            _logger.warning(
                "PRAXIS_BASH_NETNS=true 但 user+net namespace 不可用(unshare 探测失败),"
                "fail-closed:BashTool 将不注册。需启用 unprivileged userns 或关闭网络隔离。"
            )
```

(`netns_available` 已在 Step 5 同文件 import。)

- [ ] **Step 7: 跑测试确认绿 + 不回归**

Run: `.venv/bin/python -m pytest tests/test_chat_registry.py -k bash_netns -v`(新测试绿)
Run: `.venv/bin/python -m pytest tests/ --ignore=tests/integration -k "chat_registry or bash or server or app or config" --tb=short -q`(相关零回归)

- [ ] **Step 8: Commit**

```bash
git add praxis2/server/chat_registry.py praxis2/server/app.py tests/test_chat_registry.py tests/_auth_test_helpers.py
git commit -m "feat(server): chat_registry + app.py 接入 bash_netns(fail-closed)

build_chat_registry 加 bash_netns 透传 BashTool。app.py:fail-closed 判据
合并 (isolation & !userns) or (netns & !netns_available) → 不注册 Bash +
启动 warning。_TestSettings 补字段。

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: 全量回归 + 部署 staging + e2e(controller 亲做)

**Files:** 无(部署 + 验证)

- [ ] **Step 1: 本地全量回归**

Run:
```
.venv/bin/python -m pytest tests/ --ignore=tests/integration -q --tb=no --junit-xml=/tmp/v18net.xml >/dev/null 2>&1; echo "EXIT=$?"
.venv/bin/python -c "import xml.etree.ElementTree as ET; r=ET.parse('/tmp/v18net.xml').getroot(); s=r if r.tag=='testsuite' else r[0]; a=s.attrib; print('tests=%s failures=%s errors=%s' % (a.get('tests'),a.get('failures'),a.get('errors')))"
```
Expected: failures=0 errors=0。**不绿不部署**。

- [ ] **Step 2: rsync 4 文件 + 加 env**

```bash
rsync -aq praxis2/config.py               zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/praxis2/
rsync -aq praxis2/tools/bash.py           zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/praxis2/tools/
rsync -aq praxis2/server/chat_registry.py zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/praxis2/server/
rsync -aq praxis2/server/app.py           zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/praxis2/server/
ssh zkyd@10.102.106.53 'grep -q PRAXIS_BASH_NETNS ~/praxis2.env || echo "export PRAXIS_BASH_NETNS=true" >> ~/praxis2.env'
```

- [ ] **Step 3: 重启 gunicorn + 验版本**

找 master pid(`ps -ef|grep '[g]unicorn'|grep python3|awk '$3==1{print $2}'`)→ kill → sleep 3 → cd repo + source env + nohup gunicorn(同 SOP)→ sleep 7 → `curl -s 127.0.0.1:8001/api/info`(version 仍 v0.17.0,本子项目不 bump)+ tail 启动 log 确认**无 netns fail-closed warning**(staging netns 已验可用 → Bash 应正常注册)。

- [ ] **Step 4: e2e — netns 封外联(写脚本 rsync 跑)**

写 `/tmp/v18_netns_probe.py`(本地)→ rsync staging /tmp → `ssh zkyd@10.102.106.53 'cd ~/data1/mzy/PRAXIS-2 && source ~/praxis2.env && PYTHONPATH=$PWD ~/software/miniconda3/envs/praxis2/bin/python /tmp/v18_netns_probe.py'`(⚠ PYTHONPATH=$PWD 必须)。脚本直接调 BashTool(确定性,不依赖 AI):
- `BashTool(sandbox_root=sb, netns=True)` 跑连 .40:8080 的 python socket → 验 stdout 含 `BLOCKED`/`unreachable`(隔离生效)
- 对比 `BashTool(sandbox_root=sb, netns=False)` 同命令 → 连通(`CONNECTED`)
- `BashTool(netns=True, isolation=True)` 跨用户读 + 连网 → 读不到(隔离)+ 外联挡(netns)
- `BashTool(netns=True, cgroup=True)` 连网 → 外联挡(叠加 sanity)
- `BashTool(netns=True)` 跑 `df -h /` → 正常返回(非网络无回归)

打印 NETNS-AVAIL + 各 case 结果。连接目标用 python `socket.create_connection(('10.102.106.40',8080),3)`(同 spec 探针)。

- [ ] **Step 5: 记录 e2e 结果**

确认:netns on 封外联(netns off 连通对比)、netns+isolation/cgroup 叠加正常、df-h 正常。若 netns off 也被挡 或 netns on 没挡 → 排查(systematic-debugging,不继续)。

---

## Task 6: release note + memory(controller 亲做)

**Files:**
- Modify: `VERSION-STATUS-v0.18.0-alpha.md`(追加子项目3 段)
- Modify: memory

- [ ] **Step 1: 更新 release note**

`VERSION-STATUS-v0.18.0-alpha.md` 追加子项目3 段:网络隔离(unshare --net)落地、真隔离三件套齐(文件系统+资源+网络)、独立 PRAXIS_BASH_NETNS 开关 + fail-closed(netns 不可用不注册 Bash)、lo 保持 down、仍不覆盖(pathname AF_UNIX socket / lo down 副作用)、e2e 实测(netns 封外联 + 对比 + 三层叠加)。

- [ ] **Step 2: Commit release note**

```bash
git add VERSION-STATUS-v0.18.0-alpha.md
git commit -m "docs: v0.18 子项目3 release note(BashTool 网络隔离)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 3: push + 更新 memory**

```bash
git push origin main
```
更新 memory:新建 `project_v018_netns.md` 记子项目3(机制/决策/e2e/三件套齐)+ MEMORY.md 加一条。

---

## Self-Review(against spec)

**1. Spec coverage:**
- spec §3.1 netns_available → **Task 2** ✓
- spec §3.2 _isolation_argv 加 netns → **Task 2** ✓
- spec §3.3 _netns_argv → **Task 2** ✓
- spec §3.4 cwd 处理(isolation on 不设 / netns-only 设)→ **Task 3**(kw)✓
- spec §3.5 run 三情形 + 零回归判据加 not netns → **Task 3** ✓
- spec §4 config/__init__/chat_registry/app fail-closed/warning/_TestSettings → Task 1/3/4 ✓
- spec §6 单测(probe/argv/3 情形/叠加/注入/零回归/config/registry)→ Task 1-4 ✓;e2e → **Task 5** ✓
- spec §7 release note → **Task 6** ✓

**2. Placeholder scan:** 代码步骤均含完整代码。Task 1/4 Step 1 的 `_base_env()` / build 调法、Task 5 部署 SOP、Task 6 release note 内容有"对齐现有/现场"提示(运行期事实,需现场确认,非 placeholder)。

**3. Type consistency:**
- `netns_available()`(Task 2)与 app.py(Task 4)一致 ✓
- `_netns_argv(command=...)`(Task 2)与 run()(Task 3)一致 ✓
- `_isolation_argv(..., netns=...)`(Task 2)与 run()(Task 3)一致 ✓
- `BashTool(netns=...)`(Task 3)与 chat_registry(Task 4)一致 ✓
- `bash_netns`(config Task 1)与 app.py/registry/_TestSettings 引用一致 ✓
- run 三情形 inner/kw/argv 在 Task 3 内自洽 ✓

**风险点:**
- Task 1/4 Step 1 的 `_base_env()` / build_chat_registry 调法需对齐 test_config.py / test_chat_registry.py 现有辅助(子项目1/2 已建立同款测试,直接照搬)。
- run() 替换块以现有第 247-286 行为准——实现者**先 Read 该段确认与 plan 引用一致**(子项目2 刚改过此处),再 Edit。
- e2e 连接目标 .40:8080 须从 .53 可达(spec 探针已验 baseline CONNECTED)。

---

## Execution Handoff

Plan 已存 `docs/superpowers/plans/2026-06-04-bash-netns-network.md`。沿用 **subagent-driven-development**:fresh subagent per task + 两阶段 review(spec → code quality)。Task 5/6 部署/收尾 controller 亲做。
