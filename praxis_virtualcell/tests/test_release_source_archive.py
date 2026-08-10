"""The P30A source archive is clean-HEAD only, deterministic, and safe to publish locally."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_BUILDER = _ROOT / "scripts" / "build_release_source_archive.sh"
_RELEASE_CANDIDATE = _ROOT / "scripts" / "release_candidate.py"

_SPEC = importlib.util.spec_from_file_location("praxis_release_candidate_source_archive", _RELEASE_CANDIDATE)
assert _SPEC and _SPEC.loader
release_candidate = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = release_candidate
_SPEC.loader.exec_module(release_candidate)


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=True)


def _repository(tmp_path: Path, *, apple_double: bool = False, escaping_symlink: bool = False) -> Path:
    repo = tmp_path / "source"
    (repo / "scripts").mkdir(parents=True)
    (repo / "praxis_virtualcell").mkdir()
    shutil.copyfile(_BUILDER, repo / "scripts" / _BUILDER.name)
    os.chmod(repo / "scripts" / _BUILDER.name, 0o755)
    (repo / "pyproject.toml").write_text(
        "[project]\nname = 'praxis-virtualcell'\nversion = '1.7.0'\n",
        encoding="utf-8",
    )
    (repo / "praxis_virtualcell" / "__init__.py").write_text('__version__ = "1.7.0"\n', encoding="utf-8")
    (repo / "README.md").write_text("fixture\n", encoding="utf-8")
    if apple_double:
        (repo / "._forbidden").write_bytes(b"AppleDouble")
    if escaping_symlink:
        os.symlink("../outside.txt", repo / "praxis_virtualcell" / "escaping_symlink")
    _run("git", "init", "-q", cwd=repo)
    _run("git", "config", "user.name", "P30 Test", cwd=repo)
    _run("git", "config", "user.email", "p30@example.invalid", cwd=repo)
    paths = ["scripts", "praxis_virtualcell", "pyproject.toml", "README.md"]
    if apple_double:
        paths.append("._forbidden")
    if escaping_symlink:
        paths.append("praxis_virtualcell/escaping_symlink")
    _run("git", "add", *paths, cwd=repo)
    _run("git", "commit", "-qm", "fixture", cwd=repo)
    return repo


def _build(repo: Path, output: Path, *, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(repo / "scripts" / _BUILDER.name), str(output)],
        cwd=repo,
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHON_BIN": sys.executable, **(extra_env or {})},
        check=False,
    )


def test_source_archive_is_reproducible_and_matches_release_candidate(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    first = tmp_path / "first" / "praxis-virtualcell-1.7.0.tar.gz"
    second = tmp_path / "second" / "praxis-virtualcell-1.7.0.tar.gz"
    first.parent.mkdir()
    second.parent.mkdir()

    assert _build(repo, first).returncode == 0
    assert _build(repo, second).returncode == 0
    assert first.read_bytes() == second.read_bytes()

    prefix = "praxis-virtualcell-1.7.0/"
    with tarfile.open(first, "r:gz") as archive:
        names = archive.getnames()
        assert prefix + "pyproject.toml" in names
        assert prefix + "praxis_virtualcell/__init__.py" in names
        assert all(name.startswith(prefix) and "/._" not in name and not name.startswith("._") for name in names)
    source_sha = _run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()
    assert release_candidate._inspect_release_artifact(  # noqa: SLF001 - test the existing RC boundary directly.
        first,
        "1.7.0",
        repo=repo,
        source_sha=source_sha,
    ) == {"kind": "source_archive"}


def test_source_archive_rejects_dirty_tree_and_preserves_existing_output(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    output = tmp_path / "out" / "praxis-virtualcell-1.7.0.tar.gz"
    (repo / "untracked.txt").write_text("not in HEAD\n", encoding="utf-8")

    dirty = _build(repo, output)
    assert dirty.returncode != 0
    assert "clean committed worktree" in dirty.stderr
    assert not output.exists()

    (repo / "untracked.txt").unlink()
    output.parent.mkdir()
    output.write_bytes(b"do not replace")
    existing = _build(repo, output)
    assert existing.returncode != 0
    assert "already exists" in existing.stderr
    assert output.read_bytes() == b"do not replace"


def test_source_archive_exact_ref_must_match_current_head(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    stale_sha = _run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()
    (repo / "README.md").write_text("new committed source\n", encoding="utf-8")
    _run("git", "add", "README.md", cwd=repo)
    _run("git", "commit", "-qm", "new source", cwd=repo)
    output = tmp_path / "out" / "praxis-virtualcell-1.7.0.tar.gz"
    output.parent.mkdir()

    result = _build(repo, output, extra_env={"PRAXIS_SOURCE_ARCHIVE_REF": stale_sha})

    assert result.returncode != 0
    assert "reference no longer matches HEAD" in result.stderr
    assert not output.exists()


def test_source_archive_requires_an_absolute_out_of_tree_output(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    filename = "praxis-virtualcell-1.7.0.tar.gz"

    relative = _build(repo, Path(filename))
    assert relative.returncode != 0
    assert "absolute out-of-tree path" in relative.stderr

    in_tree = _build(repo, repo / filename)
    assert in_tree.returncode != 0
    assert "outside the source repository" in in_tree.stderr
    assert not (repo / filename).exists()


def test_source_archive_resolves_a_safe_output_parent_symlink(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    actual_parent = tmp_path / "actual-output"
    actual_parent.mkdir()
    symlink_parent = tmp_path / "symlink-output"
    os.symlink(actual_parent, symlink_parent)
    output = symlink_parent / "praxis-virtualcell-1.7.0.tar.gz"

    result = _build(repo, output)

    assert result.returncode == 0
    assert (actual_parent / output.name).is_file()


def test_source_archive_rejects_tracked_appledouble(tmp_path: Path) -> None:
    repo = _repository(tmp_path, apple_double=True)
    output = tmp_path / "out" / "praxis-virtualcell-1.7.0.tar.gz"
    output.parent.mkdir()

    result = _build(repo, output)

    assert result.returncode != 0
    assert "unsafe source member" in result.stderr
    assert not output.exists()


def test_source_archive_rejects_tracked_escaping_symlink(tmp_path: Path) -> None:
    repo = _repository(tmp_path, escaping_symlink=True)
    output = tmp_path / "out" / "praxis-virtualcell-1.7.0.tar.gz"
    output.parent.mkdir()

    result = _build(repo, output)

    assert result.returncode != 0
    assert "unsupported link" in result.stderr
    assert not output.exists()
