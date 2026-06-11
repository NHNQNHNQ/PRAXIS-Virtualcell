"""mime 检测:python-magic 探出 → fallback octet-stream。

production .53 装 libmagic1。dev/test 机可能没装(失败时静默兜底)。
"""

from __future__ import annotations

_OCTET_STREAM = "application/octet-stream"

try:
    import magic
    _MAGIC = magic.Magic(mime=True)
except Exception:  # libmagic 缺 / python-magic 没装 / 其他启动失败
    _MAGIC = None


def detect(path: str) -> str:
    """检 path 内容首部 mime。失败 → application/octet-stream。"""
    if _MAGIC is None:
        return _OCTET_STREAM
    try:
        out = _MAGIC.from_file(path)
        return out or _OCTET_STREAM
    except Exception:
        return _OCTET_STREAM
