from praxis2.core.prompt import Section
from praxis2.entry.cli import bind_dump_prompts, context_command, parse_args


def test_parse_args_dump_prompts_flag():
    ns = parse_args(["--dump-prompts", "/tmp/p.jsonl", "--message", "hi"])
    assert ns.dump_prompts == "/tmp/p.jsonl"
    assert ns.message == "hi"


def test_parse_args_no_dump_prompts_defaults_empty():
    ns = parse_args(["--message", "hi"])
    assert ns.dump_prompts == ""


def test_bind_dump_prompts_returns_none_when_empty():

    assert bind_dump_prompts("") is None


def test_bind_dump_prompts_returns_recorder_writing_jsonl(tmp_path):
    p = tmp_path / "dump.jsonl"
    rec = bind_dump_prompts(str(p))
    assert rec is not None
    rec({"model": "m", "messages": [{"role": "user", "content": "hi"}]})
    rec({"model": "m", "messages": [{"role": "user", "content": "yo"}]})
    lines = p.read_text().strip().splitlines()
    assert len(lines) == 2
    import json

    assert json.loads(lines[0])["model"] == "m"


def test_context_command_segments_tokens_not_repl():

    sections = [
        Section("identity", "\u4f60\u662f\u52a9\u624b"),
        Section("rmcp", "\u5148\u68c0\u7d22\u540e\u6267\u884c"),
    ]
    out = context_command(sections)
    assert out["command"] == "/context"
    assert len(out["segments"]) == 2
    names = {s["name"] for s in out["segments"]}
    assert names == {"identity", "rmcp"}
    assert all(s["tokens"] > 0 for s in out["segments"])
    assert out["total_tokens"] == sum(s["tokens"] for s in out["segments"])


def test_context_command_is_callable_by_admin_skill_not_interactive():

    out = context_command([Section("x", "\u77ed")])
    assert isinstance(out, dict)
