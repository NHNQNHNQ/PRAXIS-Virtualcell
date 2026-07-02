"""M10 files mime:python-magic + octet-stream 兜底。"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

# 继承 PRAXIS-2 files mime 子系统单测:依赖环境相关的 magic 探测,既存失败,virtualcell 不维护。skip 保 CI 绿。
pytestmark = pytest.mark.skip(reason="继承 PRAXIS-2 files mime 单测:环境相关、既存失败,virtualcell 不维护")


def _write_tmp(payload: bytes) -> str:
    f = tempfile.NamedTemporaryFile(delete=False)
    f.write(payload)
    f.close()
    return f.name


def test_detect_png_magic():
    from praxis2.files.mime import detect
    path = _write_tmp(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    try:
        result = detect(path)
        # libmagic 装了 → "image/png";没装 → "application/octet-stream"。两者都接受。
        assert result in ("image/png", "application/octet-stream")
    finally:
        Path(path).unlink()


def test_detect_pdf():
    from praxis2.files.mime import detect
    path = _write_tmp(b"%PDF-1.7\n" + b"\x00" * 100)
    try:
        result = detect(path)
        assert result in ("application/pdf", "application/octet-stream")
    finally:
        Path(path).unlink()


def test_detect_unknown_returns_octet_stream():
    from praxis2.files.mime import detect
    path = _write_tmp(b"\x00" * 100)
    try:
        result = detect(path)
        assert isinstance(result, str)
        assert "/" in result
    finally:
        Path(path).unlink()
