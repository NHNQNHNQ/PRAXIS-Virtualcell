import type { TraceResult } from "../../api";
import Card from "../ui/Card";
import Skeleton from "../ui/Skeleton";
import { AgentTraceTimeline } from "../visualization";

// Stage 5 · Trace tab(spec §2 Trace / §4 ⑤ / §3.5)——把本次运行的逐步轨迹,用 P4 已建的
// 手写 SVG 时间线(AgentTraceTimeline)呈现:默认精简到 6–8 个关键节点(首尾 + 阶段变化点),
// 可展开完整步骤,点击节点看该步字段。数据来自 /trace(getTrace → TraceResult.trace 步数组)。
//
// 职责边界:本组件只做「加载/装配」——把 TraceResult 里的步数组取出、类型对齐后交给
// AgentTraceTimeline;步数摘要、精简/展开、空态都由 AgentTraceTimeline 内部承载,故此处
// 不重复渲染「共 N 步」摘要,只在其上方加一句中文引导(§3.5:trace 属审计区,sender/receiver/
// message_type 等精确术语沿用 AgentTraceTimeline 呈现,但整体克制)。
//
// 降级:
//   · trace 为 null(未到 / 加载中)→ Skeleton,不崩;
//   · trace.trace 为空 / undefined → 传空数组给 AgentTraceTimeline,由其内置 EmptyState 兜底。
//
// 铁律(Phase9 红线):前端只读展示,不改任何请求;不引入依赖(复用 P4 组件);配色走 token。

export type TraceTabProps = {
  trace: TraceResult | null;
};

export default function TraceTab({ trace }: TraceTabProps) {
  // 加载中 / 未到达:骨架占位。
  if (trace == null) {
    return (
      <Card title="运行轨迹">
        <Skeleton lines={6} />
      </Card>
    );
  }

  // 已到达:取出步数组(可能为空 / undefined),类型对齐 AgentTraceTimeline 的 { trace: TraceStep[] }。
  // 空数组由 AgentTraceTimeline 内置空态兜底,不在此处另判。
  const steps = trace.trace ?? [];

  return (
    <Card title="运行轨迹">
      <p
        style={{
          margin: "0 0 var(--space-3)",
          fontSize: 13,
          color: "var(--text-muted)",
        }}
      >
        本次运行各步的收发方与消息类型,供审计查阅;默认精简展示,可展开完整步骤。
      </p>
      <AgentTraceTimeline trace={steps} />
    </Card>
  );
}
