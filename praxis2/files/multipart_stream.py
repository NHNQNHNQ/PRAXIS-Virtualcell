"""multipart/form-data 流式 parser(stdlib 实现,无第三方依赖)。

ASGI receive → 内部 buffer 找 boundary → asyncio.Queue 推 chunks。
不读全 body 到内存,适配大文件上传。

设计:
  parse_upload(receive, headers) -> {filename, content_type, body_iter}

  - pump() 协程在后台不断调 receive(),维护 buffer,找 boundary。
  - parser 解析到第一个 part 的 Content-Disposition 后,通过 Queue 发
    "__READY__" 信号,parse_upload 即可返回 filename/content_type。
  - 后续 body chunks 继续经 Queue 流给调用方的 body_iter。

MultipartError:missing boundary / no file field / no closing boundary。
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator
from typing import Any


class MultipartError(Exception):
    """multipart 解析错误:无 boundary / 无 file field / 解析中断。"""


_BOUNDARY_RE = re.compile(rb"boundary=([^\s;]+)")


def _extract_boundary(content_type: bytes) -> bytes:
    """从 Content-Type 头提取 boundary 值。"""
    m = _BOUNDARY_RE.search(content_type)
    if not m:
        raise MultipartError("missing boundary in Content-Type")
    return m.group(1).strip(b'"').strip()


async def parse_upload(
    receive,
    headers: list[tuple[bytes, bytes]],
) -> dict[str, Any]:
    """解析 multipart/form-data 上传,返 {filename, content_type, body_iter}。

    filename 与 content_type 在返回前已可用。
    body_iter 是 async generator,后续流式 yield 文件内容 chunks。
    """
    # 找 Content-Type 头
    ct = b""
    for k, v in headers:
        if k.lower() == b"content-type":
            ct = v
            break

    if not ct.startswith(b"multipart/form-data"):
        raise MultipartError(f"not multipart: {ct!r}")

    boundary = _extract_boundary(ct)

    # multipart 关键分隔符
    sep_open   = b"--" + boundary + b"\r\n"   # 第一个 part 起始
    sep_middle = b"\r\n--" + boundary          # part 之间 / 结尾前缀
    # 结束标志: sep_middle + "--"

    state: dict[str, Any] = {
        "filename": None,
        "content_type": "application/octet-stream",
    }
    queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()

    async def pump() -> None:  # noqa: C901
        """后台协程:不断 receive(),维护 buffer,解析并推 Queue。"""
        buf = b""
        headers_parsed = False

        try:
            while True:
                msg = await receive()
                chunk: bytes = msg.get("body", b"")
                more_body: bool = msg.get("more_body", False)
                buf += chunk

                if not headers_parsed:
                    # 等 sep_open 出现
                    if sep_open not in buf:
                        if not more_body:
                            queue.put_nowait(("__ERROR__", "no file part found"))
                            return
                        continue

                    # 剥掉 sep_open 前面的内容(preamble)
                    _, after_open = buf.split(sep_open, 1)

                    # 等 part header 结束标志 \r\n\r\n
                    hdr_end = after_open.find(b"\r\n\r\n")
                    if hdr_end < 0:
                        # header 尚未完整到达;把 after_open 存回
                        buf = sep_open + after_open
                        if not more_body:
                            queue.put_nowait(("__ERROR__", "no file part headers"))
                            return
                        continue

                    header_block = after_open[:hdr_end]
                    buf = after_open[hdr_end + 4:]  # 跳过 \r\n\r\n,buf 现在是 body 起点

                    # 解析 Content-Disposition: filename
                    m_fn = re.search(rb'filename="([^"]*)"', header_block)
                    if m_fn:
                        state["filename"] = m_fn.group(1).decode("utf-8", errors="replace")

                    # 解析 Content-Type(part 级别,可选)
                    m_ct = re.search(rb"(?i)Content-Type:\s*(\S+)", header_block)
                    if m_ct:
                        state["content_type"] = m_ct.group(1).decode("ascii", errors="replace")

                    headers_parsed = True
                    queue.put_nowait(("__READY__", None))
                    # 不 continue:继续处理 buf 里已有的 body 内容

                # --- headers_parsed == True ---
                # 在 buf 中寻找 sep_middle(内容结束点)
                end_idx = buf.find(sep_middle)
                if end_idx >= 0:
                    # 找到结尾:把 [0:end_idx] 当 body 最后一块推出
                    if end_idx > 0:
                        queue.put_nowait(("CHUNK", buf[:end_idx]))
                    queue.put_nowait(("DONE", None))
                    return

                # 尚未找到 sep_middle:安全推送 buf 的前段
                # 保留末尾 len(sep_middle)-1 字节,防止 boundary 跨 chunk 被截断
                keep = len(sep_middle) - 1
                safe = len(buf) - keep
                if safe > 0:
                    queue.put_nowait(("CHUNK", buf[:safe]))
                    buf = buf[safe:]

                if not more_body:
                    # body 流已结束但没遇到 closing boundary
                    # 可能是纯关闭边界在 buf 里
                    end_idx2 = buf.find(sep_middle)
                    if end_idx2 >= 0:
                        if end_idx2 > 0:
                            queue.put_nowait(("CHUNK", buf[:end_idx2]))
                        queue.put_nowait(("DONE", None))
                    else:
                        queue.put_nowait(("__ERROR__", "no closing boundary"))
                    return

        except Exception as exc:  # noqa: BLE001
            queue.put_nowait(("__ERROR__", str(exc)))

    pump_task = asyncio.create_task(pump())

    # 等待 pump 发送 __READY__ 或错误
    while True:
        kind, payload = await queue.get()
        if kind == "__READY__":
            break
        if kind == "__ERROR__":
            pump_task.cancel()
            raise MultipartError(payload)
        if kind == "DONE":
            # body 为空但 headers 已解析 — 认为 filename 存在时合法(0 字节文件)
            # 若 filename 都没有则报错
            if state["filename"] is None:
                pump_task.cancel()
                raise MultipartError("no file content / no filename")
            # 0 字节文件:直接返回空迭代器

            async def _empty() -> AsyncIterator[bytes]:
                return
                yield  # noqa: B901  — 使此函数成为 async generator

            return {
                "filename": state["filename"],
                "content_type": state["content_type"],
                "body_iter": _empty(),
            }

    if state["filename"] is None:
        pump_task.cancel()
        raise MultipartError("no filename in Content-Disposition")

    async def body_iter() -> AsyncIterator[bytes]:
        """流式 yield 文件内容 chunks,直到 pump 发 DONE。"""
        while True:
            kind, payload = await queue.get()
            if kind == "CHUNK":
                yield payload
            elif kind == "DONE":
                break
            elif kind == "__ERROR__":
                raise MultipartError(payload)
        await pump_task

    return {
        "filename": state["filename"],
        "content_type": state["content_type"],
        "body_iter": body_iter(),
    }
