import { useEffect, useState } from "react";
import { API_BASE, health, type Health } from "./api";
import "./App.css";

// R4.2:最小首页 —— 拉 /api/health 验证前后端连通。完整页面在 R4.3 构建。
export default function App() {
  const [h, setH] = useState<Health | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    health()
      .then(setH)
      .catch((e: unknown) => setErr(String(e)));
  }, []);

  return (
    <div className="app">
      <header className="banner">
        <strong>PRAXIS-VirtualCell</strong> —— 本地只读展示前端
        <span className="notice">LLM 未参与预测/治理决策</span>
      </header>

      <main>
        <h1>后端连通性(/api/health)</h1>
        <p className="muted">API base:{API_BASE}(默认 offline;前端不存/不显示 API key)</p>
        {err && <pre className="err">{err}</pre>}
        {h ? (
          <ul>
            <li>status:{h.status}</li>
            <li>mode:{h.mode}</li>
            <li>llm_enabled:{String(h.llm_enabled)}</li>
            <li>runtime_version:{h.runtime_version}</li>
          </ul>
        ) : (
          !err && <p>加载中……(请确认后端已启动:praxis-vc serve)</p>
        )}
      </main>
    </div>
  );
}
