"""内置 PostToolUse 否决 hook(§5④#2)。签名同 SerialToolRunner.post_hooks 元素:
(tool, blk, result, state) -> dict | None;返回非 None 替换 result。
否决 = 把通过结果替换为 is_error result,content 含*为何否决*+*可执行满足条件*
(§7.3.7 4 键形态 + §4②),模型自主修正不停下问人。"""

import re
from collections.abc import Callable
from typing import Any

from praxis2.core.rmcp import ALLOWED_OPS, Phase, advance_phase, get_phase
from praxis2.core.seams import StopDecision
from praxis2.core.state import State


def _veto(result: dict, why: str, satisfy: str) -> dict:
    """构造否决 result:沿用原 tool_use_id,is_error=True,content 写给模型看。
    依赖前置:result 由 SerialToolRunner 产出,tool_use_id 键恒存在。"""
    return {
        "type": "tool_result",
        "tool_use_id": result["tool_use_id"],
        "is_error": True,
        "content": f"[RMCP 否决] {why}\n满足条件:{satisfy}",
    }


def doi_required(
    tool: Any, blk: dict, result: dict, state: State
) -> dict | None:
    """§5④#2:case 类产出必须含 CrossRef DOI(v1 doi_required)。
    已是 is_error 的结果不二次否决。
    判定口径:认 'doi:<...>' 或 'doi.org/<...>' 子串;纯裸 DOI(无前缀)不认
    (v1 规则式实用近似,非完备 DOI 校验)。"""
    if result.get("is_error"):
        return None
    content = str(result.get("content", ""))
    if "doi:" in content.lower() or "doi.org/" in content.lower():
        return None
    return _veto(
        result,
        "案例产出缺 CrossRef DOI(科学严谨:论断须可溯源)",
        "在产出中补 'doi:<CrossRef DOI>' 后重做本步",
    )


def evidence_chain_required(
    tool: Any, blk: dict, result: dict, state: State
) -> dict | None:
    """§5④#2:artifact 必须含证据字段(v1 evidence_chain_required)。"""
    if result.get("is_error"):
        return None
    if "evidence:" in str(result.get("content", "")).lower():
        return None
    return _veto(
        result,
        "产出证据链断裂(缺 evidence 字段:结论未挂可核查依据)",
        "在产出中补 'evidence: [<case/rule 引用>]' 后重做本步",
    )


def anti_retrieval_threshold(
    tool: Any, blk: dict, result: dict, state: State, *, ratio: float = 0.8
) -> dict | None:
    """§5④#2:反向用例通过率须 ≥ ratio(v1 anti_retrieval_threshold)。
    从 content 解析 passed/total;无法解析则不否决(交其它 hook/Stop gate)。
    content 含多处 passed=/total= 时取第一个匹配(v1 近似,单输出报告无歧义)。"""
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
        f"反向过滤未达标(passed={passed}/total={total} < 阈值 {ratio})",
        f"补足反向用例使通过率 ≥ {ratio} 后重做本步",
    )


def make_rmcp_stop_gate() -> Callable[[State], StopDecision]:
    """§7.6.1 Stop + §5④#3:终答前校验证据链 + 反向过滤完整。
    判据:state.tool_use_context 的 evidence_ok / anti_filter_ok(RMCP 流程置)。
    缺任一 → veto + 可执行满足条件(query() 据此强制再走一轮)。
    工厂形态预留 T8 注入 required_keys / ratio 参数(当前无捕获参数)。"""

    def _gate(state: State) -> StopDecision:
        ctx = state.tool_use_context
        missing = []
        if not ctx.get("evidence_ok"):
            missing.append("证据链不完整")
        if not ctx.get("anti_filter_ok"):
            missing.append("反向过滤未通过")
        if not missing:
            return StopDecision(veto=False)
        return StopDecision(
            veto=True,
            message=(
                f"[RMCP 终态否决] {'; '.join(missing)}。"
                f"满足条件:先完成 retrieve→anti_filter 并补足证据链"
                f"(置 evidence_ok / anti_filter_ok),再给终答"
            ),
        )

    return _gate


def advance_phase_on_real_retrieval(
    tool: Any, blk: dict, result: dict, state: State
) -> dict | None:
    """GAP-AH-1 检索先行接线(chat):BrainQuery 真命中(tool.last_retrieval_real_hit)
    且当前 INIT → 推进 RETRIEVE。fixture/空/降级/错误结果不推进(执行仍被证据门拒)。
    幂等:已非 INIT 不动(守 S7 无 RETRIEVE→RETRIEVE 边,避 PhaseError)。永不替换 result。"""
    if result.get("is_error"):
        return None
    if getattr(tool, "last_retrieval_real_hit", False) and get_phase(state) is Phase.INIT:
        advance_phase(state, Phase.RETRIEVE)
    return None


def advance_phase_on_retrieve(
    tool: Any, blk: dict, result: dict, state: State
) -> dict | None:
    """§5④#1 接线:检索类工具(rmcp_op 属 RETRIEVE 白名单)成功 → 相位推进到
    RETRIEVE(幂等)。失败不推进。非检索工具不动。永不替换 result(返回 None)。"""
    if result.get("is_error"):
        return None
    op = getattr(tool, "rmcp_op", None)
    if op is not None and op in ALLOWED_OPS[Phase.RETRIEVE]:
        # 守卫语义必需:S7 转移表无 RETRIEVE→RETRIEVE 边,已在 RETRIEVE 则跳过,
        # 否则 advance_phase 第二次调用会 PhaseError(INIT→RETRIEVE 合法故首次通过)
        if get_phase(state) is not Phase.RETRIEVE:
            advance_phase(state, Phase.RETRIEVE)
    return None


# GAP-AH-2:声称"已执行/已分析/有结果"的中英特征(v1 小而精,精度优先,可后扩)
_CLAIM_PATTERNS = re.compile(
    r"已(运行|执行|对接|折叠|计算|跑完|完成对接|完成折叠|完成分析|得到结果)"
    r"|结果(显示|为|如下|是)"
    # metric 词须紧跟数值断言(冒号/等号/是/为 + 数字),否则纯概念提及("RMSD 是衡量指标")
    # 会误杀 → 精度优先(只命中"得分 -9.2 / 亲和力=-8.5"这类真声称结果)
    r"|(最佳|预测)?(亲和力|结合能|打分|得分|plddt|rmsd)\s*[:=是为]?\s*-?\d"
    r"|docked|folded|computed|executed|ran the|results?\s+show|affinity\s+is",
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
                return " ".join(
                    b.get("text", "")
                    for b in c
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            return ""
    return ""


def _has_successful_tool_use(state: State) -> bool:
    """历史里有无成功(非 is_error)的 tool_result(任何工具均算证据)。"""
    for m in state.messages:
        c = m.get("content")
        if isinstance(c, list):
            for b in c:
                if (
                    isinstance(b, dict)
                    and b.get("type") == "tool_result"
                    and not b.get("is_error", False)
                ):
                    return True
    return False


def make_tool_use_presence_stop_hook(
    max_veto: int = 1,
) -> "Callable[[State], StopDecision]":
    """GAP-AH-2 终答证据门:终答声称做过执行/分析,但本会话零成功 tool_use → veto
    一次、注入纠正、强制再走(§5④#3)。保守(零工具证据才 veto),几乎不误杀纯概念问答。
    防循环:state.stop_hook_veto_count >= max_veto 不再 veto(maxTurns/recovery 兜底)。"""

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
                    "[反幻觉否决] 你声称已执行/分析并给出了结果,但本会话未真正调用任何工具"
                    "拿到这些结果。请先用 BrainQuery 检索、再用 SkillExec 等真正执行,"
                    "拿到真实数据后再作答;不要凭空给出执行结论。"
                ),
            )
        return StopDecision(veto=False)

    return _hook
