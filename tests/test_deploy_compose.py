"""§6⑤/§11.4 deploy/docker-compose.yml + Dockerfile 静态契约测试。
本机不起容器(无 docker);只断言文件可读 + 关键字段。"""

from pathlib import Path

import pytest


def _deploy_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "deploy"


def test_docker_compose_yml_exists():
    f = _deploy_dir() / "docker-compose.yml"
    assert f.is_file(), f"deploy/docker-compose.yml 不存在 ({f})"


def test_docker_compose_has_three_services():
    f = _deploy_dir() / "docker-compose.yml"
    text = f.read_text()
    # 关键服务:postgres / redis / backend
    assert "postgres:" in text
    assert "redis:" in text
    assert "backend:" in text


def test_docker_compose_postgres_persist_volume():
    # PG 必须有 volume(否则 docker compose down 数据丢)
    f = _deploy_dir() / "docker-compose.yml"
    text = f.read_text()
    assert "volumes:" in text
    assert "pgdata" in text or "postgres-data" in text


def test_dockerfile_exists_and_has_pip_install():
    f = _deploy_dir() / "Dockerfile"
    assert f.is_file()
    text = f.read_text()
    assert "pip install" in text or "uv pip install" in text
    # CMD 启动 gunicorn(多 worker uvicorn)
    assert "gunicorn" in text


@pytest.mark.integration
def test_docker_compose_up_smoke():
    # 真起 docker(本机 docker 不存在自动 skip;M8 校准②留用户 Task 11 跑)
    import shutil
    if shutil.which("docker") is None:
        pytest.skip("docker 未安装,跳过真起容器测试(M8 Task 11 用户跑)")
    # 真跑 docker compose up -d 验证 PG/Redis 端口可达 留 Task 11


def test_compose_postgres_password_requires_env():
    """B.5 (reviewer M0/M8 C2):POSTGRES_PASSWORD 必须强制环境变量,不能硬编码字符串。"""
    text = (_deploy_dir() / "docker-compose.yml").read_text(encoding="utf-8")
    # 必须用 ${POSTGRES_PASSWORD:?...} 语法
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?" in text, \
        "PG 密码必须强制 env 必填,见 reviewer M0/M8 C2"
    # 硬编码 dev-only 字符串不应在
    assert "praxis2_dev_only" not in text, "dev only 密码已硬编码,有上线带上线风险"
