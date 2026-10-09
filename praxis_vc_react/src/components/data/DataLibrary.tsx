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
  return `${new Intl.NumberFormat("en-US").format(size)} bytes`;
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
            {section === "packs" ? "VirtualCellPacks" : "Species omics resources"}
          </h1>
          <p>
            {section === "packs"
              ? "Inspect data contracts revalidated by the backend and declared model capabilities."
              : "Download manifest-pinned public data or upload your original files unchanged to quarantine."}
          </p>
        </div>
        <span className="badge">
          {section === "packs" ? "Read-only capabilities" : "Resource exchange only"}
        </span>
      </header>

      <div className="data-boundary note">
        {section === "packs"
          ? "Pack validation does not imply model compatibility, execution capability, or scientific validation. The backend evaluates these for a specific request."
          : "Resource intake does not imply scientific validation, Pack validity, or model compatibility. Uploads are not automatically unpacked, converted, normalized, or used for prediction."}
      </div>

      {section === "packs" && (
        <>
        <section
          className="card data-section"
          aria-labelledby="pack-factory-title"
        >
          <div className="data-section-head">
            <div>
              <h2 id="pack-factory-title">Pack Factory lifecycle</h2>
              <p>Inspect the local factory lifecycle. Each stage has a separate identity and does not imply the next stage.</p>
            </div>
            <span className="badge">No administrative write actions</span>
          </div>

          {factoryLoading && <p className="data-message">Loading Pack Factory…</p>}
          {factoryError && (
            <p className="err" role="alert">
              Pack Factory unavailable: {factoryError}
            </p>
          )}
          {!factoryLoading && factoryCatalog && !factoryCatalog.configured && (
            <p className="data-message">No local Pack Factory store is configured; the catalog is empty.</p>
          )}
          {factoryCatalog && (
            <div className="model-capability-grid" aria-label="Pack Factory five-stage status">
              <article className="model-capability">
                <strong>1 · Quarantine</strong>
                <span>{factoryCatalog.receipts.length} quarantine receipts</span>
                <span>Identifies the original uploaded bytes; this is not a Pack.</span>
              </article>
              <article className="model-capability">
                <strong>2 · Candidate</strong>
                <span>{factoryCatalog.candidates.length} candidates</span>
                <span>Requires explicit review and strict validation.</span>
              </article>
              <article className="model-capability">
                <strong>3 · Factory-registered</strong>
                <span>{factoryCatalog.registrations.length} registered identities</span>
                <span>Records controlled registration without granting model capabilities.</span>
              </article>
              <article className="model-capability">
                <strong>4 · Model-compatible</strong>
                <span>Not evaluated for a specific request</span>
                <span>Requires a separate decision from the backend compatibility interface.</span>
              </article>
              <article className="model-capability">
                <strong>5 · Executable</strong>
                <span>No</span>
                <span>Factory registration does not grant execution authorization, evidence, or production promotion.</span>
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
            <h2 id="pack-catalog-title">VirtualCellPack capabilities and validation</h2>
            <p>
              Displays backend Pack validation and model card declarations. The backend determines compatibility for each request.
            </p>
          </div>
          <span className="badge">Scientific routing stays in the backend</span>
        </div>

        {packsLoading && <p className="data-message">Loading Pack capabilities…</p>}
        {packError && (
          <p className="err" role="alert">
            Pack capabilities unavailable: {packError}
          </p>
        )}
        <div className="data-grid">
          {packCatalog?.packs.map((pack) => (
            <article className="data-card" key={`${pack.pack_id}:${pack.pack_version}`}>
              <div className="data-card-title">
                <div>
                  <h3>{pack.pack_id}</h3>
                  <p>
                    v{pack.pack_version} · {pack.taxon?.scientific_name ?? "Identity unavailable"}
                  </p>
                </div>
                <div className="pack-statuses">
                  <span
                    className={`badge ${
                      pack.pack_valid ? "badge-ok" : "badge-inferred"
                    }`}
                  >
                    {pack.pack_valid === true
                      ? "Pack validation passed"
                      : pack.pack_valid === false
                        ? "Pack validation failed"
                        : "Pack not yet validated"}
                  </span>
                  <span className="badge">
                    {pack.model_compatible === true
                      ? "Model compatibility: passed"
                      : pack.model_compatible === false
                        ? "Model compatibility: incompatible"
                        : "Model compatibility: not evaluated for a request"}
                  </span>
                  <span className="badge badge-inferred">Not scientifically validated</span>
                </div>
              </div>
              <dl className="data-facts">
                <div>
                  <dt>Species</dt>
                  <dd>{pack.taxon?.ontology_id ?? "Unavailable"}</dd>
                </div>
                <div>
                  <dt>Modalities</dt>
                  <dd>{pack.modalities.map((item) => item.name).join(", ") || "Unavailable"}</dd>
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
                  <dd>{pack.manifest_schema_version ?? "Unavailable"}</dd>
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
            <h3>Model capabilities (backend declarations)</h3>
            <p>
              Declarations do not imply execution capability or scientific validation. Assets, environment, and request scope are checked by compatibility/run
              on each backend call.
            </p>
          </div>
          <div className="model-capability-grid">
            {packCatalog?.model_capabilities.map((model) => (
              <article className="model-capability" key={`${model.name}:${model.version}`}>
                <strong>{model.name}</strong>
                <span>v{model.version} · {model.status}</span>
                <span>{model.taxon.join(", ") || "No species declared"}</span>
                <span>{model.modalities.map((item) => item.name).join(", ")}</span>
                <code title={`Model fingerprint ${model.fingerprint}`}>
                  {model.fingerprint.slice(0, 12)}…
                </code>
              </article>
            ))}
            {!packsLoading && packCatalog?.model_capabilities.length === 0 && (
              <p className="data-message">The backend declares no model capabilities.</p>
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
            <h2 id="catalog-title">Public data catalog</h2>
            <p>Downloads are available only after file size and SHA-256 match the manifest.</p>
          </div>
          <label className="data-filter">
            <span>Filter species</span>
            <select
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            >
              <option value="">All species</option>
              {catalog?.species.map((species) => (
                <option key={species.id} value={species.id}>
                  {species.scientific_name} ({species.id})
                </option>
              ))}
            </select>
          </label>
        </div>

        {loading && <p className="data-message">Loading catalog…</p>}
        {catalogError && (
          <p className="err" role="alert">
            Catalog unavailable: {catalogError}
          </p>
        )}
        {!loading && catalog?.datasets.length === 0 && (
          <p className="data-message">No manifest data is available for this species.</p>
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
                <span className="badge badge-inferred">Not scientifically validated</span>
              </div>
              <dl className="data-facts">
                <div>
                  <dt>Modalities</dt>
                  <dd>{dataset.modality}</dd>
                </div>
                <div>
                  <dt>Value semantics</dt>
                  <dd>{dataset.value_semantics}</dd>
                </div>
                <div>
                  <dt>Observations</dt>
                  <dd>{dataset.observations}</dd>
                </div>
                <div>
                  <dt>Features</dt>
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
                  Data documentation
                </a>
                <a href={dataset.terms.url} target="_blank" rel="noreferrer">
                  Terms of use: {dataset.terms.id}
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
                        Download
                      </a>
                    ) : (
                      <button
                        className="btn btn-ghost btn-sm"
                        type="button"
                        disabled
                      >
                        Server file not ready
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
            <h2 id="upload-title">Upload your omics data</h2>
            <p>Upload to quarantine with an operator token. Files retain their original bytes and are not automatically registered as data Packs.</p>
          </div>
          <span className="badge">
            {catalog?.upload.enabled ? "Quarantine uploads enabled" : "Quarantine uploads disabled"}
          </span>
        </div>

        <form className="data-upload-form" onSubmit={submitUpload}>
          <label>
            <span>Upload species</span>
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
            <span>Upload token</span>
            <input
              type="password"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              autoComplete="off"
              disabled={!catalog?.upload.enabled}
            />
          </label>
          <label className="data-file-picker">
            <span>Omics data file</span>
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
              Per-file limit: {formatBytes(catalog.upload.max_file_bytes)}; accepted formats:{" "}
              {catalog.upload.accepted_extensions.join(", ")}
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
            {uploading ? "Uploading…" : "Upload to quarantine"}
          </button>
        </form>

        {uploadError && (
          <p className="err" role="alert">
            Upload failed: {uploadError}
          </p>
        )}
        {receipt && (
          <div className="data-upload-success" role="status">
            <strong>Quarantined</strong>
            <code>Upload ID {receipt.upload_id}</code>
            <span>
              {receipt.filename} · {formatBytes(receipt.size_bytes)}
            </span>
            <code>SHA-256 {receipt.sha256}</code>
            <p>
              Next, an operator must revalidate and record this quarantine receipt:
            </p>
            <code>
              praxis-vc pack factory-init --data-root /ABSOLUTE/DATA-ROOT
              {" "}--upload-id {receipt.upload_id} --store
              {" "}/ABSOLUTE/NEW-FACTORY-STORE
            </code>
            <p>
              This command does not parse data, create a candidate, or register a Pack. Files still require independent review.
            </p>
          </div>
        )}
          </section>
        </>
      )}
    </section>
  );
}
