"""D.5(reviewer M0/M8 #4-6):Dockerfile 加固 + .dockerignore + pin prod deps。

静态契约测试,不真跑 docker build。
"""

from pathlib import Path


def _deploy_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "deploy"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_dockerfile_has_user_directive():
    """non-root USER praxis2 防容器逃逸(reviewer M0/M8 #5)。"""
    text = (_deploy_dir() / "Dockerfile").read_text()
    assert "USER praxis2" in text
    assert "useradd" in text


def test_dockerfile_multi_stage():
    """多阶段 build:deps + runtime,site-packages COPY --from(reviewer M0/M8 #4)。"""
    text = (_deploy_dir() / "Dockerfile").read_text()
    assert "FROM python:3.13-slim AS deps" in text
    assert "COPY --from=deps" in text


def test_dockerfile_uses_pyproject_prod():
    """pip install pyproject `[prod]` extras(不再裸 pip,版本可控)。"""
    text = (_deploy_dir() / "Dockerfile").read_text()
    assert 'pip install --no-cache-dir ".[prod]"' in text


def test_dockerignore_exists_and_excludes_critical():
    """.dockerignore 排除 .venv / node_modules / brains / .git 防 GB 级 bloat。"""
    p = _repo_root() / ".dockerignore"
    assert p.is_file(), ".dockerignore 必须在 root,因为 docker build context = ."
    text = p.read_text()
    for pat in (".venv", ".git", "frontend/node_modules", "brains", "**/._*"):
        assert pat in text, f"missing {pat}"


def test_pyproject_has_prod_extras():
    """pyproject.toml 加 [project.optional-dependencies].prod 并 pin 版本上下界。"""
    text = (_repo_root() / "pyproject.toml").read_text()
    assert "prod = [" in text
    assert "gunicorn" in text
    # 至少一个 ceiling pin(防破坏性 major 升级)
    # 截取 prod 块来检查
    start = text.index("prod = [")
    end = text.index("]", start)
    prod_block = text[start:end]
    assert "<" in prod_block, "prod deps 必须带上界 pin 防破坏性更新"


def test_dockerfile_deps_stage_uses_stub():
    """D.5 fixup:deps 阶段 mkdir/touch stub 让 setuptools build 通过。"""
    text = (_deploy_dir() / "Dockerfile").read_text()
    assert "mkdir -p praxis2 && touch praxis2/__init__.py" in text


def test_dockerfile_pythonpath_set():
    """runtime 阶段 PYTHONPATH=/app 让真 praxis2/ 优先于 site-packages stub。"""
    text = (_deploy_dir() / "Dockerfile").read_text()
    assert "PYTHONPATH=/app" in text
