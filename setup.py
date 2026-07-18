"""Setuptools release hook for optional, pre-built React static assets."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildPyWithReact(build_py):
    def run(self) -> None:
        super().run()
        root = Path(__file__).resolve().parent
        source = root / "praxis_vc_react" / "dist"
        required = os.environ.get("PRAXIS_VC_REQUIRE_STATIC") == "1"
        if not source.is_dir():
            if required:
                raise RuntimeError(
                    "release wheel requires praxis_vc_react/dist; run npm ci && npm run build first"
                )
            return

        target = Path(self.build_lib) / "praxis_vc_api" / "static"
        shutil.copytree(source, target, dirs_exist_ok=True)


setup(cmdclass={"build_py": BuildPyWithReact})
