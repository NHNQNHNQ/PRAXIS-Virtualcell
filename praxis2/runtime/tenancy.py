"""§11.6/S8 多租户逻辑隔离(第一版刚需,跨用户串扰是安全红线)。

user_id 贯穿全链:鉴权 → 注入 ToolUseContext → 每次 store 访问与权限
校验强制带 user_id(无身份 store 调用是 bug)。store 层 Namespace
已强制 user_id(M0 store/base.py:Namespace.__post_init__);本模块补
ToolUseContext 注入 + 跨租户隔离校验工具(测试网兜底,§5⑧)。"""

from dataclasses import dataclass

from praxis2.core.state import State
from praxis2.store.base import Namespace, Store


def require_user_id(user_id: "str | None") -> str:
    """无身份即编程错误(§11.6:无 user_id 的 store/权限调用是 bug)。"""
    if not user_id:
        raise ValueError(
            "缺 user_id(多租户隔离强制:无身份 store/权限调用是 bug,§11.6)"
        )
    return user_id


@dataclass
class TenantContext:
    """鉴权后注入:把 user_id 贯穿进 State.tool_use_context,
    供后续 store/权限校验取用(§11.6 user_id 贯穿全链)。"""

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
    """跨租户隔离校验(§5⑧ 测试网兜底):intruder 用自己的 Namespace
    读 owner 的数据应读不到(返回 None);若 expect_intruder_blind 且
    intruder 能读出非 None 且值与 owner 相同(即数据被错误共享或污染)
    → 抛 AssertionError。"""
    owner_val = await store.kv_get(Namespace(user_id=owner, scope=scope), key)
    intruder_val = await store.kv_get(
        Namespace(user_id=intruder, scope=scope), key
    )
    if expect_intruder_blind and intruder_val is not None and (
        intruder_val == owner_val
    ):
        raise AssertionError(
            f"跨租户泄漏:intruder {intruder!r} 读到 owner {owner!r} 的 "
            f"{scope}/{key}(§11.6 安全红线)"
        )
