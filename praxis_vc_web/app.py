"""v0.6 P3:PRAXIS-VirtualCell 本地网页(Streamlit)。

流程:自然语言 → 解析(可确认/编辑)→ 离线 runtime 执行 → 报告 / trace / provenance。
科学决策全由确定性 runtime;LLM 只做解析/建议/critic/叙述,不改预测与治理。
默认 local-first:直接调进程内服务层(无需另起 API);FastAPI(praxis_vc_api)供程序化/远端使用。
启动:praxis-vc web   或   streamlit run praxis_vc_web/app.py
"""
from __future__ import annotations

import os
import sys

# 保证能 import 核心包(streamlit run 时 cwd=repo root)
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import streamlit as st  # noqa: E402

from praxis_virtualcell.core.config import Mode, RuntimeConfig  # noqa: E402
from praxis_virtualcell.io.job_store import JobStore  # noqa: E402
from praxis_virtualcell.workflows.run_virtualcell_query import (  # noqa: E402
    parse_query,
    run_query,
)

st.set_page_config(page_title="PRAXIS-VirtualCell", layout="wide")


def _config(mode_label: str) -> RuntimeConfig:
    if mode_label == "llm_assisted":
        os.environ["PRAXIS_VIRTUALCELL_MODE"] = "llm_assisted"
        return RuntimeConfig.from_env()
    return RuntimeConfig(mode=Mode.OFFLINE, llm_enabled=False)


# ---- sidebar ----
st.sidebar.title("PRAXIS-VirtualCell")
st.sidebar.caption("离线优先 · 可审计 · 可回退的虚拟细胞智能体")
mode = st.sidebar.radio("模式", ["offline", "llm_assisted"], index=0,
                        help="offline:不调用任何 LLM。llm_assisted:LLM 仅解析/建议/叙述,不改预测与治理。")
cfg = _config(mode)
st.sidebar.write(f"LLM enabled: **{cfg.llm_enabled}**")
st.sidebar.info("核心预测、可靠性治理、provenance 均由确定性 runtime 完成;LLM 不参与这些决策。")

st.title("Ask PRAXIS-VirtualCell")
ss = st.session_state

# ---- Page 1: Ask ----
text = st.text_area("用自然语言描述你的虚拟细胞问题",
                    placeholder="例:我想预测在人类 K562 细胞里敲掉 AHR 后表达会怎么变化",
                    height=100)
if st.button("解析 Parse", type="primary"):
    ss["parsed"] = parse_query(text, config=cfg)
    ss.pop("result", None)

# ---- Page 2: Parsed request(确认/编辑)----
if ss.get("parsed"):
    p = ss["parsed"]
    st.subheader("系统理解为(可修改后确认)")
    cand = dict(p["candidate_request"])
    c1, c2, c3 = st.columns(3)
    cand["species"] = c1.text_input("species", cand.get("species", ""))
    cand["cell_type"] = c2.text_input("cell_type", cand.get("cell_type") or "")
    cand["perturbation_type"] = c3.text_input("perturbation_type", cand.get("perturbation_type", ""))
    cand["perturbation_targets"] = [t.strip() for t in st.text_input(
        "perturbation_targets(逗号分隔)",
        ",".join(cand.get("perturbation_targets", []))).split(",") if t.strip()]
    st.caption(f"parser={p['parser']} · llm_used={p['llm_used']} · fallback={p['fallback_used']} "
               f"· schema_valid={p['schema_valid']}")
    if p.get("assumptions"):
        st.caption("LLM assumptions: " + "; ".join(p["assumptions"]))
    if p["missing_fields"] or p.get("errors"):
        st.warning(f"需补充/修正:missing={p['missing_fields']} errors={p.get('errors')}")

    if st.button("Confirm and Run", type="primary"):
        from praxis_virtualcell.workflows.run_virtualcell_query import validate_candidate
        v = validate_candidate(cand)
        if not v["schema_valid"]:
            st.error(f"请求仍不合法:missing={v['missing_fields']} errors={v['errors']}")
        else:
            with st.spinner("确定性 runtime 执行中…"):
                out = run_query(v["normalized"], config=cfg,
                                enable_llm_report=(mode == "llm_assisted"))
                jid = "web_" + v["normalized"]["request_id"]
                JobStore(os.environ.get("PRAXIS_VC_RUNS", "runs")).save(
                    jid, request=v["normalized"], result={**out, "parsed": p})
                ss["result"] = out
                ss["job_id"] = jid

# ---- Page 3/4/5: Report / Trace / Provenance ----
if ss.get("result"):
    out = ss["result"]
    rep = out["structured_report"]
    rd = out["reliability_decision"]
    st.success(f"完成(job {ss.get('job_id')})· mode={out['mode']} · LLM 未参与预测/治理决策")
    tab_r, tab_t, tab_p = st.tabs(["📄 Report", "🔀 Trace", "🧾 Provenance"])

    with tab_r:
        st.markdown("**1. Summary**")
        st.json({"species": rep.get("species"), "perturbation_targets": rep.get("perturbation_targets"),
                 "models_used": rep.get("models_used"), "models_rejected": rep.get("models_rejected")})
        st.markdown("**2. Prediction / analysis**")
        st.json({"abstain": rep.get("abstain"), "prediction": rep.get("prediction") is not None})
        st.markdown("**3. Reliability decision**")
        st.json(rd)
        st.markdown("**4. Boundary statement**")
        st.write(rep.get("boundary_statement") or rep.get("caution_flags") or "—")
        if out.get("narrative"):
            st.markdown("---\n**Narrative(LLM 润色)**")
            st.info("Narrative generated from structured report. LLM did not modify prediction "
                    "or reliability decision.")
            st.write(out["narrative"])

    with tab_t:
        st.caption("Agent 通讯 trace(确定性 message bus)")
        st.dataframe(out["trace"], use_container_width=True)

    with tab_p:
        prov = out["provenance"]
        st.json(prov)
        llm = (ss.get("parsed") or {}).get("llm_metadata") or {}
        st.markdown("**LLM 使用(仅 hash,不存 key/原文)**")
        st.json(llm or {"llm_used": False})
