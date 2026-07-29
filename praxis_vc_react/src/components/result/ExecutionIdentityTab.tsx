import type { CSSProperties, ReactNode } from "react";
import type {
  ExecutionIdentity,
  ExecutionModelIdentity,
  ProvenanceResult,
} from "../../api";
import Badge from "../ui/Badge";
import Card from "../ui/Card";
import Skeleton from "../ui/Skeleton";

const stackStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "var(--space-4)",
};

const monoStyle: CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: 12,
  background: "var(--code-bg)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  padding: "1px 6px",
  color: "var(--text)",
  wordBreak: "break-all",
};

const jsonStyle: CSSProperties = {
  margin: 0,
  maxHeight: 420,
  overflow: "auto",
  whiteSpace: "pre",
  fontFamily: "var(--font-mono)",
  fontSize: 12,
  lineHeight: 1.5,
  color: "var(--text)",
  background: "var(--code-bg)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  padding: "var(--space-3)",
};

function Mono({ children }: { children: ReactNode }) {
  return <code style={monoStyle}>{children}</code>;
}

function IdentityTable({
  rows,
}: {
  rows: Array<{ label: string; value: ReactNode }>;
}) {
  return (
    <div className="table-scroll">
      <table className="kv-table module-table">
        <thead>
          <tr>
            <th style={{ width: "28%" }}>身份项</th>
            <th>后端记录</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ label, value }) => (
            <tr key={label}>
              <td>{label}</td>
              <td>{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ModelTable({ models }: { models: ExecutionModelIdentity[] }) {
  if (models.length === 0) {
    return <p style={{ margin: 0, color: "var(--text-muted)" }}>未记录模型身份</p>;
  }
  return (
    <div className="table-scroll">
      <table className="kv-table module-table">
        <thead>
          <tr>
            <th>模型</th>
            <th>版本</th>
            <th>模型 fingerprint</th>
            <th>兼容性 fingerprint</th>
            <th>可执行</th>
          </tr>
        </thead>
        <tbody>
          {models.map((model, index) => (
            <tr key={`${model.name}-${model.version}-${index}`}>
              <td><Mono>{model.name}</Mono></td>
              <td><Mono>{model.version}</Mono></td>
              <td><Mono>{model.fingerprint}</Mono></td>
              <td><Mono>{model.compatibility_fingerprint}</Mono></td>
              <td>
                <Badge tone={model.executable ? "confirmed" : "danger"}>
                  {model.executable ? "true" : "false"}
                </Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function hasRecordedIdentity(identity: ExecutionIdentity): boolean {
  return Object.keys(identity).length > 0;
}

export default function ExecutionIdentityTab({
  prov,
}: {
  prov: ProvenanceResult | null;
}) {
  if (prov == null) {
    return (
      <Card title="数据与执行身份">
        <Skeleton lines={6} />
      </Card>
    );
  }

  const identity = prov.execution_identity ?? {};
  const pack = identity.pack ?? null;
  const models = Array.isArray(identity.models) ? identity.models : [];
  const legacy = identity.legacy_adapter === true;
  const rows: Array<{ label: string; value: ReactNode }> = [
    {
      label: "执行适配模式",
      value: hasRecordedIdentity(identity) ? (
        <Mono>{legacy ? "legacy_adapter" : "execution_plan"}</Mono>
      ) : (
        "未记录 execution identity"
      ),
    },
    {
      label: "VirtualCellPack",
      value: pack ? (
        <span style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
          <Mono>{pack.pack_id}</Mono>
          <Mono>{pack.pack_version}</Mono>
          <Mono>{pack.fingerprint}</Mono>
        </span>
      ) : (
        "未绑定 VirtualCellPack"
      ),
    },
    { label: "Dataset", value: "未记录 dataset identity" },
  ];

  if (identity.schema_version) {
    rows.push({ label: "Identity schema", value: <Mono>{identity.schema_version}</Mono> });
  }
  if (identity.fingerprint) {
    rows.push({ label: "Identity fingerprint", value: <Mono>{identity.fingerprint}</Mono> });
  }

  return (
    <div style={stackStyle}>
      <Card title="数据与执行身份">
        <div
          style={{
            padding: "var(--space-3) var(--space-4)",
            marginBottom: "var(--space-4)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
            background: "color-mix(in srgb, var(--primary) 6%, var(--surface))",
            color: "var(--text-muted)",
            fontSize: 13,
          }}
        >
          此处只展示后端保存的执行身份。Pack、模型兼容或 executable 状态均不推导科学验证。
        </div>
        <IdentityTable rows={rows} />
      </Card>

      <Card title={legacy ? "模型身份（legacy）" : "模型身份"}>
        <ModelTable models={models} />
      </Card>

      <Card title="完整 execution identity JSON">
        <p style={{ margin: "0 0 var(--space-2)", color: "var(--text-muted)", fontSize: 13 }}>
          以下为后端返回的完整执行身份载荷，供逐字审计。
        </p>
        <pre style={jsonStyle}>{JSON.stringify(identity, null, 2)}</pre>
      </Card>
    </div>
  );
}
