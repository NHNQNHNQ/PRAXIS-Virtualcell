"""存储抽象。三类后端:KV(redis 类)/ Blob(大对象)/ Meta(pg 行)。
所有访问强制带 user_id 命名空间——无 user_id 即编程错误(总纲 §11.6)。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Namespace:
    user_id: str
    scope: str  # session | memory | transcript | ...

    def __post_init__(self) -> None:
        if not self.user_id:
            raise ValueError("Namespace.user_id 不能为空(多租户隔离,总纲 §11.6)")
        if not self.scope:
            raise ValueError("Namespace.scope 不能为空")

    def key(self, k: str) -> str:
        return f"{self.user_id}/{self.scope}/{k}"


class Store(ABC):
    """单一接口聚合 KV/Blob/Meta;后端各自实现。"""

    @abstractmethod
    async def kv_set(
        self, ns: Namespace, key: str, value: bytes, ttl_s: float | None = None
    ) -> None: ...

    @abstractmethod
    async def kv_get(self, ns: Namespace, key: str) -> bytes | None: ...

    @abstractmethod
    async def kv_delete(self, ns: Namespace, key: str) -> None: ...

    @abstractmethod
    async def blob_put(self, ns: Namespace, key: str, data: bytes) -> str: ...

    @abstractmethod
    async def blob_get(self, ns: Namespace, key: str) -> bytes | None: ...

    @abstractmethod
    async def blob_append(self, ns: Namespace, key: str, chunk: bytes) -> None:
        """原子追加 chunk 到 blob 尾部(key 不存在则创建)。

        与 blob_put 不同:append 不读旧值不重写整盘,实现层保证并发原子。
        语义:字节拼接(caller 负责行分隔等结构,推荐 b'\\n' 终止符)。
        用途:session transcript O(1) append-only(总纲 §7.4.3,反 O(K²) read-modify-write)。
        """
        ...

    @abstractmethod
    async def meta_upsert(self, table: str, row: dict) -> None: ...

    @abstractmethod
    async def meta_get(self, table: str, user_id: str, pk: str) -> dict | None: ...

    @abstractmethod
    async def meta_list(self, table: str, user_id: str) -> list[dict]: ...
