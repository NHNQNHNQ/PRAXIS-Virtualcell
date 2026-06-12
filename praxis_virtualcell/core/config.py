"""运行配置 + 可复现时钟/ID 生成器(避免 datetime.now / random 破坏 trace 复现)。"""
from __future__ import annotations

import itertools
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_BRAINS_DEFAULT = Path(__file__).resolve().parent.parent / "brains" / "virtualcell"


class Mode(str, Enum):
    OFFLINE = "offline"
    LLM_ASSISTED = "llm_assisted"


class Clock:
    """单调递增的确定性时钟,now() 返回 't0001'、't0002'…(测试可复现)。"""

    def __init__(self, start: int = 0) -> None:
        self._t = start

    def now(self) -> str:
        self._t += 1
        return f"t{self._t:04d}"


class IdGen:
    """确定性 id 生成器。"""

    def __init__(self, prefix: str = "msg") -> None:
        self._prefix = prefix
        self._c = itertools.count(1)

    def next(self) -> str:
        return f"{self._prefix}_{next(self._c):04d}"


@dataclass
class RuntimeConfig:
    mode: Mode = Mode.OFFLINE
    brains_root: str = str(_BRAINS_DEFAULT)
    llm_enabled: bool = False  # 仅当 mode=llm_assisted 且有可用 key 时才 True
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    @classmethod
    def from_env(cls, *, env_path: str = ".env") -> "RuntimeConfig":
        load_env(env_path)
        mode = (Mode.LLM_ASSISTED
                if os.environ.get("PRAXIS_VIRTUALCELL_MODE") == "llm_assisted"
                else Mode.OFFLINE)
        key = os.environ.get("DEEPSEEK_API_KEY", "")
        return cls(
            mode=mode,
            deepseek_api_key=key,
            deepseek_base_url=os.environ.get("PRAXIS_VC_LLM_BASE_URL", "https://api.deepseek.com"),
            deepseek_model=os.environ.get("PRAXIS_VC_LLM_MODEL", "deepseek-chat"),
            llm_enabled=(mode is Mode.LLM_ASSISTED and bool(key)),
        )


def load_env(path: str = ".env") -> None:
    """读 .env 的 K=V 注入 os.environ(已存在的不覆盖;无文件 noop)。无新依赖。"""
    p = Path(path)
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
