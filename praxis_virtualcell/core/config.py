"""Runtime configuration with deterministic clocks and IDs for reproducible traces."""
from __future__ import annotations

import itertools
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_BRAINS_DEFAULT = Path(__file__).resolve().parent.parent / "brains" / "virtualcell"


class Mode(str, Enum):  # noqa: UP042
    OFFLINE = "offline"
    LLM_ASSISTED = "llm_assisted"


    LLM_ORCHESTRATED = "llm_orchestrated"
    LLM_ORCHESTRATED_STRICT = "llm_orchestrated_strict"



LLM_MODES = (Mode.LLM_ASSISTED, Mode.LLM_ORCHESTRATED, Mode.LLM_ORCHESTRATED_STRICT)


class Clock:
    """Monotonic deterministic clock returning t0001, t0002, and subsequent ticks."""

    def __init__(self, start: int = 0) -> None:
        self._t = start

    def now(self) -> str:
        self._t += 1
        return f"t{self._t:04d}"


class IdGen:
    """Deterministic identifier generator."""

    def __init__(self, prefix: str = "msg") -> None:
        self._prefix = prefix
        self._c = itertools.count(1)

    def next(self) -> str:
        return f"{self._prefix}_{next(self._c):04d}"


@dataclass
class RuntimeConfig:
    mode: Mode = Mode.OFFLINE
    brains_root: str = str(_BRAINS_DEFAULT)


    reliability_mode: str = "learned_with_rule_fallback"
    llm_enabled: bool = False
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"



    allow_llm_to_modify_core_decision: bool = False
    allow_llm_to_modify_prediction: bool = False
    allow_llm_to_override_hard_rules: bool = False

    @classmethod
    def from_env(cls, *, env_path: str = ".env") -> RuntimeConfig:
        load_env(env_path)
        _mode_str = os.environ.get("PRAXIS_VIRTUALCELL_MODE", "offline")
        _by_str = {m.value: m for m in Mode}
        mode = _by_str.get(_mode_str, Mode.OFFLINE)
        key = os.environ.get("DEEPSEEK_API_KEY", "")
        return cls(
            mode=mode,
            deepseek_api_key=key,
            deepseek_base_url=os.environ.get("PRAXIS_VC_LLM_BASE_URL", "https://api.deepseek.com"),
            deepseek_model=os.environ.get("PRAXIS_VC_LLM_MODEL", "deepseek-chat"),
            llm_enabled=(mode in LLM_MODES and bool(key)),
        )


def assert_llm_boundaries(config: RuntimeConfig) -> None:
    """Require all 3 LLM authority flags to be False. Fail closed at LLM-enabled workflow/API entry points to
    prevent core decision authority from being enabled by configuration.
    """
    bad = [f for f in ("allow_llm_to_modify_core_decision",
                       "allow_llm_to_modify_prediction",
                       "allow_llm_to_override_hard_rules") if getattr(config, f)]
    if bad:
        raise RuntimeError(
            f"LLM authority boundary violated (must always be False): {bad}. LLMs must never alter "
            "prediction / hard-rule / learned reliability final decisions.")


def load_env(path: str = ".env") -> None:
    """Load .env K=V entries into os.environ without replacing existing values; missing files are a no-op and
    require no dependency.
    """
    p = Path(path)
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
