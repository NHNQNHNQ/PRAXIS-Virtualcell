import { useEffect, useRef, useState } from "react";
import {
  parse,
  type AskDraft,
  type Mode,
  type ParseResult,
} from "../../api";


const EXAMPLES: { label: string; text: string }[] = [
  { label: "Gene perturbation", text: "Knock down AHR in human cells" },
  { label: "Drug response", text: "Treat A549 with vorinostat" },
  { label: "Metabolic stress", text: "Metabolic stress in yeast under glucose limitation" },
];

export default function AskStage({
  initialDraft,
  mode,
  onMode,
  onDraftChanged,
  onParsed,
}: {
  initialDraft: AskDraft | null;
  mode: Mode;
  onMode: (m: Mode) => void;
  onDraftChanged: (draft: AskDraft, composedQuery: string) => void;
  onParsed: (
    result: ParseResult,
    query: string,
    draft: AskDraft,
    parsedMode: Mode,
  ) => void;
}) {
  const [text, setText] = useState(
    () => initialDraft?.text || "Knock down AHR in human cells",
  );
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [advSpecies, setAdvSpecies] = useState(
    () => initialDraft?.species ?? "",
  );
  const [advJson, setAdvJson] = useState(
    () => initialDraft?.structuredDescription ?? "",
  );
  const mountedRef = useRef(true);
  const requestEpochRef = useRef(0);
  const latestModeRef = useRef(mode);
  latestModeRef.current = mode;

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    requestEpochRef.current += 1;
    setBusy(false);
    setErr(null);
  }, [mode]);

  function currentDraft(overrides: Partial<AskDraft> = {}): AskDraft {
    return {
      text,
      species: advSpecies,
      structuredDescription: advJson,
      ...overrides,
    };
  }

  function composedQuery(draft: AskDraft): string {
    const extra: string[] = [];
    if (draft.species.trim()) extra.push(`Species: ${draft.species.trim()}`);
    if (draft.structuredDescription.trim()) {
      extra.push(`Structured description:${draft.structuredDescription.trim()}`);
    }
    return extra.length ? `${draft.text}\n${extra.join("\n")}` : draft.text;
  }

  function updateDraft(next: AskDraft) {
    requestEpochRef.current += 1;
    setBusy(false);
    setErr(null);
    onDraftChanged(next, composedQuery(next));
  }

  async function submit() {
    setBusy(true);
    setErr(null);
    const draft = currentDraft();
    const query = composedQuery(draft);
    const submittedMode = mode;
    const requestEpoch = requestEpochRef.current + 1;
    requestEpochRef.current = requestEpoch;
    const isCurrentRequest = () =>
      mountedRef.current &&
      requestEpochRef.current === requestEpoch &&
      latestModeRef.current === submittedMode;
    try {
      const result = await parse(query, submittedMode);
      if (isCurrentRequest()) onParsed(result, query, draft, submittedMode);
    } catch {
      if (isCurrentRequest()) {
        setErr("Cannot connect to the runtime backend to interpret the task. Check service availability and try again.");
      }
    } finally {
      if (isCurrentRequest()) setBusy(false);
    }
  }

  return (
    <section style={{ maxWidth: "760px" }}>
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
          Describe a perturbation experiment
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
          Describe the biological system and perturbation in natural language. Review the interpreted task before proceeding.
          Only matching, executable models approved by validation produce predictions. Requests without a bound data Pack explicitly abstain.
        </p>
      </div>

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
          Research question
        </label>
        <textarea
          id="ask-input"
          rows={4}
          value={text}
          onChange={(e) => {
            const value = e.target.value;
            const next = currentDraft({ text: value });
            setText(value);
            updateDraft(next);
          }}
          placeholder="Example: Knock down AHR in human cells"
        />

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            gap: "var(--space-2)",
            marginTop: "var(--space-3)",
          }}
        >
          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Examples</span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex.text}
              type="button"
              onClick={() => {
                const next = currentDraft({ text: ex.text });
                setText(ex.text);
                updateDraft(next);
              }}
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
            Execution mode
            <select value={mode} onChange={(e) => onMode(e.target.value as Mode)}>
              <option value="offline">Offline (results bypass language models)</option>
              <option value="llm_assisted">Language-assisted narrative</option>
            </select>
          </label>
          <button
            type="button"
            className="btn"
            disabled={busy || !text.trim()}
            onClick={submit}
          >
            {busy ? "Interpreting…" : "Interpret task →"}
          </button>
        </div>

        {err && (
          <div className="err" role="alert" style={{ marginTop: "var(--space-3)" }}>
            {err}
          </div>
        )}
      </div>

      <details style={{ marginTop: "var(--space-2)" }}>
        <summary
          style={{
            cursor: "pointer",
            fontSize: "13px",
            color: "var(--text-muted)",
            userSelect: "none",
          }}
        >
          Advanced input (optional)
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
            Optionally provide known species context or a structured description. Leave blank to use only the question above.
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
            Species (optional)
            <select
              value={advSpecies}
              onChange={(e) => {
                const value = e.target.value;
                const next = currentDraft({ species: value });
                setAdvSpecies(value);
                updateDraft(next);
              }}
            >
              <option value="">Unspecified (infer from text)</option>
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
            Structured description (optional)
          </label>
          <textarea
            id="adv-json"
            rows={4}
            value={advJson}
            onChange={(e) => {
              const value = e.target.value;
              const next = currentDraft({ structuredDescription: value });
              setAdvJson(value);
              updateDraft(next);
            }}
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
            These details are submitted with the question. You can review and edit the final interpretation on the next page.
          </p>
        </div>
      </details>
    </section>
  );
}
