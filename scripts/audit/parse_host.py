#!/usr/bin/env python3
"""阶段 0 解析: host_raw.txt → host_inventory.json (结构化)
用法: python scripts/audit/parse_host.py _audit/host_raw.txt _audit/host_inventory.json
只读, 纯 stdlib。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def split_sections(text: str) -> dict[str, str]:
    """按 ===[NAME]=== 切片。"""
    out: dict[str, str] = {}
    cur_name: str | None = None
    cur_lines: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^===\[(.+?)\]===\s*$", line)
        if m:
            if cur_name is not None:
                out[cur_name] = "\n".join(cur_lines).strip()
            cur_name = m.group(1)
            cur_lines = []
        elif cur_name is not None:
            cur_lines.append(line)
    if cur_name is not None:
        out[cur_name] = "\n".join(cur_lines).strip()
    return out


def parse_basic(s: str) -> dict:
    lines = [ln for ln in s.splitlines() if ln.strip()]
    out: dict = {}
    if lines:
        out["hostname"] = lines[0].strip()
    for ln in lines:
        if ln.startswith("Description:"):
            out["os"] = ln.split(":", 1)[1].strip()
        elif ln.startswith("Linux"):
            out["kernel"] = ln.strip()
    return out


def parse_cpu(s: str) -> dict:
    out: dict = {}
    lines = s.splitlines()
    if lines and lines[0].strip().isdigit():
        out["cores"] = int(lines[0].strip())
    for ln in lines:
        if "model name" in ln:
            out["model"] = ln.split(":", 1)[1].strip()
        m = re.match(r"^Mem:\s+(\S+)", ln)
        if m:
            out["mem_total"] = m.group(1)
    return out


def parse_gpu(s: str) -> list[dict]:
    gpus = []
    for ln in s.splitlines():
        m = re.match(r"^GPU (\d+): (.+?) \(UUID:", ln)
        if m:
            gpus.append({"id": int(m.group(1)), "name": m.group(2).strip()})
    # 第二段附带显存
    mems = []
    for ln in s.splitlines():
        m = re.match(r"^(NVIDIA .+?), (\d+) MiB", ln)
        if m:
            mems.append(int(m.group(2)))
    for i, mem in enumerate(mems):
        if i < len(gpus):
            gpus[i]["mem_mib"] = mem
    return gpus


def parse_disk(s: str) -> list[dict]:
    out = []
    for ln in s.splitlines()[1:]:  # 跳 header
        parts = ln.split()
        if len(parts) >= 6 and parts[0].startswith(("/", "tmpfs")):
            out.append({
                "fs": parts[0], "size": parts[1], "used": parts[2],
                "avail": parts[3], "mount": parts[-1],
            })
    return out


def parse_conda_envs(s: str) -> list[str]:
    out = []
    for ln in s.splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            out.append(ln)
    return out


def parse_conda_packages(s: str) -> dict[str, list[str]]:
    """按 '--- env: NAME ---' 切, 每段是 pkg==ver 列表。"""
    out: dict[str, list[str]] = {}
    cur: str | None = None
    buf: list[str] = []
    for ln in s.splitlines():
        m = re.match(r"^--- env:\s*(\S+)\s*---", ln)
        if m:
            if cur is not None:
                out[cur] = sorted(set(buf))
            cur = m.group(1)
            buf = []
        elif cur is not None:
            ln = ln.strip()
            if ln and "==" in ln:
                # 仅留包名(忽略 build hash); 但保留版本号
                # 形如 numpy==1.24.0
                buf.append(ln)
    if cur is not None:
        out[cur] = sorted(set(buf))
    return out


def parse_bin_which(s: str) -> tuple[dict[str, str], dict[str, list[str]]]:
    """global 二进制 + per-env 二进制。"""
    glb: dict[str, str] = {}
    per_env: dict[str, list[str]] = {}
    for ln in s.splitlines():
        parts = ln.split("\t")
        if len(parts) < 3:
            continue
        kind = parts[0]
        if kind == "global":
            glb[parts[1]] = parts[2]
        elif kind == "env":
            env_name, binary = parts[1], parts[2]
            per_env.setdefault(env_name, []).append(binary)
    for k in per_env:
        per_env[k] = sorted(set(per_env[k]))
    return glb, per_env


def parse_running(s: str) -> list[str]:
    return [ln for ln in s.splitlines() if ln.strip()]


def packages_to_names(pkgs: list[str]) -> list[str]:
    """numpy==1.24.0 -> numpy (小写, 用于 deps 对账)。"""
    out = []
    for p in pkgs:
        name = p.split("==", 1)[0].strip().lower()
        if name:
            out.append(name)
    return sorted(set(out))


def main() -> int:
    if len(sys.argv) != 3:
        print("用法: parse_host.py <raw.txt> <out.json>", file=sys.stderr)
        return 2
    raw = Path(sys.argv[1]).read_text()
    secs = split_sections(raw)

    bin_glb, bin_env = parse_bin_which(secs.get("BIN_WHICH", ""))
    pkg_by_env = parse_conda_packages(secs.get("CONDA_ENV_PACKAGES", ""))
    pkg_names_by_env = {env: packages_to_names(pkgs) for env, pkgs in pkg_by_env.items()}

    inv = {
        "meta": {
            "basic": parse_basic(secs.get("BASIC", "")),
            "cpu": parse_cpu(secs.get("CPU", "")),
            "gpus": parse_gpu(secs.get("GPU", "")),
            "disks": parse_disk(secs.get("DISK", "")),
            "conda_info": secs.get("CONDA_INFO", "").strip(),
            "module_system": secs.get("MODULE_AVAIL", "").strip() == "(no module system)",
        },
        "conda_envs": parse_conda_envs(secs.get("CONDA_ENVS", "")),
        "conda_packages": pkg_by_env,           # env -> ["pkg==ver", ...]
        "conda_package_names": pkg_names_by_env,  # env -> ["pkg", ...] (小写)
        "binaries_global": bin_glb,
        "binaries_per_env": bin_env,
        "license_dirs_raw": secs.get("LICENSE_DIRS", ""),
        "data_paths_raw": secs.get("DATA_PATHS", ""),
        "data_sizes_raw": secs.get("DATA_SIZES", ""),
        "env_files_redacted": secs.get("ENV_FILES", "").strip(),
        "running_processes": parse_running(secs.get("RUNNING_PROCESSES", "")),
    }
    out_path = Path(sys.argv[2])
    out_path.write_text(json.dumps(inv, indent=2, ensure_ascii=False))

    # 摘要 → stderr
    print(f"OS: {inv['meta']['basic'].get('os', '?')}", file=sys.stderr)
    print(f"CPU cores: {inv['meta']['cpu'].get('cores', '?')}", file=sys.stderr)
    print(f"GPUs: {len(inv['meta']['gpus'])}x {inv['meta']['gpus'][0]['name'] if inv['meta']['gpus'] else '-'}", file=sys.stderr)
    print(f"conda envs: {len(inv['conda_envs'])}", file=sys.stderr)
    print(f"total unique pkgs (union): {len(set().union(*pkg_names_by_env.values()))}", file=sys.stderr)
    print(f"global binaries: {len(bin_glb)}", file=sys.stderr)
    print(f"per-env binaries hits: {sum(len(v) for v in bin_env.values())}", file=sys.stderr)
    print(f"→ {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
