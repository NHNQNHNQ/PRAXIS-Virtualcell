"""LLM 调用费用计算 — input/output token × 单价(li per 1M tokens)。"""
import math


def compute_cost_li(
    tokens_in: int, tokens_out: int,
    price_in_per_m: int, price_out_per_m: int,
) -> int:
    """tokens × 单价 / 1M, ceil 到整数 li。不足 1 li 也扣 1。"""
    if tokens_in <= 0 and tokens_out <= 0:
        return 0
    cost_micro = tokens_in * price_in_per_m + tokens_out * price_out_per_m
    return math.ceil(cost_micro / 1_000_000)
