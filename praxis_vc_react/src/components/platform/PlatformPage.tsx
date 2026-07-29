import { useEffect, useState } from "react";
import {
  getDataCatalog,
  getPackCatalog,
  type DataCatalog,
  type PackCatalog,
} from "../../api";
import { Badge, Button, Card, EmptyState } from "../ui";

export type PlatformPageKind = "dashboard" | "organisms" | "virtual-cells";

export type PlatformNavigationTarget =
  | PlatformPageKind
  | "datasets"
  | "packs"
  | "agent-runs";

type PlatformPageProps = {
  page: PlatformPageKind;
  jobsCount: number | null;
  jobsError: string | null;
  onNavigate: (target: PlatformNavigationTarget) => void;
};

export default function PlatformPage({
  page,
  jobsCount,
  jobsError,
  onNavigate,
}: PlatformPageProps) {
  const [catalog, setCatalog] = useState<DataCatalog | null>(null);
  const [packCatalog, setPackCatalog] = useState<PackCatalog | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
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
  }, []);

  if (page === "virtual-cells") {
    return (
      <section className="data-library" aria-labelledby="virtual-cells-title">
        <header className="data-heading">
          <div>
            <h1 id="virtual-cells-title">虚拟细胞</h1>
            <p>这里将承载经显式合同构建并持久化的 VirtualCell 实例。</p>
          </div>
          <Badge tone="neutral">合同待实现</Badge>
        </header>
        <Card>
          <EmptyState
            title="尚无持久化虚拟细胞实例"
            hint="当前后端未提供 VirtualCell 实例合同或构建 API；数据集或 Pack 的存在不会自动生成实例。"
          />
          <div className="row">
            <Button variant="ghost" onClick={() => onNavigate("datasets")}>
              查看数据集
            </Button>
            <Button variant="ghost" onClick={() => onNavigate("packs")}>
              查看 VirtualCellPacks
            </Button>
            <Button onClick={() => onNavigate("agent-runs")}>
              进入 Agent Runs
            </Button>
          </div>
        </Card>
      </section>
    );
  }

  const loading = catalog == null && packCatalog == null && error == null;
  const fileCount =
    catalog?.datasets.reduce((total, dataset) => total + dataset.files.length, 0) ??
    0;

  if (page === "organisms") {
    return (
      <section className="data-library" aria-labelledby="organisms-title">
        <header className="data-heading">
          <div>
            <h1 id="organisms-title">物种库</h1>
            <p>按后端数据目录中的 taxonomy 身份汇总数据集、文件与 Pack。</p>
          </div>
          <Badge tone="neutral">只读目录</Badge>
        </header>
        <div className="note data-boundary">
          以下数字仅是目录计数，不推导 VirtualCell readiness、模型兼容性或科学有效性。
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
                    <dt>数据集</dt>
                    <dd>{datasets.length}</dd>
                  </div>
                  <div>
                    <dt>文件</dt>
                    <dd>{speciesFiles}</dd>
                  </div>
                  <div>
                    <dt>VirtualCellPack</dt>
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
          <Button variant="ghost" onClick={() => onNavigate("datasets")}>
            查看数据集
          </Button>
          <Button variant="ghost" onClick={() => onNavigate("packs")}>
            查看 VirtualCellPacks
          </Button>
          <Button onClick={() => onNavigate("agent-runs")}>
            进入 Agent Runs
          </Button>
        </div>
      </section>
    );
  }

  return (
    <section className="data-library" aria-labelledby="dashboard-title">
      <header className="data-heading">
        <div>
          <h1 id="dashboard-title">Dashboard</h1>
          <p>Inspect explicit data and execution contracts before running an agent task.</p>
        </div>
        <Badge tone="confirmed">数据中心化基座</Badge>
      </header>
      <div className="note data-boundary">
        目录可用、Pack 校验通过或接口存在，都不代表模型可执行或已经科学验证；缺少匹配模型时系统必须
        abstain。
      </div>
      <Card title="当前后端目录">
        {loading && <p className="data-message">读取平台目录…</p>}
        {error && (
          <p className="err" role="alert">
            平台目录不可用：{error}
          </p>
        )}
        {catalog && packCatalog && (
          <dl className="data-facts">
            <div>
              <dt>Organisms</dt>
              <dd>{catalog.species.length} 个物种</dd>
            </div>
            <div>
              <dt>Datasets</dt>
              <dd>{catalog.datasets.length} 个数据集</dd>
            </div>
            <div>
              <dt>Files</dt>
              <dd>{fileCount} 个文件</dd>
            </div>
            <div>
              <dt>VirtualCellPacks</dt>
              <dd>{packCatalog.packs.length} 个 VirtualCellPack</dd>
            </div>
          </dl>
        )}
        <p className="muted">
          {jobsError
            ? `Agent Run 目录不可用：${jobsError}`
            : jobsCount == null
            ? "正在读取 Agent Run 目录…"
            : `当前记录 ${jobsCount} 个 Agent Run；每次运行仍由既有五阶段工作区执行。`}
        </p>
      </Card>
      <Card title="开始工作">
        <p className="step-hint">
          浏览真实目录或进入现有 Agent Workspace。平台尚未提供持久化 VirtualCell
          构建能力。
        </p>
        <div className="row">
          <Button onClick={() => onNavigate("datasets")}>查看数据集</Button>
          <Button variant="ghost" onClick={() => onNavigate("packs")}>
            查看 VirtualCellPacks
          </Button>
          <Button variant="ghost" onClick={() => onNavigate("agent-runs")}>
            进入 Agent Runs
          </Button>
        </div>
      </Card>
    </section>
  );
}
