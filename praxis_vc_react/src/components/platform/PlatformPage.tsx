import {
  type FormEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  createJob,
  getDataCatalog,
  getPackCatalog,
  parse,
  type CellPreset,
  type DataCatalog,
  type Health,
  type Options,
  type PackCatalog,
  type ParseResult,
} from "../../api";
import LazyResultsStage from "../stages/LazyResultsStage";
import type { PlatformView } from "../layout/JobSidebar";

type ChatTurn = {
  id: number;
  query: string;
  status:
    | "pending"
    | "interpretation"
    | "clarification"
    | "report"
    | "error";
  message?: string;
  jobId?: string;
  request?: Record<string, unknown>;
  parser?: string;
  llmUsed?: boolean;
  fallbackUsed?: boolean;
};

type PlatformPageProps = {
  page: PlatformView;
  chatEpoch: number;
  selectedCell: CellPreset | null;
  options: Options | null;
  optionsError: string | null;
  openedJobId: string | null;
  health: Health | null;
  onSelectCell: (cell: CellPreset) => void;
  onBrowseCells: () => void;
  onNewChat: () => void;
  onJobCreated: (jobId: string) => void;
};

const COMMON_CELL_IDS = new Set([
  "human_k562",
  "human_pbmc",
  "mouse_tcell",
  "ecoli_iml1515",
]);

function composeCellQuery(query: string, cell: CellPreset): string {
  return `${query}\n结构化描述:${JSON.stringify({
    species: cell.species,
    cell_type: cell.cell_type,
  })}`;
}

function unresolvedParseMessage(parsed: ParseResult): string | null {
  if (
    parsed.schema_valid &&
    !parsed.clarification_required &&
    parsed.missing_fields.length === 0 &&
    parsed.errors.length === 0
  ) {
    return null;
  }

  const details = [
    parsed.missing_fields.length
      ? `缺少：${parsed.missing_fields.join("、")}`
      : "",
    parsed.errors.length ? `错误：${parsed.errors.join("、")}` : "",
  ].filter(Boolean);
  return `还需要更明确的实验描述。${details.join("；") || "请说明扰动类型和对象。"} 未创建模拟任务。`;
}

function requestValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map(String).join("、") || "—";
  }
  if (typeof value === "string" && value.trim()) return value;
  return value == null ? "—" : String(value);
}

function parseLabel(turn: ChatTurn): string | null {
  if (turn.llmUsed) return "Language parsing: LLM-assisted";
  if (turn.fallbackUsed) {
    return turn.status === "interpretation"
      ? "Language parsing: deterministic fallback · awaiting confirmation"
      : "Language parsing: deterministic fallback · confirmed";
  }
  return turn.parser ? `Language parsing: ${turn.parser}` : null;
}

function CellCard({
  cell,
  resourceSummary,
  onSelect,
}: {
  cell: CellPreset;
  resourceSummary?: string;
  onSelect: (cell: CellPreset) => void;
}) {
  return (
    <article className="cell-choice-card">
      <div className="cell-choice-topline">
        <span>{cell.species}</span>
        <small>Context preset</small>
      </div>
      <h2>{cell.cell_type}</h2>
      <p>{cell.label}</p>
      {resourceSummary && <small className="cell-resource-summary">{resourceSummary}</small>}
      <button type="button" onClick={() => onSelect(cell)}>
        Select cell
        <span aria-hidden="true">→</span>
      </button>
    </article>
  );
}

export default function PlatformPage({
  page,
  chatEpoch,
  selectedCell,
  options,
  optionsError,
  openedJobId,
  health,
  onSelectCell,
  onBrowseCells,
  onNewChat,
  onJobCreated,
}: PlatformPageProps) {
  const [query, setQuery] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [busy, setBusy] = useState(false);
  const [catalog, setCatalog] = useState<DataCatalog | null>(null);
  const [packCatalog, setPackCatalog] = useState<PackCatalog | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [speciesFilter, setSpeciesFilter] = useState("all");
  const requestEpochRef = useRef(0);
  const turnIdRef = useRef(0);
  const inFlightRef = useRef(false);
  const latestTurnRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    requestEpochRef.current += 1;
    inFlightRef.current = false;
    setQuery("");
    setTurns([]);
    setBusy(false);
  }, [chatEpoch]);

  useEffect(() => {
    requestEpochRef.current += 1;
    inFlightRef.current = false;
    setBusy(false);
  }, [page]);

  useEffect(() => {
    if (page !== "data-center") return;
    let current = true;
    setCatalog(null);
    setPackCatalog(null);
    setCatalogError(null);
    Promise.all([getDataCatalog(), getPackCatalog()])
      .then(([nextCatalog, nextPacks]) => {
        if (!current) return;
        setCatalog(nextCatalog);
        setPackCatalog(nextPacks);
      })
      .catch((reason: unknown) => {
        if (current) setCatalogError(String(reason));
      });
    return () => {
      current = false;
    };
  }, [page]);

  useEffect(() => {
    if (turns.length) {
      latestTurnRef.current?.scrollIntoView({
        block: "start",
      });
    }
  }, [turns]);

  const allCells = useMemo(() => {
    const unique = new Map<string, CellPreset>();
    for (const cell of options?.cell_presets ?? []) {
      const key = `${cell.species}\u0000${cell.cell_type}`;
      if (!unique.has(key)) unique.set(key, cell);
    }
    return [...unique.values()];
  }, [options]);
  const commonCells = useMemo(() => {
    const preferred = allCells.filter((cell) => COMMON_CELL_IDS.has(cell.id));
    return preferred.length ? preferred : allCells.slice(0, 4);
  }, [allCells]);
  const visibleCells = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return allCells.filter((cell) => {
      const matchesSpecies =
        speciesFilter === "all" || cell.species === speciesFilter;
      const matchesSearch =
        !needle ||
        `${cell.label} ${cell.cell_type} ${cell.species}`
          .toLowerCase()
          .includes(needle);
      return matchesSpecies && matchesSearch;
    });
  }, [allCells, search, speciesFilter]);

  function updateTurn(id: number, patch: Partial<ChatTurn>) {
    setTurns((current) =>
      current.map((turn) => (turn.id === id ? { ...turn, ...patch } : turn)),
    );
  }

  async function confirmInterpretation(turn: ChatTurn) {
    if (!turn.request || busy || inFlightRef.current) return;

    const requestEpoch = requestEpochRef.current + 1;
    requestEpochRef.current = requestEpoch;
    inFlightRef.current = true;
    const isCurrent = () => requestEpochRef.current === requestEpoch;

    setBusy(true);
    updateTurn(turn.id, { status: "pending" });

    try {
      const job = await createJob(turn.request, "llm_assisted", true);
      onJobCreated(job.job_id);
      if (!isCurrent()) return;
      updateTurn(turn.id, { status: "report", jobId: job.job_id });
    } catch (reason: unknown) {
      if (!isCurrent()) return;
      updateTurn(turn.id, {
        status: "error",
        message:
          reason instanceof Error
            ? reason.message
            : "运行服务暂时不可用，请稍后重试。",
      });
    } finally {
      if (isCurrent()) {
        inFlightRef.current = false;
        setBusy(false);
      }
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = query.trim();
    if (!selectedCell || !text || busy || inFlightRef.current) return;

    const requestEpoch = requestEpochRef.current + 1;
    requestEpochRef.current = requestEpoch;
    inFlightRef.current = true;
    const turnId = turnIdRef.current + 1;
    turnIdRef.current = turnId;
    const cell = selectedCell;
    const isCurrent = () => requestEpochRef.current === requestEpoch;

    setQuery("");
    setBusy(true);
    setTurns((current) => [
      ...current,
      { id: turnId, query: text, status: "pending" },
    ]);

    try {
      const parsed = await parse(composeCellQuery(text, cell), "llm_assisted");
      if (!isCurrent()) return;
      const parseMetadata = {
        parser: parsed.parser,
        llmUsed: parsed.llm_used,
        fallbackUsed: parsed.fallback_used,
      };

      const clarification = unresolvedParseMessage(parsed);
      if (clarification) {
        updateTurn(turnId, {
          status: "clarification",
          message: clarification,
          ...parseMetadata,
        });
        return;
      }

      const candidate = parsed.candidate_request;
      if (
        candidate.species !== cell.species ||
        candidate.cell_type !== cell.cell_type
      ) {
        updateTurn(turnId, {
          status: "error",
          message: "所选细胞上下文未通过请求验证，因此没有创建模拟任务。",
          ...parseMetadata,
        });
        return;
      }

      if (parsed.fallback_used && !parsed.llm_used) {
        updateTurn(turnId, {
          status: "interpretation",
          request: candidate,
          ...parseMetadata,
        });
        return;
      }

      const job = await createJob(candidate, "llm_assisted", true);
      onJobCreated(job.job_id);
      if (!isCurrent()) return;
      updateTurn(turnId, {
        status: "report",
        jobId: job.job_id,
        request: candidate,
        ...parseMetadata,
      });
    } catch (reason: unknown) {
      if (!isCurrent()) return;
      updateTurn(turnId, {
        status: "error",
        message:
          reason instanceof Error
            ? reason.message
            : "运行服务暂时不可用，请稍后重试。",
      });
    } finally {
      if (isCurrent()) {
        inFlightRef.current = false;
        setBusy(false);
      }
    }
  }

  if (page === "data-center") {
    const species = ["all", ...(options?.species ?? [])];
    return (
      <section className="cell-data-center" aria-labelledby="data-center-title">
        <header>
          <span>PRAXIS DATA CENTER</span>
          <h1 id="data-center-title">Choose a cell</h1>
          <p>
            浏览后端声明的 biological context presets。选择只会固定物种和细胞背景；
            这些资源不与本次选择绑定，实际执行身份以报告为准。
          </p>
        </header>

        <div className="cell-search-row">
          <label>
            <span>Search cells</span>
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="K562, fibroblast, yeast…"
            />
          </label>
          <div className="cell-species-filter" aria-label="Species filter">
            {species.map((item) => (
              <button
                key={item}
                type="button"
                className={speciesFilter === item ? "active" : ""}
                onClick={() => setSpeciesFilter(item)}
                aria-pressed={speciesFilter === item}
              >
                {item === "all" ? "All" : item}
              </button>
            ))}
          </div>
        </div>

        {optionsError && (
          <p className="chat-error" role="alert">
            细胞目录不可用：{optionsError}
          </p>
        )}
        {options == null && !optionsError && (
          <p className="chat-loading">Loading cell catalog…</p>
        )}
        {catalogError && (
          <p className="cell-resource-note">
            同物种数据与 Pack 计数当前不可用；细胞 preset 仍以后端 options 为准。
          </p>
        )}

        <div className="cell-choice-grid">
          {visibleCells.map((cell) => {
            const dataCount =
              catalog?.datasets.filter(
                (dataset) => dataset.species.runtime_id === cell.species,
              ).length ?? 0;
            const taxonId = catalog?.species.find(
              (item) => item.id === cell.species,
            )?.taxon_id;
            const packCount =
              packCatalog?.packs.filter(
                (pack) => pack.taxon?.ontology_id === taxonId,
              ).length ?? 0;
            const summary =
              catalog && packCatalog
                ? `${dataCount} same-species dataset${dataCount === 1 ? "" : "s"} · ${packCount} Pack record${packCount === 1 ? "" : "s"} · not bound`
                : undefined;
            return (
              <CellCard
                key={cell.id}
                cell={cell}
                resourceSummary={summary}
                onSelect={onSelectCell}
              />
            );
          })}
        </div>

        {options && visibleCells.length === 0 && (
          <p className="chat-empty">No matching cell presets.</p>
        )}
        <p className="cell-data-boundary">
          这些是可审阅的上下文 preset，不是已注册 Virtual Cell。Same-species
          Dataset 或 Pack 计数不表示绑定、兼容、可执行或科学验证。
        </p>
      </section>
    );
  }

  if (openedJobId) {
    return (
      <section className="chat-report-view" aria-label="Saved report">
        <header className="chat-report-header">
          <div>
            <span>SAVED REPORT</span>
            <h1>Run report</h1>
            <p>结果、abstention 与 execution identity 均来自后端保存记录。</p>
          </div>
          <button type="button" onClick={onNewChat}>
            New chat
          </button>
        </header>
        <LazyResultsStage jobId={openedJobId} onReset={onNewChat} />
      </section>
    );
  }

  if (!selectedCell) {
    return (
      <section className="cell-first-home" aria-labelledby="cell-first-title">
        <div className="cell-first-hero">
          <span>PRAXIS · VIRTUAL CELL</span>
          <h1 id="cell-first-title">Choose a cell to begin.</h1>
          <p>
            先固定生物背景，再用自然语言描述实验。后端会根据请求自动路由现有执行路径并
            直接返回报告；报告会明确显示预测或 abstain。
          </p>
        </div>

        {optionsError && (
          <p className="chat-error" role="alert">
            细胞目录不可用：{optionsError}
          </p>
        )}
        {options == null && !optionsError && (
          <p className="chat-loading">Loading common cells…</p>
        )}
        <div className="cell-choice-grid common">
          {commonCells.map((cell) => (
            <CellCard key={cell.id} cell={cell} onSelect={onSelectCell} />
          ))}
        </div>
        <button
          type="button"
          className="browse-all-cells"
          onClick={onBrowseCells}
          disabled={options == null}
        >
          Browse all cells in Data Center
          <span aria-hidden="true">→</span>
        </button>
        <p className="cell-data-boundary">
          Cell choices come from the backend context catalog. They do not create
          a persistent Virtual Cell or pre-bind a model.
        </p>
      </section>
    );
  }

  return (
    <section className="cell-conversation" aria-labelledby="conversation-title">
      <header className="conversation-header">
        <div>
          <span>SELECTED CELL</span>
          <h1 id="conversation-title">{selectedCell.cell_type}</h1>
          <p>
            {selectedCell.label} · {selectedCell.species}
          </p>
        </div>
        <button type="button" onClick={onBrowseCells}>
          Change cell
        </button>
      </header>

      <div className="conversation-stream">
        <div className="assistant-message">
          <span className="assistant-avatar">P</span>
          <div>
            <strong>What would you like to investigate?</strong>
            <p>
              描述扰动、处理或条件即可。我会将任务提交给现有运行后端并直接返回报告；
              实际模型、执行身份与 abstain 以报告为准。
            </p>
          </div>
        </div>

        {turns.map((turn, index) => (
          <div
            className="conversation-turn"
            key={turn.id}
            ref={index === turns.length - 1 ? latestTurnRef : undefined}
          >
            <div className="user-message">
              <p>{turn.query}</p>
            </div>
            {turn.status === "pending" && (
              <div className="assistant-message running" role="status">
                <span className="assistant-avatar">P</span>
                <div>
                  <strong>Preparing the report…</strong>
                  <p>
                    正在解析任务并提交现有运行后端；所选 cell preset 不绑定
                    Dataset、Pack 或模型。
                  </p>
                </div>
              </div>
            )}
            {turn.status === "interpretation" && turn.request && (
              <div className="assistant-message interpretation">
                <span className="assistant-avatar">P</span>
                <div>
                  <strong>Please confirm this interpretation.</strong>
                  <p>
                    当前服务未连接语言模型。为避免确定性后备误解实验语义，请确认以下结构化请求。
                  </p>
                  <dl className="interpretation-grid">
                    <div>
                      <dt>Species</dt>
                      <dd>{requestValue(turn.request.species)}</dd>
                    </div>
                    <div>
                      <dt>Cell</dt>
                      <dd>{requestValue(turn.request.cell_type)}</dd>
                    </div>
                    <div>
                      <dt>Perturbation</dt>
                      <dd>{requestValue(turn.request.perturbation_type)}</dd>
                    </div>
                    <div>
                      <dt>Targets</dt>
                      <dd>{requestValue(turn.request.perturbation_targets)}</dd>
                    </div>
                    <div>
                      <dt>Task</dt>
                      <dd>{requestValue(turn.request.task_type)}</dd>
                    </div>
                  </dl>
                  {parseLabel(turn) && (
                    <small className="assistant-parse-meta">
                      {parseLabel(turn)}
                    </small>
                  )}
                  <button
                    type="button"
                    className="confirm-interpretation"
                    disabled={busy}
                    onClick={() => void confirmInterpretation(turn)}
                  >
                    Confirm interpretation and generate report
                  </button>
                </div>
              </div>
            )}
            {(turn.status === "clarification" || turn.status === "error") && (
              <div
                className={
                  turn.status === "error"
                    ? "assistant-message error"
                    : "assistant-message clarification"
                }
                role="alert"
              >
                <span className="assistant-avatar">P</span>
                <div>
                  <strong>
                    {turn.status === "error"
                      ? "The report could not be created."
                      : "I need one more detail."}
                  </strong>
                  <p>{turn.message}</p>
                  {parseLabel(turn) && (
                    <small className="assistant-parse-meta">
                      {parseLabel(turn)}
                    </small>
                  )}
                </div>
              </div>
            )}
            {turn.status === "report" && turn.jobId && (
              <div className="assistant-report">
                <p className="assistant-report-status" role="status">
                  Report generated. Prediction or abstention is shown below.
                  {parseLabel(turn) ? ` ${parseLabel(turn)}.` : ""}
                </p>
                <p className="assistant-report-boundary">
                  所选 cell preset 只提供请求上下文，并未绑定 Dataset、Pack
                  或模型。报告不代表该细胞已具备经过科学验证的预测器。
                </p>
                <LazyResultsStage jobId={turn.jobId} onReset={onNewChat} />
              </div>
            )}
          </div>
        ))}
      </div>

      <form className="chat-composer" onSubmit={submit}>
        <label htmlFor="chat-query">Message PRAXIS</label>
        <textarea
          id="chat-query"
          rows={3}
          value={query}
          disabled={busy}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing
            ) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
          placeholder={`Ask about ${selectedCell.cell_type}…`}
        />
        <button
          type="submit"
          aria-label="Send message"
          disabled={busy || !query.trim()}
        >
          {busy ? "…" : "↑"}
        </button>
        <small>
          语言辅助只解析与解释文字；数据、模拟、数值与最终裁决由确定性后端完成。
          {health?.llm_enabled === false
            ? " 当前服务未连接语言模型，确定性解析需要你确认后才会运行。"
            : ""}
        </small>
      </form>
    </section>
  );
}
