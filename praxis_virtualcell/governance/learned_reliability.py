"""M2.1 Step6:runtime learned reliability/abstain —— 加载冻结 artifact,对推理特征算可靠性/弃权决策。

**双模式安全**:artifact 缺失 / schema 不匹配 → 返回 `fallback=True`(caller 退回 rule mode),系统不崩(fail-closed)。
**无泄漏**:只接受 model_features(disagreement / OOD flag / n_zero),**断言**不含 label(delta_pearson 等)。
artifact 冻结在 governance/artifacts/(由 freeze_artifacts.py 导出,带 ledger sha256 + version,可复现)。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
FEATURE_SCHEMA_VERSION = "v0.3.0"
_FORBIDDEN = ("delta_pearson", "per_predictor_delta_pearson", "best_predictor")  # label,严禁进 runtime 特征


def load_artifacts(art_dir=ARTIFACT_DIR):
    try:
        rel = json.loads((Path(art_dir) / "reliability_model_v0_3.json").read_text(encoding="utf-8"))
        ab = json.loads((Path(art_dir) / "abstain_head_v0_3.json").read_text(encoding="utf-8"))
        return rel, ab
    except (FileNotFoundError, json.JSONDecodeError):
        return None, None


def score(features: dict, *, art_dir=ARTIFACT_DIR) -> dict:
    """learned 决策。artifact 缺失/schema 不匹配 → {"fallback": True, "reason": ...}。无泄漏断言。"""
    assert not (set(features) & set(_FORBIDDEN)), "runtime 特征不得含 label(泄漏)"
    rel, ab = load_artifacts(art_dir)
    if rel is None or ab is None:
        return {"fallback": True, "reason": "artifact_missing"}
    if rel.get("feature_schema_version") != FEATURE_SCHEMA_VERSION:
        return {"fallback": True, "reason": "schema_mismatch",
                "expected": FEATURE_SCHEMA_VERSION, "got": rel.get("feature_schema_version")}
    # 完整性:必需字段齐 + content hash 匹配(篡改 weights / 字段不全 → fallback,主动防护)
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
        "abstain_score": 1.0 - rscore,            # risk = 1 − 预测可靠性
        "abstain_decision": decision,             # accept / downgrade / abstain
        "features_used": used,                    # 各特征是否真到位(否则 predict_dp 用训练均值填)
        "model_version": rel.get("model_version"),
        "feature_schema_version": rel.get("feature_schema_version"),
        # 冻结治理证据:每个 learned 决策可追溯到具体不可变 artifact 内容哈希
        "artifact_sha256": _sha(Path(art_dir) / "reliability_model_v0_3.json"),
        "abstain_artifact_sha256": _sha(Path(art_dir) / "abstain_head_v0_3.json"),
    }
