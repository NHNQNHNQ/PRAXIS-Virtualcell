# 安装与运行

需要 Python 3.11 或更新版本。

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[api,chemistry,omics,dev]'
```

T7 使用 ExFAT 时，Python 安装工具可能误识别 AppleDouble 元数据。建议把虚拟环境放到 Mac 的 APFS 磁盘，再将项目的 `.venv` 链接到它。当前工作区使用 `/Users/mzy/.local/share/venvs/praxis-virtualcell-llm`：

```bash
python3.11 -m venv "$HOME/.local/share/venvs/praxis-virtualcell-llm"
ln -s "$HOME/.local/share/venvs/praxis-virtualcell-llm" .venv
.venv/bin/python -m pip install -e '.[api,chemistry,omics,dev]'
```

复制 `.env.example` 为本地 `.env`，配置 DeepSeek 凭据。环境变量优先于文件；`.env` 不提交 Git。本工作区沿用了原平台凭据，值不写入报告或命令输出。

默认输入包根为仓库 `data/organisms/`，可用 `praxis-vc --data-root DIRECTORY` 覆盖。GitHub 不保存完整表达矩阵，准备方式见 `docs/OMICS.md`。缺少本地数据时 `profiles` 返回空列表。

```bash
.venv/bin/praxis-vc profiles
.venv/bin/praxis-vc inspect --profile AB5075-AZI000
.venv/bin/praxis-vc serve --port 8787
```

浏览器打开 `http://127.0.0.1:8787`。单候选与批量入口：

```bash
.venv/bin/praxis-vc analyze --profile AB5075-AZI000 --smiles '候选SMILES' --output reports/llm_live/result.json
.venv/bin/praxis-vc batch --profile AB5075-AZI000 --input candidates/synthemol_20260923/repeat_1/molecules.csv --output reports/llm_live/batch
```

`--env-file` 和 `--data-root` 是全局参数，放在子命令之前。每个候选输出 JSON 与同名 Markdown；批量另外输出 `summary.json`。未完成或不支持时保留原因与轨迹，CLI 返回非零状态。

批量默认顺序执行，可加 `--concurrency 4` 同时处理最多四个候选。实际完成顺序可以不同，文件编号与汇总顺序始终对应输入 CSV。

默认每轮输出预算是 65,536 tokens，思考强度为 `high`。真实批量验证发现，原先 10,000 tokens 会截断部分 JSON；思考和最终回答都占用输出预算。配置文件可设 `PRAXIS_MAX_OUTPUT_TOKENS`、`PRAXIS_REASONING_EFFORT`，CLI 可用 `--max-output-tokens`、`--reasoning-effort low|high|max` 覆盖。对应 API 参数见 [DeepSeek Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)。

默认最多八轮，包括最多一次引用纠正。最后一轮关闭新工具调用并要求提交最终 JSON；若仍截断、引用未通过或没有读取实际基因，保留失败状态，不能据此输出有效预测。

`praxis-mdr` 是历史工具 CLI，独立 direct MIC 组件也不由新入口调用。
