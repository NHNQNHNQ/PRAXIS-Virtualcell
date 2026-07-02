"""v0.6:本地 job store —— 把一次 query 的 request/candidate/report/trace/provenance/narrative/llm 落盘。

runs/<job_id>/{request,candidate_request,report,trace,provenance,narrative_report,llm_meta}。
无数据库依赖(纯文件);API/CLI/web 共用。LLM 只存 hash 元数据,不存 key/原始 prompt 敏感内容。
"""
from __future__ import annotations

import json
from pathlib import Path


class JobStore:
    def __init__(self, runs_dir: str = "runs") -> None:
        self.root = Path(runs_dir)

    def _dir(self, job_id: str) -> Path:
        d = self.root / job_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _w(self, d: Path, name: str, obj) -> None:
        if isinstance(obj, str):
            (d / name).write_text(obj, encoding="utf-8")
        else:
            (d / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    def save(self, job_id: str, *, candidate=None, request=None, result=None) -> str:
        """落盘一次 job;result 为 run_query 的返回。返回 job 目录。"""
        d = self._dir(job_id)
        if candidate is not None:
            self._w(d, "candidate_request", candidate)
        if request is not None:
            self._w(d, "request", request)
        if result is not None:
            self._w(d, "report", result.get("structured_report", {}))
            self._w(d, "trace", result.get("trace", []))
            self._w(d, "provenance", result.get("provenance", {}))
            if result.get("narrative"):
                self._w(d, "narrative_report.md", result["narrative"])
            # 确定性 Markdown 报告:每次都写(含 offline),与 LLM narrative 正交
            from praxis_virtualcell.io.report_markdown import render_report_md
            job_like = {
                "report": result.get("structured_report", {}),
                "request": request, "candidate_request": candidate,
                "trace": result.get("trace", []),
                "provenance": result.get("provenance", {}),
                "mode": result.get("mode"), "llm_enabled": result.get("llm_enabled"),
            }
            self._w(d, "report.md", render_report_md(job_like))
            # LLM 元数据只存 hash(不存 key/原文)
            llm = (result.get("parsed") or {}).get("llm_metadata") or {}
            self._w(d, "llm_meta", {k: v for k, v in llm.items() if k != "api_key"})
        (d / "status").write_text("done", encoding="utf-8")
        return str(d)

    def load(self, job_id: str) -> dict:
        d = self.root / job_id
        if not d.is_dir():
            raise FileNotFoundError(job_id)
        out: dict = {"job_id": job_id, "status": (d / "status").read_text().strip()
                     if (d / "status").is_file() else "unknown"}
        for name in ("report", "trace", "provenance", "candidate_request", "request", "llm_meta"):
            f = d / f"{name}.json"
            if f.is_file():
                out[name] = json.loads(f.read_text(encoding="utf-8"))
        nf = d / "narrative_report.md"
        if nf.is_file():
            out["narrative"] = nf.read_text(encoding="utf-8")
        rf = d / "report.md"
        if rf.is_file():
            out["report_md"] = rf.read_text(encoding="utf-8")
        return out

    def list_jobs(self) -> list[str]:
        if not self.root.is_dir():
            return []
        return sorted(p.name for p in self.root.iterdir() if p.is_dir())
