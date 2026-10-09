import { useEffect, useMemo, useState } from "react";
import {
  getModules,
  getOptions,
  type CellPreset,
  type ModuleInfo,
  type ModulePlan,
} from "../../api";
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import Button from "../ui/Button";
import EmptyState from "../ui/EmptyState";
import Skeleton from "../ui/Skeleton";
export default function RouteStage({
  request,
  onNext,
  onBack,
}: {
  request: Record<string, unknown>;
  onNext: (plan: ModulePlan) => void;
  onBack: () => void;
}) {
  const [modules, setModules] = useState<ModuleInfo[] | null>(null);
  const [presets, setPresets] = useState<CellPreset[]>([]);

  useEffect(() => {
    getModules()
      .then((r) => setModules(r.modules))
      .catch(() => setModules([]));
    getOptions()
      .then((o) => setPresets(o.cell_presets))
      .catch(() => setPresets([]));
  }, []);

  const species = request.species == null ? "" : String(request.species);
  const cellType = request.cell_type == null ? "" : String(request.cell_type);

  const matched =
    presets.find(
      (p) => p.species === species && cellType !== "" && p.cell_type === cellType,
    ) ?? presets.find((p) => p.species === species);

  const expectedCodes = useMemo(() => matched?.modules ?? [], [matched]);
  const expectedSet = useMemo(() => new Set(expectedCodes), [expectedCodes]);
  const hasExpectation = expectedCodes.length > 0;

  const primaryCode = hasExpectation ? expectedCodes[0] : "";
  const secondaryCodes = hasExpectation ? expectedCodes.slice(1) : [];

  function buildExpectedPlan(): ModulePlan {
    return {
      species,
      primary: primaryCode,
      secondary: secondaryCodes,
      overall_verdict: "expected",
      entries: [],
      notes: ["Static expectations, not actual routing. Actual routing appears in the Module routing result tab."],
    };
  }

  function groupOf(code: string): "primary" | "secondary" | "inactive" {
    if (code === primaryCode && primaryCode !== "") return "primary";
    if (expectedSet.has(code)) return "secondary";
    return "inactive";
  }

  return (
    <section style={{ maxWidth: "880px" }}>
      <div style={{ marginBottom: "var(--space-4)" }}>
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
          Expected functional modules
        </h1>
        <p
          style={{
            marginTop: "var(--space-3)",
            fontSize: "14px",
            lineHeight: 1.55,
            color: "var(--text-muted)",
            maxWidth: "64ch",
          }}
        >
          For the current biological system
          {species ? (
            <>
              (<code>{species}</code>
              {cellType ? (
                <>
                  {" / "}
                  <code>{cellType}</code>
                </>
              ) : null}
              )
            </>
          ) : null}
          , the expected modules are highlighted below. Review these capabilities before deciding whether to run.
        </p>
      </div>

      <div
        className="warn"
        style={{
          fontSize: "13.5px",
          lineHeight: 1.55,
          padding: "12px 14px",
          marginBottom: "var(--space-4)",
        }}
      >
        <strong>These are expectations, not actual results.</strong>
        The grouping uses common configurations for the selected biological system. It is a reference and does not determine runtime scheduling.
        After execution, see Module routing for the modules actually used and their reliability decisions.
      </div>

      {modules != null &&
        modules.length > 0 &&
        matched == null &&
        species !== "" && (
          <div className="note" style={{ marginBottom: "var(--space-4)" }}>
            No common system configuration is available for <code>{species}</code>, so no modules are highlighted. You can continue to the next step.
          </div>
        )}

      {modules == null ? (
        <Card title="Module catalog">
          <Skeleton lines={4} />
        </Card>
      ) : modules.length === 0 ? (
        <Card title="Module catalog">
          <EmptyState
            title="Module catalog unavailable"
            hint="The module catalog could not be retrieved. You can continue with the empty catalog."
          />
        </Card>
      ) : (
        <Card title="Module catalog">
          {hasExpectation && (
            <p
              style={{
                margin: "0 0 var(--space-3)",
                fontSize: "13px",
                color: "var(--text-muted)",
                lineHeight: 1.5,
              }}
            >
              Highlighted modules are expected from common configurations; this is not actual routing. Others are marked as not expected for this run.
            </p>
          )}
          <div className="module-grid">
            {modules.map((m) => {
              const group = groupOf(m.id);
              const on = group !== "inactive";
              return (
                <div
                  key={m.id}
                  className={`module-card${on ? " expected" : ""}`}
                  style={on ? undefined : { opacity: 0.62 }}
                >
                  <div className="module-card-head">
                    <code className="module-code">{m.code}</code>
                    {group === "primary" && <Badge tone="confirmed">Primary</Badge>}
                    {group === "secondary" && <Badge tone="neutral">Expected</Badge>}
                    {group === "inactive" && (
                      <Badge tone="neutral">Not expected</Badge>
                    )}
                  </div>
                  <div className="module-name">{m.display_name}</div>
                  {m.engines.length > 0 && (
                    <div className="module-engines">
                      engines:{m.engines.join(", ")}
                    </div>
                  )}
                  <div
                    style={{
                      marginTop: "var(--space-2)",
                      fontSize: "12px",
                      lineHeight: 1.45,
                      color: "var(--text-muted)",
                    }}
                  >
                    {on
                      ? "Expected because the common configuration for this system declares this module."
                      : "Not expected for this run (actual use is determined during execution)."}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          gap: "var(--space-2)",
          marginTop: "var(--space-4)",
        }}
      >
        <Button variant="ghost" onClick={onBack}>
          ← Back
        </Button>
        <Button onClick={() => onNext(buildExpectedPlan())}>Next →</Button>
      </div>
    </section>
  );
}
