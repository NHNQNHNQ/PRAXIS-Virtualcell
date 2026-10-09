# BashTool 文件系统真隔离(unshare userns)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 BashTool 加 opt-in 的文件系统真隔离——命令在 user+mount namespace 内运行,绝对路径读不到其它用户的 `files_root` 子目录与敏感配置(praxis2.env/.ssh)。

**Architecture:** 隔离开关 `PRAXIS_BASH_ISOLATION` 启用时,`BashTool.run` 把命令从 `create_subprocess_shell(command)` 改为 `create_subprocess_exec("unshare", ..., command, ...)`,在 namespace 内用 bind mount 遮蔽其它用户目录 + 敏感文件。命令注入靠 argv 位置参数防护($1 sandbox / $2 files_root / $3 command / $4 mask / $5 cwd)。userns 不可用时 fail-closed(不注册 BashTool)。其余 v0.17 防护(黑白灰 policy / cwd 校验 / rlimit / env 裁剪 / 超时 / drain)全部保留。

**Tech Stack:** Python asyncio/subprocess + util-linux `unshare` + pytest。无新 pip 依赖。

**Spec:** `docs/superpowers/specs/2026-06-03-bash-isolation-userns-design.md`

---

## 起点与约束

- 起点:`main` HEAD `3836dd0`(spec commit)= v0.17.0 GA + v0.18 spec。
- staging 已验:`unprivileged_userns_clone=1`、`unshare --user --map-root-user --mount` 内 bind mount 生效。
- 雷区:工作区有无关 microbiome brains 改动,**每次 commit 只 add 目标文件,绝不 `git add .`**。
- commit message 简体中文,末尾 `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>`。

## File Structure(本子项目要碰的文件)

| 文件 | 动作 | 职责 |
|---|---|---|
| `praxis2/config.py` | 改 3 处(字段/KNOWN_KEYS/load) | `bash_isolation` + `bash_isolation_mask` 配置 |
| `praxis2/tools/bash.py` | 加模块级 helper + BashTool 改造 | `userns_available()` / `SETUP_TEMPLATE` / `_isolation_argv()` / `_mask_paths()` / run 二分 |
| `praxis2/server/chat_registry.py` | 改签名 + 注册 | `bash_isolation` 参数透传 BashTool |
| `praxis2/server/app.py` | 改 chat-stream 段 | 算 isolation + fail-closed 不注册 + 启动 warning |
| `tests/test_tools_bash_isolation.py` | 新建 | 隔离逻辑全覆盖 |
| `tests/test_config.py` | 追加 | bash_isolation 配置加载 |
| `VERSION-STATUS-v0.18.0.md`(或并入观察) | 后续 | release note |

---

## Task 1: config 加 bash_isolation + bash_isolation_mask

**Files:**
- Modify: `praxis2/config.py`(字段 117 后 / _KNOWN_KEYS 219 后 / load_from_env 319 后)
- Test: `tests/test_config.py`(追加)

- [ ] **Step 1: 写失败测试**

在 `tests/test_config.py` 末尾追加:

```python
def test_bash_isolation_defaults_false():
    from praxis2.config import load_from_env
    s = load_from_env({})
    assert s.bash_isolation is False
    assert s.bash_isolation_mask == ""


def test_bash_isolation_from_env():
    from praxis2.config import load_from_env
    s = load_from_env({
        "PRAXIS_BASH_ISOLATION": "true",
        "PRAXIS_BASH_ISOLATION_MASK": "/home/zkyd/secret,/etc/foo",
    })
    assert s.bash_isolation is True
    assert s.bash_isolation_mask == "/home/zkyd/secret,/etc/foo"
```

- [ ] **Step 2: 跑测试确认红**

Run: `.venv/bin/python -m pytest tests/test_config.py -k bash_isolation -v`
Expected: FAIL(`Settings` 无 `bash_isolation` 属性 / load_from_env 不认这俩 key)。

- [ ] **Step 3: 加 Settings 字段**

`praxis2/config.py` 第 117 行 `bash_tool_enabled: bool = False` 之后追加:

```python
    bash_isolation: bool = False  # v0.18:文件系统真隔离(unshare userns),叠加在软沙盒上
    bash_isolation_mask: str = ""  # 额外遮蔽的绝对路径(逗号分隔),追加到默认敏感清单
```

- [ ] **Step 4: 加 _KNOWN_KEYS**

`praxis2/config.py` 第 219 行 `"PRAXIS_BASH_TOOL_ENABLED",` 之后追加:

```python
    "PRAXIS_BASH_ISOLATION",
    "PRAXIS_BASH_ISOLATION_MASK",
```

- [ ] **Step 5: 加 load_from_env**

`praxis2/config.py` 第 319 行 `bash_tool_enabled=_get_bool(e, "PRAXIS_BASH_TOOL_ENABLED", False),` 之后追加:

```python
        bash_isolation=_get_bool(e, "PRAXIS_BASH_ISOLATION", False),
        bash_isolation_mask=e.get("PRAXIS_BASH_ISOLATION_MASK", ""),
```

- [ ] **Step 6: 跑测试确认绿**

Run: `.venv/bin/python -m pytest tests/test_config.py -v`
Expected: 全 PASS(新 2 + 原有不回归)。

- [ ] **Step 7: Commit**

```bash
git add praxis2/config.py tests/test_config.py
git commit -m "feat(config): 加 bash_isolation + bash_isolation_mask 配置

v0.18 子项目1:PRAXIS_BASH_ISOLATION(默认 false)开关文件系统真隔离,
PRAXIS_BASH_ISOLATION_MASK 追加遮蔽路径。沿用 bash_tool_enabled 模式。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: bash.py userns_available() 启动探测

**Files:**
- Modify: `praxis2/tools/bash.py`(模块级,helper 区 ~50 行后)
- Test: `tests/test_tools_bash_isolation.py`(新建)

- [ ] **Step 1: 写失败测试(新建 tests/test_tools_bash_isolation.py)**

```python
"""BashTool 文件系统真隔离(unshare userns)单测(v0.18 子项目1)。"""
from pathlib import Path

import pytest

from praxis2.tools import bash as bashmod


def test_userns_available_true_when_unshare_succeeds(monkeypatch):
    """unshare 探测 returncode=0 → 可用。"""
    class _R:
        returncode = 0

    monkeypatch.setattr(bashmod.subprocess, "run", lambda *a, **k: _R())
    bashmod.userns_available.cache_clear()
    assert bashmod.userns_available() is True


def test_userns_available_false_when_unshare_fails(monkeypatch):
    """unshare 探测非 0 / 抛异常 → 不可用。"""
    def _boom(*a, **k):
        raise OSError("no unshare")

    monkeypatch.setattr(bashmod.subprocess, "run", _boom)
    bashmod.userns_available.cache_clear()
    assert bashmod.userns_available() is False
```

- [ ] **Step 2: 跑测试确认红**

Run: `.venv/bin/python -m pytest tests/test_tools_bash_isolation.py -v`
Expected: FAIL(`bash` 模块无 `subprocess` 导入 / 无 `userns_available`)。

- [ ] **Step 3: 实现 userns_available()**

`praxis2/tools/bash.py` 顶部 import 区(第 13 行 `import time` 之后)加:

```python
import functools
import subprocess
```

在 `_truncate` 函数之后(第 60 行后)、`class BashTool` 之前加:

```python
@functools.lru_cache(maxsize=1)
def userns_available() -> bool:
    """探测 unprivileged user+mount namespace 是否可用(fail-closed 用)。
    跑一次 `unshare --user --map-root-user --mount -- true`,returncode==0 即可用。
    lru_cache:每进程只探一次。"""
    try:
        r = subprocess.run(
            ["unshare", "--user", "--map-root-user", "--mount", "--", "true"],
            capture_output=True,
            timeout=5,
        )
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
```

- [ ] **Step 4: 跑测试确认绿**

Run: `.venv/bin/python -m pytest tests/test_tools_bash_isolation.py -v`
Expected: 2 passed。

- [ ] **Step 5: Commit**

```bash
git add praxis2/tools/bash.py tests/test_tools_bash_isolation.py
git commit -m "feat(bash): 加 userns_available() 启动探测(fail-closed 基础)

跑一次 unshare --user --map-root-user --mount true 探测 userns 可用性,
lru_cache 每进程一次。用于 isolation 的 fail-closed 决策。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: bash.py SETUP_TEMPLATE + _mask_paths + _isolation_argv

**Files:**
- Modify: `praxis2/tools/bash.py`(模块级常量 + helper)
- Test: `tests/test_tools_bash_isolation.py`(追加)

- [ ] **Step 1: 写失败测试**

在 `tests/test_tools_bash_isolation.py` 末尾追加:

```python
def test_mask_paths_default_expands_home(monkeypatch):
    monkeypatch.setenv("HOME", "/home/tester")
    paths = bashmod._mask_paths("")
    assert "/home/tester/praxis2.env" in paths
    assert "/home/tester/.ssh" in paths


def test_mask_paths_appends_extra():
    paths = bashmod._mask_paths("/data/x,/data/y")
    assert "/data/x" in paths
    assert "/data/y" in paths


def test_isolation_argv_structure():
    argv = bashmod._isolation_argv(
        command="echo hi",
        sandbox="/fr/u1",
        files_root="/fr",
        mask="/home/t/.ssh\n/home/t/praxis2.env",
        cwd="/fr/u1/sub",
    )
    assert argv[:5] == ["unshare", "--user", "--map-root-user", "--mount", "--"]
    assert argv[5:8] == ["/bin/sh", "-c", bashmod.SETUP_TEMPLATE]
    # 位置参数:$0 名 + $1 sandbox / $2 files_root / $3 command / $4 mask / $5 cwd
    assert argv[8] == "praxis-bash"
    assert argv[9] == "/fr/u1"
    assert argv[10] == "/fr"
    assert argv[11] == "echo hi"
    assert argv[12] == "/home/t/.ssh\n/home/t/praxis2.env"
    assert argv[13] == "/fr/u1/sub"


def test_isolation_argv_command_injection_safe():
    """恶意 command 只是 $3 的值,不破坏 SETUP 脚本结构。"""
    evil = 'x"; rm -rf /; "'
    argv = bashmod._isolation_argv(
        command=evil, sandbox="/fr/u1", files_root="/fr", mask="", cwd="/fr/u1",
    )
    assert argv[11] == evil  # 原样作为位置参数,SETUP_TEMPLATE 不含它
    assert evil not in bashmod.SETUP_TEMPLATE
```

- [ ] **Step 2: 跑测试确认红**

Run: `.venv/bin/python -m pytest tests/test_tools_bash_isolation.py -k "mask_paths or isolation_argv" -v`
Expected: FAIL(无 `_mask_paths` / `_isolation_argv` / `SETUP_TEMPLATE`)。

- [ ] **Step 3: 实现 SETUP_TEMPLATE + helper**

`praxis2/tools/bash.py` 在 `userns_available()` 之后追加:

```python
# user+mount namespace 内的文件系统遮蔽脚本(固定常量,只用位置参数 $1..$5,
# 不含任何拼接的 user input → 命令注入防护)。
#   $1 sandbox_root  $2 files_root  $3 command  $4 mask(换行分隔)  $5 cwd
SETUP_TEMPLATE = r"""set -e
mkdir -p /tmp/.praxis-empty /tmp/.praxis-sbref
mount --bind "$1" /tmp/.praxis-sbref
mount --bind /tmp/.praxis-empty "$2"
mkdir -p "$1"
mount --bind /tmp/.praxis-sbref "$1"
printf '%s\n' "$4" | while IFS= read -r p; do
  [ -z "$p" ] && continue
  if [ -d "$p" ]; then mount --bind /tmp/.praxis-empty "$p" 2>/dev/null || true
  elif [ -e "$p" ]; then mount --bind /dev/null "$p" 2>/dev/null || true
  fi
done
cd "$5"
exec bash -c "$3"
"""

# 默认遮蔽的敏感路径(~ 展开;file→bind /dev/null,dir→bind empty)。
_DEFAULT_MASK = (
    "~/praxis2.env", "~/.pgpass", "~/.netrc",
    "~/.ssh", "~/.aws", "~/.config/gcloud",
)


def _mask_paths(extra: str) -> str:
    """算遮蔽清单(换行分隔的绝对路径)。默认敏感项 + extra(逗号分隔)。"""
    paths = [os.path.expanduser(p) for p in _DEFAULT_MASK]
    paths += [p.strip() for p in extra.split(",") if p.strip()]
    return "\n".join(paths)


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

- [ ] **Step 4: 跑测试确认绿**

Run: `.venv/bin/python -m pytest tests/test_tools_bash_isolation.py -v`
Expected: 全 PASS(含注入防护)。

- [ ] **Step 5: Commit**

```bash
git add praxis2/tools/bash.py tests/test_tools_bash_isolation.py
git commit -m "feat(bash): SETUP_TEMPLATE + _isolation_argv + _mask_paths

unshare 隔离的固定遮蔽脚本(bind empty 遮 files_root → bind this_user
回来 + 遮敏感)+ argv 构造(user command 走位置参数 \$3 防注入)+
遮蔽清单计算(默认敏感 expanduser + mask 追加)。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: BashTool isolation 参数 + run() 二分

**Files:**
- Modify: `praxis2/tools/bash.py`(__init__ 74-89 / run subprocess 138-146)
- Test: `tests/test_tools_bash_isolation.py`(追加)

- [ ] **Step 1: 写失败测试**

在 `tests/test_tools_bash_isolation.py` 末尾追加:

```python
import asyncio


def _run(tool, payload):
    return asyncio.run(tool.run(payload))


def test_isolation_off_uses_shell(tmp_path, monkeypatch):
    """isolation off(默认)→ create_subprocess_shell,零回归。"""
    captured = {}

    async def fake_shell(cmd, **kw):
        captured["mode"] = "shell"
        captured["cmd"] = cmd
        raise RuntimeError("stop-after-capture")

    monkeypatch.setattr(bashmod.asyncio, "create_subprocess_shell", fake_shell)
    t = bashmod.BashTool(sandbox_root=tmp_path)
    r = _run(t, {"command": "echo hi"})
    assert captured["mode"] == "shell"
    assert captured["cmd"] == "echo hi"
    assert r.ok is False  # spawn 失败兜底(stop-after-capture)


def test_isolation_on_uses_exec_unshare(tmp_path, monkeypatch):
    """isolation on → create_subprocess_exec("unshare", ...)。"""
    captured = {}

    async def fake_exec(*argv, **kw):
        captured["argv"] = list(argv)
        raise RuntimeError("stop-after-capture")

    monkeypatch.setattr(bashmod.asyncio, "create_subprocess_exec", fake_exec)
    t = bashmod.BashTool(sandbox_root=tmp_path, isolation=True)
    r = _run(t, {"command": "echo hi"})
    assert captured["argv"][0] == "unshare"
    assert "--map-root-user" in captured["argv"]
    assert captured["argv"][-3] == "echo hi"  # $3 command(后接 $4 mask, $5 cwd)
    assert r.ok is False
```

- [ ] **Step 2: 跑测试确认红**

Run: `.venv/bin/python -m pytest tests/test_tools_bash_isolation.py -k "isolation_off or isolation_on" -v`
Expected: FAIL(BashTool 无 `isolation` 参数 / run 不分支)。

- [ ] **Step 3: __init__ 加 isolation 参数**

`praxis2/tools/bash.py` `BashTool.__init__`(第 74-89 行)签名加参数 + 存字段。把:

```python
    def __init__(
        self,
        *,
        sandbox_root: Path,
        default_timeout_s: float = 30.0,
        max_timeout_s: float = 120.0,
        max_output_bytes: int = 65536,
        rlimit_cpu_s: int = 60,
        rlimit_mem_bytes: int = 1024 ** 3,
    ) -> None:
        self._root = Path(sandbox_root)
        self._default_timeout = default_timeout_s
        self._max_timeout = max_timeout_s
        self._max_output = max_output_bytes
        self._rlimit_cpu = rlimit_cpu_s
        self._rlimit_mem = rlimit_mem_bytes
```

替换为:

```python
    def __init__(
        self,
        *,
        sandbox_root: Path,
        default_timeout_s: float = 30.0,
        max_timeout_s: float = 120.0,
        max_output_bytes: int = 65536,
        rlimit_cpu_s: int = 60,
        rlimit_mem_bytes: int = 1024 ** 3,
        isolation: bool = False,
        isolation_mask: str = "",
    ) -> None:
        self._root = Path(sandbox_root)
        self._default_timeout = default_timeout_s
        self._max_timeout = max_timeout_s
        self._max_output = max_output_bytes
        self._rlimit_cpu = rlimit_cpu_s
        self._rlimit_mem = rlimit_mem_bytes
        self._isolation = isolation
        self._isolation_mask = isolation_mask
```

- [ ] **Step 4: run() 二分 subprocess 创建**

`praxis2/tools/bash.py` 第 138-146 行(`try: proc = await asyncio.create_subprocess_shell(...)`)替换为:

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

注:isolation 分支不设 `cwd=`(工作目录由 SETUP 脚本 `cd "$5"` 在 namespace 内切换;宿主 cwd 无意义且 bind 重挂后路径 inode 会变)。

- [ ] **Step 5: 跑测试确认绿 + bash 不回归**

Run: `.venv/bin/python -m pytest tests/test_tools_bash_isolation.py tests/test_tools_bash.py -v`
Expected: 全 PASS(isolation 新测试 + 原 bash 软沙盒测试零回归)。

- [ ] **Step 6: Commit**

```bash
git add praxis2/tools/bash.py tests/test_tools_bash_isolation.py
git commit -m "feat(bash): BashTool isolation 参数 + run() 执行二分

isolation on → create_subprocess_exec(unshare argv,namespace 内 bind
遮蔽);off → create_subprocess_shell(v0.17 软沙盒,零回归)。其余
超时/drain/rlimit/env 裁剪/截断全部共享不变。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: chat_registry + app.py 集成(fail-closed)

**Files:**
- Modify: `praxis2/server/chat_registry.py`(签名 22-27 / 注册 73-78)
- Modify: `praxis2/server/app.py`(chat-stream 段 659-668)
- Test: `tests/test_chat_registry.py`(追加;若无则新建)

- [ ] **Step 1: 写失败测试**

在 `tests/test_chat_registry.py`(无则新建,顶部 `from praxis2.server.chat_registry import build_chat_registry`)末尾追加:

```python
def test_bash_isolation_passed_to_tool(tmp_path):
    reg = build_chat_registry(bash_sandbox_root=str(tmp_path), bash_isolation=True)
    tool = reg.get("Bash")
    assert tool is not None
    assert tool._isolation is True


def test_bash_no_isolation_default(tmp_path):
    reg = build_chat_registry(bash_sandbox_root=str(tmp_path))
    tool = reg.get("Bash")
    assert tool._isolation is False
```

(注:`reg.get("Bash")` 取已注册工具——若 ToolRegistry 取实例的方法名不同,用实际方法;可先 `grep -n "def get\|def " praxis2/tools/registry.py` 确认。)

- [ ] **Step 2: 跑测试确认红**

Run: `.venv/bin/python -m pytest tests/test_chat_registry.py -k bash_isolation -v`
Expected: FAIL(build_chat_registry 无 `bash_isolation` 参数)。

- [ ] **Step 3: chat_registry 加参数 + 透传**

`praxis2/server/chat_registry.py` 签名(第 22-27 行)把:

```python
def build_chat_registry(
    *,
    selection: AgentSelection | None = None,
    mcp_tools: "list | None" = None,
    bash_sandbox_root: "str | None" = None,
) -> ToolRegistry:
```

替换为:

```python
def build_chat_registry(
    *,
    selection: AgentSelection | None = None,
    mcp_tools: "list | None" = None,
    bash_sandbox_root: "str | None" = None,
    bash_isolation: bool = False,
    bash_isolation_mask: str = "",
) -> ToolRegistry:
```

注册处(第 74-78 行)把:

```python
    if bash_sandbox_root:
        from pathlib import Path

        from praxis2.tools.bash import BashTool
        reg.register(BashTool(sandbox_root=Path(bash_sandbox_root)))
    return reg
```

替换为:

```python
    if bash_sandbox_root:
        from pathlib import Path

        from praxis2.tools.bash import BashTool
        reg.register(BashTool(
            sandbox_root=Path(bash_sandbox_root),
            isolation=bash_isolation,
            isolation_mask=bash_isolation_mask,
        ))
    return reg
```

- [ ] **Step 4: app.py 集成 + fail-closed**

`praxis2/server/app.py` 第 659-668 行(bash_root 计算 + build_chat_registry 调用)把:

```python
                bash_root = (
                    os.path.join(self._deps.settings.files_root, user_id)
                    if getattr(self._deps.settings, "bash_tool_enabled", False)
                    else None
                )
                reg = build_chat_registry(
                    selection=selection,
                    mcp_tools=self._mcp_pool.all_tools(),
                    bash_sandbox_root=bash_root,
                )
```

替换为:

```python
                bash_root = None
                bash_isolation = False
                if getattr(self._deps.settings, "bash_tool_enabled", False):
                    if self._deps.settings.bash_isolation:
                        # fail-closed:启用隔离但 userns 不可用 → 不注册 Bash
                        if userns_available():
                            bash_root = os.path.join(self._deps.settings.files_root, user_id)
                            bash_isolation = True
                        # else: bash_root 保持 None(Bash 不注册);启动已 warning
                    else:
                        bash_root = os.path.join(self._deps.settings.files_root, user_id)
                reg = build_chat_registry(
                    selection=selection,
                    mcp_tools=self._mcp_pool.all_tools(),
                    bash_sandbox_root=bash_root,
                    bash_isolation=bash_isolation,
                    bash_isolation_mask=self._deps.settings.bash_isolation_mask,
                )
```

并在 `app.py` 顶部 import 区加(找现有 `from praxis2.tools...` 处附近):

```python
from praxis2.tools.bash import userns_available
```

- [ ] **Step 5: app 启动 warning(fail-closed 可观测)**

在 `app.py` 的 `make_app`(或 deps 构造)处,settings 就绪后加一次性检查。先 `grep -n "def make_app\|settings =\|logging\|logger" praxis2/server/app.py` 定位 app 构造点与现有 logger,然后在 app 构造时插入:

```python
        if settings.bash_tool_enabled and settings.bash_isolation and not userns_available():
            logging.warning(
                "PRAXIS_BASH_ISOLATION=true 但 userns 不可用(unshare 探测失败),"
                "fail-closed:BashTool 将不注册。需启用 unprivileged userns 或关闭隔离。"
            )
```

(若 app.py 已有 module logger 如 `logger = logging.getLogger(...)`,用 `logger.warning`;若用 `logging` 模块直接调,确保 `import logging` 在顶部。)

- [ ] **Step 6: 跑测试确认绿 + server 相关不回归**

Run: `.venv/bin/python -m pytest tests/test_chat_registry.py tests/ -k "chat_registry or bash or server or app" --tb=short -q`
Expected: 全 PASS。

- [ ] **Step 7: Commit**

```bash
git add praxis2/server/chat_registry.py praxis2/server/app.py tests/test_chat_registry.py
git commit -m "feat(server): chat_registry + app.py 接入 bash_isolation(fail-closed)

build_chat_registry 加 bash_isolation/bash_isolation_mask 透传 BashTool。
app.py:启用隔离时探 userns,可用才注册带隔离的 Bash;不可用 fail-closed
不注册 + 启动 warning。非隔离走 v0.17 软沙盒(零回归)。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 6: 全量回归 + 部署 staging + e2e

> 运行验证 task(controller 亲做)。按 v0.17 部署 SOP。

**Files:** 无(部署 + 验证)

- [ ] **Step 1: 本地全量回归**

Run: `.venv/bin/python -m pytest tests/ --ignore=tests/integration -q --tb=no --junit-xml=/tmp/v018.xml >/dev/null 2>&1; echo "EXIT=$?"; .venv/bin/python -c "import xml.etree.ElementTree as ET; a=ET.parse('/tmp/v018.xml').getroot().attrib; print(a)"`
Expected: failures=0 errors=0(汇总行可能被 sandbox 吞,用 junit 取数)。**不绿不部署**。

- [ ] **Step 2: rsync backend 改动文件到 .53**

改动:`praxis2/config.py`、`praxis2/tools/bash.py`、`praxis2/server/chat_registry.py`、`praxis2/server/app.py`。逐文件 rsync(勿用 `--no-relative`):

```bash
cd /Volumes/T7/clade-learn/PRAXIS-2
rsync -aq praxis2/config.py             zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/praxis2/
rsync -aq praxis2/tools/bash.py         zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/praxis2/tools/
rsync -aq praxis2/server/chat_registry.py zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/praxis2/server/
rsync -aq praxis2/server/app.py         zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/praxis2/server/
```

- [ ] **Step 3: 加 staging env + 重启 gunicorn**

```bash
ssh zkyd@10.102.106.53 'grep -q PRAXIS_BASH_ISOLATION ~/praxis2.env || echo "export PRAXIS_BASH_ISOLATION=true" >> ~/praxis2.env'
# 找 master pid → kill → 重启(同 v0.17 SOP)
ssh zkyd@10.102.106.53 "PID=\$(ps -ef|grep '[g]unicorn'|grep python3|awk '\$3!=1{print \$2}'|sort -n|head -1); kill \$PID; sleep 3; cd ~/data1/mzy/PRAXIS-2 && source ~/praxis2.env && (nohup ~/software/miniconda3/envs/praxis2/bin/gunicorn -c deploy/gunicorn.conf.py praxis2.server.app:make_app_default > /tmp/praxis2-v018.log 2>&1 &); sleep 6; curl -s http://127.0.0.1:8001/api/info | head -c 120"
```
Expected: `/api/info` 返回(version 仍 v0.17.0,本子项目不 bump,留 v0.18 GA 时统一)。

- [ ] **Step 4: e2e — 跨用户读被挡**

预置其它用户的探针文件,再让模型用 Bash 读它:

```bash
# 预置 other 用户的敏感探针
ssh zkyd@10.102.106.53 'mkdir -p /home/zkyd/data1/praxis2-files/other-uid-probe && echo CROSS_USER_SECRET > /home/zkyd/data1/praxis2-files/other-uid-probe/secret.txt'
# 登录 + 让 AI 跑 cat 绝对路径(eval 或 curl chat-stream)
# message: "用 Bash 工具跑 cat /home/zkyd/data1/praxis2-files/other-uid-probe/secret.txt"
```
用 curl chat-stream(同 v0.17 e2e)发上述 message,看 SSE 的 tool_end:
Expected: 命令执行但**读不到**(stdout 为空 / "No such file or directory");`CROSS_USER_SECRET` **不出现**在输出。

- [ ] **Step 5: e2e — 敏感配置被挡 + sandbox 内正常 + df-h 正常**

curl chat-stream 三条 message,看 tool_end:
- `用 Bash 跑 cat ~/praxis2.env` → 读不到/空(注:此命令 BashCommandPolicy 黑名单已挡 `praxis2.env` token → DENY;改测 `cat /home/zkyd/praxis2.env` 验物理遮蔽,黑名单也挡 → 用一个不在黑名单的敏感路径如 `cat /home/zkyd/.netrc` 验遮蔽生效)
- `用 Bash 跑 'echo hello > test.txt && cat test.txt'` → sandbox 内读写正常(输出 hello)
- `用 Bash 跑 df -h` → 正常返回磁盘信息(系统目录在)

Expected: 敏感读不到、sandbox 内正常、df-h 正常。

- [ ] **Step 6: 记录 e2e 结果到验证笔记**

把 Step 4-5 的 SSE 关键帧(tool_end content)记录,确认隔离行为符合预期。若跨用户读**能**读到 → 隔离失效,走 systematic-debugging(不继续)。

---

## Task 7: release note + memory

**Files:**
- Modify: `docs/superpowers/specs/2026-06-03-bash-isolation-userns-design.md`(无需改,spec 已含安全分析)
- Create/Modify: release note 段(并入 v0.18 进展)
- Modify: memory

- [ ] **Step 1: 写 v0.18 进展 release note**

新建 `VERSION-STATUS-v0.18.0-alpha.md`(或按仓库惯例),含:子项目1 文件系统真隔离(unshare userns)落地、隔离覆盖(跨用户读/敏感/cd 出沙盒)、仍不覆盖(资源 cgroup 留后续/网络/userns map-root 风险)、开关 PRAXIS_BASH_ISOLATION + fail-closed、回滚。格式参考 `VERSION-STATUS-v0.17.0.md`。

- [ ] **Step 2: Commit release note**

```bash
git add VERSION-STATUS-v0.18.0-alpha.md
git commit -m "docs: v0.18 子项目1 release note(BashTool 文件系统真隔离)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

- [ ] **Step 3: push + 更新 memory**

```bash
git push origin main
```
更新 `~/.claude/projects/-Volumes-T7-clade-learn/memory/`:新建 `project_v018_isolation.md`(子项目1 落地细节)+ MEMORY.md 加一条"v0.18 子项目1 ship"。

---

## Self-Review(against spec)

**1. Spec coverage:**
- spec §3.1 unshare argv + 注入防护 → **Task 3**(_isolation_argv + 注入测试)✓
- spec §3.1/3.3 SETUP bind 遮蔽 → **Task 3**(SETUP_TEMPLATE)✓
- spec §3.2 mask 清单 Python 侧算 → **Task 3**(_mask_paths)✓
- spec §4 config + 开关 → **Task 1**;启动探测 → **Task 2**(userns_available)✓
- spec §4 集成 + fail-closed → **Task 5**(chat_registry + app.py)✓
- spec §2 run 二分 → **Task 4** ✓
- spec §6 单测(off 零回归/on argv/注入/fail-closed/探测)→ Task 2-5 ✓;e2e → **Task 6** ✓
- spec §7 DoD release note → **Task 7** ✓

**2. Placeholder scan:** 代码步骤均含完整代码。Task 5 Step 1/5 有"先 grep 确认方法名/logger"的现场核对提示(registry.get 取实例方法名、app.py logger 形式属运行期事实,需现场确认而非臆造)——非 placeholder。

**3. Type consistency:**
- `_isolation_argv(command, sandbox, files_root, mask, cwd)` 签名(Task 3)与 Task 4 调用一致 ✓
- `BashTool(isolation=, isolation_mask=)`(Task 4)与 chat_registry 调用(Task 5)一致 ✓
- `userns_available()`(Task 2)与 app.py 调用(Task 5)一致 ✓
- `bash_isolation`/`bash_isolation_mask`(config Task 1)与 app.py/registry 引用一致 ✓
- SETUP 位置参数 $1-$5 顺序在 SETUP_TEMPLATE(Task 3)与 _isolation_argv(Task 3)与测试断言(Task 3/4)一致 ✓

**风险点:** Task 5 `reg.get("Bash")` 取已注册实例的方法名需确认(ToolRegistry API);Task 6 e2e 敏感读测试要避开 BashCommandPolicy 黑名单已挡的 token(用 `.netrc` 等非黑名单敏感路径验物理遮蔽)。

---

## Execution Handoff

Plan 已存 `docs/superpowers/plans/2026-06-03-bash-isolation-userns.md`。沿用既定工作流 → **subagent-driven-development**:fresh subagent per task + 两阶段 review(spec → code quality)。Task 6/7 含部署/收尾,controller 亲做。
