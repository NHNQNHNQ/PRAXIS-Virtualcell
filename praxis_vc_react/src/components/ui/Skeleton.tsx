// 加载占位骨架。数据在途时显示,渲染 lines 行灰条,单行高度 height(px)。
// 无文案(纯视觉),不涉 spec §3.5 措辞;走 token 配色,轻微 pulse 动画。
// 纯展示原子,无副作用、无数据请求。

export type SkeletonProps = {
  lines?: number;
  height?: number;
};

// 一次性注入 pulse 关键帧(仅涉本组件,避免改动 components.css)。
const KEYFRAMES = "@keyframes praxis-skeleton-pulse{0%{opacity:.5}50%{opacity:1}100%{opacity:.5}}";

export default function Skeleton({ lines = 3, height = 14 }: SkeletonProps) {
  const count = Math.max(1, Math.floor(lines));
  return (
    <div
      aria-hidden="true"
      style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)", width: "100%" }}
    >
      <style>{KEYFRAMES}</style>
      {Array.from({ length: count }, (_, i) => (
        <div
          key={i}
          style={{
            height,
            // 末行留白,视觉更像文本段落收尾
            width: i === count - 1 ? "60%" : "100%",
            borderRadius: "var(--radius-sm)",
            background: "var(--border)",
            animation: "praxis-skeleton-pulse 1.4s ease-in-out infinite",
          }}
        />
      ))}
    </div>
  );
}
