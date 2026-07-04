"""model zoo 本地缓存 + 版本锁(sha256)。

缓存目录:默认 ~/.cache/praxis_virtualcell/model_zoo/<model_name>/<asset>,root 可 override。
check():资产存在性 + 可选 sha256 版本锁。缺失或 sha 不匹配 → AssetStatus(available=False),
fail-closed,绝不 silent accept(篡改/版本错的权重宁可判不可用)。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_ROOT = Path.home() / ".cache" / "praxis_virtualcell" / "model_zoo"


@dataclass
class AssetStatus:
    available: bool
    path: str | None
    reason: str


class ModelCache:
    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or _DEFAULT_ROOT)

    def asset_path(self, model_name: str, asset: str) -> Path:
        """命名空间化路径:<root>/<model_name>/<asset>(不同模型互不覆盖)。"""
        return self.root / model_name / asset

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def check(self, model_name: str, asset: str, *, sha256: str | None = None) -> AssetStatus:
        """资产存在性 + 可选 sha256 锁。缺失/不匹配 → available=False(fail-closed)。"""
        p = self.asset_path(model_name, asset)
        if not p.is_file():
            return AssetStatus(False, None, f"asset_not_found: {p}")
        if sha256 is not None:
            actual = self._sha256(p)
            if actual != sha256:
                return AssetStatus(False, None,
                                   f"sha256_mismatch: expected {sha256[:12]}… got {actual[:12]}…")
        return AssetStatus(True, str(p), "ok")
