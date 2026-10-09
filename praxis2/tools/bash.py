"""Run shell commands within configured directory, permission, and timeout boundaries."""

from __future__ import annotations

import asyncio
import functools
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from praxis2.tools.base import Tool, ToolResult

_SECRET_ENV_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PEPPER", "PRAXIS_")


def _sanitized_env() -> dict[str, str]:

    return {k: v for k, v in os.environ.items() if not any(marker in k.upper() for marker in _SECRET_ENV_MARKERS)}


def _make_rlimit_preexec(cpu_s: int, mem_bytes: int):

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
                pass

    return _set


def _truncate(b: bytes, max_bytes: int) -> tuple[str, bool]:
    if len(b) <= max_bytes:
        return b.decode("utf-8", errors="replace"), False
    return (
        b[:max_bytes].decode("utf-8", errors="replace")
        + f"\n...[Truncated: original {len(b)}bytes exceed {max_bytes}]",
        True,
    )


def _kill_process_group(proc: asyncio.subprocess.Process) -> None:
    """Kill the spawned process group so ordinary shell children release pipes."""
    if os.name == "posix":
        try:
            # Every command is started in a new session below, so its PID is also
            # the process-group ID. Killing the group prevents a shell child from
            # keeping stdout/stderr open after the direct process is gone.
            os.killpg(proc.pid, signal.SIGKILL)
            return
        except ProcessLookupError:
            return
        except OSError:
            pass  # Unexpected group-kill failure: still kill the direct process.
    if proc.returncode is None:
        try:
            proc.kill()
        except (OSError, ProcessLookupError):
            pass


@functools.lru_cache(maxsize=1)
def userns_available() -> bool:

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

    return [
        "systemd-run",
        "--user",
        "--scope",
        "--quiet",
        "-p",
        f"MemoryMax={mem_mb}M",
        "-p",
        f"CPUQuota={cpu_pct}%",
        "--",
    ]


SETUP_TEMPLATE = (
    "set -e\nmkdir -p /tmp/.praxis-sbref\nmount --bind "
    '"$1" /tmp/.praxis-sbref\nmount -t tmpfs praxis-em'
    'pty "$2"\nmkdir -p "$1"\nmount --bind /tmp/.praxis'
    '-sbref "$1"\nprintf \'%s\\n\' "$4" | while IFS= read'
    ' -r p; do\n  [ -z "$p" ] && continue\n  if [ -d "$'
    'p" ]; then mount -t tmpfs praxis-empty "$p" 2>/d'
    'ev/null || true\n  elif [ -e "$p" ]; then mount -'
    '-bind /dev/null "$p" 2>/dev/null || true\n  fi\ndo'
    'ne\ncd "$5"\nexec bash -c "$3"\n'
)


_DEFAULT_MASK = (
    "~/praxis2.env",
    "~/.pgpass",
    "~/.netrc",
    "~/.ssh",
    "~/.aws",
    "~/.config/gcloud",
)


def _mask_paths(extra: str) -> str:

    extra = extra or ""
    paths = [os.path.expanduser(p) for p in _DEFAULT_MASK]
    paths += [p.strip() for p in extra.split(",") if p.strip()]
    return "\n".join(paths)


def _isolation_argv(
    *,
    command: str,
    sandbox: str,
    files_root: str,
    mask: str,
    cwd: str,
    netns: bool = False,
) -> list[str]:

    flags = ["unshare", "--user", "--map-root-user", "--mount"]
    if netns:
        flags.append("--net")
    return [
        *flags,
        "--",
        "/bin/sh",
        "-c",
        SETUP_TEMPLATE,
        "praxis-bash",  # $0
        sandbox,  # $1
        files_root,  # $2
        command,  # $3
        mask,  # $4
        cwd,  # $5
    ]


def _netns_argv(*, command: str) -> list[str]:

    return [
        "unshare",
        "--user",
        "--map-root-user",
        "--net",
        "--",
        "/bin/bash",
        "-c",
        command,
    ]


class BashTool(Tool):
    name = "Bash"
    rmcp_op = None

    description = (
        "Run a non-interactive shell command inside the configured sandbo"
        "x directory.Dangerous commands are denied; other commands may re"
        "quire approval. The default timeout is 30 seconds, up to 120."
    )

    def __init__(
        self,
        *,
        sandbox_root: Path,
        default_timeout_s: float = 30.0,
        max_timeout_s: float = 120.0,
        max_output_bytes: int = 65536,
        rlimit_cpu_s: int = 60,
        rlimit_mem_bytes: int = 1024**3,
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
                "command": {"type": "string", "description": "Non-interactive shell command to run once"},
                "cwd": {"type": "string", "description": "Optional working directory relative to the sandbox"},
                "timeout_s": {
                    "type": "number",
                    "description": ("Optional timeout in seconds, default 30 and maximum 120"),
                },
            },
            "required": ["command"],
        }

    async def run(self, payload: dict[str, Any]) -> ToolResult:
        command = str(payload.get("command", "")).strip()
        if not command:
            return ToolResult(ok=False, error="Missing required command")

        raw_timeout = payload.get("timeout_s")
        if raw_timeout is None or raw_timeout == "":
            timeout_s = self._default_timeout
        else:
            try:
                timeout_s = float(raw_timeout)
            except (TypeError, ValueError):
                return ToolResult(
                    ok=False,
                    error=f"Invalid timeout_s: {raw_timeout!r}; a number is required",
                    recovery_hint="Supply a valid timeout in seconds, for example 30 or 45.5, up to 120",
                )
        timeout_s = max(1.0, min(timeout_s, self._max_timeout))  # clamp

        self._root.mkdir(parents=True, exist_ok=True)
        root_resolved = self._root.resolve()
        rel_cwd = payload.get("cwd") or "."
        cwd_resolved = (self._root / rel_cwd).resolve()
        try:
            cwd_resolved.relative_to(root_resolved)
        except ValueError:
            return ToolResult(
                ok=False,
                error=f"cwd {rel_cwd!r}resolves outside sandbox {root_resolved}; access denied",
            )
        if not cwd_resolved.is_dir():
            cwd_resolved = root_resolved

        preexec = _make_rlimit_preexec(self._rlimit_cpu, self._rlimit_mem)
        t0 = time.monotonic()
        try:
            if not self._isolation and not self._cgroup and not self._netns:
                proc = await asyncio.create_subprocess_shell(
                    command,
                    cwd=str(cwd_resolved),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    preexec_fn=preexec,
                    env=_sanitized_env(),
                    start_new_session=(os.name == "posix"),
                )
            else:
                if self._isolation:
                    inner = _isolation_argv(
                        command=command,
                        sandbox=str(root_resolved),
                        files_root=str(root_resolved.parent),
                        mask=_mask_paths(self._isolation_mask),
                        cwd=str(cwd_resolved),
                        netns=self._netns,
                    )
                    kw = {}
                elif self._netns:
                    inner = _netns_argv(command=command)
                    kw = {"cwd": str(cwd_resolved)}
                else:
                    inner = ["/bin/bash", "-c", command]
                    kw = {"cwd": str(cwd_resolved)}

                if self._cgroup:
                    argv = (
                        _cgroup_argv(
                            mem_mb=self._cgroup_mem_mb,
                            cpu_pct=self._cgroup_cpu_pct,
                        )
                        + inner
                    )
                else:
                    argv = inner
                proc = await asyncio.create_subprocess_exec(
                    *argv,
                    **kw,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    preexec_fn=preexec,
                    env=_sanitized_env(),
                    start_new_session=(os.name == "posix"),
                )
        except Exception as e:  # noqa: BLE001
            return ToolResult(ok=False, error=f"Could not start command:{type(e).__name__}: {e}")

        async def _drain(stream) -> bytes:
            buf = bytearray()
            try:
                while len(buf) <= self._max_output:
                    chunk = await stream.read(65536)
                    if not chunk:
                        break
                    buf.extend(chunk)
                else:
                    _kill_process_group(proc)
                    # Discard any bytes already buffered by the pipe transport. This
                    # keeps the captured buffer bounded while ensuring wait() cannot
                    # be held open by a paused, unread subprocess pipe.
                    while await stream.read(65536):
                        pass
            except BaseException:
                # If one pipe read fails, release the sibling drain immediately;
                # gather(return_exceptions=True) can then report the original error.
                _kill_process_group(proc)
                raise
            return bytes(buf)

        out_task = asyncio.create_task(_drain(proc.stdout))
        err_task = asyncio.create_task(_drain(proc.stderr))
        wait_task = asyncio.create_task(proc.wait())
        try:
            results = await asyncio.wait_for(
                asyncio.gather(out_task, err_task, wait_task, return_exceptions=True),
                timeout=timeout_s,
            )
        except asyncio.CancelledError:
            out_task.cancel()
            err_task.cancel()
            wait_task.cancel()
            _kill_process_group(proc)
            try:
                await asyncio.shield(proc.wait())
            except (OSError, ProcessLookupError):
                pass
            raise
        except TimeoutError:
            out_task.cancel()
            err_task.cancel()
            wait_task.cancel()
            try:
                _kill_process_group(proc)
                await proc.wait()
            except (OSError, ProcessLookupError):
                pass
            return ToolResult(
                ok=False,
                error=f"Command timed out after {timeout_s}s and was terminated",
                recovery_hint="Use a shorter command or increase timeout_s, up to 120",
            )

        stdout_r, stderr_r, wait_r = results
        drain_exc = next((r for r in (stdout_r, stderr_r) if isinstance(r, BaseException)), None)
        if drain_exc is not None:
            try:
                _kill_process_group(proc)
                await proc.wait()
            except (OSError, ProcessLookupError):
                pass
            return ToolResult(
                ok=False,
                error=f"Could not read command output:{type(drain_exc).__name__}: {drain_exc}",
            )
        if isinstance(wait_r, BaseException):
            _kill_process_group(proc)
            return ToolResult(
                ok=False,
                error=f"Could not wait for the command to exit:{type(wait_r).__name__}: {wait_r}",
            )
        stdout_b, stderr_b = stdout_r, stderr_r

        duration_ms = int((time.monotonic() - t0) * 1000)
        stdout, t1 = _truncate(stdout_b, self._max_output)
        stderr, t2 = _truncate(stderr_b, self._max_output)
        return ToolResult(
            ok=True,
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
