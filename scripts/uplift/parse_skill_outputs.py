"""扫 brains/**/SKILL.md,抽 '## 输出契约' 后的第一个 ```json``` 块,
   解析为 dict(容忍 trailing comma 和 // 注释);记录 verdict。"""
from __future__ import annotations

import json
import re
from pathlib import Path

_SECTION_RE = re.compile(
    r"##\s*(?:输出契约|Outputs?|Output Contract)[^\n]*\n+```json\s*\n(.*?)```",
    re.S,
)
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")
# SKILL.md 用 [...] / {...} 当 placeholder,替成空容器
_LIST_ELLIPSIS_RE = re.compile(r"\[\s*\.\.\.\s*\]")
_DICT_ELLIPSIS_RE = re.compile(r"\{\s*\.\.\.\s*\}")
# 类似 "key": ... (单独的 ... 当值)
_BARE_ELLIPSIS_RE = re.compile(r":\s*\.\.\.")


def parse_outputs_block(body: str) -> tuple[dict | None, str | None]:
    """容忍 trailing comma 与 // 行注释 与 [...]/{...} placeholder,返回 (obj, err)。"""
    cleaned = _LINE_COMMENT_RE.sub("", body)
    cleaned = _LIST_ELLIPSIS_RE.sub("[]", cleaned)
    cleaned = _DICT_ELLIPSIS_RE.sub("{}", cleaned)
    cleaned = _BARE_ELLIPSIS_RE.sub(": null", cleaned)
    cleaned = _TRAILING_COMMA_RE.sub(r"\1", cleaned)
    try:
        obj = json.loads(cleaned)
        return (obj if isinstance(obj, dict) else None), None
    except json.JSONDecodeError as e:
        return None, f"JSONDecodeError: {e.msg} at line {e.lineno}"


def parse_skill_md(path: Path) -> dict:
    txt = path.read_text(encoding="utf-8", errors="replace")
    m = _SECTION_RE.search(txt)
    if not m:
        return {"path": str(path), "verdict": "MISSING_SECTION", "keys": None, "schema": None}
    obj, err = parse_outputs_block(m.group(1))
    if obj is None:
        return {"path": str(path), "verdict": "PARSE_ERR", "keys": None, "schema": None, "err": err}
    return {"path": str(path), "verdict": "OK", "keys": sorted(obj.keys()), "schema": obj}


def scan_all(brains_root: Path = Path("brains")) -> list[dict]:
    rows = []
    for md in sorted(brains_root.rglob("SKILL.md")):
        if md.name.startswith("._"):
            continue
        parts = md.parts
        brain = parts[1]
        skill = parts[-2]
        info = parse_skill_md(md)
        info["brain"] = brain
        info["skill"] = skill
        rows.append(info)
    return rows


if __name__ == "__main__":
    import sys
    rows = scan_all()
    by_v = {}
    for r in rows:
        by_v[r["verdict"]] = by_v.get(r["verdict"], 0) + 1
    print(json.dumps({"total": len(rows), "by_verdict": by_v}, indent=2, ensure_ascii=False))
    out_path = Path("_audit/skill_outputs_parsed.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    print(f"wrote {out_path}", file=sys.stderr)
