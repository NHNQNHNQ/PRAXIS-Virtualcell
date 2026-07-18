# Changelog

本文件记录面向发布的产品变化。科学能力声明仍以 `reports/phase10/PHASE10_GATE.md` 为准；本地版本或 tag 不等于已在 GitHub 发布。

## 1.6.0 — local candidate, unreleased

- 将活跃开发副本从受 AppleDouble/磁盘空间风险影响的 ExFAT 仓库迁移到 APFS，并保存 bundle、stash 和受保护工作区资产。
- 建立本地、GitHub、`.53` 三端同步台账；没有改写历史、远端 refs 或部署状态。
- 建立分层质量基线，恢复 Ruff 绿灯，并把核心、前端、legacy、integration、LLM、remote 和 operational 测试边界显式化。
- 将 GitHub Actions 拆为 Python core、frontend/Playwright、legacy unit 三个 job。
- 建立单一产品版本源；Python 包、兼容包、CLI、OpenAPI、health API 和前端 package mirror 现在保持一致。
- health API 新增产品版本、API/runtime protocol 与 build SHA，同时保留旧 `runtime_version` 字段。
- 更新当前 README、安装、测试、UI 和版本文档。候选尚未 push、tag 或部署。
- 新增可访问的浅色/深色主题、结果工具栏与导出、输入预设、历史切换和响应式布局；这些用户可见扩展使原 `1.5.1` 补丁候选在未发布前被 `1.6.0` 取代。
- 严格校验显式结构化输入，同时保留 LLM 候选的容错澄清路径；`/api/jobs` 只执行和保存最终归一化白名单请求。
- 修复 Ask/Review/Run/Results 阶段的迟到响应、模式切换、历史切换和运行中导航竞态，并让非法可编辑字段必须经用户实际修正。
- 扩充离线、abstain、结果、主题、历史、稳定性和几何 E2E 门禁；真实 LLM E2E 仍为显式 opt-in，不以离线 skip 冒充验证。
- 对原始但可归一化的合法请求，科学输出与裁决保持不变；job/trace/provenance 标识或输入哈希可能因执行前统一归一化而变化。

## 1.5.0 — local milestone

本地 annotated tag `v1.5.0` 指向 `176019e`。该 tag 从未在 2026-07-18 实时观察到的 GitHub/`.53` 上发布，且历史树仍使用 `0.0.0` package placeholder；不得移动或重建 tag 来隐藏这项历史债务。

## 0.8.0 — published baseline

2026-07-18 实时核验时，GitHub `main`、`.53 main` 和两端最高已发布 tag 均停在 `v0.8.0 → 7fc4aa5`。后续本地里程碑的完整映射见 `docs/status/SYNC-STATE.md`。
