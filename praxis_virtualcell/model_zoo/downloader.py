"""下载契约(远端 gated)。给一条 registry 条目 → 解析 source → 目标/指认。

Phase 2 不真下载大模型:
- cobra_bundled_* / local:<relpath> → 本地已有 → status=resolved(fetch=none),直接指认路径。
- remote:<id> → 远端 ckpt(GEARS/scGPT,requires torch/gpu)→ status=requires_manual_fetch,
  available=False,fail-closed(不假装下载成功;真接入是 Phase 6)。
- 缺 source → ValueError(坏条目,不静默)。
"""
from __future__ import annotations

from pathlib import Path

# repo 根:此文件在 praxis_virtualcell/model_zoo/downloader.py → parents[2] = repo 根
_REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_source(entry: dict) -> dict:
    """返回 {status, available, ...}。status ∈ resolved | requires_manual_fetch。"""
    source = entry.get("source")
    if not source:
        raise ValueError(f"model_zoo 条目 {entry.get('name')} 缺 source 字段")

    if source.startswith("cobra_bundled"):
        # cobra 自带,由 wrapper 内部经 cobra 加载,无需下载
        return {"status": "resolved", "available": True, "fetch": "none",
                "path": None, "reason": "cobra-bundled asset, loaded via cobra"}

    if source.startswith("local:"):
        rel = source.split("local:", 1)[1]
        p = (_REPO_ROOT / rel)
        if not p.is_file():
            return {"status": "requires_manual_fetch", "available": False, "fetch": "manual",
                    "path": str(p), "reason": f"declared local asset missing: {rel}"}
        return {"status": "resolved", "available": True, "fetch": "none",
                "path": str(p), "reason": "local repo asset"}

    if source.startswith("remote:") or source.startswith("self_trained:"):
        # Phase 2 不真下载:远端权重/自训权重需人工获取(Phase 6/7 产品化)
        req = entry.get("requires", [])
        return {"status": "requires_manual_fetch", "available": False, "fetch": "manual",
                "path": None,
                "reason": f"remote/self-trained weights require manual fetch (requires={req}); "
                          "Phase 2 does not download large models"}

    raise ValueError(f"model_zoo 条目 {entry.get('name')} 无法识别 source scheme: {source}")
