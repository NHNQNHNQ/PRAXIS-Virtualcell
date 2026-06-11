"""MCP stdio server — 在 .53 上直接调用 GROMACS 工具。

启动方式(由 PRAXIS-2 backend 通过 SSH stdio transport 连接):
  ssh -i $KEY zkyd@10.102.106.53 \
    "source .../conda.sh && conda activate praxis-md-cuda && \
     python -m praxis2.mcp.servers.gmx_server"

5 个 tool:
  write_file      — 写 mdp/top/ndx 等输入文件
  run_step        — 同步跑短命令(grompp/genion/editconf, <60s)
  run_background  — nohup 跑长任务(mdrun),返 job_id
  poll_job        — 查 job 状态 + 返输出尾行
  get_file        — 拉回日志/能量/坐标片段

纯逻辑函数(_*_impl)不依赖 mcp 库,可在无 mcp 环境下单测。
MCP 绑定仅在 __main__ / FastMCP 可用时触发。
"""
from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

# 允许写入 / 执行的根目录(防止越权访问)
_SAFE_ROOT = Path(os.environ.get("PRAXIS_GMX_WORK_ROOT", "/home/zkyd/praxis-md"))


def _safe_path(p: str) -> Path:
    """将用户提供的 path 限制在 _SAFE_ROOT 下，防止路径穿越。"""
    resolved = (_SAFE_ROOT / p).resolve()
    if not str(resolved).startswith(str(_SAFE_ROOT)):
        raise ValueError(f"路径越界: {p!r} 不在 {_SAFE_ROOT}")
    return resolved


def _safe_cwd(cwd: str) -> Path:
    """cwd 若为相对路径则限在 SAFE_ROOT 下；绝对路径也做边界检查。"""
    if not Path(cwd).is_absolute():
        work = _safe_path(cwd)
    else:
        work = Path(cwd).resolve()
        if not str(work).startswith(str(_SAFE_ROOT)):
            raise ValueError(f"cwd 越界: {cwd!r}")
    work.mkdir(parents=True, exist_ok=True)
    return work


# ---- 纯逻辑实现 ----

def write_file_impl(path: str, content: str) -> dict:
    target = _safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(target)}


def run_step_impl(cmd: str, cwd: str, timeout_s: float = 120.0) -> dict:
    work = _safe_cwd(cwd)
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=str(work),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout[-4000:] if result.stdout else "",
            "stderr": result.stderr[-4000:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "stdout": "", "stderr": f"timeout after {timeout_s}s"}


def run_background_impl(cmd: str, cwd: str) -> dict:
    work = _safe_cwd(cwd)
    script = textwrap.dedent(f"""\
        #!/bin/bash
        set -e
        trap 'echo "failed" > "{work}/job.status"' ERR
        cd "{work}"
        {cmd}
        echo "done" > "{work}/job.status"
    """)
    script_path = work / "mcp_job.sh"
    script_path.write_text(script, encoding="utf-8")
    script_path.chmod(0o755)
    result = subprocess.run(
        f"nohup bash {script_path} > {work}/stdout.log 2>{work}/stderr.log & echo $!",
        shell=True,
        cwd=str(work),
        capture_output=True,
        text=True,
    )
    pid = result.stdout.strip()
    if not pid.isdigit():
        raise RuntimeError(f"nohup 未返回 PID: {result.stdout!r} stderr={result.stderr!r}")
    job_id = f"local:{pid}"
    (work / "job.pid").write_text(pid, encoding="utf-8")
    return {"job_id": job_id, "work_dir": str(work)}


def poll_job_impl(job_id: str) -> dict:
    if not job_id.startswith("local:"):
        return {"status": "unknown", "tail": ""}
    pid = job_id[len("local:"):]

    # 从 /proc/{pid}/cwd 找 work_dir
    work_dir: Path | None = None
    try:
        cwd_link = Path(f"/proc/{pid}/cwd")
        if cwd_link.exists():
            work_dir = cwd_link.resolve()
    except (PermissionError, OSError):
        pass

    # 若 /proc 不可用，遍历 SAFE_ROOT 找 job.pid
    if work_dir is None:
        for p in _SAFE_ROOT.rglob("job.pid"):
            try:
                if p.read_text().strip() == pid:
                    work_dir = p.parent
                    break
            except OSError:
                continue

    sentinel = ""
    if work_dir:
        sentinel_file = work_dir / "job.status"
        if sentinel_file.exists():
            sentinel = sentinel_file.read_text().strip()

    if sentinel in ("done", "failed"):
        status = sentinel
    else:
        try:
            os.kill(int(pid), 0)
            status = "running"
        except (ProcessLookupError, ValueError):
            status = "failed"

    tail = ""
    if work_dir:
        log = work_dir / "stdout.log"
        if log.exists():
            try:
                lines = log.read_text(errors="replace").splitlines()
                tail = "\n".join(lines[-20:])
            except OSError:
                pass
    return {"status": status, "tail": tail}


def get_file_impl(path: str, max_bytes: int = 8192) -> dict:
    target = _safe_path(path)
    if not target.exists():
        return {"content": "", "size": 0, "truncated": False, "error": "file not found"}
    size = target.stat().st_size
    if size <= max_bytes:
        content = target.read_text(errors="replace")
        return {"content": content, "size": size, "truncated": False}
    with target.open("rb") as f:
        f.seek(-max_bytes, 2)
        raw = f.read(max_bytes)
    content = raw.decode("utf-8", errors="replace")
    return {"content": content, "size": size, "truncated": True}


# ---- MCP 绑定(仅在有 mcp 库时注册) ----

def _register_tools(mcp_instance) -> None:
    mcp_instance.tool()(lambda path, content: write_file_impl(path, content))
    mcp_instance.tool()(lambda cmd, cwd, timeout_s=120.0: run_step_impl(cmd, cwd, timeout_s))
    mcp_instance.tool()(lambda cmd, cwd: run_background_impl(cmd, cwd))
    mcp_instance.tool()(lambda job_id: poll_job_impl(job_id))
    mcp_instance.tool()(lambda path, max_bytes=8192: get_file_impl(path, max_bytes))


if __name__ == "__main__":
    from mcp.server.fastmcp import FastMCP  # noqa: PLC0415

    mcp = FastMCP("praxis-gmx")

    @mcp.tool()
    def write_file(path: str, content: str) -> dict:
        """将 content 写入 SAFE_ROOT/path 文件。"""
        return write_file_impl(path, content)

    @mcp.tool()
    def run_step(cmd: str, cwd: str, timeout_s: float = 120.0) -> dict:
        """在 cwd 同步运行 shell 命令(grompp/editconf/genion 等短命令)。"""
        return run_step_impl(cmd, cwd, timeout_s)

    @mcp.tool()
    def run_background(cmd: str, cwd: str) -> dict:
        """nohup 跑长任务(mdrun),返 job_id。"""
        return run_background_impl(cmd, cwd)

    @mcp.tool()
    def poll_job(job_id: str) -> dict:
        """查询后台 job 状态 + 返 stdout 尾 20 行。"""
        return poll_job_impl(job_id)

    @mcp.tool()
    def get_file(path: str, max_bytes: int = 8192) -> dict:
        """读取文件末尾内容(日志/能量/坐标)。"""
        return get_file_impl(path, max_bytes)

    mcp.run("stdio")
