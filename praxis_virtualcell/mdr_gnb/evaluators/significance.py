"""ST 为单位的显著性检验(配对置换)+ 效应量自助 CI + 预注册参数加载。

每个 ST 聚合成一个 VME 观测,model 与 rule 在同一 ST 上配对;置换其配对内符号得零分布。
效应量 = 各 ST(model-rule VME 差)均值(负=model 更优)。预注册参数冻结在 preregistration.yaml。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml

_PRE_PATH = Path(__file__).resolve().parent / "preregistration.yaml"


def load_preregistration(path: Path | None = None) -> dict:
    """加载 G2 锚点门预注册参数(冻结)。"""
    with open(path or _PRE_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def st_level_vme(st, y_true, y_pred, cc_map=None) -> dict:
    """每个聚合单元一个 VME 观测(该单元内真R株被判非R的比例);无真R的单元跳过。

    cc_map=None(默认)→ 按精确 ST 聚合(旧行为,向后兼容,逐字不变)。
    传入 cc_map(ST→CC)→ 按克隆复合体聚合:同一 CC 的成员是近缘克隆群、非独立样本,
    应贡献**一个** VME 观测(把该 CC 内所有株的 y 一起汇总算,不是先按 ST 算再平均),
    以消除置换检验的伪重复(pseudoreplication)。无 CC 映射的 ST 回退按自身聚合。
    """
    st = np.asarray(st)
    yt = np.asarray(y_true, int)
    yp = np.asarray(y_pred, int)
    if cc_map:
        unit = np.array([cc_map.get(str(s), str(s)) for s in st])
    else:
        unit = st
    out: dict[str, float] = {}
    for u in np.unique(unit):
        m = (unit == u) & (yt == 1)
        if m.any():
            out[str(u)] = float((yp[m] == 0).mean())
    return out


def align_st_vme(model_vme: dict, rule_vme: dict):
    """把两方 per-ST VME 对齐到共同 ST 键,返回 (keys, model数组, rule数组)。"""
    keys = sorted(set(model_vme) & set(rule_vme))
    m = np.array([model_vme[k] for k in keys], dtype=float)
    r = np.array([rule_vme[k] for k in keys], dtype=float)
    return keys, m, r


def paired_permutation_test(model_vals, rule_vals, sts=None, n_perm: int = 10000, seed: int = 0) -> dict:
    """配对置换检验(单侧:model VME 显著低于 rule)。

    model_vals/rule_vals 为已对齐的 per-ST 数组;sts 仅作占位(保留签名)。
    p = 置换零分布中均值 ≤ 观测均值 的比例(观测越负越显著)。
    """
    m = np.asarray(model_vals, float)
    r = np.asarray(rule_vals, float)
    diff = m - r
    obs = float(diff.mean()) if len(diff) else float("nan")
    if len(diff) == 0:
        return {"mean_diff": float("nan"), "p_value": float("nan"), "n_st": 0}
    rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(n_perm):
        signs = rng.choice([-1.0, 1.0], size=len(diff))
        if (signs * diff).mean() <= obs:
            cnt += 1
    return {"mean_diff": obs, "p_value": (cnt + 1) / (n_perm + 1), "n_st": int(len(diff))}


def bootstrap_effect_ci(diff, n_boot: int = 10000, seed: int = 0, alpha: float = 0.05):
    """效应量(per-ST 差均值)的自助置信区间。"""
    d = np.asarray(diff, float)
    rng = np.random.default_rng(seed)
    means = np.array([rng.choice(d, size=len(d), replace=True).mean() for _ in range(n_boot)])
    return float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))
