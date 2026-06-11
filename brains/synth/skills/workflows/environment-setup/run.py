"""environment-setup — auto-detect Python deps + external binaries.

Implements PRAXIS principle 4 (self-configuring environment). Reports what's
present, what's missing, and how to install. Falls back to Docker recipes.
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PYTHON_DEPS = [
    "cobra",
    "dnachisel",
    "Bio",  # biopython
    "rdkit",
    "rank_bm25",
    "anthropic",
    "yaml",
    "jsonschema",
    "watchdog",
    "rapidfuzz",
    "pandas",
    "sympy",
    "numpy",
]

EXTERNAL_BINARIES = {
    "antismash": "ANTSMASH_BIN",
    "iBioSim": "IBIOSIM_BIN",
    "retropath2": "RETROPATH_BIN",
    "bigscape.py": "BIGSCAPE_BIN",
    "deepbgc": "DEEPBGC_BIN",
}

PACKAGE_MANAGER_CANDIDATES = ["mamba", "conda", "pixi", "pip"]


def _check_python_deps() -> dict:
    found, missing = [], []
    for mod in PYTHON_DEPS:
        try:
            m = importlib.import_module(mod)
            ver = getattr(m, "__version__", "unknown")
            found.append({"module": mod, "version": ver})
        except ImportError:
            missing.append(mod)
    return {"found": found, "missing": missing}


def _check_binary(name: str, env_var: str) -> dict:
    explicit = os.environ.get(env_var, "").strip()
    if explicit:
        path = explicit if Path(explicit).exists() else shutil.which(explicit)
    else:
        path = shutil.which(name)
    if not path:
        return {"name": name, "env_var": env_var, "found": False, "path": None, "version": None}

    version = None
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
        version = (out.stdout + out.stderr).strip().splitlines()[0] if (out.stdout + out.stderr) else None
    except Exception:
        pass
    return {"name": name, "env_var": env_var, "found": True, "path": path, "version": version}


def _check_pkg_managers() -> list[str]:
    return [pm for pm in PACKAGE_MANAGER_CANDIDATES if shutil.which(pm)]


def run() -> dict:
    py = _check_python_deps()
    bins = [_check_binary(n, ev) for n, ev in EXTERNAL_BINARIES.items()]
    pkg = _check_pkg_managers()

    install_hints = []
    if py["missing"]:
        install_hints.append(
            "pip install " + " ".join(py["missing"]).replace("Bio", "biopython").replace("yaml", "pyyaml").replace("rank_bm25", "rank-bm25")
        )
    for b in bins:
        if not b["found"]:
            if b["name"] == "antismash":
                install_hints.append("antiSMASH: conda install -c bioconda antismash  (or docker pull antismash/standalone)")
            elif b["name"] == "iBioSim":
                install_hints.append("iBioSim: download from https://github.com/MyersResearchGroup/iBioSim/releases")
            elif b["name"] == "retropath2":
                install_hints.append("RetroPath2.0: docker pull brsynth/retropath2-wrapper")
            elif b["name"] == "bigscape.py":
                install_hints.append("BiG-SCAPE: pip install bigscape  (or docker pull nselem/bigscape)")
            elif b["name"] == "deepbgc":
                install_hints.append("DeepBGC: pip install deepbgc")

    summary = {
        "python_deps": py,
        "external_binaries": bins,
        "package_managers_available": pkg,
        "install_hints": install_hints,
        "all_python_present": not py["missing"],
        "all_binaries_present": all(b["found"] for b in bins),
        "tool_provenance": {
            "simulated": False,
            "partial": False,
            "full": True,
            "version": "praxis-synth/environment-setup/0.1.0",
        },
    }
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
