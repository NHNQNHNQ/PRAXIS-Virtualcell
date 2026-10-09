"""M2.1 投稿前补强 L1:perturbation-level bootstrap CI(纯 Python,Mac 可跑)。

给 learned-governance 的核心数字加 95% CI:对 151 ledger 的**固定 OOF 预测 / frozen 决策**做
**扰动级有放回 bootstrap**(每次重采样 151 个扰动、重算指标),取 percentile CI。

诚实口径:这是对**固定 OOF 预测**(R2/R3,泛化)与**固定 frozen 决策**(R7,in-sample 回放)做扰动级
bootstrap —— 评估的是**指标在扰动采样下的稳定性**,**不含模型重训(CV 重做)的不确定性**(重采样会让
同一扰动既进 train 又进 test → 泄漏,故刻意固定预测、只 bootstrap 指标)。pert-level ≠ per-cell。

复用:reliability_model(OOF/AUROC)、abstain_head(risk-coverage)、learned_reliability(frozen 决策)、
mode_compare 同口径(bad=底 bad_quantile;rule=disagreement>rule_threshold;learned=frozen abstain/downgrade)。
"""
from __future__ import annotations

import random as _random

from praxis_virtualcell.governance import abstain_head as ah
from praxis_virtualcell.governance import learned_reliability as L
from praxis_virtualcell.governance import ledger_features as lf
from praxis_virtualcell.governance import reliability_model as rm

_NAN = float("nan")


def _isnan(x):
    return x != x


def _pct(vals, q):
    """percentile(线性插值)。vals 非空。"""
    s = sorted(vals)
    if not s:
        return _NAN
    i = q * (len(s) - 1)
    lo = int(i)
    hi = min(lo + 1, len(s) - 1)
    frac = i - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def _quantile(vals, q):
    s = sorted(v for v in vals if not _isnan(v))
    if not s:
        return _NAN
    return s[max(0, min(len(s) - 1, int(q * (len(s) - 1))))]


def _prepare(entries):
    """预计算每扰动的固定标量:OOF 预测 dp、真 dp、disagreement、rule/learned 软风险 flag。"""
    oof, y = rm.cv_reliability(entries)              # 固定 OOF 预测(泛化口径)
    X, _ = rm._matrix(entries)
    dis = [r[0] for r in X]                          # disagreement_score(nan-filled)
    rows = lf.extract_features(entries)
    rule_flag, learned_flag = [], []
    for r in rows:
        d = r.get("disagreement_score")
        rf = d is not None and d > 0.5              # rule:固定 0.5 阈值
        rule_flag.append(rf)
        lr = L.score(r)                              # frozen artifact 决策
        if lr.get("fallback"):
            learned_flag.append(rf)                 # fallback → rule
        else:
            learned_flag.append(lr["abstain_decision"] in ("abstain", "downgrade"))
    return oof, y, dis, rule_flag, learned_flag


def _metrics(idx, oof, y, dis, rule_flag, learned_flag, *, bad_quantile=0.25, rule_threshold=0.5):
    """在(可重复的)索引列表 idx 上重算所有指标。n_bad/n_good 为 0 → None(跳过该迭代)。"""
    ys = [y[i] for i in idx]
    thr = _quantile(ys, bad_quantile)
    bad = [(not _isnan(y[i]) and y[i] <= thr) for i in idx]      # mode_compare 同口径
    n_bad = sum(bad)
    n_good = len(idx) - n_bad
    if n_bad == 0 or n_good == 0:
        return None

    bad01 = [1 if b else 0 for b in bad]
    # --- 泛化(OOF):bad-pert AUROC,score 越大越像 bad ---
    learned_auc_score = [(-oof[i] if not _isnan(oof[i]) else 0.0) for i in idx]
    dis_auc_score = [dis[i] for i in idx]
    auroc_learned = rm._auroc(learned_auc_score, bad01)
    auroc_dis = rm._auroc(dis_auc_score, bad01)
    # --- 泛化(OOF):risk-coverage AUC,score 越大越保留 ---
    yi = [y[i] for i in idx]
    rc_learned = ah.rc_auc(ah.risk_coverage([oof[i] for i in idx], yi))
    rc_dis = ah.rc_auc(ah.risk_coverage([(-dis[i] if not _isnan(dis[i]) else _NAN) for i in idx], yi))
    # --- in-sample 回放:rule vs learned 软风险决策 ---
    wa_rule = sum(1 for j in range(len(idx)) if bad[j] and not rule_flag[idx[j]]) / n_bad
    wa_learned = sum(1 for j in range(len(idx)) if bad[j] and not learned_flag[idx[j]]) / n_bad
    rc_rule = sum(1 for j in range(len(idx)) if bad[j] and rule_flag[idx[j]]) / n_bad
    rc_learned_mc = sum(1 for j in range(len(idx)) if bad[j] and learned_flag[idx[j]]) / n_bad
    ru_learned = sum(1 for j in range(len(idx)) if not bad[j] and not learned_flag[idx[j]]) / n_good
    ua_learned = sum(1 for j in range(len(idx)) if not bad[j] and learned_flag[idx[j]]) / n_good

    return {
        "auroc_learned": auroc_learned,
        "auroc_disagreement": auroc_dis,
        "rc_auc_learned": rc_learned,
        "rc_auc_disagreement": rc_dis,
        "mc_wrong_accept_rule": wa_rule,
        "mc_wrong_accept_learned": wa_learned,
        "mc_risk_coverage_rule": rc_rule,
        "mc_risk_coverage_learned": rc_learned_mc,
        "mc_retained_utility_learned": ru_learned,
        "mc_unnecessary_abstain_learned": ua_learned,
    }


def _augment_diffs(m):
    """加 learned 相对 baseline 的差值(正 = learned 更优方向)。"""
    out = dict(m)
    out["auroc_diff_learned_minus_disagreement"] = m["auroc_learned"] - m["auroc_disagreement"]
    out["rc_auc_diff_learned_minus_disagreement"] = m["rc_auc_learned"] - m["rc_auc_disagreement"]
    out["mc_wrong_accept_reduction"] = m["mc_wrong_accept_rule"] - m["mc_wrong_accept_learned"]
    out["mc_risk_coverage_gain"] = m["mc_risk_coverage_learned"] - m["mc_risk_coverage_rule"]
    return out


def run(entries, *, b=2000, seed=0, bad_quantile=0.25, rule_threshold=0.5):
    """扰动级 bootstrap CI。返回 {n, n_bootstrap, seed, bad_quantile, method, metrics}。

    point = 原始全样本估计(应复现 finding);ci_lo/ci_hi = bootstrap 2.5%/97.5% percentile。
    """
    oof, y, dis, rule_flag, learned_flag = _prepare(entries)
    n = len(entries)
    full = list(range(n))
    args = (oof, y, dis, rule_flag, learned_flag)
    kw = {"bad_quantile": bad_quantile, "rule_threshold": rule_threshold}

    point = _augment_diffs(_metrics(full, *args, **kw))
    dists = {k: [] for k in point}
    rng = _random.Random(seed)
    n_valid = 0
    for _ in range(b):
        idx = [rng.randrange(n) for _ in range(n)]
        mm = _metrics(idx, *args, **kw)
        if mm is None:
            continue
        mm = _augment_diffs(mm)
        for k, v in mm.items():
            dists[k].append(v)
        n_valid += 1

    metrics = {}
    for k, pv in point.items():
        d = dists[k]
        metrics[k] = {
            "point": pv,
            "median": _pct(d, 0.5),
            "ci_lo": _pct(d, 0.025),
            "ci_hi": _pct(d, 0.975),
            "n_boot": len(d),
        }
    return {
        "n": n,
        "n_bootstrap": b,
        "n_valid": n_valid,
        "seed": seed,
        "bad_quantile": bad_quantile,
        "method": ("perturbation-level bootstrap over fixed OOF predictions (R2/R3, generalization) and "
                   "frozen decisions (R7, in-sample replay); metric sampling stability only, no CV retraining"),
        "metrics": metrics,
    }
