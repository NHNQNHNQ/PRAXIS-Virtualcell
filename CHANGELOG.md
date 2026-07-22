# Changelog

本文件记录面向发布的产品变化。科学能力声明仍以 `reports/phase10/PHASE10_GATE.md` 为准；本地版本或 tag 不等于已在 GitHub 发布。

## 1.6.0 — candidate, unreleased

- 将活跃开发副本从受 AppleDouble/磁盘空间风险影响的 ExFAT 仓库迁移到 APFS，并保存 bundle、stash 和受保护工作区资产。
- 建立本地、GitHub、`.53` 三端同步台账；D1a 只发布了精确候选分支，未改变 GitHub `main`/tag、本地 `main` 或 `.53` 部署状态。
- 建立分层质量基线，恢复 Ruff 绿灯，并把核心、前端、legacy、integration、LLM、remote 和 operational 测试边界显式化。
- 将 GitHub Actions 拆为 Python core、frontend/Playwright、release wheel、Linux release container 和 legacy unit 五个 job。首次 D1a 候选 `6086e6995b1c3c01ec31075ce1164a0165cb8d43` 的 [run 29894971142](https://github.com/NHNQNHNQ/PRAXIS-Virtualcell/actions/runs/29894971142) 为 `1/5`：只有 reproducible release wheel 通过，不能宣称 CI 全绿或这些 job 都是 branch-protection required checks。
- 修复 GitHub Linux hash-lock 的平台可移植性：dev extra/lock 显式并入 `greenlet==3.5.3` 与后续 Linux 迭代发现的 `watchdog==6.0.0`，frontend CI 改用含 mechanistic/Cobra 的 dev lock，并增加 packaging 回归。提交 `d6011d8` 已通过原生 macOS 的依赖、Ruff、核心、legacy 和前端验证，以及 Linux/amd64 QEMU 的严格依赖、Ruff、packaging 和核心验证；QEMU legacy 仍有一个 `/dev/zero` 超时用例失败，最终结论必须等待 GitHub native retry。
- 建立单一产品版本源；Python 包、兼容包、CLI、OpenAPI、health API 和前端 package mirror 现在保持一致。
- health API 新增产品版本、API/runtime protocol 与 build SHA，同时保留旧 `runtime_version` 字段。
- 更新当前 README、安装、测试、UI 和版本文档。候选分支已首次发布并取得失败 CI 证据，但尚未更新 GitHub `main`、创建 release tag 或部署。
- 新增可访问的浅色/深色主题、结果工具栏与导出、输入预设、历史切换和响应式布局；这些用户可见扩展使原 `1.5.1` 补丁候选在未发布前被 `1.6.0` 取代。
- 严格校验显式结构化输入，同时保留 LLM 候选的容错澄清路径；`/api/jobs` 只执行和保存最终归一化白名单请求。
- 修复 Ask/Review/Run/Results 阶段的迟到响应、模式切换、历史切换和运行中导航竞态，并让非法可编辑字段必须经用户实际修正。
- 扩充离线、abstain、结果、主题、历史、稳定性和几何 E2E 门禁；真实 LLM E2E 仍为显式 opt-in，不以离线 skip 冒充验证。
- 对原始但可归一化的合法请求，科学输出与裁决保持不变；job/trace/provenance 标识或输入哈希可能因执行前统一归一化而变化。
- 将 Results/Recharts 改为按需加载，减少首屏 JavaScript 与字体资源，并用自动 bundle budget 和冷加载 E2E 防回归。
- 新增 Python 3.13 build/runtime/dev hash locks；完整 wheel 现在包含 React 静态资源、Streamlit 入口和已审查默认 gene-set 数据，并在源码目录外验证 CLI/API/同源页面。
- 发布容器改为固定 digest 的四阶段构建，只从 hash-verified wheelhouse 安装同一 wheel；最终镜像以非 root 运行并暴露候选 Git SHA、健康检查和持久化 runs 契约。
- `/api/jobs` 不再向调用方返回原始异常文本：已识别输入失败返回稳定 `invalid_request`，未知执行故障返回稳定 `job_execution_failed` 并只记服务端日志。
- W4B 真 ML workflow 的 per-call 版本现在绑定三组 donor `.json + .pt` 内容身份，并在加载前校验 slot/class；Gate A 同时拒绝格式非法的输入/输出 SHA-256。该身份不是 checked-in 防篡改 pin。
- 新增三 predictor adapter/runtime Gate A 本地 seam 和严格远端验收：本地 3 success 不误伤、缺版本 fail-closed 已通过；当前候选的 donor 代码与 checkpoint 信任门仍明确 remote pending，不以本机两条 skip 冒充通过。现有 CPU-loaded 门也不证明 GPU 推理。
- 建立科学资产分发矩阵与 `.53` 远端科学验证手册；真实引擎仍仅 4 族，单模块/unsupported 百分比无 corpus 不报数，独立冲突检测与 LLM unsupported-claim 仍 unsupported。

## 1.5.0 — local milestone

本地 annotated tag `v1.5.0` 指向 `176019e`。该 tag 从未在 2026-07-18 实时观察到的 GitHub/`.53` 上发布，且历史树仍使用 `0.0.0` package placeholder；不得移动或重建 tag 来隐藏这项历史债务。

## 0.8.0 — published baseline

2026-07-18 实时核验时，GitHub `main`、`.53 main` 和两端最高已发布 tag 均停在 `v0.8.0 → 7fc4aa5`。后续本地里程碑的完整映射见 `docs/status/SYNC-STATE.md`。
