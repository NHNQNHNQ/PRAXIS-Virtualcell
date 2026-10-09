"""完整 proposal 流程: user post → my list → admin list → admin decide → audit."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tests._auth_test_helpers import make_admin_user_in_db, make_normal_user_in_db

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def test_proposal_full_lifecycle(app_with_real_backends):
    app, pg_pool, _redis = app_with_real_backends
    user_id, user_email, user_password = await make_normal_user_in_db(pg_pool)
    admin_id, admin_email, admin_password = await make_admin_user_in_db(pg_pool)
    transport = ASGITransport(app=app)

    # 1. user login + create proposal
    async with AsyncClient(transport=transport, base_url="http://test") as user_client:
        r = await user_client.post(
            "/api/auth/login",
            json={"email": user_email, "password": user_password},
        )
        assert r.status_code == 200
        user_client.cookies.set("praxis_session", r.cookies["praxis_session"])

        r = await user_client.post(
            "/api/proposals",
            json={"kind": "bug", "title": "Found a typo", "body": "details..."},
        )
        assert r.status_code == 200
        pid = r.json()["id"]
        assert r.json()["status"] == "open"

        # 2. user list mine
        r = await user_client.get("/api/me/proposals")
        assert r.status_code == 200
        # 2026-05-31:envelope key 改为 'proposals' 与 admin + FE 对齐(handlers.py 修)
        assert any(p["id"] == pid for p in r.json()["proposals"])

        # 3. invalid kind
        r = await user_client.post(
            "/api/proposals",
            json={"kind": "bogus", "title": "x"},
        )
        assert r.status_code == 422
        assert r.json()["error"] == "invalid_kind"

    # 4. admin login + list + decide
    async with AsyncClient(transport=transport, base_url="http://test") as admin_client:
        r = await admin_client.post(
            "/api/auth/login",
            json={"email": admin_email, "password": admin_password},
        )
        admin_client.cookies.set("praxis_session", r.cookies["praxis_session"])

        # admin list
        r = await admin_client.get("/api/admin/proposals?status=open")
        assert r.status_code == 200
        assert any(p["id"] == pid for p in r.json()["proposals"])

        # admin decide
        r = await admin_client.post(
            f"/api/admin/proposals/{pid}/decide",
            json={"verdict": "ship", "score": 4,
                  "shipped_to": "abc123", "note": "good"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "decided"
        assert r.json()["verdict"] == "ship"

        # 5. 再 decide → 409 already_decided
        r = await admin_client.post(
            f"/api/admin/proposals/{pid}/decide",
            json={"verdict": "reject"},
        )
        assert r.status_code == 409
        assert r.json()["error"] == "already_decided"

        # 6. audit log 应含 proposal_decide
        r = await admin_client.get("/api/admin/audit-log?action=proposal_decide")
        assert any(row["resource_id"] == pid for row in r.json()["rows"])
