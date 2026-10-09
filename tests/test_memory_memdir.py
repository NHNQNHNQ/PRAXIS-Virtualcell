from praxis2.memory.memdir import merge_memory_index


def test_same_name_session_overrides_domain_overrides_common():
    common = "- [Rule](rmcp.md) \u2014 common \u7248\n- [A](a.md) \u2014 common A"
    domain = "- [Rule](rmcp.md) \u2014 domain \u7248\n- [B](b.md) \u2014 domain B"
    session = "- [Rule](rmcp.md) \u2014 session \u7248"
    m = merge_memory_index(
        {"_common": common, "domain": domain, "session": session},
        max_lines=200,
        max_bytes=25_000,
    )

    assert "session \u7248" in m.text
    assert "common \u7248" not in m.text and "domain \u7248" not in m.text
    assert m.text.count("rmcp.md") == 1
    assert "a.md" in m.text and "b.md" in m.text
    assert m.truncated is False


def test_hard_truncation_by_lines_sets_flag_and_warning():
    big = "\n".join(f"- [T{i}](f{i}.md) — d{i}" for i in range(500))
    m = merge_memory_index({"_common": big}, max_lines=200, max_bytes=25_000)
    assert m.truncated is True
    assert len(m.text.splitlines()) <= 201
    assert "truncated" in m.text
    assert m.dropped >= 300


def test_hard_truncation_by_bytes_independent_of_line_count():

    big = "\n".join(f"- [T{i}](f{i}.md) — {'x' * 300}" for i in range(100))
    m = merge_memory_index({"_common": big}, max_lines=200, max_bytes=5_000)
    assert m.truncated is True and m.dropped > 0
    assert "truncated" in m.text

    assert len(m.text.encode()) < 5_000 + 200


def test_empty_layers_yield_empty_not_crash():
    m = merge_memory_index({}, max_lines=200, max_bytes=25_000)
    assert m.text == "" and m.truncated is False and m.dropped == 0
