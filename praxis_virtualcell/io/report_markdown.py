"""Deterministic Markdown report renderer.

Read persisted artifacts without calling an LLM, generating new scientific
evidence, or recomputing decisions. Missing fields are displayed as N/A.
"""
from __future__ import annotations

import json

_NA = "N/A"


def _verdict(report: dict) -> str:
    """Aggregate existing disposition fields for display without modifying scientific decisions."""
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
      "Predictions and governance are determined by the runtime; this report is rendered from structured artifacts.")
    w("")

    # 1. Question
    w("## 1. Question")
    w("")
    w("Original natural-language text is not stored. LLM metadata contains hashes; "
      "the structured request is authoritative.")
    w("")
    w("Structured request:")
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
    model_cautions = prov.get("model_cautions") or {}
    w("## 3. Routing Decision")
    w("")
    w(f"- models_used: `{_fmt_list(used)}`")
    if rejected:
        w("- models_rejected:")
        for m in rejected:
            reason = rej_reasons.get(m) or (
                ", ".join(model_cautions[m]) if model_cautions.get(m) else "Reason not recorded")
            w(f"  - `{m}` — {reason}")
    else:
        w("- models_rejected: —")
    w(f"- models_failed: `{_fmt_list(report.get('models_failed'))}`")
    dis = report.get("model_disagreement") or {}
    if dis:
        w(f"- model_disagreement: score=`{dis.get('score')}` · "
          f"metric=`{dis.get('metric', _NA)}` · triggered=`{dis.get('triggered')}`")
    w("")


    mp = prov.get("module_plan") or {}
    w("### Module Routing")
    w("")
    if not mp:
        w(f"- primary module: `{_NA}` (no module_plan: abstained, unroutable, or legacy job)")
    else:
        w(f"- primary module: `{mp.get('primary', _NA)}` · "
          f"secondary: `{_fmt_list(mp.get('secondary'))}` · "
          f"overall_verdict: **{mp.get('overall_verdict', _NA)}**")
        entries = mp.get("entries") or []
        if entries:
            w("- Module decisions (module · role · verdict · mismatch):")
            for e in entries:
                w(f"  - `{e.get('module', _NA)}` · {e.get('role', _NA)} · "
                  f"**{e.get('verdict', _NA)}**"
                  + (f" · mismatch=`{e.get('mismatch')}`" if e.get('mismatch') else ""))
    w("")
    w("_Module routing reads the stored module_plan artifact. M1–M8 map to existing engines; "
      "the most conservative route/species/mismatch verdict is displayed without overriding governance._")
    w("")

    # 4. Result Summary
    w("## 4. Result Summary")
    w("")
    if abstain:
        w("The system abstained and produces no prediction values. See §5 Governance Verdict and §8 Limitations.")
    else:
        pred = report.get("prediction")
        if pred is None:
            w("No prediction field is available (N/A).")
        else:
            w("Prediction (produced by the deterministic runtime and unmodified by an LLM):")
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


    ev = prov.get("evidence_level") or {}
    w("### Evidence Record")
    w("")
    w(f"- evidence_level: `{ev.get('level', _NA)}`")
    w(f"- ood_signal: `{ev.get('ood_signal', _NA)}`")
    w(f"- rationale: `{_fmt_list(ev.get('rationale'))}`")
    w(f"- aligned_with_disposition: `{ev.get('aligned_with_disposition', _NA)}`")
    w("")
    w("_Evidence levels map existing reliability/OOD/disagreement signals "
      "without overriding governance; E2 denotes in-domain acceptance aligned with the disposition._")
    w("")

    # 7. Biological Interpretation
    w("## 7. Biological Interpretation")
    w("")
    if abstain:
        w("The system abstained; no biological interpretation is provided.")
    else:
        w("See §4 for structured results. Direction and magnitude follow the prediction field; "
          "interpretation remains within the evidence.")
    w("")
    w("_Additional narration is available in LLM-assisted mode (narrative_report.md) "
      "and remains subject to the evidence boundary._")
    w("")

    # 8. Limitations
    w("## 8. Limitations")
    w("")
    limits: list[str] = []
    for r in ar:
        limits.append(f"abstain: {r}")
    for r in dr:
        limits.append(f"downgrade: {r}")
    caution = report.get("caution_flags") or {}
    if caution:
        limits.append(f"caution flags: {json.dumps(caution, ensure_ascii=False, sort_keys=True)}")
    if model_cautions:
        limits.append(f"model cautions: {json.dumps(model_cautions, ensure_ascii=False, sort_keys=True)}")
    mk = _mocks(used)
    if mk:
        limits.append(f"Predictions from mock predictors ({', '.join(mk)}) are test fixtures; "
                      "they do not constitute experimental validation.")
    sp = req.get("species")
    if sp and sp != "human":
        limits.append(f"Non-human species ({sp}) may require cross-species projection or ortholog mapping; "
                      "interpret as downgraded evidence rather than native-species accuracy.")
    if not limits:
        limits.append("No abstention, downgrade, or caution was triggered; "
                      "conclusions remain limited by the evidence in §6.")
    for x in limits:
        w(f"- {x}")
    w("")


    lq = prov.get("learning_queue") or {}
    lq_items = lq.get("items") or []
    w("### Validation Plan · Active Learning Suggestions")
    w("")
    if not lq_items:
        w(f"- Priority experiment candidates: `{_NA}` (no executable candidates or learning_queue is missing)")
    else:
        w("- Priority experiment candidates (descending information gain; advisory only):")
        for it in lq_items[:5]:            # top-5
            w(f"  - `{it.get('candidate', _NA)}` · module=`{it.get('module', _NA)}` · "
              f"information_gain=`{it.get('information_gain', _NA)}` · "
              f"drivers={_fmt_list(it.get('drivers'))}")
    lq_notes = lq.get("notes") or []
    if lq_notes:
        w(f"- notes: {_fmt_list(lq_notes)}")
    w("")
    w("_The validation plan recommends experiments ranked by disagreement, OOD, and evidence level. "
      "It does not modify predictions, final verdicts, or the provenance ledger._")
    w("")

    # 9. Reproducibility
    w("## 9. Reproducibility")
    w("")
    w(f"- request_id: `{report.get('request_id') or req.get('request_id') or _NA}`")
    w(f"- mode: `{mode}`")
    w("- llm_used_for_prediction: `False` (LLMs do not modify predictions)")
    w("- Reproduction command:")
    w("")
    w("```bash")
    w("praxis-vc run --request <request.json> --mode offline --out runs/<id>")
    w("```")
    w("")

    return "\n".join(lines) + "\n"
