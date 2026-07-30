import AppShell from "./components/layout/AppShell";
import "./App.css";

// 产品入口保持轻量；细胞选择、聊天运行与历史报告由 AppShell 编排。
export default function App() {
  return <AppShell />;
}
