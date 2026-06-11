"""跨轮状态显式承载(总纲 §7.1.2)+ 调用链追踪(§7.1.7)。

每条 query() 的 continue 路径都必须完整传递同一个 State 实例
(散落成局部变量是 v1 难查 bug 的根因之一)。"""

import uuid
from dataclasses import dataclass, field
from enum import StrEnum


class TerminalReason(StrEnum):
    STOP = "stop"  # 模型正常终答(无 tool_use)
    MAX_TURNS = "max_turns"  # §7.1.1
    ABORTED = "aborted"  # §7.1.5
    ESCALATED = "escalated"  # §4③/⑤ 自主恢复预算耗尽,转人工(模型主动 ask_user 的可测代理)
    ERROR = "error"  # 不可恢复错误冒泡


@dataclass
class QueryTracking:
    """§7.1.7:chain_id 全链唯一,depth 嵌套深度;多 agent 系统据此关联调用链。"""

    chain_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    depth: int = 0


@dataclass
class State:
    """单次 query() 全程贯穿的可变跨轮状态容器(§7.1.2)。

    每条 continue 路径都必须传递同一个实例;字段散落成局部变量是 v1 难查 bug 根因。"""

    # §7.1.2 至少含以下字段
    messages: list[dict] = field(default_factory=list)
    tool_use_context: dict = field(default_factory=dict)  # M2 填 rendered_system_prompt 等
    turn_count: int = 0
    transition: str | None = None  # 上一轮为何 continue,防恢复路径无限循环(§7.1.2/§7.1.4)
    auto_compact_tracking: dict = field(
        default_factory=lambda: {"consecutive_failures": 0}
    )  # 连续失败计数,熔断用(M4 充实)
    pending_tool_use_summary: str | None = None
    max_output_tokens_recovery_count: int = 0  # §7.1.4 #2
    # Bug B(2026-05-30):推理模型 reasoning 烧光 max_tokens → content=0 空响应。
    # max_tokens recovery 时累加此 boost,重试轮拿更大预算(见 query.py recovery 点②)。
    max_tokens_boost: int = 0
    # §7.6.1 / §5④#3(B.4 reviewer M1 C2):stop_hook 否决原因集合(诊断字段)。
    # 不再用 stop_hook_active 旗标"宁松勿死循环"——每终答都跑 hook,maxTurns 兜底。
    # 选 list 不选 set:保留顺序 + 允许重复,便于 transcript 调试。
    pending_stop_reasons: list[str] = field(default_factory=list)
    stop_hook_veto_count: int = 0  # GAP-AH-2:tool_use_presence stop_hook 已 veto 次数(防循环)
    last_assistant_text: str = ""  # GAP-AH-2:本轮终答文本(query 终态前置写入,供 stop_hook 读)
    recovery_attempts: int = 0  # §4③ 自主恢复预算计数
    tracking: QueryTracking = field(default_factory=QueryTracking)
    original_task_idx: int | None = None  # §12.3 原始任务消息下标,compact 永久 pinned
    # 计费:本次 query() 闭环累计的 LLM token 用量(多轮工具调用会有多次 message_stop),
    # chat 层据此 × 单价扣费。OpenAI 格式 prompt/completion。每个新 user turn 重置(app.py)。
    usage_total: dict = field(
        default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0}
    )
