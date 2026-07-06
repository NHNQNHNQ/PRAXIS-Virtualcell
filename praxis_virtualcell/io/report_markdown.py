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

    # 模块路由(Phase 8:module_plan 展示层。读现有 provenance.module_plan,缺则 N/A,不重算/不打乱 9 段编号)
    mp = prov.get("module_plan") or {}
    w("### 模块路由(Module Routing)")
    w("")
    if not mp:
        w(f"- primary module: `{_NA}`(无 module_plan:abstain/不可路由 job 或旧记录)")
    else:
        w(f"- primary module: `{mp.get('primary', _NA)}` · "
          f"secondary: `{_fmt_list(mp.get('secondary'))}` · "
          f"overall_verdict: **{mp.get('overall_verdict', _NA)}**")
        entries = mp.get("entries") or []
        if entries:
            w("- 模块裁决(module · role · verdict · mismatch):")
            for e in entries:
                w(f"  - `{e.get('module', _NA)}` · {e.get('role', _NA)} · "
                  f"**{e.get('verdict', _NA)}**"
                  + (f" · mismatch=`{e.get('mismatch')}`" if e.get('mismatch') else ""))
    w("")
    w("_模块路由是治理层之上的逻辑视图(读 module_plan artifact);M1–M8 映射现有 engine,"
      "verdict 取 route/species/mismatch 最保守,不重写裁决。_")
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

    # 证据记录(Phase 5:evidence_level E0–E5,附 §6 之后。缺键标 N/A,不崩)
    ev = prov.get("evidence_level") or {}
    w("### 证据记录(Evidence Record)")
    w("")
    w(f"- evidence_level: `{ev.get('level', _NA)}`")
    w(f"- ood_signal: `{ev.get('ood_signal', _NA)}`")
    w(f"- rationale: `{_fmt_list(ev.get('rationale'))}`")
    w(f"- aligned_with_disposition: `{ev.get('aligned_with_disposition', _NA)}`")
    w("")
    w("_证据等级是治理层之上的薄映射(读现有 reliability/OOD/disagreement 信号),"
      "不重写裁决;E2=in-domain accept 与现有 disposition 对齐。_")
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

    # 验证计划(Phase 5:learning_queue,附 §8 之后。advisory 建议下一步实验,不改裁决。缺键标 N/A)
    lq = prov.get("learning_queue") or {}
    lq_items = lq.get("items") or []
    w("### 验证计划(Validation Plan · 主动学习建议)")
    w("")
    if not lq_items:
        w(f"- 优先实验候选:`{_NA}`(无可执行候选或缺 learning_queue)")
    else:
        w("- 优先实验候选(按 information gain 降序,advisory 不改裁决):")
        for it in lq_items[:5]:            # top-5
            w(f"  - `{it.get('candidate', _NA)}` · module=`{it.get('module', _NA)}` · "
              f"information_gain=`{it.get('information_gain', _NA)}` · "
              f"drivers={_fmt_list(it.get('drivers'))}")
    lq_notes = lq.get("notes") or []
    if lq_notes:
        w(f"- notes: {_fmt_list(lq_notes)}")
    w("")
    w("_验证计划是主动学习的 advisory 产物:建议下一步该测什么(用 disagreement/OOD/证据等级排序),"
      "不碰 prediction/verdict 终决/provenance ledger。_")
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
