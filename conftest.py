"""Repository-wide opt-in gates for tests with external prerequisites."""

from __future__ import annotations

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("praxis external test gates")
    group.addoption(
        "--run-integration",
        action="store_true",
        help="run tests marked integration (PRAXIS_INTEGRATION=1 is also accepted)",
    )
    group.addoption(
        "--run-llm",
        action="store_true",
        help="run tests marked llm; individual tests still validate credentials",
    )
    group.addoption(
        "--run-remote",
        action="store_true",
        help="run tests marked remote; individual tests still validate dependencies",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    enabled = {
        "integration": config.getoption("--run-integration")
        or os.environ.get("PRAXIS_INTEGRATION") == "1",
        "llm": config.getoption("--run-llm"),
        "remote": config.getoption("--run-remote"),
    }

    for item in items:
        disabled = [marker for marker, allowed in enabled.items() if marker in item.keywords and not allowed]
        if disabled:
            options = ", ".join(f"--run-{marker}" for marker in disabled)
            item.add_marker(pytest.mark.skip(reason=f"external test gate requires explicit opt-in: {options}"))
