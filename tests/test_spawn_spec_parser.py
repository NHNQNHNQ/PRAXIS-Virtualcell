"""v0.15.0: auto 模式下,chat-stream 末尾要从 assistant 输出找 EXECUTABLE SPEC
并自动转后台 spawn。parser 只负责"找出 prompt 内容",决策在调用方。

规则(故意保守,避免抓飞):
1. 文本必须含 'EXECUTABLE SPEC' 字样(不区分大小写)
2. 取**最长 fenced code block(```...```)**作为 spawn prompt
3. fenced block 可以带语言(```python / ```bash)也可以裸 ```
4. 不命中 → None(调用方跳过 spawn)
"""
from __future__ import annotations

import pytest

from praxis2.spawn.spec_parser import parse_executable_spec


def test_no_spec_keyword_returns_none():
    """文本没有 EXECUTABLE SPEC 字样 → None。"""
    text = "这是普通回答。\n\n```python\nprint('hi')\n```"
    assert parse_executable_spec(text) is None


def test_keyword_but_no_code_block_returns_none():
    """有 EXECUTABLE SPEC 字样但没 fenced code block → None。"""
    text = "我会给你一个 EXECUTABLE SPEC,但还没写完。"
    assert parse_executable_spec(text) is None


def test_keyword_with_single_code_block():
    """SPEC 字样 + 1 个 code block → 提取该 block 内容。"""
    text = """EXECUTABLE SPEC 如下:

```python
primes = [n for n in range(2, 50) if all(n % d for d in range(2, int(n**0.5)+1))]
print(primes)
```
"""
    out = parse_executable_spec(text)
    assert out is not None
    assert "primes = [n for n in range(2, 50)" in out
    assert "print(primes)" in out
    # fence 本身不出现在 prompt 里
    assert "```" not in out


def test_multiple_blocks_picks_longest():
    """多个 fenced block 取最长(主体代码而非示例 import)。"""
    text = """EXECUTABLE SPEC:

```yaml
task_id: demo
runtime: python3.11
```

主要代码:
```python
def is_prime(n):
    if n < 2: return False
    for d in range(2, int(n**0.5)+1):
        if n % d == 0: return False
    return True

primes = [n for n in range(2, 50) if is_prime(n)]
print(primes)
```
"""
    out = parse_executable_spec(text)
    assert out is not None
    # 取了 Python 块(更长)而不是 yaml 元数据块
    assert "def is_prime" in out
    assert "task_id:" not in out


def test_case_insensitive_keyword():
    """关键字大小写不敏感(executable spec / Executable Spec 都行)。"""
    text = """好,这里是 executable spec:

```bash
echo "hello from spawn"
```
"""
    out = parse_executable_spec(text)
    assert out is not None
    assert 'echo "hello from spawn"' in out


def test_bare_fence_no_lang():
    """裸 ``` 不带语言也应匹配。"""
    text = """EXECUTABLE SPEC:

```
print("hi")
print("world")
```
"""
    out = parse_executable_spec(text)
    assert out is not None
    assert 'print("hi")' in out
    assert 'print("world")' in out
