"""M10 files security:filename sanitize。"""
from __future__ import annotations


def test_sanitize_keeps_chinese():
    from praxis2.files.security import sanitize_filename
    assert sanitize_filename("蛋白结构.pdb") == "蛋白结构.pdb"


def test_sanitize_strips_path_traversal():
    from praxis2.files.security import sanitize_filename
    # ../ / / 反斜线 / null / 控制字符 都该剥
    assert sanitize_filename("../../etc/passwd") == "etcpasswd"
    assert sanitize_filename("a/b/c.pdb") == "abc.pdb"
    assert sanitize_filename("a\\b.pdb") == "ab.pdb"
    assert sanitize_filename("a\x00b.pdb") == "ab.pdb"


def test_sanitize_caps_200_chars():
    from praxis2.files.security import sanitize_filename
    long_name = "a" * 300 + ".pdb"
    out = sanitize_filename(long_name)
    assert len(out) <= 200


def test_sanitize_keeps_dots_underscore_hyphen():
    from praxis2.files.security import sanitize_filename
    assert sanitize_filename("data.v1.0_final-2.pdb") == "data.v1.0_final-2.pdb"


def test_sanitize_empty_returns_underscore():
    from praxis2.files.security import sanitize_filename
    # 全是危险字符 → 不应返空,返 "_"
    assert sanitize_filename("///") == "_"
