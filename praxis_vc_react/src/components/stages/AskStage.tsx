import { useState } from "react";
import { parse, type Mode, type ParseResult } from "../../api";

// Stage 1 · Ask(spec §2 Stage1)—— 科研感 hero 输入,不是聊天窗:
// 无衬线大标题 + 简短说明 + 大输入 textarea + 模式选择 + 示例入口 + Advanced 折叠区。
// 解析全在后端(POST /api/parse,复用 api.ts 的 parse());前端绝不自己解析自然语言。
// parse 成功回传 (result, query);失败显错误态、不崩溃。

// 3 个示例:覆盖 spec 要的三类(gene perturbation / drug response / metabolic stress),
// 点击填入 textarea。文案用科学家的自然说法,不带工程黑话。
const EXAMPLES: { label: string; text: string }[] = [
  { label: "基因扰动", text: "在 human 细胞敲 AHR" },
  { label: "药物响应", text: "vorinostat 处理 A549" },
  { label: "代谢应激", text: "葡萄糖限制下的 yeast 代谢应激" },
];

export default function AskStage({
  mode,
  onMode,
  onParsed,
}: {
  mode: Mode;
  onMode: (m: Mode) => void;
  onParsed: (result: ParseResult, query: string) => void;
}) {
  const [text, setText] = useState("在 human 细胞敲 AHR");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  // Advanced 折叠区:可选物种(占位)与直接粘贴结构化描述——仅前端组装,不新增端点。
  const [advSpecies, setAdvSpecies] = useState("");
  const [advJson, setAdvJson] = useState("");

  // 把可选的高级输入(物种/结构化描述)在前端拼进问题文本一起提交——
  // 不新增端点,仍走同一个 parse(text, mode);后端负责真正的解读。
  function composedQuery(): string {
    const extra: string[] = [];
    if (advSpecies.trim()) extra.push(`物种:${advSpecies.trim()}`);
    if (advJson.trim()) extra.push(`结构化描述:${advJson.trim()}`);
    return extra.length ? `${text}\n${extra.join("\n")}` : text;
  }

  async function submit() {
    setBusy(true);
    setErr(null);
    const query = composedQuery();
    try {
      const result = await parse(query, mode);
      onParsed(result, query);
    } catch {
      // 面向用户的错误文案(spec §3.5):不暴露内部实现名词,给可操作的提示。
      setErr("暂时无法连接到运行后端,任务解读未能完成。请确认服务可达后重试。");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section style={{ maxWidth: "760px" }}>
      {/* 科研感 hero:轻字重大标题 + 一句平实说明(非「我来帮你」的聊天窗观感)。 */}
      <div style={{ marginBottom: "var(--space-6)" }}>
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "34px",
            fontWeight: 500,
            lineHeight: 1.15,
            letterSpacing: "-0.01em",
            color: "var(--text)",
            margin: 0,
          }}
        >
          描述一次扰动实验
        </h1>
        <p
          style={{
            marginTop: "var(--space-3)",
            fontSize: "15px",
            lineHeight: 1.55,
            color: "var(--text-muted)",
            maxWidth: "60ch",
          }}
        >
          用自然语言写下要考察的生物体系与扰动,系统会先给出对任务的解读供你核对,
          再由确定性模型给出预测。结果可追溯到所依据的模块与证据。
        </p>
      </div>

      {/* 大输入区:textarea + 模式 + Parse 按钮。 */}
      <div className="card">
        <label
          htmlFor="ask-input"
          style={{
            display: "block",
            fontSize: "13px",
            fontWeight: 500,
            color: "var(--text-muted)",
            marginBottom: "var(--space-2)",
          }}
        >
          研究问题
        </label>
        <textarea
          id="ask-input"
          rows={4}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="例:在 human 细胞敲 AHR"
        />

        {/* 示例入口:一行 chip,点击填入 textarea。 */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            gap: "var(--space-2)",
            marginTop: "var(--space-3)",
          }}
        >
          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>示例</span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex.text}
              type="button"
              onClick={() => setText(ex.text)}
              style={{
                fontFamily: "var(--font-sans)",
                fontSize: "13px",
                padding: "5px 12px",
                borderRadius: "var(--radius-pill)",
                border: "1px solid var(--border)",
                background: "transparent",
                color: "var(--text)",
                cursor: "pointer",
              }}
            >
              {ex.label}
              <span style={{ color: "var(--text-muted)", marginLeft: "6px" }}>
                {ex.text}
              </span>
            </button>
          ))}
        </div>

        {/* 模式选择 + 提交。offline 全程不经语言模型;llm_assisted 仅辅助改写文字表述。 */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
            gap: "var(--space-4)",
            flexWrap: "wrap",
            marginTop: "var(--space-4)",
          }}
        >
          <label
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-1)",
              fontSize: "13px",
              color: "var(--text-muted)",
              maxWidth: "260px",
            }}
          >
            运行方式
            <select value={mode} onChange={(e) => onMode(e.target.value as Mode)}>
              <option value="offline">离线(结果不经语言模型)</option>
              <option value="llm_assisted">辅以语言模型改写文字</option>
            </select>
          </label>
          <button
            type="button"
            className="btn"
            disabled={busy || !text.trim()}
            onClick={submit}
          >
            {busy ? "解读中…" : "解读任务 →"}
          </button>
        </div>

        {err && (
          <div className="err" role="alert" style={{ marginTop: "var(--space-3)" }}>
            {err}
          </div>
        )}
      </div>

      {/* Advanced input:可选,折叠。选物种(占位)/ 直接粘贴结构化描述。仅前端组装,不新增端点。 */}
      <details style={{ marginTop: "var(--space-2)" }}>
        <summary
          style={{
            cursor: "pointer",
            fontSize: "13px",
            color: "var(--text-muted)",
            userSelect: "none",
          }}
        >
          高级输入(可选)
        </summary>
        <div className="card" style={{ marginTop: "var(--space-3)" }}>
          <p
            style={{
              fontSize: "13px",
              color: "var(--text-muted)",
              marginBottom: "var(--space-3)",
              lineHeight: 1.5,
            }}
          >
            若已知物种背景,或想直接提供结构化描述,可在此补充。留空则完全由上面的文字决定。
          </p>

          <label
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-1)",
              fontSize: "13px",
              color: "var(--text-muted)",
              marginBottom: "var(--space-3)",
            }}
          >
            物种(可留空)
            <select
              value={advSpecies}
              onChange={(e) => setAdvSpecies(e.target.value)}
            >
              <option value="">不指定(由文字推断)</option>
              <option value="human">human</option>
              <option value="mouse">mouse</option>
              <option value="yeast">yeast</option>
            </select>
          </label>

          <label
            htmlFor="adv-json"
            style={{
              display: "block",
              fontSize: "13px",
              color: "var(--text-muted)",
              marginBottom: "var(--space-1)",
            }}
          >
            结构化描述(可留空)
          </label>
          <textarea
            id="adv-json"
            rows={4}
            value={advJson}
            onChange={(e) => setAdvJson(e.target.value)}
            placeholder='{ "species": "human", "perturbation_targets": ["AHR"] }'
            style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}
          />
          <p
            style={{
              fontSize: "12px",
              color: "var(--text-muted)",
              marginTop: "var(--space-2)",
            }}
          >
            这些补充会与上面的问题一起提交,最终解读仍在核对页展示,可再修改。
          </p>
        </div>
      </details>
    </section>
  );
}
