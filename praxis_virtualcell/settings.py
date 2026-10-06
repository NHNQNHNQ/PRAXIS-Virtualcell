"""One local credential profile for the LLM prediction entry point."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def read_env_file(path: str | Path) -> dict[str, str]:
    result = {}
    path = Path(path)
    if not path.is_file():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        result[key.strip()] = value
    return result


@dataclass(frozen=True)
class LLMSettings:
    api_key: str = field(repr=False)
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-pro"

    @classmethod
    def load(cls, env_path: str | Path | None = None, *, environ: dict | None = None):
        path = Path(env_path) if env_path else Path.cwd() / ".env"
        values = read_env_file(path)
        values.update(os.environ if environ is None else environ)
        return cls(
            api_key=values.get("DEEPSEEK_API_KEY") or values.get("PRAXIS_ANTHROPIC_API_KEY", ""),
            base_url=values.get("PRAXIS_ANTHROPIC_BASE_URL") or values.get("PRAXIS_VC_LLM_BASE_URL", "https://api.deepseek.com"),
            model=values.get("PRAXIS_MODEL") or values.get("PRAXIS_VC_LLM_MODEL", "deepseek-v4-pro"),
        )

    def require_key(self):
        if not self.api_key.strip():
            raise ValueError("Missing DEEPSEEK_API_KEY in local .env or process environment")
