# 验证

## 2.1 纯 LLM 与组学入口

当前 CI 安装 `.[dev,api,chemistry,omics]`，运行智能体框架、组学加载、LLM 证据校验、页面 API 和保留的基础兼容测试。2026-10-06 本地同一选择集 **453 passed**；Ruff 和 `git diff --check` 通过。其中 41 条组学测试包含小型真实 H5AD 文件、损坏哈希/形状边界、来源和未给药数组隔离，68 条 LLM 分析测试验证引用拒绝、一次格式纠正与多轮思考历史。

```bash
.venv/bin/python -m pytest -q tests/agent_runtime tests/omics tests/llm_prediction tests/test_llm_platform.py \
  tests/mdr_gnb/unit/test_abstain.py tests/mdr_gnb/unit/test_features.py \
  tests/mdr_gnb/unit/test_ensembler.py tests/mdr_gnb/unit/test_critic.py \
  tests/mdr_gnb/unit/test_rule_baseline.py tests/mdr_gnb/unit/test_species_registry.py \
  tests/mdr_gnb/unit/test_report_builder.py tests/mdr_gnb/api/test_schemas.py
.venv/bin/python -m ruff check praxis2 praxis_virtualcell tests
```

GitHub 不携带本地组学源文件，真实 AB5075 文件的用例会明确跳过；合成输入包和 H5AD 文件的边界验证仍运行。已在 APFS 暂存源代码构建 2.1.0 wheel，并在仓库外从 wheel 读取实际组学包、提供静态页面，确认页面资源已打包，凭据、大型数据和实时报告未打包。

真实 API 验证与离线测试分别记录。首个真实候选已通过全部引用校验，页面可按报告链接重开，复查无需再次调用模型。实际报告保存在本地 `reports/llm_live/`。真实调用成功只说明工具链与引用格式可运行，不是独立 MIC、杀伤能力或靶点准确率评估。

## 历史组件与整合验证

```bash
.venv/bin/python -m pytest tests/agent_runtime -q
.venv/bin/python -m pytest tests/mdr_gnb -m 'not (integration or llm or remote)' -q
.venv/bin/python -m ruff check praxis2 praxis_virtualcell tests
```

`integration` 等标记用于选择测试；Redis/PostgreSQL 集成测试还检查显式连接环境变量。标记 `local_artifacts` 的 MDR 测试需要本地数据/模型及相应科学依赖，可用 `-m 'not local_artifacts'` 排除。基础 CI 使用明确的离线选择集。

AB 组件另有依赖及测试入口，见组件 README。整合验证包含从本地旧版本权重运行直接 MIC，并保持与 09-23 的较新服务器比较结果区别。

历史整合 CI 运行不依赖大型本地工件的智能体、数值工具/API 合同测试和安装检查；旧论文实验、Docker/A100 和多阶段 release 合同退出 CI。

独立组件的验证记录见 `reports/antibacterial/direct_mic/import_verification_20261006.json` 与 `reports/antibacterial/synthemol/migration_verification_20261006.json`：12 个原版本权重各复现一条留出预测，4 项 direct MIC 与 5 项生成器验证单测通过。新主包 wheel 在仓库外安装后确认版本 2.0.0、物种规则、CLI、API `/health` 与 `/species` 可用；该安装检查未装大型工件，物种可用数为零符合预期。

2026-10-06 的本地检查：CI 中完全相同的测试选择集 **335 passed**。现有 MDR 本地环境为 Python 3.11、NumPy 2.4.6、scikit-learn 1.9.0、RDKit 2026.3.3，满足当前安装约束。MDR 回归已确认 **618 条用例通过、3 条跳过**；一次整套运行记录 616 passed / 3 skipped，随后修复 species-agent 测试的迁移路径并定向确认该文件 3 passed。跳过项是未配置 Redis/PostgreSQL 和未安装 AMRFinder。未重新运行完整套件或重训模型。

历史科学 campaign 和报告快照测试保存在同级归档目录 `PRAXIS-virtualcell-old/records/2026-10-06/migrated-legacy-tests/mdr_gnb/`，不纳入当前回归。它们包含旧战役与当前单药请求校验、T6 报告 schema 不兼容的问题；VERDICT 逐字快照也受本次报告目录重排影响。原始报告和科学结果未改写或重算。当前报告目录为 `reports/antibacterial/mdr_gnb/`。
