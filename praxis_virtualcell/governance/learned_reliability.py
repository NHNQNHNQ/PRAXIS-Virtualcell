"""Load frozen learned-governance artifacts and score inference features. Missing artifacts or schema mismatch
return fallback=True for rule mode. Reject labels such as delta_pearson in model_features; artifact metadata
carries ledger sha256 and version.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
FEATURE_SCHEMA_VERSION = "v0.3.0"
_FORBIDDEN = ("delta_pearson", "per_predictor_delta_pearson", "best_predictor")


def load_artifacts(art_dir=ARTIFACT_DIR):
    try:
        rel = json.loads((Path(art_dir) / "reliability_model_v0_3.json").read_text(encoding="utf-8"))
        ab = json.loads((Path(art_dir) / "abstain_head_v0_3.json").read_text(encoding="utf-8"))
        return rel, ab
    except (FileNotFoundError, json.JSONDecodeError):
        return None, None


def score(features: dict, *, art_dir=ARTIFACT_DIR) -> dict:
    """Score learned reliability; missing/incompatible artifacts return fallback=True with a reason. Enforce the
    no-label feature boundary.
    """
    assert not (set(features) & set(_FORBIDDEN)), "runtime features must not contain labels (leakage)"
    rel, ab = load_artifacts(art_dir)
    if rel is None or ab is None:
        return {"fallback": True, "reason": "artifact_missing"}
    if rel.get("feature_schema_version") != FEATURE_SCHEMA_VERSION:
        return {"fallback": True, "reason": "schema_mismatch",
                "expected": FEATURE_SCHEMA_VERSION, "got": rel.get("feature_schema_version")}

    if not all(rel.get(k) for k in ("features", "mean", "std", "weights")):
        return {"fallback": True, "reason": "incomplete_artifact"}
    _content = {k: rel.get(k) for k in ("features", "mean", "std", "weights", "lam")}
    _calc = hashlib.sha256(json.dumps(_content, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    if rel.get("content_sha256") != _calc:
        return {"fallback": True, "reason": "integrity_mismatch"}

    from praxis_virtualcell.governance.reliability_model import predict_dp

    feats = rel["features"]
    used = {f: (features.get(f) is not None) for f in feats}
    rscore = predict_dp(rel, features)
    if rscore < ab["abstain_threshold_dp"]:
        decision = "abstain"
    elif rscore < ab["downgrade_threshold_dp"]:
        decision = "downgrade"
    else:
        decision = "accept"
    return {
        "fallback": False,
        "reliability_score": rscore,
        "abstain_score": 1.0 - rscore,
        "abstain_decision": decision,             # accept / downgrade / abstain
        "features_used": used,
        "model_version": rel.get("model_version"),
        "feature_schema_version": rel.get("feature_schema_version"),

        "artifact_sha256": _sha(Path(art_dir) / "reliability_model_v0_3.json"),
        "abstain_artifact_sha256": _sha(Path(art_dir) / "abstain_head_v0_3.json"),
    }
