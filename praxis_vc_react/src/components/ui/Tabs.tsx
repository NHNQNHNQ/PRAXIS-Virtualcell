import type { ReactNode } from "react";

// 受控 segmented tabs(spec §2 Stage5 六 tab 容器复用)。走 components.css 的 .tabs / .tab / .tab.active。
// 纯展示 + 单一 onChange 回调,不持有选中态(由父级控制)。

export type TabItem = {
  id: string;
  label: ReactNode;
};

export type TabsProps = {
  tabs: TabItem[];
  active: string;
  onChange: (id: string) => void;
};

export default function Tabs({ tabs, active, onChange }: TabsProps) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => (
        <button
          key={t.id}
          type="button"
          role="tab"
          aria-selected={t.id === active}
          className={t.id === active ? "tab active" : "tab"}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
