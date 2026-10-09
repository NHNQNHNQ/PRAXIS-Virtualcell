
export type SkeletonProps = {
  lines?: number;
  height?: number;
};

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
