"""BashCommandPolicy:BashTool 的命令级权限裁决(v0.17 子项目 2)。

看 payload["command"] 做黑/白/灰三态裁决:
- 黑名单(破坏性 + 凭证读取)→ DENY(硬拒,不给 ASK 机会)
- 白名单(纯系统信息只读命令 + 无危险元字符)→ ALLOW(直跑)
- 其余灰区 → ASK(经 BridgePermissionAdapter 弹前端确认)

非 Bash 工具透传 ALLOW(替换 AllowAllPermission 后保证其他工具零回归)。
裁决顺序:先黑名单(查整个 command 字符串,catch 复合命令)→ 再白名单 → 灰区。

⚠ 软沙盒前提(spec §5):命令同 server uid 运行,黑名单是缓解非根治。
"""
from __future__ import annotations

import re
import shlex
from typing import Any

from praxis2.core.seams import PermissionDecision, PermissionPolicy, PermissionResult
from praxis2.core.state import State

# 黑名单:破坏性命令(对整个 command 字符串正则匹配)
# 大小写不敏感(re.IGNORECASE),与凭证黑名单 .lower() 对齐,防 SUDO/RM 大小写绕过
_BLACK_DESTRUCTIVE = [
    re.compile(r"\brm\s+-[rRfdv]*[rf][rRfdv]*\b", re.IGNORECASE),   # rm -rf / -fr / -r -f 等
    re.compile(r"\bsudo\b", re.IGNORECASE),
    re.compile(r"\bmkfs\b", re.IGNORECASE),
    re.compile(r"\bdd\s+if=", re.IGNORECASE),
    re.compile(r":\(\)\s*\{.*:\|:.*\}", re.IGNORECASE),               # fork bomb :(){:|:&};:
    re.compile(r">\s*/dev/", re.IGNORECASE),
    re.compile(r"\bchmod\s+-[Rr]\s*7?777\b", re.IGNORECASE),
    re.compile(r"\b(shutdown|reboot|halt|poweroff)\b", re.IGNORECASE),
    re.compile(r"\b(curl|wget)\b.*\|\s*(sh|bash|zsh)\b", re.IGNORECASE),  # 下载执行
    re.compile(r">\s*/etc/", re.IGNORECASE),
]
# 黑名单:凭证 / 敏感路径(子串 token,大小写不敏感)
_BLACK_CREDENTIAL = [
    "praxis2.env", ".env", "id_rsa", "id_ed25519", ".ssh",
    "/etc/passwd", "/etc/shadow", ".pgpass", "PRAXIS_", "environ",
]
# 白名单:纯系统信息只读命令(任何参数都无害)。文件读取类(cat/grep/find)
# 故意不在此(参数可能是敏感路径)→ 灰区 ASK + 黑名单兜底。
_WHITELIST = frozenset({
    "pwd", "ls", "df", "du", "whoami", "uname", "hostname",
    "date", "which", "tree", "free", "uptime", "id",
})
# 危险 shell 元字符(白名单命令含这些 → 不直接 ALLOW,降级 ASK)
_DANGER_METACHARS = (";", "&&", "||", "|", "`", "$(", ">", "<", "&")


class BashCommandPolicy(PermissionPolicy):
    """命令级黑/白/灰裁决。非 Bash 工具透传 ALLOW。"""

    def check(self, *, tool: Any, payload: dict, state: State) -> PermissionResult:
        if getattr(tool, "name", "") != "Bash":
            return PermissionResult(PermissionDecision.ALLOW)  # 非 Bash 透传(零回归)
        command = str(payload.get("command", "")).strip()

        # 1) 黑名单(查整个 command 字符串,catch 复合命令里的危险段)
        for pat in _BLACK_DESTRUCTIVE:
            if pat.search(command):
                return PermissionResult(
                    PermissionDecision.DENY,
                    reason=f"命令命中破坏性黑名单(模式 {pat.pattern!r}),拒绝执行",
                )
        low = command.lower()
        for token in _BLACK_CREDENTIAL:
            if token.lower() in low:
                return PermissionResult(
                    PermissionDecision.DENY,
                    reason=f"命令含敏感/凭证 token {token!r},拒绝执行(防泄漏)",
                )

        # 2) 白名单:首 token 在只读集 且 无危险元字符
        if command:
            try:
                tokens = shlex.split(command)
            except ValueError:
                tokens = []  # 畸形引号 → 灰区 ASK 保守
            if tokens and tokens[0] in _WHITELIST and not any(
                m in command for m in _DANGER_METACHARS
            ):
                return PermissionResult(PermissionDecision.ALLOW)

        # 3) 灰区 → ASK(经 BridgePermissionAdapter 弹前端)
        return PermissionResult(
            PermissionDecision.ASK,
            reason=f"命令 {command[:80]!r} 非白名单,需用户确认",
        )
