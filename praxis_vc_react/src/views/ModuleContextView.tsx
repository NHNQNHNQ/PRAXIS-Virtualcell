// 步骤 4 · 模块预期(占位,8.8 实装)。
// 本 task 仅提供最小可编译占位:标题 + 返回/下一步。
// request 为 confirm 步交出的组装 request(此占位不消费其字段,8.8 用它匹配预期模块)。
export default function ModuleContextView({
  onBack,
  onNext,
}: {
  request: Record<string, unknown>;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <section className="card">
      <h2>4 · 模块预期(Module Context)</h2>
      <p className="hero-sub">
        占位:8.8 实装 8 模块预期网格(静态预期,实际路由在运行后展示)。
      </p>
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
