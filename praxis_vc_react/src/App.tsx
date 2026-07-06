import AppShell from "./components/layout/AppShell";
import "./App.css";

// Phase 9 P2:App 瘦身为渲染状态机宿主 AppShell(spec §6)。
// 7 步扁平流程 + 6 散 useState 已迁入 AppShell,集中为 Stage/JobState 状态机。
export default function App() {
  return <AppShell />;
}
