from dataclasses import dataclass, field


@dataclass
class SkillManifest:
    name: str
    description: str
    when_to_use: str
    allowed_tools: list[str] = field(default_factory=list)
    user_invocable: bool = False
    context: str = "inline"  # inline | fork(§7.5.1 context: fork)
    paths: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)
    model: str | None = None
    effort: int | None = None
    body: str = ""
    skill_env: str | None = None


def _scalar(v: str) -> object:
    s = v.strip()
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [x.strip().strip("'\"") for x in inner.split(",")]
    low = s.lower()
    if low in ("true", "false"):
        return low == "true"

    if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
        return int(s)
    return s.strip("'\"")


def _split_frontmatter(text: str) -> tuple[str, str]:

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md has no frontmatter; its first line must be ---")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1 :]).strip()
    return "\n".join(lines[1:]), ""


def parse_skill_md(text: str, *, folder_name: str) -> SkillManifest:
    yaml_block, body = _split_frontmatter(text)
    raw: dict[str, object] = {}
    for line in yaml_block.splitlines():
        line = line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        raw[k.strip()] = _scalar(v)

    name = str(raw.get("name") or folder_name)
    description = raw.get("description")
    if not description or not str(description).strip():
        raise ValueError("SKILL.md requires a discoverable description")
    description = str(description)

    when = raw.get("when-to-use")
    when_to_use = str(when) if when and str(when).strip() else description

    def _as_list(key: str) -> list[str]:
        v = raw.get(key)
        if isinstance(v, list):
            return [str(x) for x in v]
        if v in (None, ""):
            return []
        return [str(v)]

    eff = raw.get("effort")
    return SkillManifest(
        name=name,
        description=description,
        when_to_use=when_to_use,
        allowed_tools=_as_list("allowed-tools"),
        user_invocable=bool(raw.get("user-invocable", False)),
        context=str(raw.get("context") or "inline"),
        paths=_as_list("paths"),
        hooks=_as_list("hooks"),
        model=(str(raw["model"]) if raw.get("model") else None),
        effort=(int(eff) if isinstance(eff, int) else None),
        body=body,
        skill_env=(str(raw["env"]) if raw.get("env") else None),
    )


def _trunc(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n] + "…"


def progressive_disclosure(manifests: list[SkillManifest], *, max_chars: int, budget_chars: int) -> str:

    if not manifests:
        return ""
    cap = budget_chars // 100
    blocks: list[str] = []
    used = 0
    dropped = 0
    for m in manifests:
        sep = 2 if blocks else 0
        blk = (
            f"## skill: {m.name}\n"
            f"- description: {_trunc(m.description, max_chars)}\n"
            f"- when-to-use: {_trunc(m.when_to_use, max_chars)}"
        )
        if used + sep + len(blk) > cap and blocks:
            dropped = len(manifests) - len(blocks)
            break
        blocks.append(blk)
        used += sep + len(blk)
    text = "\n\n".join(blocks)
    if dropped:
        text += f"\n\n[Omitted {dropped}skills beyond the summary budget; expand them on demand]"
    return text
