"""生产 ASGI 入口:uvicorn praxis_virtualcell.mdr_gnb.api.asgi:app

env 接线(全可选,未设/空白则纯内存,fail-open 不阻塞):
  MDR_DB_URL     仅非空 URL 启用持久化；SQLite 仅本地验证，PG/.53 未验证
  MDR_REDIS_URL  缓存;未设或连不上 → 不启用缓存
  MDR_STATIC_ROOT 前端构建产物目录;未设 → 仅 API(无同源托管)
"""
from __future__ import annotations

import os

from praxis_virtualcell.mdr_gnb.api.app import create_app
from praxis_virtualcell.mdr_gnb.api.cache import PredictionCache, make_redis_client


def build_app():
    db_url = os.environ.get("MDR_DB_URL")
    if db_url is not None:
        db_url = db_url.strip() or None  # 未设/空白 → 内存
    cache = None
    client = make_redis_client(os.environ.get("MDR_REDIS_URL"))
    if client is not None:
        try:
            client.ping()
            cache = PredictionCache(client)
        except Exception:  # noqa: BLE001 连不上就不启用缓存(fail-open,不阻塞预测)
            cache = None
    static_root = os.environ.get("MDR_STATIC_ROOT")  # None → 仅 API
    return create_app(db_url=db_url, cache=cache, static_root=static_root)


app = build_app()
