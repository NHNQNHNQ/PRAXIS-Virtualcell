"""§7.2.8/§8 S2:--dump-prompts argv 解析绑定 + /context 命令。

M2 已交付底层能力(make_jsonl_recorder/analyze_context/section_hash +
query() on_request 注入缝);M6 在此绑定字面 argv 与用户侧入口。
**§8 S2 不做 REPL 命令系统**:/context 是可被 admin/Skill 调用的纯
命令函数(返回结构化分段统计),非交互循环。"""

import argparse

from praxis2.core.prompt import Section, section_hash
from praxis2.core.prompt_debug import analyze_context, make_jsonl_recorder


def parse_args(argv: list[str]) -> argparse.Namespace:
    """字面 --dump-prompts argv 解析(M2 carry,绑定时机 M6,§7.2.8)。"""
    p = argparse.ArgumentParser(prog="praxis2", add_help=False)
    p.add_argument("--dump-prompts", dest="dump_prompts", default="",
                   help="非空则每次 API 请求完整 prompt 落 JSONL 到该路径")
    p.add_argument("--message", dest="message", default="")
    return p.parse_args(argv)


def bind_dump_prompts(path: str):
    """绑定 --dump-prompts → make_jsonl_recorder 回调喂 query(on_request=)。
    空路径 → None(不绑,query() 行为零回归,与 config.dump_prompts 同语义)。"""
    if not path:
        return None
    return make_jsonl_recorder(path)


def context_command(sections: list[Section]) -> dict:
    """/context 入口(§7.2.8,§8 S2 走 admin/Skill 非 REPL):把 effective
    system prompt 按 section 分段统计 token + 给 section_hash 供快照比对。
    返回结构化结果(可被 admin/Skill 调用,非交互循环)。"""
    segs = analyze_context(sections)
    return {
        "command": "/context",
        "segments": [{"name": s.name, "tokens": s.tokens} for s in segs],
        "total_tokens": sum(s.tokens for s in segs),
        "section_hash": section_hash(sections),
    }
