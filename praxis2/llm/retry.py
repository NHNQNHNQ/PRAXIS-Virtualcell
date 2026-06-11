"""上游退避重试 + 多 base_url 顺序 failover(总纲 §4④ / §11.2)。

策略:对每个 base_url 做 max_retries 次指数退避重试(可重试错误=连接错/超时/
429/5xx);该 url 重试耗尽再切下一个 url;全部 url 失败抛最后异常。"""

import asyncio
import random
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import TypeVar

import httpx

T = TypeVar("T")

# 可重试 HTTP 状态:408 请求超时 / 409 冲突(乐观锁等,通常临时)/ 425 too early /
# 429 限流 / 5xx 服务端临时故障。重试非读操作要求 do 幂等;M0 作为通用工具按上游
# 建议的"临时性错误"集合处理,幂等性由调用方/集成层(M1+)保证。
_RETRIABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


class WithheldKind(StrEnum):
    """M10.5:可恢复的"被 withhold 错误"分类。M1 只认 PROMPT_TOO_LONG;
    M10.5 加 RATE_LIMITED(query.py 暂不自动处理,M11 carry rate-limit recovery)。"""

    PROMPT_TOO_LONG = "prompt_too_long"
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"


def classify_withheld_error(exc: Exception) -> WithheldKind:
    """§7.1.4:把可恢复的"被 withhold 错误"分类。M1 只认 prompt-too-long;
    M10.5 加 OpenAI error code 识别(context_length_exceeded / rate_limit_exceeded)。"""
    # 优先检查 HTTPStatusError 的响应体(M1 向后兼容)
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 400:
        body = exc.response.text.lower()
        if "prompt is too long" in body or "too many tokens" in body:
            return WithheldKind.PROMPT_TOO_LONG

    msg = str(exc).lower()

    # Anthropic + OpenAI context length 检查(处理 Exception 字符串,
    # 用于 litellm 包装的错误等)
    if (
        "prompt is too long" in msg
        or "too many tokens" in msg
        or "context_length_exceeded" in msg
        or "context length exceeded" in msg
    ):
        return WithheldKind.PROMPT_TOO_LONG

    # M10.5:OpenAI error code 识别(litellm 错误体形如
    # {"error":{"message":"...","code":"rate_limit_exceeded"}}
    # str(exc) 拿到的是完整 JSON 字符串)
    if "rate_limit_exceeded" in msg or "rate limit" in msg or "429" in msg:
        return WithheldKind.RATE_LIMITED

    # invalid_request_error 不触发 recovery,query.py 出 ERROR
    if "invalid_request_error" in msg or "invalid model name" in msg:
        return WithheldKind.UNKNOWN

    return WithheldKind.UNKNOWN


def _is_retriable(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRIABLE_STATUS
    return isinstance(exc, httpx.TransportError | httpx.TimeoutException)


async def call_with_failover(
    do: Callable[[httpx.AsyncClient], Awaitable[T]],
    *,
    base_urls: list[str],
    max_retries: int,
    base_delay_s: float,
    max_delay_s: float,
    timeout_s: float = 60.0,
) -> T:
    if not base_urls:
        raise ValueError("base_urls 不能为空")
    last: Exception | None = None
    for url in base_urls:
        async with httpx.AsyncClient(base_url=url.rstrip("/"), timeout=timeout_s) as c:
            for attempt in range(max_retries + 1):
                try:
                    return await do(c)
                except Exception as exc:  # noqa: BLE001 - 归类后决定重试/上抛
                    last = exc
                    if not _is_retriable(exc) or attempt == max_retries:
                        break
                    delay = min(max_delay_s, base_delay_s * (2**attempt))
                    if delay > 0:
                        await asyncio.sleep(delay + random.uniform(0, delay / 2))
    if last is None:  # base_urls 非空时理论不可达,显式抛而非 assert(python -O 安全)
        raise RuntimeError("call_with_failover: 未记录任何尝试异常")
    raise last
