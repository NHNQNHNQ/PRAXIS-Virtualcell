from __future__ import annotations

import re
import shlex
from typing import Any

from praxis2.core.seams import PermissionDecision, PermissionPolicy, PermissionResult
from praxis2.core.state import State

_BLACK_DESTRUCTIVE = [
    re.compile(r"\brm\s+-[rRfdv]*[rf][rRfdv]*\b", re.IGNORECASE),
    re.compile(r"\bsudo\b", re.IGNORECASE),
    re.compile(r"\bmkfs\b", re.IGNORECASE),
    re.compile(r"\bdd\s+if=", re.IGNORECASE),
    re.compile(r":\(\)\s*\{.*:\|:.*\}", re.IGNORECASE),  # fork bomb :(){:|:&};:
    re.compile(r">\s*/dev/", re.IGNORECASE),
    re.compile(r"\bchmod\s+-[Rr]\s*7?777\b", re.IGNORECASE),
    re.compile(r"\b(shutdown|reboot|halt|poweroff)\b", re.IGNORECASE),
    re.compile(r"\b(curl|wget)\b.*\|\s*(sh|bash|zsh)\b", re.IGNORECASE),
    re.compile(r">\s*/etc/", re.IGNORECASE),
]

_BLACK_CREDENTIAL = [
    "praxis2.env",
    ".env",
    "id_rsa",
    "id_ed25519",
    ".ssh",
    "/etc/passwd",
    "/etc/shadow",
    ".pgpass",
    "PRAXIS_",
    "environ",
]


_WHITELIST = frozenset(
    {
        "pwd",
        "ls",
        "df",
        "du",
        "whoami",
        "uname",
        "hostname",
        "date",
        "which",
        "tree",
        "free",
        "uptime",
        "id",
    }
)

_DANGER_METACHARS = (";", "&&", "||", "|", "`", "$(", ">", "<", "&")


class BashCommandPolicy(PermissionPolicy):
    def check(self, *, tool: Any, payload: dict, state: State) -> PermissionResult:
        if getattr(tool, "name", "") != "Bash":
            return PermissionResult(PermissionDecision.ALLOW)
        command = str(payload.get("command", "")).strip()

        for pat in _BLACK_DESTRUCTIVE:
            if pat.search(command):
                return PermissionResult(
                    PermissionDecision.DENY,
                    reason=f"Command matches a destructive denylist pattern: {pat.pattern!r}; execution denied",
                )
        low = command.lower()
        for token in _BLACK_CREDENTIAL:
            if token.lower() in low:
                return PermissionResult(
                    PermissionDecision.DENY,
                    reason=f"Command contains a sensitive credential pattern: {token!r}; execution denied",
                )

        if command:
            try:
                tokens = shlex.split(command)
            except ValueError:
                tokens = []
            if tokens and tokens[0] in _WHITELIST and not any(m in command for m in _DANGER_METACHARS):
                return PermissionResult(PermissionDecision.ALLOW)

        return PermissionResult(
            PermissionDecision.ASK,
            reason=f"Command{command[:80]!r}is not allowlisted and requires approval",
        )
