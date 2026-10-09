from praxis2.md.pricing import compute_md_cost_li


def test_zero_hours_zero_cost():
    assert compute_md_cost_li(0, 0, 1, 10000, 500) == 0


def test_gpu_only_no_cpu_overage():
    # gpu_h=2 × 10000 = 20000;cpu_h=0.5 < free=1 → 不扣 CPU
    assert compute_md_cost_li(2, 0.5, 1, 10000, 500) == 20000


def test_cpu_overage_charged():
    # gpu_h=1 × 10000 = 10000;cpu_h=3,溢 (3-1)=2 × 500 = 1000;total=11000
    assert compute_md_cost_li(1, 3, 1, 10000, 500) == 11000


def test_ceil_to_int_li():
    # gpu_h=0.55 × 7777 = 4277.35 → ceil = 4278
    assert compute_md_cost_li(0.55, 0, 1, 7777, 500) == 4278
