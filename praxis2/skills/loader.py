"""SKILL.md frontmatter 解析 + 字段校验 + 迁移补默认(总纲 §7.5.1)
+ 渐进披露(§7.5.2)。

两种前言风格(v1 §5.1):域技能 ---\\nyaml\\n---\\nbody;
_common 跨 agent 技能 ---\\nyaml 到 EOF(无结束 ---)。
v1 常缺 when-to-use/paths/context/hooks → 迁移补默认;缺 when-to-use
用 description 兜底(否则渐进披露退化冷启动,§7.5.1)。

YAML 解析:个人开发环境不引入 pyyaml 依赖;frontmatter 只用受限子集
(标量 / [a, b] 内联列表 / true|false / 整数),够覆盖 SKILL.md 字段,
不可解析的值按原始字符串保留(不静默丢)。内联列表元素不支持含逗号
(简单 split,SKILL.md 字段无此形态;真需要时 v2 换 pyyaml)。"""

from dataclasses import dataclass, field


@dataclass
class SkillManifest:
    name: str
    description: str  # 模型可见,发现用(必需)
    when_to_use: str  # 渐进披露关键字段(缺则 description 兜底)
    allowed_tools: list[str] = field(default_factory=list)
    user_invocable: bool = False
    context: str = "inline"  # inline | fork(§7.5.1 context: fork)
    paths: list[str] = field(default_factory=list)  # 条件触发
    hooks: list[str] = field(default_factory=list)  # 会话级 hook
    model: str | None = None  # 技能专属 LLM 覆盖
    effort: int | None = None  # 估时(调度用)
    body: str = ""
    skill_env: str | None = None  # SKILL.md env:(executor 读;loader 不参与选择)


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
    # 至多一个前导负号才认作整数;"--3" 等非数值按原始串保留(不崩,守 docstring 契约)
    if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
        return int(s)
    return s.strip("'\"")


def _split_frontmatter(text: str) -> tuple[str, str]:
    """返回 (yaml_block, body)。两种风格都吃:有结束 --- → body 为其后;
    无结束 --- → yaml 到 EOF、body 为空。无起始 --- → ValueError。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md 缺 frontmatter(首行须为 ---)")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:]).strip()
    return "\n".join(lines[1:]), ""  # yaml 到 EOF,无 body


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
        raise ValueError("SKILL.md 缺 description(模型可见、发现关键,fail-fast)")
    description = str(description)
    # 缺 when-to-use → description 兜底(不留空,§7.5.1)
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


def progressive_disclosure(
    manifests: list[SkillManifest], *, max_chars: int, budget_chars: int
) -> str:
    """§7.5.2:turn-1 仅投入 description + when-to-use(各截 max_chars≈250);
    整份 SKILL.md 仅模型真正调用时展开。skill 列表 ≤ ~1% 上下文预算
    (budget_chars//100):超出按出现顺序丢尾部并记可见提示(不静默丢)。"""
    if not manifests:
        return ""
    cap = budget_chars // 100  # ≈1% 预算
    blocks: list[str] = []
    used = 0
    dropped = 0
    for m in manifests:
        sep = 2 if blocks else 0  # 块间 "\n\n" 也占预算(诚实计量)
        blk = (
            f"## skill: {m.name}\n"
            f"- description: {_trunc(m.description, max_chars)}\n"
            f"- when-to-use: {_trunc(m.when_to_use, max_chars)}"
        )
        if used + sep + len(blk) > cap and blocks:
            # blocks 此处已含全部已录入块(含首块强制收录),故 dropped = 总数 - 已录入
            dropped = len(manifests) - len(blocks)
            break
        blocks.append(blk)
        used += sep + len(blk)
    text = "\n\n".join(blocks)
    if dropped:
        text += f"\n\n[已省略 {dropped} 个 skill:超 ~1% 上下文预算,调用时按需展开]"
    return text
