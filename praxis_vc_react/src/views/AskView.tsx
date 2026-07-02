import { useState } from "react";
import { parse, type Mode, type ParseResult } from "../api";

// Ask 页(ChatGPT 空状态):居中标题 + 大输入框 + 模式选择 + Parse。
// 只调后端 /api/parse,不在前端解析。
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
    <section>
      <div className="hero">
        <h1>预测一次扰动实验</h1>
        <p className="hero-sub">用自然语言描述;解析与预测全在后端确定性 runtime 完成。</p>
      </div>

      <div className="card">
        <div className="ask-input">
          <textarea
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="例:在 human 细胞敲 AHR"
          />
        </div>
        <div className="row between">
          <label>
            模式
            <select value={mode} onChange={(e) => onMode(e.target.value as Mode)}>
              <option value="offline">offline(默认)</option>
              <option value="llm_assisted">llm_assisted</option>
            </select>
          </label>
          <button type="button" className="btn" disabled={busy || !text.trim()} onClick={doParse}>
            {busy ? "解析中…" : "Parse →"}
          </button>
        </div>
        {err && <pre className="err">{err}</pre>}
      </div>
    </section>
  );
}
