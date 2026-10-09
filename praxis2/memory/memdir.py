import re
from dataclasses import dataclass

_LAYER_ORDER = ("_common", "domain", "session")
_LINK_RE = re.compile(r"\]\(([^)]+)\)")


@dataclass
class MergedMemory:
    text: str
    truncated: bool
    dropped: int


def _file_key(line: str) -> str | None:
    m = _LINK_RE.search(line)
    return m.group(1) if m else None


def merge_memory_index(layers: dict[str, str], *, max_lines: int, max_bytes: int) -> MergedMemory:

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
                by_key[k] = line
    merged = list(by_key.values()) + loose
    truncated = False
    dropped = 0
    if len(merged) > max_lines:
        dropped += len(merged) - max_lines
        merged = merged[:max_lines]
        truncated = True
    text = "\n".join(merged)
    if len(text.encode()) > max_bytes:
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
        text = text + f"\n[memdir truncated: discarded {dropped} lines; exceeds {max_lines} lines/{max_bytes} bytes]"
    return MergedMemory(text=text, truncated=truncated, dropped=dropped)
