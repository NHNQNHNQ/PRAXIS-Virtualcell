import type { ParseResult } from "../api";

// 步骤 2 · 解析核对(占位,8.8 实装)。
// 本 task 仅提供最小可编译占位:标题 + 返回/下一步,保证 7 步状态机能前进/后退。
export default function ParseReviewView({
  onBack,
  onNext,
}: {
  parseResult: ParseResult;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <section className="card">
      <h2>2 · 解析核对(Parse Review)</h2>
      <p className="hero-sub">占位:8.8 实装解析字段/assumptions 只读核对。</p>
      <div className="row end">
        <button type="button" className="btn btn-ghost" onClick={onBack}>
          ← 返回
        </button>
        <button type="button" className="btn" onClick={onNext}>
          下一步 →
        </button>
      </div>
    </section>
  );
}
