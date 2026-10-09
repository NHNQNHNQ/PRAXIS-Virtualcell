"""完整 admin 流程: login → list → adjust → audit → freeze 拒 → 无 cookie 401 → stats。"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tests._auth_test_helpers import make_admin_user_in_db

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def test_admin_v2_full_lifecycle(app_with_real_backends):
    """admin login → list → adjust → audit log 有记录 → 拒 freeze admin → stats。"""
    app, pg_pool, _ = app_with_real_backends
    admin_id, admin_email, admin_password = await make_admin_user_in_db(
        pg_pool, balance_li=10_000,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. login
        r = await client.post(
            "/api/auth/login",
            json={"email": admin_email, "password": admin_password},
        )
        assert r.status_code == 200, r.text
        cookie = r.cookies.get("praxis_session")
        assert cookie
        client.cookies.set("praxis_session", cookie)

        # 2. list users
        r = await client.get("/api/admin/users?page=1&limit=10")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "users" in body
        assert body["total"] >= 1

        # 3. adjust balance (admin 给自己充值 50 元 = 5000 li, 1元=100li)
        r = await client.post(
            f"/api/admin/users/{admin_id}/adjust",
            json={"amount_yuan": 50.0, "note": "test topup"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["new_balance_li"] == 15_000

        # 4. audit log 应有 balance_adjust 记录
        r = await client.get(
            f"/api/admin/audit-log?user_id={admin_id}&action=balance_adjust",
        )
        assert r.status_code == 200, r.text
        rows = r.json()["rows"]
        assert any(row["action"] == "balance_adjust" for row in rows)

        # 5. freeze admin (target = 自己 = admin) 应被拒
        r = await client.post(
            f"/api/admin/users/{admin_id}/freeze",
            json={"reason": "test"},
        )
        assert r.status_code == 403, r.text
        assert r.json()["error"] == "cannot_freeze_admin"

        # 6. 非 admin 访问 admin endpoint → 401
        no_cookie_client = AsyncClient(transport=transport, base_url="http://test")
        try:
            r = await no_cookie_client.get("/api/admin/users")
            assert r.status_code == 401
        finally:
            await no_cookie_client.aclose()

        # 7. stats
        r = await client.get("/api/admin/stats")
        assert r.status_code == 200, r.text
        s = r.json()
        assert s["users"]["total"] >= 1
