import argparse

from praxis2.core.prompt import Section, section_hash
from praxis2.core.prompt_debug import analyze_context, make_jsonl_recorder


def parse_args(argv: list[str]) -> argparse.Namespace:

    p = argparse.ArgumentParser(prog="praxis2", add_help=False)
    p.add_argument(
        "--dump-prompts",
        dest="dump_prompts",
        default="",
        help="Optional path for complete API request prompts in JSONL",
    )
    p.add_argument("--message", dest="message", default="")
    return p.parse_args(argv)


def bind_dump_prompts(path: str):

    if not path:
        return None
    return make_jsonl_recorder(path)


def context_command(sections: list[Section]) -> dict:

    segs = analyze_context(sections)
    return {
        "command": "/context",
        "segments": [{"name": s.name, "tokens": s.tokens} for s in segs],
        "total_tokens": sum(s.tokens for s in segs),
        "section_hash": section_hash(sections),
    }
