"""real() 骨架生成器。

- N_A 桶:返回结构化 not-implemented;不抛
- GREEN 桶:写一个能跑通的 'echo-like' real,内部 try run_tool 调一个无害命令
  (具体真实 CLI 由人工后续编辑;这一步保的是'非崩'契约)
- RED_EASY:同 GREEN 但 diagnostics.note 写明 host 缺工具,跑出来是 dry-host 模式

后续每个 brain 内可手工把 GREEN 桶的 real() 改成真正的工具调用(留 TODO 标签)。
"""
from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path

from scripts.uplift._skills import all_brain_names, find_skill_dirs


def build_real_fn_na(reason: str) -> str:
    safe_reason = reason.replace('"', '\\"')
    return textwrap.dedent(f'''
    def real(payload):
        """N/A — 此 skill 无法实现 real 模式(license/data 受限)。"""
        return {{
            "ok": False,
            "error": "N/A — {safe_reason}",
            "fallback": "pass simulate=true to use synthetic data",
            "diagnostics": {{"brain": BRAIN, "skill": SKILL, "archetype": ARCHETYPE, "na_reason": "{safe_reason}"}},
        }}
    ''').lstrip()


def build_real_fn_green(archetype: str) -> str:
    """GREEN 骨架:导入 run_tool,跑一个无害 echo;留 TODO 给后续 commit 替成真命令。"""
    return textwrap.dedent('''
    def real(payload):
        """auto-generated real() — TODO: 换成对应工具的真实 CLI 调用。

        当前实现:用 run_tool 跑 `python3 -c "print('ok')"`,证明 host conda env
        + subprocess 链路通;diagnostics.todo 标注需要人工接入哪些 CLI。
        """
        try:
            from brains._common.lib.run_tool import run_tool
        except ImportError:
            import sys as _sys
            _sys.path.insert(0, "/home/zkyd/data1/mzy/praxis2-brains")
            from _common.lib.run_tool import run_tool  # noqa: F401

        r = run_tool(["python3", "-c", "print('skill-real-placeholder')"], timeout=30)
        diagnostics = {
            "brain": BRAIN, "skill": SKILL, "archetype": ARCHETYPE,
            "todo": "replace echo with real CLI; see SKILL.md SOP",
            "subprocess": {"cmd": r.get("cmd"), "wall_sec": r.get("wall_sec"), "rc": r.get("returncode")},
        }
        if r.get("dry"):
            diagnostics["dry"] = True
        if not r["ok"]:
            return {"ok": False, "error": r.get("error", "subprocess failed"), "diagnostics": diagnostics}
        return {"ok": True, "skill_id": SKILL, "result": "placeholder; replace with real parse", "diagnostics": diagnostics}
    ''').lstrip()


# 匹配 "def real(...):" 开始,到下一个顶层 def/class/非缩进行 之前
_REAL_FN_RE = re.compile(
    r"^def\s+real\s*\([^)]*\)\s*:[ \t]*\n(?:(?:[ \t].*|[ \t]*)\n)+",
    re.M,
)


def rewrite_real(
    run_py: Path, *, bucket: str, reason: str = "", archetype: str = "generic",
    hand_written_lines_threshold: int = 200,
) -> dict:
    if not run_py.is_file():
        return {"path": str(run_py), "action": "no-run-py"}
    txt = run_py.read_text(encoding="utf-8", errors="replace")
    if txt.count("\n") > hand_written_lines_threshold:
        return {"path": str(run_py), "action": "skip-hand-written", "lines": txt.count("\n")}
    if bucket == "N_A":
        new_fn = build_real_fn_na(reason or "no host_env or license-blocked")
    else:
        new_fn = build_real_fn_green(archetype)
    m = _REAL_FN_RE.search(txt)
    if not m:
        return {"path": str(run_py), "action": "no-real-fn"}
    new_txt = txt[: m.start()] + new_fn + "\n" + txt[m.end():]
    run_py.write_text(new_txt, encoding="utf-8")
    return {"path": str(run_py), "action": "rewritten", "bucket": bucket}


def _archetype_of(run_py: Path) -> str:
    if not run_py.is_file():
        return "generic"
    txt = run_py.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'ARCHETYPE\s*=\s*"([^"]+)"', txt)
    return m.group(1) if m else "generic"


def regen_brain(brain: str, brains_root: Path = Path("brains")) -> list[dict]:
    parity_path = Path("_audit/parity_v1_per_brain.json")
    if not parity_path.is_file():
        return [{"action": "no-parity", "hint": "run parity_per_brain first"}]
    parity = {f"{r['brain']}/{r['skill']}": r for r in json.loads(parity_path.read_text())}
    rows = []
    for sd in find_skill_dirs(brain, brains_root):
        key = f"{brain}/{sd.name}"
        p = parity.get(key)
        if not p:
            rows.append({"skill": key, "action": "skip-no-parity"})
            continue
        archetype = _archetype_of(sd / "run.py")
        rows.append(rewrite_real(
            sd / "run.py", bucket=p["bucket"], reason=p.get("reason", ""), archetype=archetype,
        ))
    return rows


if __name__ == "__main__":
    import sys
    brain = sys.argv[1] if len(sys.argv) > 1 else None
    if brain:
        rows = regen_brain(brain)
    else:
        rows = []
        for bn in all_brain_names():
            rows.extend(regen_brain(bn))
    by_a = {}
    for r in rows:
        by_a[r.get("action")] = by_a.get(r.get("action"), 0) + 1
    print(json.dumps({"total": len(rows), "by_action": by_a}, indent=2, ensure_ascii=False))
