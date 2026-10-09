from praxis2.store.base import Store


class InMemoryStore(Store):
    def __init__(self) -> None:
        self._kv: dict[str, bytes] = {}
        self._blob: dict[str, bytes] = {}
        # table -> {(user_id, pk): row}
        self._meta: dict[str, dict[tuple[str, str], dict]] = {}

    async def kv_set(self, ns, key, value, ttl_s=None):
        self._kv[ns.key(key)] = value

    async def kv_get(self, ns, key):
        return self._kv.get(ns.key(key))

    async def kv_delete(self, ns, key):
        self._kv.pop(ns.key(key), None)

    async def blob_put(self, ns, key, data):
        ref = ns.key(key)
        self._blob[ref] = data
        return ref

    async def blob_get(self, ns, key):
        return self._blob.get(ns.key(key))

    async def blob_append(self, ns, key, chunk):
        ref = ns.key(key)

        self._blob[ref] = self._blob.get(ref, b"") + chunk

    async def meta_upsert(self, table, row):
        uid = row.get("user_id")
        pk = row.get("pk")
        if not uid or not pk:
            raise ValueError("Metadata rows require nonempty user_id and pk")
        self._meta.setdefault(table, {})[(uid, pk)] = dict(row)

    async def meta_get(self, table, user_id, pk):
        row = self._meta.get(table, {}).get((user_id, pk))
        return dict(row) if row is not None else None

    async def meta_list(self, table, user_id):
        return [r for (u, _), r in self._meta.get(table, {}).items() if u == user_id]
