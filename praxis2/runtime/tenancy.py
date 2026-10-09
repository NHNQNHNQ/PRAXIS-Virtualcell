from dataclasses import dataclass

from praxis2.core.state import State
from praxis2.store.base import Namespace, Store


def require_user_id(user_id: "str | None") -> str:

    if not user_id:
        raise ValueError("Missing user_id for namespaced storage or permission checks")
    return user_id


@dataclass
class TenantContext:
    user_id: str

    def __post_init__(self) -> None:
        require_user_id(self.user_id)

    def inject(self, state: State) -> None:
        state.tool_use_context["user_id"] = self.user_id


async def assert_tenant_isolation(
    store: Store,
    *,
    owner: str,
    intruder: str,
    scope: str,
    key: str,
    expect_intruder_blind: bool = True,
) -> None:

    owner_val = await store.kv_get(Namespace(user_id=owner, scope=scope), key)
    intruder_val = await store.kv_get(Namespace(user_id=intruder, scope=scope), key)
    if expect_intruder_blind and intruder_val is not None and (intruder_val == owner_val):
        raise AssertionError(
            f"User isolation failed: intruder {intruder!r}read data owned by {owner!r}from "
            f"{scope}/{key}(user isolation violation)"
        )
