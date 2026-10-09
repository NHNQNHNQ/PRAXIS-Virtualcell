import asyncio
import random
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import TypeVar

import httpx

T = TypeVar("T")


_RETRIABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


class WithheldKind(StrEnum):
    PROMPT_TOO_LONG = "prompt_too_long"
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"


def classify_withheld_error(exc: Exception) -> WithheldKind:

    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 400:
        body = exc.response.text.lower()
        if "prompt is too long" in body or "too many tokens" in body:
            return WithheldKind.PROMPT_TOO_LONG

    msg = str(exc).lower()

    if (
        "prompt is too long" in msg
        or "too many tokens" in msg
        or "context_length_exceeded" in msg
        or "context length exceeded" in msg
    ):
        return WithheldKind.PROMPT_TOO_LONG

    # {"error":{"message":"...","code":"rate_limit_exceeded"}}

    if "rate_limit_exceeded" in msg or "rate limit" in msg or "429" in msg:
        return WithheldKind.RATE_LIMITED

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
        raise ValueError("base_urls must not be empty")
    last: Exception | None = None
    for url in base_urls:
        async with httpx.AsyncClient(base_url=url.rstrip("/"), timeout=timeout_s) as c:
            for attempt in range(max_retries + 1):
                try:
                    return await do(c)
                except Exception as exc:  # noqa: BLE001
                    last = exc
                    if not _is_retriable(exc) or attempt == max_retries:
                        break
                    delay = min(max_delay_s, base_delay_s * (2**attempt))
                    if delay > 0:
                        await asyncio.sleep(delay + random.uniform(0, delay / 2))
    if last is None:
        raise RuntimeError("call_with_failover: no attempt error was recorded")
    raise last
