"""Shared deterministic helper for governance overrides. Change only public abstain/prediction/abstain_reasons and
record the incoming state in provenance. Reliability and critic decisions are not rewritten; the gate reads the
assembled report.
"""
from __future__ import annotations


def apply_governance_gate(report: dict, reason: str, prov_key: str, detail: dict) -> bool:
    """Apply a triggered gate and return whether it changed public abstention. A nonabstained report becomes
    abstain=True/prediction=None with the reason; an already-abstained report records provenance only.
    reliability_original_abstain describes the incoming public state, which may already reflect a preceding gate
    in a chain.
    """
    original = report.get("abstain", False)
    gated = not original
    if gated:
        report["abstain"] = True
        report["prediction"] = None
        if "adapter_output" in report:
            report["adapter_output"] = None
        report.setdefault("abstain_reasons", []).append(reason)
    report.setdefault("provenance", {})[prov_key] = {
        **detail, "gate_abstained": gated, "reliability_original_abstain": original}
    return gated
