"""v0.6:praxis-vc 命令行入口。

  praxis-vc run  --request examples/ahr_k562.json --mode offline --out runs/ahr
  praxis-vc ask  --text "在 human 细胞里敲掉 AHR 会怎么样" --mode llm-assisted --out runs/ahr_llm
  praxis-vc serve --host 127.0.0.1 --port 8000        # FastAPI(需 [api] extra)
  praxis-vc web  --api http://127.0.0.1:8000          # Streamlit(需 [web] extra)

React 正式网站(praxis_vc_react/,只读展示,不参与预测/治理决策):
  开发:另起 `cd praxis_vc_react && npm run dev`(5173),serve 作后端。
  生产:`cd praxis_vc_react && npm run build` 后,serve 会自动把 dist 挂到 "/"
        (同源),浏览器开 http://127.0.0.1:8000 即前端+后端。

默认 offline;llm-assisted 需 .env 有 DEEPSEEK_API_KEY,否则自动 fallback。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from praxis_virtualcell import __version__


def _config(mode: str):
    from praxis_virtualcell.core.config import Mode, RuntimeConfig
    if mode in ("llm-assisted", "llm_assisted"):
        os.environ["PRAXIS_VIRTUALCELL_MODE"] = "llm_assisted"
        return RuntimeConfig.from_env()
    return RuntimeConfig(mode=Mode.OFFLINE, llm_enabled=False)


def _cmd_run(a) -> int:
    from praxis_virtualcell.io.job_store import JobStore
    from praxis_virtualcell.workflows.run_virtualcell_query import run_query
    cfg = _config(a.mode)
    req = json.loads(open(a.request, encoding="utf-8").read())
    out = run_query(req, config=cfg, enable_llm_report=a.llm_report)
    if a.out:
        JobStore(os.path.dirname(a.out) or "runs").save(os.path.basename(a.out), request=req, result=out)
    print(json.dumps({"reliability_decision": out["reliability_decision"],
                      "llm_used_for_prediction": out["llm_used_for_prediction"],
                      "mode": out["mode"]}, ensure_ascii=False, indent=2))
    return 0


def _cmd_ask(a) -> int:
    from praxis_virtualcell.io.job_store import JobStore
    from praxis_virtualcell.workflows.run_virtualcell_query import parse_query, run_query
    cfg = _config(a.mode)
    parsed = parse_query(a.text, config=cfg)
    print("== parsed ==")
    print(json.dumps({"candidate_request": parsed["candidate_request"], "parser": parsed["parser"],
                      "schema_valid": parsed["schema_valid"], "missing_fields": parsed["missing_fields"],
                      "llm_used": parsed["llm_used"], "fallback_used": parsed["fallback_used"]},
                     ensure_ascii=False, indent=2))
    if not parsed["schema_valid"]:
        print("== clarification_required ==", parsed["missing_fields"] or parsed["errors"])
        return 2
    if not a.yes:
        print("(加 --yes 确认执行;或用 web/API 的确认页)")
        return 0
    out = run_query(parsed["candidate_request"], config=cfg, enable_llm_report=a.llm_report)
    if a.out:
        JobStore(os.path.dirname(a.out) or "runs").save(os.path.basename(a.out),
                 candidate=parsed["candidate_request"], result={**out, "parsed": parsed})
    print("== reliability_decision ==")
    print(json.dumps(out["reliability_decision"], ensure_ascii=False, indent=2))
    return 0


def _cmd_serve(a) -> int:
    import uvicorn
    uvicorn.run("praxis_vc_api.main:app", host=a.host, port=a.port, reload=False)
    return 0


def _cmd_web(a) -> int:
    os.environ["PRAXIS_VC_API"] = a.api
    import subprocess
    return subprocess.call([sys.executable, "-m", "streamlit", "run",
                            "praxis_vc_web/app.py", "--server.address", a.host, "--server.port", str(a.port)])


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="praxis-vc", description="PRAXIS-VirtualCell 本地科学家界面")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="从 request JSON 跑一次(离线确定性)")
    r.add_argument("--request", required=True)
    r.add_argument("--mode", default="offline")
    r.add_argument("--out", default=None)
    r.add_argument("--llm-report", action="store_true", dest="llm_report")
    r.set_defaults(fn=_cmd_run)
    k = sub.add_parser("ask", help="自然语言提问 → 解析 → (--yes)执行")
    k.add_argument("--text", required=True)
    k.add_argument("--mode", default="offline")
    k.add_argument("--out", default=None)
    k.add_argument("--yes", action="store_true")
    k.add_argument("--llm-report", action="store_true", dest="llm_report")
    k.set_defaults(fn=_cmd_ask)
    s = sub.add_parser("serve", help="启动 FastAPI 本地服务")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.set_defaults(fn=_cmd_serve)
    w = sub.add_parser("web", help="启动 Streamlit 本地网页")
    w.add_argument("--api", default="http://127.0.0.1:8000")
    w.add_argument("--host", default="127.0.0.1")
    w.add_argument("--port", type=int, default=8501)
    w.set_defaults(fn=_cmd_web)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
