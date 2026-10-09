#!/usr/bin/env python3
"""大脑审计:统计各学科 cases/rules/skills 真实数 + case frontmatter 校验。

用途:
1. 给 brains/INDEX.md 提供真实统计(替换过时数字)
2. 找出无 frontmatter / 缺 case_id 的 case(格式整理)

用法: python scripts/brain_audit.py [--json]
"""
from __future__ import annotations

import json
import os
import re
import sys

BRAINS = os.path.join(os.path.dirname(__file__), "..", "brains")


def _disciplines() -> list[str]:
    return sorted(
        d for d in os.listdir(BRAINS)
        if os.path.isdir(os.path.join(BRAINS, d)) and not d.startswith(".")
    )


def _walk_md(base: str) -> list[str]:
    out = []
    for root, _, files in os.walk(base):
        for f in files:
            if f.endswith(".md") and not f.startswith("._"):
                out.append(os.path.join(root, f))
    return out


def _classify(disc: str) -> dict:
    base = os.path.join(BRAINS, disc)
    cases, rules, skills = [], [], []
    for p in _walk_md(base):
        rel = p[len(base) + 1:]
        if "memory/cases/" in rel.replace("\\", "/"):
            cases.append(p)
        elif "memory/rules/" in rel.replace("\\", "/"):
            if os.path.basename(p).upper() != "README.MD":
                rules.append(p)
        elif os.path.basename(p) == "SKILL.md":
            skills.append(p)
    return {"cases": cases, "rules": rules, "skills": skills}


def _frontmatter_keys(path: str) -> list[str] | None:
    """返回 frontmatter 字段 key 列表;无 frontmatter 返 None。"""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            txt = f.read()
    except OSError:
        return None
    m = re.match(r"^---\s*\n(.*?)\n---", txt, re.S)
    if not m:
        return None
    return re.findall(r"^([a-zA-Z_][a-zA-Z0-9_]*):", m.group(1), re.M)


def audit() -> dict:
    result = {"disciplines": {}, "issues": {"no_frontmatter": [], "no_case_id": []}}
    for disc in _disciplines():
        c = _classify(disc)
        for case in c["cases"]:
            keys = _frontmatter_keys(case)
            rel = os.path.relpath(case, BRAINS)
            if keys is None:
                result["issues"]["no_frontmatter"].append(rel)
            elif "case_id" not in keys:
                result["issues"]["no_case_id"].append(rel)
        result["disciplines"][disc] = {
            "cases": len(c["cases"]),
            "rules": len(c["rules"]),
            "skills": len(c["skills"]),
        }
    return result


def main() -> int:
    r = audit()
    if "--json" in sys.argv:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0

    print("=== 各学科统计(真实文件数) ===")
    print(f"{'学科':<14}{'cases':>7}{'rules':>7}{'skills':>7}")
    tc = tr = ts = 0
    for disc, d in r["disciplines"].items():
        print(f"{disc:<14}{d['cases']:>7}{d['rules']:>7}{d['skills']:>7}")
        tc += d["cases"]; tr += d["rules"]; ts += d["skills"]
    print(f"{'总计':<14}{tc:>7}{tr:>7}{ts:>7}")

    nf = r["issues"]["no_frontmatter"]
    nc = r["issues"]["no_case_id"]
    print("\n=== case 格式问题 ===")
    print(f"无 frontmatter 的 case: {len(nf)}")
    for p in nf[:15]:
        print(f"  - {p}")
    if len(nf) > 15:
        print(f"  ... 还有 {len(nf) - 15} 个")
    print(f"有 frontmatter 但缺 case_id: {len(nc)}")
    for p in nc[:10]:
        print(f"  - {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
