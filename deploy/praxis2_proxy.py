"""v2.0.1 — .40 同 origin 反代 + SPA 静态服务。

只用 stdlib(.40 上只有 python3.8,无 sudo),解决:
  1. 浏览器访问 http://10.102.106.40:8080/  → 同 origin 拿 SPA(无 CORS 跨域)
  2. FE 调 /api/*, /admin/*, /chat/*       → 本进程反代到 http://10.102.106.53:8001
  3. SSE chat-stream 流式直透(不缓冲)
  4. Cookie 同 origin 来回直通,SameSite=Lax 不再吞

跑法:
    python3 deploy/praxis2_proxy.py
环境变量:
    PRAXIS2_PROXY_PORT      默认 8080
    PRAXIS2_PROXY_DIST      默认 /home/hipeson/mzy/PRAXIS-2/dist
    PRAXIS2_PROXY_UPSTREAM  默认 http://10.102.106.53:8001
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn  # noqa: F401

PORT = int(os.environ.get("PRAXIS2_PROXY_PORT", "8080"))
DIST = Path(os.environ.get(
    "PRAXIS2_PROXY_DIST", "/home/hipeson/mzy/PRAXIS-2/dist"
)).resolve()
UPSTREAM = os.environ.get(
    "PRAXIS2_PROXY_UPSTREAM", "http://10.102.106.53:8001"
).rstrip("/")
PROXY_PREFIXES = ("/api/", "/admin/", "/chat/")

# urllib 默认会跟 30x,SSE / login set-cookie 不想被跟,disable
_OPENER = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())

_HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade",
    # Content-Length 由 urllib de-chunk 后会失真,统一删,改用 Connection: close 收尾
    "content-length",
}

_CTYPE_BY_EXT = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".map": "application/json",
    ".txt": "text/plain; charset=utf-8",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}


class Handler(BaseHTTPRequestHandler):
    # 默认 HTTP/1.0:Connection: close 隐式,SSE 通过 socket close 收尾,
    # 浏览器 EventSource 不依赖 Content-Length,够用且简单。
    protocol_version = "HTTP/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(
            "[%s] %s - %s\n"  # noqa: UP031
            % (self.log_date_time_string(), self.address_string(), fmt % args)
        )

    # 所有 method 统一入口
    def do_GET(self): self._dispatch()        # noqa: E704
    def do_POST(self): self._dispatch()       # noqa: E704
    def do_PUT(self): self._dispatch()        # noqa: E704
    def do_DELETE(self): self._dispatch()     # noqa: E704
    def do_OPTIONS(self): self._dispatch()    # noqa: E704
    def do_HEAD(self): self._dispatch()       # noqa: E704
    def do_PATCH(self): self._dispatch()      # noqa: E704

    def _dispatch(self) -> None:
        path = self.path.split("?", 1)[0]
        if any(path.startswith(p) for p in PROXY_PREFIXES):
            self._proxy()
        else:
            self._serve_static(path)

    # ── 静态 SPA ──────────────────────────────────────────────────────
    def _serve_static(self, path: str) -> None:
        rel = path.lstrip("/") or "index.html"
        candidate = (DIST / rel).resolve()
        try:
            candidate.relative_to(DIST)
        except ValueError:
            self.send_error(404)
            return
        if not candidate.is_file():
            # SPA fallback:未知 path → index.html(React Router 自己解析)
            candidate = DIST / "index.html"
            if not candidate.is_file():
                self.send_error(404, "index.html missing in dist/")
                return
        ctype = _CTYPE_BY_EXT.get(candidate.suffix.lower(), "application/octet-stream")
        data = candidate.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        # SPA shell 不缓存,assets 已带 hash 可长缓存
        if candidate.name == "index.html":
            self.send_header("Cache-Control", "no-cache")
        else:
            self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    # ── /api/* /admin/* /chat/* 反代 ──────────────────────────────────
    def _proxy(self) -> None:
        url = UPSTREAM + self.path
        # 读 body(POST/PUT body)
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            length = 0
        body = self.rfile.read(length) if length > 0 else None

        # 复制 headers(过滤 hop-by-hop + Host)
        req_headers = {}
        for k, v in self.headers.items():
            kl = k.lower()
            if kl in _HOP_BY_HOP or kl == "host":
                continue
            req_headers[k] = v
        # 强 close,简化流式收尾
        req_headers["Connection"] = "close"

        req = urllib.request.Request(
            url, data=body, headers=req_headers, method=self.command
        )
        try:
            resp = _OPENER.open(req, timeout=600)
            status = resp.status
            resp_headers = resp.getheaders()
        except urllib.error.HTTPError as e:
            resp = e
            status = e.code
            resp_headers = list(e.headers.items())
        except urllib.error.URLError as e:
            self.send_error(502, f"upstream unreachable: {e.reason}")
            return

        self.send_response(status)
        for k, v in resp_headers:
            if k.lower() in _HOP_BY_HOP:
                continue
            self.send_header(k, v)
        # 显式 close 给浏览器明确帧边界(SSE 也靠这个收尾)
        self.send_header("Connection", "close")
        self.end_headers()

        if self.command == "HEAD":
            try:
                resp.close()
            except Exception:
                pass
            return

        # 流式 forward(SSE 关键:逐 chunk 写出 + flush,不缓冲)
        try:
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except Exception:
            # 客户端断开(SSE abort 常见)— 忽略,让 finally 收尾
            pass
        finally:
            try:
                resp.close()
            except Exception:
                pass


class ReusableServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> None:
    if not DIST.is_dir():
        sys.stderr.write(f"dist not found: {DIST}\n")
        sys.exit(1)
    srv = ReusableServer(("0.0.0.0", PORT), Handler)
    sys.stderr.write(
        f"praxis2_proxy: 0.0.0.0:{PORT} dist={DIST} upstream={UPSTREAM}\n"
    )
    sys.stderr.flush()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.server_close()


if __name__ == "__main__":
    main()
