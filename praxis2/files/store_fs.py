"""本地 fs 流式存储。

布局:<root>/<user_id>/<file_id>      最终文件
      <root>/<user_id>/<file_id>.part  上传中(异常时清掉)
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

_CHUNK_READ = 64 * 1024   # 64 KB read 块


class FsStore:
    """本地文件系统存储,支持流式写入、范围读取和异常清理。"""

    def __init__(self, root: str) -> None:
        """初始化存储,创建根目录。

        Args:
            root: 存储根路径
        """
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _user_dir(self, user_id: str) -> Path:
        """获取用户目录,不存在时创建。"""
        d = self._root / user_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _final_path(self, user_id: str, file_id: str) -> Path:
        """获取最终文件路径。"""
        return self._user_dir(user_id) / file_id

    def _part_path(self, user_id: str, file_id: str) -> Path:
        """获取上传中文件(.part)路径。"""
        return self._user_dir(user_id) / f"{file_id}.part"

    async def write_stream(
        self,
        user_id: str,
        file_id: str,
        chunks: AsyncIterator[bytes],
    ) -> int:
        """流式写入到.part文件,成功后原子性mv到final,异常时清理.part。

        Args:
            user_id: 用户ID
            file_id: 文件ID
            chunks: 字节块异步迭代器

        Returns:
            写入的总字节数

        Raises:
            任何来自chunks的异常都会清理.part并重新抛出
        """
        part = self._part_path(user_id, file_id)
        final = self._final_path(user_id, file_id)
        total = 0
        try:
            with open(part, "wb") as f:
                async for chunk in chunks:
                    if chunk:
                        f.write(chunk)
                        total += len(chunk)
            os.rename(part, final)
            return total
        except BaseException:
            # 任何异常(含 KeyboardInterrupt)→ 删半文件
            try:
                if part.exists():
                    part.unlink()
            except OSError:
                pass
            raise

    async def read_stream(
        self,
        user_id: str,
        file_id: str,
        start: int = 0,
        end: int | None = None,
    ) -> AsyncIterator[bytes]:
        """读取文件[start, end]闭区间的字节流。

        Args:
            user_id: 用户ID
            file_id: 文件ID
            start: 起始字节位置(含), 默认0
            end: 结束字节位置(含), 默认None(到文件末尾)

        Yields:
            字节块
        """
        path = self._final_path(user_id, file_id)
        size = path.stat().st_size
        if end is None or end >= size:
            end = size - 1
        if start > end:
            return
        remaining = end - start + 1
        with open(path, "rb") as f:
            f.seek(start)
            while remaining > 0:
                chunk = f.read(min(_CHUNK_READ, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    async def delete(self, user_id: str, file_id: str) -> None:
        """删除文件(幂等:文件不存在不抛异常)。

        Args:
            user_id: 用户ID
            file_id: 文件ID
        """
        path = self._final_path(user_id, file_id)
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    def exists(self, user_id: str, file_id: str) -> bool:
        """检查文件是否存在。

        Args:
            user_id: 用户ID
            file_id: 文件ID

        Returns:
            文件存在返回True,否则False
        """
        return self._final_path(user_id, file_id).is_file()

    def get_size(self, user_id: str, file_id: str) -> int:
        """获取文件大小(字节)。

        Args:
            user_id: 用户ID
            file_id: 文件ID

        Returns:
            文件大小(字节)
        """
        return self._final_path(user_id, file_id).stat().st_size
