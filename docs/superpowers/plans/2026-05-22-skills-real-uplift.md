# 152 skill 全量 real-uplift 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 152 个 `brains/*/skills/workflows/*/run.py` 从 archetype 模板升级为真实现 — `simulate()` 按 SKILL.md 输出契约产出正确 schema 的合成数据;`real()` 按对应 host_env 内的工具实现或明确标 N/A 保留 simulate;新增 pytest 全量覆盖。

**Architecture:** 单 commit per brain × 13 brain,逐批闭环。先建可复用工具(parser/generator/helper + pytest 框架),再 brain-by-brain 跑生成器 + 人工修边角 + 跑 pytest + 抽样在 .53 真 E2E。SSH 调度归 `SkillExecTool` 管,run.py 内只用本地 `subprocess`。

**Tech Stack:** Python 3.11+ (project env)、pytest、subprocess、re/json/pathlib、ssh + conda envs on `zkyd@10.102.106.53`、4× A100-40GB。

---

## File Structure

**新建工具(一次性,Phase A):**
- `brains/_common/lib/__init__.py` — package init
- `brains/_common/lib/run_tool.py` — 本地 subprocess wrapper(dry-host 模式支持)
- `scripts/uplift/__init__.py`
- `scripts/uplift/parse_skill_outputs.py` — 抽 152 个 SKILL.md 的"## 输出契约" json
- `scripts/uplift/fix_skill_outputs.py` — 给无 outputs 段的补一个、修 json 解析失败的
- `scripts/uplift/parity_per_brain.py` — 单 brain 出 GREEN/RED-EASY/N/A 分桶
- `scripts/uplift/regen_simulate.py` — 按 SKILL.md outputs 重写 run.py 的 simulate()
- `scripts/uplift/regen_real.py` — 给 GREEN/RED-EASY 桶生成 real() 骨架;N/A 桶写 stub
- `scripts/uplift/uplift_brain.py` — 一键跑完单 brain 的所有 4 个 generator,产 dry-run diff
- `tests/skills/__init__.py`
- `tests/skills/conftest.py` — 公用 fixture(parametrize 注入 skill 路径)
- `tests/skills/test_run_py_smoke.py` — 152 个 simulate 路径 smoke(替代 /tmp 临时脚本)
- `tests/skills/test_schema_match.py` — simulate 输出 vs SKILL.md outputs MATCH 校验

**每 brain 新建(Phase B,13 次):**
- `tests/skills/test_<brain>.py` — 该 brain 所有 skill 的 simulate + real(dry-host)smoke

**每 skill 修改(Phase B,152 次):**
- `brains/<brain>/skills/workflows/<skill>/SKILL.md` — outputs 段补/规整
- `brains/<brain>/skills/workflows/<skill>/run.py` — simulate() + real() 重写

**Phase C 收尾:**
- `VERSION-STATUS-v1.0.md` — 汇总
- `_audit/parity_v1_per_brain.json` — fresh 分桶结果

---

## Phase A:通用工具(Task 0-6)

### Task 0:run_tool subprocess helper

**Files:**
- Create: `brains/_common/lib/__init__.py`
- Create: `brains/_common/lib/run_tool.py`
- Test: `tests/skills/test_run_tool.py`

- [ ] **Step 0.1: Write the failing test**

Create `tests/skills/__init__.py`(空)和 `tests/skills/test_run_tool.py`:

```python
"""run_tool 的契约:超时/非 0/异常都不抛,结构化返回。"""
import json
import os
import subprocess

import pytest

from brains._common.lib.run_tool import run_tool


def test_success_returns_ok_true():
    r = run_tool(["python3", "-c", "print('hi')"])
    assert r["ok"] is True
    assert r["returncode"] == 0
    assert r["stdout"].strip() == "hi"
    assert r["wall_sec"] >= 0


def test_nonzero_exit_returns_ok_false():
    r = run_tool(["python3", "-c", "import sys; sys.exit(7)"])
    assert r["ok"] is False
    assert r["returncode"] == 7
    assert "error" in r


def test_command_not_found_returns_structured_err():
    r = run_tool(["definitely-not-a-real-binary-xyz123"])
    assert r["ok"] is False
    assert "error" in r
    assert r["returncode"] == -1


def test_timeout_returns_structured_err():
    r = run_tool(["python3", "-c", "import time; time.sleep(5)"], timeout=1)
    assert r["ok"] is False
    assert "timeout" in r["error"].lower()


def test_stdin_passthrough():
    r = run_tool(["python3", "-c", "import sys; print(sys.stdin.read().upper())"],
                 stdin=b"hello")
    assert r["ok"] is True
    assert r["stdout"].strip() == "HELLO"


def test_dry_host_mode_returns_mock(monkeypatch):
    monkeypatch.setenv("PRAXIS_SKILL_DRY_HOST", "1")
    r = run_tool(["should-never-actually-run"])
    assert r["ok"] is True
    assert r.get("dry") is True
```

- [ ] **Step 0.2: Run test to verify it fails**

```
pytest tests/skills/test_run_tool.py -v
```

Expected: 6 failures, ModuleNotFoundError: `brains._common.lib.run_tool`.

- [ ] **Step 0.3: Create package files**

```bash
mkdir -p brains/_common/lib
test -f brains/_common/__init__.py || touch brains/_common/__init__.py
touch brains/_common/lib/__init__.py
```

- [ ] **Step 0.4: Write run_tool.py**

Create `brains/_common/lib/run_tool.py`:

```python
"""run_tool: subprocess.run 的容错包装。

run.py 内 real() 用它跑工具二进制,不必关心 SSH 调度
(SSH 由上层 SkillExecTool 负责)。所有异常→结构化 dict,绝不向上抛。
"""
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
    """跑 cmd,容错返回 dict。

    返回字段:
      ok: bool             — returncode == 0
      returncode: int      — -1 表示工具不存在
      stdout: str
      stderr: str
      wall_sec: float
      cmd: str             — 用于诊断的 shell-quoted 命令
      error: str?          — ok=False 时给一行人类可读说明
      dry: bool?           — PRAXIS_SKILL_DRY_HOST=1 时为 True
    """
    cmd_str = " ".join(shlex.quote(x) for x in cmd)

    if os.environ.get("PRAXIS_SKILL_DRY_HOST") == "1":
        return {
            "ok": True, "returncode": 0, "stdout": "", "stderr": "",
            "wall_sec": 0.0, "cmd": cmd_str, "dry": True,
        }

    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd, capture_output=True, input=stdin,
            timeout=timeout, cwd=cwd, env=env, check=False,
        )
    except FileNotFoundError as e:
        return {
            "ok": False, "returncode": -1, "stdout": "", "stderr": str(e),
            "wall_sec": round(time.time() - t0, 3), "cmd": cmd_str,
            "error": f"binary not found: {cmd[0]!r}",
        }
    except subprocess.TimeoutExpired as e:
        return {
            "ok": False, "returncode": -1, "stdout": e.stdout or "", "stderr": e.stderr or "",
            "wall_sec": round(time.time() - t0, 3), "cmd": cmd_str,
            "error": f"timeout after {timeout}s",
        }
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False, "returncode": -1, "stdout": "", "stderr": "",
            "wall_sec": round(time.time() - t0, 3), "cmd": cmd_str,
            "error": f"subprocess error: {e!r}",
        }

    out = {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or b"").decode("utf-8", "replace") if isinstance(proc.stdout, bytes) else (proc.stdout or ""),
        "stderr": (proc.stderr or b"").decode("utf-8", "replace") if isinstance(proc.stderr, bytes) else (proc.stderr or ""),
        "wall_sec": round(time.time() - t0, 3),
        "cmd": cmd_str,
    }
    if not out["ok"]:
        out["error"] = f"non-zero exit {proc.returncode}"
    return out
```

- [ ] **Step 0.5: Run tests pass**

```
pytest tests/skills/test_run_tool.py -v
```

Expected: 6 passed.

- [ ] **Step 0.6: Commit**

```bash
git add brains/_common/__init__.py brains/_common/lib/ tests/skills/__init__.py tests/skills/test_run_tool.py
git -c commit.gpgsign=false commit -m "feat(uplift): run_tool subprocess helper + PRAXIS_SKILL_DRY_HOST mock 模式"
```

---

### Task 1:SKILL.md outputs 解析器

**Files:**
- Create: `scripts/uplift/__init__.py`
- Create: `scripts/uplift/parse_skill_outputs.py`
- Test: `tests/skills/test_parse_skill_outputs.py`

- [ ] **Step 1.1: Write the failing test**

Create `tests/skills/test_parse_skill_outputs.py`:

```python
import json
from pathlib import Path

from scripts.uplift.parse_skill_outputs import parse_outputs_block, parse_skill_md


def test_parses_clean_json_block(tmp_path: Path):
    md = tmp_path / "SKILL.md"
    md.write_text(
        '---\nname: foo\nhost_env: bar\n---\n\n'
        '## 输出契约\n\n```json\n{"a": 1, "b": {"c": 2}}\n```\n'
    )
    out = parse_skill_md(md)
    assert out["verdict"] == "OK"
    assert out["keys"] == ["a", "b"]
    assert out["schema"]["a"] == 1


def test_handles_trailing_commas():
    body = '{"x": 1, "y": [1, 2,],}'
    obj, err = parse_outputs_block(body)
    assert err is None
    assert obj == {"x": 1, "y": [1, 2]}


def test_handles_line_comments():
    body = '{"x": 1,  // comment\n  "y": 2 }'
    obj, err = parse_outputs_block(body)
    assert err is None
    assert obj == {"x": 1, "y": 2}


def test_reports_missing_section(tmp_path: Path):
    md = tmp_path / "SKILL.md"
    md.write_text('---\nname: foo\n---\n\n# Title\n\nNo outputs section here.\n')
    out = parse_skill_md(md)
    assert out["verdict"] == "MISSING_SECTION"
    assert out["keys"] is None
```

- [ ] **Step 1.2: Run test to verify it fails**

```
pytest tests/skills/test_parse_skill_outputs.py -v
```

Expected: 4 failures, ModuleNotFoundError on `scripts.uplift.parse_skill_outputs`.

- [ ] **Step 1.3: Write parse_skill_outputs.py**

Create `scripts/uplift/__init__.py`(空)和 `scripts/uplift/parse_skill_outputs.py`:

```python
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


def parse_outputs_block(body: str) -> tuple[dict | None, str | None]:
    """容忍 trailing comma 与 // 行注释,返回 (obj, err)。"""
    cleaned = _LINE_COMMENT_RE.sub("", body)
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
```

- [ ] **Step 1.4: Run tests pass**

```
pytest tests/skills/test_parse_skill_outputs.py -v
```

Expected: 4 passed.

- [ ] **Step 1.5: Smoke-run scanner across all 152 SKILL.md**

```
python3 -m scripts.uplift.parse_skill_outputs
```

Expected: stdout JSON, by_verdict 含 OK/PARSE_ERR/MISSING_SECTION 三类计数,合计 152。

- [ ] **Step 1.6: Commit**

```bash
git add scripts/uplift/__init__.py scripts/uplift/parse_skill_outputs.py tests/skills/test_parse_skill_outputs.py _audit/skill_outputs_parsed.json
git -c commit.gpgsign=false commit -m "feat(uplift): SKILL.md outputs 解析器 (容忍 trailing-comma/comment)"
```

---

### Task 2:SKILL.md outputs 修复器

**Files:**
- Create: `scripts/uplift/fix_skill_outputs.py`
- Test: `tests/skills/test_fix_skill_outputs.py`

- [ ] **Step 2.1: Write the failing test**

Create `tests/skills/test_fix_skill_outputs.py`:

```python
from pathlib import Path

from scripts.uplift.fix_skill_outputs import (
    default_schema_for_archetype,
    insert_outputs_section,
)


def test_default_schema_docking_has_poses():
    s = default_schema_for_archetype("docking", brain="dock", skill="foo_dock")
    assert "poses" in s
    assert "best_affinity" in s
    assert s["skill_id"] == "foo_dock"


def test_default_schema_unknown_archetype_falls_back_to_generic():
    s = default_schema_for_archetype("brand-new-thing", brain="x", skill="y")
    assert "ok" in s
    assert "skill_id" in s


def test_insert_outputs_section_appends_when_missing(tmp_path: Path):
    md = tmp_path / "SKILL.md"
    md.write_text("---\nname: foo\n---\n\n## 一句话原则\n\n做事.\n")
    out = insert_outputs_section(md, {"a": 1, "b": "x"})
    assert out["action"] == "inserted"
    txt = md.read_text()
    assert "## 输出契约" in txt
    assert '"a": 1' in txt


def test_insert_outputs_section_skips_when_present(tmp_path: Path):
    md = tmp_path / "SKILL.md"
    md.write_text("---\nname: foo\n---\n\n## 输出契约\n\n```json\n{\"a\": 1}\n```\n")
    out = insert_outputs_section(md, {"z": 9})
    assert out["action"] == "skipped"
```

- [ ] **Step 2.2: Run test to verify it fails**

```
pytest tests/skills/test_fix_skill_outputs.py -v
```

Expected: 4 failures.

- [ ] **Step 2.3: Write fix_skill_outputs.py**

Create `scripts/uplift/fix_skill_outputs.py`:

```python
"""给 SKILL.md 没'## 输出契约'段的补一个 archetype 合理默认,
   对 json 解析失败的(trailing comma/comment)原地清洗后回写。"""
from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.uplift.parse_skill_outputs import (
    _LINE_COMMENT_RE,
    _SECTION_RE,
    _TRAILING_COMMA_RE,
    parse_skill_md,
)

ARCHETYPE_DEFAULTS: dict[str, dict] = {
    "docking": {
        "skill_id": "",
        "receptor": "",
        "ligand": "",
        "best_affinity": 0.0,
        "poses": [{"rank": 1, "affinity_kcal_per_mol": 0.0, "pose_path": ""}],
        "runtime_sec": 0.0,
        "diagnostics": {},
    },
    "structure_predict": {
        "skill_id": "",
        "sequence": "",
        "model_path": "",
        "plddt_mean": 0.0,
        "ptm": 0.0,
        "n_residues": 0,
        "runtime_sec": 0.0,
        "diagnostics": {},
    },
    "mutation_scan": {
        "skill_id": "",
        "wt_score": 0.0,
        "scan_csv": "",
        "top_mutations": [{"position": 1, "from_aa": "A", "to_aa": "V", "ddg": 0.0}],
        "diagnostics": {},
    },
    "msa_conservation": {
        "skill_id": "",
        "msa_path": "",
        "n_sequences": 0,
        "conservation_csv": "",
        "diagnostics": {},
    },
    "omics_scrna": {
        "skill_id": "",
        "matrix_path": "",
        "n_cells_post_qc": 0,
        "cluster_sizes": {},
        "marker_genes_per_cluster": {},
        "umap_png": "",
        "diagnostics": {},
    },
    "microbiome_pipeline": {
        "skill_id": "",
        "n_samples": 0,
        "taxonomy_table": "",
        "diversity_metrics": {"shannon": 0.0, "observed_otus": 0},
        "diagnostics": {},
    },
    "drug": {
        "skill_id": "",
        "n_compounds": 0,
        "best_score": 0.0,
        "compound_csv": "",
        "diagnostics": {},
    },
    "pharma": {
        "skill_id": "",
        "n_compounds": 0,
        "admet_csv": "",
        "diagnostics": {},
    },
    "cryo": {
        "skill_id": "",
        "n_particles": 0,
        "resolution_a": 0.0,
        "map_path": "",
        "diagnostics": {},
    },
    "crispr": {
        "skill_id": "",
        "n_guides": 0,
        "guides_csv": "",
        "best_guide": {"seq": "", "cfd_score": 0.0, "mit_score": 0.0},
        "diagnostics": {},
    },
    "mhc_epitope": {
        "skill_id": "",
        "n_epitopes": 0,
        "epitopes_csv": "",
        "diagnostics": {},
    },
    "fetcher": {
        "skill_id": "",
        "fetched": [],
        "diagnostics": {},
    },
    "generic": {
        "ok": True,
        "skill_id": "",
        "result": {},
        "diagnostics": {},
    },
}


def default_schema_for_archetype(archetype: str, *, brain: str, skill: str) -> dict:
    base = ARCHETYPE_DEFAULTS.get(archetype, ARCHETYPE_DEFAULTS["generic"])
    out = json.loads(json.dumps(base))  # deep copy
    out["skill_id"] = skill
    out.setdefault("diagnostics", {})["brain"] = brain
    out["diagnostics"]["archetype"] = archetype
    return out


def insert_outputs_section(path: Path, schema: dict) -> dict:
    txt = path.read_text(encoding="utf-8", errors="replace")
    if _SECTION_RE.search(txt):
        return {"path": str(path), "action": "skipped"}
    json_body = json.dumps(schema, indent=2, ensure_ascii=False)
    block = f"\n\n## 输出契约\n\n```json\n{json_body}\n```\n"
    new_txt = txt.rstrip() + block
    path.write_text(new_txt, encoding="utf-8")
    return {"path": str(path), "action": "inserted"}


def clean_existing_json_section(path: Path) -> dict:
    """若 outputs 段存在但 json 块解析失败,清洗 trailing-comma/comment 后回写。"""
    info = parse_skill_md(path)
    if info["verdict"] != "PARSE_ERR":
        return {"path": str(path), "action": "no-op", "verdict": info["verdict"]}
    txt = path.read_text(encoding="utf-8", errors="replace")
    m = _SECTION_RE.search(txt)
    if not m:
        return {"path": str(path), "action": "no-op"}
    body = m.group(1)
    cleaned = _LINE_COMMENT_RE.sub("", body)
    cleaned = _TRAILING_COMMA_RE.sub(r"\1", cleaned)
    try:
        json.loads(cleaned)
    except Exception:
        return {"path": str(path), "action": "still-broken"}
    new_txt = txt[: m.start(1)] + cleaned.strip() + "\n" + txt[m.end(1):]
    path.write_text(new_txt, encoding="utf-8")
    return {"path": str(path), "action": "cleaned"}


def _archetype_of(run_py: Path) -> str:
    if not run_py.is_file():
        return "generic"
    txt = run_py.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'ARCHETYPE\s*=\s*"([^"]+)"', txt)
    return m.group(1) if m else "generic"


def fix_one(skill_dir: Path) -> list[dict]:
    md = skill_dir / "SKILL.md"
    run_py = skill_dir / "run.py"
    if not md.is_file():
        return [{"path": str(skill_dir), "action": "no-skill-md"}]
    results = []
    archetype = _archetype_of(run_py)
    brain = skill_dir.parent.parent.parent.name
    skill = skill_dir.name
    results.append(clean_existing_json_section(md))
    schema = default_schema_for_archetype(archetype, brain=brain, skill=skill)
    results.append(insert_outputs_section(md, schema))
    return results


def fix_brain(brain: str, root: Path = Path("brains")) -> list[dict]:
    base = root / brain / "skills" / "workflows"
    if not base.is_dir():
        return []
    out = []
    for sd in sorted(base.iterdir()):
        if sd.is_dir():
            out.extend(fix_one(sd))
    return out


if __name__ == "__main__":
    import sys
    brain = sys.argv[1] if len(sys.argv) > 1 else None
    if brain:
        rows = fix_brain(brain)
    else:
        rows = []
        for bd in sorted(Path("brains").iterdir()):
            if bd.is_dir():
                rows.extend(fix_brain(bd.name))
    by_a = {}
    for r in rows:
        by_a[r.get("action")] = by_a.get(r.get("action"), 0) + 1
    print(json.dumps({"total": len(rows), "by_action": by_a}, indent=2, ensure_ascii=False))
```

- [ ] **Step 2.4: Run tests pass**

```
pytest tests/skills/test_fix_skill_outputs.py -v
```

Expected: 4 passed.

- [ ] **Step 2.5: Commit**

```bash
git add scripts/uplift/fix_skill_outputs.py tests/skills/test_fix_skill_outputs.py
git -c commit.gpgsign=false commit -m "feat(uplift): SKILL.md outputs 修复器 — archetype defaults + 清洗 trailing-comma"
```

---

### Task 3:simulate() 重写生成器

**Files:**
- Create: `scripts/uplift/regen_simulate.py`
- Test: `tests/skills/test_regen_simulate.py`

- [ ] **Step 3.1: Write the failing test**

Create `tests/skills/test_regen_simulate.py`:

```python
import json
import subprocess
import sys
import textwrap
from pathlib import Path

from scripts.uplift.regen_simulate import build_simulate_fn, rewrite_run_py


def test_build_simulate_for_flat_schema():
    code = build_simulate_fn({"x": 1, "y": "abc", "z": 0.5})
    assert "def simulate" in code
    # 应能 exec 并产 dict
    ns = {}
    exec(code, ns)
    out = ns["simulate"]({})
    assert set(out.keys()) >= {"x", "y", "z"}


def test_build_simulate_for_nested_schema_preserves_keys():
    schema = {"poses": [{"rank": 1, "score": -8.0}], "best_affinity": -8.0}
    code = build_simulate_fn(schema)
    ns = {}
    exec(code, ns)
    out = ns["simulate"]({})
    assert "poses" in out and "best_affinity" in out
    assert isinstance(out["poses"], list)
    assert "rank" in out["poses"][0]


def test_rewrite_run_py_replaces_only_simulate(tmp_path: Path):
    rp = tmp_path / "run.py"
    rp.write_text(textwrap.dedent('''
        ARCHETYPE = "X"
        BRAIN = "b"
        SKILL = "s"

        def simulate(payload):
            return {"old": True}

        def real(payload):
            return {"ok": False, "error": "stub"}

        def main():
            pass
    ''').lstrip())
    res = rewrite_run_py(rp, {"new_key": 1})
    assert res["action"] == "rewritten"
    txt = rp.read_text()
    assert "def real(payload)" in txt and 'error": "stub"' in txt
    assert "new_key" in txt
    # 真跑一下 simulate
    proc = subprocess.run([sys.executable, str(rp)],
                          input=json.dumps({"simulate": True}),
                          capture_output=True, text=True, timeout=5)
    assert proc.returncode == 0
    j = json.loads(proc.stdout)
    assert "new_key" in j
```

- [ ] **Step 3.2: Run test to verify it fails**

```
pytest tests/skills/test_regen_simulate.py -v
```

Expected: 3 failures.

- [ ] **Step 3.3: Write regen_simulate.py**

Create `scripts/uplift/regen_simulate.py`:

```python
"""按 SKILL.md outputs schema 重写 run.py 的 simulate() 函数体。

策略:
- 用 SKILL.md 'outputs' 段的 json 例子当 dummy 模板;遇 nested list 取首个元素当模板。
- 保留 run.py 的 real()/main() 不动;只换 def simulate(payload) 整段。
- 若 SKILL.md 没解析出 schema(verdict != OK),跳过(由 Task 2 修复后再来一遍)。
"""
from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path

from scripts.uplift.parse_skill_outputs import parse_skill_md


def _py_literal(value, indent: int = 4) -> str:
    """schema value → 合法 python literal(带 random 随机扰动 hook)。"""
    return repr(value)


def build_simulate_fn(schema: dict) -> str:
    """根据 schema 生成 def simulate(payload) 源码。

    schema 是从 SKILL.md outputs json 解出来的 dict。生成的 simulate 直接返回 deep-copy
    后的 schema(由 archetype 默认值组成,已经是合理 dummy)。覆盖 skill_id 用 SKILL 常量。
    """
    schema_literal = repr(schema)
    body = textwrap.dedent(f'''
    def simulate(payload):
        """auto-generated by regen_simulate.py — outputs schema 来自 SKILL.md."""
        import copy
        import random
        random.seed(int(payload.get("seed", 42)) if isinstance(payload, dict) else 42)
        out = copy.deepcopy({schema_literal})
        if isinstance(out, dict):
            out.setdefault("diagnostics", {{}})
            if isinstance(out["diagnostics"], dict):
                out["diagnostics"].update({{
                    "simulated": True,
                    "archetype": ARCHETYPE,
                    "brain": BRAIN,
                    "skill": SKILL,
                }})
            if "skill_id" in out and not out["skill_id"]:
                out["skill_id"] = SKILL
        return out
    ''').lstrip()
    return body


_SIM_FN_RE = re.compile(
    r"^def\s+simulate\s*\([^)]*\)\s*:\s*\n(?:[ \t].*\n|\s*\n)+",
    re.M,
)


def rewrite_run_py(run_py: Path, schema: dict, *, hand_written_lines_threshold: int = 200) -> dict:
    if not run_py.is_file():
        return {"path": str(run_py), "action": "no-run-py"}
    txt = run_py.read_text(encoding="utf-8", errors="replace")
    # 保护 hand-written 长 run.py(如 vina_gnina_dock 317 行)
    if txt.count("\n") > hand_written_lines_threshold:
        return {"path": str(run_py), "action": "skip-hand-written", "lines": txt.count("\n")}
    new_fn = build_simulate_fn(schema)
    m = _SIM_FN_RE.search(txt)
    if not m:
        return {"path": str(run_py), "action": "no-simulate-fn"}
    new_txt = txt[: m.start()] + new_fn + "\n" + txt[m.end():]
    run_py.write_text(new_txt, encoding="utf-8")
    return {"path": str(run_py), "action": "rewritten"}


def regen_brain(brain: str, brains_root: Path = Path("brains")) -> list[dict]:
    base = brains_root / brain / "skills" / "workflows"
    results = []
    for sd in sorted(base.iterdir()):
        if not sd.is_dir():
            continue
        md = sd / "SKILL.md"
        rp = sd / "run.py"
        info = parse_skill_md(md)
        if info["verdict"] != "OK":
            results.append({"path": str(rp), "action": "skip-no-schema", "verdict": info["verdict"]})
            continue
        results.append(rewrite_run_py(rp, info["schema"]))
    return results


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if target:
        rows = regen_brain(target)
    else:
        rows = []
        for bd in sorted(Path("brains").iterdir()):
            if bd.is_dir():
                rows.extend(regen_brain(bd.name))
    by_a = {}
    for r in rows:
        by_a[r.get("action")] = by_a.get(r.get("action"), 0) + 1
    print(json.dumps({"total": len(rows), "by_action": by_a}, indent=2, ensure_ascii=False))
```

- [ ] **Step 3.4: Run tests pass**

```
pytest tests/skills/test_regen_simulate.py -v
```

Expected: 3 passed.

- [ ] **Step 3.5: Commit**

```bash
git add scripts/uplift/regen_simulate.py tests/skills/test_regen_simulate.py
git -c commit.gpgsign=false commit -m "feat(uplift): simulate() 按 SKILL.md outputs schema 重写器"
```

---

### Task 4:fresh parity 分桶器

**Files:**
- Create: `scripts/uplift/parity_per_brain.py`

- [ ] **Step 4.1: Write parity_per_brain.py**

Create `scripts/uplift/parity_per_brain.py`:

```python
"""单 brain 分桶器:把所有 skill 分成 GREEN/RED-EASY/N_A 三桶。

GREEN  : SKILL.md frontmatter 的 host_env 出现在 host conda env 列表里;
RED-EASY: host_env 在白名单(可现场装的小 cli 工具)且 host 上无;
N_A    : host_env 是商业软件或数据缺(license-blocked)。

判据维护在常量字典里;数据源是 _audit/host_inventory.json(可被 fresh 抓的覆盖)。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# 这些 conda env 名一旦缺失,标 RED-EASY(我们可以现装)
INSTALLABLE_HINTS = {"praxis-protein", "praxis-microbiome", "praxis-omics"}

# 这些标 N/A(商业/数据/license 受限)
LICENSE_BLOCKED_HINTS = {"schrodinger", "maestro", "moe", "discovery_studio", "icm", "rosetta_commercial"}


def _frontmatter_field(md_path: Path, key: str) -> str | None:
    txt = md_path.read_text(encoding="utf-8", errors="replace")
    if not txt.startswith("---"):
        return None
    for ln in txt.splitlines()[1:]:
        if ln.strip() == "---":
            break
        if ln.startswith(f"{key}:"):
            return ln.split(":", 1)[1].strip()
    return None


def classify(skill_dir: Path, host_envs: set[str]) -> dict:
    md = skill_dir / "SKILL.md"
    host_env = _frontmatter_field(md, "host_env") if md.is_file() else None
    skill = skill_dir.name
    brain = skill_dir.parent.parent.parent.name

    if host_env and host_env.lower() in LICENSE_BLOCKED_HINTS:
        bucket = "N_A"
        reason = f"host_env {host_env} 是商业受限工具"
    elif not host_env:
        bucket = "N_A"
        reason = "SKILL.md 未声明 host_env"
    elif host_env in host_envs:
        bucket = "GREEN"
        reason = f"host_env {host_env} 在 .53 conda envs"
    elif host_env in INSTALLABLE_HINTS:
        bucket = "RED_EASY"
        reason = f"host_env {host_env} 缺,可后续 conda create"
    else:
        bucket = "N_A"
        reason = f"host_env {host_env} 未识别且不在可装白名单"
    return {"brain": brain, "skill": skill, "host_env": host_env, "bucket": bucket, "reason": reason}


def load_host_envs(inventory_json: Path = Path("_audit/host_inventory.json")) -> set[str]:
    if not inventory_json.is_file():
        return set()
    data = json.loads(inventory_json.read_text())
    return set(data.get("conda_envs", []) or [])


def classify_brain(brain: str, brains_root: Path = Path("brains")) -> list[dict]:
    base = brains_root / brain / "skills" / "workflows"
    host_envs = load_host_envs()
    rows = []
    for sd in sorted(base.iterdir()):
        if sd.is_dir():
            rows.append(classify(sd, host_envs))
    return rows


if __name__ == "__main__":
    import sys
    brain = sys.argv[1] if len(sys.argv) > 1 else None
    if brain:
        rows = classify_brain(brain)
    else:
        rows = []
        for bd in sorted(Path("brains").iterdir()):
            if bd.is_dir():
                rows.extend(classify_brain(bd.name))
    by_b = {}
    for r in rows:
        by_b[r["bucket"]] = by_b.get(r["bucket"], 0) + 1
    print(json.dumps({"total": len(rows), "by_bucket": by_b}, indent=2, ensure_ascii=False))
    out_path = Path("_audit/parity_v1_per_brain.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    print(f"wrote {out_path}", file=__import__("sys").stderr)
```

- [ ] **Step 4.2: Smoke run**

```
python3 -m scripts.uplift.parity_per_brain
```

Expected: stdout JSON,总计 152,by_bucket 含 GREEN/RED_EASY/N_A 三类计数。

- [ ] **Step 4.3: Commit**

```bash
git add scripts/uplift/parity_per_brain.py _audit/parity_v1_per_brain.json
git -c commit.gpgsign=false commit -m "feat(uplift): fresh parity 分桶 GREEN/RED_EASY/N_A"
```

---

### Task 5:real() 骨架生成器

**Files:**
- Create: `scripts/uplift/regen_real.py`
- Test: `tests/skills/test_regen_real.py`

- [ ] **Step 5.1: Write the failing test**

Create `tests/skills/test_regen_real.py`:

```python
import json
import subprocess
import sys
import textwrap
from pathlib import Path

from scripts.uplift.regen_real import build_real_fn_green, build_real_fn_na, rewrite_real


def test_real_na_returns_structured_dict():
    code = build_real_fn_na("license blocked: Schrodinger")
    ns = {"ARCHETYPE": "x", "BRAIN": "y", "SKILL": "z"}
    exec(code, ns)
    out = ns["real"]({})
    assert out["ok"] is False
    assert "N/A" in out["error"]


def test_real_green_calls_run_tool_and_returns_dict(monkeypatch):
    code = build_real_fn_green(archetype="generic")
    # 注入 run_tool stub
    ns = {
        "ARCHETYPE": "x", "BRAIN": "y", "SKILL": "z",
        "run_tool": lambda *a, **kw: {"ok": True, "stdout": "", "stderr": "", "returncode": 0, "wall_sec": 0.0, "cmd": ""},
    }
    exec(code, ns)
    out = ns["real"]({})
    assert isinstance(out, dict)
    assert "diagnostics" in out


def test_rewrite_real_replaces_only_real_fn(tmp_path: Path):
    rp = tmp_path / "run.py"
    rp.write_text(textwrap.dedent('''
        ARCHETYPE = "generic"
        BRAIN = "b"
        SKILL = "s"

        def simulate(payload):
            return {"a": 1}

        def real(payload):
            return {"ok": False, "error": "old stub"}

        def main():
            pass
    ''').lstrip())
    res = rewrite_real(rp, bucket="N_A", reason="test reason")
    assert res["action"] == "rewritten"
    txt = rp.read_text()
    assert "def simulate" in txt and 'a": 1' in txt  # simulate untouched
    assert "test reason" in txt
```

- [ ] **Step 5.2: Run test to verify it fails**

```
pytest tests/skills/test_regen_real.py -v
```

Expected: 3 failures.

- [ ] **Step 5.3: Write regen_real.py**

Create `scripts/uplift/regen_real.py`:

```python
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
            import sys
            sys.path.insert(0, "/home/zkyd/data1/mzy/praxis2-brains")
            from _common.lib.run_tool import run_tool

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
        out = {"ok": True, "skill_id": SKILL, "result": "placeholder; replace with real parse", "diagnostics": diagnostics}
        return out
    ''').lstrip()


_REAL_FN_RE = re.compile(
    r"^def\s+real\s*\([^)]*\)\s*:\s*\n(?:[ \t].*\n|\s*\n)+",
    re.M,
)


def rewrite_real(run_py: Path, *, bucket: str, reason: str = "", archetype: str = "generic") -> dict:
    if not run_py.is_file():
        return {"path": str(run_py), "action": "no-run-py"}
    txt = run_py.read_text(encoding="utf-8", errors="replace")
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


def regen_brain(brain: str, brains_root: Path = Path("brains")) -> list[dict]:
    parity_path = Path("_audit/parity_v1_per_brain.json")
    if not parity_path.is_file():
        return [{"action": "no-parity", "hint": "run parity_per_brain first"}]
    parity = {f"{r['brain']}/{r['skill']}": r for r in json.loads(parity_path.read_text())}
    base = brains_root / brain / "skills" / "workflows"
    rows = []
    for sd in sorted(base.iterdir()):
        if not sd.is_dir():
            continue
        key = f"{brain}/{sd.name}"
        p = parity.get(key)
        if not p:
            rows.append({"skill": key, "action": "skip-no-parity"})
            continue
        # 已是 DONE_real 的(只有 vina_gnina_dock 当前),跳
        if (sd / "run.py").is_file():
            txt = (sd / "run.py").read_text()
            if "skill-real-placeholder" not in txt and "N/A —" not in txt and "echo-like" not in txt:
                # 看起来已经是 hand-written real(行数 > 200 是个粗略 heuristic)
                lc = txt.count("\n")
                if lc > 200:
                    rows.append({"skill": key, "action": "skip-hand-written", "lines": lc})
                    continue
        rows.append(rewrite_real(sd / "run.py", bucket=p["bucket"], reason=p.get("reason", ""),
                                 archetype=p.get("archetype", "generic")))
    return rows


if __name__ == "__main__":
    import sys
    brain = sys.argv[1] if len(sys.argv) > 1 else None
    if brain:
        rows = regen_brain(brain)
    else:
        rows = []
        for bd in sorted(Path("brains").iterdir()):
            if bd.is_dir():
                rows.extend(regen_brain(bd.name))
    by_a = {}
    for r in rows:
        by_a[r.get("action")] = by_a.get(r.get("action"), 0) + 1
    print(json.dumps({"total": len(rows), "by_action": by_a}, indent=2, ensure_ascii=False))
```

- [ ] **Step 5.4: Run tests pass**

```
pytest tests/skills/test_regen_real.py -v
```

Expected: 3 passed.

- [ ] **Step 5.5: Commit**

```bash
git add scripts/uplift/regen_real.py tests/skills/test_regen_real.py
git -c commit.gpgsign=false commit -m "feat(uplift): real() 骨架生成器 (GREEN echo placeholder / N_A 结构化兜底)"
```

---

### Task 6:per-brain 公共 pytest 框架

**Files:**
- Create: `tests/skills/conftest.py`
- Create: `tests/skills/test_run_py_smoke.py`
- Create: `tests/skills/test_schema_match.py`

- [ ] **Step 6.1: Write conftest fixtures**

Create `tests/skills/conftest.py`:

```python
"""公共 fixture:列出所有 skill,按 brain 参数化。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BRAINS_ROOT = Path(__file__).resolve().parents[2] / "brains"


def _list_skills(brain: str | None = None) -> list[Path]:
    out: list[Path] = []
    for bd in sorted(BRAINS_ROOT.iterdir()):
        if not bd.is_dir() or bd.name.startswith("."):
            continue
        if brain and bd.name != brain:
            continue
        wf = bd / "skills" / "workflows"
        if not wf.is_dir():
            continue
        for sd in sorted(wf.iterdir()):
            if sd.is_dir() and (sd / "run.py").is_file():
                out.append(sd)
    return out


def all_skill_dirs() -> list[Path]:
    return _list_skills()


def brain_skill_dirs(brain: str) -> list[Path]:
    return _list_skills(brain)


def run_skill(skill_dir: Path, payload: dict, timeout: int = 15) -> dict:
    """跑 skill 的 run.py,返回 {exit, stdout_json, stderr}。"""
    rp = skill_dir / "run.py"
    proc = subprocess.run(
        [sys.executable, str(rp)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=timeout,
        env={**os.environ, "PRAXIS_SKILL_DRY_HOST": "1",
             "PYTHONPATH": str(BRAINS_ROOT.parent) + ":" + os.environ.get("PYTHONPATH", "")},
    )
    try:
        j = json.loads(proc.stdout) if proc.stdout.strip() else None
    except json.JSONDecodeError:
        j = None
    return {"exit": proc.returncode, "stdout_json": j, "stderr": proc.stderr}


@pytest.fixture
def skill_runner():
    return run_skill
```

- [ ] **Step 6.2: Write smoke test (全 152)**

Create `tests/skills/test_run_py_smoke.py`:

```python
"""全 152 skill simulate + real(dry-host) 路径 smoke 测试."""
from __future__ import annotations

import pytest

from tests.skills.conftest import all_skill_dirs, run_skill


@pytest.mark.parametrize("skill_dir", all_skill_dirs(), ids=lambda p: f"{p.parent.parent.parent.name}/{p.name}")
def test_simulate_path_ok(skill_dir):
    r = run_skill(skill_dir, {"simulate": True, "seed": 42})
    assert r["exit"] == 0, f"exit={r['exit']}, stderr={r['stderr'][:300]}"
    assert isinstance(r["stdout_json"], dict), f"non-dict stdout, stderr={r['stderr'][:300]}"


@pytest.mark.parametrize("skill_dir", all_skill_dirs(), ids=lambda p: f"{p.parent.parent.parent.name}/{p.name}")
def test_real_dry_host_path_ok(skill_dir):
    """PRAXIS_SKILL_DRY_HOST=1 时,real 应返 dict 不崩(可能是 N/A,也合法)。"""
    r = run_skill(skill_dir, {"simulate": False, "seed": 42})
    assert r["exit"] == 0, f"exit={r['exit']}, stderr={r['stderr'][:300]}"
    assert isinstance(r["stdout_json"], dict), f"stderr={r['stderr'][:300]}"
```

- [ ] **Step 6.3: Write schema match test**

Create `tests/skills/test_schema_match.py`:

```python
"""校验 simulate 输出 top-level keys ⊇ SKILL.md outputs 声明."""
from __future__ import annotations

import pytest

from scripts.uplift.parse_skill_outputs import parse_skill_md
from tests.skills.conftest import all_skill_dirs, run_skill


@pytest.mark.parametrize("skill_dir", all_skill_dirs(), ids=lambda p: f"{p.parent.parent.parent.name}/{p.name}")
def test_simulate_keys_match_skill_md(skill_dir):
    md = skill_dir / "SKILL.md"
    info = parse_skill_md(md)
    if info["verdict"] != "OK":
        pytest.skip(f"SKILL.md outputs not parseable: {info['verdict']}")
    r = run_skill(skill_dir, {"simulate": True, "seed": 42})
    assert isinstance(r["stdout_json"], dict)
    declared = set(info["keys"])
    actual = set(r["stdout_json"].keys())
    missing = declared - actual
    assert not missing, f"simulate missing declared keys: {sorted(missing)}"
```

- [ ] **Step 6.4: Make sure base smoke passes for current state**

```
pytest tests/skills/test_run_py_smoke.py -q -x 2>&1 | tail -20
```

Expected: 152 simulate tests pass(已经全绿)。real(dry-host) 152 个目前未必全绿(部分 run.py 没碰 run_tool),但接下来 Phase B 跑生成器后就齐了。先记录基线。

- [ ] **Step 6.5: Commit**

```bash
git add tests/skills/conftest.py tests/skills/test_run_py_smoke.py tests/skills/test_schema_match.py
git -c commit.gpgsign=false commit -m "test(skills): conftest + smoke (152 simulate + real dry-host) + schema-match parametrize"
```

---

## Phase B:13 个 brain 闭环 (Task 7-19)

**每个 brain 走相同 7 步,只是 brain 名变量不同。把 `<brain>` 替换为该 brain 名(`_common` / `cell` / `crispr` / `cryo` / `dock` / `drug` / `enzyme` / `immuno` / `md` / `microbiome` / `omics` / `pharma` / `protein`)。**

执行顺序(从最简单到最难):

| Task | brain | skills | 备注 |
|------|-------|--------|------|
| 7 | `_common` | 1 | nature_plot,最简单 |
| 8 | `md` | 8 | 中小 |
| 9 | `dock` | 13 | 已有 1 DONE_real 跳过 rewrite |
| 10 | `drug` | 12 | |
| 11 | `pharma` | 11 | |
| 12 | `crispr` | 11 | |
| 13 | `cell` | 11 | |
| 14 | `enzyme` | 11 | |
| 15 | `immuno` | 11 | |
| 16 | `cryo` | 11 | 多数 N_A |
| 17 | `omics` | 13 | |
| 18 | `protein` | 17 | 最大 |
| 19 | `microbiome` | 22 | 收尾 |

### Task 7-19 模板(对每个 brain 替换 `<brain>` 后执行)

**Files (per brain):**
- Modify: `brains/<brain>/skills/workflows/*/SKILL.md` (每个 skill)
- Modify: `brains/<brain>/skills/workflows/*/run.py` (每个 skill)
- Create: `tests/skills/test_<brain>.py`

- [ ] **Step <brain>.1: 跑 SKILL.md outputs 修复**

```
python3 -m scripts.uplift.fix_skill_outputs <brain>
```

Expected: stdout JSON, by_action 含 inserted / cleaned / skipped 等;预期 outputs 段补齐。

- [ ] **Step <brain>.2: 跑 simulate 重写**

```
python3 -m scripts.uplift.regen_simulate <brain>
```

Expected: stdout JSON, by_action 主体是 rewritten。

- [ ] **Step <brain>.3: 跑 fresh parity 分桶(只对该 brain)**

先确保 `_audit/parity_v1_per_brain.json` 已存在(Task 4 已生成)。若分桶判据需要按 brain 微调,直接重跑全量:

```
python3 -m scripts.uplift.parity_per_brain
```

- [ ] **Step <brain>.4: 跑 real() 骨架生成**

```
python3 -m scripts.uplift.regen_real <brain>
```

Expected: stdout JSON, by_action 含 rewritten / skip-hand-written 等。

- [ ] **Step <brain>.5: 写 per-brain 测试文件**

Create `tests/skills/test_<brain>.py`:

```python
"""brain=<brain> 全 skill simulate + real(dry-host) 闭环测试."""
from __future__ import annotations

import pytest

from scripts.uplift.parse_skill_outputs import parse_skill_md
from tests.skills.conftest import brain_skill_dirs, run_skill

SKILLS = brain_skill_dirs("<brain>")


@pytest.mark.parametrize("skill_dir", SKILLS, ids=lambda p: p.name)
def test_simulate_ok(skill_dir):
    r = run_skill(skill_dir, {"simulate": True, "seed": 1})
    assert r["exit"] == 0, r["stderr"][:300]
    assert isinstance(r["stdout_json"], dict)


@pytest.mark.parametrize("skill_dir", SKILLS, ids=lambda p: p.name)
def test_real_dry_host_ok(skill_dir):
    r = run_skill(skill_dir, {"simulate": False, "seed": 1})
    assert r["exit"] == 0, r["stderr"][:300]
    assert isinstance(r["stdout_json"], dict)


@pytest.mark.parametrize("skill_dir", SKILLS, ids=lambda p: p.name)
def test_simulate_matches_skill_md(skill_dir):
    info = parse_skill_md(skill_dir / "SKILL.md")
    if info["verdict"] != "OK":
        pytest.fail(f"SKILL.md outputs not parseable after fix: {info['verdict']}")
    r = run_skill(skill_dir, {"simulate": True})
    declared = set(info["keys"])
    actual = set(r["stdout_json"].keys())
    missing = declared - actual
    assert not missing, f"missing {sorted(missing)}"
```

- [ ] **Step <brain>.6: 跑该 brain 的全套测试**

```
pytest tests/skills/test_<brain>.py -q 2>&1 | tail -20
```

Expected: 该 brain 全 skill × 3 测试(simulate / real-dry / schema-match)全部 PASS。任何 FAIL 都要修(常见原因:SKILL.md 里 outputs 用了非法字段名;simulate generator 没处理某种 nested 形态)。

- [ ] **Step <brain>.7: Commit 该 brain**

```bash
git add brains/<brain>/ tests/skills/test_<brain>.py _audit/parity_v1_per_brain.json
git -c commit.gpgsign=false commit -m "feat(<brain>): N skills real-uplift — simulate schema fix + real() skeleton + tests"
```

(把 N 换成实际 skill 数;并把 commit message 里如有 N_A 桶/特殊 hand-written 跳过的 skill 加一行说明。)

---

## Phase C:收尾(Task 20)

### Task 20:全量回归 + VERSION-STATUS

**Files:**
- Create: `VERSION-STATUS-v1.0-uplift.md`

- [ ] **Step 20.1: 全量 pytest**

```
pytest tests/skills/ -q 2>&1 | tail -20
```

Expected: 全绿。 152 × (smoke + dry-real) + 152 schema-match - skip 数 = 应该 ~450 passed 或更多,0 failed。

- [ ] **Step 20.2: 跑全量 schema diff(重跑 Phase A 之前的 /tmp 脚本)**

```
python3 /tmp/schema_diff.py 2>&1 | head -20
```

Expected: by_verdict 应该 MATCH ≥ 140(允许少量 SKILL.md 仍有"NO_DECLARED" 残留,但 PARSE_ERR / DRIFT 应该为 0)。

- [ ] **Step 20.3: 跑全量 simulate smoke(原 /tmp 脚本)**

```
python3 /tmp/smoke_test_runs.py 2>&1 | head -10
```

Expected: 152 OK / 0 BAD.

- [ ] **Step 20.4: (可选)在 .53 真跑一个 GREEN skill**

需先 `export PRAXIS_SKILL_SSH_HOST=zkyd@10.102.106.53 PRAXIS_SKILL_REMOTE_BRAINS=/home/zkyd/data1/mzy/praxis2-brains PRAXIS_SKILL_CONDA_INIT=/home/zkyd/software/miniconda3/etc/profile.d/conda.sh`。然后:

```
python3 -c "
import asyncio, os
from praxis2.tools.skill_exec import SkillExecTool
t = SkillExecTool()
r = asyncio.run(t.run({'name': 'vina_gnina_dock', 'inputs': {'simulate': True}}))
print(r.ok, list(r.value.keys()) if r.value else None)
"
```

Expected: `True`,vina_gnina_dock 在 .53 跑出 dict。

- [ ] **Step 20.5: 同步 brains/ 到 .53**

```
rsync -avz --delete brains/ zkyd@10.102.106.53:/home/zkyd/data1/mzy/praxis2-brains/
```

- [ ] **Step 20.6: 写 VERSION-STATUS-v1.0-uplift.md**

Create `VERSION-STATUS-v1.0-uplift.md`,内容大纲:

```
# v1.0 uplift 现状

## 1. 数字
- 152 skill 全量覆盖
- N_A 桶: X 个 (license/data 受限,明细见 _audit/parity_v1_per_brain.json)
- GREEN/RED_EASY 桶: Y 个(已写 real placeholder,待人工接 CLI)
- DONE_real(hand-written): 1 (vina_gnina_dock)
- pytest tests/skills/: M passed / 0 failed

## 2. 13 brain commit 列表
(列每个 brain feat commit 的 SHA + 主题)

## 3. 已知 TODO(下个 milestone)
- GREEN 桶 Y 个 real() 替换 echo placeholder 为真实 CLI
- production /chat/stream 真打一发
- deploy/push_backend.sh 加 rsync brains/

## 4. 验收命令清单
(把 Step 20.1-20.4 的命令贴上)
```

- [ ] **Step 20.7: Commit + tag**

```bash
git add VERSION-STATUS-v1.0-uplift.md
git -c commit.gpgsign=false commit -m "docs(v1.0-uplift): 全量 152 skill real-uplift 现状文档"
git tag -a v1.0-uplift -m "v1.0 uplift: 152 skill simulate schema fix + real() skeleton"
```

---

## 风险与回退

- **某 brain 的 `pytest` 死活不绿**:不前进、不 commit;先 git diff 看是 SKILL.md 模板有怪字段(改 fix_skill_outputs 加特例)还是 simulate generator 不支持某种 nested(改 regen_simulate 加 case)。修完 generator 再重跑该 brain 的 Phase B。
- **regen_simulate 把现有 hand-written simulate 覆盖了**:vina_gnina_dock 这种 hand-written 的 brain 内 regen_real 已经有 line-count heuristic 跳过;simulate 端再加一个判据:文件 > 200 行就跳。Task 9(dock)前要先在 regen_simulate 加同样保护。
- **对话 token 超长**:Phase B 第 6 个 brain 后,启用 subagent-driven-development 把每剩余 brain 派给独立 subagent,只把它的 commit hash 拿回主线。
- **`_audit/parity_v1_per_brain.json` 与 host 实情漂移**:Phase C Step 20.4 真打 .53 时,N_A 桶里如果有错杀的(host 其实有),改 parity_per_brain 的 INSTALLABLE_HINTS 白名单后 reclassify + regen_real 该几个。
