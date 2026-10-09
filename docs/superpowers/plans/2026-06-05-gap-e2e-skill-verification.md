# GAP-E2E skill 真执行验证 harness + docking 切片 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建可复用 harness `scripts/e2e_skill_matrix.py`,经策展真输入驱动 skill 走 SkillExec 真路径(`simulate=false`)在 staging 真跑,四分类 DONE_real/N-A/RED/ERROR 用证据替代猜测;本轮在 docking(9 skill)跑通,DONE_real 从 1 扩到真可跑集。

**Architecture:** harness 分纯逻辑层(`classify_verdict`/`load_inputs`/`update_inventory_csv`,可本地单测)+ 执行层(`run_skill` 调 `SkillExecTool.run(simulate=false)`、`main(archetype)` 编排,run_skill 注入式 executor 便于单测)。输入集 `_audit/e2e_inputs/<archetype>.json` 策展真 payload。报告 `_audit/e2e_results_<archetype>.json` + 回写 `_audit/skill_real_impl_inventory.csv`。

**Tech Stack:** Python stdlib(asyncio/csv/json/pathlib)+ 复用 `praxis2.tools.skill_exec.SkillExecTool` + pytest。无新 pip 依赖。

**Spec:** `docs/superpowers/specs/2026-06-05-gap-e2e-skill-verification-design.md`

---

## 起点与约束
- 起点:`main` HEAD `1309e7f`(GAP-E2E spec)。
- 既有事实:`SkillExecTool()` 无构造参数(env 驱动 SSH:`PRAXIS_SKILL_SSH_HOST`/`_REMOTE_BRAINS`/`_CONDA_INIT`,staging `~/praxis2.env` 已配);`run({name, brain, inputs})`,`simulate` 放 `inputs` 内;返回 `ToolResult(ok, value, error)`,真跑时 `value` = run.py stdout 解析的输出 dict(其本身含 `ok`/`poses`/`error`/`diagnostics` 等)。
- run.py 输出契约:`real()` 成功 → `{"ok":True, ...契约 key...}`;软件缺 → `{"ok":False,"error":"gnina 未在 PATH..."}`;`simulate=true` → 输出含 `diagnostics.simulated=True`。
- 雷区:工作区常驻无关 `brains/microbiome/` 改动,**commit 只 add 目标文件,绝不 `git add .`/`-A`**;commit message 末尾 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`。
- staging SOP:probe/harness 经 rsync + `ssh ... 'cd repo && source ~/praxis2.env && PYTHONPATH=$PWD <conda python> scripts/e2e_skill_matrix.py docking'`(PYTHONPATH 必须)。

## File Structure
| 文件 | 动作 | 职责 |
|---|---|---|
| `scripts/e2e_skill_matrix.py` | 新建 | harness:纯逻辑 + 执行编排 |
| `_audit/e2e_inputs/docking.json` | 新建 | docking 9 skill 真 payload |
| `tests/test_e2e_skill_matrix.py` | 新建 | 纯逻辑单测(分类/加载/CSV 回写) |
| `_audit/skill_real_impl_inventory.csv` | 改(Task5 回写) | DONE_real 扩面 |
| `_audit/e2e_results_docking.json` | 新建(Task5 产出) | 本轮 verdict 报告 |
| `TEST-AGENT-FRAMEWORK.md` | 改(Task6) | GAP-E2E-1 回填结果 + harness 用法 |

---

## Task 1: classify_verdict 四分类(纯逻辑 + 单测)

**Files:**
- Create: `scripts/e2e_skill_matrix.py`
- Test: `tests/test_e2e_skill_matrix.py`

- [ ] **Step 1: 写失败测试**(新建 `tests/test_e2e_skill_matrix.py`)

```python
"""GAP-E2E harness 纯逻辑单测。"""
import importlib.util
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("e2e_skill_matrix", _REPO / "scripts" / "e2e_skill_matrix.py")
esm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(esm)


def test_done_real_when_ok_and_contract_keys():
    tr = {"ok": True, "value": {"ok": True, "poses": [{"rank": 1}], "best_pose": {"rank": 1}}, "error": None}
    assert esm.classify_verdict(tr, ["poses", "best_pose"]) == "DONE_real"


def test_na_when_simulated():
    tr = {"ok": True, "value": {"ok": True, "poses": [1], "diagnostics": {"simulated": True}}, "error": None}
    assert esm.classify_verdict(tr, ["poses"]) == "N-A"


def test_na_when_error_marks_not_applicable():
    tr = {"ok": False, "value": {"ok": False, "error": "N/A: composite skill 需上层编排"}, "error": None}
    assert esm.classify_verdict(tr, ["poses"]) == "N-A"


def test_red_when_software_missing():
    tr = {"ok": True, "value": {"ok": False, "error": "gnina 未在 PATH;请走 praxis-dock env"}, "error": None}
    assert esm.classify_verdict(tr, ["poses"]) == "RED"


def test_red_when_env_activate_failed():
    tr = {"ok": False, "value": {}, "error": "ssh/远端命令失败(rc=1) conda activate praxis-x"}
    assert esm.classify_verdict(tr, ["poses"]) == "RED"


def test_error_when_ok_but_no_contract_keys():
    tr = {"ok": True, "value": {"ok": True, "unexpected": 1}, "error": None}
    assert esm.classify_verdict(tr, ["poses", "best_pose"]) == "ERROR"


def test_error_when_timeout():
    tr = {"ok": False, "value": {}, "error": "命令超时(>600s),已 kill"}
    assert esm.classify_verdict(tr, ["poses"]) == "ERROR"
```

- [ ] **Step 2: 跑测试确认红**

Run: `cd /Volumes/T7/clade-learn/PRAXIS-2 && .venv/bin/python -m pytest tests/test_e2e_skill_matrix.py -v`
Expected: FAIL(模块/函数不存在)。

- [ ] **Step 3: 实现 classify_verdict**(新建 `scripts/e2e_skill_matrix.py`)

```python
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

DONE_REAL = "DONE_real"
NA = "N-A"
RED = "RED"
ERROR = "ERROR"
SKIPPED = "SKIPPED"

# error 文本特征(小写匹配)
_NA_MARKERS = ("n/a", "not applicable", "未装", "composite", "需上层", "fallback_hint", "需 redock")
_RED_MARKERS = ("未在 path", "not in path", "conda activate", "rc=1", "no such file", "env 不存在", "command not found")


def classify_verdict(tool_result: dict, contract_keys: list[str]) -> str:
    """据 ToolResult(dict {ok,value,error})+ SKILL.md 契约 key 判四分类。
    真跑时 value 是 run.py 输出 dict(本身含 ok/poses/error/diagnostics)。"""
    out = tool_result.get("value")
    if not isinstance(out, dict):
        out = {}
    outer_err = (tool_result.get("error") or "")
    inner_ok = out.get("ok")
    inner_err = (out.get("error") or "")
    err_blob = f"{inner_err} {outer_err}".lower()

    # 1. 真成功:run.py ok=True + 非合成 + 含契约 key
    if inner_ok is True:
        diag = out.get("diagnostics") or {}
        if diag.get("simulated") is True:
            return NA
        if any(k in out for k in contract_keys):
            return DONE_REAL
        return ERROR  # ok 但输出不含契约 key,可疑
    # 2. N-A:显式不适用/未装/合成兜底
    if any(m in err_blob for m in _NA_MARKERS):
        return NA
    # 3. RED:env/软件缺
    if any(m in err_blob for m in _RED_MARKERS):
        return RED
    # 4. 其它失败
    return ERROR
```

注:实现者**先 Read `praxis2/tools/skill_exec.py` 的 `_exec_via_ssh`(约 :253-324)确认 `value` 真实形态**;若真跑 value 把 run.py 输出嵌在 `value["result"]` 之类子键,在 `classify_verdict` 顶部把 `out` 解到那一层(并相应改测试的 value 结构,保持测试与实现同契约)。

- [ ] **Step 4: 跑测试确认绿**

Run: `cd /Volumes/T7/clade-learn/PRAXIS-2 && .venv/bin/python -m pytest tests/test_e2e_skill_matrix.py -v`
Expected: 7 passed。

- [ ] **Step 5: Commit**

```bash
cd /Volumes/T7/clade-learn/PRAXIS-2
git add scripts/e2e_skill_matrix.py tests/test_e2e_skill_matrix.py
git commit -m "feat(e2e): skill 真执行验证 harness — classify_verdict 四分类

DONE_real/N-A/RED/ERROR 据 run.py 输出 ok+契约key+simulated 标记 + error 特征判定。

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: load_inputs + update_inventory_csv(纯逻辑 + 单测)

**Files:**
- Modify: `scripts/e2e_skill_matrix.py`
- Test: `tests/test_e2e_skill_matrix.py`(追加)

- [ ] **Step 1: 写失败测试**(末尾追加)

```python
def test_load_inputs_filters_by_green(tmp_path, monkeypatch):
    (tmp_path / "_audit").mkdir()
    (tmp_path / "_audit" / "green_skills.json").write_text(
        '{"dock": ["vina_gnina_dock", "redock_benchmark"]}', encoding="utf-8")
    (tmp_path / "_audit" / "e2e_inputs").mkdir()
    (tmp_path / "_audit" / "e2e_inputs" / "docking.json").write_text(
        '{"vina_gnina_dock": {"brain": "dock", "inputs": {"simulate": false}, "contract_keys": ["poses"]}}',
        encoding="utf-8")
    monkeypatch.setattr(esm, "AUDIT", tmp_path / "_audit")
    loaded = esm.load_inputs("docking", green_archetype="dock")
    assert "vina_gnina_dock" in loaded
    assert loaded["vina_gnina_dock"]["contract_keys"] == ["poses"]
    # redock 在 green 但 e2e_inputs 没给 → 标记缺输入
    assert loaded["vina_gnina_dock"]["inputs"]["simulate"] is False


def test_update_inventory_csv_promotes_done_real(tmp_path, monkeypatch):
    csvp = tmp_path / "inv.csv"
    csvp.write_text("brain,skill,archetype,status\ndock,vina_gnina_dock,docking,TODO\ndock,redock_benchmark,docking,TODO\n", encoding="utf-8")
    monkeypatch.setattr(esm, "INVENTORY_CSV", csvp)
    esm.update_inventory_csv({("dock", "vina_gnina_dock"): "DONE_real", ("dock", "redock_benchmark"): "RED"})
    rows = list(csv.DictReader(csvp.open(encoding="utf-8")))
    by = {(r["brain"], r["skill"]): r["status"] for r in rows}
    assert by[("dock", "vina_gnina_dock")] == "DONE_real"
    assert by[("dock", "redock_benchmark")] == "TODO"  # 非 DONE_real 不改 CSV(详情在 JSON 报告)


def test_update_inventory_csv_idempotent(tmp_path, monkeypatch):
    csvp = tmp_path / "inv.csv"
    csvp.write_text("brain,skill,archetype,status\ndock,vina_gnina_dock,docking,DONE_real\n", encoding="utf-8")
    monkeypatch.setattr(esm, "INVENTORY_CSV", csvp)
    esm.update_inventory_csv({("dock", "vina_gnina_dock"): "DONE_real"})
    assert csvp.read_text(encoding="utf-8").count("DONE_real") == 1
```

- [ ] **Step 2: 跑测试确认红**

Run: `cd /Volumes/T7/clade-learn/PRAXIS-2 && .venv/bin/python -m pytest tests/test_e2e_skill_matrix.py -k "load_inputs or inventory" -v`
Expected: FAIL(无 load_inputs/update_inventory_csv/INVENTORY_CSV)。

- [ ] **Step 3: 实现 load_inputs + update_inventory_csv**(在 `scripts/e2e_skill_matrix.py` 的常量后追加)

```python
GREEN_SKILLS = AUDIT / "green_skills.json"
INVENTORY_CSV = AUDIT / "skill_real_impl_inventory.csv"


def load_inputs(archetype: str, green_archetype: str | None = None) -> dict:
    """读 e2e_inputs/<archetype>.json,与 green_skills 取交集(在 green 才跑)。
    返回 {skill: {"brain":..., "inputs":{...,"simulate":False}, "contract_keys":[...], "skip":bool}}。"""
    inputs_path = AUDIT / "e2e_inputs" / f"{archetype}.json"
    spec = json.loads(inputs_path.read_text(encoding="utf-8"))
    green = json.loads(GREEN_SKILLS.read_text(encoding="utf-8"))
    green_set = set(green.get(green_archetype, [])) if green_archetype else None
    out = {}
    for skill, cfg in spec.items():
        if green_set is not None and skill not in green_set:
            continue
        cfg.setdefault("inputs", {}).setdefault("simulate", False)
        cfg.setdefault("contract_keys", [])
        cfg.setdefault("skip", False)
        out[skill] = cfg
    return out


def update_inventory_csv(verdicts: dict) -> None:
    """把 verdict==DONE_real 的 (brain,skill) 行 status 改 DONE_real;其余不动(详情在 JSON 报告)。幂等。"""
    rows = list(csv.DictReader(INVENTORY_CSV.open(encoding="utf-8")))
    fields = rows[0].keys() if rows else ["brain", "skill", "archetype", "status"]
    for r in rows:
        if verdicts.get((r["brain"], r["skill"])) == DONE_REAL:
            r["status"] = DONE_REAL
    with INVENTORY_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fields))
        w.writeheader()
        w.writerows(rows)
```

- [ ] **Step 4: 跑测试确认绿**

Run: `cd /Volumes/T7/clade-learn/PRAXIS-2 && .venv/bin/python -m pytest tests/test_e2e_skill_matrix.py -v`
Expected: 全 PASS(7 + 3)。

- [ ] **Step 5: Commit**

```bash
cd /Volumes/T7/clade-learn/PRAXIS-2
git add scripts/e2e_skill_matrix.py tests/test_e2e_skill_matrix.py
git commit -m "feat(e2e): load_inputs(green 交集)+ update_inventory_csv(DONE_real 回写,幂等)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: run_skill(注入式 executor)+ main 编排(单测 + 报告)

**Files:**
- Modify: `scripts/e2e_skill_matrix.py`
- Test: `tests/test_e2e_skill_matrix.py`(追加)

- [ ] **Step 1: 写失败测试**(末尾追加,用 fake executor 不依赖 SSH)

```python
import asyncio


def test_run_archetype_with_fake_executor(tmp_path, monkeypatch):
    # fake executor:按 skill 名返回不同 ToolResult dict
    async def fake_exec(name, brain, inputs):
        if name == "vina_gnina_dock":
            return {"ok": True, "value": {"ok": True, "poses": [1], "best_pose": {"rank": 1}}, "error": None}
        if name == "induced_fit_docking":
            return {"ok": False, "value": {"ok": False, "error": "N/A: Schrödinger 商业软件未装"}, "error": None}
        return {"ok": True, "value": {"ok": False, "error": "gnina 未在 PATH"}, "error": None}

    # 装配 audit 目录
    aud = tmp_path / "_audit"
    (aud / "e2e_inputs").mkdir(parents=True)
    (aud / "green_skills.json").write_text('{"dock":["vina_gnina_dock","induced_fit_docking","covalent_docking"]}', encoding="utf-8")
    (aud / "e2e_inputs" / "docking.json").write_text(json.dumps({
        "vina_gnina_dock": {"brain": "dock", "inputs": {"simulate": False}, "contract_keys": ["poses", "best_pose"]},
        "induced_fit_docking": {"brain": "dock", "inputs": {"simulate": False}, "contract_keys": ["poses"], "skip": False},
        "covalent_docking": {"brain": "dock", "inputs": {"simulate": False}, "contract_keys": ["poses"]},
    }), encoding="utf-8")
    (aud / "skill_real_impl_inventory.csv").write_text(
        "brain,skill,archetype,status\ndock,vina_gnina_dock,docking,TODO\ndock,induced_fit_docking,docking,TODO\ndock,covalent_docking,docking,TODO\n", encoding="utf-8")
    monkeypatch.setattr(esm, "AUDIT", aud)
    monkeypatch.setattr(esm, "GREEN_SKILLS", aud / "green_skills.json")
    monkeypatch.setattr(esm, "INVENTORY_CSV", aud / "skill_real_impl_inventory.csv")

    results = asyncio.run(esm.run_archetype("docking", green_archetype="dock", executor=fake_exec))
    by = {r["skill"]: r["verdict"] for r in results}
    assert by["vina_gnina_dock"] == "DONE_real"
    assert by["induced_fit_docking"] == "N-A"
    assert by["covalent_docking"] == "RED"
    # 报告落盘
    rep = json.loads((aud / "e2e_results_docking.json").read_text(encoding="utf-8"))
    assert len(rep) == 3
    # CSV 只升 vina
    rows = list(csv.DictReader((aud / "skill_real_impl_inventory.csv").open(encoding="utf-8")))
    assert {(r["skill"], r["status"]) for r in rows} >= {("vina_gnina_dock", "DONE_real"), ("covalent_docking", "TODO")}
```

- [ ] **Step 2: 跑测试确认红**

Run: `cd /Volumes/T7/clade-learn/PRAXIS-2 && .venv/bin/python -m pytest tests/test_e2e_skill_matrix.py -k run_archetype -v`
Expected: FAIL(无 run_archetype)。

- [ ] **Step 3: 实现 run_skill + run_archetype + main**(在 `scripts/e2e_skill_matrix.py` 末尾追加)

```python
async def _default_executor(name: str, brain: str | None, inputs: dict) -> dict:
    """真 executor:调 SkillExecTool。返回 ToolResult 的 dict 形态。"""
    from praxis2.tools.skill_exec import SkillExecTool
    tool = SkillExecTool()
    payload = {"name": name, "inputs": inputs}
    if brain:
        payload["brain"] = brain
    res = await tool.run(payload)
    return {"ok": res.ok, "value": res.value, "error": res.error}


async def run_archetype(archetype: str, *, green_archetype: str | None = None, executor=None) -> list[dict]:
    """逐 skill 跑 + 分类 + 写报告 + 回写 CSV。executor 默认真 SkillExec(单测注入 fake)。"""
    executor = executor or _default_executor
    loaded = load_inputs(archetype, green_archetype=green_archetype)
    results = []
    verdicts = {}
    for skill, cfg in loaded.items():
        brain = cfg.get("brain")
        if cfg.get("skip"):
            verdict, tr = SKIPPED, {"skipped": True}
        else:
            tr = await executor(skill, brain, cfg.get("inputs", {}))
            verdict = classify_verdict(tr, cfg.get("contract_keys", []))
        verdicts[(brain, skill)] = verdict
        results.append({
            "skill": skill, "brain": brain, "verdict": verdict,
            "evidence": (tr.get("value") if isinstance(tr, dict) else None),
            "error": (tr.get("error") if isinstance(tr, dict) else None),
        })
    (AUDIT / f"e2e_results_{archetype}.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    update_inventory_csv(verdicts)
    return results


def main() -> int:
    import asyncio as _aio
    import sys
    if len(sys.argv) < 2:
        print("用法: e2e_skill_matrix.py <archetype> [green_archetype]", file=sys.stderr)
        return 2
    archetype = sys.argv[1]
    green = sys.argv[2] if len(sys.argv) > 2 else None
    results = _aio.run(run_archetype(archetype, green_archetype=green))
    counts = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print(f"[e2e:{archetype}] {counts}")
    for r in results:
        print(f"  {r['verdict']:9} {r['brain']}/{r['skill']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 跑测试确认绿 + 全量不回归**

Run: `cd /Volumes/T7/clade-learn/PRAXIS-2 && .venv/bin/python -m pytest tests/test_e2e_skill_matrix.py -v`
Expected: 全 PASS(7+3+1)。

- [ ] **Step 5: Commit**

```bash
cd /Volumes/T7/clade-learn/PRAXIS-2
git add scripts/e2e_skill_matrix.py tests/test_e2e_skill_matrix.py
git commit -m "feat(e2e): run_archetype 编排(注入式 executor)+ main + 报告落盘

逐 skill 经 SkillExec 真路径跑→分类→写 e2e_results_<archetype>.json + 回写 CSV。
单测用 fake executor 不依赖 SSH。

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: docking 输入集策展

**Files:**
- Create: `_audit/e2e_inputs/docking.json`

- [ ] **Step 1: 读 9 个 docking skill 的 SKILL.md 输入契约**

逐个 Read `brains/dock/skills/workflows/<skill>/SKILL.md` 的「输入契约」段(9 个:vina_gnina_dock / covalent_docking / flexpepdock_peptide / induced_fit_docking / pose_buster_validate / protein_na_docking / redock_benchmark / snugdock_antibody / af3_complex_predict)。注意 drug brain 也有 vina_gnina_dock(green_skills 里 dock+drug 都有),本切片只跑 dock brain 的。

- [ ] **Step 2: 写 docking.json**

按各 SKILL.md 契约填**真 payload**,受体统一用 staging 上将固化的 `~/data1/praxis2-e2e-inputs/1iep.pdb`(Task5 放置;Abl 激酶+imatinib STI 晶体配体,供 autobox/redock),ligand 用 imatinib SMILES `Cc1ccc(cc1Nc2nccc(n2)c3cccnc3)NC(=O)c4ccc(cc4)CN5CCN(CC5)C`。结构示例:

```json
{
  "vina_gnina_dock": {
    "brain": "dock",
    "contract_keys": ["poses", "best_pose", "vina_best_affinity_kcal_per_mol"],
    "inputs": {"receptor_pdb": "/home/zkyd/data1/praxis2-e2e-inputs/1iep.pdb",
               "ligand_smiles": "Cc1ccc(cc1Nc2nccc(n2)c3cccnc3)NC(=O)c4ccc(cc4)CN5CCN(CC5)C",
               "num_modes": 9, "exhaustiveness": 8, "seed": 42, "simulate": false}
  },
  "redock_benchmark": {
    "brain": "dock",
    "contract_keys": ["...按 SKILL.md 填..."],
    "inputs": {"receptor_pdb": "/home/zkyd/data1/praxis2-e2e-inputs/1iep.pdb", "...": "...", "simulate": false}
  },
  "induced_fit_docking": {"brain": "dock", "skip": false, "contract_keys": ["..."],
    "inputs": {"...": "...", "simulate": false}, "_note": "预期 N-A:Schrödinger 商业软件"},
  "af3_complex_predict": {"brain": "dock", "skip": true, "contract_keys": ["..."],
    "inputs": {"...": "...", "simulate": false}, "_note": "GPU 权重重型,本轮 skip(标 SKIPPED)"}
}
```
要求:① 9 个 skill 全列;② 每个 `contract_keys` 取自该 SKILL.md 输出契约的 2-3 个核心 key;③ `inputs` 按各自输入契约填(不止 receptor/ligand,缺啥补啥,如 box_center/peptide_seq/na_pdb 等);④ 重型(af3)`skip:true`,商业(induced_fit)给输入但预期 N-A;⑤ JSON 合法。

- [ ] **Step 3: 验 JSON 合法 + load_inputs 能读全**

Run:
```
cd /Volumes/T7/clade-learn/PRAXIS-2 && .venv/bin/python -c "import json; d=json.load(open('_audit/e2e_inputs/docking.json')); print('skills:', sorted(d)); assert len(d)==9"
```
Expected: 打印 9 个 skill 名,无异常。

- [ ] **Step 4: Commit**

```bash
cd /Volumes/T7/clade-learn/PRAXIS-2
git add _audit/e2e_inputs/docking.json
git commit -m "feat(e2e): docking 切片输入集(9 skill 真 payload,1iep 受体+imatinib)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: staging e2e — 受体固化 + 真跑 docking + 回写(controller 亲做)

**Files:** `_audit/skill_real_impl_inventory.csv`(回写)+ `_audit/e2e_results_docking.json`(产出)

- [ ] **Step 1: 本地全量回归**

Run: `cd /Volumes/T7/clade-learn/PRAXIS-2 && .venv/bin/python -m pytest tests/ --ignore=tests/integration -q --tb=no --junit-xml=/tmp/r.xml >/dev/null 2>&1; echo EXIT=$?; .venv/bin/python -c "import xml.etree.ElementTree as ET; r=ET.parse('/tmp/r.xml').getroot(); s=r if r.tag=='testsuite' else r[0]; print(s.attrib)"`
Expected: failures=0 errors=0。**不绿不上 staging**。

- [ ] **Step 2: 固化受体 1iep.pdb 到 staging**

本地取(Mac 可达 RCSB):`curl -sS -o /tmp/1iep.pdb https://files.rcsb.org/download/1IEP.pdb`(失败则换 staging `~/data1/mzy/DL-masif/1.pdb` 等带 HETATM 的受体,相应改 docking.json receptor_pdb)。
→ `ssh zkyd@10.102.106.53 'mkdir -p ~/data1/praxis2-e2e-inputs'` → `rsync /tmp/1iep.pdb zkyd@10.102.106.53:~/data1/praxis2-e2e-inputs/`。
确认受体含晶体配体 HETATM(vina autobox 需):`ssh zkyd@.53 "grep -c '^HETATM' ~/data1/praxis2-e2e-inputs/1iep.pdb"`(>0)。

- [ ] **Step 3: rsync harness + 输入集到 staging**

```
rsync scripts/e2e_skill_matrix.py zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/scripts/
ssh zkyd@10.102.106.53 'mkdir -p ~/data1/mzy/PRAXIS-2/_audit/e2e_inputs'
rsync _audit/e2e_inputs/docking.json zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/_audit/e2e_inputs/
rsync _audit/green_skills.json _audit/skill_real_impl_inventory.csv zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/_audit/
```

- [ ] **Step 4: staging 真跑 docking**

```
ssh zkyd@10.102.106.53 'cd ~/data1/mzy/PRAXIS-2 && source ~/praxis2.env && PYTHONPATH=$PWD ~/software/miniconda3/envs/praxis2/bin/python scripts/e2e_skill_matrix.py docking dock'
```
(⚠ PYTHONPATH=$PWD 必须;harness 内 SkillExecTool 读 ~/praxis2.env 的 SSH 三件套真跑。)

- [ ] **Step 5: 验结果 + 拷回**

- 验:输出 counts 含 `DONE_real >= 1`;**vina_gnina_dock = DONE_real**(`e2e_results_docking.json` 里 evidence 含真 poses + 真 affinity,`diagnostics.simulated` 非 True);induced_fit=N-A、af3=SKIPPED 符合预期;其余诚实 verdict。
- 若 vina 没到 DONE_real → systematic-debugging(查 receptor HETATM/gnina PATH/env),不硬改判定。
- 拷回:`rsync zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/_audit/e2e_results_docking.json _audit/` + `rsync zkyd@.53:~/data1/mzy/PRAXIS-2/_audit/skill_real_impl_inventory.csv _audit/`。
- 确认 CSV 里 vina(+ 真可跑的)已升 DONE_real。

---

## Task 6: 文档回填 + 收尾 commit(controller 亲做)

**Files:** `TEST-AGENT-FRAMEWORK.md`(改)+ 提交 e2e 产物

- [ ] **Step 1: 回填 TEST-AGENT-FRAMEWORK.md**

在 §5.3 GAP-E2E-1 下加「本轮结果(docking,日期)」:9 skill 的 verdict 分布 + DONE_real 名单 + harness 用法(`PYTHONPATH=$PWD python scripts/e2e_skill_matrix.py <archetype> <green_archetype>`)+ 输入集位置 `_audit/e2e_inputs/`。

- [ ] **Step 2: 提交 e2e 产物 + 文档**

```bash
cd /Volumes/T7/clade-learn/PRAXIS-2
git add _audit/skill_real_impl_inventory.csv _audit/e2e_results_docking.json TEST-AGENT-FRAMEWORK.md
git commit -m "docs(e2e): docking 切片真执行结果回填 + CSV DONE_real 扩面

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 3: push + memory**

```bash
git push origin main
```
更新 memory:新建/追加记 GAP-E2E docking 切片结果 + harness 可复用(后续 archetype 只补输入集)。

---

## Self-Review(against spec)

**1. Spec coverage:**
- spec §3.1 输入集 → Task 4 ✓ · §3.2 四分类 classify_verdict → Task 1 ✓ · §3.3 执行(SkillExec real/超时/幂等/skip)→ Task 3(_default_executor/skip)✓ · §3.4 CSV 回写 → Task 2 ✓
- spec §4 单测 → Task 1-3(纯逻辑 + fake executor)✓;e2e → Task 5 ✓
- spec §5 DoD 全项 → Task 1-6 覆盖 ✓
- 受体具体 PDB(spec 留 plan 定)→ Task 5 Step2 定 1IEP ✓

**2. Placeholder scan:** 代码步骤均含完整代码。Task 4 的 contract_keys/inputs 具体值需读各 SKILL.md 填(运行期事实,给了结构 + 要求,非 placeholder);Task 5/6 是部署/回填 SOP。

**3. Type consistency:** `classify_verdict(tool_result, contract_keys)`(T1)与 run_archetype 调用(T3)一致 ✓;`load_inputs(archetype, green_archetype=)`(T2)与 run_archetype/main(T3)一致 ✓;`update_inventory_csv(verdicts: {(brain,skill):verdict})`(T2)与 run_archetype 构造的 verdicts(T3)一致 ✓;`INVENTORY_CSV`/`AUDIT`/`GREEN_SKILLS` 常量跨 task 一致 ✓;verdict 常量 DONE_real/N-A/RED/ERROR/SKIPPED 一致 ✓。

**风险点:** ① `SkillExec` 真跑 value 形态需 Task1 Step3 现场确认(已标注,测试随实现同契约调整);② docking.json 的 inputs 必须严格对各 SKILL.md 契约(payload 错会误判 RED/ERROR,Task4 强调逐个读);③ 1IEP receptor 须含晶体配体 HETATM(Task5 Step2 校验)。

---

## Execution Handoff

Plan 已存 `docs/superpowers/plans/2026-06-05-gap-e2e-skill-verification.md`。沿用 **subagent-driven-development**:Task 1-4 fresh subagent per task + 两阶段 review;Task 5-6(staging 真跑/回填)controller 亲做。
