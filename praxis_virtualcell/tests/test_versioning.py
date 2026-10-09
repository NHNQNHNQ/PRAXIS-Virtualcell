"""Product-version contract across Python, CLI, API, and frontend metadata."""

from __future__ import annotations

import json
import tomllib
from importlib.metadata import version as distribution_version
from pathlib import Path

import pytest
from packaging.version import Version

_ROOT = Path(__file__).resolve().parents[2]


def test_product_version_has_one_authoritative_value() -> None:
    pyproject = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package = json.loads((_ROOT / "praxis_vc_react/package.json").read_text(encoding="utf-8"))
    package_lock = json.loads((_ROOT / "praxis_vc_react/package-lock.json").read_text(encoding="utf-8"))

    import praxis2
    import praxis_virtualcell

    product_version = pyproject["project"]["version"]
    assert product_version != "0.0.0"
    assert str(Version(product_version)) == product_version
    assert distribution_version("praxis-virtualcell") == product_version
    assert praxis_virtualcell.__version__ == product_version
    assert praxis2.__version__ == product_version
    assert package["version"] == product_version
    assert package_lock["version"] == product_version
    assert package_lock["packages"][""]["version"] == product_version


def test_cli_exposes_product_version(capsys: pytest.CaptureFixture[str]) -> None:
    from praxis_virtualcell.cli import main

    with pytest.raises(SystemExit) as exc:
        main(["--version"])

    assert exc.value.code == 0
    expected = distribution_version("praxis-virtualcell")
    assert capsys.readouterr().out.strip() == f"praxis-vc {expected}"


def test_openapi_uses_product_version() -> None:
    pytest.importorskip("fastapi")
    from praxis_vc_api.main import app

    assert app.version == distribution_version("praxis-virtualcell")


def test_missing_distribution_uses_honest_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    from importlib.metadata import PackageNotFoundError

    import praxis_virtualcell.version as product_version

    def missing_distribution(_: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr(product_version, "version", missing_distribution)
    assert product_version._installed_product_version() == "0+unknown"


def test_git_sha_is_injected_with_stable_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    from praxis_virtualcell.version import git_sha

    for name in ("GIT_SHA", "GITHUB_SHA", "SOURCE_VERSION"):
        monkeypatch.delenv(name, raising=False)
    assert git_sha() == "unknown"

    monkeypatch.setenv("SOURCE_VERSION", "source-sha")
    monkeypatch.setenv("GITHUB_SHA", " github-sha ")
    monkeypatch.setenv("GIT_SHA", "git-sha")
    assert git_sha() == "git-sha"

    monkeypatch.setenv("GIT_SHA", "   ")
    assert git_sha() == "github-sha"
