from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Namespace:
    user_id: str
    scope: str  # session | memory | transcript | ...

    def __post_init__(self) -> None:
        if not self.user_id:
            raise ValueError("Namespace.user_id must not be empty")
        if not self.scope:
            raise ValueError("Namespace.scope must not be empty")

    def key(self, k: str) -> str:
        return f"{self.user_id}/{self.scope}/{k}"


class Store(ABC):
    @abstractmethod
    async def kv_set(self, ns: Namespace, key: str, value: bytes, ttl_s: float | None = None) -> None: ...

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
        """Append bytes to a namespaced blob."""
        ...

    @abstractmethod
    async def meta_upsert(self, table: str, row: dict) -> None: ...

    @abstractmethod
    async def meta_get(self, table: str, user_id: str, pk: str) -> dict | None: ...

    @abstractmethod
    async def meta_list(self, table: str, user_id: str) -> list[dict]: ...
