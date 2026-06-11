"""MEMORY.md 三层合并(总纲 §7.4.1)。三层优先级 _common < domain < session。
只存索引行不存正文;硬截断保护(行数/字节)。纯函数:合并时机由 session 层管。

注:max_bytes 约束**有效内容行**;截断发生时追加的诊断警告行(`[memdir 截断:...]`)
为可观测信息,计在预算之外——故 text 总字节可略超 max_bytes 一个警告行长度。"""

import re
from dataclasses import dataclass

_LAYER_ORDER = ("_common", "domain", "session")  # 低 → 高优先级
_LINK_RE = re.compile(r"\]\(([^)]+)\)")  # 抽 - [T](file.md) — d 里的 file.md 作同名键


@dataclass
class MergedMemory:
    text: str
    truncated: bool
    dropped: int  # 因截断丢弃的索引行数


def _file_key(line: str) -> str | None:
    m = _LINK_RE.search(line)
    return m.group(1) if m else None


def merge_memory_index(
    layers: dict[str, str], *, max_lines: int, max_bytes: int
) -> MergedMemory:
    # 同名文件按 _common < domain < session 取最高优先级;无链接的行按出现顺序保留
    by_key: dict[str, str] = {}
    loose: list[str] = []
    for layer in _LAYER_ORDER:
        for raw in layers.get(layer, "").splitlines():
            line = raw.rstrip()
            if not line.strip():
                continue
            k = _file_key(line)
            if k is None:
                loose.append(line)
            else:
                by_key[k] = line  # 后写覆盖前写 = 高优先级覆盖低优先级
    merged = list(by_key.values()) + loose
    truncated = False
    dropped = 0
    if len(merged) > max_lines:
        dropped += len(merged) - max_lines
        merged = merged[:max_lines]
        truncated = True
    text = "\n".join(merged)
    if len(text.encode()) > max_bytes:
        # 按字节再截:逐行累加到不超 max_bytes
        acc: list[str] = []
        size = 0
        for ln in merged:
            b = len(ln.encode()) + 1
            if size + b > max_bytes:
                break
            acc.append(ln)
            size += b
        dropped += len(merged) - len(acc)
        merged = acc
        text = "\n".join(merged)
        truncated = True
    if truncated:
        text = text + f"\n[memdir 截断:丢弃 {dropped} 行,超 {max_lines} 行/{max_bytes} 字节]"
    return MergedMemory(text=text, truncated=truncated, dropped=dropped)
