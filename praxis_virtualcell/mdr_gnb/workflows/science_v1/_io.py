"""Science v1 冻结/导出共享小工具:sha256 + 确定性 CSV/JSON 写。

个人项目,保持精简:只放冻结脚本真正复用的三个函数,重跑得到字节一致的产物。
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


def sha256(path: str | Path) -> str:
    """算文件 sha256 十六进制摘要(分块读,避免大文件占内存)。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: str | Path, fieldnames: list[str], rows: list[dict]) -> int:
    """确定性写 CSV:固定列序、缺字段留空(.get)、CRLF 换行(csv 默认,稳定可复现)。返回写入行数。"""
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    return len(rows)


def dump_json(path: str | Path, obj) -> None:
    """确定性 JSON:sort_keys + 2 空格缩进 + 末尾换行 + 保留中文(ensure_ascii=False)。"""
    Path(path).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
