# 确定性 report.md 渲染器 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让每次 query(含 offline 零 LLM)都产出一份标准结构化、可下载的 `report.md`,补上「offline 无 Markdown 报告」这一缺口。

**Architecture:** 新增纯函数渲染器 `praxis_virtualcell/io/report_markdown.py`(只读现有确定性 artifact,不调 LLM、无 wall-clock、可复现),接线进 `JobStore`(每次落盘 report.md)→ FastAPI(`GET …/markdown`)→ React(下载按钮)→ CLI(经 JobStore 自动获得)。

**Tech Stack:** Python 3.13 / pytest / FastAPI(PlainTextResponse)/ React+TS+Vite。

**铁律(每步必守):** 渲染器不 import/调用 LLM;不用 `datetime.now()`/随机(可复现);缺字段标 `N/A` 不编造;不重算 verdict/reliability/prediction(只读)。动后端跑 `PYTHONPATH=<repo> .venv/bin/python -m pytest praxis_virtualcell/tests` 无回归。commit 前 `find docs praxis_virtualcell praxis_vc_api praxis_vc_react -name '._*' -delete`。commit 末尾 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`。仅本地 commit,不 push。

---

## 数据契约(实现前必读,取自真实 offline job 采样)

`job` dict(= `JobStore.load()` 返回或 save 时组装的等价结构)相关键:
- `job["report"]`(= structured_report):`request_id, abstain(bool), reliability("high"/"medium"/"low"), prediction(dict|None, 如 {"delta":[0.3]}), models_used(list[str], 如 ["MockLinear","MockCPA","MockGEARS"]), models_rejected(list[str]), models_failed(list[str]), abstain_reasons(list[str]), downgrade_reasons(list[str], 元素带 "downgrade:" 前缀), failed_checks(list[str]), model_disagreement(dict|None), critic_violations(list), caution_flags(dict, = ortholog_cautions), learned_reliability(dict|None), provenance(dict)`。
- `job["report"]["learned_reliability"]`:`reliability_mode, fallback(bool), reliability_score(float), abstain_score, abstain_decision("accept"/"downgrade"/"abstain"), features_used, model_version, feature_schema_version, artifact_sha256, abstain_artifact_sha256`。
- `job["report"]["provenance"]`:`n_messages(int), rules_referenced(list[str]), rules_hit(list[str]), ortholog_cautions(dict), rejection_reasons(dict: 模型名→原因), models_used/rejected/failed, critic_violations`。
- `job["request"]`(或 `job["candidate_request"]`):`request_id, species, cell_type, perturbation_type, perturbation_targets(list), task_type`。
- `job["mode"]`:save 时组装可得("offline"/"llm_assisted");load 旧 job 可能无 → `N/A`。
- mock predictor 判定:模型名以 `Mock` 开头(如 MockLinear)。

verdict 派生:`abstain=True → abstain`;否则 `downgrade_reasons 非空 → downgrade`;否则 `caution_flags 非空 → caution`;否则 `accept`。

---

## Task 1: report_markdown 渲染器(纯函数,TDD)

**Files:**
- Create: `praxis_virtualcell/io/report_markdown.py`
- Test: `praxis_virtualcell/tests/test_report_markdown.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_report_markdown.py`:

```python
"""确定性 report.md 渲染器测试:9 段齐全 / verdict 正确 / abstain 不出数值 /
缺字段防御 / 无 LLM / 可复现。"""
from praxis_virtualcell.io.report_markdown import render_report_md

_ACCEPT = {
    "mode": "offline",
    "request": {"request_id": "ahr_k562_demo", "species": "human", "cell_type": "K562",
                "perturbation_type": "gene", "perturbation_targets": ["AHR"],
                "task_type": "predict_delta_expression"},
    "report": {
        "request_id": "ahr_k562_demo", "abstain": False, "reliability": "high",
        "prediction": {"delta": [0.3]},
        "models_used": ["MockLinear", "MockCPA", "MockGEARS"],
        "models_rejected": [], "models_failed": [],
        "abstain_reasons": [], "downgrade_reasons": [], "failed_checks": [],
        "model_disagreement": {"score": 0.33, "metric": "pairwise_cosine_distance", "triggered": False},
        "critic_violations": [], "caution_flags": {},
        "learned_reliability": {"reliability_mode": "learned_with_rule_fallback", "fallback": False,
                                "reliability_score": 0.7167, "abstain_decision": "accept",
                                "model_version": "reliability_v0.3.0", "feature_schema_version": "v0.3.0",
                                "artifact_sha256": "abc123", "abstain_artifact_sha256": "def456"},
        "provenance": {"n_messages": 21, "rules_referenced": ["r1.yaml", "r2.yaml"],
                       "rules_hit": [], "ortholog_cautions": {}, "rejection_reasons": {}},
    },
}

_ABSTAIN = {
    "mode": "offline",
    "request": {"request_id": "noab", "species": "human", "cell_type": None,
                "perturbation_type": "gene", "perturbation_targets": [],
                "task_type": "predict_delta_expression"},
    "report": {"request_id": "noab", "abstain": True, "reliability": "low", "prediction": None,
               "models_used": [], "models_rejected": [], "models_failed": [],
               "abstain_reasons": ["no_perturbation_specified"], "downgrade_reasons": [],
               "failed_checks": [], "model_disagreement": None, "critic_violations": [],
               "caution_flags": {}, "learned_reliability": None,
               "provenance": {"n_messages": 5, "rules_referenced": [], "rules_hit": [],
                              "ortholog_cautions": {}, "rejection_reasons": {}}},
}

_DOWNGRADE = {
    "mode": "offline",
    "request": {"request_id": "dg", "species": "mouse", "cell_type": "T cell",
                "perturbation_type": "gene", "perturbation_targets": ["GATA1"],
                "task_type": "predict_delta_expression"},
    "report": {"request_id": "dg", "abstain": False, "reliability": "medium",
               "prediction": {"delta": [0.1]}, "models_used": ["MockLinear", "MockCPA"],
               "models_rejected": ["MockGEARS"], "models_failed": [],
               "abstain_reasons": [], "downgrade_reasons": ["downgrade:model_disagreement_too_high"],
               "failed_checks": ["model_disagreement"], "model_disagreement": {"score": 0.9, "triggered": True},
               "critic_violations": [], "caution_flags": {"GATA1": "ortholog_projected"},
               "learned_reliability": None,
               "provenance": {"n_messages": 18, "rules_referenced": ["r1.yaml"], "rules_hit": [],
                              "ortholog_cautions": {"GATA1": "ortholog_projected"},
                              "rejection_reasons": {"MockGEARS": "cell_type_unsupported"}}},
}

_SECTIONS = ["## 1. Question", "## 2. Cell Context", "## 3. Routing Decision",
             "## 4. Result Summary", "## 5. Governance Verdict",
             "## 6. Evidence and Provenance", "## 7. Biological Interpretation",
             "## 8. Limitations", "## 9. Reproducibility"]


def test_accept_has_all_nine_sections():
    md = render_report_md(_ACCEPT)
    assert md.startswith("# PRAXIS-VirtualCell Report")
    for s in _SECTIONS:
        assert s in md, f"缺段:{s}"
    assert "verdict: **accept**" in md
    assert "AHR" in md and "MockLinear" in md
    assert "0.3" in md  # prediction 数值出现


def test_abstain_shows_no_prediction_number():
    md = render_report_md(_ABSTAIN)
    assert "verdict: **abstain**" in md
    assert "弃权" in md
    assert "no_perturbation_specified" in md  # 出现在 Governance/Limitations
    # abstain 不得 dump prediction:无 json 代码块、无预测数值
    assert "```json" not in md
    assert "不产出预测数值" in md


def test_downgrade_reasons_in_output():
    md = render_report_md(_DOWNGRADE)
    assert "verdict: **downgrade**" in md
    assert "downgrade:model_disagreement_too_high" in md
    # 跨物种(mouse) + caution flags 应进 Limitations
    assert "mouse" in md


def test_mock_predictor_flagged_in_limitations():
    md = render_report_md(_ACCEPT)
    assert "mock" in md.lower()  # Limitations 标注 mock predictor 非真跑数值


def test_minimal_job_does_not_crash():
    md = render_report_md({"report": {}})
    assert "# PRAXIS-VirtualCell Report" in md
    assert "N/A" in md
    for s in _SECTIONS:
        assert s in md


def test_no_llm_import_in_module():
    import praxis_virtualcell.io.report_markdown as m
    src = open(m.__file__, encoding="utf-8").read()
    assert "agents_llm" not in src and "llm_client" not in src
    assert "import openai" not in src and "litellm" not in src


def test_reproducible_byte_identical():
    assert render_report_md(_ACCEPT) == render_report_md(_ACCEPT)
    assert render_report_md(_ABSTAIN) == render_report_md(_ABSTAIN)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_report_markdown.py -q`
Expected: FAIL(ModuleNotFoundError: praxis_virtualcell.io.report_markdown)

- [ ] **Step 3: 写渲染器实现**

写 `praxis_virtualcell/io/report_markdown.py`:

```python
"""确定性 report.md 渲染器(io 层,纯展示)。

铁律:纯确定性、不 import/调用任何 LLM、可复现(无 wall-clock/随机)、
不编造(缺字段标 N/A)、不重算科学决策(只读现有 artifact 字段)。
输入 = JobStore.load() 返回或 save 时组装的等价 job dict。
"""
from __future__ import annotations

import json

_NA = "N/A"


def _verdict(report: dict) -> str:
    """据现有字段派生单一 verdict(仅展示层聚合,不写回科学决策)。"""
    if report.get("abstain"):
        return "abstain"
    if report.get("downgrade_reasons"):
        return "downgrade"
    if report.get("caution_flags"):
        return "caution"
    return "accept"


def _fmt_list(items) -> str:
    xs = [str(x) for x in (items or []) if str(x).strip()]
    return ", ".join(xs) if xs else "—"


def _mocks(models) -> list[str]:
    return [m for m in (models or []) if str(m).lower().startswith("mock")]


def render_report_md(job: dict) -> str:
    job = job or {}
    report = job.get("report") or {}
    req = job.get("request") or job.get("candidate_request") or {}
    prov = report.get("provenance") or job.get("provenance") or {}
    learned = report.get("learned_reliability") or {}
    mode = job.get("mode") or _NA
    verdict = _verdict(report)
    abstain = bool(report.get("abstain"))
    lines: list[str] = []
    w = lines.append

    w("# PRAXIS-VirtualCell Report")
    w("")
    w(f"> mode: `{mode}` · verdict: **{verdict}** · "
      "LLM 未参与预测/治理决策;本报告由 structured artifact 确定性生成。")
    w("")

    # 1. Question
    w("## 1. Question")
    w("")
    w("原始自然语言:未记录(llm_meta 仅存 hash;offline 无 NL,以结构化任务为权威)。")
    w("")
    w("结构化任务:")
    w("")
    w(f"- species: `{req.get('species') or _NA}`")
    w(f"- cell_type: `{req.get('cell_type') or _NA}`")
    w(f"- perturbation_type: `{req.get('perturbation_type') or _NA}`")
    w(f"- perturbation_targets: `{_fmt_list(req.get('perturbation_targets'))}`")
    w(f"- task_type: `{req.get('task_type') or _NA}`")
    w("")

    # 2. Cell Context
    used = report.get("models_used") or []
    rejected = report.get("models_rejected") or []
    available = list(dict.fromkeys([*used, *rejected]))
    w("## 2. Cell Context")
    w("")
    w(f"- Species: `{req.get('species') or _NA}`")
    w(f"- Cell type / model system: `{req.get('cell_type') or _NA}`")
    w(f"- Available predictors: `{_fmt_list(available)}`")
    w(f"- Applicability: **{verdict}**")
    w("")

    # 3. Routing Decision
    rej_reasons = prov.get("rejection_reasons") or {}
    w("## 3. Routing Decision")
    w("")
    w(f"- models_used: `{_fmt_list(used)}`")
    if rejected:
        w("- models_rejected:")
        for m in rejected:
            w(f"  - `{m}` — {rej_reasons.get(m, '未记录原因')}")
    else:
        w("- models_rejected: —")
    w(f"- models_failed: `{_fmt_list(report.get('models_failed'))}`")
    dis = report.get("model_disagreement") or {}
    if dis:
        w(f"- model_disagreement: score=`{dis.get('score')}` · "
          f"metric=`{dis.get('metric', _NA)}` · triggered=`{dis.get('triggered')}`")
    w("")

    # 4. Result Summary
    w("## 4. Result Summary")
    w("")
    if abstain:
        w("系统已弃权(abstain),不产出预测数值。见 §5 治理裁决与 §8 边界。")
    else:
        pred = report.get("prediction")
        if pred is None:
            w("无 prediction 字段(N/A)。")
        else:
            w("prediction(确定性 runtime 产出,未经 LLM 修改):")
            w("")
            w("```json")
            w(json.dumps(pred, ensure_ascii=False, indent=2, sort_keys=True))
            w("```")
    w("")

    # 5. Governance Verdict
    w("## 5. Governance Verdict")
    w("")
    w(f"- Verdict: **{verdict}**")
    w(f"- reliability: `{report.get('reliability') or _NA}`")
    w(f"- abstain: `{abstain}`")
    if learned:
        w(f"- learned reliability_mode: `{learned.get('reliability_mode', _NA)}`")
        w(f"- learned reliability_score: `{learned.get('reliability_score', _NA)}`")
        w(f"- learned abstain_decision: `{learned.get('abstain_decision', _NA)}`")
        w(f"- learned fallback: `{learned.get('fallback', _NA)}`")
    ar = report.get("abstain_reasons") or []
    dr = report.get("downgrade_reasons") or []
    if ar:
        w(f"- abstain_reasons: {_fmt_list(ar)}")
    if dr:
        w(f"- downgrade_reasons: {_fmt_list(dr)}")
    fc = report.get("failed_checks") or []
    if fc:
        w(f"- failed_checks: {_fmt_list(fc)}")
    w("")

    # 6. Evidence and Provenance
    w("## 6. Evidence and Provenance")
    w("")
    w(f"- rules_referenced: `{_fmt_list(prov.get('rules_referenced'))}`")
    w(f"- rules_hit: `{_fmt_list(prov.get('rules_hit'))}`")
    w(f"- n_messages: `{prov.get('n_messages', _NA)}`")
    if learned:
        w(f"- reliability model_version: `{learned.get('model_version', _NA)}`")
        w(f"- feature_schema_version: `{learned.get('feature_schema_version', _NA)}`")
        w(f"- artifact_sha256: `{learned.get('artifact_sha256', _NA)}`")
        w(f"- abstain_artifact_sha256: `{learned.get('abstain_artifact_sha256', _NA)}`")
    w("")

    # 7. Biological Interpretation
    w("## 7. Biological Interpretation")
    w("")
    if abstain:
        w("系统弃权,不作生物学解读。")
    else:
        w("结构化结果见 §4;方向/幅度以 prediction 字段为准,不作超出证据的推断。")
    w("")
    w("_深入生物学解读需 LLM-assisted 模式(见 narrative_report.md);本段不越证据边界。_")
    w("")

    # 8. Limitations
    w("## 8. Limitations")
    w("")
    limits: list[str] = []
    for r in ar:
        limits.append(f"abstain: {r}")
    for r in dr:
        limits.append(f"降级: {r}")
    caution = report.get("caution_flags") or {}
    if caution:
        limits.append(f"caution flags: {json.dumps(caution, ensure_ascii=False, sort_keys=True)}")
    mk = _mocks(used)
    if mk:
        limits.append(f"预测数值来自 mock predictor({', '.join(mk)}),非真跑数值;"
                      "真数值预测在远端 A100(见 benchmarks/)。")
    sp = req.get("species")
    if sp and sp != "human":
        limits.append(f"非 human 物种({sp}):可能涉及跨物种投影/ortholog,"
                      "按降级解读,不当母种原生精度。")
    if not limits:
        limits.append("未触发 abstain/降级/caution;仍以 §6 证据强度为准,不过度承诺。")
    for x in limits:
        w(f"- {x}")
    w("")

    # 9. Reproducibility
    w("## 9. Reproducibility")
    w("")
    w(f"- request_id: `{report.get('request_id') or req.get('request_id') or _NA}`")
    w(f"- mode: `{mode}`")
    w("- llm_used_for_prediction: `False`(恒定:LLM 不碰预测)")
    w("- 复现命令:")
    w("")
    w("```bash")
    w("praxis-vc run --request <request.json> --mode offline --out runs/<id>")
    w("```")
    w("")

    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: 跑测试确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_report_markdown.py -q`
Expected: PASS(7 passed)

- [ ] **Step 5: commit**

```bash
find docs praxis_virtualcell praxis_vc_api praxis_vc_react -name '._*' -delete
git add praxis_virtualcell/io/report_markdown.py praxis_virtualcell/tests/test_report_markdown.py
git commit -m "feat(v0.6): 确定性 report.md 渲染器(纯函数,9段,可复现无LLM)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 2: JobStore 落盘 report.md(TDD)

**Files:**
- Modify: `praxis_virtualcell/io/job_store.py`(save 写 report.md;load 读 report_md)
- Test: `praxis_virtualcell/tests/test_report_markdown.py`(追加 JobStore 集成测试)

- [ ] **Step 1: 追加失败测试**

在 `test_report_markdown.py` 末尾追加:

```python
def test_jobstore_writes_and_loads_report_md(tmp_path):
    from praxis_virtualcell.io.job_store import JobStore
    store = JobStore(str(tmp_path / "runs"))
    result = {
        "structured_report": _ACCEPT["report"],
        "trace": [], "provenance": _ACCEPT["report"]["provenance"],
        "mode": "offline", "llm_enabled": False,
    }
    store.save("job1", request=_ACCEPT["request"], result=result)
    assert (tmp_path / "runs" / "job1" / "report.md").is_file()
    loaded = store.load("job1")
    assert "report_md" in loaded
    assert loaded["report_md"].startswith("# PRAXIS-VirtualCell Report")
    assert "verdict: **accept**" in loaded["report_md"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_report_markdown.py::test_jobstore_writes_and_loads_report_md -q`
Expected: FAIL(AssertionError:report.md 不存在 / 无 report_md 键)

- [ ] **Step 3: 改 JobStore.save 写 report.md**

`praxis_virtualcell/io/job_store.py`:在 `save` 的 `if result is not None:` 块内,`if result.get("narrative"):` 之后、`llm 元数据` 之前,插入:

```python
            # 确定性 Markdown 报告:每次都写(含 offline),与 LLM narrative 正交
            from praxis_virtualcell.io.report_markdown import render_report_md
            job_like = {
                "report": result.get("structured_report", {}),
                "request": request, "candidate_request": candidate,
                "trace": result.get("trace", []),
                "provenance": result.get("provenance", {}),
                "mode": result.get("mode"), "llm_enabled": result.get("llm_enabled"),
            }
            self._w(d, "report.md", render_report_md(job_like))
```

- [ ] **Step 4: 改 JobStore.load 读 report_md**

同文件 `load` 方法内,`nf = d / "narrative_report.md"` 那段之后追加:

```python
        rf = d / "report.md"
        if rf.is_file():
            out["report_md"] = rf.read_text(encoding="utf-8")
```

- [ ] **Step 5: 跑测试确认通过 + 全量无回归**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_report_markdown.py -q`
Expected: PASS(8 passed)

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 全绿(此前 223 passed 基线 + 新增,允许 25 skipped)

- [ ] **Step 6: commit**

```bash
find docs praxis_virtualcell praxis_vc_api praxis_vc_react -name '._*' -delete
git add praxis_virtualcell/io/job_store.py praxis_virtualcell/tests/test_report_markdown.py
git commit -m "feat(v0.6): JobStore 每次落盘确定性 report.md + load 透出 report_md

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 3: FastAPI `GET /api/reports/{id}/markdown`(TDD)

**Files:**
- Modify: `praxis_vc_api/services/runtime_service.py`(加 `report_markdown`)
- Modify: `praxis_vc_api/main.py`(加端点 + `markdown_url`)
- Test: `praxis_virtualcell/tests/test_api.py`(加 2 个用例)

- [ ] **Step 1: 写失败测试**

在 `praxis_virtualcell/tests/test_api.py` 末尾追加:

```python
def test_report_markdown(client):
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    jid = client.post("/api/jobs", json={"request": req, "mode": "offline"}).json()["job_id"]
    r = client.get(f"/api/reports/{jid}/markdown")
    assert r.status_code == 200
    assert "text/markdown" in r.headers["content-type"]
    assert "# PRAXIS-VirtualCell Report" in r.text
    assert "## 5. Governance Verdict" in r.text


def test_report_markdown_404(client):
    assert client.get("/api/reports/nope/markdown").status_code == 404
```

- [ ] **Step 2: 跑测试确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_api.py::test_report_markdown praxis_virtualcell/tests/test_api.py::test_report_markdown_404 -q`
Expected: FAIL(markdown 端点返回 404 或 Not Found)

- [ ] **Step 3: service 层加 `report_markdown`**

`praxis_vc_api/services/runtime_service.py`:在 `list_jobs` 之后追加:

```python
def report_markdown(job_id: str) -> str:
    """返回该 job 的确定性 report.md(优先读落盘,缺则现场重渲染)。只读。"""
    job = JobStore(RUNS_DIR).load(job_id)   # 缺失抛 FileNotFoundError
    md = job.get("report_md")
    if md:
        return md
    from praxis_virtualcell.io.report_markdown import render_report_md
    return render_report_md(job)
```

- [ ] **Step 4: main.py 加端点**

`praxis_vc_api/main.py`:改 import 行 `from fastapi.responses import PlainTextResponse`(加在 `from fastapi.staticfiles import StaticFiles` 之后);在 `provenance` 端点(`@app.get("/api/reports/{job_id}/provenance")` 那段)之后、React mount 注释之前,插入:

```python
@app.get("/api/reports/{job_id}/markdown", response_class=PlainTextResponse)
def report_markdown(job_id: str):
    """确定性 report.md(text/markdown)。历史 job 缺 .md 时现场重渲染。"""
    try:
        return PlainTextResponse(svc.report_markdown(job_id), media_type="text/markdown")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="job not found") from e
```

并在 `report(job_id)` 端点返回 dict 里加一行 `"markdown_url": f"/api/reports/{job_id}/markdown",`(放在 `"provenance_url"` 之后)。

- [ ] **Step 5: 跑测试确认通过 + API 全量无回归**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_api.py -q`
Expected: PASS(原 8 + 新 2 = 10 passed)

- [ ] **Step 6: commit**

```bash
find docs praxis_virtualcell praxis_vc_api praxis_vc_react -name '._*' -delete
git add praxis_vc_api/services/runtime_service.py praxis_vc_api/main.py praxis_virtualcell/tests/test_api.py
git commit -m "feat(v0.6): API GET /api/reports/{id}/markdown 返回确定性 report.md

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 4: React 下载 report.md 按钮

**Files:**
- Modify: `praxis_vc_react/src/api.ts`(加 `getReportMarkdown`)
- Modify: `praxis_vc_react/src/views/ResultView.tsx`(加导出按钮 + `markdown_url` 类型)

- [ ] **Step 1: api.ts 加文本拉取方法**

`praxis_vc_react/src/api.ts`:在 `ReportResult` 接口内加一行 `markdown_url: string;`(放在 `provenance_url` 之后)。在文件末尾 `getProvenance` 之后追加:

```typescript
// report.md 为纯文本(text/markdown),不走 JSON 解析,单独 fetch。
export async function getReportMarkdown(jobId: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/reports/${encodeURIComponent(jobId)}/markdown`);
  if (!res.ok) throw new Error(`API ${res.status}: report.md 获取失败`);
  return res.text();
}
```

- [ ] **Step 2: ResultView.tsx 加导出按钮**

`praxis_vc_react/src/views/ResultView.tsx`:第 1 处 import 里把 `getProvenance,` 那组加入 `getReportMarkdown,`(加在 `getProvenance,` 之后)。在「导出 narrative.md」按钮(`</button>` 结束,即 `onClick={() => download(\`${jobId}_narrative.md\`...` 那个 button)之后,插入:

```tsx
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() =>
              getReportMarkdown(jobId)
                .then((md) => download(`${jobId}_report.md`, md, "text/markdown"))
                .catch((e: unknown) => setErr(String(e)))
            }
          >
            导出 report.md
          </button>
```

- [ ] **Step 3: 构建验证**

Run: `cd praxis_vc_react && npm run build`
Expected: 构建通过(tsc + vite build 无 error),产出 `praxis_vc_react/dist/`

- [ ] **Step 4: commit**

```bash
find docs praxis_virtualcell praxis_vc_api praxis_vc_react -name '._*' -delete
git add praxis_vc_react/src/api.ts praxis_vc_react/src/views/ResultView.tsx
git commit -m "feat(v0.6): React ResultView 加\"导出 report.md\"按钮 + api.getReportMarkdown

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 5: CLI 验证 + 文档 + dist 刷新

**Files:**
- Verify: `praxis_virtualcell/cli.py`(已走 JobStore,`run`/`ask --yes --out` 自动含 report.md,无需改码)
- Modify: `docs/USAGE-llm-interface.md`(输出章节加 report.md)
- Rebuild: `praxis_vc_react/dist/`(让 serve 同源托管新前端)

- [ ] **Step 1: CLI 端到端验证(手动)**

Run:
```bash
PYTHONPATH=$PWD .venv/bin/python -m praxis_virtualcell.cli run \
  --request examples/ahr_k562.json --mode offline --out runs/_smoke_report_md
ls runs/_smoke_report_md/report.md && head -5 runs/_smoke_report_md/report.md
```
Expected: `report.md` 存在,首行 `# PRAXIS-VirtualCell Report`;确认 9 段。之后 `rm -rf runs/_smoke_report_md`。

- [ ] **Step 2: 更新 USAGE 文档**

`docs/USAGE-llm-interface.md`:「输出(runs/<job_id>/)」章节,把 artifact 列表更新为包含 `report.md`(确定性 Markdown 报告,offline 也有,9 段结构),并说明与 `narrative_report.md`(LLM 可选散文)正交。API 端点表加一行 `GET /api/reports/{id}/markdown` → 「确定性 report.md 下载」。

具体编辑:把第 68 行附近的输出说明改为:
```markdown
## 输出(runs/<job_id>/)
`request.json` · `report.json` · `report.md`(**确定性 Markdown 报告,9 段,offline 也有**)· `trace.json` · `provenance.json` · `narrative_report.md`(可选 LLM 散文,与 report.md 正交)· `llm_meta.json`(仅 hash)。
```
并在 endpoint 表(第 40 行附近)追加一行:
```markdown
| `GET /api/reports/{id}/markdown` | 确定性 report.md(text/markdown,可下载) |
```

- [ ] **Step 3: 刷新 React dist**

Run: `cd praxis_vc_react && npm run build`
Expected: 构建通过,`dist/` 更新(含导出 report.md 按钮的前端)。

- [ ] **Step 4: 全量测试无回归**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 全绿(≥ 226 passed,25 skipped)

- [ ] **Step 5: commit**

```bash
find docs praxis_virtualcell praxis_vc_api praxis_vc_react -name '._*' -delete
git add docs/USAGE-llm-interface.md praxis_vc_react/dist
git commit -m "docs(v0.6): USAGE 补 report.md 说明 + 刷新 React dist(含导出按钮)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## 验收(全部完成后)

1. `praxis-vc run … --out runs/x` → `runs/x/report.md` 存在,9 段齐全,offline 无 LLM。
2. `GET /api/reports/{id}/markdown` → 200 + `text/markdown` + 含 `## 5. Governance Verdict`。
3. React 结果页有「导出 report.md」按钮,点击下载。
4. `pytest praxis_virtualcell/tests` 全绿无回归;`npm run build` 通过。
5. 渲染器纯确定性、可复现(同 job 两次渲染逐字节相同)、不 import LLM。

## 停止条件(硬门,停下汇报)

1. `git push`(仅本地 commit)。
2. 需改 governance/predictors/reliability 核心科学逻辑(本 slice 只加展示层,不碰)。
3. `pytest` 回归或 `npm run build` 失败且无法自解。
4. 需新增付费/外部服务。
5. Task 1–5 全完成 → 停,简短汇报。
