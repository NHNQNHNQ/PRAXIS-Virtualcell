"""per-call provenance hash:给每个 model call 记 name/version/input-hash/output-hash/evidence,
并校验完整性(Gate A 用)。确定性 canonical sha256,无 LLM。"""
from __future__ import annotations

import hashlib
import json
import re

_REQUIRED = ("model_name", "model_version", "input_hash", "output_hash")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _canon_sha256(obj) -> str:
    """canonical json sha256(与 runtime.py trace_id 同模式,确定性)。"""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


def compute_call_provenance(model_name: str, model_version: str | None,
                            model_input, output, evidence) -> dict:
    """产 per_call 记录。input/output 走 canonical sha256(确定性)。

    input_hash 语义:reject 分支的 input 是原始 request、failed 分支可能是空 dict
    (prepare_input 未成功),success 分支是 prepare_input 产出——供审计者理解 input_hash 来源。
    注:numpy 标量经 default=str 会静默转字符串,入 hash 前建议先 .tolist()/float()。
    """
    return {
        "model_name": model_name,
        "model_version": model_version,
        "input_hash": _canon_sha256(model_input),
        "output_hash": _canon_sha256(output),
        "evidence_source": list(evidence) if evidence else [],
    }


def check_call_provenance(per_call) -> list[str]:
    """返回缺失、为空或 hash 格式无效的必需键清单(空=完整)。"""
    if not isinstance(per_call, dict):
        return list(_REQUIRED)
    invalid = [key for key in ("model_name", "model_version") if not per_call.get(key)]
    invalid.extend(
        key for key in ("input_hash", "output_hash")
        if not isinstance(per_call.get(key), str) or not _SHA256.fullmatch(per_call[key])
    )
    return invalid
