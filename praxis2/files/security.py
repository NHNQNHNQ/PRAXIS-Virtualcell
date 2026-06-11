"""文件名清洗:去 path traversal / 控制字符,保留中文 + 常用标点。"""

from __future__ import annotations

import re

# 允许字符:ASCII 字母数字 + 点 + 下划线 + 连字符 + 中日韩统一汉字 (一-鿿)。
# 去掉 / \ \0 等危险字符和控制字符。
_SAFE_RE = re.compile(r"[A-Za-z0-9._\-一-鿿]+")
_MAX_LEN = 200


def sanitize_filename(name: str) -> str:
    """剥不安全字符,截断 200 字符。空结果返 '_' 防 fs 路径空。"""
    if not name:
        return "_"

    # 用正则提取所有安全字符段
    pieces = _SAFE_RE.findall(name)
    cleaned = "".join(pieces)

    # 去掉连续的点(防 .. path traversal)
    cleaned = re.sub(r"\.{2,}", ".", cleaned)

    # 去掉前导/尾随的点
    cleaned = cleaned.strip(".")

    if not cleaned:
        return "_"

    return cleaned[:_MAX_LEN]
