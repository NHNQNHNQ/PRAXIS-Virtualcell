"""MD 作业计费 — GPU 小时 × 单价 + CPU 溢额小时 × 单价,ceil 到整数 li。"""
import math


def compute_md_cost_li(
    gpu_hours: float, cpu_hours: float,
    free_cpu_hours: float,
    price_gpu_per_h_li: int, price_cpu_per_h_li: int,
) -> int:
    """gpu_h × p_gpu + max(0, cpu_h - free) × p_cpu, ceil 到 li。"""
    cpu_overage = max(0.0, cpu_hours - free_cpu_hours)
    raw = gpu_hours * price_gpu_per_h_li + cpu_overage * price_cpu_per_h_li
    return math.ceil(raw)
