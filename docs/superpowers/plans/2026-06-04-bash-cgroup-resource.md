# BashTool cgroup 资源隔离(systemd-run --scope)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 BashTool 加 opt-in 的 cgroup 资源隔离——命令经 `systemd-run --user --scope -p MemoryMax -p CPUQuota` 运行,内存/CPU 限制覆盖整个进程树(含孙子进程),补 v0.17 rlimit 只管直接子进程的短板。

**Architecture:** 独立开关 `PRAXIS_BASH_CGROUP` 启用时,`BashTool.run` 在 isolation 之上再叠 systemd-run --scope 前缀(cgroup × isolation 4 种组合)。command 走 argv 位置参数(注入防护延续)。scope 不可用时 fail-open 降级 rlimit(命令仍跑)。子项目1 文件系统隔离 + v0.17 所有防护正交保留。

**Tech Stack:** Python asyncio/subprocess + systemd-run(systemd)+ pytest。无新 pip 依赖。

**Spec:** `docs/superpowers/specs/2026-06-04-bash-cgroup-resource-design.md`

---

## 起点与约束

- 起点:`main` HEAD `1a42487`(子项目2 spec)= v0.18 子项目1 已 ship + 子项目2 spec。
- staging 已验:`systemd-run --user --scope` 同步拿 stdout/exit、接受 MemoryMax/CPUQuota、嵌套 unshare、cgroup OOM kill 孙子(exit 137)。
- 雷区:工作区有无关 microbiome brains 改动,**每次 commit 只 add 目标文件,绝不 `git add .`**。
- commit message 简体中文,末尾 `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>`。

## File Structure(本子项目要碰的文件)

| 文件 | 动作 | 职责 |
|---|---|---|
| `praxis2/config.py` | 改 3 处 | `bash_cgroup` + `bash_cgroup_mem_mb` + `bash_cgroup_cpu_pct` |
| `praxis2/tools/bash.py` | 加 helper + run 改造 | `scope_available()` / `_cgroup_argv()` / run 4 组合矩阵 |
| `praxis2/server/chat_registry.py` | 改签名 + 注册 | `bash_cgroup`/`mem_mb`/`cpu_pct` 透传 |
| `praxis2/server/app.py` | 改 2 处 | fail-open 算 cgroup + import scope_available + 启动 warning |
| `tests/test_tools_bash_cgroup.py` | 新建 | cgroup 逻辑全覆盖 |
| `tests/test_config.py` / `test_chat_registry.py` | 追加 | 配置 + 透传 |
| `tests/_auth_test_helpers.py` | 追加字段 | `_TestSettings` 补 3 个 cgroup 字段(防裸访问 AttributeError) |

---

## Task 1: config 加 bash_cgroup + mem_mb + cpu_pct

**Files:**
- Modify: `praxis2/config.py`(字段 121 后 / _KNOWN_KEYS / load_from_env 328 后)
- Test: `tests/test_config.py`(追加)

- [ ] **Step 1: 写失败测试**

`tests/test_config.py` 末尾追加:

```python
def test_bash_cgroup_defaults(monkeypatch):
    for k in ("PRAXIS_BASH_CGROUP", "PRAXIS_BASH_CGROUP_MEM_MB", "PRAXIS_BASH_CGROUP_CPU_PCT"):
        monkeypatch.delenv(k, raising=False)
    from praxis2.config import Settings, load_from_env
    s = load_from_env(_base_env())  # 复用文件里其它测试的 env 基底辅助(若无则用 dict(os.environ))
    assert s.bash_cgroup is False
    assert s.bash_cgroup_mem_mb == 1024
    assert s.bash_cgroup_cpu_pct == 100


def test_bash_cgroup_from_env(monkeypatch):
    monkeypatch.setenv("PRAXIS_BASH_CGROUP", "true")
    monkeypatch.setenv("PRAXIS_BASH_CGROUP_MEM_MB", "512")
    monkeypatch.setenv("PRAXIS_BASH_CGROUP_CPU_PCT", "200")
    from praxis2.config import load_from_env
    s = load_from_env(_base_env())
    assert s.bash_cgroup is True
    assert s.bash_cgroup_mem_mb == 512
    assert s.bash_cgroup_cpu_pct == 200
```

注:`_base_env()` 指 test_config.py 里现有测试构造合法 env 的方式——先看文件里 `test_bash_isolation_from_env` 等怎么调 `load_from_env`(用 monkeypatch.setenv + `load_from_env(...)` 的实参),对齐;若它们直接 `load_from_env(_minimal_env())` 之类,沿用同一辅助。

- [ ] **Step 2: 跑测试确认红**

Run: `.venv/bin/python -m pytest tests/test_config.py -k bash_cgroup -v`
Expected: FAIL(Settings 无 bash_cgroup 字段)。

- [ ] **Step 3: 加 Settings 字段**

`praxis2/config.py` 第 121 行 `bash_isolation_mask: str = ""` 之后追加:

```python
    bash_cgroup: bool = False  # v0.18 子项目2:cgroup 资源隔离(systemd-run --scope)
    bash_cgroup_mem_mb: int = 1024  # MemoryMax(MB),默认 1GB(与 rlimit_mem 对齐)
    bash_cgroup_cpu_pct: int = 100  # CPUQuota(%),默认 100=1 核
```

- [ ] **Step 4: 加 _KNOWN_KEYS**

`_KNOWN_KEYS` 里 `"PRAXIS_BASH_ISOLATION_MASK",` 之后追加:

```python
    "PRAXIS_BASH_CGROUP",
    "PRAXIS_BASH_CGROUP_MEM_MB",
    "PRAXIS_BASH_CGROUP_CPU_PCT",
```

- [ ] **Step 5: 加 load_from_env**

`load_from_env` 里 `bash_isolation_mask=e.get("PRAXIS_BASH_ISOLATION_MASK", ""),` 之后追加:

```python
        bash_cgroup=_get_bool(e, "PRAXIS_BASH_CGROUP", False),
        bash_cgroup_mem_mb=int(e.get("PRAXIS_BASH_CGROUP_MEM_MB") or "1024"),
        bash_cgroup_cpu_pct=int(e.get("PRAXIS_BASH_CGROUP_CPU_PCT") or "100"),
```

(用 `int(e.get(key) or "默认")` 而非 `_get_int`:`_get_int` 经 `_get_str`+`_DEFAULTS` 无 default 参数;沿用子项目1 `bash_isolation_mask` 的直接 `e.get` 风格,missing/空串 → 默认,非法值 int() 抛 ValueError fail-fast。)

- [ ] **Step 6: 跑测试确认绿**

Run: `.venv/bin/python -m pytest tests/test_config.py -v`
Expected: 全 PASS。

- [ ] **Step 7: Commit**

```bash
git add praxis2/config.py tests/test_config.py
git commit -m "feat(config): 加 bash_cgroup + mem_mb + cpu_pct 配置

v0.18 子项目2:PRAXIS_BASH_CGROUP 开关 cgroup 资源隔离,MEM_MB/CPU_PCT
可配(默认 1024/100)。int 用 int(e.get or 默认),与子项目1 e.get 风格一致。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: bash.py cgroup helper(scope_available + _cgroup_argv)

**Files:**
- Modify: `praxis2/tools/bash.py`(模块级,`userns_available` / `_isolation_argv` 旁)
- Test: `tests/test_tools_bash_cgroup.py`(新建)

- [ ] **Step 1: 写失败测试(新建 tests/test_tools_bash_cgroup.py)**

```python
"""BashTool cgroup 资源隔离单测(v0.18 子项目2)。"""
from praxis2.tools import bash as bashmod


def test_scope_available_true(monkeypatch):
    class _R:
        returncode = 0
    monkeypatch.setattr(bashmod.subprocess, "run", lambda *a, **k: _R())
    bashmod.scope_available.cache_clear()
    assert bashmod.scope_available() is True


def test_scope_available_false(monkeypatch):
    def _boom(*a, **k):
        raise OSError("no systemd-run")
    monkeypatch.setattr(bashmod.subprocess, "run", _boom)
    bashmod.scope_available.cache_clear()
    assert bashmod.scope_available() is False


def test_cgroup_argv_structure():
    argv = bashmod._cgroup_argv(mem_mb=512, cpu_pct=200)
    assert argv[:4] == ["systemd-run", "--user", "--scope", "--quiet"]
    assert "MemoryMax=512M" in argv
    assert "CPUQuota=200%" in argv
    assert argv[-1] == "--"  # 后面接 inner 命令
```

- [ ] **Step 2: 跑测试确认红**

Run: `.venv/bin/python -m pytest tests/test_tools_bash_cgroup.py -v`
Expected: FAIL(无 `scope_available` / `_cgroup_argv`)。

- [ ] **Step 3: 实现 scope_available + _cgroup_argv**

`praxis2/tools/bash.py` 在 `userns_available()` 函数之后(约第 80 行,`_isolation_argv` 之前或 `userns_available` 紧邻处)追加:

```python
@functools.lru_cache(maxsize=1)
def scope_available() -> bool:
    """探测 systemd-run --user --scope 是否可用(cgroup fail-open 用)。
    跑一次 `systemd-run --user --scope --quiet -- true`,returncode==0 即可用。"""
    try:
        r = subprocess.run(
            ["systemd-run", "--user", "--scope", "--quiet", "--", "true"],
            capture_output=True,
            timeout=5,
        )
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _cgroup_argv(*, mem_mb: int, cpu_pct: int) -> list[str]:
    """systemd-run --user --scope 前缀:cgroup 限内存/CPU,覆盖整个进程树(含孙子)。
    拼在 inner 命令(unshare argv 或 ['/bin/bash','-c',command])之前。"""
    return [
        "systemd-run", "--user", "--scope", "--quiet",
        "-p", f"MemoryMax={mem_mb}M",
        "-p", f"CPUQuota={cpu_pct}%",
        "--",
    ]
```

(`functools` / `subprocess` 子项目1 已在顶部 import,无需再加。)

- [ ] **Step 4: 跑测试确认绿**

Run: `.venv/bin/python -m pytest tests/test_tools_bash_cgroup.py -v`
Expected: 3 passed。

- [ ] **Step 5: Commit**

```bash
git add praxis2/tools/bash.py tests/test_tools_bash_cgroup.py
git commit -m "feat(bash): scope_available() + _cgroup_argv()

systemd-run --user --scope 探测(fail-open 用,lru_cache)+ cgroup 前缀
构造(MemoryMax/CPUQuota,覆盖整树)。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: BashTool cgroup 参数 + run() 4 组合矩阵

**Files:**
- Modify: `praxis2/tools/bash.py`(__init__ 加参数 / run 214-239 二分扩 4 组合)
- Test: `tests/test_tools_bash_cgroup.py`(追加)

- [ ] **Step 1: 写失败测试**

`tests/test_tools_bash_cgroup.py` 末尾追加:

```python
import asyncio

import pytest


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


def test_off_off_uses_shell(tmp_path, monkeypatch):
    cap = _capture_shell(monkeypatch)
    _run(bashmod.BashTool(sandbox_root=tmp_path), {"command": "echo hi"})
    assert cap["cmd"] == "echo hi"  # v0.17 shell,零回归


def test_cgroup_on_isolation_off(tmp_path, monkeypatch):
    cap = _capture_exec(monkeypatch)
    _run(bashmod.BashTool(sandbox_root=tmp_path, cgroup=True, cgroup_mem_mb=256, cgroup_cpu_pct=100),
         {"command": "echo hi"})
    assert cap["argv"][0] == "systemd-run"
    assert "MemoryMax=256M" in cap["argv"]
    assert cap["argv"][-3:] == ["/bin/bash", "-c", "echo hi"]  # inner = bash -c command
    assert cap["kw"].get("cwd") == str(tmp_path.resolve())     # isolation off → 设 cwd


def test_cgroup_on_isolation_on(tmp_path, monkeypatch):
    cap = _capture_exec(monkeypatch)
    _run(bashmod.BashTool(sandbox_root=tmp_path, cgroup=True, isolation=True),
         {"command": "echo hi"})
    assert cap["argv"][0] == "systemd-run"
    assert "unshare" in cap["argv"]                            # cgroup 包 unshare
    assert "cwd" not in cap["kw"]                              # isolation on → 不设 cwd(SETUP cd)


def test_cgroup_injection_safe(tmp_path, monkeypatch):
    cap = _capture_exec(monkeypatch)
    evil = 'x"; rm -rf /; "'
    _run(bashmod.BashTool(sandbox_root=tmp_path, cgroup=True), {"command": evil})
    assert cap["argv"][-1] == evil  # command 作 bash -c 的 argv 项,不拼接
```

- [ ] **Step 2: 跑测试确认红**

Run: `.venv/bin/python -m pytest tests/test_tools_bash_cgroup.py -k "cgroup_on or off_off or injection" -v`
Expected: FAIL(BashTool 无 cgroup 参数 / run 不处理 cgroup)。

- [ ] **Step 3: __init__ 加 cgroup 参数**

`BashTool.__init__` 签名末尾(`isolation_mask: str = "",` 之后、`) -> None:` 之前)加:

```python
        cgroup: bool = False,
        cgroup_mem_mb: int = 1024,
        cgroup_cpu_pct: int = 100,
```

函数体末尾(`self._isolation_mask = isolation_mask` 之后)加:

```python
        self._cgroup = cgroup
        self._cgroup_mem_mb = cgroup_mem_mb
        self._cgroup_cpu_pct = cgroup_cpu_pct
```

- [ ] **Step 4: run() 二分扩 4 组合矩阵**

把 `praxis2/tools/bash.py` 现有的(第 213-241 行):

```python
        try:
            if self._isolation:
                argv = _isolation_argv(
                    command=command,
                    sandbox=str(root_resolved),
                    files_root=str(root_resolved.parent),
                    mask=_mask_paths(self._isolation_mask),
                    cwd=str(cwd_resolved),
                )
                # cwd 由 SETUP_TEMPLATE 内 cd "$5" 在 namespace 处理,此处不传 cwd=
                # (宿主 cwd 在 bind 重挂后 inode 失效)
                proc = await asyncio.create_subprocess_exec(
                    *argv,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    preexec_fn=preexec,
                    env=_sanitized_env(),
                )
            else:
                proc = await asyncio.create_subprocess_shell(
                    command,
                    cwd=str(cwd_resolved),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    preexec_fn=preexec,
                    env=_sanitized_env(),
                )
        except Exception as e:  # noqa: BLE001 — spawn 失败(如 preexec 异常)不冒泡
            return ToolResult(ok=False, error=f"命令 spawn 失败:{type(e).__name__}: {e}")
```

替换为(cgroup × isolation 4 组合):

```python
        try:
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
                    exec_cwd = None
                else:
                    inner = ["/bin/bash", "-c", command]
                    exec_cwd = str(cwd_resolved)
                # cgroup on → systemd-run --scope 前缀包整树(含孙子)
                if self._cgroup:
                    argv = _cgroup_argv(
                        mem_mb=self._cgroup_mem_mb, cpu_pct=self._cgroup_cpu_pct,
                    ) + inner
                else:
                    argv = inner
                kw = {} if exec_cwd is None else {"cwd": exec_cwd}
                proc = await asyncio.create_subprocess_exec(
                    *argv,
                    **kw,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    preexec_fn=preexec,
                    env=_sanitized_env(),
                )
        except Exception as e:  # noqa: BLE001 — spawn 失败(如 preexec 异常)不冒泡
            return ToolResult(ok=False, error=f"命令 spawn 失败:{type(e).__name__}: {e}")
```

- [ ] **Step 5: 跑测试确认绿 + bash/isolation 不回归**

Run: `.venv/bin/python -m pytest tests/test_tools_bash_cgroup.py tests/test_tools_bash.py tests/test_tools_bash_isolation.py -v`
Expected: 全 PASS(cgroup 新测试 + 原 bash/isolation 测试零回归)。

- [ ] **Step 6: Commit**

```bash
git add praxis2/tools/bash.py tests/test_tools_bash_cgroup.py
git commit -m "feat(bash): BashTool cgroup 参数 + run() 4 组合矩阵

cgroup × isolation 4 组合:off+off=shell(v0.17);其余 exec。cgroup on
时 systemd-run --scope 包 unshare(isolation on)或 bash -c command
(isolation off,设 cwd)。command 走 argv 位置参数(注入防护延续)。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: chat_registry + app.py 集成(fail-open + warning)

**Files:**
- Modify: `praxis2/server/chat_registry.py`(签名 27-28 后 / 注册)
- Modify: `praxis2/server/app.py`(import / chat-stream 660-675 / warning 1108-1116)
- Modify: `tests/_auth_test_helpers.py`(`_TestSettings` 补 3 字段)
- Test: `tests/test_chat_registry.py`(追加)

- [ ] **Step 1: 写失败测试**

`tests/test_chat_registry.py` 末尾追加:

```python
def test_bash_cgroup_passed_to_tool(tmp_path):
    reg = build_chat_registry(
        bash_sandbox_root=str(tmp_path), bash_cgroup=True,
        bash_cgroup_mem_mb=512, bash_cgroup_cpu_pct=200,
    )
    tool = reg.get("Bash")
    assert tool._cgroup is True
    assert tool._cgroup_mem_mb == 512
    assert tool._cgroup_cpu_pct == 200


def test_bash_cgroup_default_off(tmp_path):
    reg = build_chat_registry(bash_sandbox_root=str(tmp_path))
    assert reg.get("Bash")._cgroup is False
```

- [ ] **Step 2: 跑测试确认红**

Run: `.venv/bin/python -m pytest tests/test_chat_registry.py -k bash_cgroup -v`
Expected: FAIL(build_chat_registry 无 bash_cgroup 参数)。

- [ ] **Step 3: chat_registry 加参数 + 透传**

`praxis2/server/chat_registry.py` 签名(`bash_isolation_mask: str = "",` 之后)加:

```python
    bash_cgroup: bool = False,
    bash_cgroup_mem_mb: int = 1024,
    bash_cgroup_cpu_pct: int = 100,
```

注册 BashTool 处(现有 `reg.register(BashTool(sandbox_root=..., isolation=bash_isolation, isolation_mask=bash_isolation_mask))`)改为:

```python
        reg.register(BashTool(
            sandbox_root=Path(bash_sandbox_root),
            isolation=bash_isolation,
            isolation_mask=bash_isolation_mask,
            cgroup=bash_cgroup,
            cgroup_mem_mb=bash_cgroup_mem_mb,
            cgroup_cpu_pct=bash_cgroup_cpu_pct,
        ))
```

- [ ] **Step 4: _auth_test_helpers 补字段**

`tests/_auth_test_helpers.py` 的 `_TestSettings`(子项目1 已补 bash_tool_enabled/bash_isolation/bash_isolation_mask)再补:

```python
    bash_cgroup: bool = False
    bash_cgroup_mem_mb: int = 1024
    bash_cgroup_cpu_pct: int = 100
```

(对齐 config.py Settings 字段,防 app.py 裸/ getattr 访问缺字段。)

- [ ] **Step 5: app.py import scope_available + chat-stream 算 cgroup(fail-open)**

`praxis2/server/app.py` 顶部现有 `from praxis2.tools.bash import userns_available` 改为:

```python
from praxis2.tools.bash import scope_available, userns_available
```

chat-stream 处(现有第 660-675 行 bash_root 计算 + build_chat_registry)替换为:

```python
                bash_root = None
                bash_isolation = False
                bash_cgroup = False
                if getattr(self._deps.settings, "bash_tool_enabled", False):
                    want_isolation = getattr(self._deps.settings, "bash_isolation", False)
                    if want_isolation and not userns_available():
                        pass  # fail-closed:启用隔离但 userns 不可用 → 不注册 Bash(启动已 warning)
                    else:
                        bash_root = os.path.join(self._deps.settings.files_root, user_id)
                        bash_isolation = want_isolation
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
                )
```

- [ ] **Step 6: app.py 启动 warning(cgroup fail-open 可观测)**

`praxis2/server/app.py` 的 `_LifespanApp.__init__` 里,现有 isolation fail-closed warning(`if ... bash_isolation ... not userns_available(): _logger.warning(...)`)那段**之后**追加:

```python
        # 注:与 _chat_stream 的 cgroup fail-open 逻辑镜像,改动需两处同步。
        # cgroup fail-open 可观测:启用 cgroup 但 scope 不可用 → 降级 rlimit
        if (
            getattr(settings, "bash_tool_enabled", False)
            and getattr(settings, "bash_cgroup", False)
            and not scope_available()
        ):
            _logger.warning(
                "PRAXIS_BASH_CGROUP=true 但 systemd-run --scope 不可用,"
                "fail-open 降级 rlimit(资源限制仅覆盖直接子进程,孙子进程可逃逸)。"
            )
```

并把顶部 import(若 _LifespanApp 所在文件单独 import)确认 `scope_available` 已在 Step 5 import(同文件)。

- [ ] **Step 7: 跑测试确认绿 + 不回归**

Run: `.venv/bin/python -m pytest tests/test_chat_registry.py -v`(新测试绿)
Run: `.venv/bin/python -m pytest tests/ --ignore=tests/integration -k "chat_registry or bash or server or app or config" --tb=short -q`(相关零回归)

- [ ] **Step 8: Commit**

```bash
git add praxis2/server/chat_registry.py praxis2/server/app.py tests/test_chat_registry.py tests/_auth_test_helpers.py
git commit -m "feat(server): chat_registry + app.py 接入 bash_cgroup(fail-open)

build_chat_registry 加 bash_cgroup/mem_mb/cpu_pct 透传 BashTool。app.py:
Bash 注册时算 cgroup=settings.bash_cgroup and scope_available()(fail-open:
scope 不可用降级 rlimit,Bash 仍注册)+ 启动 warning。_TestSettings 补字段。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: 全量回归 + 部署 staging + e2e(controller 亲做)

**Files:** 无(部署 + 验证)

- [ ] **Step 1: 本地全量回归**

Run: `.venv/bin/python -m pytest tests/ --ignore=tests/integration -q --tb=no --junit-xml=/tmp/v18cg.xml >/dev/null 2>&1; echo "EXIT=$?"; .venv/bin/python -c "import xml.etree.ElementTree as ET; r=ET.parse('/tmp/v18cg.xml').getroot(); s=r if r.tag=='testsuite' else r[0]; a=s.attrib; print('tests=%s failures=%s errors=%s' % (a.get('tests'),a.get('failures'),a.get('errors')))"`
Expected: failures=0 errors=0。**不绿不部署**。

- [ ] **Step 2: rsync 4 文件 + 加 env**

```bash
cd /Volumes/T7/clade-learn/PRAXIS-2
rsync -aq praxis2/config.py               zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/praxis2/
rsync -aq praxis2/tools/bash.py           zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/praxis2/tools/
rsync -aq praxis2/server/chat_registry.py zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/praxis2/server/
rsync -aq praxis2/server/app.py           zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/praxis2/server/
ssh zkyd@10.102.106.53 'grep -q PRAXIS_BASH_CGROUP ~/praxis2.env || echo "export PRAXIS_BASH_CGROUP=true" >> ~/praxis2.env'
```

- [ ] **Step 3: 重启 gunicorn + 验版本**

找 master pid(`ps -ef|grep '[g]unicorn'|grep python3|awk '$3==1{print $2}'`)→ kill → sleep 3 → nohup gunicorn(同子项目1 SOP)→ sleep 6 → `curl -s 127.0.0.1:8001/api/info`(version v0.17.0,本子项目不 bump)+ tail 启动 log 查无 cgroup fail-open warning(scope 可用)。

- [ ] **Step 4: e2e — cgroup kill 超量孙子(写脚本 rsync 跑)**

写 `/tmp/v18_cgroup_probe.py`(本地)→ rsync staging /tmp → `ssh ... 'cd ~/data1/mzy/PRAXIS-2 && source ~/praxis2.env && PYTHONPATH=$PWD python /tmp/v18_cgroup_probe.py'`。脚本直接调 `BashTool(sandbox_root=sb, cgroup=True, cgroup_mem_mb=64)`:
- 跑 `sh -c "dd if=/dev/zero of=/dev/null bs=256M count=1"` → 验被 cgroup kill(exit_code 非 0 / 137 / stderr 含 Killed)
- 对比 `BashTool(sandbox_root=sb, cgroup=False)` 同命令 → 不被 kill(正常完成)
- `BashTool(cgroup=True)` 跑 `df -h /` → 正常返回
- `BashTool(cgroup=True, isolation=True)` 跑跨用户 cat → 读不到(隔离)+ 资源受限(叠加)

打印 SCOPE-AVAIL + 各 case 结果。

- [ ] **Step 5: 记录 e2e 结果**

确认:cgroup on 时超量孙子被 kill(cgroup off 不被)、df-h 正常、cgroup+isolation 叠加正常。若 cgroup off 也被 kill 或 cgroup on 没 kill → 排查(systematic-debugging,不继续)。

---

## Task 6: release note + memory(controller 亲做)

**Files:**
- Modify: `VERSION-STATUS-v0.18.0-alpha.md`(追加子项目2 段)
- Modify: memory

- [ ] **Step 1: 更新 release note**

`VERSION-STATUS-v0.18.0-alpha.md` 追加子项目2 段:cgroup 资源隔离(systemd-run --scope)落地、覆盖整树含孙子(补 rlimit 短板)、独立 PRAXIS_BASH_CGROUP 开关 + fail-open 降级 rlimit、资源可配、仍不覆盖(IO/PID/网络)。

- [ ] **Step 2: Commit release note**

```bash
git add VERSION-STATUS-v0.18.0-alpha.md
git commit -m "docs: v0.18 子项目2 release note(BashTool cgroup 资源隔离)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

- [ ] **Step 3: push + 更新 memory**

```bash
git push origin main
```
更新 memory:`project_v018_isolation.md`(或新建 `project_v018_cgroup.md`)记子项目2 + MEMORY.md 加一条。

---

## Self-Review(against spec)

**1. Spec coverage:**
- spec §3.1 _cgroup_argv → **Task 2** ✓
- spec §3.2 scope_available → **Task 2** ✓
- spec §3.3 资源值(mem_mb/cpu_pct 默认+可配)→ **Task 1**(config)+ **Task 3**(argv 用)✓
- spec §3.4 cwd 处理(isolation on 不设 / off 设)→ **Task 3**(exec_cwd)✓
- spec §3.5 run 4 组合 → **Task 3** ✓
- spec §4 集成 + fail-open + warning → **Task 4** ✓
- spec §6 单测(scope/argv/4 组合/注入)→ Task 2-4 ✓;e2e → **Task 5** ✓
- spec §7 release note → **Task 6** ✓

**2. Placeholder scan:** 代码步骤均含完整代码。Task 1 Step 1 的 `_base_env()` / Task 5 部署 SOP / Task 6 release note 内容有"对齐现有/现场"提示(运行期事实,需现场确认,非 placeholder)。

**3. Type consistency:**
- `_cgroup_argv(mem_mb, cpu_pct)`(Task 2)与 Task 3 调用一致 ✓
- `scope_available()`(Task 2)与 app.py(Task 4)一致 ✓
- `BashTool(cgroup, cgroup_mem_mb, cgroup_cpu_pct)`(Task 3)与 chat_registry(Task 4)一致 ✓
- `bash_cgroup`/`bash_cgroup_mem_mb`/`bash_cgroup_cpu_pct`(config Task 1)与 app.py/registry/_TestSettings 引用一致 ✓
- run 4 组合的 inner/exec_cwd/argv 在 Task 3 内自洽 ✓

**风险点:** Task 1 `_base_env()` 需对齐 test_config.py 现有辅助;Task 5 e2e 的 dd bs=256M 默认 MemoryMax(1G)下不会被 kill(需 cgroup_mem_mb=64 配置触发),脚本已用 cgroup_mem_mb=64。

---

## Execution Handoff

Plan 已存 `docs/superpowers/plans/2026-06-04-bash-cgroup-resource.md`。沿用 **subagent-driven-development**:fresh subagent per task + 两阶段 review(spec → code quality)。Task 5/6 部署/收尾 controller 亲做。
