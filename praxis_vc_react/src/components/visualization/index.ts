// 可视化组件 barrel(spec §4 / Task 9.17)。统一导出 P4 的 5 个只读展示组件,
// 供 P5 各 result tab 复用。全部纯展示、无副作用、不请求数据;空/异常输入统一降级
// 到 ui/EmptyState,不崩(null / {} / [] / offline mock 四输入自检通过)。
// 导出风格对齐 ui/index.ts:default export 组件用 `export { default as X }`,类型单列。
// 用 .ts(非 .tsx)避 oxlint 告警。

export { default as PredictionBarChart } from "./PredictionBarChart";
export type { PredictionBarChartProps } from "./PredictionBarChart";

export { default as ReliabilityMeter } from "./ReliabilityMeter";
export type { ReliabilityMeterProps } from "./ReliabilityMeter";

export { default as EvidenceDistributionChart } from "./EvidenceDistributionChart";
export type { EvidenceDistributionChartProps } from "./EvidenceDistributionChart";

export { default as ModuleRoutingGraph } from "./ModuleRoutingGraph";
export type { ModuleRoutingGraphProps } from "./ModuleRoutingGraph";

export { default as AgentTraceTimeline } from "./AgentTraceTimeline";
export type { AgentTraceTimelineProps } from "./AgentTraceTimeline";
