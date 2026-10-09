import httpx
import pytest
import respx

from praxis2.llm.retry import (
    WithheldKind,
    call_with_failover,
    classify_withheld_error,
)


@respx.mock
async def test_failover_switches_url_after_retries_exhausted():
    respx.post("https://u1/v1/messages").mock(return_value=httpx.Response(503))
    ok = respx.post("https://u2/v1/messages").mock(return_value=httpx.Response(200, json={"ok": True}))

    async def do(client: httpx.AsyncClient):
        r = await client.post("/v1/messages", json={})
        r.raise_for_status()
        return r.json()

    result = await call_with_failover(
        do,
        base_urls=["https://u1", "https://u2"],
        max_retries=2,
        base_delay_s=0.0,
        max_delay_s=0.0,
    )
    assert result == {"ok": True}
    assert ok.called


@respx.mock
async def test_succeeds_on_first_url_without_failover():
    first = respx.post("https://u1/v1/messages").mock(return_value=httpx.Response(200, json={"ok": 1}))

    async def do(client: httpx.AsyncClient):
        r = await client.post("/v1/messages", json={})
        r.raise_for_status()
        return r.json()

    result = await call_with_failover(
        do,
        base_urls=["https://u1", "https://u2"],
        max_retries=2,
        base_delay_s=0.0,
        max_delay_s=0.0,
    )
    assert result == {"ok": 1}
    assert first.call_count == 1


@respx.mock
async def test_all_urls_exhausted_raises_last_exception():
    respx.post("https://u1/v1/messages").mock(return_value=httpx.Response(503))
    respx.post("https://u2/v1/messages").mock(return_value=httpx.Response(503))

    async def do(client: httpx.AsyncClient):
        r = await client.post("/v1/messages", json={})
        r.raise_for_status()
        return r.json()

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await call_with_failover(
            do,
            base_urls=["https://u1", "https://u2"],
            max_retries=1,
            base_delay_s=0.0,
            max_delay_s=0.0,
        )
    assert exc_info.value.response.status_code == 503


@respx.mock
async def test_non_retriable_error_does_not_retry():
    route = respx.post("https://u1/v1/messages").mock(return_value=httpx.Response(400))

    async def do(client: httpx.AsyncClient):
        r = await client.post("/v1/messages", json={})
        r.raise_for_status()
        return r.json()

    with pytest.raises(httpx.HTTPStatusError):
        await call_with_failover(
            do,
            base_urls=["https://u1"],
            max_retries=3,
            base_delay_s=0.0,
            max_delay_s=0.0,
        )
    assert route.call_count == 1


def test_classify_anthropic_prompt_too_long_still_works():

    e = Exception("prompt is too long: max_tokens exceeded")
    assert classify_withheld_error(e) == WithheldKind.PROMPT_TOO_LONG


def test_classify_openai_context_length_exceeded():
    e = Exception("Error: context_length_exceeded")
    assert classify_withheld_error(e) == WithheldKind.PROMPT_TOO_LONG


def test_classify_openai_rate_limit():
    e = Exception("HTTP 429 rate_limit_exceeded")
    assert classify_withheld_error(e) == WithheldKind.RATE_LIMITED


def test_classify_openai_invalid_model_returns_unknown():

    e = Exception("invalid_request_error: Invalid model name passed")
    assert classify_withheld_error(e) == WithheldKind.UNKNOWN


def test_classify_unknown_error():
    e = Exception("some random network blip")
    assert classify_withheld_error(e) == WithheldKind.UNKNOWN
