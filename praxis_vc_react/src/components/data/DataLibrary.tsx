import { type FormEvent, useEffect, useRef, useState } from "react";
import {
  API_BASE,
  getDataCatalog,
  getPackCatalog,
  getPackFactoryCatalog,
  type DataCatalog,
  type PackCatalog,
  type PackFactoryCatalog,
  type UploadReceipt,
  uploadData,
} from "../../api";

function formatBytes(size: number): string {
  return `${new Intl.NumberFormat("zh-CN").format(size)} bytes`;
}

export default function DataLibrary({
  section,
}: {
  section: "datasets" | "packs";
}) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [filter, setFilter] = useState("");
  const [catalog, setCatalog] = useState<DataCatalog | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [packCatalog, setPackCatalog] = useState<PackCatalog | null>(null);
  const [packError, setPackError] = useState<string | null>(null);
  const [packsLoading, setPacksLoading] = useState(true);
  const [factoryCatalog, setFactoryCatalog] = useState<PackFactoryCatalog | null>(null);
  const [factoryError, setFactoryError] = useState<string | null>(null);
  const [factoryLoading, setFactoryLoading] = useState(section === "packs");
  const [uploadSpecies, setUploadSpecies] = useState("");
  const [token, setToken] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<UploadReceipt | null>(null);

  useEffect(() => {
    let current = true;
    setLoading(true);
    setCatalogError(null);
    getDataCatalog(filter || undefined)
      .then((next) => {
        if (!current) return;
        setCatalog(next);
        setUploadSpecies((previous) => previous || next.species[0]?.id || "");
      })
      .catch((error: unknown) => {
        if (!current) return;
        setCatalog(null);
        setCatalogError(String(error));
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
    };
  }, [filter]);

  useEffect(() => {
    let current = true;
    getPackCatalog()
      .then((next) => {
        if (current) setPackCatalog(next);
      })
      .catch((error: unknown) => {
        if (current) setPackError(String(error));
      })
      .finally(() => {
        if (current) setPacksLoading(false);
      });
    return () => {
      current = false;
    };
  }, []);

  useEffect(() => {
    if (section !== "packs") {
      setFactoryLoading(false);
      return;
    }
    let current = true;
    setFactoryLoading(true);
    setFactoryError(null);
    getPackFactoryCatalog()
      .then((next) => {
        if (current) setFactoryCatalog(next);
      })
      .catch((error: unknown) => {
        if (!current) return;
        setFactoryCatalog(null);
        setFactoryError(String(error));
      })
      .finally(() => {
        if (current) setFactoryLoading(false);
      });
    return () => {
      current = false;
    };
  }, [section]);

  async function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || !uploadSpecies || !token) return;
    setUploading(true);
    setUploadError(null);
    setReceipt(null);
    try {
      const next = await uploadData(uploadSpecies, file, token);
      setReceipt(next);
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
    } catch (error: unknown) {
      setUploadError(String(error));
    } finally {
      setUploading(false);
    }
  }

  return (
    <section className="data-library">
      <header className="data-heading">
        <div>
          <h1>
            {section === "packs" ? "VirtualCellPacks" : "物种组学数据资源"}
          </h1>
          <p>
            {section === "packs"
              ? "查看后端逐次重验的数据合同与模型能力声明。"
              : "下载清单锁定的公开数据，或将自己的原始文件原样上传到隔离区。"}
          </p>
        </div>
        <span className="badge">
          {section === "packs" ? "只读能力面" : "仅资源交换"}
        </span>
      </header>

      <div className="data-boundary note">
        {section === "packs"
          ? "Pack 校验通过不代表模型兼容、可执行或科学验证；具体关系必须绑定请求由后端评估。"
          : "资源入库不代表科学验证、Pack 有效或模型兼容；上传文件不会自动解包、转换、归一化或参与预测。"}
      </div>

      {section === "packs" && (
        <>
        <section
          className="card data-section"
          aria-labelledby="pack-factory-title"
        >
          <div className="data-section-head">
            <div>
              <h2 id="pack-factory-title">Pack Factory 生命周期</h2>
              <p>只读展示本地工厂的分层身份；每一层都不会隐含下一层成立。</p>
            </div>
            <span className="badge">无管理写入口</span>
          </div>

          {factoryLoading && <p className="data-message">读取 Pack Factory…</p>}
          {factoryError && (
            <p className="err" role="alert">
              Pack Factory 不可用：{factoryError}
            </p>
          )}
          {!factoryLoading && factoryCatalog && !factoryCatalog.configured && (
            <p className="data-message">未配置本地 Pack Factory store；当前目录为空。</p>
          )}
          {factoryCatalog && (
            <div className="model-capability-grid" aria-label="Pack Factory 五层状态">
              <article className="model-capability">
                <strong>1 · Quarantine</strong>
                <span>{factoryCatalog.receipts.length} 份隔离收据</span>
                <span>仅确认原始上传字节身份；不是 Pack。</span>
              </article>
              <article className="model-capability">
                <strong>2 · Candidate</strong>
                <span>{factoryCatalog.candidates.length} 个候选</span>
                <span>仍需显式审核与严格校验。</span>
              </article>
              <article className="model-capability">
                <strong>3 · Factory-registered</strong>
                <span>{factoryCatalog.registrations.length} 个登记身份</span>
                <span>只表示受控登记，不授予模型能力。</span>
              </article>
              <article className="model-capability">
                <strong>4 · Model-compatible</strong>
                <span>未按具体请求评估</span>
                <span>须由后端兼容性接口另行裁决。</span>
              </article>
              <article className="model-capability">
                <strong>5 · Executable</strong>
                <span>否</span>
                <span>工厂登记不产生执行授权、证据或生产提升。</span>
              </article>
            </div>
          )}
        </section>

        <section
          className="card data-section"
          aria-labelledby="pack-catalog-title"
        >
        <div className="data-section-head">
          <div>
            <h2 id="pack-catalog-title">VirtualCellPack 能力与验证</h2>
            <p>
              原样展示后端 Pack 校验与模型卡声明；具体请求的兼容性仍由后端裁决。
            </p>
          </div>
          <span className="badge">不在浏览器内科学路由</span>
        </div>

        {packsLoading && <p className="data-message">读取 Pack 能力…</p>}
        {packError && (
          <p className="err" role="alert">
            Pack 能力不可用：{packError}
          </p>
        )}
        <div className="data-grid">
          {packCatalog?.packs.map((pack) => (
            <article className="data-card" key={`${pack.pack_id}:${pack.pack_version}`}>
              <div className="data-card-title">
                <div>
                  <h3>{pack.pack_id}</h3>
                  <p>
                    v{pack.pack_version} · {pack.taxon?.scientific_name ?? "身份不可用"}
                  </p>
                </div>
                <div className="pack-statuses">
                  <span
                    className={`badge ${
                      pack.pack_valid ? "badge-ok" : "badge-inferred"
                    }`}
                  >
                    {pack.pack_valid === true
                      ? "Pack 校验通过"
                      : pack.pack_valid === false
                        ? "Pack 校验失败"
                        : "Pack 尚未校验"}
                  </span>
                  <span className="badge">
                    {pack.model_compatible === true
                      ? "模型兼容：通过"
                      : pack.model_compatible === false
                        ? "模型兼容：不兼容"
                        : "模型兼容：未按请求评估"}
                  </span>
                  <span className="badge badge-inferred">未科学验证</span>
                </div>
              </div>
              <dl className="data-facts">
                <div>
                  <dt>物种</dt>
                  <dd>{pack.taxon?.ontology_id ?? "不可用"}</dd>
                </div>
                <div>
                  <dt>模态</dt>
                  <dd>{pack.modalities.map((item) => item.name).join(", ") || "不可用"}</dd>
                </div>
                <div>
                  <dt>Feature namespace</dt>
                  <dd className="pack-namespaces">
                    {pack.feature_namespaces.map((item) => (
                      <span key={`${item.name}:${item.version}`}>{item.name}</span>
                    ))}
                  </dd>
                </div>
                <div>
                  <dt>Manifest</dt>
                  <dd>{pack.manifest_schema_version ?? "不可用"}</dd>
                </div>
              </dl>
              <code
                className="pack-fingerprint"
                title={`Pack fingerprint ${pack.pack_fingerprint}`}
              >
                fingerprint {pack.pack_fingerprint}
              </code>
              {pack.reasons.length > 0 && (
                <ul className="pack-reasons">
                  {pack.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              )}
            </article>
          ))}
        </div>

        <div className="model-capabilities">
          <div>
            <h3>模型能力（后端声明）</h3>
            <p>
              声明不等于可执行或科学验证；资产、环境和请求范围由 compatibility/run
              在后端逐次校验。
            </p>
          </div>
          <div className="model-capability-grid">
            {packCatalog?.model_capabilities.map((model) => (
              <article className="model-capability" key={`${model.name}:${model.version}`}>
                <strong>{model.name}</strong>
                <span>v{model.version} · {model.status}</span>
                <span>{model.taxon.join(", ") || "未声明物种"}</span>
                <span>{model.modalities.map((item) => item.name).join(", ")}</span>
                <code title={`Model fingerprint ${model.fingerprint}`}>
                  {model.fingerprint.slice(0, 12)}…
                </code>
              </article>
            ))}
            {!packsLoading && packCatalog?.model_capabilities.length === 0 && (
              <p className="data-message">后端未声明模型能力。</p>
            )}
          </div>
        </div>
        </section>
        </>
      )}

      {section === "datasets" && (
        <>
          <section className="card data-section" aria-labelledby="catalog-title">
        <div className="data-section-head">
          <div>
            <h2 id="catalog-title">公开数据目录</h2>
            <p>文件仅按清单中的大小与 SHA-256 校验后开放下载。</p>
          </div>
          <label className="data-filter">
            <span>筛选物种</span>
            <select
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            >
              <option value="">全部物种</option>
              {catalog?.species.map((species) => (
                <option key={species.id} value={species.id}>
                  {species.scientific_name} ({species.id})
                </option>
              ))}
            </select>
          </label>
        </div>

        {loading && <p className="data-message">读取目录…</p>}
        {catalogError && (
          <p className="err" role="alert">
            目录不可用：{catalogError}
          </p>
        )}
        {!loading && catalog?.datasets.length === 0 && (
          <p className="data-message">该物种暂无清单数据。</p>
        )}
        <div className="data-grid">
          {catalog?.datasets.map((dataset) => (
            <article className="data-card" key={dataset.id}>
              <div className="data-card-title">
                <div>
                  <h3>{dataset.title}</h3>
                  <p>
                    <i>{dataset.species.scientific_name}</i> ·{" "}
                    {dataset.species.taxon_id}
                  </p>
                </div>
                <span className="badge badge-inferred">未科学验证</span>
              </div>
              <dl className="data-facts">
                <div>
                  <dt>模态</dt>
                  <dd>{dataset.modality}</dd>
                </div>
                <div>
                  <dt>数值语义</dt>
                  <dd>{dataset.value_semantics}</dd>
                </div>
                <div>
                  <dt>观测数</dt>
                  <dd>{dataset.observations}</dd>
                </div>
                <div>
                  <dt>特征数</dt>
                  <dd>{dataset.features}</dd>
                </div>
              </dl>
              <p className="data-citation">{dataset.source.citation}</p>
              <div className="data-links">
                <a
                  href={dataset.source.landing_page}
                  target="_blank"
                  rel="noreferrer"
                >
                  数据说明
                </a>
                <a href={dataset.terms.url} target="_blank" rel="noreferrer">
                  使用条款：{dataset.terms.id}
                </a>
              </div>
              <div className="data-files">
                {dataset.files.map((item) => (
                  <div className="data-file" key={item.id}>
                    <div>
                      <strong>{item.filename}</strong>
                      <span>{formatBytes(item.size_bytes)}</span>
                      <code title={`SHA-256 ${item.sha256}`}>
                        SHA-256 {item.sha256.slice(0, 12)}…
                      </code>
                    </div>
                    {item.available ? (
                      <a
                        className="btn btn-ghost btn-sm"
                        href={`${API_BASE}${item.download_url}`}
                        download={item.filename}
                      >
                        下载
                      </a>
                    ) : (
                      <button
                        className="btn btn-ghost btn-sm"
                        type="button"
                        disabled
                      >
                        服务器文件未就绪
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
          </section>

          <section className="card data-section" aria-labelledby="upload-title">
        <div className="data-section-head">
          <div>
            <h2 id="upload-title">上传自己的组学数据</h2>
            <p>凭操作员令牌写入隔离区；文件保持原字节，不自动注册为数据 Pack。</p>
          </div>
          <span className="badge">
            {catalog?.upload.enabled ? "隔离上传已启用" : "隔离上传未启用"}
          </span>
        </div>

        <form className="data-upload-form" onSubmit={submitUpload}>
          <label>
            <span>上传物种</span>
            <select
              value={uploadSpecies}
              onChange={(event) => setUploadSpecies(event.target.value)}
              disabled={!catalog?.upload.enabled}
            >
              {catalog?.species.map((species) => (
                <option key={species.id} value={species.id}>
                  {species.scientific_name} ({species.id})
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>上传令牌</span>
            <input
              type="password"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              autoComplete="off"
              disabled={!catalog?.upload.enabled}
            />
          </label>
          <label className="data-file-picker">
            <span>组学数据文件</span>
            <input
              ref={fileInput}
              type="file"
              accept={catalog?.upload.accepted_extensions.join(",")}
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              disabled={!catalog?.upload.enabled}
            />
          </label>
          {catalog?.upload.enabled && (
            <p className="data-upload-limit">
              单文件上限 {formatBytes(catalog.upload.max_file_bytes)}；接受{" "}
              {catalog.upload.accepted_extensions.join("、")}
            </p>
          )}
          <button
            className="btn"
            type="submit"
            disabled={
              uploading ||
              !catalog?.upload.enabled ||
              !uploadSpecies ||
              !token ||
              !file
            }
          >
            {uploading ? "正在上传…" : "上传到隔离区"}
          </button>
        </form>

        {uploadError && (
          <p className="err" role="alert">
            上传失败：{uploadError}
          </p>
        )}
        {receipt && (
          <div className="data-upload-success" role="status">
            <strong>已进入隔离区</strong>
            <span>
              {receipt.filename} · {formatBytes(receipt.size_bytes)}
            </span>
            <code>SHA-256 {receipt.sha256}</code>
            <p>该文件不会自动参与预测；后续须经过独立审查与显式注册。</p>
          </div>
        )}
          </section>
        </>
      )}
    </section>
  );
}
