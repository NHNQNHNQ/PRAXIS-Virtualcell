from praxis2.memory.memdir import merge_memory_index


def test_same_name_session_overrides_domain_overrides_common():
    common = "- [Rule](rmcp.md) — common 版\n- [A](a.md) — common A"
    domain = "- [Rule](rmcp.md) — domain 版\n- [B](b.md) — domain B"
    session = "- [Rule](rmcp.md) — session 版"
    m = merge_memory_index(
        {"_common": common, "domain": domain, "session": session},
        max_lines=200, max_bytes=25_000,
    )
    # 同名 rmcp.md 取最高优先级 session 版;a.md/b.md 各保留一次
    assert "session 版" in m.text
    assert "common 版" not in m.text and "domain 版" not in m.text
    assert m.text.count("rmcp.md") == 1
    assert "a.md" in m.text and "b.md" in m.text
    assert m.truncated is False


def test_hard_truncation_by_lines_sets_flag_and_warning():
    big = "\n".join(f"- [T{i}](f{i}.md) — d{i}" for i in range(500))
    m = merge_memory_index({"_common": big}, max_lines=200, max_bytes=25_000)
    assert m.truncated is True
    assert len(m.text.splitlines()) <= 201  # 200 行 + 1 行截断警告
    assert "截断" in m.text  # 警告行可见
    assert m.dropped >= 300


def test_hard_truncation_by_bytes_independent_of_line_count():
    # 行数远低于 max_lines,但总字节超 max_bytes → 字节路径独立触发(§7.4.1 双保护)
    big = "\n".join(f"- [T{i}](f{i}.md) — {'x' * 300}" for i in range(100))
    m = merge_memory_index({"_common": big}, max_lines=200, max_bytes=5_000)
    assert m.truncated is True and m.dropped > 0
    assert "截断" in m.text
    # 锁 max_bytes 语义:有效内容受预算约束,仅警告行额外(docstring 契约可测化)
    assert len(m.text.encode()) < 5_000 + 200


def test_empty_layers_yield_empty_not_crash():
    m = merge_memory_index({}, max_lines=200, max_bytes=25_000)
    assert m.text == "" and m.truncated is False and m.dropped == 0
