import { lazy, Suspense } from "react";
import Card from "../ui/Card";
import Skeleton from "../ui/Skeleton";
import type { ResultsStageProps } from "./ResultsStage";

// Results pulls the charting stack and is only reachable after a run or from
// history. Keep that work out of the Ask/Review initial bundle while sharing
// one lazy boundary between both entry paths.
const ResultsStage = lazy(() => import("./ResultsStage"));

export default function LazyResultsStage(props: ResultsStageProps) {
  return (
    <Suspense
      fallback={
        <Card title="正在加载结果" ariaLabel="正在加载结果">
          <div role="status" aria-live="polite">
            <Skeleton lines={6} />
          </div>
        </Card>
      }
    >
      <ResultsStage {...props} />
    </Suspense>
  );
}
