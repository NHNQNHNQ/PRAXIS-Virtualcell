# Rules

当前 `memory/rules/` 按主题分成 7 组，目标是让智能体扫一眼文件名就知道先读哪一组。

## 推荐读取顺序

1. 先看文件名，按任务落到对应分组
2. 不确定时，优先读：
   - `01` 和 `02` 处理构建起点
   - `03` 处理体系验收和膜体系 fallback
   - `04` 和 `05` 处理运行命令与输出完整性
   - `06` 处理增强采样和兼容性
   - `07` 处理分析前置处理与 PBC 完整性

## 分组说明

- `01-build-default-routes.md`
  - 默认构建路线
- `02-build-forcefield-and-preflight-checks.md`
  - 力场目录和构建前检查
- `03-build-acceptance-and-membrane-fallbacks.md`
  - 体系验收和膜体系 fallback
- `04-run-launch-and-resource-strategy.md`
  - 启动方式和资源策略
- `05-run-output-and-process-integrity.md`
  - 输出完整性和进程完整性
- `06-sampling-cv-and-version-compatibility.md`
  - 增强采样、反应坐标和版本兼容
- `07-analysis-pbc-and-measurement-integrity.md`
  - 分析前置处理与 PBC 完整性
- `08-topology-coordinate-consistency.md`
  - 非标准聚合体系拓扑-坐标一致性：图同构验证、inconsistent shifts 根因诊断

## 使用原则

- `rules` 负责短规则和默认判断，不负责案例背景
- 需要知道“为什么会这样”时，回到 `memory/cases/`
- 需要知道“具体怎么执行”时，再去读 `skills/`
