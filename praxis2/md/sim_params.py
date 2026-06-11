"""5 sim_type 必填字段校验 — 返 err str(handler 转 400),None=OK。"""
from __future__ import annotations


class SimParamsError(Exception):
    pass


# (field_name, type 校验函数)
_SMD_REQUIRED: list[tuple[str, type | tuple]] = [
    ("pull_coord_geometry", str),
    ("pull_rate", (int, float)),
    ("pull_k1", (int, float)),
    ("pull_group1_name", str),
    ("pull_group2_name", str),
]

_META_REQUIRED: list[tuple[str, type | tuple]] = [
    ("plumed_file_id", str),
]

_UMBRELLA_REQUIRED: list[tuple[str, type | tuple]] = [
    ("pull_group1_name", str),
    ("pull_group2_name", str),
    ("pull_rate", (int, float)),
    ("pull_k1", (int, float)),
    ("window_spacing_nm", (int, float)),
    ("n_windows", int),
]

_REMD_REQUIRED: list[tuple[str, type | tuple]] = [
    ("temperatures", list),        # [300, 310, 320, 330, ...]
    ("exchange_interval", int),    # steps 间隔
]

_SUPPORTED = {"standard", "smd_pulling", "metadynamics", "umbrella_sampling", "remd"}


def validate_sim_params(sim_type: str, sim_params: dict) -> str | None:
    """返 None=OK,否则返错误字符串(supplied to handler 转 400)。"""
    if sim_type not in _SUPPORTED:
        return "unsupported_sim_type"
    if sim_type == "standard":
        return None
    if sim_type == "smd_pulling":
        return _check_required(sim_params, _SMD_REQUIRED)
    if sim_type == "metadynamics":
        return _check_required(sim_params, _META_REQUIRED)
    if sim_type == "umbrella_sampling":
        err = _check_required(sim_params, _UMBRELLA_REQUIRED)
        if err:
            return err
        # n_windows 范围检查
        if not (2 <= sim_params["n_windows"] <= 100):
            return "type: n_windows"
        return None
    if sim_type == "remd":
        err = _check_required(sim_params, _REMD_REQUIRED)
        if err:
            return err
        temps = sim_params["temperatures"]
        if not isinstance(temps, list) or len(temps) < 2:
            return "type: temperatures"
        if not all(isinstance(t, (int, float)) for t in temps):
            return "type: temperatures"
        return None
    return None


def _check_required(
    params: dict, required: list[tuple[str, type | tuple]],
) -> str | None:
    for name, expect_type in required:
        if name not in params:
            return f"missing: {name}"
        v = params[name]
        if not isinstance(v, expect_type):
            return f"type: {name}"
    return None
