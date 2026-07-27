# P0 基线冻结

- 实施基线：`8e0d06348ebdf22e076037e6d661094ae877c5d1`
- 工作位置：独立 sibling worktree `/Volumes/T7/PRAXIS-virtualcell-p0`；原 `/Volumes/T7/PRAXIS-virtualcell` dirty 工作树未切换、未覆盖。
- GitHub 只读：`refs/heads/main` 指向 `8e0d06348ebdf22e076037e6d661094ae877c5d1`。
- `.53` 只读：`/home/zkyd/data1/mzy/PRAXIS-virtualcell` 的 `codex/deploy-v1.6.0` HEAD 为同一 SHA；仅有未跟踪 `vc_api.log`，未写入。
- 说明：dirty T7 工作树缺少 `docs/TESTING.md`、`docs/VERSIONING.md`；本 P0 clean baseline 中两份文档存在并已读取。

## 代表性离线报告

输入：`examples/ahr_k562.json`，`Mode.OFFLINE`、`llm_enabled=False`。

- `structured_report` canonical JSON SHA-256：`27a16eef2493bf953c4e572f3480d9c80e4013b5f92ebca4b8bfe0f59722228b`
- 9 段 Markdown SHA-256：`ed4b03d12e9618a7685a19106609f2ec0b0461ccf533c6beec20e7318ec7898a`
- 报告包含完整 `request`；首个 ActiveLearning candidate：`genetic_hub@human:AHR`
- 该哈希是在 P0 request seam 修复后冻结；后续阶段若改变报告字节，必须更新版本化基线并说明原因。
- P4.2 起，上述两个 SHA-256 也由
  `praxis_virtualcell/tests/baseline/test_baseline_offline_report.py` 直接断言，文档值与
  可执行基线不得分离。

## 测试冻结口径

规范命令来自 `docs/TESTING.md`，不把 core 与 legacy 相加：

```bash
python -m pytest praxis_virtualcell/tests \
  -m "not llm" -o addopts='' -q -ra

python -m pytest tests \
  -m "not (integration or llm or remote)" \
  -o addopts='' -q -ra

ruff check .
```

本次在 Python 3.13.12 editable 环境实测：

| 口径 | 结果 | 说明 |
|---|---|---|
| P0 seam 定向 | `7 passed / 0 failed` | 包含 Report request 与 AL candidate 回归 |
| VirtualCell core non-LLM | `959 passed / 43 skipped / 9 deselected / 0 failed` | 当前环境含 torch，部分 fail-closed 本地测试按 marker skip；无 LLM/remote opt-in |
| Ruff | `All checks passed` | 全仓 lint |
| legacy unit | `1139 passed / 58 skipped / 105 deselected / 1 failed` | 唯一失败为继承 `tests/test_mcp_pool.py::test_pool_slow_server_startup_timeout_skipped`：slow 与 good MCP server 均握手超时；未改继承模块 |

`docs/TESTING.md` 中的 fresh-lock 目标数字（core `965/35/9`、legacy `1139/59/105`）保留为仓库质量契约；本次报告使用的是实际执行环境数字，不把环境差异冒充为绿勾。
