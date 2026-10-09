"""Local Streamlit interface for PRAXIS-VirtualCell.

Parse, review, and confirm a request before deterministic execution.
The local service provides reports, traces, and provenance; LLM assistance
is limited to interpretation, suggestions, critique, and narration.
Start with praxis-vc web or streamlit run praxis_vc_web/app.py.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import streamlit as st  # noqa: E402

from praxis_virtualcell.core.config import Mode, RuntimeConfig  # noqa: E402
from praxis_virtualcell.io.job_store import JobStore  # noqa: E402
from praxis_virtualcell.workflows.run_virtualcell_query import (  # noqa: E402
    coerce_str_list,
    parse_query,
    run_formal_query,
)

st.set_page_config(page_title="PRAXIS-VirtualCell", layout="wide")


def _config(mode_label: str) -> RuntimeConfig:
    if mode_label == "llm_assisted":
        os.environ["PRAXIS_VIRTUALCELL_MODE"] = "llm_assisted"
        return RuntimeConfig.from_env()
    return RuntimeConfig(mode=Mode.OFFLINE, llm_enabled=False)


# ---- sidebar ----
st.sidebar.title("PRAXIS-VirtualCell")
st.sidebar.caption("Offline first · Auditable · Virtual-cell agents with fallback")
mode = st.sidebar.radio(
    "Mode",
    ["offline", "llm_assisted"],
    index=0,
    help=("offline: no LLM calls. llm_assisted: interpretation, suggestions, and narration only; "
          "predictions and governance remain deterministic."),
)
cfg = _config(mode)
st.sidebar.write(f"LLM enabled: **{cfg.llm_enabled}**")
st.sidebar.info("The deterministic runtime governs predictions, reliability, and provenance.")

st.title("Ask PRAXIS-VirtualCell")
ss = st.session_state

# ---- Page 1: Ask ----
text = st.text_area(
    "Describe your virtual-cell question",
    placeholder="Example: What happens to expression after knocking out AHR in human K562 cells?",
    height=100,
)
if st.button("Parse", type="primary"):
    ss["parsed"] = parse_query(text, config=cfg)
    ss.pop("result", None)


if ss.get("parsed"):
    p = ss["parsed"]
    st.subheader("Review the interpreted request before confirmation")
    cand = dict(p["candidate_request"])
    c1, c2, c3 = st.columns(3)
    cand["species"] = c1.text_input("species", cand.get("species", ""))
    cand["cell_type"] = c2.text_input("cell_type", cand.get("cell_type") or "")
    cand["perturbation_type"] = c3.text_input("perturbation_type", cand.get("perturbation_type", ""))


    cand["perturbation_targets"] = [
        t.strip()
        for t in st.text_input(
            "perturbation_targets (comma separated)", ",".join(coerce_str_list(cand.get("perturbation_targets")))
        ).split(",")
        if t.strip()
    ]
    st.caption(
        f"parser={p['parser']} · llm_used={p['llm_used']} · fallback={p['fallback_used']} "
        f"· schema_valid={p['schema_valid']}"
    )
    if p.get("assumptions"):
        st.caption("LLM assumptions: " + "; ".join(p["assumptions"]))
    if p["missing_fields"] or p.get("errors"):
        st.warning(f"Complete or correct: missing={p['missing_fields']} errors={p.get('errors')}")

    if st.button("Confirm and Run", type="primary"):
        from praxis_virtualcell.workflows.run_virtualcell_query import validate_candidate

        v = validate_candidate(cand)
        if not v["schema_valid"]:
            st.error(f"Invalid request: missing={v['missing_fields']} errors={v['errors']}")
        else:
            with st.spinner("Running the deterministic runtime…"):
                out = run_formal_query(
                    v["normalized"],
                    config=cfg,
                    enable_llm_report=(mode == "llm_assisted"),
                )
                jid = "web_" + v["normalized"]["request_id"]
                JobStore(os.environ.get("PRAXIS_VC_RUNS", "runs")).save(
                    jid, request=v["normalized"], result={**out, "parsed": p}
                )
                ss["result"] = out
                ss["job_id"] = jid

# ---- Page 3/4/5: Report / Trace / Provenance ----
if ss.get("result"):
    out = ss["result"]
    rep = out["structured_report"]
    rd = out["reliability_decision"]
    st.success(f"Completed (job {ss.get('job_id')})· mode={out['mode']} · "
               "Predictions and governance were determined by the runtime")
    tab_r, tab_t, tab_p = st.tabs(["📄 Report", "🔀 Trace", "🧾 Provenance"])

    with tab_r:
        st.markdown("**1. Summary**")
        st.json(
            {
                "species": rep.get("species"),
                "perturbation_targets": rep.get("perturbation_targets"),
                "models_used": rep.get("models_used"),
                "models_rejected": rep.get("models_rejected"),
            }
        )
        st.markdown("**2. Prediction / analysis**")
        st.json({"abstain": rep.get("abstain"), "prediction": rep.get("prediction") is not None})
        st.markdown("**3. Reliability decision**")
        st.json(rd)
        st.markdown("**4. Boundary statement**")
        st.write(rep.get("boundary_statement") or rep.get("caution_flags") or "—")
        if out.get("narrative"):
            st.markdown("---\n**Narrative (LLM assisted)**")
            st.info(
                "Narrative generated from structured report. LLM did not modify prediction or reliability decision."
            )
            st.write(out["narrative"])

    with tab_t:
        st.caption("Agent communication trace (deterministic message bus)")
        st.dataframe(out["trace"], use_container_width=True)

    with tab_p:
        prov = out["provenance"]
        st.json(prov)
        llm = (ss.get("parsed") or {}).get("llm_metadata") or {}
        st.markdown("**LLM usage (hashes only; no keys or raw text stored)**")
        st.json(llm or {"llm_used": False})
