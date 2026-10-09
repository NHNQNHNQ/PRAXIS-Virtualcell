import { useEffect, useMemo, useState } from "react";
import {
  getOptions,
  type CellPreset,
  type Options,
  type ParseResult,
} from "../../api";
import Card from "../ui/Card";
import FieldRow from "../ui/FieldRow";
import Button from "../ui/Button";
import type { FieldStatus } from "../ui/StatusPill";
function readStr(src: Record<string, unknown>, key: string): string {
  const v = src[key];
  return typeof v === "string" ? v : "";
}

function readStringList(src: Record<string, unknown>, key: string): string {
  const v = src[key];
  return Array.isArray(v)
    ? v.filter((item): item is string => typeof item === "string").join(", ")
    : "";
}

export default function ReviewStage({
  parsedIntent,
  initialRequest,
  onConfirmed,
  onBack,
  onEdited,
}: {
  parsedIntent: ParseResult;
  initialRequest: Record<string, unknown> | null;
  onConfirmed: (request: Record<string, unknown>) => void;
  onBack: (draft: Record<string, unknown>) => void;
  onEdited: (draft: Record<string, unknown>) => void;
}) {
  const cand = parsedIntent.candidate_request as Record<string, unknown>;
  const seed = initialRequest ?? cand;

  const [species, setSpecies] = useState(() => readStr(seed, "species"));
  const [cellType, setCellType] = useState(() => readStr(seed, "cell_type"));
  const [pertType, setPertType] = useState(() =>
    readStr(seed, "perturbation_type"),
  );
  const [targets, setTargets] = useState(() =>
    readStringList(seed, "perturbation_targets"),
  );
  const [targetsEdited, setTargetsEdited] = useState(false);
  const [opts, setOpts] = useState<Options | null>(null);

  useEffect(() => {
    getOptions().then(setOpts).catch(() => setOpts(null));
  }, []);

  function applyPreset(p: CellPreset) {
    const nextPertType = p.example_perturbation_type ?? pertType;
    const nextTargets = p.example_targets
      ? p.example_targets.join(", ")
      : targets;
    onEdited(
      currentDraft({
        species: p.species,
        cellType: p.cell_type,
        pertType: nextPertType,
        targets: nextTargets,
      }),
    );
    setSpecies(p.species);
    setCellType(p.cell_type);
    setPertType(nextPertType);
    setTargets(nextTargets);
    setTargetsEdited(true);
  }

  function withCurrent(list: string[] | undefined, cur: string): string[] {
    const xs = list ?? [];
    return cur && !xs.includes(cur) ? [cur, ...xs] : xs;
  }

  const missingSet = useMemo(
    () => new Set(parsedIntent.missing_fields),
    [parsedIntent.missing_fields],
  );
  const assumptionsText = useMemo(
    () => parsedIntent.assumptions.join(" ").toLowerCase(),
    [parsedIntent.assumptions],
  );

  function statusOf(key: string, value: string): FieldStatus {
    if (value.trim()) {
      return assumptionsText.includes(key) ? "inferred" : "confirmed";
    }
    return missingSet.has(key) ? "missing" : "editable";
  }

  function currentDraft(
    overrides: Partial<{
      species: string;
      cellType: string;
      pertType: string;
      targets: string;
    }> = {},
  ): Record<string, unknown> {
    const values = { species, cellType, pertType, targets, ...overrides };
    return {
      ...cand,
      species: values.species,
      cell_type:
        values.cellType.trim() === "" ? null : values.cellType.trim(),
      perturbation_type: values.pertType,
      perturbation_targets: values.targets
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    };
  }

  function confirm() {
    onConfirmed(currentDraft());
  }

  const taskType = readStr(cand, "task_type");
  function errorIsUnresolved(error: string): boolean {
    if (error.startsWith("unsupported_species:")) {
      const current = species.trim().toLowerCase();
      const original = error.slice("unsupported_species:".length).trim().toLowerCase();
      return opts ? !opts.species.includes(current) : !current || current === original;
    }
    if (error.startsWith("unsupported_perturbation_type:")) {
      const current = pertType.trim().toLowerCase();
      const original = error
        .slice("unsupported_perturbation_type:".length)
        .trim()
        .toLowerCase();
      return opts
        ? !opts.perturbation_type.includes(current)
        : !current || current === original;
    }
    if (error === "invalid_cell_type_type") return false;
    if (error === "invalid_perturbation_targets_type") {
      return !(targetsEdited && (pertType === "medium" || targets.trim()));
    }
    return true;
  }
  const unresolvedErrors = parsedIntent.errors.filter(errorIsUnresolved);
  const resolvedErrors = parsedIntent.errors.filter(
    (error) => !errorIsUnresolved(error),
  );
  const unresolvedMissing = parsedIntent.missing_fields.filter((field) => {
    if (field === "species") return !species.trim();
    if (field === "perturbation_type") return !pertType.trim();
    if (field === "perturbation_targets") {
      return pertType !== "medium" && !targets.trim();
    }
    return true;
  });
  const confirmationBlocked =
    !species.trim() ||
    !pertType.trim() ||
    (pertType !== "medium" && !targets.trim()) ||
    unresolvedErrors.length > 0;

  return (
    <section style={{ maxWidth: "820px" }}>
      <div style={{ marginBottom: "var(--space-5)" }}>
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "28px",
            fontWeight: 500,
            lineHeight: 1.15,
            letterSpacing: "-0.01em",
            color: "var(--text)",
            margin: 0,
          }}
        >
          Review the task interpretation
        </h1>
        <p
          style={{
            marginTop: "var(--space-3)",
            fontSize: "14px",
            lineHeight: 1.55,
            color: "var(--text-muted)",
            maxWidth: "62ch",
          }}
        >
          Review the interpretation of your experiment. Check the biological system and perturbation settings and edit them if needed;
          continue once they are correct. This step makes the task definition reviewable before execution.
        </p>
      </div>

      <Card title="Biological system">
        {opts && opts.cell_presets.length > 0 && (
          <div style={{ marginBottom: "var(--space-3)" }}>
            <label
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "var(--space-1)",
                fontSize: "13px",
                color: "var(--text-muted)",
                maxWidth: "360px",
              }}
            >
              Load a common system (editable)
              <select
                defaultValue=""
                onChange={(e) => {
                  const p = opts.cell_presets.find((x) => x.id === e.target.value);
                  if (p) applyPreset(p);
                }}
              >
                <option value="">— Select species / cell type —</option>
                {opts.cell_presets.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}

        <FieldRow label="Species" status={statusOf("species", species)}>
          {opts ? (
            <select
              value={species}
              onChange={(e) => {
                const value = e.target.value;
                onEdited(currentDraft({ species: value }));
                setSpecies(value);
              }}
            >
              {withCurrent(opts.species, species).map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          ) : (
            <input
              value={species}
              onChange={(e) => {
                const value = e.target.value;
                onEdited(currentDraft({ species: value }));
                setSpecies(value);
              }}
            />
          )}
        </FieldRow>

        <FieldRow
          label="Cell type (optional)"
          status={cellType.trim() ? "confirmed" : "editable"}
        >
          <input
            value={cellType}
            onChange={(e) => {
              const value = e.target.value;
              onEdited(currentDraft({ cellType: value }));
              setCellType(value);
            }}
          />
        </FieldRow>
      </Card>

      <Card title="Perturbation">
        <FieldRow
          label="Perturbation type"
          status={statusOf("perturbation_type", pertType)}
        >
          {opts ? (
            <select
              value={pertType}
              onChange={(e) => {
                const value = e.target.value;
                onEdited(currentDraft({ pertType: value }));
                setPertType(value);
              }}
            >
              {withCurrent(opts.perturbation_type, pertType).map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          ) : (
            <input
              value={pertType}
              onChange={(e) => {
                const value = e.target.value;
                onEdited(currentDraft({ pertType: value }));
                setPertType(value);
              }}
            />
          )}
        </FieldRow>

        <FieldRow
          label="Perturbation targets (comma-separated)"
          status={statusOf("perturbation_targets", targets)}
        >
          <input
            value={targets}
            onChange={(e) => {
              const value = e.target.value;
              onEdited(currentDraft({ targets: value }));
              setTargets(value);
              setTargetsEdited(true);
            }}
            placeholder="Example: AHR, TP53"
          />
        </FieldRow>
      </Card>

      <Card title="Requested output">
        <FieldRow label="Task type" status="locked">
          <span style={{ fontSize: "14px", color: "var(--text)" }}>
            {taskType || "—"}
          </span>
        </FieldRow>
      </Card>

      <Card title="Task interpretation and assumptions">
        <ul className="meta" style={{ marginTop: 0 }}>
          <li>
            Interpretation method:
            <code>
              {parsedIntent.parser.toLowerCase().includes("llm")
                ? "Language assistance"
                : "Deterministic keywords"}
            </code>
          </li>
          <li>
            Language model used: <code>{parsedIntent.llm_used ? "Yes" : "No"}</code>
          </li>
        </ul>

        {parsedIntent.assumptions.length > 0 && (
          <div className="note">
            Inferred assumptions: {parsedIntent.assumptions.join(";")}
          </div>
        )}
        {unresolvedMissing.length > 0 && (
          <div className="warn">
            Missing information: {unresolvedMissing.join(", ")}
          </div>
        )}
        {unresolvedErrors.length > 0 && (
          <div className="err">
            Interpretation issues: {unresolvedErrors.join(";")}
          </div>
        )}
        {resolvedErrors.length > 0 && (
          <div className="note">
            Original issues resolved in this draft: {resolvedErrors.join(";")}
          </div>
        )}
        {confirmationBlocked && (
          <div className="warn">Clarify this description before execution.</div>
        )}
      </Card>

      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          gap: "var(--space-2)",
          marginTop: "var(--space-4)",
        }}
      >
        <Button variant="ghost" onClick={() => onBack(currentDraft())}>
          ← Back
        </Button>
        <Button onClick={confirm} disabled={confirmationBlocked}>
          Confirm and continue →
        </Button>
      </div>
    </section>
  );
}
