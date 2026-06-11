from praxis2.core.prompt import Section
from praxis2.entry.cli import bind_dump_prompts, context_command, parse_args


def test_parse_args_dump_prompts_flag():
    ns = parse_args(["--dump-prompts", "/tmp/p.jsonl", "--message", "hi"])
    assert ns.dump_prompts == "/tmp/p.jsonl"
    assert ns.message == "hi"


def test_parse_args_no_dump_prompts_defaults_empty():
    ns = parse_args(["--message", "hi"])
    assert ns.dump_prompts == ""  # 空 = 关(与 config.dump_prompts 同语义)


def test_bind_dump_prompts_returns_none_when_empty():
    # 空路径 → 不绑(on_request=None,query() 行为零回归)
    assert bind_dump_prompts("") is None


def test_bind_dump_prompts_returns_recorder_writing_jsonl(tmp_path):
    p = tmp_path / "dump.jsonl"
    rec = bind_dump_prompts(str(p))
    assert rec is not None
    rec({"model": "m", "messages": [{"role": "user", "content": "hi"}]})
    rec({"model": "m", "messages": [{"role": "user", "content": "yo"}]})
    lines = p.read_text().strip().splitlines()
    assert len(lines) == 2  # 每次 API 请求一行 JSON(可逐行 diff,§7.2.8)
    import json
    assert json.loads(lines[0])["model"] == "m"


def test_context_command_segments_tokens_not_repl():
    # /context 走命令函数(非 REPL):调 M2 analyze_context 分段统计 token
    sections = [
        Section("identity", "你是助手"),
        Section("rmcp", "先检索后执行"),
    ]
    out = context_command(sections)
    assert out["command"] == "/context"
    assert len(out["segments"]) == 2
    names = {s["name"] for s in out["segments"]}
    assert names == {"identity", "rmcp"}
    assert all(s["tokens"] > 0 for s in out["segments"])
    assert out["total_tokens"] == sum(s["tokens"] for s in out["segments"])


def test_context_command_is_callable_by_admin_skill_not_interactive():
    # S2:不做 REPL;context_command 是纯函数(可被 admin/Skill 调),不阻塞
    out = context_command([Section("x", "短")])
    assert isinstance(out, dict)  # 返回结构化结果,非进入交互循环
