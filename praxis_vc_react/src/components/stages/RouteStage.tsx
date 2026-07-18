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

// Stage 3 · Route(spec §2 "预计涉及的功能模块" / Module Routing Preview)。
// 迁自 views/ModuleContextView:并发拉 8 模块目录(/api/modules)与 cell_presets(/api/options),
// 按 request.species(+可选 cell_type)匹配 cell preset,取其 modules[] 作【预期模块集】,
// 在模块目录卡片网格上高亮这些预期模块。
//
// 🔴 红线 3(核心):module_plan 是 run 产物,运行前绝不重算真实路由。
// 本页展示的是【静态预期】——仅由 cell preset 声明 + /api/modules 目录元数据拼出,
// 【预期,非实际】。真实模块路由结果在运行后的结果页 Module Routing tab 由后端返回。
// 前端在此不做任何路由裁决,不显示 reliability / abstain / verdict 等 run 产物数值。
//
// 前端派生一个轻量静态预期 modulePlan(overall_verdict="expected"),经 onNext 传出,
// 仅为承载预期集 + 满足 route→run 的 canEnter(modulePlan!=null),不是真实路由。

export default function RouteStage({
  request,
  onNext,
  onBack,
}: {
  request: Record<string, unknown>;
  onNext: (plan: ModulePlan) => void;
  onBack: () => void;
}) {
  const [modules, setModules] = useState<ModuleInfo[] | null>(null); // null=加载中,[]=降级
  const [presets, setPresets] = useState<CellPreset[]>([]);

  useEffect(() => {
    // 失败静默降级:getModules 失败 → 空目录提示(EmptyState);getOptions 失败 → 无预期高亮但不阻塞。
    getModules()
      .then((r) => setModules(r.modules))
      .catch(() => setModules([]));
    getOptions()
      .then((o) => setPresets(o.cell_presets))
      .catch(() => setPresets([]));
  }, []);

  const species = request.species == null ? "" : String(request.species);
  const cellType = request.cell_type == null ? "" : String(request.cell_type);

  // 匹配 cell preset:优先 species+cell_type 双命中,否则退化为仅 species 命中(迁 ModuleContextView 逻辑)。
  const matched =
    presets.find(
      (p) => p.species === species && cellType !== "" && p.cell_type === cellType,
    ) ?? presets.find((p) => p.species === species);

  // 预期模块 code 有序列表(preset.modules[] 顺序);无匹配 preset 或未声明 modules 则为空。
  const expectedCodes = useMemo(() => matched?.modules ?? [], [matched]);
  const expectedSet = useMemo(() => new Set(expectedCodes), [expectedCodes]);
  const hasExpectation = expectedCodes.length > 0;

  // 静态预期分组(非真实路由裁决):预期集首个 → primary,其余预期 → secondary,其余 → not activated。
  // 分组顺序按 preset.modules[] 声明序,让"为什么调这些模块"来自 preset 声明而非前端重算。
  const primaryCode = hasExpectation ? expectedCodes[0] : "";
  const secondaryCodes = hasExpectation ? expectedCodes.slice(1) : [];

  // 前端派生的轻量静态 modulePlan:overall_verdict="expected",entries 留空(不编造 run 产物),
  // notes 明示"静态预期(非实际路由)"。仅承载预期集 + 满足 route→run 的 canEnter。
  function buildExpectedPlan(): ModulePlan {
    return {
      species,
      primary: primaryCode,
      secondary: secondaryCodes,
      overall_verdict: "expected",
      entries: [],
      notes: ["静态预期(非实际路由);真实路由在结果页 Module Routing 中由运行结果给出。"],
    };
  }

  // 单张模块卡的静态分组标签(仅用于呈现,非真实裁决)。
  function groupOf(code: string): "primary" | "secondary" | "inactive" {
    if (code === primaryCode && primaryCode !== "") return "primary";
    if (expectedSet.has(code)) return "secondary";
    return "inactive";
  }

  return (
    <section style={{ maxWidth: "880px" }}>
      {/* 标题区:平实说明(spec §3.5),不外泄内部实现名词。 */}
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
          预计涉及的功能模块
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
          根据当前生物体系
          {species ? (
            <>
              （<code>{species}</code>
              {cellType ? (
                <>
                  {" / "}
                  <code>{cellType}</code>
                </>
              ) : null}
              ）
            </>
          ) : null}
          ,下面标出预计会用到的模块。这一步帮助你先了解大致会调用哪些能力,再决定是否运行。
        </p>
      </div>

      {/* Step 1 · 醒目"预期,非实际"横幅(红线 3 核心)。用 .warn(amber)提高存在感。 */}
      <div
        className="warn"
        style={{
          fontSize: "13.5px",
          lineHeight: 1.55,
          padding: "12px 14px",
          marginBottom: "var(--space-4)",
        }}
      >
        <strong>这里是预期,不是实际结果。</strong>
        下面的模块划分只依据所选生物体系的常用配置得出,仅供参考,并不代表运行时真正会怎样调度。
        实际用到的模块、以及它们的可靠性与判定,要等运行结束后在结果页的「模块路由」中查看。
      </div>

      {/* 无匹配 preset:无高亮但不阻塞,可正常前进 run(继承现有语义)。 */}
      {modules != null &&
        modules.length > 0 &&
        matched == null &&
        species !== "" && (
          <div className="note" style={{ marginBottom: "var(--space-4)" }}>
            暂无 <code>{species}</code> 对应的常用体系配置,因此没有预期高亮。这不影响运行,可继续下一步。
          </div>
        )}

      {/* Step 2 · 模块目录卡片网格。 */}
      {modules == null ? (
        <Card title="模块目录">
          <Skeleton lines={4} />
        </Card>
      ) : modules.length === 0 ? (
        <Card title="模块目录">
          <EmptyState
            title="暂时无法读取模块目录"
            hint="模块清单获取失败,已降级为空。这不影响运行,可继续下一步。"
          />
        </Card>
      ) : (
        <Card title="模块目录">
          {hasExpectation && (
            <p
              style={{
                margin: "0 0 var(--space-3)",
                fontSize: "13px",
                color: "var(--text-muted)",
                lineHeight: 1.5,
              }}
            >
              高亮项为预期会用到的模块(仅按常用配置分组,非实际路由);其余标为「本次预计不启用」。
            </p>
          )}
          <div className="module-grid">
            {modules.map((m) => {
              // 高亮匹配用模块语义 id(与 preset.modules 语义码同空间);显示标签仍用 m.code(M1-M8)。
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
                    {group === "primary" && <Badge tone="confirmed">主</Badge>}
                    {group === "secondary" && <Badge tone="neutral">预期</Badge>}
                    {group === "inactive" && (
                      <Badge tone="neutral">未启用</Badge>
                    )}
                  </div>
                  <div className="module-name">{m.display_name}</div>
                  {m.engines.length > 0 && (
                    <div className="module-engines">
                      engines:{m.engines.join(", ")}
                    </div>
                  )}
                  {/* 触发原因=cell preset 声明(非重算);未启用项标"运行后确定"。 */}
                  <div
                    style={{
                      marginTop: "var(--space-2)",
                      fontSize: "12px",
                      lineHeight: 1.45,
                      color: "var(--text-muted)",
                    }}
                  >
                    {on
                      ? "预期原因:所选体系的常用配置声明了该模块。"
                      : "本次预计不启用(是否实际调用,运行后确定)。"}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* 操作行:返回上一步 / 继续到运行前确认。无匹配 preset 也不阻塞前进。 */}
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          gap: "var(--space-2)",
          marginTop: "var(--space-4)",
        }}
      >
        <Button variant="ghost" onClick={onBack}>
          ← 返回
        </Button>
        <Button onClick={() => onNext(buildExpectedPlan())}>下一步 →</Button>
      </div>
    </section>
  );
}
