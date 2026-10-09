"""M10.5 hotfix: 12 个 stub endpoint smoke 测试。"""
from __future__ import annotations

import pytest

from tests.test_auth_routes import _make_deps
from tests.test_auth_routes_v2_me import (
    _capture,
    _mk_receive,
    _mk_scope,
    _mk_userrow,
)


@pytest.fixture
async def stubs_deps():
    return await _make_deps()


@pytest.mark.asyncio
async def test_admin_user_adjust_requires_admin(stubs_deps):
    from praxis2.server.routes.stubs import handle_admin_user_adjust_stub

    stubs_deps["repo"]._users["uid-ua"] = _mk_userrow(
        id="uid-ua", email="ua@x", role="user"
    )
    scope = _mk_scope(
        "POST", "/api/admin/users/x/adjust", user={"user_id": "uid-ua", "role": "user"}
    )
    status, body, _ = await _capture(
        handle_admin_user_adjust_stub, scope, _mk_receive(b"{}"), {}
    )
    assert status == 403
    assert body["error"] == "forbidden"


@pytest.mark.asyncio
async def test_admin_user_freeze_admin_role_returns_503(stubs_deps):
    from praxis2.server.routes.stubs import handle_admin_user_freeze_stub

    stubs_deps["repo"]._users["uid-ad"] = _mk_userrow(
        id="uid-ad", email="ad@x", role="admin"
    )
    scope = _mk_scope(
        "POST", "/api/admin/users/x/freeze", user={"user_id": "uid-ad", "role": "admin"}
    )
    status, body, _ = await _capture(
        handle_admin_user_freeze_stub, scope, _mk_receive(b"{}"), {}
    )
    assert status == 503
    assert body["error"] == "admin_not_implemented"
