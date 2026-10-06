# MDR 回归测试

`api/` 覆盖当前 HTTP/CLI 合同，`unit/` 覆盖预测器、路由、报告与证据规则，`science_v2/` 保留结构/肽特征、合成小模型和指标正确性测试。

需要真实本地工件的测试（例如运行时清单、API 实际预测、CWD 工件检查）使用 `data/mdr_gnb/models/`；该目录不随 GitHub 提交。完整本地回归请安装 `chemistry` 和 `api` extras。CI 的基础离线测试只运行不需要这些工件的选择集。

历史科学验证战役及报告快照测试已移到同级归档目录 `PRAXIS-virtualcell-old/records/2026-10-06/migrated-legacy-tests/mdr_gnb/`，不纳入当前默认回归。归档原因包括旧战役与当前单药请求及报告 schema 不兼容，以及报告目录重排造成的快照差异；本次未重算或改写科学结果。

标记 `local_artifacts` 的用例依赖本地 MDR 工件/科学运行环境，可用 `-m "not local_artifacts"` 排除。基础 CI 仍使用明确的离线选择集；该标记不宣称完整套件可在缺少所有可选依赖时收集。
