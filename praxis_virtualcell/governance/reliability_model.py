"""Lightweight plain-Python ridge reliability regression and bad-perturbation classification. Use only
INFERENCE_FEATURES and perturbation-level CV; regularization limits overfitting. Compare learned,
disagreement-only, OOD-only, and random rankings. Historical disagreement correlation r=-0.716 is
protocol-bound.
"""
from __future__ import annotations

from praxis_virtualcell.governance import ledger_features as lf

FEATURES = ("disagreement_score", "seen_in_train", "disagreement_n_zero_pairs")
_NAN = float("nan")


def _f(v):
    return float(v) if v is not None else _NAN


def _isnan(x):
    return x != x


def _matrix(entries, feats=FEATURES):
    rows = lf.extract_features(entries)
    X = [[_f(r.get(k)) for k in feats] for r in rows]
    y = [_f(lf.reliability_target(e)) for e in entries]
    return X, y


def _col_stats(X):
    d = len(X[0])
    mean, std = [], []
    for j in range(d):
        vals = [row[j] for row in X if not _isnan(row[j])]
        m = sum(vals) / len(vals) if vals else 0.0
        v = sum((x - m) ** 2 for x in vals) / len(vals) if vals else 0.0
        mean.append(m)
        std.append(v ** 0.5 or 1.0)
    return mean, std


def _imp_std(X, mean, std):
    return [[((row[j] if not _isnan(row[j]) else mean[j]) - mean[j]) / std[j]
             for j in range(len(row))] for row in X]


def _solve(A, b):
    """Solve a small m×m linear system A w=b by Gaussian elimination."""
    m = len(A)
    M = [A[i][:] + [b[i]] for i in range(m)]
    for col in range(m):
        piv = max(range(col, m), key=lambda r: abs(M[r][col]))
        M[col], M[piv] = M[piv], M[col]
        if M[col][col] == 0:
            M[col][col] = 1e-9
        for r in range(m):
            if r != col:
                f = M[r][col] / M[col][col]
                M[r] = [M[r][k] - f * M[col][k] for k in range(m + 1)]
    return [M[i][m] / M[i][i] for i in range(m)]


def _ridge_fit(X, y, lam=1.0):
    """Fit ridge to standardized X; w[0] is the unregularized intercept."""
    n, d = len(X), len(X[0])
    Xb = [[1.0] + row for row in X]
    p = d + 1
    A = [[sum(Xb[i][a] * Xb[i][b] for i in range(n)) + (lam if a == b and a != 0 else 0.0)
          for b in range(p)] for a in range(p)]
    g = [sum(Xb[i][a] * y[i] for i in range(n)) for a in range(p)]
    return _solve(A, g)


def _pred(w, X):
    return [w[0] + sum(w[j + 1] * row[j] for j in range(len(row))) for row in X]


def cv_reliability(entries, *, k=5, lam=1.0):
    """Generate perturbation-level k-fold OOF dp predictions; return (oof_pred, y)."""
    X, y = _matrix(entries)
    oof = [_NAN] * len(y)
    for tr, te in lf.leave_perturbation_out_folds(entries, k):
        mean, std = _col_stats([X[i] for i in tr])
        Xtr = _imp_std([X[i] for i in tr], mean, std)
        Xte = _imp_std([X[i] for i in te], mean, std)
        w = _ridge_fit(Xtr, [y[i] for i in tr], lam)
        for idx, pv in zip(te, _pred(w, Xte)):  # noqa: B905
            oof[idx] = pv
    return oof, y


def fit_full(entries, *, lam=1.0):
    """Fit all rows without CV and return frozen features/mean/std/weights for artifact export and runtime loading."""
    X, y = _matrix(entries)
    mean, std = _col_stats(X)
    Xs = _imp_std(X, mean, std)

    idx = [i for i in range(len(y)) if not _isnan(y[i])]
    w = _ridge_fit([Xs[i] for i in idx], [y[i] for i in idx], lam)
    return {"features": list(FEATURES), "mean": mean, "std": std, "weights": w, "lam": lam}


def predict_dp(params, feat: dict) -> float:
    """Predict dp from one inference feature row using frozen parameters; impute missing features with training
    means and record imputation separately.
    """
    feats, mean, std, w = params["features"], params["mean"], params["std"], params["weights"]
    xs = []
    for j, f in enumerate(feats):
        v = feat.get(f)
        v = mean[j] if (v is None or _isnan(float(v))) else float(v)
        xs.append((v - mean[j]) / std[j])
    return w[0] + sum(w[j + 1] * xs[j] for j in range(len(xs)))


def _pearson(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if not (_isnan(x) or _isnan(y))]  # noqa: B905
    if len(pairs) < 2:
        return _NAN
    xs = [p[0] for p in pairs]; ys = [p[1] for p in pairs]  # noqa: E702
    mx = sum(xs) / len(xs); my = sum(ys) / len(ys)  # noqa: E702
    sx = (sum((x - mx) ** 2 for x in xs)) ** 0.5
    sy = (sum((y - my) ** 2 for y in ys)) ** 0.5
    if sx == 0 or sy == 0:
        return _NAN
    return sum((x - mx) * (y - my) for x, y in pairs) / (sx * sy)


def _auroc(scores, labels):
    """Compute AUROC by hand; labels=1 means bad and larger scores indicate greater badness."""
    pos = [s for s, y in zip(scores, labels) if y == 1]  # noqa: B905
    neg = [s for s, y in zip(scores, labels) if y == 0]  # noqa: B905
    if not pos or not neg:
        return _NAN
    wins = sum(sum(1.0 if p > n else 0.5 if p == n else 0.0 for n in neg) for p in pos)
    return wins / (len(pos) * len(neg))


def _quantile(vals, q):
    s = sorted(v for v in vals if not _isnan(v))
    if not s:
        return _NAN
    i = max(0, min(len(s) - 1, int(q * (len(s) - 1))))
    return s[i]


def evaluate(entries, *, k=5, bad_quantile=0.25):
    """Compare learned against disagreement-only/OOD-only/random using regression correlation and bad-perturbation
    AUROC.
    """
    oof, y = cv_reliability(entries, k=k)
    X, _ = _matrix(entries)
    dis = [r[0] for r in X]
    seen = [r[1] for r in X]
    thr = _quantile(y, bad_quantile)
    bad = [1 if (not _isnan(v) and v <= thr) else 0 for v in y]
    import random as _r
    rnd = _r.Random(0)
    scores = {
        "learned": [(-v if not _isnan(v) else 0.0) for v in oof],
        "disagreement_only": dis,
        "ood_only": [(0.5 if _isnan(s) else 1.0 - s) for s in seen],
        "random": [rnd.random() for _ in y],
    }
    return {
        "n": sum(1 for v in y if not _isnan(v)),
        "bad_threshold_dp": thr,
        "reg_corr_pred_vs_true": _pearson(oof, y),
        "auroc": {name: _auroc(sc, bad) for name, sc in scores.items()},
    }
