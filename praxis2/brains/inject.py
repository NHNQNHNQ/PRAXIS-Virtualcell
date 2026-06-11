"""检索命中 + SKILL 摘要 + MEMORY.md 组装进唯一一条 system prompt 的
agent 层(总纲 §3 step2.5 + §7.2.4 + §7.4.1)。

复用 M2 core/prompt.Section/build_effective_system_prompt(不复制 prompt
组装逻辑,§7.5.0 不产生第二条路径)。所有大脑内容置于动态边界之前
= 静态可缓存(§7.2.3:会话级稳定,走 prompt cache 前缀)。检索为空仍带
_common(S13)+ 显式降级 section(不静默,§3 step2.5)。"""

from typing import Any

from praxis2.core.prompt import SYSTEM_PROMPT_DYNAMIC_BOUNDARY, Section


def _join_docs(docs: list[Any]) -> str:
    return "\n\n".join(
        f"### {getattr(d, 'kind', '?')}/{getattr(d, 'stem', '?')}\n"
        f"{getattr(d, 'text', '')}"
        for d in docs
    )


def assemble_agent_sections(
    selection: Any,
    *,
    retrieval: Any,
    common_docs: list[Any],
    skill_summary: str,
    memory_text: str,
) -> list[Section]:
    """产 agent 层 Section 列表,末尾压 SYSTEM_PROMPT_DYNAMIC_BOUNDARY
    (其前全部静态可缓存)。调用方传入 build_effective_system_prompt(agent=...)。

    调用方契约:common_docs 不应为空(S13:bare 也必带 _common,调用方保证,
    本函数不强制以免 over-engineering);retrieval 为 RetrievalResult
    (hits/degraded_to_bare 必有,故 hits 直接访问、degraded_to_bare 取
    getattr 默认 True 取安全失守方向)。契约由 T11/T12 端到端锁死。"""
    secs: list[Section] = []
    # 测试日志行3:每轮意图聚焦——防模型被上一轮超长输出带跑、复读旧任务。
    # 放最前(静态可缓存前缀),所有模式/agent 都带。
    secs.append(Section(
        "current_turn_focus",
        "# 当前轮次优先级\n"
        "优先理解并回答**对话中最新一条用户消息**的真实意图。"
        "若它与上文话题无关,视为新话题独立作答,不要延续或复述上一轮内容;"
        "仅当用户明确表示继续/追问时才承接上文。",
    ))
    # _common RMCP/安全规则:所有模式(含 bare)始终带(S13)
    if common_docs:
        secs.append(Section(
            "brain_common_rules",
            "# 通用规则(_common,RMCP/安全,所有 agent 生效)\n"
            + _join_docs(common_docs),
        ))
    # 命中领域知识(检索非空)
    if not getattr(retrieval, "degraded_to_bare", True) and retrieval.hits:
        secs.append(Section(
            "brain_domain_hits",
            "# 命中领域知识(大脑检索 retrieve-first,§3 step2.5)\n"
            + _join_docs(retrieval.hits),
        ))
    else:
        # 显式降级说明(不静默,§3 step2.5)
        secs.append(Section(
            "retrieval_degraded",
            "# 大脑检索降级\n本轮领域检索为空 → 降级 bare(不注入领域大脑;"
            f"仅保留 _common 规则)。原因:{getattr(retrieval, 'reason', '')}",
        ))
    if skill_summary.strip():
        secs.append(Section(
            "skill_disclosure",
            "# 可用 skill(渐进披露摘要,§7.5.2)\n" + skill_summary,
        ))
    if memory_text.strip():
        secs.append(Section(
            "memory_index",
            "# MEMORY.md 索引(三层合并,§7.4.1)\n" + memory_text,
        ))
    # 边界 sentinel:以上全部静态可缓存(§7.2.3)
    secs.append(Section(SYSTEM_PROMPT_DYNAMIC_BOUNDARY, ""))
    return secs
