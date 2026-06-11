from praxis2.spawn.pricing import compute_cost_li


def test_zero_tokens_zero_cost():
    assert compute_cost_li(0, 0, 1500, 6000) == 0


def test_small_input_only():
    # 1000 input tokens × 1500 li/M = 1.5 li → ceil = 2
    assert compute_cost_li(1000, 0, 1500, 6000) == 2


def test_mixed_in_out():
    # 100k in × 1500/M + 50k out × 6000/M = 150 + 300 = 450 li
    assert compute_cost_li(100_000, 50_000, 1500, 6000) == 450


def test_ceil_rounds_up_fractional_li():
    # 1 input token × 1500/M = 0.0015 li → ceil = 1
    assert compute_cost_li(1, 0, 1500, 6000) == 1
