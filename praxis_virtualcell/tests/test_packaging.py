"""打包配置守卫:wheel 必须含 praxis_virtualcell/praxis_vc_api + 运行时数据。
防 packages.find 回退到只打 praxis2(否则 praxis-vc CLI ImportError)。"""
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def test_packages_find_includes_virtualcell():
    cfg = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    include = cfg["tool"]["setuptools"]["packages"]["find"]["include"]
    assert any(p.startswith("praxis_virtualcell") for p in include), include
    assert any(p.startswith("praxis_vc_api") for p in include), include


def test_include_package_data_and_manifest():
    cfg = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert cfg["tool"]["setuptools"].get("include-package-data") is True
    manifest = (_ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    assert "recursive-include praxis_virtualcell" in manifest
