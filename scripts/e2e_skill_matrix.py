#!/usr/bin/env python3
"""GAP-E2E skill 真执行验证 harness。

用法(staging):
  PYTHONPATH=$PWD <conda python> scripts/e2e_skill_matrix.py <archetype>
读 _audit/green_skills.json + _audit/e2e_inputs/<archetype>.json,逐 skill 经
SkillExecTool 真路径(simulate=false)跑,四分类 verdict,写 _audit/e2e_results_<archetype>.json
+ 回写 _audit/skill_real_impl_inventory.csv。
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
AUDIT = REPO / "_audit"

# green_skills.json:各 brain 已通过人工确认的 skill 白名单
GREEN_SKILLS = AUDIT / "green_skills.json"
# skill 真实现清单 CSV(brain,skill,archetype,status)
INVENTORY_CSV = AUDIT / "skill_real_impl_inventory.csv"

DONE_REAL = "DONE_real"
NA = "N-A"
RED = "RED"
INCOMPLETE = "INCOMPLETE"  # 输入未提供/缺数据文件(策展缺口,非 skill 缺陷)
ERROR = "ERROR"
SKIPPED = "SKIPPED"

# error 文本特征(小写匹配)
_NA_MARKERS = ("n/a", "not applicable", "未装", "composite", "需上层", "fallback_hint", "需 redock")
_RED_MARKERS = ("未在 path", "not in path", "conda activate", "rc=1", "no such file", "env 不存在", "command not found",
                # env/依赖装坏(import/CUDA 库冲突)= 环境问题,非 skill bug → RED
                "importerror", "modulenotfounderror", "no module named", "undefined symbol",
                "libcusparse", "libnvjitlink", "cannot import", "cuda error", "cuda out of memory")
# 输入未提供/缺数据文件(策展输入没给齐,非 skill 缺陷、非软件缺):与真崩的 ERROR 区分
_INCOMPLETE_MARKERS = ("不存在", "需要 input", "缺少输入", "missing input", "required input", "not provided")


def load_inputs(archetype: str, green_archetype: str | None = None) -> dict:
    """读 e2e_inputs/<archetype>.json,与 green_skills 取交集(在 green 才跑)。

    返回 {skill: {"brain":..., "inputs":{...,"simulate":False}, "contract_keys":[...], "skip":bool}}。
    green_archetype 为 None 时不过滤,全量返回。
    """
    inputs_path = AUDIT / "e2e_inputs" / f"{archetype}.json"
    spec = json.loads(inputs_path.read_text(encoding="utf-8"))
    green_set: set[str] | None = None
    if green_archetype is not None:
        green = json.loads(GREEN_SKILLS.read_text(encoding="utf-8"))
        green_set = set(green.get(green_archetype, []))
    out: dict = {}
    for skill, cfg in spec.items():
        if green_set is not None and skill not in green_set:
            continue
        cfg.setdefault("inputs", {}).setdefault("simulate", False)
        cfg.setdefault("contract_keys", [])
        cfg.setdefault("skip", False)
        out[skill] = cfg
    return out


def update_inventory_csv(verdicts: dict) -> None:
    """把 verdict==DONE_real 的 (brain,skill) 行 status 改 DONE_real;其余不动。幂等。"""
    rows = list(csv.DictReader(INVENTORY_CSV.open(encoding="utf-8")))
    fields = list(rows[0].keys()) if rows else ["brain", "skill", "archetype", "status"]
    for r in rows:
        if verdicts.get((r["brain"], r["skill"])) == DONE_REAL:
            r["status"] = DONE_REAL
    with INVENTORY_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def classify_verdict(tool_result: dict, contract_keys: list[str]) -> str:
    """据 ToolResult(dict {ok,value,error})+ SKILL.md 契约 key 判四分类。

    真跑时 value 是 run.py 输出 dict(本身含 ok/poses/error/diagnostics 等)。

    返回值:
        DONE_real  — run.py ok=True + 非模拟 + 含契约 key
        N-A        — 模拟兜底(diagnostics.simulated=True)或显式不适用
        RED        — env/软件缺失导致失败
        ERROR      — 超时、契约 key 缺失等其它异常
    """
    raw = tool_result.get("value")
    if not isinstance(raw, dict):
        raw = {}
    # SkillExec 真跑把 run.py 输出嵌在 value["result"](外层 value 是
    # {execution_plan, ok, result, exec_via} 包装);降级/无 result 时退回 value 本身。
    out = raw["result"] if isinstance(raw.get("result"), dict) else raw
    outer_err = (tool_result.get("error") or "")
    inner_ok = out.get("ok")
    inner_err = (out.get("error") or "")
    inner_stderr = (out.get("stderr") or "")  # run.py subprocess stderr(import/CUDA 坏库线索在此)
    err_blob = f"{inner_err} {inner_stderr} {outer_err}".lower()

    # 1. run.py ok=True:先检查 simulated,再检查契约 key
    if inner_ok is True:
        diag = out.get("diagnostics") or {}
        if diag.get("simulated") is True:
            return NA
        if any(k in out for k in contract_keys):
            return DONE_REAL
        return ERROR  # ok 但输出不含任何契约 key,结构异常

    # 2. N-A:显式不适用/未装/合成兜底
    if any(m in err_blob for m in _NA_MARKERS):
        return NA

    # 3. RED:env/软件缺失
    if any(m in err_blob for m in _RED_MARKERS):
        return RED

    # 4. INCOMPLETE:输入未提供/缺数据文件(策展缺口,非 skill 缺陷,也非软件缺)
    if any(m in err_blob for m in _INCOMPLETE_MARKERS):
        return INCOMPLETE

    # 5. 其它失败(真崩:non-zero exit / 超时 / 未知错误)
    return ERROR


async def _default_executor(name: str, brain: str | None, inputs: dict) -> dict:
    """真 executor:调 SkillExecTool。返回 ToolResult 的 dict 形态。"""
    from praxis2.tools.skill_exec import SkillExecTool
    tool = SkillExecTool()
    payload: dict = {"name": name, "inputs": inputs}
    if brain:
        payload["brain"] = brain
    res = await tool.run(payload)
    return {"ok": res.ok, "value": res.value, "error": res.error}


async def run_archetype(archetype: str, *, green_archetype: str | None = None, executor=None) -> list[dict]:
    """逐 skill 跑 + 分类 + 写报告 + 回写 CSV。

    executor 默认走真 SkillExec(单测注入 fake,不依赖 SSH)。
    """
    executor = executor or _default_executor
    loaded = load_inputs(archetype, green_archetype=green_archetype)
    results: list[dict] = []
    verdicts: dict = {}
    for skill, cfg in loaded.items():
        brain = cfg.get("brain")
        if cfg.get("skip"):
            verdict = SKIPPED
            tr: dict = {"skipped": True}
        else:
            tr = await executor(skill, brain, cfg.get("inputs", {}))
            verdict = classify_verdict(tr, cfg.get("contract_keys", []))
        verdicts[(brain, skill)] = verdict
        results.append({
            "skill": skill,
            "brain": brain,
            "verdict": verdict,
            "evidence": tr.get("value") if isinstance(tr, dict) else None,
            "error": tr.get("error") if isinstance(tr, dict) else None,
        })
    # 写 e2e_results_<archetype>.json 报告
    (AUDIT / f"e2e_results_{archetype}.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # 回写 CSV:DONE_real 的 skill 升级 status
    update_inventory_csv(verdicts)
    return results


def main() -> int:
    """命令行入口:python scripts/e2e_skill_matrix.py <archetype> [green_archetype]。"""
    import asyncio as _aio
    import sys

    if len(sys.argv) < 2:
        print("用法: e2e_skill_matrix.py <archetype> [green_archetype]", file=sys.stderr)
        return 2
    archetype = sys.argv[1]
    green = sys.argv[2] if len(sys.argv) > 2 else None
    results = _aio.run(run_archetype(archetype, green_archetype=green))
    counts: dict = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print(f"[e2e:{archetype}] {counts}")
    for r in results:
        print(f"  {r['verdict']:9} {r['brain']}/{r['skill']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
