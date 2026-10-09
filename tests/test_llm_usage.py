from praxis2.llm.usage import UsageTracker, estimate_tokens


def test_tracker_accumulates_per_model_and_cost():
    t = UsageTracker(price_per_mtok={"m1": (3.0, 15.0)})  # (in, out) USD / 1M tok
    t.add("m1", {"input_tokens": 1000, "output_tokens": 500})
    t.add("m1", {"input_tokens": 1000, "output_tokens": 0, "cache_read_input_tokens": 200})
    total = t.total()
    assert total["input_tokens"] == 2000
    assert total["output_tokens"] == 500
    assert total["cache_read_input_tokens"] == 200

    assert round(t.cost_usd(), 6) == round(2000 / 1e6 * 3 + 500 / 1e6 * 15, 6)


def test_cost_unknown_when_no_price():
    t = UsageTracker(price_per_mtok={})
    t.add("m9", {"input_tokens": 10, "output_tokens": 1})
    assert t.cost_usd() == 0.0
    assert t.cost_is_known() is False


def test_estimate_prefers_api_then_falls_back():
    msgs = [{"role": "user", "content": "abcd" * 100}]

    got = estimate_tokens(msgs, tools=None, api_count=lambda: 1234)
    assert got == (1234, False)

    def boom():
        raise RuntimeError("count_tokens unavailable")

    n, is_est = estimate_tokens(msgs, tools=None, api_count=boom)
    assert is_est is True and n > 0

    n2, is_est2 = estimate_tokens(msgs, tools=None, api_count=None)
    assert is_est2 is True and n2 > 0


def test_should_auto_compact_threshold():
    from praxis2.llm.usage import should_auto_compact

    assert should_auto_compact(used=190_000, window=200_000, buffer=13_000) is True
    assert should_auto_compact(used=100_000, window=200_000, buffer=13_000) is False
