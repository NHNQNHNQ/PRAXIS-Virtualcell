import { type FormEvent, useEffect, useState } from "react";
import {
  getDataCatalog,
  getPackCatalog,
  type DataCatalog,
  type Health,
  type JobSummary,
  type PackCatalog,
} from "../../api";
import { Badge, Button, Card, EmptyState } from "../ui";
import LazyResultsStage from "../stages/LazyResultsStage";

export type PlatformPageKind =
  | "home"
  | "virtual-cells"
  | "reports"
  | "data-center"
  | "my-cells"
  | "settings"
  | "organisms";

export type PlatformNavigationTarget =
  | PlatformPageKind
  | "datasets"
  | "packs"
  | "agent-workspace";

type PlatformPageProps = {
  page: PlatformPageKind;
  jobs: JobSummary[] | null;
  jobsError: string | null;
  health: Health | null;
  healthError: string | null;
  openedJobId: string | null;
  onNavigate: (target: PlatformNavigationTarget) => void;
  onOpenJob: (jobId: string) => void;
  onCloseReport: () => void;
  onNewQuery: () => void;
  onStartQuery: (query: string) => void;
};

const CATALOG_PAGES = new Set<PlatformPageKind>([
  "home",
  "virtual-cells",
  "data-center",
  "organisms",
]);

export default function PlatformPage({
  page,
  jobs,
  jobsError,
  health,
  healthError,
  openedJobId,
  onNavigate,
  onOpenJob,
  onCloseReport,
  onNewQuery,
  onStartQuery,
}: PlatformPageProps) {
  const [catalog, setCatalog] = useState<DataCatalog | null>(null);
  const [packCatalog, setPackCatalog] = useState<PackCatalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [homeQuery, setHomeQuery] = useState("");

  useEffect(() => {
    if (!CATALOG_PAGES.has(page)) return;
    let current = true;
    setCatalog(null);
    setPackCatalog(null);
    setError(null);
    Promise.all([getDataCatalog(), getPackCatalog()])
      .then(([nextCatalog, nextPackCatalog]) => {
        if (!current) return;
        setCatalog(nextCatalog);
        setPackCatalog(nextPackCatalog);
      })
      .catch((reason: unknown) => {
        if (current) setError(String(reason));
      });
    return () => {
      current = false;
    };
  }, [page]);

  const loading =
    CATALOG_PAGES.has(page) &&
    catalog == null &&
    packCatalog == null &&
    error == null;
  const fileCount =
    catalog?.datasets.reduce(
      (total, dataset) => total + dataset.files.length,
      0,
    ) ?? 0;

  if (page === "home") {
    function submitHomeQuery(event: FormEvent<HTMLFormElement>) {
      event.preventDefault();
      if (homeQuery.trim()) onStartQuery(homeQuery.trim());
    }

    return (
      <section className="research-home" aria-labelledby="home-title">
        <header className="research-hero">
          <span className="platform-eyebrow">PRAXIS · VIRTUAL CELL</span>
          <h1 id="home-title">A trustworthy foundation for virtual-cell research.</h1>
          <p>
            当前部署尚无持久化 Virtual Cell registry。你可以检查真实数据与 Pack
            合同，或启动明确标注为 unbound 的受控任务；缺少兼容模型时系统必须 abstain。
          </p>
        </header>

        <form className="home-query-card" onSubmit={submitHomeQuery}>
          <div className="home-cell-context">
            <div>
              <span>Current virtual cell</span>
              <strong>尚未绑定持久化实例</strong>
            </div>
            <Badge tone="neutral">Registry unavailable</Badge>
          </div>
          <label htmlFor="home-query">Describe a scientific task</label>
          <textarea
            id="home-query"
            rows={4}
            value={homeQuery}
            onChange={(event) => setHomeQuery(event.target.value)}
            placeholder="例如：在 human 细胞敲低 AHR 后，哪些表达模块可能发生变化？"
          />
          <div className="home-query-actions">
            <p>
              当前问题将进入未绑定 Virtual Cell 的既有五阶段工作区；执行身份以后端结果为准。
            </p>
            <Button type="submit" disabled={!homeQuery.trim()}>
              Open unbound Agent Workspace
            </Button>
          </div>
        </form>

        <section className="home-explore" aria-labelledby="explore-title">
          <div className="section-heading">
            <div>
              <span className="platform-eyebrow">EXPLORE THE FOUNDATION</span>
              <h2 id="explore-title">从真实资源开始</h2>
            </div>
            <Button
              variant="ghost"
              onClick={() => onNavigate("virtual-cells")}
            >
              Browse Virtual Cells
            </Button>
          </div>

          {loading && <p className="data-message">读取平台资源…</p>}
          {error && (
            <p className="err" role="alert">
              平台资源不可用：{error}
            </p>
          )}
          <div className="home-foundation-grid">
            <button
              type="button"
              className="home-foundation-card"
              onClick={() => onNavigate("virtual-cells")}
            >
              <span>VIRTUAL CELL LIBRARY</span>
              <strong>实例目录尚未提供</strong>
              <p>Pack 或数据集不会被前端自动冒充为 Virtual Cell。</p>
              <em>View honest state →</em>
            </button>
            <button
              type="button"
              className="home-foundation-card"
              onClick={() => onNavigate("data-center")}
            >
              <span>DATA FOUNDATION</span>
              <strong>
                {catalog
                  ? `${catalog.datasets.length} datasets · ${fileCount} files`
                  : "目录状态待读取"}
              </strong>
              <p>公开数据、隔离上传和版本身份均来自现有后端目录。</p>
              <em>Open Data Center →</em>
            </button>
            <button
              type="button"
              className="home-foundation-card"
              onClick={() => onNavigate("reports")}
            >
              <span>RESULTS & PROVENANCE</span>
              <strong>
                {jobsError
                  ? "运行目录不可用"
                  : jobs == null
                    ? "运行目录读取中"
                    : `${jobs.length} recorded runs`}
              </strong>
              <p>预测、abstention、trace 与 execution identity 保持可审计。</p>
              <em>Browse reports →</em>
            </button>
          </div>
        </section>
      </section>
    );
  }

  if (page === "virtual-cells") {
    return (
      <section className="cell-hub" aria-labelledby="virtual-cells-title">
        <header className="hub-heading">
          <div>
            <span className="platform-eyebrow">VIRTUAL CELL HUB</span>
            <h1 id="virtual-cells-title">Virtual Cells</h1>
            <p>
              发现具有显式物种、细胞上下文、数据身份、能力边界和版本指纹的虚拟细胞。
            </p>
          </div>
          <Badge tone="neutral">Registry unavailable</Badge>
        </header>

        {error && (
          <p className="err" role="alert">
            支撑资源不可用：{error}
          </p>
        )}
        <Card>
          <EmptyState
            title="此部署尚未提供 Virtual Cell registry"
            hint="当前后端只有数据目录和 VirtualCellPack 目录；它们不会自动生成可查询的细胞实例，也不代表模型可执行或已经科学验证。"
          />
          <div className="row">
            <Button variant="ghost" onClick={() => onNavigate("data-center")}>
              Inspect foundation resources
            </Button>
            <Button onClick={() => onNavigate("agent-workspace")}>
              Open unbound workspace
            </Button>
          </div>
        </Card>

        <section className="cell-contract-preview">
          <span className="platform-eyebrow">A REGISTERED CELL MUST DECLARE</span>
          <div>
            <article>
              <strong>Biological identity</strong>
              <p>Taxon、cell context、state、condition 与 ontology CURIE。</p>
            </article>
            <article>
              <strong>Data & Pack identity</strong>
              <p>不可变版本、SHA-256、feature contract 与来源。</p>
            </article>
            <article>
              <strong>Task-bound capability</strong>
              <p>模型兼容和环境可执行必须针对具体请求重新检查。</p>
            </article>
            <article>
              <strong>Scientific boundary</strong>
              <p>验证状态、适用范围、限制和明确 abstention 原因。</p>
            </article>
          </div>
        </section>
      </section>
    );
  }

  if (page === "reports") {
    if (openedJobId) {
      return (
        <section className="reports-page" aria-label="Report detail">
          <header className="hub-heading">
            <div>
              <span className="platform-eyebrow">REPORTS / SAVED RUN</span>
              <h1>Report</h1>
              <p>结果、abstention 和 execution identity 均来自后端保存记录。</p>
            </div>
            <Button variant="ghost" onClick={onCloseReport}>
              Back to Reports
            </Button>
          </header>
          <LazyResultsStage
            key={openedJobId}
            jobId={openedJobId}
            onReset={onNewQuery}
          />
        </section>
      );
    }

    return (
      <section className="reports-page" aria-labelledby="reports-title">
        <header className="hub-heading">
          <div>
            <span className="platform-eyebrow">RESULTS & PROVENANCE</span>
            <h1 id="reports-title">Reports</h1>
            <p>查看后端保存的预测、abstention、trace 与 execution identity。</p>
          </div>
          <Badge tone="neutral">Read-only run index</Badge>
        </header>
        {jobsError ? (
          <p className="err" role="alert">
            Agent Run 目录不可用：{jobsError}
          </p>
        ) : jobs == null ? (
          <p className="data-message">读取 Agent Run 目录…</p>
        ) : jobs.length === 0 ? (
          <Card>
            <EmptyState
              title="还没有可审计的运行记录"
              hint="完成一次 Agent Workspace 任务后，后端保存的结果会出现在这里。"
            />
          </Card>
        ) : (
          <div className="report-list">
            {jobs.map((job) => (
              <article className="report-row" key={job.job_id}>
                <div>
                  <span className="report-id">{job.job_id}</span>
                  <h2>
                    {job.species ?? "未指定物种"} ·{" "}
                    {job.perturbation_targets.join("、") || "无扰动靶点"}
                  </h2>
                  <p>
                    status {job.status} · reliability{" "}
                    {job.reliability ?? "未记录"}
                  </p>
                </div>
                <div className="report-actions">
                  <Badge tone={job.abstain ? "inferred" : "neutral"}>
                    {job.abstain === true
                      ? "Abstained"
                      : job.abstain === false
                        ? "Result recorded"
                        : "Outcome unavailable"}
                  </Badge>
                  <Button variant="ghost" onClick={() => onOpenJob(job.job_id)}>
                    Open report
                  </Button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    );
  }

  if (page === "data-center") {
    return (
      <section className="data-center-page" aria-labelledby="data-center-title">
        <header className="hub-heading">
          <div>
            <span className="platform-eyebrow">ADVANCED FOUNDATION</span>
            <h1 id="data-center-title">Data Center</h1>
            <p>检查真实数据资源、物种汇总和 VirtualCellPack 合同。</p>
          </div>
          <Badge tone="neutral">No automatic build or install</Badge>
        </header>
        <div className="note data-boundary">
          下载、上传回执或 Pack 校验均不代表 Virtual Cell 已构建、模型可执行或已经科学验证。
        </div>
        {loading && <p className="data-message">读取数据底座…</p>}
        {error && (
          <p className="err" role="alert">
            数据底座不可用：{error}
          </p>
        )}
        <div className="data-center-grid">
          <button
            type="button"
            className="data-center-card"
            onClick={() => onNavigate("organisms")}
          >
            <span>ORGANISMS</span>
            <strong>
              {catalog ? `${catalog.species.length} catalogued taxa` : "状态待读取"}
            </strong>
            <p>仅汇总目录中的 taxonomy、数据集、文件和 Pack。</p>
            <em>Inspect organisms →</em>
          </button>
          <button
            type="button"
            className="data-center-card"
            onClick={() => onNavigate("datasets")}
          >
            <span>DATA CATALOG & UPLOADS</span>
            <strong>
              {catalog
                ? `${catalog.datasets.length} datasets · ${fileCount} files`
                : "状态待读取"}
            </strong>
            <p>公开下载与 byte-preserving quarantine upload。</p>
            <em>Open data catalog →</em>
          </button>
          <button
            type="button"
            className="data-center-card"
            onClick={() => onNavigate("packs")}
          >
            <span>VIRTUALCELLPACKS</span>
            <strong>
              {packCatalog
                ? `${packCatalog.packs.length} Pack records`
                : "状态待读取"}
            </strong>
            <p>查看验证、fingerprint 和模型卡声明，不推导 readiness。</p>
            <em>Inspect Pack contracts →</em>
          </button>
        </div>
      </section>
    );
  }

  if (page === "my-cells") {
    return (
      <section className="cell-hub" aria-labelledby="my-cells-title">
        <header className="hub-heading">
          <div>
            <span className="platform-eyebrow">PRIVATE WORKSPACE</span>
            <h1 id="my-cells-title">My Cells</h1>
            <p>这里将承载有明确所有权、版本和审计记录的私有 Virtual Cell。</p>
          </div>
          <Badge tone="neutral">Ownership contract unavailable</Badge>
        </header>
        <Card>
          <EmptyState
            title="此部署尚未提供用户级 Virtual Cell 存储"
            hint="隔离区上传不会自动出现在 My Cells；当前也没有 clone、share、delete 或 query 的持久化合同。"
          />
          <Button variant="ghost" onClick={() => onNavigate("data-center")}>
            Inspect quarantine boundary
          </Button>
        </Card>
      </section>
    );
  }

  if (page === "settings") {
    return (
      <section className="settings-page" aria-labelledby="settings-title">
        <header className="hub-heading">
          <div>
            <span className="platform-eyebrow">RUNTIME CONTEXT</span>
            <h1 id="settings-title">Settings</h1>
            <p>当前只展示后端公开身份；本页不会保存密钥或伪造服务器设置。</p>
          </div>
          <Badge tone="neutral">Read-only</Badge>
        </header>
        {healthError && (
          <p className="err" role="alert">
            后端状态不可用：{healthError}
          </p>
        )}
        <Card title="Deployment identity">
          {health ? (
            <dl className="settings-facts">
              <div>
                <dt>Status</dt>
                <dd>{health.status}</dd>
              </div>
              <div>
                <dt>Product version</dt>
                <dd>{health.product_version}</dd>
              </div>
              <div>
                <dt>Runtime protocol</dt>
                <dd>{health.runtime_protocol_version}</dd>
              </div>
              <div>
                <dt>Git SHA</dt>
                <dd>{health.git_sha}</dd>
              </div>
            </dl>
          ) : !healthError ? (
            <p className="data-message">读取部署身份…</p>
          ) : null}
        </Card>
        <div className="note data-boundary">
          语言模型仅用于解析与解释，不参与数据真相、数值预测、兼容性裁决或最终结论。
        </div>
      </section>
    );
  }

  return (
    <section className="data-library" aria-labelledby="organisms-title">
      <header className="data-heading">
        <div>
          <span className="platform-eyebrow">DATA CENTER / ORGANISMS</span>
          <h1 id="organisms-title">Organisms</h1>
          <p>按后端数据目录中的 taxonomy 身份汇总数据集、文件与 Pack。</p>
        </div>
        <Badge tone="neutral">Read-only catalog</Badge>
      </header>
      <div className="note data-boundary">
        以下数字仅是目录计数，不推导 Virtual Cell readiness、模型兼容性或科学有效性。
      </div>
      {loading && <p className="data-message">读取物种目录…</p>}
      {error && (
        <p className="err" role="alert">
          物种目录不可用：{error}
        </p>
      )}
      <div className="data-grid">
        {catalog?.species.map((species) => {
          const datasets = catalog.datasets.filter(
            (dataset) => dataset.species.taxon_id === species.taxon_id,
          );
          const speciesFiles = datasets.reduce(
            (total, dataset) => total + dataset.files.length,
            0,
          );
          const packs =
            packCatalog?.packs.filter(
              (pack) => pack.taxon?.ontology_id === species.taxon_id,
            ).length ?? 0;
          return (
            <article className="data-card" key={species.id}>
              <div className="data-card-title">
                <div>
                  <h2>
                    <i>{species.scientific_name}</i>
                  </h2>
                  <p>{species.id}</p>
                </div>
                <Badge tone="neutral">{species.taxon_id}</Badge>
              </div>
              <dl className="data-facts">
                <div>
                  <dt>Datasets</dt>
                  <dd>{datasets.length}</dd>
                </div>
                <div>
                  <dt>Files</dt>
                  <dd>{speciesFiles}</dd>
                </div>
                <div>
                  <dt>VirtualCellPacks</dt>
                  <dd>{packs}</dd>
                </div>
              </dl>
            </article>
          );
        })}
      </div>
      {!loading && !error && catalog?.species.length === 0 && (
        <EmptyState title="后端目录未声明物种" />
      )}
      <div className="row">
        <Button variant="ghost" onClick={() => onNavigate("data-center")}>
          Back to Data Center
        </Button>
        <Button variant="ghost" onClick={() => onNavigate("datasets")}>
          View datasets
        </Button>
        <Button variant="ghost" onClick={() => onNavigate("packs")}>
          View VirtualCellPacks
        </Button>
      </div>
    </section>
  );
}
