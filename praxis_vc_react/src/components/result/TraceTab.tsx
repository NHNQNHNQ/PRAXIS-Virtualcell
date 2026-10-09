import type { TraceResult } from "../../api";
import Card from "../ui/Card";
import Skeleton from "../ui/Skeleton";
import { AgentTraceTimeline } from "../visualization";
export type TraceTabProps = {
  trace: TraceResult | null;
};

export default function TraceTab({ trace }: TraceTabProps) {
  if (trace == null) {
    return (
      <Card title="Execution trace">
        <Skeleton lines={6} />
      </Card>
    );
  }

  const steps = trace.trace ?? [];

  return (
    <Card title="Execution trace">
      <p
        style={{
          margin: "0 0 var(--space-3)",
          fontSize: 13,
          color: "var(--text-muted)",
        }}
      >
        Audit senders, recipients, and message types for each execution step. The default view is condensed; expand it to see every step.
      </p>
      <AgentTraceTimeline trace={steps} />
    </Card>
  );
}
