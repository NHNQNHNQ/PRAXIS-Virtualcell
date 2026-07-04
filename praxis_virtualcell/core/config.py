"""运行配置 + 可复现时钟/ID 生成器(避免 datetime.now / random 破坏 trace 复现)。"""
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
    # Phase 4(v1.1):LLM 编排模式。LLM 只出 module 集建议(经 safety_contract 过滤成合法候选),
    # 不碰 prediction/hard-rule/verdict 终决(assert_llm_boundaries 三 flag 仍恒 False)。
    LLM_ORCHESTRATED = "llm_orchestrated"
    LLM_ORCHESTRATED_STRICT = "llm_orchestrated_strict"


# 需要 LLM 的运行模式集合(assist / 编排 / 编排-strict)。OFFLINE 不在内 → 恒零 LLM。
LLM_MODES = (Mode.LLM_ASSISTED, Mode.LLM_ORCHESTRATED, Mode.LLM_ORCHESTRATED_STRICT)


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
    # M2.1 Step6:可靠性判定模式 rule / learned / learned_with_rule_fallback。
    # 默认 learned_with_rule_fallback(artifact 缺失/schema 不匹配自动退回 rule,fail-closed)。
    reliability_mode: str = "learned_with_rule_fallback"
    llm_enabled: bool = False  # 仅当 mode=llm_assisted 且有可用 key 时才 True
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    # v0.6 决策边界铁律:以下三者**永远 False**,任何路径不得置 True(assert_llm_boundaries 守卫)。
    # LLM 只做输入解析/路由建议/critic 复核/报告润色,绝不碰 prediction / hard-rule /
    # learned reliability / abstain-downgrade-accept 终决 / artifact 校验 / provenance。
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
    """守卫:LLM 决策边界三 flag 必须全 False,否则拒绝运行(fail-closed)。
    在任何启用 LLM 的入口(workflow/api)调用一次,防止误配置让 LLM 侵入核心决策。"""
    bad = [f for f in ("allow_llm_to_modify_core_decision",
                       "allow_llm_to_modify_prediction",
                       "allow_llm_to_override_hard_rules") if getattr(config, f)]
    if bad:
        raise RuntimeError(
            f"LLM 决策边界被违反(必须永为 False): {bad}。LLM 绝不允许碰 "
            "prediction / hard-rule / learned reliability 终决。")


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
