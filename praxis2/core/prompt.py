"""唯一一条 system prompt 组装路径(总纲 §7.2)。

prompt 是 code 不是 template(§7.2.1):所有 section 定义在本模块,随代码部署,
无远程拉取、无第二条加载路径。组装唯一入口 build_effective_system_prompt(Task 2)。"""

import hashlib
from dataclasses import dataclass

from praxis2.core.state import State

# §7.2.3 静态/动态边界标记:此 sentinel 之前为静态 section(走 prompt cache 前缀),
# 之后为每轮可变 section。用不可见控制符避免与正常 section 名碰撞。
SYSTEM_PROMPT_DYNAMIC_BOUNDARY = "\x00__PRAXIS2_DYNAMIC_BOUNDARY__\x00"


@dataclass
class Section:
    """命名 prompt 片段(§7.2.2)。

    cache_break=True:跳过 section 级内存缓存、每轮重算(如 MCP 指令类;§7.2.3,Task 3 消费)。
    特例:name == SYSTEM_PROMPT_DYNAMIC_BOUNDARY 时为结构占位(text 恒空),仅标记
    静态/动态边界(§7.2.3),不参与内容序列化(Task 4 to_api_system 按它切分)。"""

    name: str
    text: str
    cache_break: bool = False


def get_default_system_prompt() -> list[Section]:
    """§7.2.1/§7.2.2:default 层(总是有)。M2 给最小骨架,
    后续 M3(RMCP)/M5(大脑)在边界前扩静态 section。"""
    return [
        Section("identity", "你是 PRAXIS-2 科研多 agent 系统的内核助手。"),
        Section("safety", "遵守科学严谨纪律:先检索证据再执行;不杜撰 DOI 或引用。"),
        Section(SYSTEM_PROMPT_DYNAMIC_BOUNDARY, ""),  # 以上静态可缓存,以下每轮可变
    ]


def build_effective_system_prompt(
    *,
    override: list[Section] | None = None,
    coordinator: list[Section] | None = None,
    agent: list[Section] | None = None,
    custom: list[Section] | None = None,
    default: list[Section] | None = None,
    append: list[Section] | None = None,
) -> list[Section]:
    """§7.2.4 五层优先级唯一组装入口。base = 最高优先级的非 None 层
    (override > coordinator > agent > custom > default);全部层均为 None 时
    回落 get_default_system_prompt()。append 永远线性追加在最后,按传入顺序,
    不乱序、不漏层。"""
    if override is not None:
        base = override
    elif coordinator is not None:
        base = coordinator
    elif agent is not None:
        base = agent
    elif custom is not None:
        base = custom
    elif default is not None:
        base = default
    else:
        base = get_default_system_prompt()
    return [*base, *(append or [])]


class SectionCache:
    """§7.2.3 section 级内存缓存(key=section name)。cache_break=True 跳过。
    /clear、compact、worktree 切换时由调用方显式 invalidate()(本类不自动失效)。
    调用方须确保不同语义的 section 用不同 name(name 是唯一 key,重名会相互覆盖)。"""

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def render(self, section: Section) -> str:
        if section.cache_break:
            return section.text  # 每轮重算,不进缓存
        if section.name not in self._cache:
            self._cache[section.name] = section.text
        return self._cache[section.name]

    def invalidate(self) -> None:
        self._cache.clear()


def to_api_system(sections: list[Section]) -> list[dict]:
    """§7.2.3:按 SYSTEM_PROMPT_DYNAMIC_BOUNDARY 切分。静态前缀合成一个 block
    并打 cache_control: ephemeral(Anthropic prompt cache 前缀命中点);动态部分
    合成一个普通 block(不缓存)。无边界 → 全部视为静态。空 text section 跳过。
    多个 boundary 时首个生效(其后全归 dynamic)。无内容 → 返回 [];调用方须把
    [] 视为不传 system(传 None),Anthropic 拒绝 system=[]。"""
    static_parts: list[str] = []
    dynamic_parts: list[str] = []
    seen_boundary = False
    for s in sections:
        if s.name == SYSTEM_PROMPT_DYNAMIC_BOUNDARY:
            seen_boundary = True
            continue
        if not s.text:
            continue
        (dynamic_parts if seen_boundary else static_parts).append(s.text)
    blocks: list[dict] = []
    if static_parts:
        blocks.append(
            {
                "type": "text",
                "text": "\n\n".join(static_parts),
                "cache_control": {"type": "ephemeral"},
            }
        )
    if dynamic_parts:
        blocks.append({"type": "text", "text": "\n\n".join(dynamic_parts)})
    return blocks


def get_user_context(
    *,
    claude_md: str | None = None,
    agents_md: str | None = None,
    today: str | None = None,
) -> str | None:
    """§7.2.5:CLAUDE.md/AGENTS.md 内容 + 当前日期 —— 轮级 context,注入 messages 最前
    (不进 system,避免混入拉低 prompt cache 命中率)。全空 → None。"""
    parts: list[str] = []
    if today:
        parts.append(f"当前日期:{today}")
    if claude_md:
        parts.append(f"<project-instructions>\n{claude_md}\n</project-instructions>")
    if agents_md:
        parts.append(f"<agents-md>\n{agents_md}\n</agents-md>")
    return "\n\n".join(parts) if parts else None


def prepend_user_context(messages: list[dict], user_context: str | None) -> list[dict]:
    """§7.2.5:user context 作为最前一条 user 消息插入。不就地改 messages,返回新 list。"""
    if not user_context:
        return list(messages)
    return [{"role": "user", "content": user_context}, *messages]


def get_system_context(
    *, git_status: str | None = None, cache_breaker: str | None = None
) -> str | None:
    """§7.2.5:git 状态 + cache breaker —— 轮级 context,追加到 system 末尾且不缓存。"""
    parts: list[str] = []
    if git_status:
        parts.append(f"<git-status>\n{git_status}\n</git-status>")
    if cache_breaker:
        parts.append(f"<cache-breaker>{cache_breaker}</cache-breaker>")
    return "\n\n".join(parts) if parts else None


def append_system_context(
    sections: list[Section], system_context: str | None
) -> list[Section]:
    """§7.2.5:system context 作为最后一个 cache_break section 追加。它在动态边界
    之后 → to_api_system 时落动态 block、不带 cache_control,每轮可变。
    注:to_api_system 的静/动分流只看 boundary 位置,与 cache_break 无关;
    cache_break=True 在此确保 SectionCache 也每轮重算(双保险,不冗余)。"""
    if not system_context:
        return list(sections)
    return [*sections, Section("system_context", system_context, cache_break=True)]


# §7.2.6:专项 prompt 各有独立协议,不复用主 prompt(格式严格、要省 token)。
# M2 给最小占位协议串;M4(compact/memory-*)、M5(route)填实际严格协议。
SPECIALIZED_PROMPTS: dict[str, str] = {
    "compact": "你是会话压缩器。仅输出保留关键事实/未决任务的压缩摘要,不寒暄、不解释。",
    "memory-extract": "你是事实抽取器。仅输出可长期沉淀的结构化事实列表,无其他文字。",
    "memory-update": "你是 MEMORY 索引维护器。仅输出更新后的索引行(文件名+单行描述)。",
    "route": "你是路由判定器。仅输出选定 agent slug 一个词,无其他文字。",
}


def get_specialized_prompt(name: str) -> str:
    """§7.2.6:取专项 prompt。未知名直接 KeyError(fail-fast,不静默兜底主 prompt)。"""
    return SPECIALIZED_PROMPTS[name]


def section_hash(sections: list[Section]) -> str:
    """§7.2.8:section 列表稳定哈希,用于会话级 prompt 快照比对(drift 定位)。
    name 与 text 都纳入,用 \\x1f(name/text 间)/\\x1e(section 间)防拼接歧义。
    前提:name/text 不含 \\x1f、\\x1e(控制字符,正常 prompt 不出现)。"""
    h = hashlib.sha256()
    for s in sections:
        h.update(s.name.encode())
        h.update(b"\x1f")
        h.update(s.text.encode())
        h.update(b"\x1e")
    return h.hexdigest()


def render_and_persist(state: State, sections: list[Section]) -> list[dict]:
    """§7.2.7:渲染 system 为 API blocks 并挂到 state.tool_use_context,
    让 fork/subagent/hook 都看同一份字节,避免 prompt drift。返回 API system blocks。
    注:返回值与 state 里存的是同一引用,调用方只读勿就地改(T9 仅传 query 只读)。"""
    api_system = to_api_system(sections)
    state.tool_use_context["rendered_system_prompt"] = api_system
    state.tool_use_context["system_prompt_hash"] = section_hash(sections)
    return api_system
