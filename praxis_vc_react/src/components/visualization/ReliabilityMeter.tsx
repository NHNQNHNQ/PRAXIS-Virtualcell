// 可靠性条(spec §4 ③:reliability score strip)。
// 纯展示、无副作用、不请求数据:score 由 P5 从 learned_reliability.reliability_score 提取后传入。
// 横向 0–1 strip,按阈值分段着色(高=--accent,中=--warn,低=--danger),
// 指针标出当前 score 位置。配色走 token(不硬编码 hex)。
// score == null → 显示「未提供」占位,不崩。
// 文案守 spec §3.5:用平实中文,不外泄内部名词。

export type ReliabilityMeterProps = {
  score: number | null;
  mode?: string;
  reliability?: string;
};

// 阈值:>=0.7 高;>=0.4 中;其余低。
function scoreLabel(score: number): string {
  if (score >= 0.7) return "较高";
  if (score >= 0.4) return "中等";
  return "偏低";
}

export default function ReliabilityMeter({ score, mode, reliability }: ReliabilityMeterProps) {
  // score 缺失 / NaN → 占位,不渲染 strip(NaN 也走「未提供」,不渲染 NaN)。
  if (score == null || Number.isNaN(score)) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
        <div style={{ fontSize: 13, color: "var(--text-muted)" }}>结果可靠性</div>
        <div style={{ fontSize: 14, color: "var(--text-muted)" }}>未提供</div>
      </div>
    );
  }

  // 夹取到 [0,1] 供指针定位;文字仍用原值展示。
  const clamped = Math.max(0, Math.min(1, score));
  const pct = clamped * 100;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "var(--space-3)" }}>
        <span style={{ fontSize: 13, color: "var(--text-muted)" }}>结果可靠性</span>
        <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text)" }}>
          {clamped.toFixed(2)}
          <span style={{ marginLeft: "var(--space-2)", fontWeight: 500, color: "var(--text-muted)" }}>
            {scoreLabel(clamped)}
          </span>
        </span>
      </div>

      {/* strip:三段阈值底色 + 指针。用 SVG 保证配色走 token 且不受字体影响。 */}
      <svg viewBox="0 0 100 8" preserveAspectRatio="none" style={{ width: "100%", height: 8, display: "block" }} role="img" aria-label={`可靠性 ${clamped.toFixed(2)}`}>
        {/* 低 0–40% */}
        <rect x="0" y="0" width="40" height="8" rx="1.5" fill="var(--danger)" opacity="0.28" />
        {/* 中 40–70% */}
        <rect x="40" y="0" width="30" height="8" fill="var(--warn)" opacity="0.28" />
        {/* 高 70–100% */}
        <rect x="70" y="0" width="30" height="8" rx="1.5" fill="var(--accent)" opacity="0.28" />
        {/* 指针 */}
        <rect
          x={Math.max(0, Math.min(99, pct - 0.6))}
          y="-1"
          width="1.2"
          height="10"
          fill={clamped >= 0.7 ? "var(--accent)" : clamped >= 0.4 ? "var(--warn)" : "var(--danger)"}
        />
      </svg>

      {(mode != null && mode !== "") || (reliability != null && reliability !== "") ? (
        <div style={{ display: "flex", gap: "var(--space-4)", fontSize: 12, color: "var(--text-muted)" }}>
          {mode != null && mode !== "" && <span>运行方式:{mode}</span>}
          {reliability != null && reliability !== "" && <span>可靠性判定:{reliability}</span>}
        </div>
      ) : null}
    </div>
  );
}
