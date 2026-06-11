import json

from praxis2.core.prompt import get_default_system_prompt
from praxis2.core.prompt_debug import (
    ContextSegment,
    analyze_context,
    make_jsonl_recorder,
)


def test_jsonl_recorder_appends_one_comparable_line_per_request(tmp_path):
    p = tmp_path / "dump.jsonl"
    rec = make_jsonl_recorder(str(p))
    rec({"model": "m", "system": [{"type": "text", "text": "s"}], "messages": [{"r": 1}]})
    rec({"model": "m", "system": [{"type": "text", "text": "s2"}], "messages": [{"r": 2}]})
    lines = p.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2  # 每次 API 请求一行,可逐行 diff 比对(§7.2.8)
    assert json.loads(lines[0])["system"][0]["text"] == "s"
    assert json.loads(lines[1])["messages"] == [{"r": 2}]


def test_analyze_context_breaks_into_named_segments_with_tokens():
    secs = get_default_system_prompt()
    segs = analyze_context(secs)
    assert all(isinstance(x, ContextSegment) for x in segs)
    names = [x.name for x in segs]
    # §7.2.8 /context:按 section 拆命名段;空 text 的边界 sentinel 段跳过
    assert "identity" in names and "safety" in names
    assert all(x.tokens > 0 for x in segs)
    # 段名与 default 的非空 section 一一对应
    non_empty = [s.name for s in secs if s.text]
    assert names == non_empty
