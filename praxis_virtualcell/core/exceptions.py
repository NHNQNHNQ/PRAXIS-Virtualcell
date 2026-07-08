"""praxis_virtualcell 主链路异常(均不依赖 praxis2)。"""
from __future__ import annotations


class PraxisVCError(Exception):
    """所有本包异常基类。"""


class InputValidationError(PraxisVCError):
    """VirtualCellRequest 解析/校验失败。"""


class RetrieveBeforePredictError(PraxisVCError):
    """反幻觉硬门:未先检索 brain 就尝试预测。"""


class UnknownAgentError(PraxisVCError):
    """dispatch 到未注册的 agent。"""


class SchemaError(PraxisVCError):
    """message/handoff schema 校验失败(缺必需字段 / payload 非 dict / 自由文本 handoff)。"""
