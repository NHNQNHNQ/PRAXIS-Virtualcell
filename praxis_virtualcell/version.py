"""Product and protocol identities for PRAXIS-VirtualCell."""

from __future__ import annotations

import os
from importlib.metadata import PackageNotFoundError, version

DISTRIBUTION_NAME = "praxis-virtualcell"
API_PROTOCOL_VERSION = "vc.api.v1"
RUNTIME_PROTOCOL_VERSION = "vc.runtime.v1"
LEGACY_RUNTIME_VERSION = "v0.3"


def _installed_product_version() -> str:
    try:
        return version(DISTRIBUTION_NAME)
    except PackageNotFoundError:
        return "0+unknown"


PRODUCT_VERSION = _installed_product_version()


def git_sha() -> str:
    """Return an injected build identity without guessing from a local checkout."""
    for name in ("GIT_SHA", "GITHUB_SHA", "SOURCE_VERSION"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return "unknown"
