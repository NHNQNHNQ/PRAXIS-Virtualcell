import { useState } from "react";
import { parse, type Mode, type ParseResult } from "../api";

// Ask 页:自然语言 textarea + 模式选择 + Parse。只调后端 /api/parse,不在前端解析。
export default function AskView({
  mode,
  onMode,
  onParsed,
}: {
  mode: Mode;
  onMode: (m: Mode) => void;
  onParsed: (r: ParseResult) => void;
}) {
  const [text, setText] = useState("在 human 细胞敲 AHR");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function doParse() {
    setBusy(true);
    setErr(null);
    try {
      onParsed(await parse(text, mode));
    } catch (e: unknown) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <h2>1 · 提问(Ask)</h2>
      <p className="muted">用自然语言描述扰动实验;解析完全在后端确定性 runtime 完成。</p>
      <textarea
        rows={4}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="例:在 human 细胞敲 AHR"
      />
      <div className="row">
        <label>
          模式:
          <select value={mode} onChange={(e) => onMode(e.target.value as Mode)}>
            <option value="offline">offline(默认)</option>
            <option value="llm_assisted">llm_assisted</option>
          </select>
        </label>
        <button type="button" disabled={busy || !text.trim()} onClick={doParse}>
          {busy ? "解析中…" : "Parse"}
        </button>
      </div>
      {err && <pre className="err">{err}</pre>}
    </section>
  );
}
