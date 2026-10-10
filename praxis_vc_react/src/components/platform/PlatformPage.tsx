import {
  type FormEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  createJob,
  executeResearchTask,
  getDataCatalog,
  getPackCatalog,
  getResearchTaskCompatibility,
  getResearchTasks,
  parse,
  type CellPreset,
  type DataCatalog,
  type Health,
  type Options,
  type PackCatalog,
  type ParseResult,
  type ResearchTask,
  type ResearchTaskCompatibility,
} from "../../api";
import DataLibrary from "../data/DataLibrary";
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

type PromptExample = {
  text: string;
  perturbationType: string;
  targets: string[];
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

function nestedText(value: unknown, ...keys: string[]): string | null {
  let current = value;
  for (const key of keys) {
    if (typeof current !== "object" || current === null || Array.isArray(current)) {
      return null;
    }
    current = (current as Record<string, unknown>)[key];
  }
  return typeof current === "string" && current ? current : null;
}

function researchTaskLabel(task: ResearchTask, action: "Preview" | "Run") {
  const condition = nestedText(task.request, "constraints", "condition_id");
  const timepoint = nestedText(task.request, "perturbation", "timepoint");
  return `${action} registered ${condition ?? task.task_id}${timepoint ? ` · ${timepoint}` : ""} · ${task.execution_scope.replace("_", "-")}`;
}

function researchTaskMatchesCell(task: ResearchTask, cell: CellPreset) {
  return (
    nestedText(task.request, "species", "common_name") === cell.species &&
    nestedText(task.request, "cell_context", "cell_type_name") === cell.cell_type
  );
}

function composeCellQuery(
  query: string,
  cell: CellPreset,
  example?: PromptExample,
): string {
  return `${query}\nStructured description:${JSON.stringify({
    species: cell.species,
    cell_type: cell.cell_type,
    ...(example
      ? {
          perturbation_type: example.perturbationType,
          perturbation_targets: example.targets,
        }
      : {}),
  })}`;
}

function cellPromptExamples(
  presets: CellPreset[],
  cell: CellPreset,
): PromptExample[] {
  const examples: PromptExample[] = [];
  const add = (
    text: string,
    perturbationType: string,
    targets: string[],
  ) => {
    if (!examples.some((example) => example.text === text)) {
      examples.push({ text, perturbationType, targets });
    }
  };

  for (const preset of presets.filter(
    (item) =>
      item.species === cell.species && item.cell_type === cell.cell_type,
  )) {
    const type = preset.example_perturbation_type;
    const targets = preset.example_targets ?? [];
    if (!type) continue;

    if (type === "gene") {
      for (const target of targets) {
        add(`How does expression change after knocking down ${target}?`, type, [target]);
      }
      if (targets.length > 1) {
        add(`How does expression change after perturbing ${targets.join(" and ")} together?`, type, targets);
      } else if (targets[0]) {
        add(`Which expression responses are strongest after perturbing ${targets[0]}?`, type, targets);
      }
    } else if (type === "drug" && targets[0]) {
      add(`How does expression change after treatment with ${targets[0]}?`, type, targets);
      add(`Compare expression responses before and after treatment with ${targets[0]}`, type, targets);
    } else if (type === "medium") {
      add(`How does expression change in ${cell.cell_type} after changing the medium?`, type, []);
      add(`What is the expression response of ${cell.cell_type} after changing culture conditions?`, type, []);
    } else if (targets[0]) {
      add(`How does expression change after perturbing ${targets.join(" and ")}?`, type, targets);
      add(`Compare expression responses before and after perturbing ${targets.join(" and ")}`, type, targets);
    }
  }

  return examples.slice(0, 3);
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
      ? `Missing: ${parsed.missing_fields.join(", ")}`
      : "",
    parsed.errors.length ? `Errors: ${parsed.errors.join(", ")}` : "",
  ].filter(Boolean);
  return `A more specific experiment description is needed. ${details.join("; ") || "Please specify the perturbation type and targets."} No simulation task was created.`;
}

function requestValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map(String).join(", ") || "—";
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
  const [researchTasks, setResearchTasks] = useState<ResearchTask[]>([]);
  const [researchPreview, setResearchPreview] = useState<{
    task: ResearchTask;
    compatibility: ResearchTaskCompatibility;
  } | null>(null);
  const [researchError, setResearchError] = useState<string | null>(null);
  const [researchLoading, setResearchLoading] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [speciesFilter, setSpeciesFilter] = useState("all");
  const requestEpochRef = useRef(0);
  const turnIdRef = useRef(0);
  const inFlightRef = useRef(false);
  const latestTurnRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    requestEpochRef.current += 1;
    inFlightRef.current = false;
    setQuery("");
    setTurns([]);
    setBusy(false);
    setResearchPreview(null);
    setResearchError(null);
    setResearchLoading(null);
  }, [chatEpoch]);

  useEffect(() => {
    requestEpochRef.current += 1;
    inFlightRef.current = false;
    setBusy(false);
    setResearchPreview(null);
    setResearchError(null);
    setResearchLoading(null);
  }, [page]);

  useEffect(() => {
    let current = true;
    getResearchTasks()
      .then(({ tasks }) => {
        if (current) setResearchTasks(tasks);
      })
      .catch(() => {
        if (current) setResearchTasks([]);
      });
    return () => {
      current = false;
    };
  }, []);

  useEffect(() => {
    setResearchPreview(null);
    setResearchError(null);
  }, [selectedCell]);

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
  const promptExamples = useMemo(
    () =>
      selectedCell
        ? cellPromptExamples(options?.cell_presets ?? [selectedCell], selectedCell)
        : [],
    [options, selectedCell],
  );
  const cellResearchTasks = useMemo(
    () =>
      selectedCell
        ? researchTasks.filter((task) => researchTaskMatchesCell(task, selectedCell))
        : [],
    [researchTasks, selectedCell],
  );

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
            : "The runtime service is unavailable. Please try again later.",
      });
    } finally {
      if (isCurrent()) {
        inFlightRef.current = false;
        setBusy(false);
      }
    }
  }

  async function previewResearchTask(task: ResearchTask) {
    if (busy || inFlightRef.current) return;

    const requestEpoch = requestEpochRef.current + 1;
    requestEpochRef.current = requestEpoch;
    inFlightRef.current = true;
    const isCurrent = () => requestEpochRef.current === requestEpoch;

    setBusy(true);
    setResearchLoading(task.task_id);
    setResearchPreview(null);
    setResearchError(null);

    try {
      const compatibility = await getResearchTaskCompatibility(task.task_id);
      if (!isCurrent()) return;
      if (
        compatibility.task_id !== task.task_id ||
        compatibility.descriptor_fingerprint.length !== 64 ||
        compatibility.compatibility_fingerprint.length !== 64 ||
        compatibility.execution_plan.pack_id !== task.pack_id ||
        compatibility.execution_plan.pack_version !== task.pack_version
      ) {
        throw new Error("research task compatibility identity mismatch");
      }
      setResearchPreview({ task, compatibility });
    } catch (reason: unknown) {
      if (!isCurrent()) return;
      const detail = reason instanceof Error ? reason.message : "";
      setResearchError(
        detail.includes("direct_v2_factory_unconfigured")
          ? "A real research runtime is not configured. No task was created; mock, legacy model, and parsing fallbacks are disabled."
          : "The research compatibility preview failed. No task was created; legacy fallbacks are disabled.",
      );
    } finally {
      if (isCurrent()) {
        inFlightRef.current = false;
        setBusy(false);
        setResearchLoading(null);
      }
    }
  }

  async function runResearchTask() {
    if (
      !researchPreview?.compatibility.execution_plan.executable ||
      busy ||
      inFlightRef.current
    ) {
      return;
    }

    const requestEpoch = requestEpochRef.current + 1;
    requestEpochRef.current = requestEpoch;
    inFlightRef.current = true;
    const turnId = turnIdRef.current + 1;
    turnIdRef.current = turnId;
    const isCurrent = () => requestEpochRef.current === requestEpoch;
    const task = researchPreview.task;

    setBusy(true);
    setTurns((current) => [
      ...current,
      {
        id: turnId,
        query: researchTaskLabel(task, "Run"),
        status: "pending",
        request: task.request,
      },
    ]);

    try {
      const job = await executeResearchTask(
        task.task_id,
        researchPreview.compatibility.compatibility_fingerprint,
      );
      onJobCreated(job.job_id);
      if (!isCurrent()) return;
      updateTurn(turnId, { status: "report", jobId: job.job_id });
    } catch (reason: unknown) {
      if (!isCurrent()) return;
      const detail = reason instanceof Error ? reason.message : "";
      updateTurn(turnId, {
        status: "error",
        message:
          detail ||
          "Real research tasks are unavailable; mock, legacy model, and parsing fallbacks are disabled.",
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
      const example = promptExamples.find((item) => item.text === text);
      const parsed = await parse(
        composeCellQuery(text, cell, example),
        "llm_assisted",
      );
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
          message: "The selected cell context failed request validation. No simulation task was created.",
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
            : "The runtime service is unavailable. Please try again later.",
      });
    } finally {
      if (isCurrent()) {
        inFlightRef.current = false;
        setBusy(false);
      }
    }
  }

  if (page === "omics-intake") {
    return <DataLibrary section="datasets" />;
  }

  if (page === "pack-library") {
    return <DataLibrary section="packs" />;
  }

  if (page === "data-center") {
    const species = ["all", ...(options?.species ?? [])];
    return (
      <section className="cell-data-center" aria-labelledby="data-center-title">
        <header>
          <span>PRAXIS-VirtualCell Data Center</span>
          <h1 id="data-center-title">Choose a cell</h1>
          <p>
            Browse biological context presets provided by the backend. Selection sets the species and cell context;
            these resources are not bound by the selection. The report records the actual execution identity.
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
            Cell catalog unavailable: {optionsError}
          </p>
        )}
        {options == null && !optionsError && (
          <p className="chat-loading">Loading cell catalog…</p>
        )}
        {catalogError && (
          <p className="cell-resource-note">
            Same-species dataset and Pack counts are unavailable. Cell presets still come from backend options.
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
          These are reviewable context presets, not registered Virtual Cells. Same-species
          Dataset or Pack counts do not imply binding, compatibility, execution capability, or scientific validation.
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
            <p>Results, abstention, and execution identity come from records saved by the backend.</p>
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
          <span>PRAXIS-VirtualCell</span>
          <h1 id="cell-first-title">Choose a cell to begin.</h1>
          <p>
            Set the biological context, then describe the experiment in natural language. The backend routes the request through existing execution paths and
            returns a report showing a prediction or explicit abstention.
          </p>
        </div>

        {optionsError && (
          <p className="chat-error" role="alert">
            Cell catalog unavailable: {optionsError}
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
              Describe the perturbation, treatment, or condition. I will submit the task to the runtime backend and return a report;
              the report records the actual models, execution identity, and abstention.
            </p>
          </div>
        </div>

        {(cellResearchTasks.length > 0 ||
          (turns.length === 0 && promptExamples.length > 0)) && (
          <div className="prompt-examples" aria-label="Example questions">
            <span>Try an example</span>
            <div>
              {cellResearchTasks.map((task) => (
                <button
                  key={task.task_id}
                  type="button"
                  className="registered-research"
                  disabled={busy}
                  onClick={() => void previewResearchTask(task)}
                >
                  {researchLoading === task.task_id
                    ? "Checking registered compatibility…"
                    : researchTaskLabel(task, "Preview")}
                </button>
              ))}
              {turns.length === 0 &&
                promptExamples.map((example) => (
                  <button
                    key={example.text}
                    type="button"
                    onClick={() => {
                      setQuery(example.text);
                      composerRef.current?.focus();
                    }}
                  >
                    {example.text}
                  </button>
                ))}
            </div>
            {researchError && (
              <p className="chat-error" role="alert">
                {researchError}
              </p>
            )}
            {researchPreview && (
              <section aria-label="Research task compatibility preview">
                <dl className="interpretation-grid">
                  <div>
                    <dt>Pack</dt>
                    <dd>
                      {researchPreview.compatibility.execution_plan.pack_id}@
                      {researchPreview.compatibility.execution_plan.pack_version}
                    </dd>
                  </div>
                  <div>
                    <dt>Model</dt>
                    <dd>
                      {researchPreview.task.model_name}@
                      {researchPreview.task.model_version}
                    </dd>
                  </div>
                  <div>
                    <dt>Executable</dt>
                    <dd>
                      {String(
                        researchPreview.compatibility.execution_plan.executable,
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt>Scope</dt>
                    <dd>{researchPreview.task.execution_scope}</dd>
                  </div>
                  <div>
                    <dt>Scientifically validated</dt>
                    <dd>
                      {String(researchPreview.task.scientifically_validated)}
                    </dd>
                  </div>
                </dl>
                {researchPreview.compatibility.execution_plan.executable ? (
                  <button
                    type="button"
                    className="confirm-interpretation"
                    disabled={busy}
                    onClick={() => void runResearchTask()}
                  >
                    Confirm compatibility and run direct-v2
                  </button>
                ) : (
                  <p className="chat-error" role="alert">
                    The compatibility plan is not executable. No task was created.
                  </p>
                )}
              </section>
            )}
            <small>
              “Preview registered…” retrieves a compatibility plan from the same runtime and submits the catalog task only after explicit confirmation.
              Other examples only fill the question. Research execution does not imply scientific validation or production promotion.
            </small>
          </div>
        )}

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
                    Parsing the task and submitting it to the runtime backend. The selected cell preset does not bind a
                    Dataset, Pack, or model.
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
                    No language model is connected. Please confirm the structured request to avoid misunderstandings from deterministic fallback parsing.
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
                  The selected cell preset only supplies request context; it does not bind a Dataset, Pack,
                  or model. The report does not imply a scientifically validated predictor for this cell.
                </p>
                <LazyResultsStage jobId={turn.jobId} onReset={onNewChat} />
              </div>
            )}
          </div>
        ))}
      </div>

      <form className="chat-composer" onSubmit={submit}>
        <label htmlFor="chat-query">Message PRAXIS-VirtualCell</label>
        <textarea
          ref={composerRef}
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
          Language assistance only parses and explains text; the deterministic backend handles data, simulation, numerical results, and final decisions.
          {health?.llm_enabled === false
            ? " No language model is connected. Deterministic parsing requires confirmation before execution."
            : ""}
        </small>
      </form>
    </section>
  );
}
