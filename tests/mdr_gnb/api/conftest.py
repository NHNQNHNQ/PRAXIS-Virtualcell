"""tests/api 共享:FastAPI TestClient(不需真起服务)。"""
import pytest
from fastapi.testclient import TestClient

from praxis_virtualcell.mdr_gnb.api.app import create_app


@pytest.fixture()
def client():
    # 每个测试新建 app(内存 store 隔离),确定性由 run_mdr_query 保证
    return TestClient(create_app())
