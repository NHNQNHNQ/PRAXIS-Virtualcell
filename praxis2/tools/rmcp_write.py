"""RMCPWriteCaseTool:SEAL 相位用,把推理出的 case 落到 _proposed inbox。

回归:rmcp.py:35-47 的 ALLOWED_OPS[SEAL] 声明了 write_case op,但没有 Tool 子类
实体——模型在 SEAL 相位"想把结论 seal 成 case"时,system prompt 提及 write_case
但工具池里没有,只能纯文字描述"应该把这个 case 存起来"(幻觉)。本工具补这一缝。

第一版设计(v0.16.0-alpha):
- 写到 `brains/<slug>/memory/cases/_proposed/<safe-stem>.md`,等审核 inbox
- 不直接动 store DB(避免引入 user_id 注入复杂性);后续 review 流可 approve
- evidence 必含 DOI(§安全规则:不杜撰引用)
- 同 brain + 同 title → 同 stem → 后写覆盖前写(便于模型迭代)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from praxis2.brains.migrate import DISCIPLINE_SLUGS
from praxis2.tools.base import Tool, ToolResult

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BRAINS_ROOT_DEFAULT = _REPO_ROOT / "brains"

# 文件名安全字符:字母 / 数字 / 短横 / 下划线;其余统一替成 -
_STEM_UNSAFE = re.compile(r"[^A-Za-z0-9_\-]+")


def _safe_stem(title: str, *, max_len: int = 80) -> str:
    """把任意 title 安全化成文件 stem(去掉路径分隔符 / 中文 / 特殊字符)。

    策略:ASCII 化(中文字符直接被替成 -)+ 限长 + 去重连字符。
    不保留 .md 后缀(由调用方拼)。
    """
    s = _STEM_UNSAFE.sub("-", title.strip()).strip("-")
    s = re.sub(r"-+", "-", s)  # 多连字符合并
    if not s:
        s = "untitled"
    return s[:max_len].rstrip("-") or "untitled"


def _format_doi_field(doi: str) -> str:
    """frontmatter 里 doi 字段:含 / 时加引号(YAML 习惯)。"""
    if "/" in doi or ":" in doi:
        return f'"{doi}"'
    return doi


def _render_markdown(
    *, brain: str, title: str, summary: str, evidence: list[dict]
) -> str:
    primary_doi = evidence[0].get("doi", "") if evidence else ""
    lines = [
        "---",
        f"case_id: {_safe_stem(title)}",
        f"brain: {brain}",
        "status: proposed",
        f"title: {title!r}",
        f"doi: {_format_doi_field(primary_doi)}" if primary_doi else "doi: null",
        f"evidence_count: {len(evidence)}",
        "schema_version: 1",
        "---",
        "",
        f"# {title}",
        "",
        "## Summary",
        "",
        summary.strip(),
        "",
        "## Evidence",
        "",
    ]
    if not evidence:
        lines.append("(无)")
    else:
        for i, ev in enumerate(evidence, 1):
            doi = ev.get("doi", "(无 DOI)")
            citation = ev.get("citation", "")
            note = ev.get("note", "")
            lines.append(f"{i}. DOI: `{doi}`")
            if citation:
                lines.append(f"   - 引用:{citation}")
            if note:
                lines.append(f"   - 备注:{note}")
    lines.append("")
    return "\n".join(lines)


class RMCPWriteCaseTool(Tool):
    """SEAL 相位的 write_case op:把推理出的新 case 落到 _proposed inbox。

    input: {brain, title, summary, evidence: [{doi, citation?, note?}]}
    output: {brain, title, stem, written_path, evidence_count}
    """

    name = "RMCPWriteCase"
    description = (
        "把本轮推理得到的新案例(case)落到本学科 brain 的 _proposed inbox,"
        "等用户/管理员审核后并入正式 cases。input: brain(学科 slug) + title + "
        "summary + evidence(必含至少 1 个 doi,§安全规则:不杜撰引用)。"
        "同 title 后写覆盖前写。"
    )
    # §7.3.7:write_case 属 SEAL 相位白名单(rmcp.py:43-45)
    rmcp_op = "write_case"

    def __init__(self, brains_root: Path | None = None) -> None:
        self._root = Path(brains_root) if brains_root else _BRAINS_ROOT_DEFAULT

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "brain": {
                    "type": "string",
                    "description": (
                        "学科 slug(小写),如 enzyme/dock/cell/.../synth(13 个)"
                    ),
                },
                "title": {
                    "type": "string",
                    "description": "case 标题(模型用,人类可读;同 title 后写覆盖)",
                },
                "summary": {
                    "type": "string",
                    "description": "case 主体摘要 markdown(2-5 段,含结论 + 关键证据指向)",
                },
                "evidence": {
                    "type": "array",
                    "description": (
                        "证据列表,每条 {doi, citation?, note?};必含至少 1 个 doi"
                        "(§安全规则:不杜撰引用)"
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "doi": {"type": "string"},
                            "citation": {"type": "string"},
                            "note": {"type": "string"},
                        },
                        "required": ["doi"],
                    },
                },
            },
            "required": ["brain", "title", "summary", "evidence"],
        }

    async def run(self, payload: dict[str, Any]) -> ToolResult:
        brain = (payload.get("brain") or "").strip().lower()
        title = (payload.get("title") or "").strip()
        summary = (payload.get("summary") or "").strip()
        evidence = payload.get("evidence") or []

        if not brain:
            return ToolResult(ok=False, error="缺 brain(必填,例: enzyme)")
        if not title:
            return ToolResult(ok=False, error="缺 title(必填)")
        if not summary:
            return ToolResult(ok=False, error="缺 summary(必填)")
        if not isinstance(evidence, list) or not evidence:
            return ToolResult(
                ok=False,
                error=(
                    "evidence 必须是非空 list,且至少 1 条含 DOI"
                    "(§安全规则:不杜撰引用,禁止 0 evidence 写 case)"
                ),
                recovery_hint=(
                    'evidence=[{"doi": "10.XXX/YYY", '
                    '"citation": "Author Year Journal"}]'
                ),
            )
        # 至少 1 条 DOI 非空
        dois = [str(ev.get("doi") or "").strip() for ev in evidence if isinstance(ev, dict)]
        if not any(dois):
            return ToolResult(
                ok=False,
                error=(
                    "evidence 中至少 1 条必须有非空 doi 字段"
                    "(§安全规则:不杜撰引用)"
                ),
            )

        # brain 验证:接受 13 学科 slug + _common
        if brain not in DISCIPLINE_SLUGS and brain != "_common":
            return ToolResult(
                ok=False,
                error=(
                    f"未知 brain '{brain}'。可选:{', '.join(DISCIPLINE_SLUGS)}"
                ),
            )

        # 即使 brain 合法,本地 brains/<slug>/ 目录可能不存在(测试 tmp_path
        # 场景):自动建目录(mkdir parents=True)。
        # v0.16.3:mkdir / write_text 在 read-only 挂载或无权限目录会抛
        # PermissionError/OSError → 此前直接冒泡致 chat-stream 500。包成
        # ok=False 结构化回执,模型可据此换路径 / 提示 user。
        inbox = self._root / brain / "memory" / "cases" / "_proposed"
        stem = _safe_stem(title)
        path = inbox / f"{stem}.md"
        content = _render_markdown(
            brain=brain, title=title, summary=summary, evidence=evidence,
        )
        try:
            inbox.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except OSError as e:
            return ToolResult(
                ok=False,
                error=(
                    f"写 case 失败({type(e).__name__}: {e})。"
                    f"目标 {inbox} 可能无写权限 / read-only 挂载 / 磁盘满。"
                ),
                recovery_hint="检查 brains_root 写权限,或联系管理员。",
            )

        # 返回相对 repo 的路径(便于模型/用户后续 review)
        try:
            rel = path.relative_to(_REPO_ROOT)
            rel_str = str(rel)
        except ValueError:
            rel_str = str(path)  # tmp_path 等非 repo 内路径

        return ToolResult(
            ok=True,
            value={
                "brain": brain,
                "title": title,
                "stem": stem,
                "written_path": str(path),
                "written_path_rel": rel_str,
                "evidence_count": len(evidence),
                "status": "proposed (等审核 inbox)",
                "next_action": (
                    f"case 已落到 {rel_str},等用户/管理员审核后合并入正式 cases。"
                    "审核 OK 即可由管理员 mv 到 ../<stem>.md 上线。"
                ),
            },
        )
