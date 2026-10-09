import re
from collections.abc import Callable
from typing import Any

from praxis2.core.rmcp import ALLOWED_OPS, Phase, advance_phase, get_phase
from praxis2.core.seams import StopDecision
from praxis2.core.state import State


def _veto(result: dict, why: str, satisfy: str) -> dict:

    return {
        "type": "tool_result",
        "tool_use_id": result["tool_use_id"],
        "is_error": True,
        "content": f"[RMCP veto] {why}\nRequired condition: {satisfy}",
    }


def doi_required(tool: Any, blk: dict, result: dict, state: State) -> dict | None:

    if result.get("is_error"):
        return None
    content = str(result.get("content", ""))
    if "doi:" in content.lower() or "doi.org/" in content.lower():
        return None
    return _veto(
        result,
        "The case output lacks a CrossRef DOI required for a traceable claim",
        "Add doi:<CrossRef DOI> to the output and repeat this step",
    )


def evidence_chain_required(tool: Any, blk: dict, result: dict, state: State) -> dict | None:

    if result.get("is_error"):
        return None
    if "evidence:" in str(result.get("content", "")).lower():
        return None
    return _veto(
        result,
        "The output lacks an evidence field linking its claims to verifiable sources",
        "Add evidence with case or rule references and repeat this step",
    )


def anti_retrieval_threshold(tool: Any, blk: dict, result: dict, state: State, *, ratio: float = 0.8) -> dict | None:

    if result.get("is_error"):
        return None
    content = str(result.get("content", ""))
    mp = re.search(r"passed\s*=\s*(\d+)", content)
    mt = re.search(r"total\s*=\s*(\d+)", content)
    if not (mp and mt):
        return None
    passed, total = int(mp.group(1)), int(mt.group(1))
    if total > 0 and passed / total >= ratio:
        return None
    return _veto(
        result,
        f"Reverse filtering below threshold, passed={passed}/total={total} < threshold {ratio}",
        f"Add negative cases to reach a pass rate of at least {ratio} and repeat this step",
    )


def make_rmcp_stop_gate() -> Callable[[State], StopDecision]:

    def _gate(state: State) -> StopDecision:
        ctx = state.tool_use_context
        missing = []
        if not ctx.get("evidence_ok"):
            missing.append("Evidence chain is incomplete")
        if not ctx.get("anti_filter_ok"):
            missing.append("Reverse filtering did not pass")
        if not missing:
            return StopDecision(veto=False)
        return StopDecision(
            veto=True,
            message=(
                f"[RMCP final-state veto] {'; '.join(missing)}. "
                "Required condition: complete retrieval and reverse filtering, "
                "then establish evidence_ok and anti_filter_ok before answering"
            ),
        )

    return _gate


def advance_phase_on_real_retrieval(tool: Any, blk: dict, result: dict, state: State) -> dict | None:

    if result.get("is_error"):
        return None
    if getattr(tool, "last_retrieval_real_hit", False) and get_phase(state) is Phase.INIT:
        advance_phase(state, Phase.RETRIEVE)
    return None


def advance_phase_on_retrieve(tool: Any, blk: dict, result: dict, state: State) -> dict | None:

    if result.get("is_error"):
        return None
    op = getattr(tool, "rmcp_op", None)
    if op is not None and op in ALLOWED_OPS[Phase.RETRIEVE]:
        if get_phase(state) is not Phase.RETRIEVE:
            advance_phase(state, Phase.RETRIEVE)
    return None


_CLAIM_PATTERNS = re.compile(
    (
        "\u5df2(\u8fd0\u884c|\u6267\u884c|\u5bf9\u63a5|\u6298\u53e0|"
        "\u8ba1\u7b97|\u8dd1\u5b8c|\u5b8c\u6210\u5bf9\u63a5|\u5b8c\u6210"
        "\u6298\u53e0|\u5b8c\u6210\u5206\u6790|\u5f97\u5230\u7ed3\u679c)|"
        "\u7ed3\u679c(\u663e\u793a|\u4e3a|\u5982\u4e0b|\u662f)|(\u6700"
        "\u4f73|\u9884\u6d4b)?(\u4eb2\u548c\u529b|\u7ed3\u5408\u80fd|"
        "\u6253\u5206|\u5f97\u5206|plddt|rmsd)\\s*[:=\u662f\u4e3a]?\\s*-?"
        "\\d|docked|folded|computed|executed|ran the|results?\\s+show|aff"
        "inity\\s+is"
    ),
    re.IGNORECASE,
)


def _last_assistant_text(state: State) -> str:
    if state.last_assistant_text:
        return state.last_assistant_text
    for m in reversed(state.messages):
        if m.get("role") == "assistant":
            c = m.get("content")
            if isinstance(c, str):
                return c
            if isinstance(c, list):
                return " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
            return ""
    return ""


def _has_successful_tool_use(state: State) -> bool:

    for m in state.messages:
        c = m.get("content")
        if isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_result" and not b.get("is_error", False):
                    return True
    return False


def make_tool_use_presence_stop_hook(
    max_veto: int = 1,
) -> "Callable[[State], StopDecision]":

    def _hook(state: State) -> StopDecision:
        if state.stop_hook_veto_count >= max_veto:
            return StopDecision(veto=False)
        text = _last_assistant_text(state)
        claims = bool(_CLAIM_PATTERNS.search(text))
        if claims and not _has_successful_tool_use(state):
            state.stop_hook_veto_count += 1
            return StopDecision(
                veto=True,
                message=(
                    "[Unsupported execution claim] The answer claims "
                    "an analysis result without an actual tool call i"
                    "n this session. Retrieve evidence with BrainQuer"
                    "y and execute the required tools before reportin"
                    "g results."
                ),
            )
        return StopDecision(veto=False)

    return _hook
