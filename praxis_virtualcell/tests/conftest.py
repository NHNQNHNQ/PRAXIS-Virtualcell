import os

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """After explicit opt-in, skip tests whose local prerequisites are still absent."""
    from praxis_virtualcell.core.config import load_env

    if config.getoption("--run-remote"):
        try:
            import torch  # noqa: F401
            has_torch = True
        except Exception:
            has_torch = False
        if not has_torch:
            skip_remote = pytest.mark.skip(reason="torch unavailable; skipping remote tests")
            for item in items:
                if "remote" in item.keywords:
                    item.add_marker(skip_remote)

    if not config.getoption("--run-llm"):
        return
    load_env()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        skip_llm = pytest.mark.skip(reason="DEEPSEEK_API_KEY unavailable; skipping live LLM tests")
        for item in items:
            if "llm" in item.keywords:
                item.add_marker(skip_llm)
