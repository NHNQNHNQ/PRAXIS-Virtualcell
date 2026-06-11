"""M10 files multipart_stream:python-multipart 流式 parser 包装。"""
from __future__ import annotations

import pytest


def _build_multipart_body(
    boundary: bytes, filename: bytes, content: bytes,
    content_type: bytes = b"application/octet-stream",
) -> bytes:
    """构造一个最小 multipart/form-data body,只含一个 file field。"""
    return (
        b"--" + boundary + b"\r\n"
        + b'Content-Disposition: form-data; name="file"; filename="' + filename + b'"\r\n'
        + b"Content-Type: " + content_type + b"\r\n\r\n"
        + content + b"\r\n"
        + b"--" + boundary + b"--\r\n"
    )


def _mk_receive(body: bytes, chunk_size: int = 1024):
    """ASGI receive 模拟,分块发 body。最后空 chunk + more_body=False。"""
    chunks = [body[i:i+chunk_size] for i in range(0, len(body), chunk_size)]
    iter_chunks = iter(chunks)

    async def receive():
        try:
            chunk = next(iter_chunks)
            return {"type": "http.request", "body": chunk, "more_body": True}
        except StopIteration:
            return {"type": "http.request", "body": b"", "more_body": False}
    return receive


async def test_parse_upload_returns_filename_and_chunks():
    from praxis2.files.multipart_stream import parse_upload

    boundary = b"BOUNDARY_TEST_X"
    body = _build_multipart_body(boundary, b"test.pdb", b"hello world")
    headers = [(b"content-type", b"multipart/form-data; boundary=" + boundary)]

    result = await parse_upload(_mk_receive(body), headers)
    assert result["filename"] == "test.pdb"
    chunks = b""
    async for c in result["body_iter"]:
        chunks += c
    assert chunks == b"hello world"


async def test_parse_upload_streams_large_body():
    """100 KB body,分多 chunk receive,parser 流式 yield 出来。"""
    from praxis2.files.multipart_stream import parse_upload

    boundary = b"BOUNDARY_BIG"
    content = b"x" * (100 * 1024)
    body = _build_multipart_body(boundary, b"big.bin", content)
    headers = [(b"content-type", b"multipart/form-data; boundary=" + boundary)]

    result = await parse_upload(_mk_receive(body, chunk_size=4096), headers)
    total = 0
    async for c in result["body_iter"]:
        total += len(c)
    assert total == 100 * 1024
    assert result["filename"] == "big.bin"


async def test_parse_upload_missing_boundary_raises():
    from praxis2.files.multipart_stream import MultipartError, parse_upload

    headers = [(b"content-type", b"multipart/form-data")]   # 无 boundary
    with pytest.raises(MultipartError):
        await parse_upload(_mk_receive(b""), headers)


async def test_parse_upload_no_file_field_raises():
    from praxis2.files.multipart_stream import MultipartError, parse_upload

    boundary = b"BOUNDARY"
    # 空 multipart(只有 closing boundary)
    body = b"--" + boundary + b"--\r\n"
    headers = [(b"content-type", b"multipart/form-data; boundary=" + boundary)]

    # parse_upload 立即抛 / 或 body_iter 消费时抛 — 两种都可,只要明确报错
    try:
        result = await parse_upload(_mk_receive(body), headers)
        with pytest.raises(MultipartError):
            async for _ in result["body_iter"]:
                pass
    except MultipartError:
        pass   # 也可
