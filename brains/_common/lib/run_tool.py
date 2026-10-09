"""Run a tool binary and return structured success, error, timeout, or dry-run results."""

from __future__ import annotations

import os
import shlex
import subprocess
import time


def run_tool(
    cmd: list[str],
    *,
    timeout: int = 600,
    cwd: str | None = None,
    env: dict | None = None,
    stdin: bytes | None = None,
) -> dict:
    """Run a subprocess and return bounded structured output, timeout, error, or dry-run diagnostics."""
    cmd_str = " ".join(shlex.quote(x) for x in cmd)

    if os.environ.get("PRAXIS_SKILL_DRY_HOST") == "1":
        return {
            "ok": True,
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "wall_sec": 0.0,
            "cmd": cmd_str,
            "dry": True,
        }

    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            input=stdin,
            timeout=timeout,
            cwd=cwd,
            env=env,
            check=False,
        )
    except FileNotFoundError as e:
        return {
            "ok": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "wall_sec": round(time.time() - t0, 3),
            "cmd": cmd_str,
            "error": f"binary not found: {cmd[0]!r}",
        }
    except subprocess.TimeoutExpired as e:
        return {
            "ok": False,
            "returncode": -1,
            "stdout": (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or ""),
            "stderr": (e.stderr or b"").decode("utf-8", "replace") if isinstance(e.stderr, bytes) else (e.stderr or ""),
            "wall_sec": round(time.time() - t0, 3),
            "cmd": cmd_str,
            "error": f"timeout after {timeout}s",
        }
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "",
            "wall_sec": round(time.time() - t0, 3),
            "cmd": cmd_str,
            "error": f"subprocess error: {e!r}",
        }

    out = {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or b"").decode("utf-8", "replace")
        if isinstance(proc.stdout, bytes)
        else (proc.stdout or ""),
        "stderr": (proc.stderr or b"").decode("utf-8", "replace")
        if isinstance(proc.stderr, bytes)
        else (proc.stderr or ""),
        "wall_sec": round(time.time() - t0, 3),
        "cmd": cmd_str,
    }
    if not out["ok"]:
        out["error"] = f"non-zero exit {proc.returncode}"
    return out
