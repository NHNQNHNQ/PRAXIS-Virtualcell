"""BashTool:在 user 软沙盒里跑非交互 shell 命令(v0.17 子项目 2)。

执行层:命令安全裁决由 BashCommandPolicy(permission 层)负责;本工具只管
"在沙盒里安全执行已放行的命令" —— cwd 限定 + 超时 + rlimit + 输出截断。

⚠ 软沙盒(spec §5):命令同 server uid 运行,cwd 只限默认目录,绝对路径可越界。
黑名单 + ASK + rlimit + 默认关缓解;真隔离留 v0.18。
"""
from __future__ import annotations

import asyncio
import functools
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from praxis2.tools.base import Tool, ToolResult

# 机密 env 变量名特征:子进程 env 滤掉这些,防 BashTool 命令读出上游 API key /
# DB 口令 / pepper(final review I-1)。PATH/HOME/LANG 等非机密保留。
_SECRET_ENV_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PEPPER", "PRAXIS_")


def _sanitized_env() -> dict[str, str]:
    """裁剪父进程 env,移除机密(防子进程泄漏)。保留 PATH/HOME 等运行必需。"""
    return {
        k: v for k, v in os.environ.items()
        if not any(marker in k.upper() for marker in _SECRET_ENV_MARKERS)
    }


def _make_rlimit_preexec(cpu_s: int, mem_bytes: int):
    """返回 preexec_fn(子进程内设 rlimit);非 posix / import 失败 → None 降级。"""
    try:
        import resource
    except ImportError:
        return None

    def _set() -> None:
        for res, limit in (
            (resource.RLIMIT_CPU, cpu_s),
            (resource.RLIMIT_AS, mem_bytes),
        ):
            try:
                resource.setrlimit(res, (limit, limit))
            except (ValueError, OSError):
                pass  # 单项 rlimit 设失败不影响命令执行(尽力而为)

    return _set


def _truncate(b: bytes, max_bytes: int) -> tuple[str, bool]:
    if len(b) <= max_bytes:
        return b.decode("utf-8", errors="replace"), False
    return (
        b[:max_bytes].decode("utf-8", errors="replace")
        + f"\n…[截断:原 {len(b)} bytes 超 {max_bytes}]",
        True,
    )


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


@functools.lru_cache(maxsize=1)
def scope_available() -> bool:
    """探测 systemd-run --user --scope 是否可用(cgroup fail-open 用)。
    跑一次 `systemd-run --user --scope --quiet -- true`,returncode==0 即可用。
    lru_cache:每进程只探一次。"""
    try:
        r = subprocess.run(
            ["systemd-run", "--user", "--scope", "--quiet", "--", "true"],
            capture_output=True,
            timeout=5,
        )
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


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


def _cgroup_argv(*, mem_mb: int, cpu_pct: int) -> list[str]:
    """systemd-run --user --scope 前缀:cgroup 限内存/CPU,覆盖整个进程树(含孙子)。
    拼在 inner 命令(unshare argv 或 ['/bin/bash','-c',command])之前。"""
    return [
        "systemd-run", "--user", "--scope", "--quiet",
        "-p", f"MemoryMax={mem_mb}M",
        "-p", f"CPUQuota={cpu_pct}%",
        "--",
    ]


# user+mount namespace 内的文件系统遮蔽脚本(固定常量,只用位置参数 $1..$5,
# 不含任何拼接的 user input → 命令注入防护)。
#   $1 sandbox_root  $2 files_root  $3 command  $4 mask(换行分隔)  $5 cwd
SETUP_TEMPLATE = r"""set -e
mkdir -p /tmp/.praxis-sbref
mount --bind "$1" /tmp/.praxis-sbref
mount -t tmpfs praxis-empty "$2"
mkdir -p "$1"
mount --bind /tmp/.praxis-sbref "$1"
# 敏感清单 best-effort 遮蔽($4 换行分隔):核心 files_root 遮蔽已由上方 set -e
# 保证 fail-closed;此处对额外敏感路径尽力遮(不存在则跳过),漏遮有 v0.17
# BashCommandPolicy 黑名单(praxis2.env/.ssh token)双保险。
printf '%s\n' "$4" | while IFS= read -r p; do
  [ -z "$p" ] && continue
  if [ -d "$p" ]; then mount -t tmpfs praxis-empty "$p" 2>/dev/null || true
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
    extra = extra or ""  # 防 None
    paths = [os.path.expanduser(p) for p in _DEFAULT_MASK]
    paths += [p.strip() for p in extra.split(",") if p.strip()]
    return "\n".join(paths)


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


class BashTool(Tool):
    """在 user 软沙盒跑 shell 命令。命令安全由 BashCommandPolicy 裁决。"""

    name = "Bash"
    rmcp_op = None  # 命令安全由 BashCommandPolicy 管,不靠相位门

    description = (
        "在你的沙盒目录里跑一条非交互 shell 命令(如 df -h 看磁盘、ls 看文件)。"
        "危险命令会被拒,非白名单命令需你确认。超时 30s(可调,上限 120s)。"
    )

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
        cgroup: bool = False,
        cgroup_mem_mb: int = 1024,
        cgroup_cpu_pct: int = 100,
        netns: bool = False,
    ) -> None:
        self._root = Path(sandbox_root)
        self._default_timeout = default_timeout_s
        self._max_timeout = max_timeout_s
        self._max_output = max_output_bytes
        self._rlimit_cpu = rlimit_cpu_s
        self._rlimit_mem = rlimit_mem_bytes
        self._isolation = isolation
        self._isolation_mask = isolation_mask
        self._cgroup = cgroup
        self._cgroup_mem_mb = cgroup_mem_mb
        self._cgroup_cpu_pct = cgroup_cpu_pct
        self._netns = netns

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要跑的 shell 命令(非交互、一次性)"},
                "cwd": {"type": "string", "description": "(可选)沙盒内相对工作目录"},
                "timeout_s": {"type": "number", "description": "(可选)超时秒,默认 30,上限 120"},
            },
            "required": ["command"],
        }

    async def run(self, payload: dict[str, Any]) -> ToolResult:
        command = str(payload.get("command", "")).strip()
        if not command:
            return ToolResult(ok=False, error="缺 command(必填)")

        raw_timeout = payload.get("timeout_s")
        if raw_timeout is None or raw_timeout == "":  # 仅缺省(未传/空串)→ 用默认
            timeout_s = self._default_timeout
        else:
            try:
                timeout_s = float(raw_timeout)
            except (TypeError, ValueError):
                return ToolResult(
                    ok=False,
                    error=f"timeout_s 非法(收到 {raw_timeout!r}),必须是数字",
                    recovery_hint="传有效秒数(如 30 或 45.5),上限 120",
                )
        timeout_s = max(1.0, min(timeout_s, self._max_timeout))  # clamp

        # cwd 沙盒校验:resolve 后必须在 sandbox_root 内
        self._root.mkdir(parents=True, exist_ok=True)
        root_resolved = self._root.resolve()
        rel_cwd = payload.get("cwd") or "."
        cwd_resolved = (self._root / rel_cwd).resolve()
        try:
            cwd_resolved.relative_to(root_resolved)
        except ValueError:
            return ToolResult(
                ok=False,
                error=f"cwd {rel_cwd!r} resolve 后在沙盒 {root_resolved} 外(越权拒绝,escape)",
            )
        if not cwd_resolved.is_dir():
            cwd_resolved = root_resolved  # 子目录不存在 → 退回根

        preexec = _make_rlimit_preexec(self._rlimit_cpu, self._rlimit_mem)
        t0 = time.monotonic()
        try:
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
        except Exception as e:  # noqa: BLE001 — spawn 失败(如 preexec 异常)不冒泡
            return ToolResult(ok=False, error=f"命令 spawn 失败:{type(e).__name__}: {e}")

        # 流式 drain:每个 stream 读到 max_output_bytes 即停(buffer 有界,防父进程 OOM);
        # 读够就 kill 进程,让另一 stream EOF(防进程阻塞写 → 另一 drain 卡读误判超时)。
        async def _drain(stream) -> bytes:
            buf = bytearray()
            while len(buf) <= self._max_output:
                chunk = await stream.read(65536)
                if not chunk:
                    break  # EOF:命令自然结束
                buf.extend(chunk)
            else:
                # while 条件转假(读够 max_output)→ 输出超限,kill 防继续写阻塞
                if proc.returncode is None:
                    try:
                        proc.kill()
                    except (OSError, ProcessLookupError):
                        pass
            return bytes(buf)

        out_task = asyncio.create_task(_drain(proc.stdout))
        err_task = asyncio.create_task(_drain(proc.stderr))
        try:
            results = await asyncio.wait_for(
                asyncio.gather(out_task, err_task, return_exceptions=True),
                timeout=timeout_s,
            )
        except TimeoutError:
            out_task.cancel()
            err_task.cancel()
            try:
                proc.kill()
                await proc.wait()
            except (OSError, ProcessLookupError):
                pass
            return ToolResult(
                ok=False,
                error=f"命令超时(>{timeout_s}s),已 kill",
                recovery_hint="缩短命令耗时或调大 timeout_s(上限 120)",
            )

        # return_exceptions=True:drain 内部异常变返回值(非超时,如管道损坏)。
        # 任一异常 → kill + wait 兜底 + 返回 ok=False(不裸冒泡致 chat-stream 500)。
        stdout_r, stderr_r = results
        drain_exc = next(
            (r for r in results if isinstance(r, BaseException)), None
        )
        if drain_exc is not None:
            if proc.returncode is None:
                try:
                    proc.kill()
                    await proc.wait()
                except (OSError, ProcessLookupError):
                    pass
            return ToolResult(
                ok=False,
                error=f"读取命令输出失败:{type(drain_exc).__name__}: {drain_exc}",
            )
        stdout_b, stderr_b = stdout_r, stderr_r

        # 进程回收(读够已 kill / 或自然结束;wait 收 returncode 防僵尸)
        try:
            await proc.wait()
        except (OSError, ProcessLookupError):
            pass

        duration_ms = int((time.monotonic() - t0) * 1000)
        stdout, t1 = _truncate(stdout_b, self._max_output)
        stderr, t2 = _truncate(stderr_b, self._max_output)
        return ToolResult(
            ok=True,  # 命令跑完即 ok;exit_code 非零由模型自判
            value={
                "command": command,
                "cwd": str(cwd_resolved),
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": proc.returncode,
                "duration_ms": duration_ms,
                "truncated": t1 or t2,
            },
        )
